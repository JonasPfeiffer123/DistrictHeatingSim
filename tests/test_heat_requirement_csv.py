"""Heat-demand profile generation from building CSV data.

A zero-demand building yields a zero profile.

pyslpheat rejects ``annual_heat_kWh <= 0``; a building with 0.0 Wärmebedarf must still be
carried through with an all-zero profile instead of crashing the whole portfolio.
"""

import os

import numpy as np
import pandas as pd
import pytest

import districtheatingsim
from districtheatingsim.heat_requirement.heat_requirement_calculation_csv import (
    generate_profiles_from_csv,
    resolve_calculation_method,
)

_TRY = os.path.join(
    os.path.dirname(districtheatingsim.__file__),
    "data",
    "TRY",
    "TRY_511676144222",
    "TRY2015_511676144222_Jahr.dat",
)

pytestmark = pytest.mark.skipif(not os.path.exists(_TRY), reason="bundled TRY data not available")


def _buildings(types, subtypes, demands):
    n = len(demands)
    return pd.DataFrame(
        {
            "Wärmebedarf": demands,
            "Gebäudetyp": types,
            "Subtyp": subtypes,
            "WW_Anteil": [0.2] * n,
            "Normaußentemperatur": [-12] * n,
            "VLT_max": [70] * n,
            "RLT_max": [55] * n,
            "Steigung_Heizkurve": [1.5] * n,
        }
    )


@pytest.mark.parametrize(
    ("method", "types", "subtypes"),
    [
        ("BDEW", ["HMF", "HMF"], ["03", "03"]),
        ("VDI4655", ["EFH", "EFH"], ["05", "05"]),
    ],
)
def test_zero_demand_building_yields_zero_profile(method, types, subtypes):
    df = _buildings(types, subtypes, [0.0, 20000.0])
    out = generate_profiles_from_csv(df, _TRY, method, year=2023)
    total_heat_W = out[1]

    assert total_heat_W.shape[0] == 2  # both buildings kept
    assert total_heat_W[0].sum() == 0.0  # zero-demand building → all-zero profile
    assert total_heat_W[1].sum() > 0.0  # normal building → non-zero profile


# --- C42: one method per project, hourly VDI 4655 profiles --------------------------------------


def test_vdi_profiles_are_hourly_and_keep_the_annual_energy():
    # pyslpheat's VDI 4655 profiles are quarter-hourly; they used to be passed on as 35 040
    # "hours" (4x the energy in an hourly model, and only Jan-Mar simulated).
    df = _buildings(["EFH", "MFH"], ["05", "05"], [20000.0, 60000.0])
    time_steps, total_heat_W, heating_W, dhw_W, max_W, supply, _ret, air = generate_profiles_from_csv(
        df, _TRY, "Datensatz", year=2023
    )

    assert len(time_steps) == 8760
    assert (np.diff(time_steps[:3]) == np.timedelta64(1, "h")).all()
    assert total_heat_W.shape == heating_W.shape == dhw_W.shape == supply.shape == (2, 8760)
    assert air.shape == (8760,)
    # 1 h steps: sum of W / 1000 = kWh; VDI 4655 reproduces the annual demand
    np.testing.assert_allclose(total_heat_W.sum(axis=1) / 1000, [20000.0, 60000.0], rtol=1e-3)
    np.testing.assert_allclose(total_heat_W, heating_W + dhw_W)
    np.testing.assert_allclose(max_W, total_heat_W.max(axis=1))


def test_bdew_portfolio_with_residential_types_is_hourly():
    df = _buildings(["HEF", "HMF", "GKO"], ["03", "03", "01"], [20000.0, 60000.0, 40000.0])
    time_steps, total_heat_W, *_ = generate_profiles_from_csv(df, _TRY, "Datensatz", year=2023)

    assert len(time_steps) == 8760
    assert total_heat_W.shape == (3, 8760)


def test_mixing_vdi_and_bdew_types_is_rejected():
    df = _buildings(["EFH", "GKO"], ["05", "01"], [20000.0, 40000.0])
    with pytest.raises(ValueError, match="HEF .* HMF"):
        generate_profiles_from_csv(df, _TRY, "Datensatz", year=2023)


class TestResolveCalculationMethod:
    def test_follows_the_building_types(self):
        assert resolve_calculation_method(["EFH", "MFH", "EFH"], "Datensatz") == "VDI4655"
        assert resolve_calculation_method(["HEF", "HMF", "GKO"], "Datensatz") == "BDEW"
        assert resolve_calculation_method([" MFH "], "Datensatz") == "VDI4655"  # whitespace from CSVs

    def test_explicit_method_is_kept(self):
        assert resolve_calculation_method(["EFH"], "BDEW") == "BDEW"

    def test_mixed_types_name_both_groups(self):
        with pytest.raises(ValueError, match=r"VDI 4655 types \(EFH, MFH\) with BDEW types \(GHA, HMF\)"):
            resolve_calculation_method(["EFH", "HMF", "MFH", "GHA"], "Datensatz")

    def test_unknown_types_are_rejected(self):
        # They silently fell back to VDI 4655 and failed later inside pyslpheat.
        with pytest.raises(ValueError, match="Unknown building types: XYZ, nan"):
            resolve_calculation_method(["HMF", "XYZ", float("nan")], "Datensatz")
