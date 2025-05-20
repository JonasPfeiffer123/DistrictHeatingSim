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

from districtheatingsim.gui.NetSimulationTab.NetworkDataClass import NetworkGenerationData

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
    main_producer_location_index = 0 # index of the main producer location
    secondary_producers = [{"index": 1, "percentage": 5}] # secondary producers with index and percentage
    import_type = "geoJSON" # type of import, currently only geoJSON
    supply_temperature_heat_consumer = 60 # minimum supply temperature for heat consumers
    return_temperature_heat_consumer = 50 # return temperature for heat consumers
    
    TRY_filename = "examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
    COP_filename = "examples/data/COP/Kennlinien WP.csv"

    NetworkGenerationData = NetworkGenerationData(
        flow_line_path=vorlauf_path,
        return_line_path=ruecklauf_path,
        heat_consumer_path=hast_path,
        heat_generator_path=erzeugeranlagen_path,
        heat_demand_json_path=json_path,
        supply_temperature_heat_generator=supply_temperature,
        flow_pressure_pump=flow_pressure_pump,
        lift_pressure_pump=lift_pressure_pump,
        netconfiguration=netconfiguration,
        dT_RL=dT_RL,
        building_temperature_checked=building_temp_checked,
        pipetype=pipetype,
        max_velocity_pipe=v_max_pipe,
        material_filter_pipe=material_filter,
        diameter_optimization_pipe_checked=DiameterOpt_ckecked,
        k_mm_pipe=k_mm,
        main_producer_location_index=main_producer_location_index,
        secondary_producers=secondary_producers,
        import_type=import_type,
        min_supply_temperature_building=supply_temperature_heat_consumer,
        fixed_return_temperature_heat_consumer=return_temperature_heat_consumer,
        COP_filename=COP_filename
    )

    NetworkGenerationData = initialize_geojson(NetworkGenerationData)      

    # Common steps for both import types
    if NetworkGenerationData.diameter_optimization_pipe_checked == True:
        NetworkGenerationData.net = optimize_diameter_types(NetworkGenerationData.net, NetworkGenerationData.max_velocity_pipe, NetworkGenerationData.material_filter_pipe, NetworkGenerationData.k_mm_pipe)
    
    NetworkGenerationData.start_time_step = 0
    NetworkGenerationData.end_time_step = 100
    #NetworkGenerationData.results_csv_filename = netCalcInputs["results_filename"]

    NetworkGenerationData = time_series_preprocessing(NetworkGenerationData)
            
    NetworkGenerationData = thermohydraulic_time_series_net(NetworkGenerationData)

    print("Simulation erfolgreich abgeschlossen.")

    print_net_results(NetworkGenerationData.net)
    plot(NetworkGenerationData.net, 
         NetworkGenerationData.yearly_time_steps_start_end, 
         NetworkGenerationData.waerme_ges_kW[NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step], 
         NetworkGenerationData.strombedarf_ges_kW[NetworkGenerationData.start_time_step:NetworkGenerationData.end_time_step])