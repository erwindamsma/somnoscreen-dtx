"""Decoder for DATEN1.DTX, the raw recording of a SOMNOscreen plus. See FORMAT.md."""
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import adpcm
from .konfig import Konfig, read_konfig

BLOCK_BYTES = 154
BLOCK_SECONDS = 0.25
HEADER_BYTES = 15
NIBBLE_BYTES = 121
TAIL_BYTES = 18
PREAMBLE_BYTES = 121
FIRST_BLOCK = PREAMBLE_BYTES + TAIL_BYTES


class UnsupportedMontage(ValueError):
    pass


@dataclass(frozen=True)
class Montage:
    """Channel layout of one recorder configuration.

    roles         channel roles in konfig.dt2 order
    tail          roles whose ADPCM state ends each block, in tail order
    header_adpcm  role whose ADPCM state sits in the block header
    rates         sampling rate per waveform role, Hz
    frame         role per slot of a 31-slot frame (1/32 s)
    signature     samples per block of the konfig channels, in order
    """
    name: str
    roles: tuple
    tail: tuple
    header_adpcm: str
    rates: dict
    frame: tuple
    signature: tuple
    default_labels: dict

    def slots(self, role):
        """Nibble positions of a role within a block: 8 frames minus the final sample of
        each ADPCM channel, which the block stores as a state instead of a code."""
        stored = 8 * len(self.frame) - len(self.tail) - 1
        return [p for p in range(stored) if self.frame[p % len(self.frame)] == role]


_E, _P, _S, _L = 'ecg', 'flow_pr', 'snore', 'pleth'
PG12 = Montage(
    name='PG, 12 channels (thermistor + pressure flow)',
    roles=('flow_th', 'ecg', 'flow_pr', 'abdomen', 'snore', 'thorax',
           'position', 'light', 'battery', 'pleth', 'pulse', 'spo2'),
    tail=('flow_th', 'ecg', 'flow_pr', 'abdomen', 'snore', 'thorax'),
    header_adpcm='pleth',
    rates={'flow_th': 32, 'ecg': 256, 'flow_pr': 256, 'abdomen': 32, 'snore': 256,
           'thorax': 32, 'pleth': 128},
    frame=(_E, _P, _S, _E, _P, _S, _L, _E, _P, _S, _E, _P, _S, _L, _E, _P, _S, _E, _P, _S, _L,
           _E, _P, _S, 'flow_th', _E, _P, 'abdomen', _S, 'thorax', _L),
    signature=(8, 64, 64, 8, 64, 8, 8, 8, 8, 32, 1, 1),
    default_labels={'flow_th': 'Flow Th', 'ecg': 'ECG-AUX', 'flow_pr': 'Flow Pr',
                    'abdomen': 'Abdomen', 'snore': 'Snore', 'thorax': 'Thorax',
                    'position': 'Pos.', 'light': 'Light', 'battery': 'Battery',
                    'pleth': 'Pleth', 'pulse': 'Pulse', 'spo2': 'SPO2'},
)
MONTAGES = (PG12,)

# Header fields stored once per block (4 Hz): role -> (offset, size, unit)
HEADER_FIELDS = {
    'position': (0, 2, ''),
    'light': (4, 1, ''),
    'header_byte5': (5, 1, ''),
    'battery': (6, 2, 'mV'),
    'pulse': (11, 1, 'bpm'),
    'spo2': (13, 1, '%'),
}

POSITIONS = {0: 'prone', 600: 'upright', 1300: 'left', 2000: 'right',
             2500: 'upside down', 3000: 'supine'}


@dataclass
class Signal:
    label: str
    rate: float
    data: np.ndarray
    unit: str = ''


@dataclass
class Recording:
    signals: dict
    start: object
    blocks: int
    trailing_bytes: int
    consistency: dict
    montage: Montage
    konfig: Konfig | None
    header: np.ndarray = field(repr=False)

    @property
    def duration(self):
        return self.blocks * BLOCK_SECONDS


def detect_montage(konfig):
    if konfig is None:
        return None
    signature = tuple(c.samples_per_block for c in konfig.channels)
    for montage in MONTAGES:
        if montage.signature == signature:
            return montage
    raise UnsupportedMontage(
        'unknown channel configuration in konfig.dt2: '
        + ', '.join(f'{c.name} ({c.samples_per_block * 4} Hz)' for c in konfig.channels)
        + '. Only the 12-channel PG montage is known so far; a sample recording of this '
          'configuration would allow adding it.')


def _states(raw):
    """Big-endian int16 predictors and step indices from 3-byte groups."""
    raw = raw.astype(np.int64)
    pred = ((raw[..., 0::3] << 8) | raw[..., 1::3]).astype(np.uint16).astype(np.int16)
    return pred.astype(np.int64), raw[..., 2::3]


