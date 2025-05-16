"""
Filename: 08_example_complex_pandapipes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-13
Description: Script for testing the pandapipes net simulation functions. Aims to simulate a district heating network using GeoJSON files for the network layout and a JSON file for the building load profile. The script includes functions to create and initialize the network, perform time series calculations, and plot the results.
Usage: Run the script in the main directory of the repository.


"""

import matplotlib.pyplot as plt
import numpy as np

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import *
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import *
from districtheatingsim.net_simulation_pandapipes.utilities import *

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot

def create_and_initialize_net_geojson(vorlauf, ruecklauf, hast, erzeugeranlagen, json_path, supply_temperature_heat_consumer, 
                                          return_temperature_heat_consumer, supply_temperature, flow_pressure_pump, lift_pressure_pump, 
                                          netconfiguration, dT_RL, building_temp_checked, pipetype, v_max_pipe, material_filter, 
                                          DiameterOpt_ckecked, k_mm, main_producer_location_index, secondary_producers, COP_filename, TRY_filename):
        """
        Creates and initializes the network from GeoJSON files.

        Args:
            vorlauf: Path to the Vorlauf GeoJSON file.
            ruecklauf: Path to the Rücklauf GeoJSON file.
            hast: Path to the HAST GeoJSON file.
            erzeugeranlagen: Path to the Erzeugeranlagen GeoJSON file.
            json_path: Path to the JSON file.
            supply_temperature_heat_consumer: Supply temperature for heat consumers.
            return_temperature_heat_consumer: Return temperature for heat consumers.
            supply_temperature: Supply temperature for the network.
            flow_pressure_pump: Flow pressure of the pump.
            lift_pressure_pump: Lift pressure of the pump.
            netconfiguration: Network configuration.
            dT_RL: Temperature difference between supply and return lines.
            building_temp_checked: Flag indicating if building temperatures are considered.
            pipetype: Type of pipe.
            v_max_pipe: Maximum flow velocity in the pipes.
            material_filter: Material filter for pipes.
            DiameterOpt_ckecked: Flag indicating if diameter optimization is checked.
            k_mm: Roughness of the pipe.
        """

        results = (initialize_geojson(vorlauf, ruecklauf, hast, erzeugeranlagen, json_path, COP_filename, 
                          supply_temperature_heat_consumer, return_temperature_heat_consumer, supply_temperature, 
                          flow_pressure_pump, lift_pressure_pump, netconfiguration, pipetype, dT_RL, 
                          v_max_pipe, material_filter, k_mm, main_producer_location_index, secondary_producers))
            
        net, yearly_time_steps, waerme_hast_ges_W, return_temperature_heat_consumer, supply_temperature_buildings, \
        return_temperature_buildings, supply_temperature_buildings_curve, return_temperature_buildings_curve, \
            min_supply_temperature_heat_consumer, strombedarf_hast_ges_W, max_el_leistung_hast_ges_W = results

        # Common steps for both import types
        if DiameterOpt_ckecked == True:
            net = optimize_diameter_types(net, v_max_pipe, material_filter, k_mm)
        
        # This equals the return from the NetInitializationThread
        net_data = net, yearly_time_steps, waerme_hast_ges_W, supply_temperature_heat_consumer, supply_temperature, return_temperature_heat_consumer, supply_temperature_buildings, return_temperature_buildings, \
            supply_temperature_buildings_curve, return_temperature_buildings_curve, min_supply_temperature_heat_consumer, netconfiguration, dT_RL, building_temp_checked, strombedarf_hast_ges_W, \
            max_el_leistung_hast_ges_W, TRY_filename, COP_filename

        waerme_ges_kW = np.where(waerme_hast_ges_W == 0, 0, waerme_hast_ges_W / 1000)
        strombedarf_hast_ges_kW = np.where(strombedarf_hast_ges_W == 0, 0, strombedarf_hast_ges_W / 1000)
        max_el_leistung_hast_ges_W = max_el_leistung_hast_ges_W

        waerme_ges_kW = np.sum(waerme_ges_kW, axis=0)
        strombedarf_hast_ges_kW = np.sum(strombedarf_hast_ges_kW, axis=0)

        #plot(net, yearly_time_steps, waerme_ges_kW, strombedarf_hast_ges_kW)

        return net_data

