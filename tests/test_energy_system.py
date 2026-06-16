"""
Integration and unit tests for EnergySystem, ThermalStorageAdapter, and BufferStorage.

Golden-master tests pin headline metrics (WGK_Gesamt, per-tech Wärmemengen/Anteile)
from a deterministic run so that any unintended change to dispatch or cost logic
flips a test.  Structural tests assert that the 8 parallel result lists stay in
lockstep — a guard against the C4-style divergence bugs that were fixed in the
storage integration work.

Unit tests for ThermalStorageAdapter and BufferStorage verify physical invariants
(SOC bounds, Q_loss ≥ 0, energy-balance direction, serialisation round-trip)
independently of EnergySystem.

Expected values were captured from the current implementation (Python 3.11,
Windows).  If the model changes intentionally, regenerate them in the same commit
so the diff makes the behaviour change explicit.
"""

import numpy as np
import pandas as pd
import pytest

from districtheatingsim.heat_generators.chp import CHP, CHPStrategy
from districtheatingsim.heat_generators.energy_system import EnergySystem
from districtheatingsim.heat_generators.gas_boiler import GasBoiler, GasBoilerStrategy
from districtheatingsim.heat_generators.results import TechnologyResult
from districtheatingsim.heat_generators.thermal_storage import BufferStorage, ThermalStorageAdapter
from districtheatingsim.utilities.schema import SCHEMA_VERSIONS

REL = 1e-4  # relative tolerance — slightly looser than single-generator tests

# The 8 parallel result lists that must always stay equal in length (BACKLOG C4).
_PARALLEL_KEYS = (
    "techs",
    "Wärmeleistung_L",
    "Wärmemengen",
    "Anteile",
    "WGK",
    "specific_emissions_L",
    "primärenergie_L",
    "colors",
)


def _assert_parallel_lists(results: dict) -> None:
    """Structural guard: all 8 result lists must be the same length."""
    lengths = {k: len(results[k]) for k in _PARALLEL_KEYS}
    assert len(set(lengths.values())) == 1, f"Parallel result list lengths diverged — C4 regression: {lengths}"


# ---------------------------------------------------------------------------
# Module-scoped helper: build a minimal EnergySystem (no fixtures dependency)
# ---------------------------------------------------------------------------


def _make_energy_system(load: np.ndarray, economic_params: dict) -> EnergySystem:
    ts = pd.date_range("2023-01-01", periods=8760, freq="h").to_numpy()
    VLT_L = np.full(8760, 85.0)
    RLT_L = np.full(8760, 50.0)
    try_data = tuple(np.zeros(8760) for _ in range(5))
    cop_data = np.zeros((2, 2))
    return EnergySystem(ts, load, VLT_L, RLT_L, try_data, cop_data, economic_params)


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

_LOAD = np.linspace(50.0, 400.0, 8760)


# ===========================================================================
# 1. EnergySystem — no network storage
# ===========================================================================


@pytest.fixture(scope="module")
def no_storage_results():
    """CHP(100 kW) + GasBoiler(500 kW), no seasonal storage.  Run once per module."""
    es = _make_energy_system(_LOAD, _ECONOMIC_PARAMS)
    chp = CHP(name="BHKW_1", th_Leistung_kW=100)
    gas_boiler = GasBoiler("Gaskessel_1", thermal_capacity_kW=500)
    es.add_technology(chp)
    es.add_technology(gas_boiler)
    return es.calculate_mix()


class TestEnergySystemNoStorage:
    # ── structural ───────────────────────────────────────────────────────────

    def test_parallel_list_lengths(self, no_storage_results):
        _assert_parallel_lists(no_storage_results)

    def test_anteile_sum_to_one(self, no_storage_results):
        assert sum(no_storage_results["Anteile"]) == pytest.approx(1.0, rel=1e-3)

    def test_wgk_gesamt_positive(self, no_storage_results):
        assert no_storage_results["WGK_Gesamt"] > 0

    def test_waermemengen_match_jahresbedarf(self, no_storage_results):
        # Sum of per-tech heat totals == annual demand
        total = sum(no_storage_results["Wärmemengen"])
        assert total == pytest.approx(no_storage_results["Jahreswärmebedarf"], rel=1e-3)

    # ── golden master ────────────────────────────────────────────────────────

    def test_wgk_gesamt_golden(self, no_storage_results):
        assert no_storage_results["WGK_Gesamt"] == pytest.approx(96.103224, rel=REL)

    def test_chp_waermemenge_golden(self, no_storage_results):
        # BHKW_1 is technology index 0
        assert no_storage_results["Wärmemengen"][0] == pytest.approx(814.638001, rel=REL)

    def test_gaskessel_waermemenge_golden(self, no_storage_results):
        # Gaskessel_1 is technology index 1
        assert no_storage_results["Wärmemengen"][1] == pytest.approx(1156.361999, rel=REL)


