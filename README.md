# somnoscreen-dtx

[![CI](https://github.com/erwindamsma/somnoscreen-dtx/actions/workflows/ci.yml/badge.svg)](https://github.com/erwindamsma/somnoscreen-dtx/actions/workflows/ci.yml)
[![Python 3.10–3.14](https://img.shields.io/badge/python-3.10%E2%80%933.14-3776AB)](pyproject.toml)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-8AB803)](LICENSE)

Read the raw recordings of a **SOMNOmedics SOMNOscreen plus** sleep recorder
(`DATEN1.DTX` + `konfig.dt2`) and convert them to EDF, so they open in EDFbrowser, MNE,
or any other tool that reads EDF.

The file format is not publicly documented. It was worked out from a recording and is
described in [FORMAT.md](FORMAT.md). In short: 0.25-second blocks of 4-bit IMA ADPCM, with
the ADPCM state stored after every block, which lets the decoder verify its own output.

The story behind it:
[Reading my sleep study before the hospital did](https://damsma.dev/notes/reading-my-sleep-study/).

> **Not a medical device.** This is an independent project, not affiliated with or endorsed
> by SOMNOmedics. It reads files; it does not score or interpret them. Do not use it for
> diagnosis.

## Install

```
pip install "somnoscreen-dtx[ecg] @ git+https://github.com/erwindamsma/somnoscreen-dtx"
```

Requires Python 3.10+ and numpy. The `ecg` extra adds scipy, needed only for `--clean-ecg`.

## Use

Put `DATEN1.DTX` and `konfig.dt2` in one folder.

```
somnoscreen-dtx info DATEN1.DTX
somnoscreen-dtx edf DATEN1.DTX -o recording.edf
```

`info` prints the start time, duration, channels and a decoding check per channel; add
`--show-patient` to include the patient details from `konfig.dt2`. Example output:

```
Montage:   PG, 12 channels (thermistor + pressure flow)
Start:     2025-01-01 22:30:00
Duration:  9:12:01 (132484 blocks of 0.25 s, 150 trailing bytes)

Channel              Rate  Check
Flow Th             32 Hz  99.999%
ECG-AUX            256 Hz  99.999%
...
```

The check is the share of blocks whose decoded data ends exactly on the state the recorder
stored. Values close to 100% mean the file was decoded correctly.

`edf` options:

| Option | Effect |
|---|---|
| `-o FILE` | output file (default: the DTX name with `.edf`) |
| `--konfig FILE` | `konfig.dt2` elsewhere than next to the DTX file |
| `--clean-ecg` | add an `ECG cleaned` channel without the recorder's own interference (see below) |
| `--include-patient` | copy name, sex and birth date into the EDF header; anonymous by default |

From Python:

```python
from somnoscreen_dtx import read_dtx, write_edf

rec = read_dtx('DATEN1.DTX')  # finds konfig.dt2 next to it
spo2 = rec.signals['spo2']  # Signal(label, rate, data, unit)
print(rec.start, rec.duration, spo2.rate, spo2.data[:8])
write_edf(rec, 'recording.edf')
```

Signal keys: `flow_th`, `ecg`, `flow_pr`, `abdomen`, `snore`, `thorax`, `pleth`
(waveforms) and `position`, `light`, `battery`, `pulse`, `spo2`, `header_byte5`
(4 Hz header fields). `somnoscreen_dtx.POSITIONS` maps position codes to names.

## The EDF file

- One data record per DTX block (0.25 s), so record *n* is block *n*.
- Values are exactly as decoded: physical = digital. The recording holds no calibration, so
  waveforms are in device units; SpO2 (%), pulse (bpm), battery (mV) and position codes are
  real values.
- Channel names come from `konfig.dt2`.
- The patient field is `X X X X` unless `--include-patient` is given.

## Status

| | |
|---|---|
| **Confirmed** | 12-channel PG montage: every waveform decodes onto the recorder's stored states (99.999% of blocks); start time, end time and body position codes match the manufacturer's report for the same recording |
| **Confirmed** | EDF output reads back identically with an independent EDF reader |
| **Untested** | other montages (e.g. polysomnography with EEG), other firmware versions, other SOMNOmedics recorders |

## Limitations

- **One montage.** Only the 12-channel PG montage (thermistor and pressure flow, effort
  belts, snore, ECG-AUX, oximetry, position) has been seen. A different `konfig.dt2` is
  refused rather than decoded wrongly. Open a
  [Recording not supported](https://github.com/erwindamsma/somnoscreen-dtx/issues/new?template=unsupported_recording.yml)
  issue to get another montage added; never attach the recording itself.
- **No calibration**, see above.
- **ECG interference.** In the recording examined, the recorder's own 37.5 Hz interference
  swamped the ECG. `--clean-ecg` removes it; the raw channel stays untouched.
- **Start time** has minute resolution: `konfig.dt2` stores the programming time without
  seconds.

## Tests

```
pip install -e ".[dev]"
pytest
```

The tests build synthetic recordings with an encoder that mirrors the recorder, decode them
and check every sample. No real recording is included.

## Contributing and support

- Questions, bugs and feature requests: [issues](https://github.com/erwindamsma/somnoscreen-dtx/issues/new/choose).
- How to propose a change, the checks to run and how to add a montage: [CONTRIBUTING.md](CONTRIBUTING.md).
- Security issues are reported privately: [SECURITY.md](SECURITY.md).
- What changed per version: [CHANGELOG.md](CHANGELOG.md).

Never attach a recording or an EDF file to an issue or a pull request: they contain health
data and personal details.

## Licence

[MIT](LICENSE)
