# pygnss — GNSS utilities and tools

pygnss is a lightweight collection of utilities for GNSS data processing:

- parsers for Hatanaka (CRX) and RINEX formats,
- IONEX (GIM) utilities and exporters,
- small geodetic and ionospheric helpers, and
- a few filtering tools (particle filter, EKF/UKF helpers) used in demos and tests.

This README gives a short overview for users and contributors: installation,
development (building the compiled extension), available CLI scripts and
examples of the most used APIs.

## Installation

Stable release from PyPI (no compiled extension required for pure-Python
features):

```bash
pip install pygnss
```

Developer / editable install (builds the C extension declared in
`pyproject.toml`). This is the recommended setup when working on the
repository locally because some features (Hatanaka/CRX parsing) rely on a
compiled extension for speed.

```bash
# create and activate a venv
python -m venv .venv
source .venv/bin/activate
# install the package and test/dev extras
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

Notes on the compiled extension

- The extension module `pygnss._c_ext` is built from the sources listed in
  `pyproject.toml` (under [[tool.setuptools.ext-modules]]). Building the
  package with `pip install .` or `python -m build` will compile it. On CI
  the workflow provided in `.github/workflows/python-package.yml` creates a
  virtualenv and runs `pip install -e '.[test]'` to ensure the entry points
  and compiled modules are available for tests.

## CLI entry points (installed as console scripts)

The package declares several console scripts (see `pyproject.toml`):

- `ionex_diff`  — compare IONEX files or compare an IONEX to NeQuick output
- `compute_cdf` — utility to compute CDF from data (used by examples)
- `rinex_from_file`, `rinex_to_parquet`, `merge_rinex_nav` — helpers for
  RINEX conversions

After installing the package into a venv these commands are available on
`$PATH` (from `.venv/bin`). Tests rely on the entry points being discoverable
via PATH in CI, so the workflow prepends `.venv/bin` to PATH before running
tests.

## Quick usage examples

1. Hatanaka (CRX) -> pandas DataFrame

```python
from pygnss import hatanaka

df = hatanaka.to_dataframe('station.crx.gz', station='MYST')
print(df.head())
```

If the compiled extension is not available the function raises an ImportError
with instructions to build/install the package (see "Developer" section).

1. Read and diff IONEX maps (programmatic)

```python
from pygnss import ionex
from pygnss.iono import gim

# load an ionex and collect VTEC maps
handler = gim.GimHandlerArray()
ionex.load('sample.ionex', gim_handler=handler)
print(len(handler.vtec_gims))
```

## Running tests locally

With the venv active and the test extras installed the canonical way to run
the test-suite is:

```bash
# inside the project root with .venv activated
python -m pytest -v
```

If tests call console scripts (such as `ionex_diff`) the venv `bin` directory
must be on `PATH` so subprocesses can find the entry points. The CI workflow
prepares the environment accordingly.

## Where to look next

- `pygnss/hatanaka.py` — Hatanaka/CRX parsing wrapper (uses compiled helper)
- `pygnss/ionex.py`    — IONEX loader/writer and CLI glue
- `pygnss/filter/`     — particle filter, EKF/UKF helpers and demos