class TestOptimizerCoverage:
    """C16: the optimiser must not minimise the objective by undersizing generators."""

    def test_optimizer_does_not_collapse_to_empty_system(self):
        # Before C16 the objective (WGK + emissions + primary-energy, all / full annual
        # demand) was minimised by shrinking the CHP: the uncovered load fell into the
        # cost-free "Ungedeckter Bedarf" row and every term went to 0, so a seeded SLSQP
        # run drove the capacity to the lower bound (0 kW, 0 % covered). The unmet-demand
        # penalty must keep the optimum at a demand-covering size.
        np.random.seed(42)
        es = _make_energy_system(_LOAD, _ECONOMIC_PARAMS)
        es.add_technology(CHP(name="BHKW_1", th_Leistung_kW=300, opt_BHKW_min=0, opt_BHKW_max=1000))
        weights = {"WGK_Gesamt": 1.0, "specific_emissions_Gesamt": 1.0, "primärenergiefaktor_Gesamt": 1.0}

        opt = es.optimize_mix(weights, num_restarts=3)
        chp = opt.technologies[0]
        r = opt.calculate_mix()
        covered = (r["Jahreswärmebedarf"] - r["Restwärmebedarf"]) / r["Jahreswärmebedarf"]

        assert chp.th_Leistung_kW > 50.0  # not collapsed toward the 0 kW lower bound
        assert covered > 0.5  # covers a meaningful share of demand (was ~0 before)


class TestEnergySystemRobustness:
    """C21: domain-core edge cases that used to fail silently or opaquely."""

    def test_single_timestep_duration_defaults_to_one_hour(self):
        # A single-step profile carries no interval, so the np.diff that infers
        # `duration` is empty — construction used to raise IndexError. It now
        # falls back to 1 h instead of crashing.
        ts = pd.date_range("2023-01-01", periods=1, freq="h").to_numpy()
        z = tuple(np.zeros(1) for _ in range(5))
        es = EnergySystem(
            ts, np.array([100.0]), np.array([85.0]), np.array([50.0]), z, np.zeros((2, 2)), _ECONOMIC_PARAMS
        )
        assert es.duration == 1.0

    def test_zero_demand_raises(self):
        # An all-zero load profile gives Jahreswärmebedarf == 0; every share/WGK
        # term divides by it, so the result set used to go silently NaN/inf.
        # calculate_mix now fails loud.
        es = _make_energy_system(np.zeros(8760), _ECONOMIC_PARAMS)
        es.add_technology(GasBoiler("Gaskessel_1", thermal_capacity_kW=500))
        with pytest.raises(ValueError, match="Jahreswärmebedarf"):
            es.calculate_mix()


# ===========================================================================
# 2. EnergySystem — with small network storage (ThermalStorageAdapter)
# ===========================================================================


@pytest.fixture(scope="module")
def network_storage_results():
    """CHP(150 kW) + GasBoiler(500 kW) + 100 m³ cylinder network storage."""
    es = _make_energy_system(_LOAD, _ECONOMIC_PARAMS)

    storage = ThermalStorageAdapter(
        name="TestSpeicher",
        volume=100.0,
        height=5.0,
        T_min=40.0,
        T_max=90.0,
        initial_temp=60.0,
        n_nodes=5,
        geometry_type="cylinder",
        loss_model_type="constant",
        U_loss=0.3,
        T_ambient=15.0,
        fluid_type="water",
        solver="implicit",
        advection_scheme="tvd",
        buoyancy=True,
        spez_Investitionskosten=50.0,
        hours=8760,
        T_charge=85.0,
        T_discharge_return=50.0,
    )

    chp = CHP(name="BHKW_1", th_Leistung_kW=150)
    chp.strategy = CHPStrategy(charge_on=55, charge_off=80)
    gas_boiler = GasBoiler("Gaskessel_1", thermal_capacity_kW=500)
    gas_boiler.strategy = GasBoilerStrategy(charge_on=40)

    es.add_storage(storage)
    es.add_technology(chp)
    es.add_technology(gas_boiler)
    return es.calculate_mix()


