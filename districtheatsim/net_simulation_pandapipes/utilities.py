import time
import logging
import sys
import os

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from scipy.interpolate import RegularGridInterpolator

import pandapipes as pp
from pandapipes.control.run_control import run_control

from pandapower.timeseries import DFData
from pandapower.control.controller.const_control import ConstControl

from net_simulation_pandapipes.controllers import ReturnTemperatureController, WorstPointPressureController

# Initialize logging
logging.basicConfig(level=logging.INFO)

def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def COP_WP(VLT_L, QT, values=np.genfromtxt(get_resource_path('heat_generators\Kennlinien WP.csv'), delimiter=';')):
    row_header = values[0, 1:]  # Vorlauftemperaturen
    col_header = values[1:, 0]  # Quelltemperaturen
    values = values[1:, 1:]
    f = RegularGridInterpolator((col_header, row_header), values, method='linear')

    # Technical limit of the heat pump is a temperature range of 75 °C
    VLT_L = np.minimum(VLT_L, 75+QT)
    VLT_L = np.maximum(VLT_L, 35)

    # Check whether QT is a number or an array
    if np.isscalar(QT):
        # If QT is a number, we create an array with that number
        QT_array = np.full_like(VLT_L, QT)
    else:
        # If QT is already an array, we check if it has the same length as VLT_L
        if len(QT) != len(VLT_L):
            raise ValueError("QT muss entweder eine einzelne Zahl oder ein Array mit der gleichen Länge wie VLT_L sein.")
        QT_array = QT

    # Calculation of COP_L
    COP_L = f(np.column_stack((QT_array, VLT_L)))

    return COP_L, VLT_L

def net_optimization(net, v_max_pipe, v_max_heat_exchanger, material_filter, insulation_filter):
    run_control(net, mode="all")

    net = optimize_diameter_types(net, v_max=v_max_pipe, material_filter=material_filter, insulation_filter=insulation_filter)
    net = optimize_diameter_parameters(net, element="heat_consumer", v_max=v_max_heat_exchanger)

    # recalculate maximum and minimum mass flows in the controller
    net = recalculate_all_mass_flow_limits(net)
    
    run_control(net, mode="all")

    return net

def create_controllers(net, qext_w, return_temperature):
    if len(qext_w) != len(return_temperature):
        raise ValueError("Die Längen von qext_w und return_temperature müssen gleich sein.")

    # Creates controllers for the network
    #for i in range(len(net.heat_exchanger)):
    for i in range(len(net.heat_consumer)):
        # Create a simple DFData object for qext_w with the specific value for this pass
        placeholder_df = pd.DataFrame({f'qext_w_{i}': [qext_w[i]]})
        placeholder_data_source = DFData(placeholder_df)

        ConstControl(net, element='heat_consumer', variable='qext_w', element_index=i, data_source=placeholder_data_source, profile_name=f'qext_w_{i}')
        
        # Adjustment for using return_temperature as an array
        T_controller = ReturnTemperatureController(net, heat_consumer_idx=i, target_temperature=return_temperature[i])
        net.controller.loc[len(net.controller)] = [T_controller, True, -1, -1, False, False]

    dp_min, idx_dp_min = calculate_worst_point(net)  # This function must be defined
    dp_controller = WorstPointPressureController(net, idx_dp_min)  # This class must be defined
    net.controller.loc[len(net.controller)] = [dp_controller, True, -1, -1, False, False]

    return net

def recalculate_all_mass_flow_limits(net):
    for idx, controller in net.controller.iterrows():
        if isinstance(controller['object'], ReturnTemperatureController):
            controller['object'].calculate_mass_flow_limits(net)

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
    v_max /= 1.5
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

