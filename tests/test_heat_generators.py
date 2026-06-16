"""
Golden-master regression tests for the GUI-free heat-generator domain core.

Each test drives a generator through ``calculate()`` with the deterministic
fixtures from ``conftest.py`` and pins the headline output metrics (Wärmemenge,
Brennstoffbedarf, WGK, specific CO2, primary energy). These are *characterization*
tests: the expected numbers were captured from the current implementation, so any
unintended change to the dispatch or economic logic will flip a test. If you
change the model on purpose, regenerate the expected values in the same commit.

Tolerance is relative 1e-5 — tight enough to catch logic changes, loose enough to
absorb platform float noise.
"""

import numpy as np
import pytest

from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler
from districtheatingsim.heat_generators.chp import CHP
from districtheatingsim.heat_generators.gas_boiler import GasBoiler
from districtheatingsim.heat_generators.geothermal_heat_pump import Geothermal
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat
from districtheatingsim.heat_generators.river_heat_pump import RiverHeatPump

REL = 1e-5


class TestGasBoiler:
    @staticmethod
    def _make():
        return GasBoiler(
            name="GB",
            thermal_capacity_kW=200,
            spez_Investitionskosten=30,
            Nutzungsgrad=0.9,
        )

    def test_golden_master(self, economic_parameters, load_profile):
        r = self._make().calculate(economic_parameters, 1, load_profile)
        assert r["Wärmemenge"] == pytest.approx(1470.385712, rel=REL)
        assert r["Brennstoffbedarf"] == pytest.approx(1633.761902, rel=REL)
        assert r["WGK"] == pytest.approx(100.121910, rel=REL)
        assert r["spec_co2_total"] == pytest.approx(0.223333, rel=REL)
        assert r["primärenergie"] == pytest.approx(1797.138092, rel=REL)

    def test_output_capped_at_capacity(self, economic_parameters, load_profile):
        r = self._make().calculate(economic_parameters, 1, load_profile)
        assert np.max(r["Wärmeleistung_L"]) <= 200 + 1e-9

    def test_fuel_consistent_with_efficiency(self, economic_parameters, load_profile):
        r = self._make().calculate(economic_parameters, 1, load_profile)
        # Brennstoffbedarf = Wärmemenge / Nutzungsgrad
        assert r["Brennstoffbedarf"] == pytest.approx(r["Wärmemenge"] / 0.9, rel=REL)


class TestPowerToHeat:
    def test_golden_master(self, economic_parameters, load_profile):
        pth = PowerToHeat(
            name="PTH",
            thermal_capacity_kW=1000,
            spez_Investitionskosten=30,
            Nutzungsgrad=0.98,
        )
        r = pth.calculate(economic_parameters, 1, load_profile)
        assert r["Wärmemenge"] == pytest.approx(1971.0, rel=REL)
        assert r["WGK"] == pytest.approx(197.886234, rel=REL)
        assert r["spec_co2_total"] == pytest.approx(0.408163, rel=REL)
        assert r["primärenergie"] == pytest.approx(4826.938776, rel=REL)


class TestBiomassBoiler:
    @staticmethod
    def _make():
        return BiomassBoiler(
            name="BB",
            thermal_capacity_kW=200,
            Größe_Holzlager=40,
            spez_Investitionskosten=200,
            spez_Investitionskosten_Holzlager=400,
            Nutzungsgrad_BMK=0.8,
            min_Teillast=0.3,
            speicher_aktiv=False,
            Speicher_Volumen=20,
            T_vorlauf=90,
            T_ruecklauf=60,
            initial_fill=0.0,
            min_fill=0.2,
            max_fill=0.8,
            spez_Investitionskosten_Speicher=750,
            active=True,
            opt_BMK_min=0,
            opt_BMK_max=1000,
            opt_Speicher_min=0,
            opt_Speicher_max=100,
        )

    def test_golden_master(self, economic_parameters, load_profile):
        r = self._make().calculate(economic_parameters, 1, load_profile)
        assert r["Wärmemenge"] == pytest.approx(1456.582001, rel=REL)
        assert r["Brennstoffbedarf"] == pytest.approx(1820.727502, rel=REL)
        assert r["WGK"] == pytest.approx(103.223583, rel=REL)
        assert r["spec_co2_total"] == pytest.approx(0.045000, rel=REL)
        assert r["primärenergie"] == pytest.approx(364.145500, rel=REL)


