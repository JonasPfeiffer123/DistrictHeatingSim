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
drift (pandapipes is pinned to 0.14.0). Pipe sizing is asserted structurally (all
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


def _make_nd(cop_filename):
    """Build the Görlitz NetworkGenerationData (normal network) with a given COP path."""
    from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import (
        NetworkGenerationData,
    )

    return NetworkGenerationData(
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
        # Network solved: junction results all finite.
        assert np.all(np.isfinite(nd.net.res_junction.values))

    def test_topology_and_demand_kpis(self, goerlitz_run):
        # Geometry + load-profile KPIs — platform-independent, match the GUI; pinned tight.
        _, k = goerlitz_run
        assert k["Anzahl angeschlossene Gebäude"] == 9
        assert k["Anzahl Heizzentralen"] == 1
        assert k["Trassenlänge Wärmenetz [m]"] == pytest.approx(1171.1128, rel=1e-4)
        assert k["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] == pytest.approx(4443.6060, rel=1e-4)
        assert k["max. Heizlast Gebäude [kW]"] == pytest.approx(2107.7698, rel=1e-4)
        assert k["Wärmebedarfsdichte [MWh/(a*m)]"] == pytest.approx(3.794345, rel=1e-4)
        assert k["Anschlussdichte [kW/m]"] == pytest.approx(1.799801, rel=1e-4)

    def test_solver_kpis(self, goerlitz_run):
        # Pipeflow-derived KPIs for the fixed 8-step range; looser tolerance to survive
        # cross-platform solver float drift. Values reflect the round-up diameter sizing
        # in init_diameter_types (pumpstrom dropped ~31% vs the old round-to-closest
        # sizing, which under-sized pipes and inflated the pump head — see BACKLOG C14).
        _, k = goerlitz_run
        assert k["Jahreswärmeerzeugung [MWh]"] == pytest.approx(6.2508, rel=1e-2)
        assert k["Pumpenstrom [MWh]"] == pytest.approx(0.0037649, rel=2e-2)
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