def init_diameter_types(net, v_max_pipe=1.0, material_filter="KMR", insulation_filter="2v"):
    start_time_total = time.time()
    pp.pipeflow(net, mode="all")
    logging.info(f"Initial pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    filtered_by_material = pipe_std_types[pipe_std_types['material'] == material_filter]
    filtered_by_material_and_insulation = filtered_by_material[filtered_by_material['insulation'] == insulation_filter]

    type_position_dict = {type_name: i for i, type_name in enumerate(filtered_by_material_and_insulation.index)}

    # Initial diameter adjustment
    for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
        current_diameter = net.pipe.at[pipe_idx, 'diameter_m']
        required_diameter = current_diameter * (velocity / v_max_pipe)**0.5
        # Find the closest available standard type
        closest_type = min(filtered_by_material_and_insulation.index, key=lambda x: abs(filtered_by_material_and_insulation.loc[x, 'inner_diameter_mm'] / 1000 - required_diameter))
        net.pipe.std_type.at[pipe_idx] = closest_type
        properties = filtered_by_material_and_insulation.loc[closest_type]
        net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
        net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
        net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']

    pp.pipeflow(net, mode="all")
    logging.info(f"Post-initial diameter adjustment pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    return net

def optimize_diameter_types(net, v_max=1.0, material_filter="KMR", insulation_filter="2v"):
    start_time_total = time.time()
    pp.pipeflow(net, mode="all")
    logging.info(f"Initial pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    pipe_std_types = pp.std_types.available_std_types(net, "pipe")
    filtered_by_material = pipe_std_types[pipe_std_types['material'] == material_filter]
    filtered_by_material_and_insulation = filtered_by_material[filtered_by_material['insulation'] == insulation_filter]

    type_position_dict = {type_name: i for i, type_name in enumerate(filtered_by_material_and_insulation.index)}

    # Initial diameter adjustment
    for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
        current_diameter = net.pipe.at[pipe_idx, 'diameter_m']
        required_diameter = current_diameter * (velocity / v_max)**0.5
        # Find the closest available standard type
        closest_type = min(filtered_by_material_and_insulation.index, key=lambda x: abs(filtered_by_material_and_insulation.loc[x, 'inner_diameter_mm'] / 1000 - required_diameter))
        net.pipe.std_type.at[pipe_idx] = closest_type
        properties = filtered_by_material_and_insulation.loc[closest_type]
        net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
        net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
        net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']

    pp.pipeflow(net, mode="all")
    logging.info(f"Post-initial diameter adjustment pipeflow calculation took {time.time() - start_time_total:.2f} seconds")

    # Add a column to track if a pipe is optimized
    net.pipe['optimized'] = False

    change_made = True
    iteration_count = 0

    while change_made:
        iteration_start_time = time.time()
        change_made = False

        # Track the number of pipes within and outside the desired velocity range
        pipes_within_target = 0
        pipes_outside_target = 0

        for pipe_idx, velocity in enumerate(net.res_pipe.v_mean_m_per_s):
            if net.pipe.at[pipe_idx, 'optimized'] and velocity <= v_max:
                pipes_within_target += 1
                continue

            #if velocity > v_max:
            #    logging.info(f"Velocity at {pipe_idx} at start is {velocity} m/s")

            current_type = net.pipe.std_type.at[pipe_idx]
            current_type_position = type_position_dict[current_type]

            if velocity > v_max and current_type_position < len(filtered_by_material_and_insulation) - 1:
                new_type = filtered_by_material_and_insulation.index[current_type_position + 1]
                net.pipe.std_type.at[pipe_idx] = new_type
                properties = filtered_by_material_and_insulation.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
                net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']
                change_made = True
                pipes_outside_target += 1

            elif velocity <= v_max and current_type_position > 0:
                new_type = filtered_by_material_and_insulation.index[current_type_position - 1]
                net.pipe.std_type.at[pipe_idx] = new_type
                properties = filtered_by_material_and_insulation.loc[new_type]
                net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
                net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']

                pp.pipeflow(net, mode="all")
                new_velocity = net.res_pipe.v_mean_m_per_s[pipe_idx]

                #logging.info(f"Adjusted velocity for pipe {pipe_idx}: {new_velocity} m/s with new type {new_type}")

                if new_velocity <= v_max:
                    change_made = True
                else:
                    #logging.info(f"Reverting pipe {pipe_idx} to original type {current_type} as new velocity is {new_velocity} m/s")
                    net.pipe.std_type.at[pipe_idx] = current_type
                    properties = filtered_by_material_and_insulation.loc[current_type]
                    net.pipe.at[pipe_idx, 'diameter_m'] = properties['inner_diameter_mm'] / 1000
                    net.pipe.at[pipe_idx, 'k_mm'] = properties['RAU']
                    net.pipe.at[pipe_idx, 'alpha_w_per_m2k'] = properties['WDZAHL']
                    
                    net.pipe.at[pipe_idx, 'optimized'] = True
                    pipes_within_target += 1
            else:
                net.pipe.at[pipe_idx, 'optimized'] = True
                pipes_within_target += 1

            #if velocity > v_max:
            #    logging.info(f"Velocity at {pipe_idx} at end is {velocity} m/s")

        iteration_count += 1
        if change_made:
            iteration_pipeflow_start = time.time()
            pp.pipeflow(net, mode="all")
            #logging.info(f"Iteration {iteration_count}: pipeflow calculation took {time.time() - iteration_pipeflow_start:.2f} seconds")
        
        logging.info(f"Iteration {iteration_count}: {pipes_within_target} pipes within target velocity, {pipes_outside_target} pipes outside target velocity")
        logging.info(f"Iteration {iteration_count} took {time.time() - iteration_start_time:.2f} seconds")

    logging.info(f"Total optimization time: {time.time() - start_time_total:.2f} seconds")
    return net

def calculate_worst_point(net):
    # with this function, the worst point in the heating network is being calculated
    # specificially the worst point is defined as the heat exchanger with the lowest pressure difference between the forward and the return line, resulting in a lower mass flow
    # after finding the worst point a differential pressure control for the circulation pump could be implemented

    # Initial pipeflow calculation
    pp.pipeflow(net, mode="all")
    
    dp = []

    for idx, p_from, p_to in zip(net.heat_consumer.index, net.res_heat_consumer["p_from_bar"], net.res_heat_consumer["p_to_bar"]):
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

    if 'heat_consumer' in net and not net.heat_consumer.empty:
        # Iterate through each pair of heat_exchanger and flow_control
        for idx, heat_consumer in net.heat_consumer.iterrows():
            # Get the coordinates for flow_control's start and heat_exchanger's end coordinates
            start_coords = net.junction_geodata.loc[heat_consumer['from_junction']]
            end_coords = net.junction_geodata.loc[heat_consumer['to_junction']]

            # Create a line between these points
            line = LineString([(start_coords['x'], start_coords['y']), (end_coords['x'], end_coords['y'])])
            
            # Create a GeoDataFrame for this combined component
            gdf_component = gpd.GeoDataFrame({
                'name': "HAST",
                'diameter_mm': f"{heat_consumer['diameter_m']*1000:.1f}",
                'qext_W': f"{heat_consumer['qext_w']:.0f}",
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