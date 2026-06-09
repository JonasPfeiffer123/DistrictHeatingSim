"""
Example: Energy System with Seasonal Thermal Storage (1D model)
================================================================

Demonstrates a district heating energy system with a seasonal pit thermal
energy storage (PTES) backed by ThermalStorage1D (via ThermalStorageAdapter).

System design:
  - CHP (600 kW thermal) as base-load generator. Summer average demand is
    ~228 kW, so the CHP over-produces by ~372 kW that charges the storage.
  - Gas boiler (2500 kW) as peak-load backup for winter demand peaks.
  - PTES (15 000 m³, truncated-cone, ground loss model, 20 nodes):
    absorbs CHP excess in summer and discharges it in winter.

Storage interface (4 hydraulic ports via StorageInputs.two_port):
  - Charge loop   → hot generator supply (T_VL) enters at top;
                    storage return exits at bottom → T_bottom.
  - Discharge loop → cold network return (T_RL) enters at bottom;
                    storage supply exits at top    → T_top.

The EnergySystem passes Q_in (generators) and Q_out (demand) to the storage.
The adapter converts the net flow to mass flows:
  - Q_charge    = max(0, Q_in − Q_out)   → enters storage top
  - Q_discharge = max(0, Q_out − Q_in)   → leaves storage top
"""

import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt

from districtheatingsim.heat_generators.energy_system import EnergySystem
from districtheatingsim.heat_generators.chp import CHP, CHPStrategy
from districtheatingsim.heat_generators.gas_boiler import GasBoiler, GasBoilerStrategy
from districtheatingsim.heat_generators.thermal_storage import ThermalStorageAdapter

from districtheatingsim.utilities.test_reference_year import import_TRY

# ── Simulation horizon ────────────────────────────────────────────────────────
time_steps = pd.date_range(start="2023-01-01", end="2023-12-31 23:00:00", freq="h").to_numpy()

# ── Load profile & temperatures ───────────────────────────────────────────────
file_path = os.path.join('examples', 'data', 'Lastgang', 'Lastgang.csv')
df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
load_profile = df['Gesamtwärmebedarf_Gebäude_kW'].values
# Mean ≈ 474 kW, peak ≈ 2081 kW, annual ≈ 4153 MWh, summer mean ≈ 228 kW

VLT_L = np.full(8760, 85.0)   # generator / network supply temperature [°C]
RLT_L = np.full(8760, 50.0)   # network return temperature [°C]

# ── Climate data ──────────────────────────────────────────────────────────────
TRY_filename = os.path.abspath(
    'src/districtheatingsim/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat'
)
TRY_data = import_TRY(TRY_filename)

COP_filename = os.path.abspath('src/districtheatingsim/data/COP/Kennlinien WP.csv')
COP_data = np.genfromtxt(COP_filename, delimiter=';')

# ── Economic parameters ───────────────────────────────────────────────────────
economic_parameters = {
    "gas_price": 50,
    "wood_price": 40,
    "electricity_price": 120,
    "capital_interest_rate": 1.05,   # factor = 1 + rate (5 %), per VDI 2067 annuity()
    "inflation_rate": 1.03,          # factor = 1 + rate (3 %)
    "time_period": 20,
    "subsidy_eligibility": "Nein",
    "hourly_rate": 45,
}

# ── Seasonal pit thermal energy storage (PTES) ────────────────────────────────
# 15 000 m³ truncated-cone PTES:
#   capacity ≈ 15 000 × 997 × 4200 × 50 / 3.6e9 ≈ 873 MWh
# The CHP summer excess is ~372 kW × 4 400 h ≈ 1 637 MWh, so the storage
# fills and empties about 1.9 times per year — a realistic seasonal cycle.
#
# Ground loss model: buried 2 m deep, mean ground surface temp 10 °C,
# well-insulated lid (U_top = 0.15 W/m²K).
# Implicit solver + TVD advection: unconditionally stable for dt = 1 h.
storage = ThermalStorageAdapter(
    name="Saisonaler Wärmespeicher",
    volume=15_000.0,           # m³
    height=15.0,               # m
    geometry_type="truncated_cone",
    n_nodes=20,
    T_min=40.0,                # °C – lower SOC bound (≈ network return temp)
    T_max=90.0,                # °C – upper SOC bound
    initial_temp=55.0,         # °C – start of year (partially charged)
    loss_model_type="ground",
    U_top=0.15,                # W/m²K – insulated lid
    T_ambient=10.0,            # °C – mean ground surface temperature
    z_ground=2.0,              # m  – burial depth
    fluid_type="water",        # temperature-dependent properties
    solver="implicit",
    advection_scheme="tvd",
    buoyancy=True,
    spez_Investitionskosten=40.0,   # €/m³
    hours=8760,
    T_charge=90.0,                 # °C – fixed generator supply temperature (charge side)
    T_discharge_return=50.0,       # °C – fixed network return temperature (discharge side)
)

