import datetime as dt

import numpy as np
import pytest

from somnoscreen_dtx import UnsupportedMontage, read_dtx, read_konfig
from somnoscreen_dtx.dtx import PG12
from synth import make_dtx, make_konfig, make_signals

BLOCKS = 40


@pytest.fixture(scope='module')
def recording(tmp_path_factory):
    folder = tmp_path_factory.mktemp('rec')
    signals, header = make_signals(BLOCKS)
    data, recon = make_dtx(signals, header, BLOCKS)
    (folder / 'DATEN1.DTX').write_bytes(data)
    (folder / 'konfig.dt2').write_bytes(make_konfig())
    return folder, signals, header, recon


def test_waveforms_decode_exactly(recording):
    folder, _, _, recon = recording
    rec = read_dtx(folder / 'DATEN1.DTX')
    for role, expected in recon.items():
        assert np.array_equal(rec.signals[role].data.astype(np.int64), expected), role


def test_every_block_lines_up_with_the_stored_state(recording):
    rec = read_dtx(recording[0] / 'DATEN1.DTX')
    assert rec.consistency == dict.fromkeys(rec.consistency, 1.0)


def test_reconstruction_follows_the_input(recording):
    _, signals, _, recon = recording
    for role, x in signals.items():
        error = np.abs(recon[role] - x)
        assert np.median(error) < 0.05 * np.ptp(x), role


def test_rates_and_lengths(recording):
    rec = read_dtx(recording[0] / 'DATEN1.DTX')
    assert rec.blocks == BLOCKS and rec.trailing_bytes == 150
    for role, rate in PG12.rates.items():
        assert rec.signals[role].rate == rate
        assert len(rec.signals[role].data) == BLOCKS * rate // 4


def test_header_fields(recording):
    _, _, header, _ = recording
    rec = read_dtx(recording[0] / 'DATEN1.DTX')
    for role, values in header.items():
        assert np.array_equal(rec.signals[role].data, values), role


def test_labels_and_start_come_from_konfig(recording):
    rec = read_dtx(recording[0] / 'DATEN1.DTX')
    assert rec.signals['ecg'].label == 'ECG-AUX'
    assert rec.signals['spo2'].label == 'SPO2'
    assert rec.start == dt.datetime(2025, 1, 1, 22, 30)


def test_konfig_fields(recording):
    k = read_konfig(recording[0] / 'konfig.dt2')
    assert (k.surname, k.initials, k.sex, k.height_cm, k.weight_kg) == ('Test', 'T.', 'M', 180, 80)
    assert [c.samples_per_block for c in k.channels] == list(PG12.signature)
    assert [c.number for c in k.channels][:2] == [37, 39]
    assert k.log == [(8, 1, 1, 22, 30)]


def test_without_konfig_assumes_pg12(recording, tmp_path):
    (tmp_path / 'DATEN1.DTX').write_bytes((recording[0] / 'DATEN1.DTX').read_bytes())
    with pytest.warns(UserWarning):
        rec = read_dtx(tmp_path / 'DATEN1.DTX')
    assert rec.start is None
    assert np.array_equal(rec.signals['ecg'].data.astype(np.int64), recording[3]['ecg'])


def test_unknown_montage_is_refused(recording, tmp_path):
    (tmp_path / 'DATEN1.DTX').write_bytes((recording[0] / 'DATEN1.DTX').read_bytes())
    signature = list(PG12.signature)
    signature[1] = 32
    (tmp_path / 'konfig.dt2').write_bytes(make_konfig(signature))
    with pytest.raises(UnsupportedMontage):
        read_dtx(tmp_path / 'DATEN1.DTX')


def test_without_trailing_block_the_last_pleth_sample_repeats(tmp_path):
    signals, header = make_signals(BLOCKS)
    data, recon = make_dtx(signals, header, BLOCKS, truncated=0)
    (tmp_path / 'DATEN1.DTX').write_bytes(data)
    (tmp_path / 'konfig.dt2').write_bytes(make_konfig())
    rec = read_dtx(tmp_path / 'DATEN1.DTX')
    pleth = rec.signals['pleth'].data.astype(np.int64)
    assert np.array_equal(pleth[:-1], recon['pleth'][:-1])
    assert pleth[-1] == pleth[-2]
    assert rec.consistency['pleth'] == 1.0
