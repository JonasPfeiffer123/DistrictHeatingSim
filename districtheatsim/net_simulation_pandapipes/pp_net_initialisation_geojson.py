"""
Filename: pp_net_initialisation_geojson.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-26
Description: Script for the net initialisation of geojson based net data.

"""

import numpy as np
import geopandas as gpd
import pandapipes as pp
import json
import pandas as pd

from net_simulation_pandapipes.utilities import create_controllers, correct_flow_directions, COP_WP, init_diameter_types

def initialize_geojson(vorlauf, ruecklauf, hast, erzeugeranlagen, json_path, COP_filename, min_supply_temperature_building, \
                       return_temperature_heat_consumer, supply_temperature_net, flow_pressure_pump, lift_pressure_pump, netconfiguration, pipetype, dT_RL, \
                       v_max_pipe, material_filter, insulation_filter, v_max_heat_consumer, mass_flow_secondary_producers=0.5):
    vorlauf = gpd.read_file(vorlauf, driver='GeoJSON')
    ruecklauf = gpd.read_file(ruecklauf, driver='GeoJSON')
    hast = gpd.read_file(hast, driver='GeoJSON')
    erzeugeranlagen = gpd.read_file(erzeugeranlagen, driver='GeoJSON')

    supply_temperature_net = np.max(supply_temperature_net)
    print(f"Vorlauftemperatur Netz: {supply_temperature_net} °C")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)

        # Ensure results contain the necessary keys
        results = {k: v for k, v in loaded_data.items() if isinstance(v, dict) and 'lastgang_wärme' in v}

        # Process the loaded data to form a DataFrame
        df = pd.DataFrame.from_dict({k: v for k, v in loaded_data.items() if k.isdigit()}, orient='index')

    supply_temperature_buildings = df["VLT_max"].values.astype(float)
    return_temperature_buildings = df["RLT_max"].values.astype(float)

    # Extract data arrays
    yearly_time_steps = np.array(df["zeitschritte"].values[0]).astype(np.datetime64)
    waerme_gebaeude_ges_W = np.array([results[str(i)]["lastgang_wärme"] for i in range(len(results))])
    heizwaerme_gebaeude_ges_W = np.array([results[str(i)]["heating_wärme"] for i in range(len(results))])
    ww_waerme_gebaeude_ges_W = np.array([results[str(i)]["warmwater_wärme"] for i in range(len(results))])
    supply_temperature_building_curve = np.array([results[str(i)]["vorlauftemperatur"] for i in range(len(results))])
    return_temperature_building_curve = np.array([results[str(i)]["rücklauftemperatur"] for i in range(len(results))])
    max_waerme_gebaeude_ges_W = results["0"]["heizlast"]

    ### Definition Soll-Rücklauftemperatur ### 
    if return_temperature_heat_consumer == None:
        return_temperature_heat_consumer = return_temperature_buildings + dT_RL
        print(f"Rücklauftemperatur HAST: {return_temperature_heat_consumer} °C")
    else:
        return_temperature_heat_consumer = np.full_like(return_temperature_buildings, return_temperature_heat_consumer)
        print(f"Rücklauftemperatur HAST: {return_temperature_heat_consumer} °C")

    if np.any(return_temperature_heat_consumer >= supply_temperature_net):
        raise ValueError("Rücklauftemperatur darf nicht höher als die Vorlauftemperatur am Einspeisepunkt sein. Bitte überprüfen sie die Eingaben.")
    
    ### Definition Mindestvorlauftemperatur ###
    if min_supply_temperature_building == None:
        min_supply_temperature_building = np.zeros_like(supply_temperature_buildings)
        min_supply_temperature_heat_consumer = np.zeros_like(supply_temperature_buildings)
        print(f"Mindestvorlauftemperatur Gebäude: {min_supply_temperature_building} °C")
        print(f"Mindestvorlauftemperatur HAST: {min_supply_temperature_heat_consumer} °C")
    else:
        min_supply_temperature_building = np.full_like(supply_temperature_buildings, min_supply_temperature_building)
        min_supply_temperature_heat_consumer = np.full_like(supply_temperature_buildings, min_supply_temperature_building + dT_RL)
        print(f"Mindestvorlauftemperatur Gebäude: {min_supply_temperature_building} °C")
        print(f"Mindestvorlauftemperatur HAST: {min_supply_temperature_heat_consumer} °C")

    if np.any(min_supply_temperature_heat_consumer >= supply_temperature_net):
        raise ValueError("Vorlauflauftemperatur an HAST kann nicht höher als die Vorlauftemperatur am Einspeisepunkt sein. Bitte überprüfen sie die Eingaben.")

    waerme_hast_ges_W = []
    max_waerme_hast_ges_W = []
    strombedarf_hast_ges_W = []
    max_el_leistung_hast_ges_W = []
    if netconfiguration == "kaltes Netz":
        COP_file_values = np.genfromtxt(COP_filename, delimiter=';')
        COP, _ = COP_WP(supply_temperature_buildings, return_temperature_heat_consumer, COP_file_values)
        print(f"COP dezentrale Wärmepumpen Gebäude: {COP}")

        for waerme_gebaeude, leistung_gebaeude, cop in zip(waerme_gebaeude_ges_W, max_waerme_gebaeude_ges_W, COP):
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
        waerme_hast_ges_W = waerme_gebaeude_ges_W
        max_waerme_hast_ges_W = max_waerme_gebaeude_ges_W
        strombedarf_hast_ges_W = np.zeros_like(waerme_gebaeude_ges_W)
        max_el_leistung_hast_ges_W = np.zeros_like(max_waerme_gebaeude_ges_W)

    net = create_network(vorlauf, ruecklauf, hast, erzeugeranlagen, max_waerme_hast_ges_W, min_supply_temperature_building, return_temperature_heat_consumer, \
                            supply_temperature_net, flow_pressure_pump, lift_pressure_pump, pipetype, \
                            v_max_pipe, material_filter, insulation_filter, v_max_heat_consumer=v_max_heat_consumer, mass_flow_secondary_producers=mass_flow_secondary_producers)
    
    return net, yearly_time_steps, waerme_hast_ges_W, return_temperature_heat_consumer, supply_temperature_buildings, return_temperature_buildings, \
        supply_temperature_building_curve, return_temperature_building_curve, strombedarf_hast_ges_W, max_el_leistung_hast_ges_W