class TestEnergySystemWithNetworkStorage:
    # ── structural ───────────────────────────────────────────────────────────

    def test_parallel_list_lengths(self, network_storage_results):
        _assert_parallel_lists(network_storage_results)

    def test_storage_key_present(self, network_storage_results):
        assert "storage_class" in network_storage_results

    def test_storage_soc_bounds(self, network_storage_results):
        soc = network_storage_results["storage_class"]._soc
        assert np.all(soc >= -1e-9), "SOC went below 0"
        assert np.all(soc <= 1.0 + 1e-9), "SOC exceeded 1"

    def test_storage_q_loss_nonneg(self, network_storage_results):
        q_loss = network_storage_results["storage_class"].Q_loss
        assert np.all(q_loss >= 0), "Q_loss has negative values"

    def test_wgk_gesamt_positive(self, network_storage_results):
        assert network_storage_results["WGK_Gesamt"] > 0

    # ── golden master ────────────────────────────────────────────────────────

    def test_wgk_gesamt_golden(self, network_storage_results):
        assert network_storage_results["WGK_Gesamt"] == pytest.approx(97.689475, rel=REL)

    def test_chp_waermemenge_golden(self, network_storage_results):
        assert network_storage_results["Wärmemengen"][0] == pytest.approx(1192.050, rel=REL)


# ===========================================================================
# 2b. TechnologyResult records (C4)
# ===========================================================================


class TestTechnologyResultRecords:
    """C4: per-row `TechnologyResult` records are the single source of truth; the
    German parallel lists are projected from them. Each record field must equal its
    projected list entry at the same index, and records are not serialized.
    """

    @staticmethod
    def _no_storage_system():
        es = _make_energy_system(_LOAD, _ECONOMIC_PARAMS)
        es.add_technology(CHP(name="BHKW_1", th_Leistung_kW=100))
        es.add_technology(GasBoiler("Gaskessel_1", thermal_capacity_kW=500))
        return es

    @staticmethod
    def _network_storage_system():
        es = _make_energy_system(_LOAD, _ECONOMIC_PARAMS)
        storage = ThermalStorageAdapter(
            name="TestSpeicher",
            volume=100.0,
            height=5.0,
            T_min=40.0,
            T_max=90.0,
            initial_temp=60.0,
            n_nodes=5,
            geometry_type="cylinder",
            loss_model_type="constant",
            U_loss=0.3,
            T_ambient=15.0,
            fluid_type="water",
            solver="implicit",
            advection_scheme="tvd",
            buoyancy=True,
            spez_Investitionskosten=50.0,
            hours=8760,
            T_charge=85.0,
            T_discharge_return=50.0,
        )
        chp = CHP(name="BHKW_1", th_Leistung_kW=150)
        chp.strategy = CHPStrategy(charge_on=55, charge_off=80)
        gas = GasBoiler("Gaskessel_1", thermal_capacity_kW=500)
        gas.strategy = GasBoilerStrategy(charge_on=40)
        es.add_storage(storage)
        es.add_technology(chp)
        es.add_technology(gas)
        return es

    def test_records_count_matches_projection(self):
        es = self._no_storage_system()
        results = es.calculate_mix()
        assert len(es.tech_results) == len(results["techs"])
        assert all(isinstance(r, TechnologyResult) for r in es.tech_results)

    def test_record_fields_match_projected_lists(self):
        es = self._no_storage_system()
        r = es.calculate_mix()
        for i, rec in enumerate(es.tech_results):
            assert rec.name == r["techs"][i]
            assert rec.heat_amount_MWh == r["Wärmemengen"][i]
            assert rec.share == r["Anteile"][i]
            assert rec.heat_generation_cost == r["WGK"][i]
            assert rec.specific_co2 == r["specific_emissions_L"][i]
            assert rec.primary_energy == r["primärenergie_L"][i]
            assert rec.color == r["colors"][i]
            # projection reuses the same array object
            assert rec.heat_output_kW is r["Wärmeleistung_L"][i]

    def test_network_storage_has_discharge_record(self):
        es = self._network_storage_system()
        es.calculate_mix()
        names = [rec.name for rec in es.tech_results]
        assert any("Entladung" in name for name in names)
        # all eight projected lists stay in lockstep with the records
        assert len(es.tech_results) == len(es.results["techs"])
        _assert_parallel_lists(es.results)

    def test_records_not_serialized(self):
        es = self._no_storage_system()
        es.calculate_mix()
        d = es.to_dict()
        assert "tech_results" not in d
        assert "tech_results" not in d.get("results", {})


# ===========================================================================
# 2c. Serialization schema version (D2)
# ===========================================================================


