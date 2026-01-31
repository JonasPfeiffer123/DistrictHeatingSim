"""
Filename: 08_example_complex_pandapipes_timeseries.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-01-12
Description: Script for testing the pandapipes net simulation functions. Aims to simulate a district heating network using GeoJSON files for the network layout and a JSON file for the building load profile. The script includes functions to create and initialize the network, perform time series calculations, and plot the results.
Usage: Run the script in the main directory of the repository.

Updated to work with the current NetworkGenerationData class structure.
"""

import matplotlib.pyplot as plt
import numpy as np

from districtheatingsim.net_simulation_pandapipes.pp_net_initialisation_geojson import *
from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import *
from districtheatingsim.net_simulation_pandapipes.utilities import *

from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot

from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import NetworkGenerationData, SecondaryProducer

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
    from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
    import tempfile
    
    # File paths - Load unified format
    unified_path = "examples/data/Wärmenetz/Variante 2/Wärmenetz.geojson"
    
    # Extract layers from unified format
    unified_geojson = NetworkGeoJSONSchema.import_from_file(unified_path)
    vorlauf_gdf, ruecklauf_gdf, hast_gdf, erzeuger_gdf = NetworkGeoJSONSchema.split_to_legacy_format(unified_geojson)
    
    # Save to temporary files for compatibility
    temp_dir = tempfile.mkdtemp()
    vorlauf_path = os.path.join(temp_dir, "vorlauf.geojson")
    ruecklauf_path = os.path.join(temp_dir, "ruecklauf.geojson")
    hast_path = os.path.join(temp_dir, "hast.geojson")
    erzeugeranlagen_path = os.path.join(temp_dir, "erzeuger.geojson")
    
    vorlauf_gdf.to_file(vorlauf_path, driver="GeoJSON")
    ruecklauf_gdf.to_file(ruecklauf_path, driver="GeoJSON")
    hast_gdf.to_file(hast_path, driver="GeoJSON")
    erzeuger_gdf.to_file(erzeugeranlagen_path, driver="GeoJSON")
    json_path = "examples/data/Gebäude Lastgang.json"
    
    # Optional external data files
    TRY_filename = "examples/data/TRY/TRY_511676144222/TRY2015_511676144222_Jahr.dat"
    COP_filename = "examples/data/COP/Kennlinien WP.csv"

    # Network configuration parameters
    netconfiguration = "Niedertemperaturnetz"  # or "kaltes Netz"
    supply_temperature_control = "Statisch"  # or "Gleitend"
    
    # Temperature control parameters
    max_supply_temperature_heat_generator = 85.0  # °C
    min_supply_temperature_heat_generator = 70.0  # °C (for sliding control)
    max_air_temperature_heat_generator = 15.0     # °C
    min_air_temperature_heat_generator = -12.0    # °C
    
    # Pump parameters
    flow_pressure_pump = 4.0      # bar
    lift_pressure_pump = 1.5      # bar
    
    # Building temperature parameters
    min_supply_temperature_building_checked = False
    min_supply_temperature_building = None # 60.0  # °C
    fixed_return_temperature_heat_consumer_checked = False
    fixed_return_temperature_heat_consumer = None # 50.0  # °C
    dT_RL = 5.0  # K - temperature difference between heat consumer and net due to heat exchanger
    building_temperature_checked = False  # flag indicating if building temperatures are considered
    
    # Pipe parameters
    pipetype = "KMR 100/250-2v"  # type of pipe
    diameter_optimization_pipe_checked = True  # flag indicating if diameter optimization is checked
    max_velocity_pipe = 2.0  # m/s - maximum flow velocity in the pipes
    material_filter_pipe = "KMR"  # material filter for pipes
    k_mm_pipe = 0.1  # mm - roughness of the pipe
    
    # Producer configuration
    main_producer_location_index = 0  # index of the main producer location
    #secondary_producers = []  # list of secondary producers, can be empty or contain multiple producers
    secondary_producers = [
        SecondaryProducer(index=1, load_percentage=5.0)  # secondary producer with 5% load
    ]
    
    # Import type
    import_type = "geoJSON"  # currently only geoJSON

    # Create NetworkGenerationData object with all required parameters
    network_data = NetworkGenerationData(
        # Required input data paths
        import_type=import_type,
        flow_line_path=vorlauf_path,
        return_line_path=ruecklauf_path,
        heat_consumer_path=hast_path,
        heat_generator_path=erzeugeranlagen_path,
        heat_demand_json_path=json_path,
        
        # Network configuration data
        netconfiguration=netconfiguration,
        supply_temperature_control=supply_temperature_control,
        max_supply_temperature_heat_generator=max_supply_temperature_heat_generator,
        min_supply_temperature_heat_generator=min_supply_temperature_heat_generator,
        max_air_temperature_heat_generator=max_air_temperature_heat_generator,
        min_air_temperature_heat_generator=min_air_temperature_heat_generator,
        flow_pressure_pump=flow_pressure_pump,
        lift_pressure_pump=lift_pressure_pump,
        min_supply_temperature_building_checked=min_supply_temperature_building_checked,
        min_supply_temperature_building=min_supply_temperature_building,
        fixed_return_temperature_heat_consumer_checked=fixed_return_temperature_heat_consumer_checked,
        fixed_return_temperature_heat_consumer=fixed_return_temperature_heat_consumer,
        dT_RL=dT_RL,
        building_temperature_checked=building_temperature_checked,
        pipetype=pipetype,
        
        # Optimization variables
        diameter_optimization_pipe_checked=diameter_optimization_pipe_checked,
        max_velocity_pipe=max_velocity_pipe,
        material_filter_pipe=material_filter_pipe,
        k_mm_pipe=k_mm_pipe,
        
        # Producer configuration
        main_producer_location_index=main_producer_location_index,
        secondary_producers=secondary_producers,
        
        # Optional external data files
        COP_filename=COP_filename,
        TRY_filename=TRY_filename
    )

    # Initialize network from GeoJSON data
    network_data = initialize_geojson(network_data)      

    # Optimize pipe diameters if requested
    if network_data.diameter_optimization_pipe_checked:
        network_data.net = optimize_diameter_types(
            network_data.net, 
            network_data.max_velocity_pipe, 
            network_data.material_filter_pipe, 
            network_data.k_mm_pipe
        )
    
    # Set simulation time range
    network_data.start_time_step = 0
    network_data.end_time_step = 100
    
    # Preprocess time series data
    network_data = time_series_preprocessing(network_data)
    
    # Run thermohydraulic time series simulation
    network_data = thermohydraulic_time_series_net(network_data)

    print("Simulation erfolgreich abgeschlossen.")

    # Print network results
    print_net_results(network_data.net)
    
    # Calculate and display key performance indicators
    results = network_data.calculate_results()
    print("\nKennzahlen:")
    for key, value in results.items():
        if value is not None:
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
        else:
            print(f"{key}: Nicht verfügbar")
    
    # Prepare plot data
    network_data.prepare_plot_data()
    
    # Plot results
    plot(network_data.net, 
         network_data.yearly_time_steps[network_data.start_time_step:network_data.end_time_step], 
         network_data.waerme_ges_kW[network_data.start_time_step:network_data.end_time_step], 
         network_data.strombedarf_ges_kW[network_data.start_time_step:network_data.end_time_step])
    
    # Show additional plots using prepared plot data
    if network_data.plot_data:
        print("\nVerfügbare Plot-Daten:")
        for key in network_data.plot_data.keys():
            print(f"  - {key}")
        
        # Example: Plot heat demand over time
        heat_demand_data = network_data.plot_data["Gesamtwärmebedarf Wärmeübertrager"]
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(heat_demand_data['time'], heat_demand_data['data'], 'b-')
        ax.set_xlabel('Zeit')
        ax.set_ylabel(heat_demand_data['label'])
        ax.set_title('Wärmebedarf über Zeit')
        ax.grid(True)
        plt.show()

    plt.show()