def _decode(nibbles, slots, pred, index, final, limits):
    out = np.empty((len(pred), len(slots) + 1), dtype=np.int64)
    for j, slot in enumerate(slots):
        pred, index = adpcm.step(pred, index, nibbles[:, slot], limits)
        out[:, j] = pred
    out[:, -1] = final
    return out, pred, index


def _reachable(pred, index, next_pred, next_index, limits):
    """True where some code turns the state after the stored codes into the next state."""
    ok = np.zeros(len(pred), bool)
    for code in range(16):
        p, i = adpcm.step(pred, index, np.int64(code), limits)
        ok |= (p == next_pred) & (i == next_index)
    return ok


def read_dtx(path, konfig='auto', montage=None):
    """Decode DATEN1.DTX.

    konfig: path to konfig.dt2, a Konfig, None, or 'auto' (konfig.dt2 next to the DTX file).
    montage: force a layout instead of detecting it from konfig.dt2.
    """
    path = Path(path)
    if isinstance(konfig, str) and konfig == 'auto':
        candidate = path.with_name('konfig.dt2')
        konfig = read_konfig(candidate) if candidate.exists() else None
    elif konfig is not None and not isinstance(konfig, Konfig):
        konfig = read_konfig(konfig)
    if montage is None:
        montage = detect_montage(konfig)
    if montage is None:
        warnings.warn('no konfig.dt2: assuming the 12-channel PG montage', stacklevel=2)
        montage = PG12

    raw = np.fromfile(path, dtype=np.uint8)
    if len(raw) < FIRST_BLOCK + BLOCK_BYTES:
        raise ValueError(f'{path}: too small for a DTX recording')
    n = (len(raw) - FIRST_BLOCK) // BLOCK_BYTES
    trailing = raw[FIRST_BLOCK + n * BLOCK_BYTES:]
    blocks = raw[FIRST_BLOCK:FIRST_BLOCK + n * BLOCK_BYTES].reshape(n, BLOCK_BYTES)
    header = blocks[:, :HEADER_BYTES]
    body = blocks[:, HEADER_BYTES:HEADER_BYTES + NIBBLE_BYTES]
    nibbles = np.empty((n, 2 * NIBBLE_BYTES), dtype=np.int64)
    nibbles[:, 0::2], nibbles[:, 1::2] = body >> 4, body & 15

    tail = np.vstack([raw[PREAMBLE_BYTES:FIRST_BLOCK],
                      blocks[:, HEADER_BYTES + NIBBLE_BYTES:]])
    tail_pred, tail_index = _states(tail)

    labels = dict(montage.default_labels)
    if konfig is not None:
        labels.update({role: c.name for role, c in zip(montage.roles, konfig.channels) if c.name})

    signals, consistency = {}, {}
    for c, role in enumerate(montage.tail):
        out, pred, index = _decode(nibbles, montage.slots(role), tail_pred[:-1, c],
                                   tail_index[:-1, c], tail_pred[1:, c], adpcm.INT16)
        signals[role] = Signal(labels[role], montage.rates[role], out.ravel().astype(np.int16))
        consistency[role] = _reachable(pred, index, tail_pred[1:, c], tail_index[1:, c],
                                       adpcm.INT16).mean()

    # The header ADPCM channel: a block header holds the state at the block's start, so the
    # final sample of block i is the state in header i+1 (for the last complete block: the
    # header of the truncated block after it, if present).
    role = montage.header_adpcm
    h = header.astype(np.int64)
    h_pred, h_index = (h[:, 8] << 8) | h[:, 9], h[:, 10]
    if len(trailing) >= 11:
        next_pred = np.r_[h_pred[1:], (int(trailing[8]) << 8) | int(trailing[9])]
        next_index = np.r_[h_index[1:], int(trailing[10])]
        checked = n
    else:
        next_pred = np.r_[h_pred[1:], h_pred[-1]]
        next_index = np.r_[h_index[1:], h_index[-1]]
        checked = n - 1
    out, pred, index = _decode(nibbles, montage.slots(role), h_pred, h_index, next_pred,
                               adpcm.UINT8)
    if checked < n:
        out[-1, -1] = out[-1, -2]
    signals[role] = Signal(labels[role], montage.rates[role], out.ravel().astype(np.uint8))
    consistency[role] = _reachable(pred[:checked], index[:checked], next_pred[:checked],
                                   next_index[:checked], adpcm.UINT8).mean()

    for role, (offset, size, unit) in HEADER_FIELDS.items():
        value = h[:, offset] if size == 1 else (h[:, offset] << 8) | h[:, offset + 1]
        label = labels.get(role, 'Header byte 5' if role == 'header_byte5' else role)
        signals[role] = Signal(label, 1 / BLOCK_SECONDS, value.astype(np.int32), unit)

    start = konfig.programmed if konfig is not None else None
    return Recording(signals=signals, start=start, blocks=n, trailing_bytes=len(trailing),
                     consistency=consistency, montage=montage, konfig=konfig, header=header)
