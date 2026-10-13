"""Removal of the recorder's own interference from the ECG-AUX channel (needs scipy).

In the recordings examined the ECG carries a 37.5 Hz periodic interference whose harmonics
alias across the whole 0-128 Hz band, plus an intermittent spike every 6 s. Both are locked
to the sample clock, so they repeat exactly every 512 and 1536 samples and can be removed by
subtracting a running median template instead of notch filtering.
"""
import numpy as np


def _remove_periodic(x, period, epochs):
    from scipy import ndimage
    n = len(x) // period
    e = x[:n * period].reshape(n, period)
    y = (e - ndimage.median_filter(e, size=(epochs, 1), mode='nearest')).ravel()
    rest = x[n * period:]
    return np.r_[y, rest - np.median(rest)] if len(rest) else y


def clean_ecg(ecg, rate=256, band=(0.5, 40)):
    """Return the ECG without the clock-locked interference, band-pass filtered, as float32.

    Polarity is left as recorded; it depends on where the electrodes were placed.
    """
    from scipy import signal
    y = _remove_periodic(np.asarray(ecg, dtype=np.float32), 512, 31)
    y = _remove_periodic(y, 1536, 31)
    sos = signal.butter(2, band, btype='band', fs=rate, output='sos')
    return signal.sosfiltfilt(sos, y).astype(np.float32)
