"""EDF export: one 0.25-s data record per DTX block, values exactly as decoded."""

import datetime as dt

import numpy as np

from .dtx import BLOCK_SECONDS

MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']


def _field(value, width):
    text = str(value).encode('ascii', 'replace')
    if len(text) > width:
        raise ValueError(f'EDF header field too long: {value!r}')
    return text.ljust(width)


def _patient_field(konfig):
    """EDF+ style patient field: code, sex, birth date, name."""
    birth = 'X'
    b = konfig.birth_date
    if len(b) == 8 and b.isdigit() and 1 <= int(b[2:4]) <= 12:
        birth = f'{b[:2]}-{MONTHS[int(b[2:4]) - 1]}-{b[4:]}'
    name = '_'.join(part for part in (konfig.surname, konfig.initials) if part) or 'X'
    return f'X {konfig.sex or "X"} {birth} {name.replace(" ", "_")}'


def write_edf(recording, path, clean_ecg=False, include_patient=False):
    """Write all channels to a plain EDF file.

    Physical values equal the stored device values: the recording carries no calibration.
    clean_ecg adds a channel with the interference-free ECG (needs scipy).
    include_patient copies name, sex and birth date from konfig.dt2 into the header;
    by default the patient field is anonymous.
    """
    per_block = {role: round(s.rate * BLOCK_SECONDS) for role, s in recording.signals.items()}
    roles = [*recording.montage.roles, 'header_byte5']
    channels = []
    for role in roles:
        s = recording.signals[role]
        data = s.data[: recording.blocks * per_block[role]].astype(np.int64)
        if np.issubdtype(s.data.dtype, np.integer) and s.data.dtype.itemsize <= 2:
            lo, hi = np.iinfo(s.data.dtype).min, np.iinfo(s.data.dtype).max
        else:
            lo, hi = int(data.min()), max(int(data.max()), int(data.min()) + 1)
            if lo < -32768 or hi > 32767:
                raise ValueError(f'{s.label}: values outside the 16-bit EDF range')
        channels.append((s.label, s.unit, per_block[role], data, lo, hi))
    if clean_ecg:
        from .ecg import clean_ecg as clean

        ecg = recording.signals['ecg']
        cleaned = np.clip(np.round(clean(ecg.data, ecg.rate)), -32768, 32767).astype(np.int64)
        channels.append(
            (
                'ECG cleaned',
                ecg.unit,
                per_block['ecg'],
                cleaned[: recording.blocks * per_block['ecg']],
                -32768,
                32767,
            )
        )

    start = recording.start or dt.datetime(1985, 1, 1)
    patient = 'X X X X'
    if include_patient and recording.konfig is not None:
        patient = _patient_field(recording.konfig)
    date = f'{start.day:02d}-{MONTHS[start.month - 1]}-{start.year}' if recording.start else 'X'

    ns = len(channels)
    head = _field('0', 8) + _field(patient, 80)
    head += _field(f'Startdate {date} X X SOMNOscreen_plus', 80)
    head += _field(start.strftime('%d.%m.%y'), 8) + _field(start.strftime('%H.%M.%S'), 8)
    head += _field(256 * (ns + 1), 8) + _field('', 44)
    head += _field(recording.blocks, 8) + _field(f'{BLOCK_SECONDS:g}', 8) + _field(ns, 4)
    columns = [
        (16, lambda c: c[0]),
        (80, lambda c: ''),
        (8, lambda c: c[1]),
        (8, lambda c: c[4]),
        (8, lambda c: c[5]),
        (8, lambda c: c[4]),
        (8, lambda c: c[5]),
        (80, lambda c: ''),
        (8, lambda c: c[2]),
        (32, lambda c: ''),
    ]
    for width, value in columns:
        head += b''.join(_field(value(c), width) for c in channels)

    records = np.concatenate(
        [c[3].astype('<i2').reshape(recording.blocks, c[2]) for c in channels], axis=1
    )
    with open(path, 'wb') as fh:
        fh.write(head)
        fh.write(records.tobytes())
