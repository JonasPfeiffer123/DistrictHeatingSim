"""
Shared pytest fixtures for the DistrictHeatingSim domain-core test suite.

These fixtures provide *deterministic* inputs so that golden-master regression
tests (frozen output metrics: Wärmemenge, WGK, CO2, primary energy) are
reproducible across machines and CI runs. Do not introduce randomness here.
"""

# Set non-interactive backend before any matplotlib import so that
# energy_system.py (which does `import matplotlib.pyplot as plt` at module
# level) works in headless CI environments without a display.
import matplotlib
matplotlib.use('Agg')

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope='module')
def time_steps():
    """8760-h datetime64 array for a full simulation year — module-scoped."""
    return pd.date_range(start="2023-01-01", periods=8760, freq="h").to_numpy()


@pytest.fixture(scope='module')
def try_data_stub():
    """Minimal TRY-shaped tuple (5 zero arrays of 8760 h).

    GasBoiler and CHP do not use climate data; this stub satisfies the
    EnergySystem constructor signature without reading files from disk.
    """
    z = np.zeros(8760, dtype=float)
    return (z, z, z, z, z)  # temperature, wind, direct_rad, global_rad, cloud_cover


@pytest.fixture(scope='module')
def cop_data_stub():
    """Minimal COP array stub — not used by GasBoiler or CHP."""
    return np.zeros((2, 2), dtype=float)


@pytest.fixture
def economic_parameters():
    """VDI 2067 economic parameters in the FACTOR convention.

    ``capital_interest_rate`` / ``inflation_rate`` are factors (1 + rate),
    e.g. 1.05 == 5 %. Passing a bare rate (0.05) silently collapses costs to
    ~0 — see ``tests/test_annuity.py`` and BACKLOG C5.
    """
    return {
        "gas_price": 70,            # €/MWh
        "electricity_price": 150,   # €/MWh
        "wood_price": 60,           # €/MWh
        "capital_interest_rate": 1.05,
        "inflation_rate": 1.03,
        "time_period": 20,          # years
        "hourly_rate": 45,          # €/h
        "subsidy_eligibility": "Nein",
    }


@pytest.fixture
def load_profile():
    """Deterministic 8760 h thermal load profile [kW].

    A fixed linear ramp from 50 kW to 400 kW. Chosen over ``np.random`` (which
    the examples use) precisely so the golden-master metrics below are stable.
    """
    return np.linspace(50.0, 400.0, 8760)
