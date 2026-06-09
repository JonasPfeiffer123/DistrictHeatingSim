"""
Example: CHP with Generator-Specific Buffer Storage (Pufferspeicher)
=====================================================================

Demonstrates a CHP unit with an integrated short-term buffer tank
("Anlagenspezifischer Pufferspeicher") backed by ThermalStorage1D.

System design:
  - CHP 500 kW thermal with a 30 m³ buffer tank.
  - The CHP runs at full load when demand is below its capacity,
    charging the buffer with the excess heat.
  - When demand exceeds CHP capacity (or CHP is off), the buffer
    discharges to cover the deficit.
  - Gas boiler 1500 kW as peak-load backup (no buffer).

Buffer storage physics (BufferStorage):
  - Height auto-derived from volume (aspect ratio h ≈ (2V/π)^(1/3)).
  - Implicit ThermalStorage1D solver, WaterProperties fluid.
  - Heat loss modelled with a constant U_loss = 0.5 W/m²K
    (typical well-insulated steel tank in an indoor machine room).

The example plots one week in mid-January (high load) and one week
in May (low load / charging period) to show buffer dispatch behavior.
"""

import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

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

VLT_L = np.full(8760, 90.0)   # supply temperature [°C]
RLT_L = np.full(8760, 60.0)   # return temperature [°C]

# ── Climate data ──────────────────────────────────────────────────────────────
TRY_filename = os.path.abspath(
    'src/districtheatingsim/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat'
)
TRY_data = import_TRY(TRY_filename)
COP_data = np.genfromtxt(
    os.path.abspath('src/districtheatingsim/data/COP/Kennlinien WP.csv'), delimiter=';'
)

# ── Economic parameters ───────────────────────────────────────────────────────
economic_parameters = {
    "gas_price": 50,
    "wood_price": 40,
    "electricity_price": 120,
    "capital_interest_rate": 0.05,
    "inflation_rate": 0.03,
    "time_period": 20,
    "subsidy_eligibility": "Nein",
    "hourly_rate": 45,
}

# ── Energy system (no seasonal network storage) ───────────────────────────────
energy_system = EnergySystem(
    time_steps, load_profile, VLT_L, RLT_L, TRY_data, COP_data, economic_parameters
)

# CHP 500 kW with 30 m³ buffer tank (Pufferspeicher).
# speicher_aktiv=True enables the BufferStorage in simulate_storage().
# Strategy: start if SOC ≤ 20 % (min_fill), stop if SOC ≥ 80 % (max_fill).
chp = CHP(
    name="BHKW_1",
    th_Leistung_kW=500,
    speicher_aktiv=True,
    Speicher_Volumen_BHKW=30,    # m³
    T_vorlauf=90.0,              # °C – matches VLT_L
    T_ruecklauf=60.0,            # °C – matches RLT_L
    initial_fill=0.5,            # start at 50 % SOC
    min_fill=0.2,                # start charging below 20 %
    max_fill=0.8,                # stop charging above 80 %
    spez_Investitionskosten_Speicher=750,   # €/m³
)
# CHPStrategy thresholds are based on NETWORK storage temperatures and are
# not used when speicher_aktiv=True (buffer controls via SOC hysteresis).
# Set to neutral values so CHP always tries to run.
chp.strategy = CHPStrategy(charge_on=85, charge_off=90)
energy_system.add_technology(chp)

# Gas boiler as peak backup (no buffer storage).
gas_boiler = GasBoiler("Gaskessel_1", thermal_capacity_kW=1500)
gas_boiler.strategy = GasBoilerStrategy(charge_on=70)
energy_system.add_technology(gas_boiler)

# ── Run simulation ────────────────────────────────────────────────────────────
print("Running annual simulation …")
results = energy_system.calculate_mix()

