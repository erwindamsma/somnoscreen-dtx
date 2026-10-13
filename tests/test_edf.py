import numpy as np
import pytest

from somnoscreen_dtx import read_dtx, write_edf
from somnoscreen_dtx.cli import main
from synth import make_dtx, make_konfig, make_signals

BLOCKS = 40


@pytest.fixture(scope='module')
def folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp('rec')
    signals, header = make_signals(BLOCKS)
    data, _ = make_dtx(signals, header, BLOCKS)
    (folder / 'DATEN1.DTX').write_bytes(data)
    (folder / 'konfig.dt2').write_bytes(make_konfig())
    return folder


def read_edf(path):
    """Minimal EDF reader for the tests."""
    raw = path.read_bytes()
    ns = int(raw[252:256])
    records = int(raw[236:244])
    h = raw[256 : 256 * (ns + 1)]

    def column(offset, width):
        return [
            h[offset * ns + i * width : offset * ns + (i + 1) * width].decode().strip()
            for i in range(ns)
        ]

    labels = column(0, 16)
    per_record = [int(x) for x in column(16 + 80 + 8 + 8 + 8 + 8 + 8 + 80, 8)]
    data = np.frombuffer(raw[256 * (ns + 1) :], '<i2').reshape(records, sum(per_record))
    signals, start = {}, 0
    for label, n in zip(labels, per_record, strict=True):
        signals[label] = data[:, start : start + n].ravel().astype(np.int64)
        start += n
    return raw[:256], signals


def test_edf_holds_the_decoded_values(folder, tmp_path):
    rec = read_dtx(folder / 'DATEN1.DTX')
    write_edf(rec, tmp_path / 'out.edf')
    head, signals = read_edf(tmp_path / 'out.edf')
    assert head[236:252].split() == [str(BLOCKS).encode(), b'0.25']
    assert head[168:184] == b'01.01.2522.30.00'
    for s in rec.signals.values():
        assert np.array_equal(signals[s.label], s.data.astype(np.int64)), s.label


def test_patient_field_is_anonymous_unless_asked(folder, tmp_path):
    rec = read_dtx(folder / 'DATEN1.DTX')
    write_edf(rec, tmp_path / 'anon.edf')
    write_edf(rec, tmp_path / 'named.edf', include_patient=True)
    assert read_edf(tmp_path / 'anon.edf')[0][8:88].strip() == b'X X X X'
    assert read_edf(tmp_path / 'named.edf')[0][8:88].strip() == b'X M 01-JAN-1980 Test_T.'


def test_clean_ecg_channel(folder, tmp_path):
    pytest.importorskip('scipy')
    rec = read_dtx(folder / 'DATEN1.DTX')
    write_edf(rec, tmp_path / 'ecg.edf', clean_ecg=True)
    _, signals = read_edf(tmp_path / 'ecg.edf')
    assert len(signals['ECG cleaned']) == len(rec.signals['ecg'].data)


def test_cli(folder, tmp_path, capsys):
    assert main(['info', str(folder / 'DATEN1.DTX')]) == 0
    assert '100.000%' in capsys.readouterr().out
    assert main(['edf', str(folder / 'DATEN1.DTX'), '-o', str(tmp_path / 'cli.edf')]) == 0
    assert (tmp_path / 'cli.edf').stat().st_size > 0
