"""
Golden-master / characterization test for the full pandapipes production pipeline.

Drives the real Görlitz project through the exact GUI calculation chain —
``initialize_geojson`` / ``create_network`` → ``time_series_preprocessing`` →
``thermohydraulic_time_series_net`` → ``calculate_results`` — and pins the headline
KPIs, so a regression anywhere in net generation, diameter sizing, the time-series
controllers or the KPI computation is caught.

Marked ``slow`` (numba cold-start + an 8-step bidirectional pipeflow, ~25 s on the dev
box; deselected by ``-m 'not slow'``). The geometry/demand KPIs are derived from the
GeoJSON + load profile only — platform-independent, pinned tight (they match the GUI).
The pipeflow-derived KPIs get a looser tolerance to survive cross-platform solver float
drift (pandapipes is pinned to 0.17.0). Pipe sizing is asserted structurally (all
ISOPLUS, 68 pipes) rather than per-size, since a borderline velocity could flip one.

To regenerate the pinned values after an intentional model change, run this file and
copy the reported KPIs into the ``approx`` calls in the same commit.
"""

from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
_PROJECT = _REPO / "src" / "districtheatingsim" / "project_data" / "Görlitz" / "Variante 1"
_GEOJSON = _PROJECT / "Wärmenetz" / "Wärmenetz.geojson"
_LOAD = _PROJECT / "Lastgang" / "Gebäude Lastgang.json"
_TRY = _REPO / "examples" / "data" / "TRY" / "TRY_511676144222" / "TRY2015_511676144222_Jahr.dat"
_COP = _REPO / "examples" / "data" / "COP" / "Kennlinien WP.csv"

pytestmark = pytest.mark.skipif(
    not (_GEOJSON.exists() and _LOAD.exists() and _TRY.exists() and _COP.exists()),
    reason="Görlitz golden-master data not present in this checkout",
)


def _make_nd(cop_filename, **overrides):
    """Build the Görlitz NetworkGenerationData (normal network) with a given COP path."""
    from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import (
        NetworkGenerationData,
    )

    settings = dict(
        import_type="geoJSON",
        network_geojson_path=str(_GEOJSON),
        heat_demand_json_path=str(_LOAD),
        netconfiguration="Niedertemperaturnetz",
        supply_temperature_control="Statisch",
        max_supply_temperature_heat_generator=85.0,
        min_supply_temperature_heat_generator=70.0,
        max_air_temperature_heat_generator=15.0,
        min_air_temperature_heat_generator=-12.0,
        flow_pressure_pump=4.0,
        lift_pressure_pump=1.5,
        min_supply_temperature_building_checked=False,
        min_supply_temperature_building=0.0,
        fixed_return_temperature_heat_consumer_checked=False,
        fixed_return_temperature_heat_consumer=0.0,
        dT_RL=5.0,
        building_temperature_checked=False,
        pipetype="ISOPLUS_DRE100_2x",
        diameter_optimization_pipe_checked=True,
        max_velocity_pipe=2.0,
        material_filter_pipe="P235GH/PUR/PEHD",
        k_mm_pipe=0.1,
        main_producer_location_index=0,
        secondary_producers=[],
        COP_filename=cop_filename,
        TRY_filename=str(_TRY),
    )
    settings.update(overrides)
    return NetworkGenerationData(**settings)


def _time_series(nd, start, end):
    """Run the GUI time-series chain on a copy of an initialised net (like NetCalculationThread)."""
    import copy

    from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import (
        thermohydraulic_time_series_net,
        time_series_preprocessing,
    )

    run = copy.deepcopy(nd)
    run.start_time_step, run.end_time_step = start, end
    return thermohydraulic_time_series_net(time_series_preprocessing(run))


@pytest.fixture(scope="module")
def goerlitz_run():
    """Run the full production pipeline once for the whole module."""
    import matplotlib

    matplotlib.use("Agg")

    from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import (
        initialize_geojson,
    )
    from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import (
        thermohydraulic_time_series_net,
        time_series_preprocessing,
    )

    nd = _make_nd(str(_COP))
    nd = initialize_geojson(nd)
    nd.start_time_step = 0
    nd.end_time_step = 8  # short characterization range — keep the test fast
    nd = time_series_preprocessing(nd)
    nd = thermohydraulic_time_series_net(nd)
    kpis = nd.calculate_results()
    return nd, kpis


