"""Tests for the energy-system calculation worker isolation (BACKLOG C1).

The worker now computes on a *deep copy* and returns it (the main thread swaps it
in), so the UI's shared `energy_system` is never mutated mid-run — closing the
read/write race. `run_energy_system_calculation` is the GUI-free seam; the QThread
is a thin wrapper around it.
"""

import numpy as np
import pandas as pd

from districtheatingsim.gui.EnergySystemTab._06_calculate_energy_system_thread import (
    run_energy_system_calculation,
)
from districtheatingsim.heat_generators.chp import CHP
from districtheatingsim.heat_generators.energy_system import EnergySystem
from districtheatingsim.heat_generators.gas_boiler import GasBoiler

_ECON = {
    "gas_price": 70,
    "electricity_price": 150,
    "wood_price": 60,
    "capital_interest_rate": 1.05,
    "inflation_rate": 1.03,
    "time_period": 20,
    "hourly_rate": 45,
    "subsidy_eligibility": "Nein",
}


def _system():
    ts = pd.date_range("2023-01-01", periods=8760, freq="h").to_numpy()
    load = np.linspace(50.0, 400.0, 8760)
    es = EnergySystem(
        ts,
        load,
        np.full(8760, 85.0),
        np.full(8760, 50.0),
        tuple(np.zeros(8760) for _ in range(5)),
        np.zeros((2, 2)),
        _ECON,
    )
    es.add_technology(CHP(name="BHKW_1", th_Leistung_kW=100))
    es.add_technology(GasBoiler("Gaskessel_1", thermal_capacity_kW=500))
    return es


class TestWorkerIsolation:
    def test_computes_on_a_copy_leaving_input_untouched(self):
        es = _system()
        assert es.results == {}  # not yet computed

        result = run_energy_system_calculation(es, optimize=False, weights=None)

        assert len(result) == 1
        assert result[0] is not es  # a deep copy, not the shared object
        assert result[0].technologies is not es.technologies
        assert result[0].results != {}  # the copy was computed
        assert es.results == {}  # input NOT mutated (the C1 race)

    def test_repeated_calls_do_not_accumulate_on_input(self):
        es = _system()
        run_energy_system_calculation(es, optimize=False, weights=None)
        run_energy_system_calculation(es, optimize=False, weights=None)
        # Each run is independent of the input; nothing leaks back onto it.
        assert es.results == {}
        assert len(es.technologies) == 2
