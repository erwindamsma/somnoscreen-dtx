# The SOMNOscreen plus DTX format

This describes the raw recording files of a SOMNOmedics SOMNOscreen plus as far as they have
been worked out. There is no public specification; everything below comes from analysing a
recording, and every claim is checked by the decoder itself (see [Consistency check](#consistency-check)).

A recording consists of two files:

- `DATEN1.DTX`: the signal data
- `konfig.dt2`: patient details, the channel list and the sampling rates

All multi-byte integers are big-endian.

**Scope.** One recording has been examined: a home polygraphy (PG) montage with 12 channels.
Other montages, for example a polysomnography with EEG, will have the same block structure
but almost certainly a different slot layout. See [Other montages](#other-montages).

## DATEN1.DTX

```
offset 0     121 bytes    zero (as observed)
offset 121   18 bytes     initial ADPCM state of the six tail channels
offset 139   154 bytes    block 0
             154 bytes    block 1
             ...
             < 154 bytes  optional truncated final block
```

Each block covers **0.25 s**. A recording can end in the middle of a block; the bytes that
are present still contain a valid header.

### Block layout

| Offset | Size | Content |
|---|---|---|
| 0 | 15 | header |
| 15 | 121 | 242 ADPCM codes of 4 bits, high nibble first; 241 used, the last is 0 |
| 136 | 18 | tail: ADPCM state of six channels after this block |

### Header

| Offset | Size | Content |
|---|---|---|
| 0 | 2 | body position code (see below) |
| 2 | 2 | 0 in all blocks examined |
| 4 | 1 | light sensor, relative units |
| 5 | 1 | unknown, mostly 0 |
| 6 | 2 | battery voltage, mV |
| 8 | 2 | pleth ADPCM predictor at the start of the block (0..255) |
| 10 | 1 | pleth ADPCM step index at the start of the block |
| 11 | 1 | pulse rate, bpm |
| 12 | 1 | 0 in all blocks examined |
| 13 | 1 | SpO2, %. 0 = no sensor, 127 = no valid reading |
| 14 | 1 | 0 in all blocks examined |

The header fields are therefore sampled at 4 Hz.

Body position codes, confirmed against the manufacturer's report for the same recording:

| Code | Position |
|---|---|
| 0 | prone |
| 600 | upright |
| 1300 | left |
| 2000 | right |
| 2500 | upside down |
| 3000 | supine |

The position sensor sits in the recorder, so a recorder lying flat on a table reads as
supine.

### ADPCM

All waveforms are stored as standard IMA/DVI ADPCM:

- 4-bit codes: bit 3 is the sign, bits 2..0 the magnitude
- the standard 89-entry step table and index adjustment table (-1, -1, -1, -1, 2, 4, 6, 8)
- reconstruction: `diff = step >> 3`, plus `step` for bit 2, `step >> 1` for bit 1,
  `step >> 2` for bit 0; subtract for a negative sign
- the predictor is clamped to 16 bits signed, except pleth: 0..255

### Slot layout and sampling rates

The codes are interleaved in frames of 31 slots. One frame covers 1/32 s:

```
slot   0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30
       E  P  S  E  P  S  L  E  P  S  E  P  S  L  E  P  S  E  P  S  L  E  P  S  T  E  P  A  S  X  L

E = ECG-AUX (256 Hz)    P = Flow Pr, pressure flow (256 Hz)    S = Snore (256 Hz)
L = Pleth (128 Hz)      T = Flow Th, thermistor (32 Hz)
A = Abdomen (32 Hz)     X = Thorax (32 Hz)
```

A block holds 8 frames, which would be 248 slots. Only 241 are stored: the last 7 slots
(24..30 of the eighth frame) hold the final sample of each of the 7 channels, and for those
the block stores a **state** instead of a code:

- the six channels in the tail store their state after the final sample: the final sample
  *is* the tail predictor
- pleth stores its state in the header of the *next* block

Per block this gives 64 samples for each 256 Hz channel, 32 for pleth and 8 for each 32 Hz
channel.

### Tail

Six times 3 bytes: a 16-bit signed predictor and an 8-bit step index, in this order:

```
Flow Th, ECG-AUX, Flow Pr, Abdomen, Snore, Thorax
```

This is also the order of these channels in `konfig.dt2`.

To decode block *n*, start each channel from the tail of block *n*−1 (for block 0: the
initial states at offset 121), apply the stored codes, and take the tail predictor of block
*n* as the final sample. Pleth starts from the header of block *n* and takes the header
predictor of block *n*+1 as its final sample.

### Consistency check

Because each block stores the state after its final sample, the decoder can verify itself:
after applying a block's stored codes, exactly one more code must lead to the stored state.
`somnoscreen-dtx info` reports, per channel, the share of blocks for which this holds.

In the recording examined this held for 99.999% of the blocks for the six tail channels and
99.96% for pleth. The exceptions were three blocks at the very end, after the sensors had
been disconnected, and pleth blocks mostly from periods when the finger sensor was not
attached. A wrong slot layout
breaks the check for nearly every block.

### Timing

The recording starts at the programming time stored in `konfig.dt2`, which has minute
resolution, and runs without gaps at 4 blocks per second. Start and end time were confirmed
against the manufacturer's report for the same recording.

## konfig.dt2

2048 bytes. Text fields are zero-terminated Latin-1. Known fields:

| Offset | Content |
|---|---|
| 0x09 | surname |
| 0x1E | initials |
| 0x33 | recording date, `ddmmyyyy` |
| 0x3C | birth date, `ddmmyyyy` |
| 0x45 | height, cm |
| 0x49 | weight, kg |
| 0x4D | sex |
| 0x54 | a date in `mm/dd/yy` format, possibly firmware |
| 0xAB | a short alphanumeric code, possibly the device ID |
| 0xB4 | programming time: day, month, hour, minute (1 byte each) |
| 0xE6, 0x3C0, 0x708, 0x728 | order and patient numbers from the hospital system |
| 0x15D | device log: entries of 5 bytes (code, day, month, hour, minute); code 8 appears to mean programmed, 12 read out |
| 0x258 | 32 entries of 10 bytes for channels 1..32 (`C:1` .. `C:32`, unused in a PG montage) |
| 0x400 | channels 33..64: samples per 0.25-s block (32 bytes) |
| 0x420 | channels 33..64: divider from a 256 Hz base clock (32 bytes) |
| 0x44C | channels 33..64: 10-byte entries, 8-byte name plus a 16-bit value |

The 16-bit value after each channel name is `0xFFFF` for most waveforms, `0xBFFF` for Snore,
`0x03FF` for Light, `0x00FF` for Pleth and 2 or 3 for the header channels. It looks like a value
mask or type code; its exact meaning is unknown.

Unused channels are named `C:nn` and have zero rates. The active channels of the PG montage:

| Channel | Name | Samples per block | Divider | Rate |
|---|---|---|---|---|
| 37 | Flow Th | 8 | 8 | 32 Hz |
| 39 | ECG-AUX | 64 | 1 | 256 Hz |
| 43 | Flow Pr | 64 | 1 | 256 Hz |
| 45 | Abdomen | 8 | 8 | 32 Hz |
| 47 | Snore | 64 | 1 | 256 Hz |
| 48 | Thorax | 8 | 8 | 32 Hz |
| 50 | Pos. | 8 | 64 | 4 Hz stored |
| 54 | Light | 8 | 64 | 4 Hz stored |
| 55 | Battery | 8 | 64 | 4 Hz stored |
| 58 | Pleth | 32 | 2 | 128 Hz |
| 59 | Pulse | 1 | 64 | 4 Hz |
| 60 | SPO2 | 1 | 64 | 4 Hz |

**No calibration.** Neither file contains gains, offsets or physical units. The waveforms
are in device units; SpO2, pulse, battery and position are in real units. The scaling to
physical units lives in the manufacturer's analysis software.

## Known quirks

- **ECG interference.** In the recording examined the ECG-AUX channel carries a strong
  37.5 Hz periodic interference. Its harmonics alias across the whole 0–128 Hz band. There is
  also an intermittent narrow spike every 6 s. Both are locked to the sample clock and repeat
  exactly every 512 and 1536 samples, so subtracting a running median template removes them
  (`--clean-ecg`). Whether every recorder does this is unknown.
- **Snore channel.** A sensitive sensor that also picks up heartbeats and body sounds; snoring
  shows as bursts above 20 Hz during inspiration.
- **Saturation.** The effort belts often reach the 16-bit limits during deep breathing.

## Other montages

The rate tables in `konfig.dt2` describe each channel, so other montages can probably be
decoded with the same block structure once their slot layout is known. The decoder refuses a
`konfig.dt2` it does not recognise rather than guessing. A sample recording, with the
patient fields blanked, would allow adding another montage: the consistency check shows
immediately whether a candidate layout is right.
