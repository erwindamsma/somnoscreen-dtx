"""Check the built wheel and sdist: only the expected files, no recordings, the right version.

Usage: python tools/check_dist.py DIST_FOLDER [--version X.Y.Z]
"""

import argparse
import os
import re
import sys
import tarfile
import zipfile
from pathlib import Path

PACKAGE = 'somnoscreen_dtx'
FORBIDDEN = re.compile(r'\.(dtx|dt2|edf)$', re.IGNORECASE)

WHEEL_ALLOWED = [
    rf'{PACKAGE}/[a-z_]+\.py',
    rf'{PACKAGE}-[^/]+\.dist-info/(METADATA|WHEEL|RECORD|entry_points\.txt|top_level\.txt)',
    rf'{PACKAGE}-[^/]+\.dist-info/licenses/LICENSE',
]
WHEEL_REQUIRED = [rf'{PACKAGE}-[^/]+\.dist-info/licenses/LICENSE', rf'{PACKAGE}/dtx\.py']

SDIST_ALLOWED = [
    r'PKG-INFO',
    r'pyproject\.toml',
    r'setup\.cfg',
    r'MANIFEST\.in',
    r'README\.md',
    r'FORMAT\.md',
    r'LICENSE',
    rf'src/{PACKAGE}/[a-z_]+\.py',
    rf'src/{PACKAGE}\.egg-info/[A-Za-z_]+\.txt',
    rf'src/{PACKAGE}\.egg-info/PKG-INFO',
    r'tests/[a-z_]+\.py',
]
SDIST_REQUIRED = [r'LICENSE', r'README\.md', r'FORMAT\.md', r'tests/synth\.py']


def check_names(names, allowed, required):
    problems = []
    for name in names:
        if FORBIDDEN.search(name):
            problems.append(f'recording or EDF file: {name}')
        elif not any(re.fullmatch(pattern, name) for pattern in allowed):
            problems.append(f'unexpected file: {name}')
    for pattern in required:
        if not any(re.fullmatch(pattern, name) for name in names):
            problems.append(f'missing: {pattern}')
    return problems


def wheel_names(path):
    with zipfile.ZipFile(path) as wheel:
        return [n for n in wheel.namelist() if not n.endswith('/')]


def sdist_names(path):
    with tarfile.open(path) as sdist:
        names = [m.name for m in sdist.getmembers() if m.isfile()]
    return [n.split('/', 1)[1] for n in names if '/' in n]


def check_dist(folder, version=None):
    folder = Path(folder)
    wheels, sdists = sorted(folder.glob('*.whl')), sorted(folder.glob('*.tar.gz'))
    problems = []
    if len(wheels) != 1 or len(sdists) != 1:
        return [f'expected one wheel and one sdist, found {len(wheels)} and {len(sdists)}']
    problems += [
        f'{wheels[0].name}: {p}'
        for p in check_names(wheel_names(wheels[0]), WHEEL_ALLOWED, WHEEL_REQUIRED)
    ]
    problems += [
        f'{sdists[0].name}: {p}'
        for p in check_names(sdist_names(sdists[0]), SDIST_ALLOWED, SDIST_REQUIRED)
    ]
    if version:
        expected = {f'{PACKAGE}-{version}-py3-none-any.whl', f'{PACKAGE}-{version}.tar.gz'}
        problems += [
            f'{path.name}: not version {version}'
            for path in (wheels[0], sdists[0])
            if path.name not in expected
        ]
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('folder')
    parser.add_argument('--version')
    args = parser.parse_args(argv)
    problems = check_dist(args.folder, args.version)
    prefix = '::error::' if os.environ.get('GITHUB_ACTIONS') else ''
    for problem in problems:
        print(f'{prefix}{problem}')
    if problems:
        return 1
    print(f'{args.folder}: wheel and sdist contain only the expected files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
