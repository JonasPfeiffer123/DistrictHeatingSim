"""
Pandapipes Network Initialization Module
=========================================

This module provides comprehensive network initialization capabilities for district heating
systems using GeoJSON-based geographic data.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

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
from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

def initialize_geojson(NetworkGenerationData) -> Any:
    """
    Initialize district heating network from unified GeoJSON and heat demand data.
    
    :param NetworkGenerationData: Configuration with network_geojson_path, heat_demand_json_path, temperatures, pipe specs, producer config
    :type NetworkGenerationData: object
    :return: Updated NetworkGenerationData with initialized net, time series, mass flows, building data
    :rtype: Any
    :raises FileNotFoundError: If GeoJSON or JSON files not found
    :raises ValueError: If temperature constraints violated (return > supply)
    :raises KeyError: If required JSON fields missing
    
    .. note::
       Loads unified GeoJSON (Wärmenetz.geojson), processes heat demands, validates temperatures.
       Handles cold networks (COP calculation), applies 2% min load. Calculates mass flows
       (main: total demand/ΔT, secondary: percentage-based). Creates complete pandapipes network.
    """
    # Load unified network GeoJSON data
    
    # Read unified GeoJSON file
    network_gdf = gpd.read_file(NetworkGenerationData.network_geojson_path, driver='GeoJSON')
    
    # Separate features by type
    gdf_dict = {
        "flow_line": network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_FLOW].copy(),
        "return_line": network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_RETURN].copy(),
        "heat_consumer": network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_BUILDING].copy(),
        "heat_producer": network_gdf[network_gdf['feature_type'] == NetworkGeoJSONSchema.FEATURE_TYPE_GENERATOR].copy()
    }
    
    print(f"Loaded unified network GeoJSON with {len(network_gdf)} features")
    print(f"  Flow lines: {len(gdf_dict['flow_line'])}")
    print(f"  Return lines: {len(gdf_dict['return_line'])}")
    print(f"  Heat consumers: {len(gdf_dict['heat_consumer'])}")
    print(f"  Heat producers: {len(gdf_dict['heat_producer'])}")

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
    Extract coordinates and lengths from LineString geometries.
    
    :param gdf: GeoDataFrame with LineString geometries (flow/return lines)
    :type gdf: gpd.GeoDataFrame
    :return: (all_line_coords, all_line_lengths) - coordinate sequences and lengths
    :rtype: Tuple[List[List[Tuple]], List[float]]
    
    .. note::
       Only processes LineString geometries, skips others with warning. Uses
       GeoPandas length property for geodetic calculation.
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
    Extract unique point coordinates for network junction creation.
    
    :param all_line_coords: List of coordinate sequences [(x1,y1), (x2,y2), ...]
    :type all_line_coords: List[List[Tuple]]
    :return: Unique point coordinates (x, y) for junction locations
    :rtype: List[Tuple]
    
    .. note::
       Removes duplicates using set operations. Order not guaranteed.
       Essential for proper network topology without duplicate junctions.
    """
    point_coords = [koordinate for paar in all_line_coords for koordinate in paar]
    unique_point_coords = list(set(point_coords))
    return unique_point_coords

def create_network(gdf_dict: Dict[str, gpd.GeoDataFrame], consumer_dict: Dict[str, Any], 
                  pipe_dict: Dict[str, Any], producer_dict: Dict[str, Any]) -> pp.pandapipesNet:
    """
    Create complete pandapipes network with junctions, pipes, consumers, and producers.
    
    :param gdf_dict: GeoDataFrames with keys flow_line, return_line, heat_consumer, heat_producer
    :type gdf_dict: Dict[str, gpd.GeoDataFrame]
    :param consumer_dict: Heat consumer config (qext_w, min_supply_temperature_heat_consumer, return_temperature_heat_consumer)
    :type consumer_dict: Dict[str, Any]
    :param pipe_dict: Pipe config (pipetype, v_max_pipe, material_filter, pipe_creation_mode, k_mm)
    :type pipe_dict: Dict[str, Any]
    :param producer_dict: Producer config (supply_temperature, pressures, main_producer_location_index, secondary_producers)
    :type producer_dict: Dict[str, Any]
    :return: Complete pandapipes network with optimized diameters and controllers
    :rtype: pp.pandapipesNet
    
    .. note::
       Steps: 1) junctions from coords, 2) pipes (supply/return), 3) heat consumers,
       4) producers (main=circ_pump_pressure, secondary=circ_pump_mass), 5) pipeflow,
       6) controllers, diameter optimization. Corrects flow directions automatically.
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