class TestSerializationVersion:
    """D2: the serialized EnergySystem carries a schema version, round-trips, and
    a pre-versioning dict (no `version`) still loads."""

    @staticmethod
    def _system():
        es = _make_energy_system(_LOAD, _ECONOMIC_PARAMS)
        es.add_technology(CHP(name="BHKW_1", th_Leistung_kW=100))
        es.add_technology(GasBoiler("Gaskessel_1", thermal_capacity_kW=500))
        es.calculate_mix()
        return es

    def test_to_dict_has_schema_version(self):
        d = self._system().to_dict()
        assert d["_meta"]["schema_version"] == SCHEMA_VERSIONS["energy_system"]
        assert "app_version" in d["_meta"]

    def test_round_trip(self):
        d = self._system().to_dict()
        restored = EnergySystem.from_dict(d)
        assert len(restored.technologies) == 2
        assert restored.economic_parameters == _ECONOMIC_PARAMS

    def test_legacy_dict_without_version_loads(self):
        d = self._system().to_dict()
        d.pop("_meta", None)  # pre-versioning file (no _meta, no version)
        restored = EnergySystem.from_dict(d)  # must not raise
        assert len(restored.technologies) == 2

    def test_legacy_top_level_version_loads(self):
        # Real files saved by the D2 app used a top-level "version" field instead of
        # the _meta block — they must still load.
        d = self._system().to_dict()
        d.pop("_meta", None)
        d["version"] = 1
        restored = EnergySystem.from_dict(d)  # must not raise
        assert len(restored.technologies) == 2


# ===========================================================================
# 3. ThermalStorageAdapter — unit tests
# ===========================================================================


class TestThermalStorageAdapter:
    @staticmethod
    def _make(n_steps: int = 48) -> ThermalStorageAdapter:
        return ThermalStorageAdapter(
            name="UnitTest",
            volume=10.0,
            height=2.0,
            T_min=40.0,
            T_max=90.0,
            initial_temp=65.0,
            n_nodes=5,
            geometry_type="cylinder",
            loss_model_type="constant",
            U_loss=0.5,
            T_ambient=15.0,
            fluid_type="water",
            solver="implicit",
            advection_scheme="tvd",
            buoyancy=True,
            spez_Investitionskosten=50.0,
            hours=n_steps,
        )

    def _simulate(self, sto: ThermalStorageAdapter, Q_in: float, Q_out: float) -> None:
        for t in range(sto.hours):
            sto.simulate_stratified_temperature_mass_flows(t, Q_in, Q_out, T_Q_in_flow=85.0, T_Q_out_return=50.0)

    # ── physical bounds ──────────────────────────────────────────────────────

    def test_soc_bounds_charging(self):
        sto = self._make(48)
        self._simulate(sto, Q_in=50.0, Q_out=10.0)
        assert np.all(sto._soc >= -1e-9)
        assert np.all(sto._soc <= 1.0 + 1e-9)

    def test_soc_bounds_discharging(self):
        sto = self._make(48)
        self._simulate(sto, Q_in=10.0, Q_out=50.0)
        assert np.all(sto._soc >= -1e-9)
        assert np.all(sto._soc <= 1.0 + 1e-9)

    def test_q_loss_nonneg_idle(self):
        sto = self._make(48)
        self._simulate(sto, Q_in=0.0, Q_out=0.0)
        assert np.all(sto.Q_loss >= 0)

    def test_q_loss_nonneg_cycling(self):
        sto = self._make(48)
        # Alternate charge / discharge each step
        for t in range(48):
            q_in = 50.0 if t % 2 == 0 else 0.0
            q_out = 0.0 if t % 2 == 0 else 30.0
            sto.simulate_stratified_temperature_mass_flows(t, q_in, q_out, T_Q_in_flow=85.0, T_Q_out_return=50.0)
        assert np.all(sto.Q_loss >= 0)

    # ── energy balance direction ─────────────────────────────────────────────

    def test_charging_raises_soc(self):
        sto = self._make(24)
        # Initial SOC from the 1D model before any simulation step
        soc_initial = sto._model.get_soc(sto._state, sto.T_min, sto.T_max)
        self._simulate(sto, Q_in=50.0, Q_out=5.0)
        assert sto._soc[-1] > soc_initial, "24 h of net charging should increase SOC"

    def test_discharging_lowers_soc(self):
        # Pre-charge to ~80 % then discharge
        sto = self._make(48)
        for t in range(24):  # charge phase
            sto.simulate_stratified_temperature_mass_flows(t, 50.0, 5.0, T_Q_in_flow=85.0, T_Q_out_return=50.0)
        soc_after_charge = sto._soc[23]
        for t in range(24, 48):  # discharge phase
            sto.simulate_stratified_temperature_mass_flows(t, 5.0, 40.0, T_Q_in_flow=85.0, T_Q_out_return=50.0)
        assert sto._soc[-1] < soc_after_charge, "Net discharging should reduce SOC"

    # ── serialisation ────────────────────────────────────────────────────────

    def test_to_from_dict_roundtrip(self):
        sto = self._make(48)
        d = sto.to_dict()
        sto2 = ThermalStorageAdapter.from_dict(d)
        assert sto2 is not None
        assert sto2.volume == sto.volume
        assert sto2.height == sto.height
        assert sto2.T_min == sto.T_min
        assert sto2.T_max == sto.T_max
        assert sto2.n_nodes == sto.n_nodes
        assert sto2.geometry_type == sto.geometry_type
        assert sto2.loss_model_type == sto.loss_model_type
        assert sto2.initial_temp == sto.initial_temp
        assert sto2.solver == sto.solver

    def test_from_dict_old_config_returns_none(self):
        """Pre-1D config keys must return None, not corrupt data silently."""
        old = {"name": "old", "storage_type": "stratified", "dimensions": {}}
        assert ThermalStorageAdapter.from_dict(old) is None

    def test_to_dict_has_expected_keys(self):
        sto = self._make(48)
        d = sto.to_dict()
        for key in (
            "volume",
            "height",
            "T_min",
            "T_max",
            "n_nodes",
            "geometry_type",
            "loss_model_type",
            "initial_temp",
            "solver",
            "T_charge",
            "T_discharge_return",
        ):
            assert key in d, f"Missing key in to_dict(): {key}"


