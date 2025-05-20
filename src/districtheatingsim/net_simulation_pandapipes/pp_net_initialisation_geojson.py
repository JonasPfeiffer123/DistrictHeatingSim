"""
Filename: pp_net_initialisation_geojson.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
    Date: 2025-05-17
Description: Script for the net initialisation of geojson based net data.
"""

import numpy as np
import geopandas as gpd
import pandapipes as pp
import json
import pandas as pd

from districtheatingsim.net_simulation_pandapipes.utilities import create_controllers, correct_flow_directions, COP_WP, init_diameter_types

def initialize_geojson(NetworkGenerationData):
    """Initialize the network using GeoJSON data and various parameters.

    Args:
        NetworkGenerationData (object): Network generation data object containing all necessary parameters.

    Returns:

    """

    # Create the network, cluster information
    gdf_dict = {
        "flow_line": gpd.read_file(NetworkGenerationData.flow_line_path, driver='GeoJSON'),
        "return_line": gpd.read_file(NetworkGenerationData.return_line_path, driver='GeoJSON'),
        "heat_consumer": gpd.read_file(NetworkGenerationData.heat_consumer_path, driver='GeoJSON'),
        "heat_producer": gpd.read_file(NetworkGenerationData.heat_generator_path, driver='GeoJSON')
    }

    # max supply temperature of the heat generator
    print(f"Max supply temperature heat generator: {NetworkGenerationData.max_supply_temperature_heat_generator} °C")
    
    with open(NetworkGenerationData.heat_demand_json_path, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)

        # Ensure results contain the necessary keys
        results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'wärme' in v}

        # Process the loaded data to form a DataFrame
        heat_demand_df = pd.DataFrame.from_dict({k: v for k, v in loaded_data.items() if k.isdigit()}, orient='index')

    # Extract supply and return temperatures from the DataFrame
    supply_temperature_buildings = heat_demand_df["VLT_max"].values.astype(float)
    return_temperature_buildings = heat_demand_df["RLT_max"].values.astype(float)

    # Extract data arrays
    yearly_time_steps = np.array(heat_demand_df["zeitschritte"].values[0]).astype(np.datetime64)
    total_building_heat_demand_W = np.array([results[str(i)]["wärme"] for i in range(len(results))])*1000
    total_building_heating_demand_W = np.array([results[str(i)]["heizwärme"] for i in range(len(results))])*1000
    total_building_hot_water_demand_W = np.array([results[str(i)]["warmwasserwärme"] for i in range(len(results))])*1000
    supply_temperature_building_curve = np.array([results[str(i)]["vorlauftemperatur"] for i in range(len(results))])
    return_temperature_building_curve = np.array([results[str(i)]["rücklauftemperatur"] for i in range(len(results))])
    maximum_building_heat_load_W = np.array(results["0"]["max_last"])*1000

    print(f"Max heat demand buildings (W): {maximum_building_heat_load_W}")

    ### Definition of the return temperature of the heat_consumer ###
    ### If the return temperature is not fixed, calculate it based on the return temperature of the buildings and the delta T ###
    if NetworkGenerationData.fixed_return_temperature_heat_consumer == None:
        return_temperature_heat_consumer = return_temperature_buildings + NetworkGenerationData.dT_RL
        print(f"Return temperature heat consumers: {return_temperature_heat_consumer} °C")
    ### If the return temperature is fixed, use the fixed value. Creare an array with the same size as the return temperature of the buildings ###
    else:
        return_temperature_heat_consumer = np.full_like(return_temperature_buildings, NetworkGenerationData.fixed_return_temperature_heat_consumer)
        print(f"Return temperature heat consumers: {return_temperature_heat_consumer} °C")

    ### Check if the return temperature is higher than the supply temperature of the heat generator ###
    if np.any(return_temperature_heat_consumer >= NetworkGenerationData.max_supply_temperature_heat_generator):
        raise ValueError("Return temperature must not be higher than the supply temperature at the injection point. Please check your inputs.")
    
    ### Definition of the minimum supply temperature of the heat consumer###
    ### If the minimum supply temperature for the building is not set, set the values for the minimum supply temperature of the heat consumer to 0###
    if NetworkGenerationData.min_supply_temperature_building == None:
        min_supply_temperature_heat_consumer = np.zeros_like(supply_temperature_buildings, NetworkGenerationData.min_supply_temperature_building)
        print(f"Minimum supply temperature heat consumers: {min_supply_temperature_heat_consumer} °C")
    ### If the minimum supply temperature for the building is set, create an array with the same size as the supply temperature of the buildings using dT_RL ###
    else:
        min_supply_temperature_heat_consumer = np.full_like(supply_temperature_buildings, NetworkGenerationData.min_supply_temperature_building + NetworkGenerationData.dT_RL)
        print(f"Minimum supply temperature heat consumers: {min_supply_temperature_heat_consumer} °C")
    
    ### Check if the minimum supply temperature is higher than the supply temperature of the heat generator ###
    if np.any(min_supply_temperature_heat_consumer >= NetworkGenerationData.max_supply_temperature_heat_generator):
        raise ValueError("Supply temperature at the heat consumer cannot be higher than the supply temperature at the injection point. Please check your inputs.")

    waerme_hast_ges_W = []
    max_waerme_hast_ges_W = []
    strombedarf_hast_ges_W = []
    max_el_leistung_hast_ges_W = []

    if NetworkGenerationData.netconfiguration == "kaltes Netz":
        COP_file_values = np.genfromtxt(NetworkGenerationData.COP_filename, delimiter=';')
        COP, _ = COP_WP(supply_temperature_buildings, return_temperature_heat_consumer, COP_file_values)
        print(f"COP dezentrale Wärmepumpen Gebäude: {COP}")

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
        waerme_hast_ges_W = total_building_heat_demand_W
        max_waerme_hast_ges_W = maximum_building_heat_load_W
        strombedarf_hast_ges_W = np.zeros_like(total_building_heat_demand_W)
        max_el_leistung_hast_ges_W = np.zeros_like(maximum_building_heat_load_W)

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

    # Calculate mass flow for secondary producers
    if NetworkGenerationData.secondary_producers:
        # Calculate mass flow of main producer with cp = 4.18 kJ/kgK from sum of max_waerme_hast_ges_W (in W)
        cp = 4.18  # kJ/kgK
        mass_flow = np.sum(total_building_heat_demand_W / 1000) / (cp * (NetworkGenerationData.max_supply_temperature_heat_generator - np.average(return_temperature_heat_consumer)))  # kW / (kJ/kgK * K) = kg/s

        print(f"Mass flow of main producer: {mass_flow} kg/s")

        # Update each secondary producer's dictionary with the calculated mass flow
        for secondary_producer in NetworkGenerationData.secondary_producers:
            secondary_producer["mass_flow"] = secondary_producer["percentage"]/100 * mass_flow
            print(f"Mass flow of secondary producer {secondary_producer['index']}: {secondary_producer['mass_flow']} kg/s")

    producer_dict = {
        "supply_temperature": NetworkGenerationData.max_supply_temperature_heat_generator,
        "flow_pressure_pump": NetworkGenerationData.flow_pressure_pump,
        "lift_pressure_pump": NetworkGenerationData.lift_pressure_pump,
        "main_producer_location_index": NetworkGenerationData.main_producer_location_index,
        "secondary_producers": NetworkGenerationData.secondary_producers
    }

    net = create_network(gdf_dict, consumer_dict, pipe_dict, producer_dict)

    # Save calculated variables in NetworkGenerationData
    NetworkGenerationData.supply_temperature_buildings = supply_temperature_buildings # supply temperature of the buildings from the heat demand json file, 1D array with floats
    NetworkGenerationData.return_temperature_buildings = return_temperature_buildings # return temperature of the buildings from the heat demand json file, 1D array with floats
    NetworkGenerationData.supply_temperature_building_curve = supply_temperature_building_curve # supply temperature of the buildings from the heat demand json file, 2D array (time dependent) with floats
    NetworkGenerationData.return_temperature_building_curve = return_temperature_building_curve # return temperature of the buildings from the heat demand json file, 2D array (time dependent) with floats
    NetworkGenerationData.yearly_time_steps = yearly_time_steps # yearly time steps from the heat demand json file, 1D array with datetime64
    NetworkGenerationData.waerme_gebaeude_ges_W = total_building_heat_demand_W # total heat demand of the buildings from the heat demand json file, 2D array (time dependent) with floats
    NetworkGenerationData.heizwaerme_gebaeude_ges_W = total_building_heating_demand_W # total heating demand of the buildings from the heat demand json file, 2D array (time dependent) with floats
    NetworkGenerationData.ww_waerme_gebaeude_ges_W = total_building_hot_water_demand_W  # total hot water demand of the buildings from the heat demand json file, 2D array (time dependent) with floats
    NetworkGenerationData.max_waerme_gebaeude_ges_W = maximum_building_heat_load_W # maximum heat load of the buildings from the heat demand json file, 1D array with floats
    NetworkGenerationData.return_temperature_heat_consumer = return_temperature_heat_consumer # return temperature of the heat consumers, 1D array with floats
    NetworkGenerationData.min_supply_temperature_heat_consumer = min_supply_temperature_heat_consumer # minimum supply temperature of the heat consumers, 1D array with floats
    NetworkGenerationData.waerme_hast_ges_W = waerme_hast_ges_W # heat demand of the heat consumers (different from waerme_gebaeude_ges_W if heat pump), 2D array (time dependent) with floats
    NetworkGenerationData.strombedarf_hast_ges_W = strombedarf_hast_ges_W # electricity demand of the heat consumers (not 0 if heat pump), 2D array (time dependent) with floats
    NetworkGenerationData.max_waerme_hast_ges_W = max_waerme_hast_ges_W # maximum heat load of the heat consumers (different from max_waerme_gebaeude_ges_W if heat pump), 1D array with floats
    NetworkGenerationData.max_el_leistung_hast_ges_W = max_el_leistung_hast_ges_W # maximum electricity load of the heat consumers (not 0 if heat pump), 1D array with floats

    # replace all values in NetworkGenerationData.waerme_hast_ges_W with 2 % of the maximum value if the value is smaller than 2 % of the maximum value
    max_heat = np.max(NetworkGenerationData.waerme_hast_ges_W)
    max_power = np.max(NetworkGenerationData.strombedarf_hast_ges_W)
    NetworkGenerationData.waerme_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_heat, NetworkGenerationData.waerme_hast_ges_W)
    NetworkGenerationData.strombedarf_hast_ges_W = np.where(NetworkGenerationData.waerme_hast_ges_W < 0.02 * max_heat, 0.02 * max_power, NetworkGenerationData.strombedarf_hast_ges_W)

    # Convert all values in NetworkGenerationData.waerme_hast_ges_W and NetworkGenerationData.strombedarf_hast_ges_W to kW
    NetworkGenerationData.waerme_hast_ges_kW = np.where(NetworkGenerationData.waerme_hast_ges_W == 0, 0, NetworkGenerationData.waerme_hast_ges_W / 1000)
    NetworkGenerationData.strombedarf_hast_ges_kW = np.where(NetworkGenerationData.strombedarf_hast_ges_W == 0, 0, NetworkGenerationData.strombedarf_hast_ges_W / 1000)

    # Calculate the total heat and electricity demand profiles
    NetworkGenerationData.waerme_ges_kW = np.sum(NetworkGenerationData.waerme_hast_ges_kW, axis=0)
    NetworkGenerationData.strombedarf_ges_kW = np.sum(NetworkGenerationData.strombedarf_hast_ges_kW, axis=0)

    NetworkGenerationData.net = net # pandapipes network object

    return NetworkGenerationData
    
