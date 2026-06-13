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

from districtheatingsim.net_simulation_pandapipes.pipe_std_types import (
    kmr_to_isoplus_std_type,
    nearest_isoplus_for_kmr,
    resolve_pipe_u_w_per_m2k,
)
from districtheatingsim.net_simulation_pandapipes.result_validation import (
    validate_design_state,
    validate_net_results,
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


class TestValidateNetResults:
    """Build-time guard (create_network): a solved net must have finite res_junction;
    an empty/NaN result means the design pipeflow did not converge (BACKLOG C2)."""

    @staticmethod
    def _net(res_junction):
        from types import SimpleNamespace
        return SimpleNamespace(res_junction=res_junction)

    def test_finite_results_pass(self):
        import pandas as pd
        net = self._net(pd.DataFrame({"p_bar": [5.0, 4.9], "t_k": [358.0, 357.0]}))
        validate_net_results(net)  # must not raise

    def test_missing_or_empty_results_raise(self):
        import pandas as pd
        with pytest.raises(RuntimeError, match="no junction results"):
            validate_net_results(self._net(None))
        with pytest.raises(RuntimeError, match="no junction results"):
            validate_net_results(self._net(pd.DataFrame()))

    def test_nan_results_raise(self):
        import pandas as pd
        net = self._net(pd.DataFrame({"p_bar": [5.0, np.nan]}))
        with pytest.raises(RuntimeError, match="NaN/inf"):
            validate_net_results(net)

    def test_context_in_message(self):
        with pytest.raises(RuntimeError, match="network generation"):
            validate_net_results(self._net(None), context="network generation")


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


class TestResolvePipeU:
    """pandapipes >=0.14 ISOPLUS pipes carry u_w_per_mk (per length); the legacy
    KMR types stored u_w_per_m2k (per area). The resolver handles both."""

    def test_legacy_per_area_returned_as_is(self):
        props = {"u_w_per_m2k": 0.4, "u_w_per_mk": np.nan, "outer_diameter_mm": 250.0}
        assert resolve_pipe_u_w_per_m2k(props) == 0.4

    def test_isoplus_per_length_converted_via_outer_surface(self):
        # ISOPLUS_DRE100_2x: u_w_per_mk=0.1905, outer=114.3 mm.
        # pandapipes assigns u_w_per_m2k = 0.1905 / (pi * 0.1143) = 0.5305.
        props = {"u_w_per_m2k": np.nan, "u_w_per_mk": 0.1905, "outer_diameter_mm": 114.3}
        assert resolve_pipe_u_w_per_m2k(props) == pytest.approx(0.5305, abs=1e-4)

    def test_per_area_preferred_when_both_present(self):
        props = {"u_w_per_m2k": 0.3, "u_w_per_mk": 0.1905, "outer_diameter_mm": 114.3}
        assert resolve_pipe_u_w_per_m2k(props) == 0.3

    def test_raises_when_neither_available(self):
        props = {"u_w_per_m2k": np.nan, "u_w_per_mk": np.nan, "outer_diameter_mm": 114.3}
        with pytest.raises(ValueError):
            resolve_pipe_u_w_per_m2k(props)

    def test_works_with_pandas_series(self):
        import pandas as pd
        s = pd.Series({"u_w_per_m2k": np.nan, "u_w_per_mk": 0.1905, "outer_diameter_mm": 114.3})
        assert resolve_pipe_u_w_per_m2k(s) == pytest.approx(0.5305, abs=1e-4)


class TestNetworkDataArrayCoercion:
    """`from_dict` must restore numpy-array fields that older project JSONs saved as
    their `str(array)` repr (via json default=str), else the time-series controllers
    silently skip them (KeyError mid-run). BACKLOG C2/C11 regression."""

    @staticmethod
    def _coerce(value):
        from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import (
            NetworkGenerationData,
        )
        return NetworkGenerationData._coerce_array(value)

    def test_string_repr_restored_to_array(self):
        out = self._coerce("[60. 60. 55. 60.]")
        assert isinstance(out, np.ndarray)
        assert out.tolist() == [60.0, 60.0, 55.0, 60.0]

    def test_list_restored_to_array(self):
        out = self._coerce([55.0, 60.0])
        assert isinstance(out, np.ndarray) and out.tolist() == [55.0, 60.0]

    def test_none_and_ndarray_passthrough(self):
        assert self._coerce(None) is None
        arr = np.array([1.0, 2.0])
        assert self._coerce(arr) is arr

    def test_truncated_repr_dropped(self):
        # numpy abbreviates long arrays — unrecoverable, must not be half-parsed.
        assert self._coerce("[77.8 77.3 ... 79.1 78.5]") is None

    def test_2d_and_nonarray_strings_dropped(self):
        assert self._coerce("[[1. 2.][3. 4.]]") is None
        assert self._coerce("Statisch") is None

    def test_json_default_round_trip_is_lossless(self):
        """json_default (save) + _coerce_array (load) must round-trip arrays exactly,
        including long ones that str() would have truncated (BACKLOG C12 save side)."""
        import json as _json

        from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import (
            json_default,
        )
        original = np.linspace(70.0, 85.0, 9000)  # long enough that str() abbreviates
        dumped = _json.dumps({"x": original}, default=json_default)
        assert "..." not in dumped  # serialised as a full list, not a truncated repr
        restored = self._coerce(_json.loads(dumped)["x"])
        assert isinstance(restored, np.ndarray)
        assert np.array_equal(restored, original)


class TestSecondaryProducerRoundTrip:
    """A non-empty secondary_producers list must round-trip through the project JSON:
    saved as dicts (json_default) and rebuilt into SecondaryProducer objects (from_dict),
    so the time-series code can use producer.index / .load_percentage (BACKLOG C12)."""

    @staticmethod
    def _types():
        from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import (
            NetworkGenerationData,
            SecondaryProducer,
            json_default,
        )
        return NetworkGenerationData, SecondaryProducer, json_default

    def test_json_default_serialises_dataclass_to_dict(self):
        _, SecondaryProducer, json_default = self._types()
        out = json_default(SecondaryProducer(index=2, load_percentage=5.0))
        assert out == {"index": 2, "load_percentage": 5.0, "mass_flow": None}

    def test_dicts_rebuilt_into_objects(self):
        NetworkGenerationData, SecondaryProducer, _ = self._types()
        rebuilt = NetworkGenerationData._coerce_secondary_producers(
            [{"index": 1, "load_percentage": 5.0, "mass_flow": None}]
        )
        assert rebuilt == [SecondaryProducer(index=1, load_percentage=5.0)]

    def test_full_json_round_trip(self):
        import json as _json
        NetworkGenerationData, SecondaryProducer, json_default = self._types()
        producers = [SecondaryProducer(index=1, load_percentage=5.0)]
        dumped = _json.dumps({"secondary_producers": producers}, default=json_default)
        loaded = _json.loads(dumped)["secondary_producers"]
        rebuilt = NetworkGenerationData._coerce_secondary_producers(loaded)
        assert rebuilt == producers
        assert rebuilt[0].index == 1 and rebuilt[0].load_percentage == 5.0

    def test_legacy_str_and_empty_and_garbage_drop_to_empty(self):
        NetworkGenerationData, _, _ = self._types()
        assert NetworkGenerationData._coerce_secondary_producers([]) == []
        assert NetworkGenerationData._coerce_secondary_producers(None) == []
        # legacy str(obj) repr is unrecoverable -> dropped
        assert NetworkGenerationData._coerce_secondary_producers(
            ["SecondaryProducer(index=1, load_percentage=5.0, mass_flow=None)"]
        ) == []

    def test_unexpected_dict_keys_ignored(self):
        NetworkGenerationData, SecondaryProducer, _ = self._types()
        rebuilt = NetworkGenerationData._coerce_secondary_producers(
            [{"index": 3, "load_percentage": 10.0, "mass_flow": None, "future_field": 7}]
        )
        assert rebuilt == [SecondaryProducer(index=3, load_percentage=10.0)]


class TestKmrToIsoplus:
    """Legacy KMR pipe names map to their ISOPLUS successors (pandapipes >=0.14)."""

    @pytest.mark.parametrize("kmr,iso", [
        ("KMR 100/250-2v", "ISOPLUS_DRE100_2x"),
        ("KMR 32/140-2v", "ISOPLUS_DRE32_2x"),
        ("KMR 20/125-2v", "ISOPLUS_DRE20_2x"),
        ("KMR 125/280-2v", "ISOPLUS_DRE125_2x"),
        ("KMR 175/-2v", "ISOPLUS_DRE175_2x"),  # blank outer diameter in old data
    ])
    def test_kmr_names_map(self, kmr, iso):
        assert kmr_to_isoplus_std_type(kmr) == iso

    def test_non_kmr_returns_none(self):
        assert kmr_to_isoplus_std_type("ISOPLUS_DRE100_2x") is None
        assert kmr_to_isoplus_std_type("100/182 PLUS") is None
        assert kmr_to_isoplus_std_type(None) is None


class TestNearestIsoplusForKmr:
    """Snap legacy KMR names to an ISOPLUS type that actually exists in the catalog."""

    @staticmethod
    def _catalog():
        import pandapipes as pp
        return pp.std_types.available_std_types(pp.create_empty_network(fluid="water"), "pipe")

    def test_exact_match_used_when_available(self):
        assert nearest_isoplus_for_kmr("KMR 100/250-2v", self._catalog()) == "ISOPLUS_DRE100_2x"

    def test_missing_nominal_width_snaps_to_nearest_rounding_up(self):
        # DN175 is not an ISOPLUS size; 150 and 200 are equidistant -> round up to 200.
        assert nearest_isoplus_for_kmr("KMR 175/-2v", self._catalog()) == "ISOPLUS_DRE200_2x"

    def test_non_kmr_returns_none(self):
        assert nearest_isoplus_for_kmr("ISOPLUS_DRE100_2x", self._catalog()) is None


class TestMigrateLoadedNet:
    """A net saved on pandapipes 0.13 (KMR std-types, diameter_m, no
    inner_diameter_mm) must be upgraded on load so old projects open + recalculate."""

    @staticmethod
    def _old_net():
        import pandapipes as pp
        net = pp.create_empty_network(fluid="water")
        j1 = pp.create_junction(net, pn_bar=5, tfluid_k=358)
        j2 = pp.create_junction(net, pn_bar=5, tfluid_k=358)
        pp.create_pipe_from_parameters(net, j1, j2, length_km=0.1, diameter_m=0.037, k_mm=0.1)
        # Emulate the 0.13 schema: diameter_m present, inner_diameter_mm absent, KMR name.
        net.pipe["diameter_m"] = 0.037
        net.pipe.drop(columns=["inner_diameter_mm"], inplace=True, errors="ignore")
        net.pipe["std_type"] = "KMR 32/140-2v"
        # Emulate the obsolete std-types library shipped inside an old pickle: it holds
        # only KMR types, so a lookup against this net would never find ISOPLUS.
        net.std_types["pipe"] = {
            "KMR 32/140-2v": {"nominal_width_mm": 32, "inner_diameter_mm": 37.2,
                              "outer_diameter_mm": 140, "u_w_per_m2k": 0.4},
        }
        return net

    def test_kmr_pipe_reanchored_to_isoplus(self):
        import pandapipes as pp

        from districtheatingsim.net_simulation_pandapipes.net_migration import migrate_loaded_net
        net = migrate_loaded_net(self._old_net())
        row = net.pipe.iloc[0]
        assert row["std_type"] == "ISOPLUS_DRE32_2x"
        assert "inner_diameter_mm" in net.pipe.columns
        assert np.isfinite(row["inner_diameter_mm"]) and row["inner_diameter_mm"] > 0
        assert np.isfinite(row["u_w_per_m2k"]) and row["u_w_per_m2k"] > 0
        # The net's embedded catalog was refreshed to the current ISOPLUS library so the
        # GUI combo offers (and can select) the new type, not the stale KMR one.
        catalog = pp.std_types.available_std_types(net, "pipe")
        assert "ISOPLUS_DRE32_2x" in catalog.index
        assert "KMR 32/140-2v" not in catalog.index

    def test_inner_diameter_added_when_no_kmr_match(self):
        from districtheatingsim.net_simulation_pandapipes.net_migration import migrate_loaded_net
        net = self._old_net()
        net.pipe["std_type"] = ""  # unknown / no remap
        migrate_loaded_net(net)
        # inner_diameter_mm derived from the legacy diameter_m [m] -> mm.
        assert net.pipe.iloc[0]["inner_diameter_mm"] == pytest.approx(37.0)


@pytest.mark.slow
class TestNetworkInitialization:
    """End-to-end seam: build a tiny district-heating net, run the production
    diameter-init path, and assert invariants on pandapipes 0.14 (pins the
    KMR→ISOPLUS / inner_diameter_mm / u_w_per_mk migration, BACKLOG C11).

    Asserts invariants (convergence, finiteness, ISOPLUS selection), not golden
    values, so it is robust to pandapipes solver-value drift.
    """

    @staticmethod
    def _build_and_init():
        import pandapipes as pp
        from pandapipes.control.run_control import run_control

        from districtheatingsim.net_simulation_pandapipes.utilities import (
            correct_flow_directions,
            create_controllers,
            init_diameter_types,
        )

        net = pp.create_empty_network(fluid="water")
        st = 85 + 273.15
        coords = [(0, 10), (0, 0), (10, 0), (60, 0), (85, 0), (85, 10), (60, 10), (10, 10)]
        j = [pp.create_junction(net, pn_bar=1.05, tfluid_k=st, geodata=c) for c in coords]
        pp.create_circ_pump_const_pressure(net, j[0], j[1], p_flow_bar=4, plift_bar=1.5,
                                           t_flow_k=st, type="auto")
        for a, b, length in [(1, 2, 0.01), (2, 3, 0.05), (3, 4, 0.025)]:
            pp.create_pipe(net, j[a], j[b], std_type="ISOPLUS_DRE100_2x", length_km=length, k_mm=0.1)
        pp.create_heat_consumer(net, j[4], j[5], qext_w=500000, treturn_k=55 + 273.15)
        pp.create_heat_consumer(net, j[3], j[6], qext_w=200000, treturn_k=60 + 273.15)
        for a, b, length in [(5, 6, 0.25), (6, 7, 0.05), (7, 0, 0.01)]:
            pp.create_pipe(net, j[a], j[b], std_type="ISOPLUS_DRE100_2x", length_km=length, k_mm=0.1)

        pp.pipeflow(net, mode="bidirectional", iter=100)
        net = create_controllers(net, np.array([500000, 200000]), 85, None,
                                 np.array([55, 60]), None)
        run_control(net, mode="bidirectional", iter=100)
        net = correct_flow_directions(net)
        return init_diameter_types(net, v_max_pipe=1.5, k=0.1)

    def test_init_converges_and_selects_isoplus(self):
        net = self._build_and_init()
        # Converged: all junction results finite.
        assert np.all(np.isfinite(net.res_junction.values))
        # The u-value resolver assigned finite per-area coefficients (u_w_per_mk path).
        assert np.all(np.isfinite(net.pipe["u_w_per_m2k"].values))
        # Diameter init selected ISOPLUS std-types (the KMR successor) for every pipe.
        assert all(str(s).startswith("ISOPLUS_DRE") for s in net.pipe["std_type"])
        # Pipe diameters are stored in the 0.14 inner_diameter_mm column, all positive.
        assert np.all(net.pipe["inner_diameter_mm"].values > 0)

    def test_recalculate_net_reconverges_after_pipe_edit(self):
        # The domain step behind the GUI "recalculate" button (extracted from the view,
        # BACKLOG B2): editing a pipe + recalculating must re-solve to finite results.
        from districtheatingsim.net_simulation_pandapipes.utilities import recalculate_net
        net = self._build_and_init()
        net.pipe.at[0, "inner_diameter_mm"] *= 1.5
        recalculate_net(net)
        assert np.all(np.isfinite(net.res_junction.values))

    def test_calculate_results_topology_kpis(self):
        # calculate_results is the domain KPI computation the info panel used to call
        # itself (now done by the worker thread, BACKLOG B2). Pin the topology/demand
        # KPIs; with no time series the generation/loss KPIs degrade to None.
        from types import SimpleNamespace

        from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import (
            NetworkGenerationData,
        )
        net = self._build_and_init()
        nd = SimpleNamespace(net=net, waerme_ges_kW=np.array([100.0, 120.0]), pump_results=None)
        kpis = NetworkGenerationData.calculate_results(nd)
        assert kpis["Anzahl angeschlossene Gebäude"] == len(net.heat_consumer)
        assert kpis["Trassenlänge Wärmenetz [m]"] == pytest.approx(net.pipe.length_km.sum() * 1000 / 2)
        assert kpis["Jahresgesamtwärmebedarf Gebäude [MWh/a]"] == pytest.approx(0.22)
        assert kpis["Pumpenstrom [MWh]"] is None  # no pump_results yet
        assert nd.kpi_results is kpis  # cached on the object


class TestAvailablePlotParameters:
    """Plotly-free data layer extracted from interactive_network_plot (BACKLOG B1/B3):
    which result parameters the plot can colour by, per component."""

    @staticmethod
    def _params(net):
        from districtheatingsim.net_simulation_pandapipes.plot_data import (
            available_plot_parameters,
        )
        return available_plot_parameters(net)

    def test_empty_net_has_no_parameters(self):
        from types import SimpleNamespace
        params = self._params(SimpleNamespace())
        assert params == {"junction": [], "pipe": [], "heat_consumer": [],
                          "pump": [], "flow_control": []}

    def test_junction_pipe_consumer_parameters(self):
        from types import SimpleNamespace

        import pandas as pd
        net = SimpleNamespace(
            res_junction=pd.DataFrame(columns=["p_bar", "t_k"]),
            res_pipe=pd.DataFrame(columns=["mdot_from_kg_per_s", "v_mean_m_per_s",
                                           "t_from_k", "t_to_k", "p_from_bar", "p_to_bar"]),
            res_heat_consumer=pd.DataFrame(columns=["qext_w", "mdot_from_kg_per_s",
                                                    "t_from_k", "t_to_k"]),
        )
        params = self._params(net)
        assert params["junction"] == ["p_bar", "t_k"]
        # differential params (dt_k/dp_bar) appear only when both endpoints are present
        assert params["pipe"] == ["mdot_from_kg_per_s", "v_mean_m_per_s", "dt_k", "dp_bar"]
        assert params["heat_consumer"] == ["qext_w", "mdot_from_kg_per_s", "dt_k"]
        assert params["pump"] == []

    def test_pump_parameters_from_pressure_pump(self):
        from types import SimpleNamespace

        import pandas as pd
        net = SimpleNamespace(
            res_circ_pump_pressure=pd.DataFrame(
                {"mdot_from_kg_per_s": [1.0], "deltap_bar": [0.5],
                 "t_from_k": [330.0], "t_to_k": [360.0]}
            ),
        )
        params = self._params(net)
        assert set(params["pump"]) == {"mdot_from_kg_per_s", "deltap_bar", "dt_k"}


class TestJunctionPlotData:
    """Junction marker extraction (Plotly-free data layer, BACKLOG B1/B3)."""

    @staticmethod
    def _net():
        from types import SimpleNamespace

        import pandas as pd
        # Realistic EPSG:25833 (UTM33N) coordinates near Görlitz so reprojection works.
        return SimpleNamespace(
            junction_geodata=pd.DataFrame({"x": [500000.0, 500010.0], "y": [5680000.0, 5680010.0]}),
            junction=pd.DataFrame({"name": ["J0", "J1"]}),
            res_junction=pd.DataFrame({"p_bar": [5.0, 4.9], "t_k": [358.15, 357.15]}),
        )

    def test_coords_hover_and_values(self):
        from districtheatingsim.net_simulation_pandapipes.plot_data import junction_plot_data
        data = junction_plot_data(self._net(), "EPSG:25833", parameter="p_bar")
        assert len(data.lats) == len(data.lons) == 2
        # Reprojected to WGS84 -> latitudes ~51°, longitudes ~14-15° (Görlitz region).
        assert 50 < data.lats[0] < 52
        assert 14 < data.lons[0] < 16
        assert data.hover_texts[0].startswith("<b>J0</b>")
        assert "Druck: 5.00 bar" in data.hover_texts[0]
        assert "Temperatur: 85.0 °C" in data.hover_texts[0]  # 358.15 K - 273.15
        assert list(data.values) == [5.0, 4.9]

    def test_no_parameter_leaves_values_none(self):
        from districtheatingsim.net_simulation_pandapipes.plot_data import junction_plot_data
        data = junction_plot_data(self._net(), "EPSG:25833", parameter=None)
        assert data.values is None
        assert list(data.ids) == [0, 1]


class TestRecalculateNet:
    def test_wraps_solver_failure_in_runtime_error(self):
        import pandapipes as pp

        from districtheatingsim.net_simulation_pandapipes.utilities import recalculate_net
        # An empty network cannot be solved; the opaque pandapipes error is re-raised
        # with run context instead (BACKLOG B2/C2).
        with pytest.raises(RuntimeError, match="recalculation failed"):
            recalculate_net(pp.create_empty_network(fluid="water"))
