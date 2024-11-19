"""
Filename: 04_example_data_heat_requirement.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Contains the heat requirement functions necessary to calculate the heat requirement of a building.
Usage:
    Run this script directly to calculate the heat requirement of a building.
Functions:
    calculation() -> None
        Calculates the heat requirement according to the given data.
Example:
    $ python 04_example_data_heat_requirement.py

"""

import traceback
import matplotlib.pyplot as plt
import pandas as pd

from districtheatingsim.heat_requirement import heat_requirement_calculation_csv

def calculation(data, TRY, calc_method):
    yearly_time_steps, total_heat_W, heating_heat_W, warmwater_heat_W, max_heat_requirement_W, supply_temperature_curve, return_temperature_curve, hourly_air_temperatures = heat_requirement_calculation_csv.generate_profiles_from_csv(data, TRY, calc_method)
    
    print("Ergebnisse")
    print(f"Jährliche Zeitschritte: {yearly_time_steps}")
    print(f"Gesamtwärmebedarf: {total_heat_W}")
    print(f"Wärmebedarf für Heizung: {heating_heat_W}")
    print(f"Wärmebedarf für Warmwasser: {warmwater_heat_W}")
    print(f"Maximaler Wärmebedarf: {max_heat_requirement_W}")
    print(f"Vorlauftemperaturkurve: {supply_temperature_curve}")
    print(f"Rücklauftemperaturkurve: {return_temperature_curve}")
    print(f"Stündliche Außentemperaturen: {hourly_air_temperatures}")

    # Plotting each element as they are 2-dimensional arrays
    fig, axs = plt.subplots(3, 1, figsize=(10, 15))

    # Plot total heat requirement
    for i in range(total_heat_W.shape[0]):
        axs[0].plot(yearly_time_steps, total_heat_W[i, :], label=f"Gesamtwärmebedarf {i+1}")
    axs[0].set_xlabel("Zeitschritte")
    axs[0].legend()

    # Plot supply and return temperature curves
    for i in range(supply_temperature_curve.shape[0]):
        axs[1].plot(yearly_time_steps, supply_temperature_curve[i, :], label=f"Vorlauftemperatur {i+1}")
        axs[1].plot(yearly_time_steps, return_temperature_curve[i, :], label=f"Rücklauftemperatur {i+1}")
    axs[1].set_xlabel("Zeitschritte")
    axs[1].legend()

    # Plot hourly air temperatures
    axs[2].plot(yearly_time_steps, hourly_air_temperatures, label=f"Außentemperatur")
    axs[2].set_xlabel("Zeitschritte")
    axs[2].legend()

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    try:
        print("Running the heat requirement script.")
        
        data = pd.read_csv("examples/data/data_ETRS89.csv", sep=";")
        TRY_filename = "src/districtheatingsim/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
        calc_method = "Datensatz"

        print(f"Data: {data}")

        # if data in column "Subtyp" is just one digit, add a leading zero
        data["Subtyp"] = data["Subtyp"].apply(lambda x: f"0{x}" if len(str(x)) == 1 else x)

        calculation(data, TRY_filename, calc_method)

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        raise e