## Summary

<!-- What changes and why. Link the issue it resolves, for example "Fixes #12". -->

## How it was tested

<!-- The commands you ran, and for a format change: how the consistency check came out on a real recording. -->

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `pytest` passes, with tests added or updated for the change (format changes through the synthetic encoder in `tests/synth.py`)
- [ ] Package contents checked when packaging changed (`python -m build` and `python tools/check_dist.py dist`)
- [ ] `FORMAT.md` updated when anything new is known about the file format
- [ ] README updated where the change touches it, and `CHANGELOG.md` has an entry under `Unreleased`
- [ ] No recordings, EDF files, patient data, hospital numbers, local paths or user names in code, tests, docs or the pull request