def get_line_coords_and_lengths(gdf):
    """Extract line coordinates and lengths from a GeoDataFrame.

    Args:
        gdf (GeoDataFrame): GeoDataFrame containing line geometries.

    Returns:
        tuple: Lists of line coordinates and their lengths.
    """
    all_line_coords, all_line_lengths = [], []
    # Berechnung der Länge jeder Linie
    gdf['length'] = gdf.geometry.length
    for index, row in gdf.iterrows():
        line = row['geometry']
        
        if line.geom_type == 'LineString':
            coords = list(line.coords)
            length = row['length']
            all_line_coords.append(coords)
            all_line_lengths.append(length)
        else:
            print(f"Geometrie ist kein LineString: {line.type}")

    return all_line_coords, all_line_lengths

def get_all_point_coords_from_line_cords(all_line_coords):
    """Get all unique point coordinates from line coordinates.

    Args:
        all_line_coords (list): List of line coordinates.

    Returns:
        list: List of unique point coordinates.
    """
    point_coords = [koordinate for paar in all_line_coords for koordinate in paar]
    unique_point_coords = list(set(point_coords))
    return unique_point_coords

def create_network(gdf_dict, consumer_dict, pipe_dict, producer_dict):
    """Create the pandapipes network using the provided data and parameters.

    Args:
        gdf_dict (dict): Dictionary containing GeoDataFrames for the flow line, return line, heat exchangers, and heat producers.
        consumer_dict (dict): Dictionary containing the heat consumer data.
        pipe_dict (dict): Dictionary containing the pipe data.
        producer_dict (dict): Dictionary containing the producer data.

    Returns:
        pandapipesNet: The created pandapipes network.
    """

    gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer = gdf_dict["flow_line"], gdf_dict["return_line"], gdf_dict["heat_consumer"], gdf_dict["heat_producer"]
    qext_w, min_supply_temperature_heat_consumer, return_temperature_heat_consumer = consumer_dict["qext_w"], consumer_dict["min_supply_temperature_heat_consumer"], consumer_dict["return_temperature_heat_consumer"]
    supply_temperature, flow_pressure_pump, lift_pressure_pump, main_producer_location_index, secondary_producers = producer_dict["supply_temperature"], producer_dict["flow_pressure_pump"], producer_dict["lift_pressure_pump"], producer_dict["main_producer_location_index"], producer_dict["secondary_producers"]
    pipetype, v_max_pipe, material_filter, pipe_creation_mode, k_mm = pipe_dict["pipetype"], pipe_dict["v_max_pipe"], pipe_dict["material_filter"], pipe_dict["pipe_creation_mode"], pipe_dict["k_mm"]

    net = pp.create_empty_network(fluid="water")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")

    properties = pipe_std_types.loc[pipetype]
    diameter_mm  = properties['inner_diameter_mm']
    u_w_per_m2k_pipe = properties['u_w_per_m2k'] # heat transfer coefficient for pipes

    supply_temperature_k = supply_temperature + 273.15
    return_temperature_heat_consumer_k = return_temperature_heat_consumer + 273.15

    def create_junctions_from_coords(net_i, all_coords):
        """Create junctions in the network from coordinates.

        Args:
            net_i (pandapipesNet): The pandapipes network.
            all_coords (list): List of coordinates for the junctions.

        Returns:
            dict: Dictionary mapping coordinates to junction IDs.
        """
        junction_dict = {}
        for i, coords in enumerate(all_coords, start=0):
            junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=supply_temperature_k, name=f"Junction {i}", geodata=coords) # pn_bar and tfluid_k just for initialization
            junction_dict[coords] = junction_id
        return junction_dict

    def create_pipes(net_i, all_line_coords, all_line_lengths, junction_dict, pipe_mode, pipe_type_or_diameter, line_type):
        """Create pipes in the network from line coordinates and lengths.

        Args:
            net_i (pandapipesNet): The pandapipes network.
            all_line_coords (list): List of line coordinates.
            all_line_lengths (list): List of line lengths.
            junction_dict (dict): Dictionary mapping coordinates to junction IDs.
            pipe_mode (str): Mode for creating pipes ("type" or "diameter").
            pipe_type_or_diameter (str or float): Pipe type or diameter.
            line_type (str): Type of line ("flow line" or "return line").
        """
        for coords, length_m, i in zip(all_line_coords, all_line_lengths, range(len(all_line_coords))):
            if pipe_mode == "diameter":
                diameter_mm = pipe_type_or_diameter
                pipe_name = line_type
                pp.create_pipe_from_parameters(net_i, from_junction=junction_dict[coords[0]],
                                            to_junction=junction_dict[coords[1]], length_km=length_m/1000,
                                            diameter_m=diameter_mm/1000, k_mm=k_mm, u_w_per_m2k=u_w_per_m2k_pipe, 
                                            name=f"{pipe_name} {i}", geodata=coords, sections=5, text_k=283)
            elif pipe_mode == "type":
                pipetype = pipe_type_or_diameter
                pipe_name = line_type
                pp.create_pipe(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]],
                            std_type=pipetype, length_km=length_m/1000, k_mm=k_mm, name=f"{pipe_name} {i}", geodata=coords, 
                            sections=5, text_k=283)

    def create_heat_consumers(net_i, all_coords, junction_dict, name_prefix):
        """Create heat exchangers in the network.

        Args:
            net_i (pandapipesNet): The pandapipes network.
            all_coords (list): List of coordinates for the heat exchangers.
            junction_dict (dict): Dictionary mapping coordinates to junction IDs.
            name_prefix (str): Prefix for naming the heat exchangers.
        """
        for i, (coords, q, t) in enumerate(zip(all_coords, qext_w, return_temperature_heat_consumer_k)):
            pp.create_heat_consumer(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]], loss_coefficient=0, 
                                    qext_w=q, treturn_k=t, name=f"{name_prefix} {i}")

    def create_circulation_pump_pressure(net_i, all_coords, junction_dict, name_prefix):
        """Create circulation pumps with constant pressure in the network.

        Args:
            net_i (pandapipesNet): The pandapipes network.
            all_coords (list): List of coordinates for the pumps.
            junction_dict (dict): Dictionary mapping coordinates to junction IDs.
            name_prefix (str): Prefix for naming the pumps.
        """
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                               t_flow_k=supply_temperature_k, type="auto",
                                               name=f"{name_prefix} {i}")
            
    def create_circulation_pump_mass_flow(net_i, all_coords, junction_dict, name_prefix, mass_flow):
        """Create circulation pumps with constant mass flow in the network.

        Args:
            net_i (pandapipesNet): The pandapipes network.
            all_coords (list): List of coordinates for the pumps.
            junction_dict (dict): Dictionary mapping coordinates to junction IDs.
            name_prefix (str): Prefix for naming the pumps.
        """
        for i, coords in enumerate(all_coords, start=0):
            mid_coord = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
            mid_junction_idx = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=supply_temperature_k, name=f"Junction {name_prefix}", geodata=mid_coord)
            # Create the pump with constant mass flow
            pp.create_circ_pump_const_mass_flow(net_i, junction_dict[coords[1]], mid_junction_idx,
                                               p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=mass_flow,
                                               t_flow_k=supply_temperature_k, type="auto",
                                               name=f"{name_prefix} {i}", in_service=True)
            pp.create_flow_control(net, mid_junction_idx, junction_dict[coords[0]], controlled_mdot_kg_per_s=mass_flow)

    # Create the junction dictionaries for the forward and return lines
    junction_dict_vl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_flow_line)[0]))
    junction_dict_rl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_return_line)[0]))

    # Create the pipes
    create_pipes(net, *get_line_coords_and_lengths(gdf_flow_line), junction_dict_vl, pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "flow line")
    create_pipes(net, *get_line_coords_and_lengths(gdf_return_line), junction_dict_rl, pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "return line")
    
    # Create the heat exchangers
    create_heat_consumers(net, get_line_coords_and_lengths(gdf_heat_exchanger)[0], {**junction_dict_vl, **junction_dict_rl}, "heat cosnumer")
    
    # Heat producer preprocessing for multiple pumps
    all_heat_producer_coords, all_heat_producer_lengths = get_line_coords_and_lengths(gdf_heat_producer)
    # Ensure at least one coordinate pair is present
    if all_heat_producer_coords:
        # Create the circulation pump with constant pressure for the first heat producer location
        create_circulation_pump_pressure(net, [all_heat_producer_coords[main_producer_location_index]], {**junction_dict_vl, **junction_dict_rl}, "heat source")

        # Create circulation pumps with constant mass flow for the remaining producer locations
        if secondary_producers:
            mass_flows = [producer["mass_flow"] for producer in secondary_producers]
            secondary_coords = [all_heat_producer_coords[producer["index"]] for producer in secondary_producers]
            create_circulation_pump_mass_flow(net, secondary_coords, {**junction_dict_vl, **junction_dict_rl}, "heat source slave", mass_flows)

    # Simulate pipe flow
    pp.pipeflow(net, mode="bidirectional", iter=100)

    print(f"secondary_producers: {secondary_producers}")
    net = create_controllers(net, qext_w, supply_temperature, min_supply_temperature_heat_consumer, return_temperature_heat_consumer, secondary_producers)
    net = correct_flow_directions(net)
    net = init_diameter_types(net, v_max_pipe=v_max_pipe, material_filter=material_filter, k=k_mm)

    return net