def plot(net, time_steps, qext_kW, strom_kW):
    """
    Plots the network data.

    Args:
        time_steps: Array of time steps.
        qext_kW: Array of external heat demand in kW.
        strom_kW: Array of power demand in kW.
    """
    fig, ax1 = plt.subplots()

    if np.sum(strom_kW) == 0:
        ax1.plot(time_steps, qext_kW, 'b-', label="Gesamtheizlast Gebäude in kW")

    if np.sum(strom_kW) > 0:
        ax1.plot(time_steps, qext_kW+strom_kW, 'b-', label="Gesamtheizlast Gebäude in kW")
        ax1.plot(time_steps, strom_kW, 'g-', label="Gesamtstrombedarf Wärmepumpen Gebäude in kW")

    ax1.set_xlabel("Zeit")
    ax1.set_ylabel("Leistung in kW", color='b')
    ax1.tick_params('y', colors='b')
    ax1.legend(loc='upper center')
    ax1.grid()

    fig, ax2 = plt.subplots()

    config_plot(net, ax2, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_basemap=False, show_plot=True)

def timeseries_calculation_net(net_data, start=0, end=100, secondary_producers=None):
    net, yearly_time_steps, total_heat_W, supply_temperature_heat_consumer, supply_temperature, return_temperature_heat_consumer, supply_temperature_buildings, \
        return_temperature_buildings, supply_temperature_buildings_curve, return_temperature_buildings_curve, min_supply_temperature_heat_consumer, netconfiguration, dT_RL, building_temp_checked, \
        strombedarf_hast_ges_W, max_el_leistung_hast_ges_W, TRY_filename, COP_filename = net_data

    waerme_hast_ges_W, strom_hast_ges_W, supply_temperature_heat_consumer, return_temperature_heat_consumer = time_series_preprocessing(supply_temperature, supply_temperature_heat_consumer, \
                                                                                                    return_temperature_heat_consumer, supply_temperature_buildings, \
                                                                                                    return_temperature_buildings, building_temp_checked, \
                                                                                                    netconfiguration, total_heat_W, \
                                                                                                    return_temperature_buildings_curve, dT_RL, \
                                                                                                    supply_temperature_buildings_curve, COP_filename)

    return_temperature_heat_consumer = np.array([np.full(end - start, temp) for temp in return_temperature_heat_consumer])
    min_supply_temperature_heat_consumer = np.array([np.full(end - start, temp) for temp in min_supply_temperature_heat_consumer])

    time_steps, net, net_results = thermohydraulic_time_series_net(net, yearly_time_steps, waerme_hast_ges_W, start, \
                                                                    end, supply_temperature, min_supply_temperature_heat_consumer, \
                                                                    return_temperature_heat_consumer, secondary_producers)

    return (time_steps, net, net_results, waerme_hast_ges_W, strom_hast_ges_W)

def print_net_results(net):
    print("Netzdaten:")
    print(f"Junctions: {net.junction}")
    print(f"Results Junctions: {net.res_junction}")
    print(f"Pipes: {net.pipe}")
    print(f"Results Pipes: {net.res_pipe}")
    print(f"Heat Consumers: {net.heat_consumer}")
    print(f"Results Heat Consumers: {net.res_heat_consumer}")
    print(f"Circ Pump Pressure: {net.circ_pump_pressure}")
    print(f"Results Circ Pump Pressure: {net.res_circ_pump_pressure}")
    if 'circ_pump_mass' in net:
        print(f"Circ Pump Mass: {net.circ_pump_mass}")
        print(f"Results Circ Pump Mass: {net.res_circ_pump_mass}")

