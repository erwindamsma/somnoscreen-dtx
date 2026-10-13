# Contributing

Contributions are welcome: bug reports, knowledge about the file format, documentation fixes, tests and code.

## Proposing a change

- For a bug, open an issue with the bug template first, unless the fix is small and obvious. For a new feature or a behaviour change, open an issue before writing code, so the approach can be agreed before you spend time on it.
- A recording that is refused or decodes badly gets the "Recording not supported" template.
- Fork the repository, branch from `main`, and keep one topic per pull request.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`).
- Fill in the pull request template. CI runs the linter, the tests on Linux, Windows and macOS, and the package inspection on every pull request.

## Never commit recordings

Recordings and EDF files contain health data, and `konfig.dt2` holds the patient's name, birth date and hospital numbers. They never go into the repository, an issue or a pull request, not even "anonymised": `.gitignore` blocks `*.DTX`, `*.dt2` and `*.edf`, and the package inspection fails on them. Tests use synthetic recordings from `tests/synth.py` instead, an encoder that writes files the way the recorder does.

Samples in code and docs stay neutral: no real patient data, hospital or order numbers, device IDs, local paths or user names.

## Toolchain

Python 3.10 or later.

```
pip install -e ".[dev]"
```

## Checks to run

| What changed | Run before opening the pull request |
|---|---|
| Anything | `ruff check .`, `ruff format --check .` and `pytest` |
| Decoding or the format | The tests, plus `somnoscreen-dtx info` on a real recording: the check column must stay at or near 100% |
| Packaging (`pyproject.toml`, `MANIFEST.in`) | `python -m build`, `twine check --strict dist/*` and `python tools/check_dist.py dist` |

`tools/check_dist.py` accepts only an allowlist of files in the wheel and the sdist, fails on any recording or EDF file, and checks the version when `--version` is given. `tests/test_check_dist.py` makes sure it keeps catching leaks.

## Adding a montage

A montage is the channel configuration of a recording. Only the 12-channel PG montage is known (`PG12` in `src/somnoscreen_dtx/dtx.py`). To add one:

1. Get a sample recording privately, with the patient fields of `konfig.dt2` blanked.
2. Read the channel table and the rate tables with `read_konfig`. They give the channels, their order and their samples per block.
3. Work out the slot layout of the frame. The decoding check shows immediately whether a candidate is right: a wrong layout fails for nearly every block.
4. Add a `Montage` to `MONTAGES`, extend `tests/synth.py` to encode it, and add tests.
5. Describe it in `FORMAT.md` and add an entry to `CHANGELOG.md`.

## Keeping the docs in sync

| Change | Update |
|---|---|
| Anything new about the file format | `FORMAT.md` |
| A behaviour users can see | The README and an entry under `Unreleased` in `CHANGELOG.md` |
| A new montage or a lifted limitation | The Status and Limitations sections of the README |

`CHANGELOG.md` becomes the GitHub release notes, so it uses absolute links. The README and `FORMAT.md` use relative links.

## Publishing (maintainers)

The first time:

1. Make the repository public, with `main` as the default branch.
2. Right after that, enable Private vulnerability reporting (Settings > Advanced Security): it is the only reporting channel [SECURITY.md](SECURITY.md) offers, and GitHub leaves it off by default.
3. Add the rulesets: `main` only through pull requests, squash merges only, with the `CI result` check required; tags `v*` cannot be moved or deleted.

Every release:

1. Open a release pull request with one commit, `chore: release <version>`, that sets `__version__` in `src/somnoscreen_dtx/__init__.py`, renames `## [Unreleased]` in `CHANGELOG.md` to `## [<version>] - <date>` and adds an empty `## [Unreleased]` above it.
2. Squash-merge it, update your local `main`, wait for CI to pass on the squash commit, and only then push an annotated tag `v<version>` on it. A prerelease uses a PEP 440 version, for example `v0.2.0rc1`.
3. `release.yml` tests and builds the tag again, checks that the tag matches `__version__` and that `CHANGELOG.md` has a section for it, and creates the GitHub release with the wheel and the sdist.

Publishing to PyPI is off. To switch it on: create a PyPI trusted publisher for this repository, workflow `release.yml` and environment `pypi`; add the environment `pypi` with a required reviewer; then set the repository variable `PUBLISH_TO_PYPI` to `true`. A package name on PyPI is effectively permanent.