@pytest.mark.slow
class TestGoerlitzGoldenMaster:
    def test_network_structure(self, goerlitz_run):
        nd, _ = goerlitz_run
        assert len(nd.net.pipe) == 68
        # Diameter optimization selected ISOPLUS pipes for the whole net.
        assert all(str(s).startswith("ISOPLUS_DRE") for s in nd.net.pipe["std_type"])
        # C30 regression: the start type was ISOPLUS_DRE100_2x; init + optimize must keep
        # the chosen insulation grade (2x) on every pipe, never reset it to _STD.
        assert all(str(s).endswith("_2x") for s in nd.net.pipe["std_type"])
        # Network solved: junction results all finite.
        assert np.all(np.isfinite(nd.net.res_junction.values))

    def test_topology_and_demand_kpis(self, goerlitz_run):
        # Geometry + load-profile KPIs — platform-independent, match the GUI; pinned tight.
        # Re-pinned for UT-K8: the minimum load is now 2 % of each station's own peak (it was 2 %
        # of the largest station's peak, which had raised the annual demand by 7 %).
        _, k = goerlitz_run
        assert k["Anzahl angeschlossene Gebäude"] == 9
        assert k["Anzahl Heizzentralen"] == 1
        assert k["Trassenlänge Wärmenetz [m]"] == pytest.approx(1171.1128, rel=1e-4)
        assert k["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] == pytest.approx(4155.1464, rel=1e-4)
        assert k["max. Heizlast Gebäude [kW]"] == pytest.approx(2081.3026, rel=1e-4)
        assert k["Wärmebedarfsdichte [MWh/(a*m)]"] == pytest.approx(3.548033, rel=1e-4)
        assert k["Anschlussdichte [kW/m]"] == pytest.approx(1.777201, rel=1e-4)
        # C34: trace length + densities also reported *without* the house-connection (HAST)
        # stubs, which inflate the usual density KPIs.
        assert k["Trassenlänge ohne Hausanschlüsse [m]"] == pytest.approx(966.5170, rel=1e-4)
        assert k["Wärmebedarfsdichte ohne Hausanschlüsse [MWh/(a*m)]"] == pytest.approx(4.299093, rel=1e-4)
        assert k["Anschlussdichte ohne Hausanschlüsse [kW/m]"] == pytest.approx(2.153405, rel=1e-4)

    def test_network_demand_matches_the_building_profiles(self, goerlitz_run):
        # UT-K8: the minimum load may only add a trace; with the old rule (2 % of the largest
        # station's peak for every station) the network carried 7 % more heat than the buildings.
        from districtheatingsim.heat_requirement.building_profiles_io import read_building_profiles

        profiles = read_building_profiles(str(_LOAD))
        building_mwh = sum(np.nansum(v["wärme"]) for v in profiles.values() if isinstance(v, dict) and "wärme" in v)
        _, k = goerlitz_run
        assert k["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] == pytest.approx(building_mwh / 1000, rel=1e-3)

    def test_solver_kpis(self, goerlitz_run):
        # Pipeflow-derived KPIs for the fixed 8-step range; looser tolerance to survive
        # cross-platform solver float drift. Values reflect the round-up diameter sizing
        # in init_diameter_types (pumpstrom dropped ~31% vs the old round-to-closest
        # sizing, which under-sized pipes and inflated the pump head — see BACKLOG C14).
        # Re-pinned for C30: keeping the _2x insulation grade (the old init reset it to
        # _STD) lowers the pipe heat loss, so generation and pumpstrom both dropped ~1-3%.
        # Re-pinned for UT-K1: resized pipes now carry their own outer diameter instead of
        # the DN100 start type's, which had inflated their heat loss (pandapipes uses
        # u * pi * outer diameter); generation dropped 2.0 %, pumpstrom 4.7 %.
        # Re-pinned for UT-K8 (per-station minimum load): generation -2.6 %, pumpstrom -4.4 %.
        # Re-pinned for the pressure loss limit (300 Pa/m next to v_max; this test sizes with
        # v_max 2 m/s): pump lift 2.22 -> 1.39 bar, pumpstrom -29.6 %, generation +0.06 %.
        _, k = goerlitz_run
        assert k["Jahreswärmeerzeugung [MWh]"] == pytest.approx(5.9204, rel=1e-2)
        assert k["Pumpenstrom [MWh]"] == pytest.approx(0.0023542, rel=2e-2)
        # Distribution loss = generation − demand (negative here: an 8-step generation
        # is compared against the annual demand — a known partial-range artifact).
        assert k["Verteilverluste [MWh]"] == pytest.approx(
            k["Jahreswärmeerzeugung [MWh]"] - k["Jahresgesamtwärmebedarf Gebäude [MWh/a]"],
            rel=1e-9,
        )
        # Every KPI computed (no None / NaN leaking through).
        assert all(np.isfinite(v) for v in k.values() if isinstance(v, float))


@pytest.mark.slow
def test_normal_network_runs_without_cop_file():
    # C27: a normal (non-cold) network has no heat pumps and may carry no COP file; COP_filename=None
    # must not crash time_series_preprocessing (was np.genfromtxt(None) -> TypeError).
    import matplotlib

    matplotlib.use("Agg")
    from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson
    from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import time_series_preprocessing

    nd = _make_nd(cop_filename=None)
    nd = initialize_geojson(nd)
    nd.start_time_step = 0
    nd.end_time_step = 8
    nd = time_series_preprocessing(nd)  # must not raise on a normal network without a COP file
    assert nd.waerme_hast_ges_W is not None


@pytest.mark.slow
def test_net_initialisation_reads_parquet_profiles_identically(tmp_path):
    # G7: the building profiles file is now a Parquet array store; network initialisation must
    # get exactly the same demand / temperature data from it as from the legacy Görlitz JSON.
    import json

    import pandas as pd

    from districtheatingsim.heat_requirement.building_profiles_io import write_building_profiles
    from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson

    parquet = tmp_path / "Gebäude Lastgang.parquet"
    original = json.loads(_LOAD.read_text(encoding="utf-8"))
    write_building_profiles(str(parquet), {k: v for k, v in original.items() if k != "_meta"})

    from_json = initialize_geojson(_make_nd(str(_COP)))
    nd = _make_nd(str(_COP))
    nd.heat_demand_json_path = str(parquet)
    from_parquet = initialize_geojson(nd)

    for attr in (
        "waerme_hast_ges_W",
        "heizwaerme_gebaeude_ges_W",
        "supply_temperature_building_curve",
        "return_temperature_building_curve",
        "yearly_time_steps",
    ):
        np.testing.assert_array_equal(getattr(from_parquet, attr), getattr(from_json, attr))
    pd.testing.assert_frame_equal(from_parquet.net.heat_consumer, from_json.net.heat_consumer)  # NaN-aware


@pytest.mark.slow
def test_time_series_with_building_temperatures_and_minimum_supply_temperature():
    # C47: "Gebäudeheizungstemperaturen im zeitlichen Verlauf berücksichtigen" crashed the time
    # series; with a minimum supply temperature its controllers also overwrote the time-dependent
    # return temperatures, and at summer loads the time series aborted after 30 control iterations.
    from districtheatingsim.constants import KELVIN_OFFSET
    from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson

    nd = initialize_geojson(
        _make_nd(str(_COP), building_temperature_checked=True, min_supply_temperature_building=60.0)
    )

    winter = _time_series(nd, 0, 3)
    # January: every station gets its minimum, so the returns follow the building curves (+ dT_RL)
    t_return = winter.net_results["res_heat_consumer.t_to_k"] - KELVIN_OFFSET
    np.testing.assert_allclose(t_return, winter.return_temperature_heat_consumer[:, 0:3].T, atol=1e-3)
    assert np.ptp(t_return, axis=0).min() > 1.0  # time-dependent, not frozen at the first step

    summer = _time_series(nd, 5008, 5009)
    # July: weak stations raise their return temperature until the minimum (60 + 5 °C) is met,
    # 1 K per control iteration - this hour needs 53 (pandapower's default limit is 30)
    assert summer.net_results["res_heat_consumer.t_from_k"].min() - KELVIN_OFFSET >= 64.9


@pytest.mark.slow
@pytest.mark.parametrize("building_temperatures", [False, True], ids=["static", "building_curves"])
def test_cold_network_time_series(building_temperatures):
    # C48: the cold-network time series crashed in both modes and applied the decentral heat pumps
    # twice (to the network heat the initialisation had already reduced).
    from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import initialize_geojson

    nd = initialize_geojson(
        _make_nd(
            str(_COP),
            netconfiguration="kaltes Netz",
            max_supply_temperature_heat_generator=10.0,
            min_supply_temperature_heat_generator=5.0,
            min_supply_temperature_building=None,
            fixed_return_temperature_heat_consumer=5.0,
            building_temperature_checked=building_temperatures,
        )
    )
    run = _time_series(nd, 0, 3)

    building = nd.waerme_gebaeude_ges_W[:, 0:3]
    heat, power = run.waerme_hast_ges_W[:, 0:3], run.strombedarf_hast_ges_W[:, 0:3]
    above_minimum_load = building > 0.02 * nd.waerme_gebaeude_ges_W.max(axis=1, keepdims=True)
    assert above_minimum_load.any()
    # network heat + heat pump electricity = building demand, with a plausible COP
    np.testing.assert_allclose((heat + power)[above_minimum_load], building[above_minimum_load], rtol=1e-9)
    cop = building[above_minimum_load] / power[above_minimum_load]
    assert cop.min() > 2.0 and cop.max() < 6.0
    # the network carries the heat net of the heat pumps
    np.testing.assert_allclose(run.net_results["heat_consumer.qext_w"], heat.T)
