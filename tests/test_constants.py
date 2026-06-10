"""
Tests for the central physical constants (BACKLOG D3).

Pins the values that have no other test coverage (the Kelvin offset and the unified
water heat capacity) and verifies that the heat generators actually source their
emission / primary-energy factors from ``constants`` rather than re-hardcoding them.
"""

from districtheatingsim import constants as C
from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler
from districtheatingsim.heat_generators.gas_boiler import GasBoiler
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat


class TestPhysicalConstants:
    def test_kelvin_offset(self):
        assert C.KELVIN_OFFSET == 273.15

    def test_water_cp_unified_to_4_18(self):
        # D3: cp was 4.18 *and* 4.2 across net_simulation_pandapipes; unified to 4.18.
        assert C.CP_WATER_KJ_KGK == 4.18


class TestFactorValues:
    def test_co2_factors(self):
        assert C.CO2_FACTOR_GAS == 0.201
        assert C.CO2_FACTOR_WOOD == 0.036
        assert C.CO2_FACTOR_ELECTRICITY == 0.4
        assert C.CO2_FACTOR_SOLAR == 0.0

    def test_primary_energy_factors(self):
        assert C.PRIMARY_ENERGY_FACTOR_GAS == 1.1
        assert C.PRIMARY_ENERGY_FACTOR_WOOD == 0.2
        assert C.PRIMARY_ENERGY_FACTOR_ELECTRICITY_PTH == 2.4
        assert C.PRIMARY_ENERGY_FACTOR_ELECTRICITY_HP == 1.8

    def test_bew_subsidy_share(self):
        assert C.BEW_SUBSIDY_SHARE == 0.4


class TestGeneratorsSourceConstants:
    """The centralization must be wired through — not just defined."""

    def test_gas_boiler_uses_gas_constants(self):
        gb = GasBoiler(name="GB", thermal_capacity_kW=100)
        assert gb.co2_factor_fuel == C.CO2_FACTOR_GAS
        assert gb.primärenergiefaktor == C.PRIMARY_ENERGY_FACTOR_GAS

    def test_power_to_heat_uses_electricity_constants(self):
        pth = PowerToHeat(name="PTH", thermal_capacity_kW=100)
        assert pth.co2_factor_fuel == C.CO2_FACTOR_ELECTRICITY
        assert pth.primärenergiefaktor == C.PRIMARY_ENERGY_FACTOR_ELECTRICITY_PTH

    def test_biomass_boiler_uses_wood_constants(self):
        bb = BiomassBoiler(name="BB", thermal_capacity_kW=100, Größe_Holzlager=40)
        assert bb.co2_factor_fuel == C.CO2_FACTOR_WOOD
        assert bb.primärenergiefaktor == C.PRIMARY_ENERGY_FACTOR_WOOD
