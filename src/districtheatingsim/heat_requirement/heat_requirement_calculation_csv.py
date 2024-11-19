"""
Filename: heat_requirement_calculation_csv.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-09
Description: Contains the functions for calculating the heating demand for given buildings.
"""

import numpy as np
from districtheatingsim.heat_requirement import heat_requirement_VDI4655, heat_requirement_BDEW

def generate_profiles_from_csv(data, TRY, calc_method):
    """
    Generiert Heizprofile auf Basis von CSV-Daten.

    Args:
        data (DataFrame): DataFrame mit Informationen zum Gebäude (Spalten: 'Wärmebedarf', 'Gebäudetyp', 'Subtyp', 'WW_Anteil', 'Normaußentemperatur').
        TRY (str): Pfad zur TRY (Test Reference Year)-Datei, die Wetterdaten enthält.
        calc_method (str): Berechnungsmethode.

    Returns:
        tuple: Enthält folgende Werte:
            - yearly_time_steps (ndarray): Jährliche Zeitschritte.
            - total_heat_W (ndarray): Gesamtwärmebedarf in Watt.
            - heating_heat_W (ndarray): Wärmebedarf für Heizung in Watt.
            - warmwater_heat_W (ndarray): Wärmebedarf für Warmwasser in Watt.
            - max_heat_requirement_W (ndarray): Maximaler Wärmebedarf in Watt.
            - supply_temperature_curve (ndarray): Vorlauftemperaturkurve.
            - return_temperature_curve (ndarray): Rücklauftemperaturkurve.
            - hourly_air_temperatures (ndarray): Stündliche Außentemperaturen.
    """

    # folgendes wird statisch gesetzt, muss in Zukunft noch in config-Datei ausgelagert werden oder im UI einstellbar sein
    year = 2021 # Jahr, für das die Berechnung durchgeführt wird (für VDI 4655, BDEW)
    holidays = np.array(["2021-01-01", "2021-04-02", "2021-04-05", "2021-05-01", "2021-05-24", "2021-05-13", 
                         "2021-06-03", "2021-10-03", "2021-11-01", "2021-12-25", "2021-12-26"]).astype('datetime64[D]') # Feiertage in Deutschland 2021 (ohne Wochenenden) als datetime64[D]-Array (YYYY-MM-DD) für VDI 4655
    climate_zone = "9"  # Klimazone 9: Deutschland (VDI 4655)
    number_people_household = 2  # Anzahl der Personen im Haushalt (VDI 4655)
    
    try:
        YEU_total_heat_kWh = data["Wärmebedarf"].values.astype(float)
        building_type = data["Gebäudetyp"].values.astype(str)
        subtyp = data["Subtyp"].values.astype(str)
        ww_demand = data["WW_Anteil"].values.astype(float)
        min_air_temperature = data["Normaußentemperatur"].values.astype(float)
    except KeyError as e:
        raise KeyError(f"Fehlende Spalte im CSV: {e}. Überprüfen Sie die CSV-Datei auf Vollständigkeit.") from e
    except ValueError as e:
        raise ValueError(f"Fehlerhafte Datentypen in CSV-Daten: {e}. Bitte stellen Sie sicher, dass die Daten korrekt formatiert sind.") from e

    total_heat_W = []
    heating_heat_W = []
    warmwater_heat_W = []
    max_heat_requirement_W = []
    yearly_time_steps = None

    building_type_to_method = {
        "EFH": "VDI4655",
        "MFH": "VDI4655",
        "HEF": "BDEW",
        "HMF": "BDEW",
        "GKO": "BDEW",
        "GHA": "BDEW",
        "GMK": "BDEW",
        "GBD": "BDEW",
        "GBH": "BDEW",
        "GWA": "BDEW",
        "GGA": "BDEW",
        "GBA": "BDEW",
        "GGB": "BDEW",
        "GPD": "BDEW",
        "GMF": "BDEW",
        "GHD": "BDEW",
    }

    for idx, YEU in enumerate(YEU_total_heat_kWh):
        current_building_type = str(data.at[idx, "Gebäudetyp"])
        current_subtype = str(data.at[idx, "Subtyp"])
        current_ww_demand = float(data.at[idx, "WW_Anteil"])
        if calc_method == "Datensatz":
            try:
                current_calc_method = building_type_to_method.get(current_building_type, "StandardMethode")
            except KeyError:
                print("Building type column not found in CSV.")
                current_calc_method = "StandardMethode"
        else:
            current_building_type = building_type
            current_calc_method = calc_method

        if current_calc_method == "VDI4655":
            YEU_heating_kWh, YEU_hot_water_kWh = YEU_total_heat_kWh * (1-ww_demand), YEU_total_heat_kWh * ww_demand
            heating, hot_water = YEU_heating_kWh[idx], YEU_hot_water_kWh[idx]
            # YEU_electricity_kW is currently set to 0, as it is not used in the following calculations
            yearly_time_steps, hourly_heat_demand_total_kW, hourly_heat_demand_heating_kW, hourly_heat_demand_warmwater_kW, hourly_air_temperatures, electricity_kW = heat_requirement_VDI4655.calculate(YEU_heating_kWh=heating, YEU_hot_water_kWh=hot_water, YEU_electricity_kWh=0, building_type=current_building_type, number_people_household=number_people_household, year=year, climate_zone=climate_zone, TRY=TRY, holidays=holidays)

        elif current_calc_method == "BDEW":
            # year is set to 2021 as a default value
            yearly_time_steps, hourly_heat_demand_total_kW, hourly_heat_demand_heating_kW, hourly_heat_demand_warmwater_kW, hourly_air_temperatures = heat_requirement_BDEW.calculate(YEU, current_building_type, current_subtype, TRY, year, current_ww_demand)

        hourly_heat_demand_total_kW = np.clip(hourly_heat_demand_total_kW, 0, None)
        hourly_heat_demand_heating_kW = np.clip(hourly_heat_demand_heating_kW, 0, None)
        hourly_heat_demand_warmwater_kW = np.clip(hourly_heat_demand_warmwater_kW, 0, None)

        total_heat_W.append(hourly_heat_demand_total_kW * 1000)
        heating_heat_W.append(hourly_heat_demand_heating_kW * 1000)
        warmwater_heat_W.append(hourly_heat_demand_warmwater_kW * 1000)
        max_heat_requirement_W.append(np.max(hourly_heat_demand_total_kW * 1000))

    total_heat_W = np.array(total_heat_W)
    heating_heat_W = np.array(heating_heat_W)
    warmwater_heat_W = np.array(warmwater_heat_W)
    max_heat_requirement_W = np.array(max_heat_requirement_W)

    supply_temperature_curve, return_temperature_curve = calculate_temperature_curves(data, hourly_air_temperatures)

    return yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures

def calculate_temperature_curves(data, hourly_air_temperatures):
    """
    Calculate the supply and return temperature curves for buildings.

    Args:
        data (DataFrame): Input data containing building information.
        hourly_air_temperatures (array): Array of hourly air temperatures.

    Returns:
        tuple: Supply temperature curve and return temperature curve arrays.
    """
    supply_temperature_buildings = data["VLT_max"].values.astype(float)
    return_temperature_buildings = data["RLT_max"].values.astype(float)
    slope = -data["Steigung_Heizkurve"].values.astype(float)
    supply_temperature_curve = []
    return_temperature_curve = []

    dT = np.expand_dims(supply_temperature_buildings - return_temperature_buildings, axis=1)
    min_air_temperatures = data["Normaußentemperatur"].values.astype(float)

    for st, s, min_air_temperature in zip(supply_temperature_buildings, slope, min_air_temperatures):
        st_curve = np.where(hourly_air_temperatures <= min_air_temperature, st, st + (s * (hourly_air_temperatures - min_air_temperature)))
        supply_temperature_curve.append(st_curve)

    supply_temperature_curve = np.array(supply_temperature_curve)
    return_temperature_curve = supply_temperature_curve - dT

    return supply_temperature_curve, return_temperature_curve