def get_line_coords_and_lengths(gdf):
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
    point_coords = [koordinate for paar in all_line_coords for koordinate in paar]
    unique_point_coords = list(set(point_coords))
    return unique_point_coords

def create_network(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, supply_temperature_heat_consumer=75, return_temperature_heat_consumer=60, supply_temperature=85,
                   flow_pressure_pump=4, lift_pressure_pump=1.5, pipetype="KMR 100/250-2v", v_max_pipe=1, material_filter="KMR", insulation_filter="2v", 
                   pipe_creation_mode="type", v_max_heat_consumer=2, main_producer_location_index=0, mass_flow_secondary_producers=0.5):
    net = pp.create_empty_network(fluid="water")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")

    properties = pipe_std_types.loc[pipetype]
    diameter_mm  = properties['inner_diameter_mm']
    k = properties['RAU']
    alpha = properties['WDZAHL']

    initial_mdot_guess_kg_s = qext_w / (4170*(supply_temperature-return_temperature_heat_consumer))
    initial_Vdot_guess_m3_s = initial_mdot_guess_kg_s/1000
    area_m2 = initial_Vdot_guess_m3_s/(v_max_heat_consumer*(1/1.2))       # Safety factor of 1.1
    initial_dimension_guess_m = np.round(np.sqrt(area_m2 *(4/np.pi)), 3)

    def create_junctions_from_coords(net_i, all_coords):
        junction_dict = {}
        for i, coords in enumerate(all_coords, start=0):
            junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {i}", geodata=coords) # pn_bar and tfluid_k just for initialization
            junction_dict[coords] = junction_id
        return junction_dict

    def create_pipes(net_i, all_line_coords, all_line_lengths, junction_dict, pipe_mode, pipe_type_or_diameter, line_type):
        for coords, length_m, i in zip(all_line_coords, all_line_lengths, range(len(all_line_coords))):
            if pipe_mode == "diameter":
                diameter_mm = pipe_type_or_diameter
                pipe_name = line_type
                pp.create_pipe_from_parameters(net_i, from_junction=junction_dict[coords[0]],
                                            to_junction=junction_dict[coords[1]], length_km=length_m/1000,
                                            diameter_m=diameter_mm/1000, k_mm=k, alpha_w_per_m2k=alpha, 
                                            name=f"{pipe_name} {i}", geodata=coords, sections=5, text_k=283)
            elif pipe_mode == "type":
                pipetype = pipe_type_or_diameter
                pipe_name = line_type
                pp.create_pipe(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]],
                            std_type=pipetype, length_km=length_m/1000, k_mm=k, alpha_w_per_m2k=alpha,
                            name=f"{pipe_name} {i}", geodata=coords, sections=5, text_k=283)


    def create_heat_exchangers(net_i, all_coords, junction_dict, name_prefix):
        for i, (coords, q, t, m, d) in enumerate(zip(all_coords, qext_w, return_temperature_heat_consumer, initial_mdot_guess_kg_s, initial_dimension_guess_m)):
            pp.create_heat_consumer(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]], controlled_mdot_kg_per_s=m, diameter_m=d, 
                                    loss_coefficient=0, qext_w=q, name=f"{name_prefix} {i}") # treturn_k=t when implemented in function


    def create_circulation_pump_pressure(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")
            
    def create_circulation_pump_mass_flow(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            mid_coord = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
            mid_junction_idx = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {name_prefix}", geodata=mid_coord)

            pp.create_circ_pump_const_mass_flow(net_i, junction_dict[coords[1]], mid_junction_idx,
                                               p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=mass_flow_secondary_producers,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")
            pp.create_flow_control(net, mid_junction_idx, junction_dict[coords[0]], controlled_mdot_kg_per_s=mass_flow_secondary_producers, diameter_m=0.1)

    # creates the junction dictonaries for the forward an return line
    junction_dict_vl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_flow_line)[0]))
    junction_dict_rl = create_junctions_from_coords(net, get_all_point_coords_from_line_cords(
        get_line_coords_and_lengths(gdf_return_line)[0]))

    # creates the pipes
    create_pipes(net, *get_line_coords_and_lengths(gdf_flow_line), junction_dict_vl, pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "flow line")
    create_pipes(net, *get_line_coords_and_lengths(gdf_return_line), junction_dict_rl, pipe_creation_mode, diameter_mm if pipe_creation_mode == "diameter" else pipetype, "return line")
    
    # creates the heat exchangers
    create_heat_exchangers(net, get_line_coords_and_lengths(gdf_heat_exchanger)[0], {**junction_dict_vl, **junction_dict_rl}, "heat exchanger")
    
    # heat producer preprocessing for multiple pumps
    all_heat_producer_coords, all_heat_producer_lengths = get_line_coords_and_lengths(gdf_heat_producer)
    # Sicherstellen, dass mindestens ein Koordinatenpaar vorhanden ist
    if all_heat_producer_coords:
        # creates the circulation pump const pressure for the first heat producer location // might implement some functionality to choose which one is main producer
        create_circulation_pump_pressure(net, [all_heat_producer_coords[main_producer_location_index]], {**junction_dict_vl, **junction_dict_rl}, "heat source")

        # creates circulation pump const mass flow for the remaining producer locations
        for i in range(len(all_heat_producer_coords)):
            if i != main_producer_location_index:
                create_circulation_pump_mass_flow(net, [all_heat_producer_coords[i]], {**junction_dict_vl, **junction_dict_rl}, "heat source slave")

    net = create_controllers(net, qext_w, return_temperature_heat_consumer, supply_temperature_heat_consumer)
    net = correct_flow_directions(net)
    net = init_diameter_types(net, v_max_pipe=v_max_pipe, material_filter=material_filter, insulation_filter=insulation_filter)

    return net