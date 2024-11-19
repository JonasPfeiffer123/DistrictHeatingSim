"""
Filename: 07_example_complex_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Script for testing the pandapipes net simulation functions.
Usage: Run the script in the main directory of the repository.
Functions:
    * initialize_net_geojson: Initializes a pandapipes network from geojson files and optimizes the network.
    * initialize_net_geojson2: Initializes a pandapipes network from geojson files and optimizes the network.
Usage:
    $ python 07_example_complex_pandapipes.py

"""

# needs fixes due to updated functions

import time
import logging

import matplotlib.pyplot as plt
import numpy as np
from pandapipes.control.run_control import run_control

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import *
from districtheatingsim.net_simulation_pandapipes.utilities import *

### hier noch weitere Tests mit der geojson-basierten Erstellungsmethode ###
# Example
def initialize_net_geojson():
    base_path = "examples\data"
    gdf_flow_line = gpd.read_file(f"{base_path}\Wärmenetz\Vorlauf.geojson", driver='GeoJSON')
    gdf_return_line = gpd.read_file(f"{base_path}\Wärmenetz\Rücklauf.geojson", driver='GeoJSON')
    gdf_heat_exchanger = gpd.read_file(f"{base_path}\Wärmenetz\HAST.geojson", driver='GeoJSON')
    gdf_heat_producer = gpd.read_file(f"{base_path}\Wärmenetz\Erzeugeranlagen.geojson", driver='GeoJSON')

    # Set a fixed random seed for reproducibility
    np.random.seed(42)

    #return_temperature = return_temperature_building_curve
    qext_w = np.random.randint(500, 1000000, size=len(gdf_heat_exchanger))
    return_temperature = np.random.randint(30, 60, size=len(gdf_heat_exchanger))

    v_max_pipe = 1
    v_max_heat_exchanger = 2
    
    # net generation from gis data
    net = create_network(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, return_temperature, supply_temperature=85, flow_pressure_pump=4, lift_pressure_pump=2, 
                        pipetype="KMR 100/250-2v",  pipe_creation_mode="type", v_max_heat_consumer=v_max_heat_exchanger, v_max_pipe=v_max_pipe, material_filter="KMR", insulation_filter="2v")
    
    run_control(net, mode="all")

    logging.info("Starting pipe optimization")
    start_time = time.time()
    net = optimize_diameter_types(net, v_max=v_max_pipe, material_filter="KMR", insulation_filter="2v")
    logging.info(f"Pipe optimization finished in {time.time() - start_time:.2f} seconds")

    logging.info("Starting heat consumer optimization")
    start_time = time.time()
    net = optimize_diameter_parameters(net, element="heat_consumer", v_max=v_max_heat_exchanger)
    logging.info(f"Heat consumer optimization finished in {time.time() - start_time:.2f} seconds")

    # recalculate maximum and minimum mass flows in the controller
    net = recalculate_all_mass_flow_limits(net)

    run_control(net, mode="all")

    fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse
    # heat_consumer doesnt work at this point
    config_plot(net, ax, show_junctions=True, show_pipes=True,  show_heat_consumers=True, show_pump=True, show_plot=True)

    return net

def initialize_net_geojson2():
    base_path = "examples\data"
    vorlauf = f"{base_path}\Wärmenetz\Vorlauf.geojson"
    ruecklauf = f"{base_path}\Wärmenetz\Rücklauf.geojson"
    hast = f"{base_path}\Wärmenetz\HAST.geojson"
    erzeugeranlagen = f"{base_path}\Wärmenetz\Erzeugeranlagen.geojson"

    calc_method = "Datensatz" 
    #calc_method = "BDEW"
    #calc_method = "VDI4655"
    building_type = None
    #return_temperature_heat_consumer = None # 60, Erklärung
    return_temperature_heat_consumer = 55 # 60, Erklärung
    supply_temperature_net = 85 # alternative ist Gleitende Temperatur
    #supply_temperature = np.array([...]) # alternative ist Gleitende Temperatur
    min_supply_temperature_building = 65
    flow_pressure_pump = 4
    lift_pressure_pump = 1.5
    netconfiguration = "Niedertemperaturnetz"
    #netconfiguration = "wechselwarmes Netz"
    #netconfiguration = "kaltes Netz"
    pipetype = "KMR 100/250-2v"
    dT_RL = 5
    v_max_pipe = 1
    material_filter = "KMR"
    insulation_filter = "2v"
    v_max_heat_consumer = 1.5
    mass_flow_secondary_producers = 0.1 #placeholder
    TRY_filename = f"{base_path}\TRY\TRY_511676144222\TRY2015_511676144222_Jahr.dat"
    COP_filename = f"{base_path}\COP\Kennlinien WP.csv"

    net, yearly_time_steps, waerme_hast_ges_W, return_temperature_heat_consumer, supply_temperature_buildings, return_temperature_buildings, \
        supply_temperature_building_curve, return_temperature_building_curve, strombedarf_hast_ges_W, max_el_leistung_hast_ges_W = initialize_geojson(vorlauf, ruecklauf, hast, erzeugeranlagen, \
                                                                                TRY_filename, COP_filename, calc_method, building_type, \
                                                                                min_supply_temperature_building, return_temperature_heat_consumer, \
                                                                                supply_temperature_net, flow_pressure_pump, lift_pressure_pump, \
                                                                                netconfiguration, pipetype, dT_RL, v_max_pipe, material_filter, \
                                                                                insulation_filter, v_max_heat_consumer, mass_flow_secondary_producers)
    
    net = net_optimization(net, v_max_pipe, v_max_heat_consumer, material_filter, insulation_filter)

    fig, ax = plt.subplots()  # Erstelle eine Figure und eine Achse
    # heat_consumer doesnt work at this point
    config_plot(net, ax, show_junctions=True, show_pipes=True,  show_heat_consumers=True, show_pump=True, show_plot=True)

    return net

if __name__ == "__main__":
    initialize_net_geojson()
    initialize_net_geojson2()