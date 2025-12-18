"""
Pandapipes Network Initialization Module
=========================================

This module provides comprehensive network initialization capabilities for district heating
systems using GeoJSON-based geographic data.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-17

It handles the complete workflow from GeoJSON
data processing to pandapipes network creation, including heat demand integration, temperature
calculation, and multi-producer system configuration.

The module supports various network configurations including traditional hot water networks,
cold networks with decentralized heat pumps, and hybrid systems with multiple heat generators.
It automatically processes building heat demands, calculates temperature requirements, and
creates appropriate network topologies with proper controller configurations.
"""

import numpy as np
import geopandas as gpd
import pandapipes as pp
import json
import pandas as pd
from typing import Dict, List, Tuple, Union, Any

from pandapipes.control.run_control import run_control

from districtheatingsim.net_simulation_pandapipes.utilities import create_controllers, correct_flow_directions, COP_WP, init_diameter_types

def initialize_geojson(NetworkGenerationData) -> Any:
    """
    Initialize the district heating network using GeoJSON data and configuration parameters.

    This function orchestrates the complete network initialization workflow including
    GeoJSON data loading, heat demand processing, temperature calculations, network
    topology creation, and controller setup. It handles different network configurations
    and automatically calculates derived parameters for simulation.

    Parameters
    ----------
    NetworkGenerationData : object
        Network generation data object containing all necessary parameters including:
        
        - **GeoJSON file paths** : Paths to flow lines, return lines, heat consumers, and producers
        - **Heat demand data** : JSON file with building heat demands and temperature profiles  
        - **Network configuration** : Type of network (traditional, cold network, hybrid)
        - **Temperature parameters** : Supply/return temperatures and control strategies
        - **Pipe specifications** : Pipe types, materials, and hydraulic parameters
        - **Producer configuration** : Main and secondary heat generator specifications

    Returns
    -------
    NetworkGenerationData
        Updated NetworkGenerationData object with initialized network and calculated parameters:
        
        - **net** : pandapipes network object ready for simulation
        - **Time series data** : Processed heat demands and temperature profiles
        - **Network parameters** : Calculated mass flows, temperatures, and system configuration
        - **Building data** : Processed building heat demands and characteristics

    Raises
    ------
    FileNotFoundError
        If any of the required GeoJSON or JSON files cannot be found.
    ValueError
        If temperature constraints are violated (return > supply temperature).
    KeyError
        If required data fields are missing from the heat demand JSON file.
    gpd.errors.DataSourceError
        If GeoJSON files are corrupted or have invalid format.

    Notes
    -----
    Network Configuration Types:
        - **"kaltes Netz"** : Cold network with decentralized heat pumps
        - **Traditional** : Hot water network with central heat generation
        - **Hybrid** : Mixed systems with multiple heat sources

    Temperature Processing:
        - Validates temperature constraints (return < supply)
        - Calculates heat pump performance for cold networks
        - Applies minimum load constraints (2% of maximum)
        - Processes time-dependent temperature profiles

    Mass Flow Calculations:
        - Main producer: Based on total heat demand and temperature difference
        - Secondary producers: Percentage-based distribution of total flow
        - Uses water properties (cp = 4.18 kJ/kg·K)

    Examples
    --------
    >>> # Initialize network from GeoJSON data
    >>> network_data = initialize_geojson(config_data)
    >>> print(f"Created network with {len(network_data.net.heat_consumer)} consumers")
    >>> print(f"Total heat demand: {np.sum(network_data.waerme_ges_kW):.1f} kW")
    
    >>> # Access network components
    >>> net = network_data.net
    >>> print(f"Junctions: {len(net.junction)}")
    >>> print(f"Pipes: {len(net.pipe)}")
    >>> print(f"Heat consumers: {len(net.heat_consumer)}")

    See Also
    --------
    create_network : Creates the pandapipes network topology
    COP_WP : Heat pump coefficient of performance calculation
    create_controllers : Adds control systems to the network
    """
    # Load GeoJSON data for network topology
    gdf_dict = {
        "flow_line": gpd.read_file(NetworkGenerationData.flow_line_path, driver='GeoJSON'),
        "return_line": gpd.read_file(NetworkGenerationData.return_line_path, driver='GeoJSON'),
        "heat_consumer": gpd.read_file(NetworkGenerationData.heat_consumer_path, driver='GeoJSON'),
        "heat_producer": gpd.read_file(NetworkGenerationData.heat_generator_path, driver='GeoJSON')
    }

    print(f"Max supply temperature heat generator: {NetworkGenerationData.max_supply_temperature_heat_generator} °C")
    
    # Load and process heat demand data
    with open(NetworkGenerationData.heat_demand_json_path, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
        results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'wärme' in v}
        heat_demand_df = pd.DataFrame.from_dict({k: v for k, v in loaded_data.items() if k.isdigit()}, orient='index')

    # Extract building temperature data
    supply_temperature_buildings = heat_demand_df["VLT_max"].values.astype(float)
    return_temperature_buildings = heat_demand_df["RLT_max"].values.astype(float)

    # Extract time series data
    yearly_time_steps = np.array(heat_demand_df["zeitschritte"].values[0]).astype(np.datetime64)
    total_building_heat_demand_W = np.array([results[str(i)]["wärme"] for i in range(len(results))])*1000
    total_building_heating_demand_W = np.array([results[str(i)]["heizwärme"] for i in range(len(results))])*1000
    total_building_hot_water_demand_W = np.array([results[str(i)]["warmwasserwärme"] for i in range(len(results))])*1000
    supply_temperature_building_curve = np.array([results[str(i)]["vorlauftemperatur"] for i in range(len(results))])
    return_temperature_building_curve = np.array([results[str(i)]["rücklauftemperatur"] for i in range(len(results))])
    maximum_building_heat_load_W = np.array(results["0"]["max_last"])*1000

    print(f"Max heat demand buildings (W): {maximum_building_heat_load_W}")

    # Calculate return temperature for heat consumers
    if NetworkGenerationData.fixed_return_temperature_heat_consumer == None:
        return_temperature_heat_consumer = return_temperature_buildings + NetworkGenerationData.dT_RL
        print(f"Return temperature heat consumers: {return_temperature_heat_consumer} °C")
    else:
        return_temperature_heat_consumer = np.full_like(return_temperature_buildings, NetworkGenerationData.fixed_return_temperature_heat_consumer)
        print(f"Return temperature heat consumers: {return_temperature_heat_consumer} °C")

    # Validate temperature constraints
    if np.any(return_temperature_heat_consumer >= NetworkGenerationData.max_supply_temperature_heat_generator):
        raise ValueError("Return temperature must not be higher than the supply temperature at the injection point. Please check your inputs.")
    
    # Calculate minimum supply temperature for heat consumers
    if NetworkGenerationData.min_supply_temperature_building == None:
        min_supply_temperature_heat_consumer = np.zeros_like(supply_temperature_buildings, NetworkGenerationData.min_supply_temperature_building)
        print(f"Minimum supply temperature heat consumers: {min_supply_temperature_heat_consumer} °C")
    else:
        min_supply_temperature_heat_consumer = np.full_like(supply_temperature_buildings, NetworkGenerationData.min_supply_temperature_building + NetworkGenerationData.dT_RL)
        print(f"Minimum supply temperature heat consumers: {min_supply_temperature_heat_consumer} °C")
    
    # Validate minimum supply temperature constraints
    if np.any(min_supply_temperature_heat_consumer >= NetworkGenerationData.max_supply_temperature_heat_generator):
        raise ValueError("Supply temperature at the heat consumer cannot be higher than the supply temperature at the injection point. Please check your inputs.")

    # Initialize heat and power arrays
    waerme_hast_ges_W = []
    max_waerme_hast_ges_W = []
    strombedarf_hast_ges_W = []
    max_el_leistung_hast_ges_W = []

    # Process heat demands based on network configuration
    if NetworkGenerationData.netconfiguration == "kaltes Netz":
        # Cold network: Calculate heat pump performance
        COP_file_values = np.genfromtxt(NetworkGenerationData.COP_filename, delimiter=';')
        COP, _ = COP_WP(supply_temperature_buildings, return_temperature_heat_consumer, COP_file_values)
        print(f"COP dezentrale Wärmepumpen Gebäude: {COP}")

        # Calculate heat pump electricity consumption and network heat demand
        for waerme_gebaeude, leistung_gebaeude, cop in zip(total_building_heat_demand_W, maximum_building_heat_load_W, COP):
            strombedarf_wp = waerme_gebaeude/cop
            waerme_hast = waerme_gebaeude - strombedarf_wp
            waerme_hast_ges_W.append(waerme_hast)
            strombedarf_hast_ges_W.append(strombedarf_wp)

            el_leistung_wp = leistung_gebaeude/cop
            waerme_leistung_hast = leistung_gebaeude - el_leistung_wp
            max_waerme_hast_ges_W.append(waerme_leistung_hast)
            max_el_leistung_hast_ges_W.append(el_leistung_wp)

        waerme_hast_ges_W = np.array(waerme_hast_ges_W)
        max_waerme_hast_ges_W = np.array(max_waerme_hast_ges_W)
        strombedarf_hast_ges_W = np.array(strombedarf_hast_ges_W)
        max_el_leistung_hast_ges_W = np.array(max_el_leistung_hast_ges_W)
    else:
        # Traditional network: Direct heat transfer
        waerme_hast_ges_W = total_building_heat_demand_W
        max_waerme_hast_ges_W = maximum_building_heat_load_W
        strombedarf_hast_ges_W = np.zeros_like(total_building_heat_demand_W)
        max_el_leistung_hast_ges_W = np.zeros_like(maximum_building_heat_load_W)

    # Prepare data dictionaries for network creation
    consumer_dict = {
        "qext_w": max_waerme_hast_ges_W,
        "min_supply_temperature_heat_consumer": min_supply_temperature_heat_consumer,
        "return_temperature_heat_consumer": return_temperature_heat_consumer
    }

    pipe_dict = {
        "pipetype": NetworkGenerationData.pipetype,
        "v_max_pipe": NetworkGenerationData.max_velocity_pipe,
        "material_filter": NetworkGenerationData.material_filter_pipe,
        "pipe_creation_mode": "type",
        "k_mm": NetworkGenerationData.k_mm_pipe
    }

    # Calculate mass flows for secondary producers
    if NetworkGenerationData.secondary_producers:
        cp = 4.18  # kJ/kgK - specific heat capacity of water
        print(f"Specific heat capacity of water: {cp} kJ/kgK")
        print(f"maximum_building_heat_load_W: {maximum_building_heat_load_W}")
        sum_maximum_building_heat_load_W = np.sum(maximum_building_heat_load_W)
        print(f"sum_maximum_building_heat_load_W: {sum_maximum_building_heat_load_W}")
        print(f"Max supply temperature heat generator: {NetworkGenerationData.max_supply_temperature_heat_generator} °C")
        print(f"Return temperature heat consumer: {np.average(return_temperature_heat_consumer)} °C")
        mass_flow = (sum_maximum_building_heat_load_W / 1000) / (cp * (NetworkGenerationData.max_supply_temperature_heat_generator - np.average(return_temperature_heat_consumer)))

        print(f"Mass flow of main producer: {mass_flow} kg/s")

        for secondary_producer in NetworkGenerationData.secondary_producers:
            secondary_producer.mass_flow = secondary_producer.load_percentage/100 * mass_flow
            print(f"Mass flow of secondary producer {secondary_producer.index}: {secondary_producer.mass_flow} kg/s")

    producer_dict = {
        "supply_temperature": NetworkGenerationData.max_supply_temperature_heat_generator,
        "flow_pressure_pump": NetworkGenerationData.flow_pressure_pump,
        "lift_pressure_pump": NetworkGenerationData.lift_pressure_pump,
        "main_producer_location_index": NetworkGenerationData.main_producer_location_index,
        "secondary_producers": NetworkGenerationData.secondary_producers
    }

    # Create the pandapipes network
    net = create_network(gdf_dict, consumer_dict, pipe_dict, producer_dict)

    # Store processed data in NetworkGenerationData object
    NetworkGenerationData.supply_temperature_buildings = supply_temperature_buildings
    NetworkGenerationData.return_temperature_buildings = return_temperature_buildings
    NetworkGenerationData.supply_temperature_building_curve = supply_temperature_building_curve
    NetworkGenerationData.return_temperature_building_curve = return_temperature_building_curve
    NetworkGenerationData.yearly_time_steps = yearly_time_steps
    NetworkGenerationData.waerme_gebaeude_ges_W = total_building_heat_demand_W
    NetworkGenerationData.heizwaerme_gebaeude_ges_W = total_building_heating_demand_W
    NetworkGenerationData.ww_waerme_gebaeude_ges_W = total_building_hot_water_demand_W
    NetworkGenerationData.max_waerme_gebaeude_ges_W = maximum_building_heat_load_W
    NetworkGenerationData.return_temperature_heat_consumer = return_temperature_heat_consumer
    NetworkGenerationData.min_supply_temperature_heat_consumer = min_supply_temperature_heat_consumer
    NetworkGenerationData.waerme_hast_ges_W = waerme_hast_ges_W
    NetworkGenerationData.strombedarf_hast_ges_W = strombedarf_hast_ges_W
    NetworkGenerationData.max_waerme_hast_ges_W = max_waerme_hast_ges_W
    NetworkGenerationData.max_el_leistung_hast_ges_W = max_el_leistung_hast_ges_W

    # Apply minimum load constraints (2% of maximum)
    max_heat = np.max(NetworkGenerationData.waerme_hast_ges_W)
    max_power = np.max(NetworkGenerationData.strombedarf_hast_ges_W)
    NetworkGenerationData.waerme_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_heat, NetworkGenerationData.waerme_hast_ges_W)
    NetworkGenerationData.strombedarf_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_power, NetworkGenerationData.strombedarf_hast_ges_W)

    # Convert to kW units
    NetworkGenerationData.waerme_hast_ges_kW = np.where(NetworkGenerationData.waerme_hast_ges_W == 0, 0, NetworkGenerationData.waerme_hast_ges_W / 1000)
    NetworkGenerationData.strombedarf_hast_ges_kW = np.where(NetworkGenerationData.strombedarf_hast_ges_W == 0, 0, NetworkGenerationData.strombedarf_hast_ges_W / 1000)

    # Calculate total system demands
    NetworkGenerationData.waerme_ges_kW = np.sum(NetworkGenerationData.waerme_hast_ges_kW, axis=0)
    NetworkGenerationData.strombedarf_ges_kW = np.sum(NetworkGenerationData.strombedarf_hast_ges_kW, axis=0)

    NetworkGenerationData.net = net

    return NetworkGenerationData
    
