"""
Filename: 03_example_heat_requirement.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-18
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

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import traceback

from src.districtheatingsim.heat_requirement import heat_requirement_BDEW
from src.districtheatingsim.heat_requirement import heat_requirement_VDI4655

# Berechnung mit BDEW-SLPs
def VDI4655():
    YEU_heating_kWh = 20000
    YEU_hot_water_kWh = 4000
    YEU_electricity_kWh = 10000
    building_type = "MFH"
    number_people_household = 2
    year = 2019
    climate_zone = "9"
    TRY = None # need fix
    holidays = None # need fix

    time_15min, electricity_kW, heating_kW, hot_water_kW, total_heat_kW, temperature = heat_requirement_VDI4655.calculate(YEU_heating_kWh, YEU_hot_water_kWh, YEU_electricity_kWh, building_type, number_people_household, year, climate_zone, TRY, holidays)

    print("Ergebnisse VDI 4655")
    print(f"Zeitschritte: {time_15min}")
    print(f"Strombedarf: {electricity_kW}")    
    print(f"Wärmebedarf Heizung: {heating_kW}")
    print(f"Wärmebedarf Warmwasser: {hot_water_kW}")
    print(f"Wärmebedarf Gesamt: {total_heat_kW}")
    print(f"Temperaturen: {temperature}")

# Berechnung nach VDI 4655 (Referenzlastprofile)
def BDEW():
    YEU_heating_kWh = 20000
    building_type = "HMF"
    subtype = "03"
    TRY = None # need fix
    year = 2021
    real_ww_share = 0.3

    hourly_intervals, hourly_heat_demand, hourly_temperature = heat_requirement_BDEW.calculate(YEU_heating_kWh, building_type, subtype, TRY, year, real_ww_share)

    print("Ergebnisse VDI 4655")
    print(f"Zeitschritte: {hourly_intervals}")
    print(f"Wärmebedarf Gesamt: {hourly_heat_demand}")    
    print(f"Temperaturen: {hourly_temperature}")

if __name__ == '__main__':
    try:
        print("Running the heat requirement script.")
        
        VDI4655()
        BDEW()
    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e