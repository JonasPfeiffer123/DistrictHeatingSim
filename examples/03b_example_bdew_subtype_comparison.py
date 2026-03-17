"""
Filename: 03b_example_bdew_subtype_comparison.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2026-03-04
Description: Vergleicht die verschiedenen Subtypen für building_type "HMF" nach BDEW und stellt die Ergebnisse interaktiv dar.
Usage:
    $ python 03b_example_bdew_subtype_comparison.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons

from pyslpheat import bdew_calculate

# Verfügbare Subtypen für HMF
subtypes = ["03", "04", "05", "33", "34"]
subtype_labels = {
    "03": "HMF03",
    "04": "HMF04",
    "05": "HMF05",
    "33": "HMF33",
    "34": "HMF34"
}

TRY_filename = "src/districtheatingsim/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
YEU_heating_kWh = 20000
building_type = "HMF"
year = 2021
real_ww_share = 0.25

# Ergebnisse für alle Subtypen berechnen
results = {}
for subtype in subtypes:
    df = bdew_calculate(
        annual_heat_kWh=YEU_heating_kWh,
        profile_type=building_type,
        subtype=subtype,
        TRY_file_path=TRY_filename,
        year=year,
        dhw_share=real_ww_share,
    )
    results[subtype] = {
        "hourly_intervals": df.index.values,
        "total": df["Q_total_kWh"].values,
        "heating": df["Q_heat_kWh"].values,
        "warmwater": df["Q_dhw_kWh"].values,
        "temperature": df["temperature_C"].values,
    }

# Interaktives Plotten mit Dropdown
fig, ax = plt.subplots(figsize=(10, 5))
plt.subplots_adjust(top=0.85)

# Initiale Plots für den ersten Subtyp
def plot_subtype(subtype):
    ax.clear()
    r = results[subtype]
    ax.plot(r["hourly_intervals"], r["total"], 'g-', label="Gesamt", linewidth=0.5)
    ax.plot(r["hourly_intervals"], r["heating"], 'b-', label="Heizung", linewidth=0.5)
    ax.plot(r["hourly_intervals"], r["warmwater"], 'r-', label="Warmwasser", linewidth=0.5)
    ax.set_xlabel("Zeitschritte")
    ax.set_ylabel("Wärmebedarf (kW)")
    ax.set_title(f"BDEW: {building_type} Subtyp {subtype_labels[subtype]} - Jahreswärmebedarf: {YEU_heating_kWh} kWh")
    ax.legend(loc='upper left')
    fig.canvas.draw_idle()

# RadioButtons-Widget für Subtyp-Auswahl
ax_radio = plt.axes([0.82, 0.3, 0.15, 0.25], frameon=True)
radio = RadioButtons(ax_radio, [subtype_labels[s] for s in subtypes], active=0)

def on_select(label):
    # Finde den Subtyp-Key anhand des Labels
    for key, val in subtype_labels.items():
        if val == label:
            plot_subtype(key)
            break

radio.on_clicked(on_select)

# Initial Plot
plot_subtype(subtypes[0])

plt.show()