def get_line_coords_and_lengths(gdf: gpd.GeoDataFrame) -> Tuple[List[List[Tuple]], List[float]]:
    """
    Extract line coordinates and lengths from a GeoDataFrame.

    This function processes a GeoDataFrame containing LineString geometries and
    extracts coordinate pairs along with their calculated lengths. It validates
    geometry types and handles only valid LineString objects.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame containing line geometries (typically flow or return lines).
        Must contain LineString geometries in the 'geometry' column.

    Returns
    -------
    Tuple[List[List[Tuple]], List[float]]
        A tuple containing:
        
        - **all_line_coords** (List[List[Tuple]]) : List of coordinate sequences,
          where each sequence represents one line as [(x1,y1), (x2,y2), ...]
        - **all_line_lengths** (List[float]) : List of line lengths in the same
          order as coordinates, calculated using geodetic methods

    Notes
    -----
    - Only processes LineString geometries, skips other geometry types
    - Calculates lengths using GeoPandas' built-in length property
    - Prints warnings for non-LineString geometries
    - Coordinate order depends on the original GeoJSON projection

    Examples
    --------
    >>> # Process flow line coordinates
    >>> coords, lengths = get_line_coords_and_lengths(flow_line_gdf)
    >>> print(f"Found {len(coords)} lines with total length {sum(lengths):.1f}m")
    
    >>> # Access individual line data
    >>> first_line_coords = coords[0]  # [(x1,y1), (x2,y2)]
    >>> first_line_length = lengths[0]  # length in meters

    See Also
    --------
    get_all_point_coords_from_line_cords : Extract unique junction points
    create_pipes : Create pandapipes pipe elements
    """
    all_line_coords, all_line_lengths = [], []
    gdf['length'] = gdf.geometry.length
    
    for index, row in gdf.iterrows():
        line = row['geometry']
        
        if line.geom_type == 'LineString':
            coords = list(line.coords)
            length = row['length']
            all_line_coords.append(coords)
            all_line_lengths.append(length)
        else:
            print(f"Geometrie ist kein LineString: {line.geom_type}")

    return all_line_coords, all_line_lengths

