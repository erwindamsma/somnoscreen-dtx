"""Reader for konfig.dt2, the recording configuration stored next to DATEN1.DTX.

See FORMAT.md for the layout. The file holds no calibration (gains, offsets or units).
"""
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

SIZE = 2048
CHANNEL_TABLE = 0x44C      # 32 x (8-byte name, 16-bit big-endian value), channels 33..64
SAMPLES_PER_BLOCK = 0x400  # 32 bytes, channels 33..64
CLOCK_DIVIDER = 0x420      # 32 bytes, channels 33..64, divider from a 256 Hz clock
FIRST_CHANNEL = 33
LOG = 0x15D
LOG_END = 0x1DC


@dataclass
class Channel:
    number: int
    name: str
    value: int              # 16-bit field after the name: 0xffff, 0x03ff, 0x00ff, 2, 3 ...
    samples_per_block: int  # per 0.25 s
    divider: int            # sampling rate = 256 Hz / divider


@dataclass
class Konfig:
    surname: str
    initials: str
    birth_date: str          # as stored, ddmmyyyy
    sex: str
    height_cm: int | None
    weight_kg: int | None
    recording_date: dt.date | None
    programmed: dt.datetime | None
    channels: list[Channel] = field(default_factory=list)
    log: list[tuple[int, int, int, int, int]] = field(default_factory=list)

    @property
    def montage(self):
        """(name, samples per block) of the active channels, in channel order."""
        return [(c.name, c.samples_per_block) for c in self.channels]


def _text(raw, start, end):
    return raw[start:end].split(b'\0')[0].decode('latin-1').strip()


def _int(text):
    return int(text) if text.isdigit() else None


def read_konfig(path):
    raw = Path(path).read_bytes()
    if len(raw) < SIZE:
        raise ValueError(f'{path}: expected {SIZE} bytes, got {len(raw)}')

    date_text = _text(raw, 0x33, 0x3C)
    recording_date = None
    if len(date_text) == 8 and date_text.isdigit():
        recording_date = dt.date(int(date_text[4:]), int(date_text[2:4]), int(date_text[:2]))

    programmed = None
    day, month, hour, minute = raw[0xB4:0xB8]
    if recording_date and 1 <= month <= 12 and 1 <= day <= 31 and hour < 24 and minute < 60:
        year = recording_date.year - (1 if month > recording_date.month else 0)
        programmed = dt.datetime(year, month, day, hour, minute)

    channels = []
    for i in range(32):
        entry = raw[CHANNEL_TABLE + 10 * i:CHANNEL_TABLE + 10 * i + 10]
        name = entry[:8].split(b'\0')[0].decode('latin-1')
        per_block, divider = raw[SAMPLES_PER_BLOCK + i], raw[CLOCK_DIVIDER + i]
        if per_block or divider:
            channels.append(Channel(FIRST_CHANNEL + i, name, int.from_bytes(entry[8:10], 'big'),
                                    per_block, divider))

    log = []
    for pos in range(LOG, LOG_END - 4, 5):
        code, day, month, hour, minute = raw[pos:pos + 5]
        if code and 1 <= month <= 12 and 1 <= day <= 31 and hour < 24 and minute < 60:
            log.append((code, day, month, hour, minute))

    return Konfig(
        surname=_text(raw, 0x09, 0x1E),
        initials=_text(raw, 0x1E, 0x22),
        birth_date=_text(raw, 0x3C, 0x45),
        sex=_text(raw, 0x4D, 0x4E),
        height_cm=_int(_text(raw, 0x45, 0x48)),
        weight_kg=_int(_text(raw, 0x49, 0x4C)),
        recording_date=recording_date,
        programmed=programmed,
        channels=channels,
        log=log,
    )
