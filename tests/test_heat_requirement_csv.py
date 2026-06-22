"""Heat-demand profile generation: a zero-demand building yields a zero profile.

pyslpheat rejects ``annual_heat_kWh <= 0``; a building with 0.0 Wärmebedarf must still be
carried through with an all-zero profile instead of crashing the whole portfolio.
"""

import os

import pandas as pd
import pytest

import districtheatingsim
from districtheatingsim.heat_requirement.heat_requirement_calculation_csv import generate_profiles_from_csv

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
