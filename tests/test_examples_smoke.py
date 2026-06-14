"""Smoke tests for the ``examples/`` scripts.

``examples/`` are the author's de-facto manual tests; nothing guarded them
against API drift, so they rot silently (e.g. the pandapipes 0.13 -> 0.14
migration, or the ``→`` print that crashed under the Windows cp1252 console).

These tests run the GUI-free / network-free examples end-to-end as subprocesses
and assert they exit cleanly. They do **not** pin output values (several examples
use ``np.random``); they only catch crashes and import/API breakage.

Run with ``-m 'not slow'`` to skip the pandapipes examples (numba cold-start).
Examples needing a display (Qt), live downloads (osmnx/Overpass/geocoding) or an
external absolute path are intentionally excluded.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_EXAMPLES = _REPO / "examples"
_DATA = _EXAMPLES / "data"

# Examples are run from the repo root and use UTF-8 so German/symbol prints do
# not crash on a cp1252 console; Agg + offscreen keep them headless.
_ENV = {
    **os.environ,
    "PYTHONIOENCODING": "utf-8",
    "MPLBACKEND": "Agg",
    "QT_QPA_PLATFORM": "offscreen",
}

# Fast, deterministic-enough domain examples — part of the default suite.
_FAST = [
    "03_example_simple_heat_requirement",
    "03b_example_bdew_subtype_comparison",
    "09_example_heat_generators",
    "10_example_heat_generation_optimization",
    "14_example_photovoltaics",
    "15_example_annuity",
    "17_energy_system_seasonal_storage",
    "18_chp_pufferspeicher",
    "BHKW_Speicher",
]

# pandapipes examples — slow (numba cold-start + a real pipeflow), ~15-25 s each.
# 08_example_complex_pandapipes_timeseries is deliberately excluded: its full
# 100-iteration bidirectional time series runs for several minutes — too slow for
# CI. It is covered manually / by tests/test_simulation_golden_master.py instead.
_SLOW = [
    "06_example_simple_pandapipes",
    "07_example_timeseries_pandapipes",
]

pytestmark = pytest.mark.skipif(
    not _DATA.exists(),
    reason="examples/data not present in this checkout",
)


def _run_example(name: str, timeout: int) -> None:
    script = _EXAMPLES / f"{name}.py"
    if not script.exists():
        pytest.skip(f"{script} not present")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_REPO),  # examples use paths relative to the repo root
        env=_ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode != 0:
        tail = "\n".join((result.stderr or "").splitlines()[-15:])
        pytest.fail(f"{name} exited {result.returncode}\n--- stderr tail ---\n{tail}")


@pytest.mark.parametrize("name", _FAST)
def test_example_runs(name):
    _run_example(name, timeout=240)


@pytest.mark.slow
@pytest.mark.parametrize("name", _SLOW)
def test_pandapipes_example_runs(name):
    _run_example(name, timeout=360)
