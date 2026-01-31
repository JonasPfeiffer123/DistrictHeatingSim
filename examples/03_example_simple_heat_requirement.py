"""
Filename: 03_example_heat_requirement.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Contains the heat requirement functions necessary to calculate the heat requirement of a building.
Usage:
    Run this script directly to calculate the heat requirement of a building.
Functions:
    VDI4655() -> None
        Calculates the heat requirement according to VDI 4655.
    BDEW() -> None
        Calculates the heat requirement according to BDEW.
Example:
    $ python simple_heat_requirement_test.py

"""

import traceback
import numpy as np
import matplotlib.pyplot as plt

from districtheatingsim.heat_requirement import heat_requirement_BDEW
from districtheatingsim.heat_requirement import heat_requirement_VDI4655

# Berechnung mit VDI 4655 (Referenzlastprofile)
def VDI4655(TRY_filename):
    YEU_heating_kWh = 20000
    YEU_hot_water_kWh = 4000
    YEU_electricity_kWh = 10000
    building_type = "MFH"

    # folgendes wird statisch gesetzt, muss in Zukunft noch in config-Datei ausgelagert werden oder im UI einstellbar sein
    year = 2021 # Jahr, für das die Berechnung durchgeführt wird (für VDI 4655, BDEW)
    holidays = np.array(["2021-01-01", "2021-04-02", "2021-04-05", "2021-05-01", "2021-05-24", "2021-05-13", 
                         "2021-06-03", "2021-10-03", "2021-11-01", "2021-12-25", "2021-12-26"]).astype('datetime64[D]') # Feiertage in Deutschland 2021 (ohne Wochenenden) als datetime64[D]-Array (YYYY-MM-DD) für VDI 4655
    climate_zone = "9"  # Klimazone 9: Deutschland (VDI 4655)
    number_people_household = 2  # Anzahl der Personen im Haushalt (VDI 4655)

    time_15min, total_heat_kW, heating_kW, hot_water_kW, temperature, electricity_kW = heat_requirement_VDI4655.calculate(YEU_heating_kWh, YEU_hot_water_kWh, YEU_electricity_kWh, building_type, number_people_household, year, climate_zone, TRY_filename, holidays)

    print("Ergebnisse VDI 4655")
    print(f"Zeitschritte: {time_15min}")
    print(f"Strombedarf: {electricity_kW}")    
    print(f"Wärmebedarf Heizung: {heating_kW}")
    print(f"Wärmebedarf Warmwasser: {hot_water_kW}")
    print(f"Wärmebedarf Gesamt: {total_heat_kW}")
    print(f"Temperaturen: {temperature}")

    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax2 = ax1.twinx()
    ax1.plot(time_15min, total_heat_kW, 'g-', label="Gesamt", linewidth=0.5)
    ax1.plot(time_15min, heating_kW, 'b-', label="Heizung", linewidth=0.5)
    ax1.plot(time_15min, hot_water_kW, 'r-', label="Warmwasser", linewidth=0.5)
    ax1.plot(time_15min, electricity_kW, 'm-', label="Strombedarf", linewidth=0.5)
    
    # temperature is hourly, so we need to repeat the values for the 15min intervals
    temperature = np.repeat(temperature, 4)
    ax2.plot(time_15min, temperature, 'k-', label="Außentemperatur", linewidth=0.5)

    ax1.set_xlabel("Zeitschritte")
    ax1.set_ylabel("Wärmebedarf (kW)")
    ax2.set_ylabel("Temperatur (°C)")

    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

# Berechnung nach BDEW
def BDEW(TRY_filename):
    YEU_heating_kWh = 20000
    building_type = "HMF"
    subtype = "03"
    real_ww_share = 0.3

    year = 2021

    hourly_intervals, hourly_heat_demand_total_normed, hourly_heat_demand_heating_normed, hourly_heat_demand_warmwater_normed, hourly_temperature = heat_requirement_BDEW.calculate(YEU_heating_kWh, building_type, subtype, TRY_filename, year, real_ww_share)

    print("Ergebnisse BDEW")
    print(f"Zeitschritte: {hourly_intervals}")
    print(f"Wärmebedarf Gesamt: {hourly_heat_demand_total_normed}") 
    print(f"Wärmebedarf Heizung: {hourly_heat_demand_heating_normed}")
    print(f"Wärmebedarf Warmwasser: {hourly_heat_demand_warmwater_normed}")  
    print(f"Temperaturen: {hourly_temperature}")

    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax2 = ax1.twinx()
    ax1.plot(hourly_intervals, hourly_heat_demand_total_normed, 'g-', label="Gesamt", linewidth=0.5)
    ax1.plot(hourly_intervals, hourly_heat_demand_heating_normed, 'b-', label="Heizung", linewidth=0.5)
    ax1.plot(hourly_intervals, hourly_heat_demand_warmwater_normed, 'r-', label="Warmwasser", linewidth=0.5)
    ax2.plot(hourly_intervals, hourly_temperature, 'k-', label="Außentemperatur", linewidth=0.5)

    ax1.set_xlabel("Zeitschritte")
    ax1.set_ylabel("Wärmebedarf (kW)")
    ax2.set_ylabel("Temperatur (°C)")

    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

if __name__ == '__main__':
    try:
        print("Running the heat requirement script.")

        TRY_filename = "src/districtheatingsim/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
        
        VDI4655(TRY_filename)
        BDEW(TRY_filename)

        plt.show()

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e