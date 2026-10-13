import argparse
import sys
from pathlib import Path

import numpy as np

from .dtx import POSITIONS, read_dtx
from .edf import write_edf


def _load(args):
    konfig = args.konfig if args.konfig else 'auto'
    return read_dtx(args.dtx, konfig=konfig)


def info(args):
    rec = _load(args)
    hours, rest = divmod(int(rec.duration), 3600)
    print(f'File:      {args.dtx}')
    print(f'Montage:   {rec.montage.name}')
    print(f'Start:     {rec.start or "unknown (no konfig.dt2)"}')
    print(
        f'Duration:  {hours}:{rest // 60:02d}:{rest % 60:02d} ({rec.blocks} blocks of 0.25 s'
        + (f', {rec.trailing_bytes} trailing bytes' if rec.trailing_bytes else '')
        + ')'
    )
    print()
    print(f'{"Channel":<16}{"Rate":>9}  Check')
    for role in rec.montage.roles:
        s = rec.signals[role]
        check = f'{rec.consistency[role]:.3%}' if role in rec.consistency else ''
        print(f'{s.label:<16}{s.rate:>6g} Hz  {check}')
    print()
    print('Check: share of blocks whose decoded data ends exactly on the state stored by the')
    print('recorder. Values close to 100% mean the file was decoded correctly.')
    if args.show_patient and rec.konfig is not None:
        k = rec.konfig
        print()
        print(
            f'Patient:   {k.surname} {k.initials}, {k.sex}, born {k.birth_date}, '
            f'{k.height_cm} cm, {k.weight_kg} kg'
        )
    positions = rec.signals['position'].data
    print()
    print(
        'Body position (minutes):',
        ', '.join(
            f'{POSITIONS.get(int(code), code)} {count * 0.25 / 60:.0f}'
            for code, count in zip(*np.unique(positions, return_counts=True), strict=True)
        ),
    )


def edf(args):
    rec = _load(args)
    out = Path(args.output or Path(args.dtx).with_suffix('.edf'))
    write_edf(rec, out, clean_ecg=args.clean_ecg, include_patient=args.include_patient)
    print(f'{out}: {rec.blocks} records of 0.25 s, {len(rec.signals) + args.clean_ecg} channels')


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='somnoscreen-dtx',
        description='Read SOMNOscreen plus raw recordings (DATEN1.DTX + konfig.dt2).',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('info', help='show recording details and a decoding check')
    p.add_argument('dtx', help='path to DATEN1.DTX')
    p.add_argument('--konfig', help='path to konfig.dt2 (default: next to the DTX file)')
    p.add_argument('--show-patient', action='store_true', help='also print patient details')
    p.set_defaults(func=info)

    p = sub.add_parser('edf', help='convert to EDF')
    p.add_argument('dtx', help='path to DATEN1.DTX')
    p.add_argument('-o', '--output', help='output file (default: DTX name with .edf)')
    p.add_argument('--konfig', help='path to konfig.dt2 (default: next to the DTX file)')
    p.add_argument(
        '--clean-ecg',
        action='store_true',
        help='add an ECG channel with the recorder interference removed (needs scipy)',
    )
    p.add_argument(
        '--include-patient',
        action='store_true',
        help='copy name, sex and birth date into the EDF header (default: anonymous)',
    )
    p.set_defaults(func=edf)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == '__main__':
    sys.exit(main())
