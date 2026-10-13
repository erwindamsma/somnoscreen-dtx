# Security policy

## Supported versions

Security fixes go into the latest release. Older releases get no separate fixes; update to the latest release.

## Reporting a vulnerability

Report vulnerabilities privately through a GitHub security advisory:
https://github.com/erwindamsma/somnoscreen-dtx/security/advisories/new
(on the repository page: Security > Report a vulnerability).

Please do not open a public issue or pull request for a vulnerability, and do not include exploit details in one. Never attach a recording or an EDF file to a report: they contain health data and personal details. Describe the file instead, or build one with the synthetic encoder in `tests/synth.py`.

A useful report contains:

- the version (`somnoscreen-dtx --version`), the Python version and the operating system;
- what an attacker can achieve, and what they need for it (for example a crafted file the victim converts);
- the steps to reproduce.

The report stays private until a fix is released. Reports are handled on a best-effort basis by the maintainer, and reporters are credited in the advisory unless they prefer not to be.

## What counts as a vulnerability

The tool reads files that may come from anyone. In scope, for example:

- a crafted `DATEN1.DTX` or `konfig.dt2` that makes the tool write outside the output file it was given, or execute code;
- a crafted file that makes the tool hang, or use memory far out of proportion to the file's size;
- patient data from `konfig.dt2` (name, birth date, hospital numbers) that ends up in the EDF header or in the `info` output without `--include-patient` or `--show-patient`.

Not in scope:

- a file that decodes to wrong values, or is refused: that is a bug, report it as an issue;
- the medical meaning of a recording: the tool does not interpret recordings and is not a medical device.