# ── Buffer storage history ────────────────────────────────────────────────────
buf = chp.buffer
soc  = np.array(buf.soc_history)
T_top   = np.array(buf.T_top_history)
T_mid   = np.array(buf.T_middle_history)
T_bot   = np.array(buf.T_bottom_history)
Q_loss  = np.array(buf.Q_loss_history)
Q_net   = np.array(buf.Q_net_history)  # + = charge, - = discharge
n_h = len(soc)

print("\n=== Buffer Storage (Pufferspeicher) ===")
print(f"  Volume         : {buf.volume:.0f} m³")
print(f"  Capacity       : {buf.get_capacity_kwh():.0f} kWh")
print(f"  SOC min / max  : {soc.min()*100:.1f} % / {soc.max()*100:.1f} %")
print(f"  Total Q_loss   : {Q_loss.sum():.0f} kWh")
print(f"  T_top range    : {T_top.min():.1f} – {T_top.max():.1f} °C")

print("\n=== Annual Energy Mix ===")
for tech, amt, share in zip(results['techs'], results['Wärmemengen'], results['Anteile']):
    print(f"  {tech:<28s}: {amt:7.0f} MWh  ({share*100:.1f} %)")

# ── Plotting ──────────────────────────────────────────────────────────────────
hours = np.arange(n_h)
chp_profile  = results['Wärmeleistung_L'][0]
load         = load_profile[:n_h]

# Define two interesting windows
windows = {
    "January week (high load)": (7 * 24, 14 * 24),   # 2nd week of January
    "May week (low load/charging)": (31 + 28 + 31 + 30 + 7) * 24,  # 3rd week of May
}
# Convert to (start, end) pairs
windows = {
    "Januar – Woche 2 (hohe Last)":  (7 * 24,  14 * 24),
    "Mai – Woche 3 (niedrige Last)": ((31+28+31+30+14)*24, (31+28+31+30+21)*24),
}

# ── Figure 1: full-year overview ──────────────────────────────────────────────
fig1, axes = plt.subplots(4, 1, figsize=(13, 10), sharex=True)

ax = axes[0]
ax.fill_between(hours, load, alpha=0.25, color='gray', label='Wärmebedarf (kW)')
ax.plot(hours, chp_profile, color='orange', linewidth=0.6, label='BHKW Leistung (kW)')
ax.set_ylabel('Leistung (kW)')
ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

ax = axes[1]
ax.fill_between(hours, Q_net, where=(Q_net > 0), color='steelblue', alpha=0.7,
                label='Beladung (kW)')
ax.fill_between(hours, Q_net, where=(Q_net < 0), color='tomato', alpha=0.7,
                label='Entladung (kW)')
ax.axhline(0, color='black', linewidth=0.5)
ax.set_ylabel('Pufferspeicher\nfluss (kW)')
ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

ax = axes[2]
ax.fill_between(hours, soc * 100, alpha=0.4, color='steelblue')
ax.plot(hours, soc * 100, color='steelblue', linewidth=0.7, label='SOC (%)')
ax.axhline(chp.min_fill * 100, color='red', linewidth=0.8, linestyle='--',
           label=f'min_fill {chp.min_fill*100:.0f}%')
ax.axhline(chp.max_fill * 100, color='green', linewidth=0.8, linestyle='--',
           label=f'max_fill {chp.max_fill*100:.0f}%')
ax.set_ylabel('SOC (%)'); ax.set_ylim(0, 100)
ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

ax = axes[3]
ax.plot(hours, T_top, color='red',       linewidth=0.6, label='T oben (°C)')
ax.plot(hours, T_mid, color='orange',    linewidth=0.6, label='T mitte (°C)')
ax.plot(hours, T_bot, color='royalblue', linewidth=0.6, label='T unten (°C)')
ax.set_ylabel('Temperatur (°C)')
ax.set_xlabel('Stunde des Jahres')
ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

