"""
Filename: renovation_analysis_test.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Script for testing the calculation of renovation costs of buildings with TABULA data.

"""

import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
from src.districtheatingsim.utilities.test_reference_year import import_TRY

class Building:
    STANDARD_U_VALUES = {
        'ground_u': 0.31, 'wall_u': 0.23, 'roof_u': 0.19,
        'window_u': 1.3, 'door_u': 1.3, 'air_change_rate': 0.5,
        'floors': 4, 'fracture_windows': 0.10, 'fracture_doors': 0.01,
        'min_air_temp': -15, 'room_temp': 20, 'max_air_temp_heating': 15,
        'ww_demand_kWh_per_m2': 12.8
    }

    def __init__(self, ground_area, wall_area, roof_area, building_volume, u_values=None):
        self.ground_area = ground_area
        self.wall_area = wall_area
        self.roof_area = roof_area
        self.building_volume = building_volume
        self.u_values = u_values if u_values else self.STANDARD_U_VALUES.copy()
        self.window_area = wall_area * self.u_values["fracture_windows"]
        self.door_area = wall_area * self.u_values["fracture_doors"]

    def calc_heat_demand(self):
        self.real_wall_area = self.wall_area - self.window_area - self.door_area

        heat_loss_per_K = {
            'wall': self.real_wall_area * self.u_values["wall_u"],
            'ground': self.ground_area * self.u_values["ground_u"],
            'roof': self.roof_area * self.u_values["roof_u"],
            'window': self.window_area * self.u_values["window_u"],
            'door': self.door_area * self.u_values["door_u"]
        }

        self.total_heat_loss_per_K = sum(heat_loss_per_K.values())
        self.dT_max_K = self.u_values["room_temp"] - self.u_values["min_air_temp"]
        self.transmission_heat_loss = self.total_heat_loss_per_K * self.dT_max_K
        self.ventilation_heat_loss = 0.34 * self.u_values["air_change_rate"] * self.building_volume * self.dT_max_K
        self.max_heating_demand = self.transmission_heat_loss + self.ventilation_heat_loss

    def calc_yearly_heating_demand(self, temperature_data):
        m = self.max_heating_demand / (self.u_values["min_air_temp"] - self.u_values["max_air_temp_heating"])
        b = -m * self.u_values["max_air_temp_heating"]
        self.yearly_heating_demand = sum(max(m * temp + b, 0) for temp in temperature_data if temp < self.u_values["max_air_temp_heating"]) / 1000

    def calc_yearly_warm_water_demand(self):
        self.yearly_warm_water_demand = self.u_values["ww_demand_kWh_per_m2"] * self.ground_area * self.u_values["floors"]

    def calc_yearly_heat_demand(self, temperature_data):
        self.calc_heat_demand()
        self.calc_yearly_heating_demand(temperature_data)
        self.calc_yearly_warm_water_demand()
        self.yearly_heat_demand = self.yearly_heating_demand + self.yearly_warm_water_demand

class SanierungsAnalyse:
    def __init__(self, ref_building, san_building, energiepreis, diskontierungsrate, jahre):
        self.ref_building = ref_building
        self.san_building = san_building
        self.energiepreis = energiepreis
        self.diskontierungsrate = diskontierungsrate
        self.jahre = jahre

    def berechne_kosteneinsparungen(self):
        alter_waermebedarf = self.ref_building.yearly_heat_demand
        neuer_waermebedarf = self.san_building.yearly_heat_demand
        einsparung = alter_waermebedarf - neuer_waermebedarf
        return einsparung * self.energiepreis

    def berechne_amortisationszeit(self, investitionskosten, foerderquote=0):
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen()
        return effektive_investitionskosten / kosteneinsparung

    def berechne_npv(self, investitionskosten, foerderquote=0):
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        kosteneinsparung = self.berechne_kosteneinsparungen()
        cashflows = [-effektive_investitionskosten] + [kosteneinsparung] * self.jahre
        return npf.npv(self.diskontierungsrate, cashflows)

    def lcca(self, investitionskosten, betriebskosten, instandhaltungskosten, restwert, foerderquote=0):
        effektive_investitionskosten = investitionskosten * (1 - foerderquote)
        cashflows = [-effektive_investitionskosten] + [betriebskosten + instandhaltungskosten] * self.jahre + [restwert]
        return npf.npv(self.diskontierungsrate, cashflows)

# Beispiel-Eingabedaten für ein typisches Mehrfamilienhaus
länge = 10 # m
breite = 15 # m
grundflaeche = länge * breite  # m² pro Etage
anzahl_stockwerke = 2
wall_area_pro_stockwerk = (2*länge + 2*breite) * 2.5  # Wandfläche (2*länge + 2*breite) * 2.5 (Höhe) pro Stockwerk