# ===========================================================================
# 4. BufferStorage — unit tests
# ===========================================================================


class TestBufferStorage:
    @staticmethod
    def _make() -> BufferStorage:
        return BufferStorage(
            volume=5.0,
            T_flow=80.0,
            T_return=60.0,
            U_loss=0.5,
            T_ambient=15.0,
        )

    # ── initial state ────────────────────────────────────────────────────────

    def test_initial_soc_in_range(self):
        buf = self._make()
        soc = buf.get_soc()
        assert 0.0 <= soc <= 1.0

    def test_capacity_positive(self):
        buf = self._make()
        assert buf.get_capacity_kwh() > 0

    # ── physical bounds ──────────────────────────────────────────────────────

    def test_soc_stays_in_range_charging(self):
        buf = self._make()
        for _ in range(24):
            buf.step(50.0)
        assert 0.0 <= buf.get_soc() <= 1.0

    def test_soc_stays_in_range_discharging(self):
        buf = self._make()
        for _ in range(5):
            buf.step(50.0)
        for _ in range(20):
            buf.step(-40.0)
        assert 0.0 <= buf.get_soc() <= 1.0

    def test_q_loss_nonneg(self):
        buf = self._make()
        for _ in range(24):
            buf.step(0.0)
        assert all(q >= 0 for q in buf.Q_loss_history)

    def test_q_loss_after_step_nonneg(self):
        buf = self._make()
        buf.step(0.0)
        assert buf.get_heat_loss_kw() >= 0

    # ── energy balance direction ─────────────────────────────────────────────

    def test_charging_raises_soc(self):
        buf = self._make()
        soc_start = buf.get_soc()
        for _ in range(10):
            buf.step(50.0)
        assert buf.get_soc() >= soc_start

    def test_discharging_lowers_soc(self):
        buf = self._make()
        for _ in range(5):
            buf.step(50.0)  # pre-charge
        soc_mid = buf.get_soc()
        for _ in range(10):
            buf.step(-30.0)
        assert buf.get_soc() <= soc_mid

    # ── history tracking ─────────────────────────────────────────────────────

    def test_history_length_matches_steps(self):
        buf = self._make()
        n = 20
        for _ in range(n):
            buf.step(10.0)
        assert len(buf.soc_history) == n
        assert len(buf.T_top_history) == n
        assert len(buf.T_middle_history) == n
        assert len(buf.T_bottom_history) == n
        assert len(buf.Q_loss_history) == n
        assert len(buf.Q_net_history) == n

    def test_q_net_history_sign_convention(self):
        # step(+x) = charging → Q_net should be positive; step(-x) = discharging → negative
        buf = self._make()
        buf.step(30.0)
        buf.step(-20.0)
        assert buf.Q_net_history[0] == pytest.approx(30.0)
        assert buf.Q_net_history[1] == pytest.approx(-20.0)

    def test_reset_history_clears_all_lists(self):
        buf = self._make()
        for _ in range(5):
            buf.step(10.0)
        buf.reset_history()
        assert len(buf.soc_history) == 0
        assert len(buf.Q_loss_history) == 0
        assert len(buf.Q_net_history) == 0
