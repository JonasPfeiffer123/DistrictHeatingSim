"""
Central physical constants and emission/energy factors.
=======================================================

Single source of truth for values that were previously hard-coded (and sometimes
inconsistent) across the codebase (BACKLOG D3): the water heat capacity (`cp` was
both 4.18 and 4.2 kJ/kgK), the Kelvin offset (hard-coded ~20×), and the CO₂ /
primary-energy / subsidy factors duplicated across heat generators.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

# ── Physical constants ────────────────────────────────────────────────────────

#: Celsius ↔ Kelvin offset.
KELVIN_OFFSET = 273.15

#: Specific heat capacity of water [kJ/kg·K]. Unified to 4.18 (≈ value near typical
#: district-heating temperatures; consistent with the 4187 J/kgK in thermal_storage).
CP_WATER_KJ_KGK = 4.18


# ── CO₂ emission factors [t CO₂ / MWh] ────────────────────────────────────────

CO2_FACTOR_GAS = 0.201  #: natural gas
CO2_FACTOR_WOOD = 0.036  #: wood pellets / wood gas
CO2_FACTOR_ELECTRICITY = 0.4  #: grid electricity (mix / displacement)
CO2_FACTOR_SOLAR = 0.0  #: solar thermal heat


# ── Primary-energy factors [-] ────────────────────────────────────────────────

PRIMARY_ENERGY_FACTOR_GAS = 1.1
PRIMARY_ENERGY_FACTOR_WOOD = 0.2
PRIMARY_ENERGY_FACTOR_ELECTRICITY_PTH = 2.4  #: power-to-heat (grid mix)
PRIMARY_ENERGY_FACTOR_ELECTRICITY_HP = 1.8  #: heat pumps
PRIMARY_ENERGY_FACTOR_SOLAR = 0.0


# ── Subsidies ─────────────────────────────────────────────────────────────────

#: BEW (Bundesförderung effiziente Wärmenetze) funding share (40 %).
BEW_SUBSIDY_SHARE = 0.4
