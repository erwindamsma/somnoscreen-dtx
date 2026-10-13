import io
import tarfile
import zipfile

import pytest

from check_dist import check_dist

GOOD_WHEEL = [
    'somnoscreen_dtx/__init__.py',
    'somnoscreen_dtx/dtx.py',
    'somnoscreen_dtx-0.1.0.dist-info/METADATA',
    'somnoscreen_dtx-0.1.0.dist-info/WHEEL',
    'somnoscreen_dtx-0.1.0.dist-info/RECORD',
    'somnoscreen_dtx-0.1.0.dist-info/licenses/LICENSE',
]
GOOD_SDIST = [
    'PKG-INFO',
    'pyproject.toml',
    'README.md',
    'FORMAT.md',
    'LICENSE',
    'src/somnoscreen_dtx/dtx.py',
    'src/somnoscreen_dtx.egg-info/SOURCES.txt',
    'tests/synth.py',
    'tests/test_dtx.py',
]


def build(folder, wheel=GOOD_WHEEL, sdist=GOOD_SDIST, version='0.1.0'):
    with zipfile.ZipFile(folder / f'somnoscreen_dtx-{version}-py3-none-any.whl', 'w') as z:
        for name in wheel:
            z.writestr(name, 'x')
    with tarfile.open(folder / f'somnoscreen_dtx-{version}.tar.gz', 'w:gz') as t:
        for name in sdist:
            info = tarfile.TarInfo(f'somnoscreen_dtx-{version}/{name}')
            info.size = 1
            t.addfile(info, io.BytesIO(b'x'))
    return folder


def test_expected_contents_pass(tmp_path):
    assert check_dist(build(tmp_path), '0.1.0') == []


@pytest.mark.parametrize(
    ('wheel', 'sdist', 'problem'),
    [
        ([*GOOD_WHEEL, 'somnoscreen_dtx/DATEN1.DTX'], GOOD_SDIST, 'recording'),
        (GOOD_WHEEL, [*GOOD_SDIST, 'tests/konfig.dt2'], 'recording'),
        (GOOD_WHEEL, [*GOOD_SDIST, 'tests/sample.EDF'], 'recording'),
        ([*GOOD_WHEEL, 'somnoscreen_dtx/data.json'], GOOD_SDIST, 'unexpected'),
        (GOOD_WHEEL[:-1], GOOD_SDIST, 'missing'),
        (GOOD_WHEEL, [n for n in GOOD_SDIST if n != 'FORMAT.md'], 'missing'),
    ],
)
def test_leaks_and_gaps_fail(tmp_path, wheel, sdist, problem):
    problems = check_dist(build(tmp_path, wheel, sdist))
    assert any(problem in p for p in problems)


def test_wrong_version_fails(tmp_path):
    assert any('not version' in p for p in check_dist(build(tmp_path), '0.2.0'))
