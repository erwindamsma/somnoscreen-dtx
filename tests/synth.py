"""Synthetic DTX and konfig.dt2 files, encoded the way the recorder encodes them."""

import numpy as np

from somnoscreen_dtx import adpcm
from somnoscreen_dtx.dtx import BLOCK_SECONDS, PG12, PREAMBLE_BYTES
from somnoscreen_dtx.konfig import CHANNEL_TABLE, CLOCK_DIVIDER, FIRST_CHANNEL, SAMPLES_PER_BLOCK

# fmt: off
CHANNEL_NUMBERS = (37, 39, 43, 45, 47, 48, 50, 54, 55, 58, 59, 60)
NAMES = ('Flow Th', 'ECG-AUX', 'Flow Pr', 'Abdomen', 'Snore', 'Thorax',
         'Pos.', 'Light', 'Battery', 'Pleth', 'Pulse', 'SPO2')
VALUES = (0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0xBFFF, 0xFFFF,
          0x0003, 0x03FF, 0x0002, 0x00FF, 0x0002, 0x0002)
DIVIDERS = (8, 1, 1, 8, 1, 8, 64, 64, 64, 2, 64, 64)
# fmt: on
INITIAL = ((11, 8), (11, 8), (-11, 8), (-11, 8), (11, 8), (-11, 8))


def make_signals(blocks, seed=0):
    rng = np.random.default_rng(seed)
    signals = {}
    for role, rate in PG12.rates.items():
        t = np.arange(int(blocks * rate * BLOCK_SECONDS)) / rate
        if role == 'pleth':
            x = 120 + 60 * np.sin(2 * np.pi * 1.1 * t) + rng.normal(0, 2, len(t))
            signals[role] = np.clip(np.round(x), 0, 255).astype(np.int64)
        else:
            x = 9000 * np.sin(2 * np.pi * 0.25 * t) + 1500 * np.sin(2 * np.pi * 7 * t)
            signals[role] = np.round(x + rng.normal(0, 300, len(t))).astype(np.int64)
    header = {
        'position': np.repeat([3000, 1300, 2000, 600], -(-blocks // 4))[:blocks],
        'light': rng.integers(0, 30, blocks),
        'header_byte5': np.zeros(blocks, np.int64),
        'battery': 3500 - np.arange(blocks) // 10,
        'pulse': rng.integers(55, 75, blocks),
        'spo2': rng.integers(92, 99, blocks),
    }
    return signals, header


def _encode(x, slots, blocks, state, limits):
    """Encode per block: one stored code per slot, then the final sample whose code is
    not stored. Returns codes (blocks, slots), reconstruction and the state after each block."""
    pred, index = state
    per_block = len(slots) + 1
    codes = np.zeros((blocks, len(slots)), np.int64)
    recon = np.empty(blocks * per_block, np.int64)
    states = []
    for b in range(blocks):
        for j in range(per_block):
            code, pred, index = adpcm.encode_sample(x[b * per_block + j], pred, index, limits)
            recon[b * per_block + j] = pred
            if j < len(slots):
                codes[b, j] = code
        states.append((pred, index))
    return codes, recon, states


def _state_bytes(pred, index):
    return (int(pred) & 0xFFFF).to_bytes(2, 'big') + bytes([index])


def make_dtx(signals, header, blocks, truncated=150):
    """Return (file bytes, reconstructed signals). The final block is cut to `truncated`
    bytes, as when a recording stops mid-block (0 = no partial block)."""
    nibbles = np.zeros((blocks + 1, 242), np.int64)
    recon, tails = {}, []
    for c, role in enumerate(PG12.tail):
        slots = PG12.slots(role)
        codes, recon[role], states = _encode(signals[role], slots, blocks, INITIAL[c], adpcm.INT16)
        nibbles[:blocks, slots] = codes
        tails.append(states)
    slots = PG12.slots(PG12.header_adpcm)
    pleth_start = (int(signals['pleth'][0]), 0)
    codes, recon['pleth'], pleth_states = _encode(
        signals['pleth'], slots, blocks, pleth_start, adpcm.UINT8
    )
    nibbles[:blocks, slots] = codes
    pleth_states = [pleth_start, *pleth_states]

    out = bytearray(PREAMBLE_BYTES)
    for pred, index in INITIAL:
        out += _state_bytes(pred, index)
    for b in range(blocks + 1):
        if b == blocks and not truncated:
            break
        h = {key: int(values[min(b, blocks - 1)]) for key, values in header.items()}
        hb = bytearray(15)
        hb[0:2] = h['position'].to_bytes(2, 'big')
        hb[4], hb[5] = h['light'], h['header_byte5']
        hb[6:8] = h['battery'].to_bytes(2, 'big')
        hb[8:11] = _state_bytes(*pleth_states[b])
        hb[11], hb[13] = h['pulse'], h['spo2']
        body = bytes((nibbles[b, 2 * k] << 4) | nibbles[b, 2 * k + 1] for k in range(121))
        tail = b''.join(_state_bytes(*tails[c][b]) for c in range(6)) if b < blocks else bytes(18)
        block = bytes(hb) + body + tail
        out += block if b < blocks else block[:truncated]
    return bytes(out), recon


def make_konfig(signature=None):
    raw = bytearray(2048)

    def put(offset, text):
        raw[offset : offset + len(text)] = text.encode('latin-1')

    put(0x09, 'Test')
    put(0x1E, 'T.')
    put(0x33, '01012025')
    put(0x3C, '01011980')
    put(0x45, '180')
    put(0x49, '80')
    put(0x4D, 'M')
    raw[0xB4:0xB8] = bytes([1, 1, 22, 30])
    raw[0x15D:0x162] = bytes([8, 1, 1, 22, 30])
    per_block = signature or PG12.signature
    for i in range(32):
        number = FIRST_CHANNEL + i
        entry = CHANNEL_TABLE + 10 * i
        if number in CHANNEL_NUMBERS:
            k = CHANNEL_NUMBERS.index(number)
            put(entry, NAMES[k])
            raw[entry + 8 : entry + 10] = VALUES[k].to_bytes(2, 'big')
            raw[SAMPLES_PER_BLOCK + i] = per_block[k]
            raw[CLOCK_DIVIDER + i] = DIVIDERS[k]
        else:
            put(entry, f'C:{number}')
    return bytes(raw)
