"""
Golden-master / characterization tests for the solar thermal model.

Pins the radiation on the tilted collector (``calculate_solar_radiation``), the standalone
hourly simulation behind ``SolarThermal.calculate`` (what the optimizer calls) and the
per-step ``SolarThermal.generate`` path (used with a network storage), on the real TRY data
set of the examples. Added before the BACKLOG G3 performance work (vectorised day-of-year and
IAM lookup, precomputed same-day flags), so that work is provably behaviour-preserving. The
expected numbers were captured from the implementation before G3; the standalone-simulation
values were deliberately re-pinned for the C38 storage balance (2026-10-01: heat is delivered
only after the losses, a cooled storage's loss temperature follows its deficit; +0.06 to +0.11 %
Wärmemenge) and for the overflow fix (an overflowing storage is exactly full, so the stagnation
count no longer depends on the platform's rounding: 2 m³ case 712 → 736 h).
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


@pytest.fixture(params=["python", "numba"])
def kernel_path(request, monkeypatch):
    """Run a test once on the plain-Python hourly loop and once numba-compiled (if installed)."""
    from districtheatingsim.heat_generators import solar_thermal

    if request.param == "numba":
        pytest.importorskip("numba")
        monkeypatch.delenv(solar_thermal.NUMBA_DISABLE_ENV, raising=False)
        monkeypatch.setattr(solar_thermal, "_jit_kernel", None)  # resolve (and compile) afresh
    else:
        monkeypatch.setattr(solar_thermal, "_jit_kernel", False)
    return request.param


@pytest.mark.usefixtures("kernel_path")
class TestSolarThermalCalculate:
    """Standalone hourly simulation (``calculate`` → ``calculate_solar_thermal_with_storage``),
    on both kernel paths: plain Python is bit-identical to the pre-G3 loop; the numba build
    differs by at most one ulp in single steps (LLVM evaluates ``x ** 2`` as ``x * x``)."""

    @pytest.mark.parametrize(
        "typ, waermemenge, wgk, betriebsstunden, starts, speicher_sum",
        [
            ("Vakuumröhrenkollektor", 93.465548945164, 141.52776116961752, 1985.0, 260, -280968.48263637),
            ("Flachkollektor", 68.12238410323721, 147.45961366487373, 1283.0, 275, -534297.9001488248),
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
        # 736 (was 710/712 depending on the platform): every overflowing hour now counts as full.
        assert int(np.sum(st.Stagnation_L)) == 736
        assert r["Wärmemenge"] == pytest.approx(25.24302754643216, rel=REL)

    @pytest.mark.parametrize(("vs", "load"), [(20, np.linspace(50.0, 400.0, 8760)), (2, np.full(8760, 5.0))])
    def test_storage_energy_balance(self, try_data, time_steps, vs, load):
        # C38: `Speicherinhalt` is the usable energy above the lower storage level; below zero the
        # storage has cooled below it. Heat is only delivered from what is left after the previous
        # step's losses, and every step closes the balance (capped at QSmax = stagnation).
        st = _make(vs=vs)
        _calculate(st, try_data, time_steps, load)
        content = np.asarray(st.Speicherinhalt)
        loss = np.asarray(st.Verlustwärmestrom_Speicher_L)
        yield_ = np.asarray(st.Kollektorfeldertrag_L)
        heat = np.asarray(st.Wärmeleistung_kW)

        available = yield_[1:] + content[:-1] - loss[:-1]
        assert np.all(heat[1:] <= np.maximum(available, 0.0) + 1e-9)
        np.testing.assert_allclose(content[1:], np.minimum(st.QSmax, available - heat[1:]), rtol=0, atol=1e-9)
        assert content.min() < 0  # the storage does cool below its usable level in these cases
        assert np.all(loss[content < 0] >= 0)  # a cooled storage never gains heat from the air
        # An overflowing storage is exactly full — never 1 ulp below, where the stagnation check
        # (content >= QSmax) used to depend on the platform's rounding.
        assert not np.any((content < st.QSmax) & (content > st.QSmax * (1 - 1e-12)))


class TestKernelSelection:
    def test_numba_kernel_is_used_when_installed(self, monkeypatch):
        pytest.importorskip("numba")
        from districtheatingsim.heat_generators import solar_thermal

        monkeypatch.delenv(solar_thermal.NUMBA_DISABLE_ENV, raising=False)
        monkeypatch.setattr(solar_thermal, "_jit_kernel", None)
        assert solar_thermal._jit_solar_storage_steps() is not None

    def test_env_switch_forces_python(self, monkeypatch):
        from districtheatingsim.heat_generators import solar_thermal

        monkeypatch.setenv(solar_thermal.NUMBA_DISABLE_ENV, "1")
        monkeypatch.setattr(solar_thermal, "_jit_kernel", None)
        assert solar_thermal._jit_solar_storage_steps() is None

    def test_short_inputs_raise_instead_of_reading_out_of_bounds(self, try_data, time_steps, monkeypatch):
        # numba does not bounds-check; too-short inputs must take the Python path and raise.
        from districtheatingsim.heat_generators import solar_thermal

        monkeypatch.setattr(solar_thermal, "_jit_kernel", None)
        st = _make()
        with pytest.raises(IndexError):
            st.calculate_solar_thermal_with_storage(
                np.full(100, 50.0), np.full(8760, 85.0), np.full(8760, 55.0), try_data, time_steps, 1.0
            )


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