def get_all_point_coords_from_line_cords(all_line_coords: List[List[Tuple]]) -> List[Tuple]:
    """
    Extract all unique point coordinates from line coordinate sequences.

    This function takes a list of line coordinate sequences and extracts all
    unique point coordinates, which are needed for creating network junctions.
    It automatically removes duplicates to ensure each junction is created only once.

    Parameters
    ----------
    all_line_coords : List[List[Tuple]]
        List of line coordinate sequences, where each sequence contains
        coordinate tuples [(x1,y1), (x2,y2), ...].

    Returns
    -------
    List[Tuple]
        List of unique point coordinates as tuples (x, y).
        Each coordinate represents a potential network junction location.

    Notes
    -----
    - Automatically removes duplicate coordinates using set operations
    - Maintains coordinate precision from original data
    - Order of returned coordinates is not guaranteed due to set conversion
    - Essential for creating proper network topology without duplicate junctions

    Examples
    --------
    >>> # Extract unique junction points
    >>> line_coords = [[(0,0), (1,0)], [(1,0), (2,0)], [(2,0), (2,1)]]
    >>> unique_points = get_all_point_coords_from_line_cords(line_coords)
    >>> print(f"Found {len(unique_points)} unique junction points")
    Found 4 unique junction points
    
    >>> # Points would be: [(0,0), (1,0), (2,0), (2,1)]

    See Also
    --------
    create_junctions_from_coords : Create pandapipes junctions from coordinates
    get_line_coords_and_lengths : Extract line data from GeoDataFrame
    """
    point_coords = [koordinate for paar in all_line_coords for koordinate in paar]
    unique_point_coords = list(set(point_coords))
    return unique_point_coords