months = ["Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]
mstarts = [0,744,1416,2160,2880,3624,4344,5088,5832,6552,7296,8016]
for ax in axes:
    ax.set_xticks(mstarts); ax.set_xticklabels(months)

fig1.suptitle(
    f'Anlagenspezifischer Pufferspeicher – BHKW 500 kW | V = {buf.volume:.0f} m³'
)
fig1.tight_layout()

# ── Figure 2: weekly detail (2 sub-figures) ───────────────────────────────────
fig2, axs = plt.subplots(2, 3, figsize=(14, 7))
fig2.suptitle('Pufferspeicher – Wochendetail')

for col, (label, (h0, h1)) in enumerate(windows.items()):
    t = np.arange(h0, h1)
    axs[0, col].fill_between(t, load[t], alpha=0.25, color='gray',
                              label='Last (kW)')
    axs[0, col].plot(t, chp_profile[t], color='orange', linewidth=1,
                     label='BHKW (kW)')
    axs[0, col].fill_between(t, Q_net[t], where=(Q_net[t] > 0),
                              color='steelblue', alpha=0.6, label='Beladung')
    axs[0, col].fill_between(t, Q_net[t], where=(Q_net[t] < 0),
                              color='tomato', alpha=0.6, label='Entladung')
    axs[0, col].axhline(0, color='black', linewidth=0.5)
    axs[0, col].set_title(label, fontsize=9)
    axs[0, col].set_ylabel('Leistung / Fluss (kW)')
    axs[0, col].legend(fontsize=7)
    axs[0, col].grid(True, alpha=0.3)

    axs[1, col].plot(t, soc[t] * 100, color='steelblue', linewidth=1,
                     label='SOC (%)')
    axs[1, col].axhline(chp.min_fill * 100, color='red', linestyle='--',
                         linewidth=0.8)
    axs[1, col].axhline(chp.max_fill * 100, color='green', linestyle='--',
                         linewidth=0.8)
    axs[1, col].plot(t, T_top[t], color='red', linewidth=0.8,
                     label='T oben (°C)')
    axs[1, col].plot(t, T_bot[t], color='royalblue', linewidth=0.8,
                     label='T unten (°C)')
    axs[1, col].set_ylabel('SOC (%) / Temp (°C)')
    axs[1, col].set_xlabel('Stunde des Jahres')
    axs[1, col].legend(fontsize=7)
    axs[1, col].grid(True, alpha=0.3)

# Third column: annual Q_loss bar (monthly)
monthly_loss = [Q_loss[s:e].sum() for s, e in zip(mstarts, mstarts[1:] + [8760])]
axs[0, 2].bar(range(12), monthly_loss, color='orange', alpha=0.8)
axs[0, 2].set_xticks(range(12)); axs[0, 2].set_xticklabels(months, fontsize=7)
axs[0, 2].set_title('Monatliche Wärmeverluste')
axs[0, 2].set_ylabel('Verluste (kWh/Monat)')
axs[0, 2].grid(True, alpha=0.3, axis='y')

monthly_charge    = [max(0, Q_net[s:e].sum()) for s, e in zip(mstarts, mstarts[1:] + [8760])]
monthly_discharge = [max(0, -Q_net[s:e].sum()) for s, e in zip(mstarts, mstarts[1:] + [8760])]
axs[1, 2].bar(range(12), monthly_charge, color='steelblue', alpha=0.8,
              label='Beladung (kWh)')
axs[1, 2].bar(range(12), monthly_discharge, color='tomato', alpha=0.8,
              label='Entladung (kWh)', bottom=monthly_charge)
axs[1, 2].set_xticks(range(12)); axs[1, 2].set_xticklabels(months, fontsize=7)
axs[1, 2].set_title('Monatliche Be-/Entladung')
axs[1, 2].set_ylabel('Energie (kWh/Monat)')
axs[1, 2].legend(fontsize=7)
axs[1, 2].grid(True, alpha=0.3, axis='y')

fig2.tight_layout()

energy_system.plot_stack_plot()
energy_system.plot_pie_chart()
plt.show()