# ── Energy system ─────────────────────────────────────────────────────────────
energy_system = EnergySystem(
    time_steps, load_profile, VLT_L, RLT_L, TRY_data, COP_data, economic_parameters
)
energy_system.add_storage(storage)

# CHP 600 kW (base-load) — strategy:
#   OFF → ON  when upper storage temp ≤ 82 °C (storage not yet full)
#   ON  → OFF when upper storage temp ≥ 85 °C (T_max reached)
# In summer the CHP runs almost continuously and charges the storage.
chp = CHP("BHKW_1", th_Leistung_kW=600)
chp.strategy = CHPStrategy(charge_on=82, charge_off=85)
energy_system.add_technology(chp)

# Gas boiler 2500 kW — peak-load backup for winter demand spikes.
gas_boiler = GasBoiler("Gaskessel_1", thermal_capacity_kW=2500)
gas_boiler.strategy = GasBoilerStrategy(charge_on=70)
energy_system.add_technology(gas_boiler)

# ── Run simulation ────────────────────────────────────────────────────────────
print("Running annual simulation …")
results = energy_system.calculate_mix()

# ── Print results ─────────────────────────────────────────────────────────────
sto = results['storage_class']
print("\n=== Seasonal Storage Results ===")
print(f"  Round-trip efficiency  : {sto.efficiency * 100:.1f} %")
print(f"  Total heat loss        : {np.sum(sto.Q_loss) / 1000:.0f} MWh")
print(f"  SOC min / max          : {sto._soc.min() * 100:.1f} % / {sto._soc.max() * 100:.1f} %")
print(f"  SOC at end of year     : {sto._soc[-1] * 100:.1f} %")
print(f"  T_top    min / max     : {sto._T_supply.min():.1f} / {sto._T_supply.max():.1f} °C")
print(f"  T_middle min / max     : {sto._T_middle.min():.1f} / {sto._T_middle.max():.1f} °C")
print(f"  T_bottom min / max     : {sto._T_return.min():.1f} / {sto._T_return.max():.1f} °C")

print("\n=== Energy Mix ===")
for tech, amt, share in zip(results['techs'], results['Wärmemengen'], results['Anteile']):
    print(f"  {tech:<30s}: {amt:8.0f} MWh  ({share * 100:.1f} %)")

# ── Plots ─────────────────────────────────────────────────────────────────────
hours = np.arange(8760)
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
month_starts = [0, 744, 1416, 2160, 2880, 3624,
                4344, 5088, 5832, 6552, 7296, 8016]

fig, axes = plt.subplots(4, 1, figsize=(13, 11), sharex=True)

# Panel 1: Heat demand vs CHP generation
ax = axes[0]
ax.fill_between(hours, load_profile, alpha=0.3, color='gray', label='Heat demand (kW)')
chp_profile = results['Wärmeleistung_L'][0]   # CHP is first technology
ax.plot(hours, chp_profile, color='orange', linewidth=0.7, label='CHP generation (kW)')
ax.set_ylabel('Power (kW)')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Panel 2: Net storage flow
ax = axes[1]
net_flow = sto._Q_net_storage_flow
ax.fill_between(hours, net_flow, where=(net_flow > 0),
                color='red', alpha=0.6, label='Discharge to network (kW)')
ax.fill_between(hours, net_flow, where=(net_flow < 0),
                color='royalblue', alpha=0.6, label='Charge from generators (kW)')
ax.axhline(0, color='black', linewidth=0.5)
ax.set_ylabel('Net storage flow (kW)')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Panel 3: State of charge
ax = axes[2]
ax.fill_between(hours, sto._soc * 100, alpha=0.5, color='steelblue')
ax.plot(hours, sto._soc * 100, color='steelblue', linewidth=0.8, label='SOC (%)')
ax.set_ylabel('SOC (%)')
ax.set_ylim(0, 100)
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Panel 4: Storage temperatures (top / middle / bottom)
# T_middle is used by the generator control strategy (charge_off threshold).
ax = axes[3]
ax.plot(hours, sto._T_supply, color='red', linewidth=0.8, label='T_top (°C)')
ax.plot(hours, sto._T_middle, color='orange', linewidth=0.8,
        label='T_middle – strategy (°C)')
ax.plot(hours, sto._T_return, color='royalblue', linewidth=0.8, label='T_bottom (°C)')
ax.set_ylabel('Temperature (°C)')
ax.set_xlabel('Hour of year')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Month labels on x-axis
for ax in axes:
    ax.set_xticks(month_starts)
    ax.set_xticklabels(months)

fig.suptitle(
    'Seasonal PTES – 15 000 m³  |  CHP 600 kW + Gas Boiler 2 500 kW  |  1D stratified model'
)
plt.tight_layout()

energy_system.plot_stack_plot()
energy_system.plot_pie_chart()
plt.show()