# Berechnung der Gesamtflächen
ground_area = grundflaeche  # Erdgeschossfläche
wall_area = wall_area_pro_stockwerk * anzahl_stockwerke  # Wandfläche
roof_area = grundflaeche  # Dachfläche
building_volume = ground_area * 3 * anzahl_stockwerke  # Volumen, Höhe pro Stockwerk = 3m

print(f"Grundfläche: {ground_area} m²")
print(f"Wandfläche: {wall_area} m²")
print(f"Dachfläche: {roof_area} m²")
print(f"Gebäudevolumen: {building_volume} m³")
print(f"Anzahl Stockwerke: {anzahl_stockwerke}")

fracture_windows = 0.10
fracture_doors = 0.01

print(f"Fensterfläche: {wall_area * fracture_windows} m²")
print(f"Türfläche: {wall_area * fracture_doors} m²")

u_wert_ground = 0.77 # W/m²K
u_wert_fassade = 1.0  # W/m²K
u_wert_dach = 0.51  # W/m²K
u_wert_fenster = 3.0  # W/m²K
u_wert_tuer = 4  # W/m²K
warmwasserbedarf = 12.80 # kWh/m²
energiepreis = 0.10  # Euro/kWh
diskontierungsrate = 0.03  # 3%
jahre = 20  # Betrachtungszeitraum

# Kaltmiete in €/m² und Gesamtwohnfläche
kaltmiete_pro_m2 = 5  # Euro/m²
wohnflaeche = ground_area * anzahl_stockwerke  # Gesamtwohnfläche in m²
gesamt_kaltmiete = kaltmiete_pro_m2 * wohnflaeche

# Referenz-U-Werte
ref_u_values = {
    'ground_u': u_wert_ground,
    'wall_u': u_wert_fassade,
    'roof_u': u_wert_dach,
    'window_u': u_wert_fenster,
    'door_u': u_wert_tuer,
    'air_change_rate': 0.5,
    'floors': 4,
    'fracture_windows': fracture_windows,
    'fracture_doors': fracture_doors,
    'min_air_temp': -12,
    'room_temp': 20,
    'max_air_temp_heating': 15,
    'ww_demand_kWh_per_m2': warmwasserbedarf
}

# Erstellen eines Building-Objekts für den Referenzzustand
ref_building = Building(ground_area, wall_area, roof_area, building_volume, ref_u_values)

# Ziel-U-Werte nach Sanierung
ziel_u_wert = {
    'ground_u': 0.15,  # W/m²K
    'wall_u': 0.15,  # W/m²K
    'roof_u': 0.15,  # W/m²K
    'window_u': 0.8,  # W/m²K
    'door_u': 0.8  # W/m²K
}

# Sanierungskosten pro m²
kosten = {
    'ground_u': 100,  # Euro/m²
    'wall_u': 100,  # Euro/m²
    'roof_u': 150,  # Euro/m²
    'window_u': 200,  # Euro/m²
    'door_u': 250  # Euro/m²
}

# Betriebs- und Instandhaltungskosten sowie Restwerte
betriebskosten = {
    'ground_u': 50,  # Euro/Jahr
    'wall_u': 100,  # Euro/Jahr
    'roof_u': 125,  # Euro/Jahr
    'window_u': 120,  # Euro/Jahr
    'door_u': 40  # Euro/Jahr
}
instandhaltungskosten = {
    'ground_u': 25,  # Euro/Jahr
    'wall_u': 50,  # Euro/Jahr
    'roof_u': 75,  # Euro/Jahr
    'window_u': 60,  # Euro/Jahr
    'door_u': 25  # Euro/Jahr
}

# Investitionskosten berechnen
investitionskosten = {
    'ground_u': kosten['ground_u'] * ground_area,
    'wall_u': kosten['wall_u'] * wall_area,
    'roof_u': kosten['roof_u'] * roof_area,
    'window_u': kosten['window_u'] * wall_area * fracture_windows,
    'door_u': kosten['door_u'] * wall_area * fracture_doors
}

restwert = {
    'ground_u': investitionskosten['ground_u'] * 0.30,  # 30 % der Investitionskosten
    'wall_u': investitionskosten['wall_u'] * 0.30,  # 30 % der Investitionskosten
    'roof_u': investitionskosten['roof_u'] * 0.30,  # 50 % der Investitionskosten
    'window_u': investitionskosten['window_u'] * 0.30,  # 20 % der Investitionskosten
    'door_u': investitionskosten['door_u'] * 0.30  # 10 % der Investitionskosten
}

# Temperaturdaten importieren (hier ein Beispiel-Array)
temperature_data, _, _, _ = import_TRY("C:\\Users\\jp66tyda\\Documents\\GitHub\\Building-heat-pump-Simulation\\heat_requirement\\TRY_511676144222\\TRY2015_511676144222_Jahr.dat")