if __name__ == "__main__":
    #vorlauf_path = "examples/data/Wärmenetz/Variante 1/Vorlauf.geojson"
    #ruecklauf_path = "examples/data/Wärmenetz/Variante 1/Rücklauf.geojson"
    #hast_path = "examples/data/Wärmenetz/Variante 1/HAST.geojson"
    #erzeugeranlagen_path = "examples/data/Wärmenetz/Variante 1/Erzeugeranlagen.geojson"

    vorlauf_path = "examples/data/Wärmenetz/Variante 2/Vorlauf.geojson"
    ruecklauf_path = "examples/data/Wärmenetz/Variante 2/Rücklauf.geojson"
    hast_path = "examples/data/Wärmenetz/Variante 2/HAST.geojson"
    erzeugeranlagen_path = "examples/data/Wärmenetz/Variante 2/Erzeugeranlagen.geojson"

    json_path = "examples/data/Gebäude Lastgang.json"

    supply_temperature_heat_consumer = 60 # minimum supply temperature for heat consumers
    return_temperature_heat_consumer = 50 # return temperature for heat consumers

    supply_temperature = np.linspace(85, 70, 8760) # supply temperature for the network
    flow_pressure_pump = 4 # flow pressure of the pump
    lift_pressure_pump = 1.5 # lift pressure of the pump

    netconfiguration = "Niedertemperaturnetz" # network configuration ("kaltes Netz")

    dT_RL = 5 # temperature difference between heat consumer and net due to heat exchanger
    building_temp_checked = False # flag indicating if building temperatures are considered
    pipetype = "KMR 100/250-2v" # type of pipe
    v_max_pipe = 2 # maximum flow velocity in the pipes
    material_filter = "KMR" # material filter for pipes
    DiameterOpt_ckecked = True # flag indicating if diameter optimization is checked
    k_mm = 0.1 # roughness of the pipe

    secondary_producers = [{"index": 1, "percentage": 5}] # secondary producers with index and percentage
    main_producer_location_index = 0 # index of the main producer location
    #secondary_producers = None
    TRY_filename = "examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
    COP_filename = "examples/data/COP/Kennlinien WP.csv"

    net_data = create_and_initialize_net_geojson(vorlauf_path, ruecklauf_path, hast_path, erzeugeranlagen_path, json_path, supply_temperature_heat_consumer,
                                        return_temperature_heat_consumer, supply_temperature, flow_pressure_pump, lift_pressure_pump, netconfiguration, dT_RL,
                                        building_temp_checked, pipetype, v_max_pipe, material_filter, DiameterOpt_ckecked, k_mm, main_producer_location_index, 
                                        secondary_producers, COP_filename, TRY_filename)

    #print_net_results(net_data[0])

    #fig, ax2 = plt.subplots()
    #config_plot(net_data[0], ax2, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_basemap=False, show_plot=True)
    #plt.show()

    start_time_step = 0 # start time step
    end_time_step = 100 # end time step
    
    time_steps, net, net_results, waerme_hast_ges_W, strom_hast_ges_W = timeseries_calculation_net(net_data, start_time_step, end_time_step, secondary_producers=secondary_producers)

    waerme_ges_kW = (np.sum(waerme_hast_ges_W, axis=0)/1000)[start_time_step:end_time_step]
    strom_wp_kW = (np.sum(strom_hast_ges_W, axis=0)/1000)[start_time_step:end_time_step]

    pump_results = calculate_results(net, net_results)

    print_net_results(net)

    #print(f"Gesamtwärmebedarf: {waerme_ges_kW} kW")
    #print(f'Gesamtwärmeerzeugung: {pump_results["Heizentrale Haupteinspeisung"][0]["qext_kW"]} kW')
    
    print("Simulation erfolgreich abgeschlossen.")

    plot(net, time_steps, waerme_ges_kW, strom_wp_kW)