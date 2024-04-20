import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import numpy as np

import pandapipes as pp
from pandapower.timeseries import DFData
from pandapower.control.controller.const_control import ConstControl
from net_simulation_pandapipes.controllers import ReturnTemperatureController, WorstPointPressureController

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

def create_network(gdf_flow_line, gdf_return_line, gdf_heat_exchanger, gdf_heat_producer, qext_w, return_temperature=60, supply_temperature=85, 
                   flow_pressure_pump=4, lift_pressure_pump=1.5, pipetype="KMR 100/250-2v",  pipe_creation_mode="type", v_max_m_s=1.5):
    net = pp.create_empty_network(fluid="water")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")

    properties = pipe_std_types.loc[pipetype]
    diameter_mm  = properties['inner_diameter_mm']
    k = properties['RAU']
    alpha = properties['WDZAHL']

    initial_mdot_guess_kg_s = qext_w / (4170*(supply_temperature-return_temperature))
    initial_Vdot_guess_m3_s = initial_mdot_guess_kg_s/1000
    area_m2 = initial_Vdot_guess_m3_s/v_max_m_s
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
                                            name=pipe_name, geodata=coords, sections=5, text_k=283)
            elif pipe_mode == "type":
                pipetype = pipe_type_or_diameter
                pipe_name = line_type
                pp.create_pipe(net_i, from_junction=junction_dict[coords[0]], to_junction=junction_dict[coords[1]],
                            std_type=pipetype, length_km=length_m/1000, k_mm=k, alpha_w_per_m2k=alpha,
                            name=pipe_name, geodata=coords, sections=5, text_k=283)


    def create_heat_exchangers(net_i, all_coords, junction_dict, name_prefix):
        for i, (coords, q, m, d) in enumerate(zip(all_coords, qext_w, initial_mdot_guess_kg_s, initial_dimension_guess_m)):
            # creates a middle coordinate to place the flow control an the heat exchanger
            mid_coord = ((coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2)
            mid_junction_idx = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=293.15, name=f"Junction {name_prefix}", geodata=mid_coord)

            pp.create_flow_control(net_i, from_junction=junction_dict[coords[0]], to_junction=mid_junction_idx, controlled_mdot_kg_per_s=m, diameter_m=d)

            pp.create_heat_exchanger(net_i, from_junction=mid_junction_idx, to_junction=junction_dict[coords[1]], diameter_m=d, loss_coefficient=0,
                                     qext_w=q, name=f"{name_prefix} {i}")

    def create_circulation_pump_pressure(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_pressure(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=flow_pressure_pump, plift_bar=lift_pressure_pump,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")
            
    def create_circulation_pump_mass_flow(net_i, all_coords, junction_dict, name_prefix):
        for i, coords in enumerate(all_coords, start=0):
            pp.create_circ_pump_const_mass_flow(net_i, junction_dict[coords[1]], junction_dict[coords[0]],
                                               p_flow_bar=flow_pressure_pump, mdot_flow_kg_per_s=0.1,
                                               t_flow_k=273.15 + supply_temperature, type="auto",
                                               name=f"{name_prefix} {i}")

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
    
    # creates the circulation pump pressure for the first heat producer location // might implement some functionality to choose which one is main producer
    create_circulation_pump_pressure(net, get_line_coords_and_lengths(gdf_heat_producer)[0], {**junction_dict_vl, **junction_dict_rl}, "heat source")

    # creates circulation pump mass flow for the remaining producer locations
    # count_heat_producer = 2
    # if count_heat_producer > 1:
    # create_circulation_pump_mass_flow(net, get_line_coords_and_lengths(gdf_heat_producer)[0], {**junction_dict_vl, **junction_dict_rl}, "heat source slave")

    net = create_controllers(net, qext_w, return_temperature)
    net = correct_flow_directions(net)

    return net

def create_controllers(net, qext_w, return_temperature):
    if len(qext_w) != len(return_temperature):
        raise ValueError("Die Längen von qext_w und return_temperature müssen gleich sein.")

    # Creates controllers for the network
    for i in range(len(net.heat_exchanger)):
        # Create a simple DFData object for qext_w with the specific value for this pass
        placeholder_df = pd.DataFrame({f'qext_w_{i}': [qext_w[i]]})
        placeholder_data_source = DFData(placeholder_df)

        ConstControl(net, element='heat_exchanger', variable='qext_w', element_index=i, data_source=placeholder_data_source, profile_name=f'qext_w_{i}')
        
        # Adjustment for using return_temperature as an array
        T_controller = ReturnTemperatureController(net, heat_exchanger_idx=i, target_temperature=return_temperature[i])
        net.controller.loc[len(net.controller)] = [T_controller, True, -1, -1, False, False]

    dp_min, idx_dp_min = calculate_worst_point(net)  # This function must be defined
    dp_controller = WorstPointPressureController(net, idx_dp_min)  # This class must be defined
    net.controller.loc[len(net.controller)] = [dp_controller, True, -1, -1, False, False]

    return net

def correct_flow_directions(net):
    # Initial pipeflow calculation
    pp.pipeflow(net, mode="all")

    # Check the velocities in each pipe and swap the junctions if necessary
    for pipe_idx in net.pipe.index:
        # Check the average velocity in the pipe
        if net.res_pipe.v_mean_m_per_s[pipe_idx] < 0:
            # Swap the junctions
            from_junction = net.pipe.at[pipe_idx, 'from_junction']
            to_junction = net.pipe.at[pipe_idx, 'to_junction']
            net.pipe.at[pipe_idx, 'from_junction'] = to_junction
            net.pipe.at[pipe_idx, 'to_junction'] = from_junction

    # Perform the pipeflow calculation again to obtain updated results
    pp.pipeflow(net, mode="all")

    return net


def optimize_diameter_parameters(net, element="pipe", v_max=2, dx=0.001):
    pp.pipeflow(net, mode="all")
    element_df = getattr(net, element)  # Access the element's DataFrame
    res_df = getattr(net, f"res_{element}")  # Access the result DataFrame
            
    change_made = True
    while change_made:
        change_made = False
        
        for idx in element_df.index:
            current_velocity = res_df.v_mean_m_per_s[idx]
            current_diameter = element_df.at[idx, 'diameter_m']
            
            # enlarge if speed > v_max
            if current_velocity > v_max:
                element_df.at[idx, 'diameter_m'] += dx
                change_made = True

           # shrink as long as speed < v_max and check
            elif current_velocity < v_max:
                element_df.at[idx, 'diameter_m'] -= dx
                pp.pipeflow(net, mode="all")
                element_df = getattr(net, element)  # Access the element's DataFrame
                res_df = getattr(net, f"res_{element}")  # Access the result DataFrame
                new_velocity = res_df.v_mean_m_per_s[idx]

                if new_velocity > v_max:
                    # Reset if new speed exceeds v_max
                    element_df.at[idx, 'diameter_m'] = current_diameter
                else:
                    change_made = True
        
        if change_made:
            pp.pipeflow(net, mode="all")  # Recalculation only if changes were made
            element_df = getattr(net, element)
            res_df = getattr(net, f"res_{element}")

    return net

def optimize_diameter_types(net, v_max=1.0, material_filter="KMR", insulation_filter="2v"):
    pp.pipeflow(net, mode="all")

    # List and filter standard types for pipes
    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    filtered_by_material = pipe_std_types[pipe_std_types['material'] == material_filter]
    filtered_by_material_and_insulation = filtered_by_material[filtered_by_material['insulation'] == insulation_filter]

    # Dictionary for pipe type positions
    type_position_dict = {type_name: i for i, type_name in enumerate(filtered_by_material_and_insulation.index)}

    change_made = True
    while change_made:
        change_made = False

        for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
            current_type = net.pipe.std_type.at[pipe_idx]
            current_type_position = type_position_dict[current_type]


            if velocity > v_max and current_type_position < len(filtered_by_material_and_insulation) - 1:
                 # enlarge diameter
                new_type = filtered_by_material_and_insulation.index[current_type_position + 1]

                # Temporarily apply the new type
                net.pipe.std_type.at[pipe_idx] = new_type
                properties = filtered_by_material_and_insulation.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
                net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']

                change_made = True

            elif velocity < v_max and current_type_position > 0:
                # shrink diameter, but check if this shrink makes the velocity exceed v_max
                new_type = filtered_by_material_and_insulation.index[current_type_position - 1]

                # Temporarily apply the new type
                net.pipe.std_type.at[pipe_idx] = new_type
                properties = filtered_by_material_and_insulation.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
                net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']

                # Recalculate to check new velocity
                pp.pipeflow(net, mode="all")
                new_velocity = net.res_pipe.v_mean_m_per_s[pipe_idx]

                if new_velocity <= v_max:
                    change_made = True
                else:
                    # Revert to original type if velocity exceeds v_max
                    net.pipe.std_type.at[pipe_idx] = current_type
                    properties = filtered_by_material_and_insulation.loc[current_type]
                    net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                    net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
                    net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']
            
        if change_made:
            # Recalculate the pipe flow after all changes
            pp.pipeflow(net, mode="all")

    return net

def calculate_worst_point(net):
    # with this function, the worst point in the heating network is being calculated
    # specificially the worst point is defined as the heat exchanger with the lowest pressure difference between the forward and the return line, resulting in a lower mass flow
    # after finding the worst point a differential pressure control for the circulation pump could be implemented

    # Initial pipeflow calculation
    pp.pipeflow(net, mode="all")
    
    dp = []

    for idx, p_from, p_to in zip(net.heat_exchanger.index, net.res_flow_control["p_from_bar"], net.res_heat_exchanger["p_to_bar"]):
        dp_diff = p_from - p_to
        dp_diff = p_from - p_to
        dp.append((dp_diff, idx))

    # find the minimum delta p
    dp_min, idx_min = min(dp, key=lambda x: x[0])

    return dp_min, idx_min

def export_net_geojson(net, filename):
    features = []  # List to collect GeoDataFrames of all components
    
    # Process lines
    if 'pipe_geodata' in net and not net.pipe_geodata.empty:
        geometry_lines = [LineString(coords) for coords in net.pipe_geodata['coords']]
        gdf_lines = gpd.GeoDataFrame(net.pipe_geodata, geometry=geometry_lines)
        del gdf_lines['coords'] # Remove the 'coords' column
        # Add attributes
        gdf_lines['name'] = net.pipe['name']
        gdf_lines['diameter_mm'] = net.pipe['diameter_m'] * 1000
        gdf_lines['std_type'] = net.pipe['std_type']
        gdf_lines['length_m'] = net.pipe['length_km'] * 1000
        features.append(gdf_lines)

    if 'circ_pump_pressure' in net and not net.circ_pump_pressure.empty:
        # Calculate the geometry
        pump_lines = [LineString([
            (net.junction_geodata.loc[pump['return_junction']]['x'], net.junction_geodata.loc[pump['return_junction']]['y']),
            (net.junction_geodata.loc[pump['flow_junction']]['x'], net.junction_geodata.loc[pump['flow_junction']]['y'])
        ]) for index, pump in net.circ_pump_pressure.iterrows()]
        
        # Filter only relevant columns (adapted to actual data)
        relevant_columns = ['name', 'geometry']
        gdf_pumps = gpd.GeoDataFrame(net.circ_pump_pressure, geometry=pump_lines)[relevant_columns]
        
        features.append(gdf_pumps)

    if 'heat_exchanger' in net and not net.heat_exchanger.empty and 'flow_control' in net and not net.flow_control.empty:
        # Iterate through each pair of heat_exchanger and flow_control
        for idx, heat_exchanger in net.heat_exchanger.iterrows():
            # Since flow_controls and heat_exchangers are created together, we assume that they
            # have the same order or can be linked via logic that must be implemented here
            flow_control = net.flow_control.loc[net.flow_control['to_junction'] == heat_exchanger['from_junction']].iloc[0]

            # Get the coordinates for flow_control's start and heat_exchanger's end coordinates
            start_coords = net.junction_geodata.loc[flow_control['from_junction']]
            end_coords = net.junction_geodata.loc[heat_exchanger['to_junction']]

            # Create a line between these points
            line = LineString([(start_coords['x'], start_coords['y']), (end_coords['x'], end_coords['y'])])
            
            # Create a GeoDataFrame for this combined component
            gdf_component = gpd.GeoDataFrame({
                'name': "HAST",
                'diameter_mm': f"{heat_exchanger['diameter_m']*1000:.1f}",
                'qext_W': f"{heat_exchanger['qext_w']:.0f}",
                'geometry': [line]
            }, crs="EPSG:25833") # set crs to EPSG:25833
            
            features.append(gdf_component)

    # Set the coordinate system (CRS) for all GeoDataFrames and merge them
    for feature in features:
        feature.set_crs(epsg=25833, inplace=True)

    # Combine all GeoDataFrames into a FeatureCollection
    gdf_all = gpd.GeoDataFrame(pd.concat(features, ignore_index=True), crs="EPSG:25833")

    # export as GeoJSON
    if not gdf_all.empty:
        gdf_all.to_file(filename, driver='GeoJSON')
    else:
        print("No geographical data available in the network.")