# Berechnung des Wärmebedarfs für den Referenzzustand
ref_building.calc_yearly_heat_demand(temperature_data)
print(f"Wärmebedarf vor Sanierung: {ref_building.yearly_heat_demand:.2f} kWh/Jahr")

# Ergebnisse speichern
ergebnisse = {}

# Sanierungsvarianten
varianten = ['ground_u', 'wall_u', 'roof_u', 'window_u', 'door_u', 'Komplettsanierung']

foerderquote = 0.5  # Beispielhafte Förderquote von 50%
for komponente in varianten:
    # Erstellen eines Building-Objekts für den Sanierungszustand
    san_building = Building(ground_area, wall_area, roof_area, building_volume, u_values=ref_building.u_values.copy())
    
    if komponente == 'Komplettsanierung':
        san_building.u_values.update(ziel_u_wert)
    else:
        san_building.u_values[komponente] = ziel_u_wert[komponente]
    
    san_building.calc_yearly_heat_demand(temperature_data)
    neuer_waermebedarf = san_building.yearly_heat_demand

    # Erstellen eines SanierungsAnalyse-Objekts
    analyse = SanierungsAnalyse(ref_building, san_building, energiepreis, diskontierungsrate, jahre)

    # Berechnung der Amortisationszeiten
    amortisationszeit = analyse.berechne_amortisationszeit(sum(investitionskosten.values()) if komponente == 'Komplettsanierung' else investitionskosten[komponente], foerderquote)

    # Berechnung der Netto-Gegenwartswerte (NPV)
    npv = analyse.berechne_npv(sum(investitionskosten.values()) if komponente == 'Komplettsanierung' else investitionskosten[komponente], foerderquote)

    # Berechnung der Lebenszykluskostenanalyse (LCCA)
    lcca = analyse.lcca(sum(investitionskosten.values()) if komponente == 'Komplettsanierung' else investitionskosten[komponente],
                        sum(betriebskosten.values()) if komponente == 'Komplettsanierung' else betriebskosten[komponente],
                        sum(instandhaltungskosten.values()) if komponente == 'Komplettsanierung' else instandhaltungskosten[komponente],
                        sum(restwert.values()) if komponente == 'Komplettsanierung' else restwert[komponente],
                        foerderquote)

    # Ergebnisse speichern
    ergebnisse[komponente] = {
        'Amortisationszeit': amortisationszeit,
        'NPV': npv,
        'LCCA': lcca,
        'Neuer Wärmebedarf': neuer_waermebedarf,
        'Kosteneinsparung': analyse.berechne_kosteneinsparungen()
    }

    # Ausgabe der Ergebnisse
    print(f"--- Ergebnisse für {komponente} mit {foerderquote*100:.0f}% Förderung ---")
    print(f"Amortisationszeit: {amortisationszeit:.2f} Jahre")
    print(f"Netto-Gegenwartswert: {npv:.2f} Euro")
    print(f"Lebenszykluskostenanalyse: {lcca:.2f} Euro")
    print(f"Neuer Wärmebedarf: {neuer_waermebedarf:.2f} kWh/Jahr")
    print(f"Kosteneinsparung: {ergebnisse[komponente]['Kosteneinsparung']:.2f} Euro/Jahr")

# Berechnung der neuen Kaltmiete pro m²
for komponente in varianten:
    investition = sum(investitionskosten.values()) if komponente == 'Komplettsanierung' else investitionskosten[komponente]
    neue_kaltmiete_pro_m2 = kaltmiete_pro_m2 + investition / (amortisationszeit * 12 * wohnflaeche)
    ergebnisse[komponente]['Neue Kaltmiete pro m²'] = neue_kaltmiete_pro_m2

# Diagramme erstellen
n_diagrams = 7  # Anzahl der Diagramme
n_rows = (n_diagrams + 1) // 2  # Berechne die Anzahl der benötigten Zeilen

fig, axs = plt.subplots(n_rows, 2, figsize=(14, 5 * n_rows))
fig.suptitle('Sanierungsergebnisse mit 50% Förderung')

komponenten = ['Boden', 'Wand', 'Dach', 'Fenster', 'Tür', 'Komplett']
labels = ['Amortisationszeit', 'NPV', 'LCCA', 'Kosteneinsparung', 'Energieeinsparung', 'Gesamtenergiebedarf', 'Neue Kaltmiete pro m²']