class TestCHP:
    @staticmethod
    def _make(name="BHKW"):
        return CHP(
            name=name,
            th_Leistung_kW=100,
            spez_Investitionskosten_GBHKW=1500,
            spez_Investitionskosten_HBHKW=1850,
            el_Wirkungsgrad=0.33,
            KWK_Wirkungsgrad=0.9,
            min_Teillast=0.7,
            speicher_aktiv=False,
            Speicher_Volumen_BHKW=20,
            T_vorlauf=90,
            T_ruecklauf=60,
            initial_fill=0.0,
            min_fill=0.2,
            max_fill=0.8,
            spez_Investitionskosten_Speicher=750,
            active=True,
            opt_BHKW_min=0,
            opt_BHKW_max=1000,
            opt_BHKW_Speicher_min=0,
            opt_BHKW_Speicher_max=100,
        )

    def test_golden_master(self, economic_parameters, load_profile):
        r = self._make().calculate(economic_parameters, 1, load_profile)
        assert r["Wärmemenge"] == pytest.approx(814.638001, rel=REL)
        assert r["Strommenge"] == pytest.approx(471.632527, rel=REL)
        assert r["Brennstoffbedarf"] == pytest.approx(1429.189475, rel=REL)
        assert r["WGK"] == pytest.approx(88.901016, rel=REL)
        assert r["spec_co2_total"] == pytest.approx(0.121053, rel=REL)
        assert r["primärenergie"] == pytest.approx(1572.108423, rel=REL)

    def test_arbitrary_name_defaults_to_gas(self, economic_parameters, load_profile):
        # C6 fixed: a CHP not named BHKW/Holzgas-BHKW no longer crashes with an
        # UnboundLocalError; it keys cost off self.fuel_type (default "gas") and
        # so yields the same result as a "BHKW"-named unit.
        r_named = self._make(name="BHKW").calculate(economic_parameters, 1, load_profile)
        r_other = self._make(name="CHP").calculate(economic_parameters, 1, load_profile)
        assert r_other["WGK"] == pytest.approx(r_named["WGK"], rel=REL)
        assert r_other["spec_co2_total"] == pytest.approx(r_named["spec_co2_total"], rel=REL)

    def test_explicit_fuel_type_overrides_name(self):
        # fuel_type keys the economics, independent of the display name.
        assert self._make(name="BHKW").fuel_type == "gas"
        wood = CHP(name="BHKW", th_Leistung_kW=100, fuel_type="wood_gas")
        assert wood.fuel_type == "wood_gas"
        assert wood.co2_factor_fuel == 0.036  # biomass factor, despite the BHKW name

    def test_holzgas_name_infers_wood_gas(self):
        assert self._make(name="Holzgas-BHKW").fuel_type == "wood_gas"

    def test_invalid_bew_raises(self, economic_parameters, load_profile):
        # C21: BEW neither "Ja" nor "Nein" used to fall off the end of
        # calculate_heat_generation_costs returning None, which silently
        # propagated into the WGK result. It now raises a clear ValueError.
        chp = self._make()
        chp.calculate(economic_parameters, 1, load_profile)  # populate Wärmemenge_MWh
        # subsidy_eligibility drives self.BEW (reloaded at the top of the cost calc),
        # so an invalid value must come through the economic parameters.
        bad_params = {**economic_parameters, "subsidy_eligibility": "Vielleicht"}
        with pytest.raises(ValueError, match="BEW"):
            chp.calculate_heat_generation_costs(bad_params)

    def test_zero_heat_amount_cost_is_inf(self, economic_parameters):
        # C21: the zero-Wärmemenge sentinel is unified on inf (was 0), matching
        # GasBoiler/PowerToHeat so an idle generator never shows a misleading 0 WGK.
        chp = self._make()
        chp.Wärmemenge_MWh = 0
        assert chp.calculate_heat_generation_costs(economic_parameters) == float("inf")


# A 2x2 COP grid: rows = source temps [5, 15] °C, cols = flow temps [40, 60] °C.
# Query (source=10, flow=50) bilinearly interpolates to COP = 4.0 exactly.
_COP_GRID = np.array(
    [
        [0.0, 40.0, 60.0],
        [5.0, 4.0, 3.0],
        [15.0, 5.0, 4.0],
    ]
)


class TestRiverHeatPumpPartLoad:
    """C17: electricity must rescale to the demand-capped heat output."""

    def test_electricity_scales_to_capped_heat_output(self):
        hp = RiverHeatPump("Flusswärme", Wärmeleistung_FW_WP=100.0, Temperatur_FW_WP=10.0)
        # Step 0: demand above nominal -> heat capped to 100 kW (full load).
        # Step 1: demand 50 kW -> heat capped to 50 kW (part load).
        Last_L = np.array([200.0, 50.0])
        VLT_L = np.array([50.0, 50.0])
        hp.calculate_operation(Last_L, VLT_L, _COP_GRID)

        assert hp.COP[0] == pytest.approx(4.0)
        assert hp.Wärmeleistung_kW[0] == pytest.approx(100.0)
        assert hp.Wärmeleistung_kW[1] == pytest.approx(50.0)
        # el = Q / COP at BOTH steps; the part-load step used to stay at the
        # nominal 25 kW (overstated) before C17.
        assert hp.el_Leistung_kW[0] == pytest.approx(25.0)
        assert hp.el_Leistung_kW[1] == pytest.approx(12.5)
        # Energy balance Q = river extraction + electricity on operating steps.
        mask = hp.betrieb_mask
        np.testing.assert_allclose(
            hp.Wärmeleistung_kW[mask],
            hp.Kühlleistung_kW[mask] + hp.el_Leistung_kW[mask],
        )


class TestGeothermalElectricity:
    """C17: generate() must report electrical power, not ground-extraction power."""

    def test_generate_reports_electrical_power(self):
        geo = Geothermal("Erdsonden", Fläche=100.0, Bohrtiefe=100.0, Temperatur_Geothermie=10.0)
        geo.init_operation(2)
        q, el = geo.generate(0, VLT_L=50.0, COP_data=_COP_GRID)

        assert geo.betrieb_mask[0]
        assert geo.COP[0] == pytest.approx(4.0)
        # Electricity is Q / COP (the smaller term), NOT the extraction power
        # Q * (1 - 1/COP); before C17 el equalled the extraction power.
        assert el == pytest.approx(q / 4.0)
        extraction = q * (1 - 1 / 4.0)
        assert el < extraction
        assert el == pytest.approx(geo.Wärmeleistung_kW[0] / geo.COP[0])
