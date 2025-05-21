"""
Filename: 18_stanet_to_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-21
Description: This script demonstrates how to use the `create_net_from_stanet_csv` function from the `feature_develop.stanet_import_pandapipes` module.

"""

from stanet_import_pandapipes import create_net_from_stanet_csv
import pandapipes as pp

if __name__ == "__main__":
    # Example usage
    stanet_csv_file_path= "examples/data/STANET/Example_STANET_ETRS89.CSV"
    TRY_file_path = "examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
    supply_temperature = 80  # Supply temperature in Celsius
    flow_pressure_pump = 4.0  # Flow pressure of the pump in bar
    lift_pressure_pump = 1.5  # Lift pressure of the pump in bar

    net, yearly_time_steps, total_heat_W, max_heat_requirement_W = create_net_from_stanet_csv(stanet_csv_file_path, TRY_file_path, supply_temperature, flow_pressure_pump, lift_pressure_pump)