# Mapping of labels to more descriptive titles
title_mapping = {
    'Amortisationszeit': 'Amortisationszeit (Jahre)',
    'NPV': 'Netto-Gegenwartswert (Euro)',
    'LCCA': 'Lebenszykluskostenanalyse (Euro)',
    'Kosteneinsparung': 'Kosteneinsparung (Euro/Jahr)',
    'Energieeinsparung': 'Energieeinsparung (kWh/Jahr)',
    'Gesamtenergiebedarf': 'Gesamtenergiebedarf (kWh/Jahr)',
    'Neue Kaltmiete pro m²': 'Neue Kaltmiete pro m² (Euro)'
}

# Berechne Energieeinsparung und Gesamtenergiebedarf
energieeinsparung = [ref_building.yearly_heat_demand - ergebnisse[komponente]['Neuer Wärmebedarf'] for komponente in ['ground_u', 'wall_u', 'roof_u', 'window_u', 'door_u', 'Komplettsanierung']]
gesamtenergiebedarf = [ref_building.yearly_heat_demand] + [ergebnisse[komponente]['Neuer Wärmebedarf'] for komponente in ['ground_u', 'wall_u', 'roof_u', 'window_u', 'door_u', 'Komplettsanierung']]
gesamtkomponenten = ['Referenz'] + komponenten

for i, ax in enumerate(axs.flat):
    if i < len(labels):
        label = labels[i]
        if label in ['Energieeinsparung']:
            values = energieeinsparung
            ax.bar(komponenten, values)
        elif label in ['Gesamtenergiebedarf']:
            values = gesamtenergiebedarf
            ax.bar(gesamtkomponenten, values)
        else:
            values = [ergebnisse[komponente][label] for komponente in ['ground_u', 'wall_u', 'roof_u', 'window_u', 'door_u', 'Komplettsanierung']]
            ax.bar(komponenten, values)
        ax.set_title(title_mapping[label])
        ax.set_ylabel('Wert')
        ax.set_xlabel('Komponente')
    else:
        fig.delaxes(ax)  # Entferne überflüssige Subplots

# Diagramm für die Ergebnisse in Abhängigkeit des Förderungssatzes
foerderquoten = np.linspace(0, 1, 11)
amortisationszeit_variation = {komponente: [] for komponente in varianten}
npv_variation = {komponente: [] for komponente in varianten}
lcca_variation = {komponente: [] for komponente in varianten}

for foerderquote in foerderquoten:
    for komponente in varianten:
        san_building = Building(ground_area, wall_area, roof_area, building_volume, u_values=ref_building.u_values.copy())
        
        if komponente == 'Komplettsanierung':
            san_building.u_values.update(ziel_u_wert)
        else:
            san_building.u_values[komponente] = ziel_u_wert[komponente]
        
        san_building.calc_yearly_heat_demand(temperature_data)
        analyse = SanierungsAnalyse(ref_building, san_building, energiepreis, diskontierungsrate, jahre)
        
        amortisationszeit = analyse.berechne_amortisationszeit(sum(investitionskosten.values()) if komponente == 'Komplettsanierung' else investitionskosten[komponente], foerderquote)
        npv = analyse.berechne_npv(sum(investitionskosten.values()) if komponente == 'Komplettsanierung' else investitionskosten[komponente], foerderquote)
        lcca = analyse.lcca(sum(investitionskosten.values()) if komponente == 'Komplettsanierung' else investitionskosten[komponente],
                            sum(betriebskosten.values()) if komponente == 'Komplettsanierung' else betriebskosten[komponente],
                            sum(instandhaltungskosten.values()) if komponente == 'Komplettsanierung' else instandhaltungskosten[komponente],
                            sum(restwert.values()) if komponente == 'Komplettsanierung' else restwert[komponente],
                            foerderquote)
        
        npv_variation[komponente].append(npv)
        lcca_variation[komponente].append(lcca)
        amortisationszeit_variation[komponente].append(amortisationszeit)

fig, axs = plt.subplots(3, 1, figsize=(14, 10))
fig.suptitle('Ergebnisse in Abhängigkeit des Förderungssatzes')

for komponente in varianten:
    axs[0].plot(foerderquoten, npv_variation[komponente], label=komponente)
    axs[1].plot(foerderquoten, lcca_variation[komponente], label=komponente)
    axs[2].plot(foerderquoten, amortisationszeit_variation[komponente], label=komponente)

axs[0].set_title('Netto-Gegenwartswert (NPV)')
axs[0].set_ylabel('NPV (Euro)')
axs[0].set_xlabel('Förderquote')
axs[0].legend()

axs[1].set_title('Lebenszykluskostenanalyse (LCCA)')
axs[1].set_ylabel('LCCA (Euro)')
axs[1].set_xlabel('Förderquote')
axs[1].legend()

axs[2].set_title('Amortisationszeit')
axs[2].set_ylabel('Jahre (a)')
axs[2].set_xlabel('Förderquote')
axs[2].legend()

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()
