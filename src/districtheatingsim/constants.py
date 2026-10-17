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

#: Credit per MWh of CHP electricity (Stromgutschrift), on the same basis as the CO₂ credit
#: ``CO2_FACTOR_ELECTRICITY`` (grid mix): 1.8 = GEG grid electricity. The credit method of
#: AGFW FW 309-1 / GEG Anlage 4 uses the displacement mix instead (2.8, with 0.86 t CO₂/MWh for
#: the CO₂ credit, and an overall factor of at least 0); change both together.
PRIMARY_ENERGY_FACTOR_ELECTRICITY_CREDIT = 1.8


# ── Generator design ──────────────────────────────────────────────────────────

#: Smallest storage volume per m² solar collector [l/m²] the optimizer may choose, and the green
#: limit of the plausibility check: a daily storage holds about 50-100 l/m² (UT-M15).
SOLAR_STORAGE_MIN_L_PER_M2 = 50.0


# ── Subsidies ─────────────────────────────────────────────────────────────────

#: BEW (Bundesförderung effiziente Wärmenetze) funding share (40 %).
BEW_SUBSIDY_SHARE = 0.4


# ── Network design ────────────────────────────────────────────────────────────

#: Limit of the specific friction pressure loss in the pipe sizing [Pa/m], next to the velocity
#: limit. Velocity alone (1 m/s for every pipe) gives small pipes high losses: DN 20 loses about
#: 690 Pa/m at 1 m/s (k = 0.1 mm), DN 100 about 90 Pa/m. Zittau user test (UT-M12), v_max 1 m/s:
#: without a limit 5.40 bar pump lift (pipes up to 687 Pa/m); 300 Pa/m 3.24 bar for +3.4 % pipe
#: material and +2.8 % design heat loss; 150 Pa/m 2.89 bar, +11.5 % / +6.1 %; 100 Pa/m 2.23 bar,
#: +19 % / +9.5 %. 300 takes most of the pump lift for little extra heat loss (which lasts all
#: year). About 100 Pa/m is the long-standing, conservative practice for service pipes
#: (Energiforsk report 2021:813).
MAX_PRESSURE_LOSS_PA_PER_M = 300.0
