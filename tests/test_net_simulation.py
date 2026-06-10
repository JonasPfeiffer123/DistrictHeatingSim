"""
Unit tests for pandapipes simulation-result validation (BACKLOG C2).

`validate_simulation_results` is the GUI-free, numpy-only guard wired into
`thermohydraulic_time_series_net` to turn a non-converged / infeasible run (NaN/inf
in the result arrays, or an empty result set) into a clear RuntimeError instead of
silently propagating NaN into the heat/temperature post-processing. Tested in
isolation with synthetic result dicts — no pandapipes network needed.
"""

import numpy as np
import pytest

from districtheatingsim.net_simulation_pandapipes.result_validation import (
    validate_design_state,
    validate_simulation_results,
)


def _finite_results():
    return {
        "res_circ_pump_pressure.mdot_from_kg_per_s": np.array([[1.0], [1.1], [1.2]]),
        "res_circ_pump_pressure.t_to_k": np.array([[360.0], [361.0], [362.0]]),
    }


class TestValidateSimulationResults:
    def test_finite_results_pass(self):
        validate_simulation_results(_finite_results())  # must not raise

    def test_empty_results_raise(self):
        with pytest.raises(RuntimeError, match="no results"):
            validate_simulation_results({})

    def test_nan_raises_and_names_the_key(self):
        bad = _finite_results()
        bad["res_circ_pump_pressure.t_to_k"][1, 0] = np.nan
        with pytest.raises(RuntimeError, match="res_circ_pump_pressure.t_to_k"):
            validate_simulation_results(bad)

    def test_inf_raises(self):
        bad = _finite_results()
        bad["res_circ_pump_pressure.mdot_from_kg_per_s"][0, 0] = np.inf
        with pytest.raises(RuntimeError, match="NaN/inf"):
            validate_simulation_results(bad)

    def test_context_in_message(self):
        with pytest.raises(RuntimeError, match="my-run"):
            validate_simulation_results({}, context="my-run")

    def test_non_numeric_and_empty_arrays_are_skipped(self):
        results = {
            "labels": np.array(["a", "b"]),         # non-numeric → skipped
            "empty": np.array([]),                   # empty → skipped
            "ok": np.array([1.0, 2.0]),
        }
        validate_simulation_results(results)  # must not raise


def _design_state(qext=7.5):
    return {
        "Heizentrale Haupteinspeisung": {
            0: {"mass_flow_design": 1.2, "flow_temp_design": 85.0,
                "return_temp_design": 60.0, "qext_kW_design": qext},
        },
        "weitere Einspeisung": {},
    }


class TestValidateDesignState:
    def test_finite_design_state_passes(self):
        validate_design_state(_design_state())  # must not raise

    def test_empty_design_state_passes(self):
        # No producers extracted yet → nothing to check, must not raise.
        validate_design_state({"Heizentrale Haupteinspeisung": {}, "weitere Einspeisung": {}})

    def test_nan_design_value_raises_and_names_it(self):
        bad = _design_state(qext=np.nan)
        with pytest.raises(RuntimeError, match=r"qext_kW_design"):
            validate_design_state(bad)

    def test_context_in_message(self):
        with pytest.raises(RuntimeError, match="init-run"):
            validate_design_state(_design_state(qext=np.inf), context="init-run")
