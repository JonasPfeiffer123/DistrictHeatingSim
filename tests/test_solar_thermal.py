"""
Golden-master / characterization tests for the solar thermal model.

Pins the radiation on the tilted collector (``calculate_solar_radiation``), the standalone
hourly simulation behind ``SolarThermal.calculate`` (what the optimizer calls) and the
per-step ``SolarThermal.generate`` path (used with a network storage), on the real TRY data
set of the examples. Added before the BACKLOG G3 performance work (vectorised day-of-year and
IAM lookup, precomputed same-day flags), so that work is provably behaviour-preserving. The
expected numbers were captured from the implementation before G3.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_TRY = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "data"
    / "TRY"
    / "TRY_511676144222"
    / "TRY2015_511676144222_Jahr.dat"
)

pytestmark = pytest.mark.skipif(not _TRY.exists(), reason="TRY example data not present in this checkout")

REL = 1e-9

_ECONOMIC_PARAMS = {
    "gas_price": 70,
    "electricity_price": 150,
    "wood_price": 60,
    "capital_interest_rate": 1.05,
    "inflation_rate": 1.03,
    "time_period": 20,
    "hourly_rate": 45,
    "subsidy_eligibility": "Nein",
}


@pytest.fixture(scope="module")
def try_data():
    from districtheatingsim.utilities.test_reference_year import import_TRY

    return import_TRY(str(_TRY))


@pytest.fixture(scope="module")
def time_steps():
    return pd.date_range("2023-01-01", periods=8760, freq="h").to_numpy()


def _make(typ="Vakuumröhrenkollektor", vs=20):
    from districtheatingsim.heat_generators.solar_thermal import SolarThermal

    st = SolarThermal(
        name="Solarthermie",
        bruttofläche_STA=200,
        vs=vs,
        Typ=typ,
        kosten_speicher_spez=750,
        kosten_fk_spez=430,
        kosten_vrk_spez=590,
        Tsmax=90,
        Longitude=-14.4222,
        STD_Longitude=-15,
        Latitude=51.1676,
        East_West_collector_azimuth_angle=0,
        Collector_tilt_angle=36,
        Tm_rl=60,
        Qsa=0,
        Vorwärmung_K=8,
        DT_WT_Solar_K=5,
        DT_WT_Netz_K=5,
    )
    st.init_operation(8760)
    return st


def _calculate(st, try_data, time_steps, load):
    return st.calculate(
        _ECONOMIC_PARAMS,
        1.0,
        load,
        VLT_L=np.full(8760, 85.0),
        RLT_L=np.full(8760, 55.0),
        TRY_data=try_data,
        time_steps=time_steps,
    )


class TestSolarRadiation:
    def test_tilted_radiation_golden(self, try_data, time_steps):
        from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation

        st = _make()
        GT, K, GbT, GdT = calculate_solar_radiation(
            time_steps,
            try_data[3],
            try_data[2],
            st.Longitude,
            st.STD_Longitude,
            st.Latitude,
            st.Albedo,
            st.East_West_collector_azimuth_angle,
            st.Collector_tilt_angle,
            st.IAM_W,
            st.IAM_N,
        )
        for arr in (GT, K, GbT, GdT):
            assert arr.dtype == float
            assert not np.any(np.isnan(arr))
        assert GT.sum() == pytest.approx(1121660.5710772339, rel=REL)
        assert K.sum() == pytest.approx(3739.712650677282, rel=REL)
        assert GbT.sum() == pytest.approx(378468.87848549837, rel=REL)
        assert GdT.sum() == pytest.approx(743191.6925917354, rel=REL)
        assert GT.max() == pytest.approx(1230.401250900771, rel=REL)
        assert K.max() == pytest.approx(1.1882391829793475, rel=REL)

    def test_day_of_year_handles_leap_year(self, try_data):
        # The vectorised day-of-year must count 29 February (a 2024 profile has 8784 h).
        from districtheatingsim.heat_generators.solar_radiation import calculate_solar_radiation

        st = _make()
        ts = pd.date_range("2024-01-01", periods=8784, freq="h").to_numpy()
        rad = np.concatenate([try_data[3], try_data[3][:24]])
        direct = np.concatenate([try_data[2], try_data[2][:24]])
        GT, *_ = calculate_solar_radiation(
            ts, rad, direct, st.Longitude, st.STD_Longitude, st.Latitude, st.Albedo, 0, 36, st.IAM_W, st.IAM_N
        )
        assert GT.shape == (8784,) and np.all(np.isfinite(GT))


class TestIamLookup:
    def test_matches_dict_get_semantics(self):
        from districtheatingsim.heat_generators.solar_radiation import _iam_lookup

        iam = {0: 1, 10: 1, 20: 0.99, 90: 0.0}
        angles = np.array([0.0, 10.0, 20.0, 30.0, 90.0, 15.0])
        expected = np.array([iam.get(a, 0.0) for a in angles], dtype=float)
        result = _iam_lookup(iam, angles)
        assert result.dtype == float
        np.testing.assert_array_equal(result, expected)

    def test_non_numeric_keys_never_match(self):
        # Same as dict.get(float) on string keys: no match -> 0.0.
        from districtheatingsim.heat_generators.solar_radiation import _iam_lookup

        np.testing.assert_array_equal(_iam_lookup({"10": 1.0}, np.array([10.0])), [0.0])
        np.testing.assert_array_equal(_iam_lookup({}, np.array([10.0, 20.0])), [0.0, 0.0])


class TestSolarThermalCalculate:
    """Standalone hourly simulation (``calculate`` → ``calculate_solar_thermal_with_storage``)."""

    @pytest.mark.parametrize(
        "typ, waermemenge, wgk, betriebsstunden, starts, speicher_sum",
        [
            ("Vakuumröhrenkollektor", 93.40645700946575, 141.61729619353673, 1983.0, 259, -309238.30316791707),
            ("Flachkollektor", 68.04944766491543, 147.61766313310721, 1283.0, 275, -620451.1836507195),
        ],
    )
    def test_golden_master(self, try_data, time_steps, typ, waermemenge, wgk, betriebsstunden, starts, speicher_sum):
        st = _make(typ)
        r = _calculate(st, try_data, time_steps, np.linspace(50.0, 400.0, 8760))
        assert r["Wärmemenge"] == pytest.approx(waermemenge, rel=REL)
        assert r["WGK"] == pytest.approx(wgk, rel=REL)
        assert r["Betriebsstunden"] == pytest.approx(betriebsstunden)
        assert r["Anzahl_Starts"] == starts
        assert np.sum(st.Speicherinhalt) == pytest.approx(speicher_sum, rel=REL)

    def test_stagnation_golden_master(self, try_data, time_steps):
        # Small storage + small load: the stagnation protection (same-day check) kicks in.
        st = _make(vs=2)
        r = _calculate(st, try_data, time_steps, np.full(8760, 5.0))
        assert int(np.sum(st.Stagnation_L)) == 710
        assert r["Wärmemenge"] == pytest.approx(25.251349143881527, rel=REL)


class TestJsonRoundTrip:
    """C37: JSON turns the IAM angle keys into strings; the radiation lookup matches by value,
    so a saved-and-reloaded collector lost its beam IAM and ~half its yield (93.4 -> 46.0 MWh)."""

    def test_reloaded_collector_keeps_its_yield(self, try_data, time_steps):
        import json

        from districtheatingsim.heat_generators.json_encoder import CustomJSONEncoder
        from districtheatingsim.heat_generators.solar_thermal import SolarThermal

        load = np.linspace(50.0, 400.0, 8760)
        fresh = _make()
        reloaded = SolarThermal.from_dict(json.loads(json.dumps(fresh.to_dict(), cls=CustomJSONEncoder)))
        reloaded.init_operation(8760)

        assert all(isinstance(k, float) for k in reloaded.IAM_W)
        assert all(isinstance(k, float) for k in reloaded.IAM_N)
        expected = _calculate(fresh, try_data, time_steps, load)["Wärmemenge"]
        assert _calculate(reloaded, try_data, time_steps, load)["Wärmemenge"] == pytest.approx(expected, rel=REL)


class TestSolarThermalGenerate:
    """Per-step path used by EnergySystem with a network storage."""

    def test_golden_master(self, try_data, time_steps):
        st = _make()
        st.active = True
        load = np.linspace(50.0, 400.0, 8760)
        for t in range(8760):
            st.generate(
                t,
                remaining_load=load[t],
                upper_storage_temperature=70.0,
                lower_storage_temperature=40.0,
                current_storage_state=0.85 if t % 48 < 24 else 0.3,
                available_energy=500.0,
                max_energy=600.0,
                Q_loss=1.0,
                TRY_data=try_data,
                time_steps=time_steps,
                duration=1.0,
            )
        assert np.sum(st.Wärmeleistung_kW) == pytest.approx(105003.74888594961, rel=REL)

    def test_stagnation_golden_master(self, try_data, time_steps):
        st = _make(vs=2)
        st.active = True
        for t in range(8760):
            st.generate(
                t,
                remaining_load=5.0,
                upper_storage_temperature=70.0,
                lower_storage_temperature=40.0,
                current_storage_state=0.9,
                available_energy=100.0,
                max_energy=50.0,
                Q_loss=0.5,
                TRY_data=try_data,
                time_steps=time_steps,
                duration=1.0,
            )
        assert int(np.sum(st.Stagnation_L)) == 1210
        assert np.sum(st.Wärmeleistung_kW) == pytest.approx(52022.67994981218, rel=REL)
