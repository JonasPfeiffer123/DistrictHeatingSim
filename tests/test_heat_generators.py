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
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat

REL = 1e-5


class TestGasBoiler:
    @staticmethod
    def _make():
        return GasBoiler(
            name="GB", thermal_capacity_kW=200,
            spez_Investitionskosten=30, Nutzungsgrad=0.9,
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
            name="PTH", thermal_capacity_kW=1000,
            spez_Investitionskosten=30, Nutzungsgrad=0.98,
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
            name="BB", thermal_capacity_kW=200, Größe_Holzlager=40,
            spez_Investitionskosten=200, spez_Investitionskosten_Holzlager=400,
            Nutzungsgrad_BMK=0.8, min_Teillast=0.3, speicher_aktiv=False,
            Speicher_Volumen=20, T_vorlauf=90, T_ruecklauf=60, initial_fill=0.0,
            min_fill=0.2, max_fill=0.8, spez_Investitionskosten_Speicher=750,
            active=True, opt_BMK_min=0, opt_BMK_max=1000,
            opt_Speicher_min=0, opt_Speicher_max=100,
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
            name=name, th_Leistung_kW=100,
            spez_Investitionskosten_GBHKW=1500, spez_Investitionskosten_HBHKW=1850,
            el_Wirkungsgrad=0.33, KWK_Wirkungsgrad=0.9, min_Teillast=0.7,
            speicher_aktiv=False, Speicher_Volumen_BHKW=20, T_vorlauf=90,
            T_ruecklauf=60, initial_fill=0.0, min_fill=0.2, max_fill=0.8,
            spez_Investitionskosten_Speicher=750, active=True,
            opt_BHKW_min=0, opt_BHKW_max=1000,
            opt_BHKW_Speicher_min=0, opt_BHKW_Speicher_max=100,
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
