import numpy as np
import pytest

pytest.importorskip('scipy')

from somnoscreen_dtx.ecg import clean_ecg  # noqa: E402


def power_at(x, freq, rate=256):
    spectrum = np.abs(np.fft.rfft(x)) ** 2
    return spectrum[int(round(freq * len(x) / rate))]


def test_clock_locked_interference_is_removed():
    rate, seconds = 256, 600
    t = np.arange(rate * seconds) / rate
    rng = np.random.default_rng(1)
    beats = np.zeros_like(t)
    beat_times = np.cumsum(rng.uniform(0.8, 1.0, int(seconds / 0.8)))
    beats[(beat_times[beat_times < seconds - 1] * rate).astype(int)] = 1
    ecg = np.convolve(beats, np.hanning(12) * 3000, mode='same')
    # 37.5 Hz with harmonics; above 128 Hz they alias, but stay periodic in 512 samples
    interference = sum(8000 / k * np.sin(2 * np.pi * 37.5 * k * t + k) for k in range(1, 8))
    cleaned = clean_ecg(ecg + interference)
    assert power_at(cleaned, 37.5) < 1e-3 * power_at(ecg + interference, 37.5)
    assert np.corrcoef(cleaned, clean_ecg(ecg))[0, 1] > 0.95