def create_network(gdf_dict: Dict[str, gpd.GeoDataFrame], consumer_dict: Dict[str, Any], 
                  pipe_dict: Dict[str, Any], producer_dict: Dict[str, Any]) -> pp.pandapipesNet:
    """
    Create the complete pandapipes network using GeoJSON data and configuration parameters.

    This function orchestrates the creation of a complete district heating network
    including junctions, pipes, heat consumers, and heat producers. It handles
    different pipe creation modes, multiple producer configurations, and applies
    network optimization algorithms.

    Parameters
    ----------
    gdf_dict : Dict[str, gpd.GeoDataFrame]
        Dictionary containing GeoDataFrames with keys:
        
        - "flow_line" : Supply line geometries
        - "return_line" : Return line geometries  
        - "heat_consumer" : Heat consumer locations
        - "heat_producer" : Heat producer locations
        
    consumer_dict : Dict[str, Any]
        Heat consumer configuration containing:
        
        - "qext_w" : External heat demands [W]
        - "min_supply_temperature_heat_consumer" : Minimum supply temperatures [°C]
        - "return_temperature_heat_consumer" : Return temperatures [°C]
        
    pipe_dict : Dict[str, Any]
        Pipe configuration parameters:
        
        - "pipetype" : Standard pipe type or diameter specification
        - "v_max_pipe" : Maximum allowable velocity [m/s]
        - "material_filter" : Pipe material filter criteria
        - "pipe_creation_mode" : Creation mode ("type" or "diameter")
        - "k_mm" : Pipe roughness [mm]
        
    producer_dict : Dict[str, Any]
        Heat producer configuration:
        
        - "supply_temperature" : Supply temperature [°C]
        - "flow_pressure_pump" : Pump outlet pressure [bar]
        - "lift_pressure_pump" : Pump pressure lift [bar]
        - "main_producer_location_index" : Index of main producer location
        - "secondary_producers" : List of secondary producer configurations

    Returns
    -------
    pp.pandapipesNet
        Complete pandapipes network object ready for simulation containing:
        
        - Junctions for all network nodes
        - Pipes for supply and return lines
        - Heat consumers with proper connections
        - Heat producers (main and secondary)
        - Controllers for system operation
        - Optimized pipe diameters

    Notes
    -----
    Network Creation Steps:
        1. Create junctions from unique coordinate points
        2. Create pipes connecting junctions (supply and return)
        3. Add heat consumers with thermal specifications
        4. Install heat producers (pressure and mass flow controlled)
        5. Run initial flow simulation for validation
        6. Add control systems and optimization

    Producer Types:
        - **Main producer** : Pressure-controlled circulation pump
        - **Secondary producers** : Mass flow-controlled circulation pumps
        - **Flow controls** : Additional flow regulation elements

    Optimization Features:
        - Automatic pipe diameter sizing based on velocity constraints
        - Flow direction correction for proper hydraulic operation
        - Controller integration for dynamic operation

    Examples
    --------
    >>> # Create network from processed data
    >>> network = create_network(geo_data, consumers, pipes, producers)
    >>> print(f"Created network with {len(network.junction)} junctions")
    >>> print(f"Supply pipes: {len([p for p in network.pipe.name if 'flow' in p])}")
    >>> print(f"Return pipes: {len([p for p in network.pipe.name if 'return' in p])}")

    See Also
    --------
    create_controllers : Add control systems to the network
    correct_flow_directions : Optimize flow directions
    init_diameter_types : Optimize pipe diameters
    pp.pipeflow : pandapipes flow simulation
    """
    # Extract data from dictionaries
    gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer = gdf_dict["flow_line"], gdf_dict["return_line"], gdf_dict["heat_consumer"], gdf_dict["heat_producer"]
    qext_w, min_supply_temperature_heat_consumer, return_temperature_heat_consumer = consumer_dict["qext_w"], consumer_dict["min_supply_temperature_heat_consumer"], consumer_dict["return_temperature_heat_consumer"]
    supply_temperature, flow_pressure_pump, lift_pressure_pump, main_producer_location_index, secondary_producers = producer_dict["supply_temperature"], producer_dict["flow_pressure_pump"], producer_dict["lift_pressure_pump"], producer_dict["main_producer_location_index"], producer_dict["secondary_producers"]
    pipetype, v_max_pipe, material_filter, pipe_creation_mode, k_mm = pipe_dict["pipetype"], pipe_dict["v_max_pipe"], pipe_dict["material_filter"], pipe_dict["pipe_creation_mode"], pipe_dict["k_mm"]

    # Create empty network and get pipe properties
    net = pp.create_empty_network(fluid="water")
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    properties = pipe_std_types.loc[pipetype]
    diameter_mm = properties['inner_diameter_mm']
    u_w_per_m2k_pipe = properties['u_w_per_m2k']

    # Convert temperatures to Kelvin
    supply_temperature_k = supply_temperature + 273.15
    return_temperature_heat_consumer_k = return_temperature_heat_consumer + 273.15

    def create_junctions_from_coords(net_i: pp.pandapipesNet, all_coords: List[Tuple]) -> Dict[Tuple, int]:
        """
        Create junctions in the network from coordinate points.

        Parameters
        ----------
        net_i : pp.pandapipesNet
            The pandapipes network object.
        all_coords : List[Tuple]
            List of coordinate tuples for junction locations.

        Returns
        -------
        Dict[Tuple, int]
            Dictionary mapping coordinates to junction IDs.
        """
        junction_dict = {}
        for i, coords in enumerate(all_coords, start=0):
            junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=supply_temperature_k, 
                                           name=f"Junction {i}", geodata=coords)
            junction_dict[coords] = junction_id
        return junction_dict

    def create_pipes(net_i: pp.pandapipesNet, all_line_coords: List[List[Tuple]], 
                    all_line_lengths: List[float], junction_dict: Dict[Tuple, int], 
                    pipe_mode: str, pipe_type_or_diameter: Union[str, float], line_type: str) -> None:
        """
        Create pipes in the network from line geometries.

        Parameters
        ----------
        net_i : pp.pandapipesNet
            The pandapipes network object.
        all_line_coords : List[List[Tuple]]
            List of line coordinate sequences.
        all_line_lengths : List[float]
            List of corresponding line lengths.
        junction_dict : Dict[Tuple, int]
            Dictionary mapping coordinates to junction IDs.
        pipe_mode : str
            Pipe creation mode ("type" or "diameter").
        pipe_type_or_diameter : Union[str, float]
            Pipe type name or diameter value.
        line_type : str
            Description of line type for naming.
        """
        for coords, length_m, i in zip(all_line_coords, all_line_lengths, range(len(all_line_coords))):
            if pipe_mode == "diameter":
                diameter_mm = pipe_type_or_diameter
                pp.create_pipe_from_parameters(net_i, from_junction=junction_dict[coords[0]],
                                            to_junction=junction_dict[coords[1]], length_km=length_m/1000,
                                            diameter_m=diameter_mm/1000, k_mm=k_mm, u_w_per_m2k=u_w_per_m2k_pipe, 
                                            name=f"{line_type} {i}", geodata=coords, sections=5, text_k=283)
            elif pipe_mode == "type":
                pp.create_pipe(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]],
                            std_type=pipe_type_or_diameter, length_km=length_m/1000, k_mm=k_mm, 
                            name=f"{line_type} {i}", geodata=coords, sections=5, text_k=283)

    def create_heat_consumers(net_i: pp.pandapipesNet, all_coords: List[List[Tuple]], 
                            junction_dict: Dict[Tuple, int], name_prefix: str) -> None:
        """Create heat consumers in the network."""
        for i, (coords, q, t) in enumerate(zip(all_coords, qext_w, return_temperature_heat_consumer_k)):
            pp.create_heat_consumer(net_i, from_junction=junction_dict[coords[0]], 
                                  to_junction=junction_dict[coords[1]], loss_coefficient=0, 
                                  qext_w=q, treturn_k=t, name=f"{name_prefix} {i}")

    def create_circulation_pump_pressure(net_i: pp.pandapipesNet, all_coords: List[List[Tuple]], 
                                       junction_dict: Dict[Tuple, int], name_prefix: str) -> None:
        """Create pressure-controlled circulation pumps."""
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                             p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                             t_flow_k=supply_temperature_k, type="auto",
                                             name=f"{name_prefix} {i}")
            
    def create_circulation_pump_mass_flow(net_i: pp.pandapipesNet, all_coords: List[List[Tuple]], 
                                        junction_dict: Dict[Tuple, int], name_prefix: str, 
                                        mass_flows: List[float]) -> None:
        """Create mass flow-controlled circulation pumps."""
        for i, (coords, mass_flow) in enumerate(zip(all_coords, mass_flows), start=0):
            mid_coord = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
            mid_junction_idx = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=supply_temperature_k, 
                                                name=f"Junction {name_prefix}", geodata=mid_coord)
            pp.create_circ_pump_const_mass_flow(net_i, junction_dict[coords[1]], mid_junction_idx,
                                              p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=mass_flow,
                                              t_flow_k=supply_temperature_k, type="auto",
                                              name=f"{name_prefix} {i}", in_service=True)
            pp.create_flow_control(net, mid_junction_idx, junction_dict[coords[0]], 
                                 controlled_mdot_kg_per_s=mass_flow)

    # Create network topology
    junction_dict_vl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_flow_line)[0]))
    junction_dict_rl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_return_line)[0]))

    # Create pipes
    create_pipes(net, *get_line_coords_and_lengths(gdf_flow_line), junction_dict_vl, 
                pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "flow line")
    create_pipes(net, *get_line_coords_and_lengths(gdf_return_line), junction_dict_rl, 
                pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "return line")
    
    # Create heat consumers
    create_heat_consumers(net, get_line_coords_and_lengths(gdf_heat_exchanger)[0], 
                        {**junction_dict_vl, **junction_dict_rl}, "heat consumer")
    
    # Create heat producers
    all_heat_producer_coords, all_heat_producer_lengths = get_line_coords_and_lengths(gdf_heat_producer)
    if all_heat_producer_coords:
        # Main producer (pressure controlled)
        create_circulation_pump_pressure(net, [all_heat_producer_coords[main_producer_location_index]], 
                                       {**junction_dict_vl, **junction_dict_rl}, "heat source")

        # Secondary producers (mass flow controlled)
        if secondary_producers:
            mass_flows = [producer.mass_flow for producer in secondary_producers]
            secondary_coords = [all_heat_producer_coords[producer.index] for producer in secondary_producers]
            create_circulation_pump_mass_flow(net, secondary_coords, {**junction_dict_vl, **junction_dict_rl}, 
                                            "heat source slave", mass_flows)

    print(f"secondary_producers: {secondary_producers}")

    # Intial flow simulation
    pp.pipeflow(net, mode="bidirectional", iter=100)

    # Network optimization
    net = create_controllers(net, qext_w, supply_temperature, min_supply_temperature_heat_consumer, 
                           return_temperature_heat_consumer, secondary_producers)
    
    run_control(net, mode="bidirectional",iter=100)
    
    net = correct_flow_directions(net)
    net = init_diameter_types(net, v_max_pipe=v_max_pipe, material_filter=material_filter, k=k_mm)

    return net