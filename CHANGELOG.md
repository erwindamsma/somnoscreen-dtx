# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).
The release workflow publishes the section whose heading matches the tag (`## [1.2.3]`) as the GitHub release notes, so use absolute links in this file.

## [Unreleased]

### Added

- Decoder for `DATEN1.DTX` and reader for `konfig.dt2` of a SOMNOscreen plus recording with the 12-channel PG montage: thermistor and pressure flow, thorax and abdomen belts, snore, ECG-AUX, pleth, SpO2, pulse, body position, light and battery, at their native rates (256, 128, 32 and 4 Hz).
- A decoding check per channel: the share of blocks whose decoded data ends exactly on the ADPCM state the recorder stored.
- EDF export with one 0.25-second data record per DTX block and the device values unchanged. The patient field is anonymous unless `--include-patient` is given.
- `--clean-ecg`: an extra ECG channel without the recorder's own 37.5 Hz interference and 6-second spikes.
- Command-line tool `somnoscreen-dtx` with `info` and `edf`.
- [FORMAT.md](https://github.com/erwindamsma/somnoscreen-dtx/blob/main/FORMAT.md), a description of the file format.
- A configuration in `konfig.dt2` other than the known montage is refused instead of decoded wrongly.
