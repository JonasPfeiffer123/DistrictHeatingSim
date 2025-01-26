"""
Filename: config_plot.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31
Description: Contains the config_plot function for plotting the results of the initialised pandapipes net.
"""

import numpy as np
import matplotlib.pyplot as plt
import pandapipes.plotting as pp_plot
import contextily as cx
import geopandas as gpd
from shapely.geometry import Point

def config_plot(net, ax, show_junctions=True, show_pipes=True, show_heat_consumers=True, show_pump=True, show_plot=False, show_basemap=True, map_type="OSM", show_all_annotations=False):
    """
    Configures and plots the pandapipes network on a given matplotlib axis.

    Args:
        net (pandapipesNet): The pandapipes network to plot.
        ax (matplotlib.axes.Axes): The axis to plot on.
        show_junctions (bool, optional): Whether to show junctions. Defaults to True.
        show_pipes (bool, optional): Whether to show pipes. Defaults to True.
        show_heat_consumers (bool, optional): Whether to show heat consumers. Defaults to True.
        show_pump (bool, optional): Whether to show pumps. Defaults to True.
        show_plot (bool, optional): Whether to show the plot. Defaults to False.
        show_basemap (bool, optional): Whether to show a basemap. Defaults to True.
        map_type (str, optional): Type of basemap to show ("OSM", "Satellite", "Topology"). Defaults to "OSM".

    Returns:
        None
    """
    ax.clear()  # Clear previous plots

    data_annotations = []  # To store annotation references and data

    # Function to create an annotation
    def make_annotation(text, x, y, obj_type, obj_id=None, line_points=None, visible=False):
        # Adjust distance based on type
        if obj_type in ["heat_consumer", "pump"]:
            xytext = (50, 50)  # Increase distance for better visibility
        else:
            xytext = (10, 10)
            
        ann = ax.annotate(text, xy=(x, y), xytext=xytext,
                        textcoords='offset points', ha='center', va='bottom',
                        fontsize=8, visible=visible,
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        return {"annotation": ann, "x": x, "y": y, "obj_type": obj_type, "obj_id": obj_id, "line_points": line_points}

    # Add objects with appropriate customizations
    # Junctions
    if show_junctions:
        for junction in net.junction.index:
            x, y = net.junction_geodata.loc[junction, ['x', 'y']]
            name = net.junction.loc[junction, 'name']
            pressure = net.res_junction.loc[junction, 'p_bar']
            temperature = net.res_junction.loc[junction, 't_k']
            text = f"{name}\nPressure: {pressure:.2f} bar\nTemperature: {temperature - 273.15:.2f} °C"
            ann = make_annotation(text, x, y, "junction", junction)
            data_annotations.append(ann)

    # Pipes
    if show_pipes:
        for pipe in net.pipe.index:
            from_junction = net.pipe.at[pipe, 'from_junction']
            to_junction = net.pipe.at[pipe, 'to_junction']
            from_x, from_y = net.junction_geodata.loc[from_junction, ['x', 'y']]
            to_x, to_y = net.junction_geodata.loc[to_junction, ['x', 'y']]
            name = net.pipe.loc[pipe, 'name']
            mid_x = (from_x + to_x) / 2
            mid_y = (from_y + to_y) / 2
            pipe_type = net.pipe.loc[pipe, 'std_type']
            pipe_length_km = net.pipe.loc[pipe, 'length_km']
            mdot = net.res_pipe.loc[pipe, 'mdot_from_kg_per_s']
            v = net.res_pipe.loc[pipe, 'v_mean_m_per_s']
            text = f"{name}: {pipe_type}\nLength: {pipe_length_km:.2f} km\nMass flow: {mdot:.2f} kg/s\nVelocity: {v:.2f} m/s"
            ann = make_annotation(text, mid_x, mid_y, "pipe", pipe, [(from_x, from_y), (to_x, to_y)])
            data_annotations.append(ann)

    if show_heat_consumers:
        for hc in net.heat_consumer.index:
            from_x, from_y = net.junction_geodata.loc[net.heat_consumer.at[hc, 'from_junction'], ['x', 'y']]
            to_x, to_y = net.junction_geodata.loc[net.heat_consumer.at[hc, 'to_junction'], ['x', 'y']]
            mid_x = (from_x + to_x) / 2
            mid_y = (from_y + to_y) / 2
            name = net.heat_consumer.loc[hc, 'name']
            qext = net.heat_consumer.loc[hc, 'qext_w']
            mdot = net.res_heat_consumer.loc[hc, 'mdot_from_kg_per_s']
            text = f"{name}\nHeat demand: {qext:.2f} W\nMass flow: {mdot:.2f} kg/s\n"
            ann = make_annotation(text, mid_x, mid_y, "heat_consumer", hc)
            data_annotations.append(ann)

    if show_pump:
        for pump in net.circ_pump_pressure.index:
            from_x, from_y = net.junction_geodata.loc[net.circ_pump_pressure.at[pump, 'return_junction'], ['x', 'y']]
            to_x, to_y = net.junction_geodata.loc[net.circ_pump_pressure.at[pump, 'flow_junction'], ['x', 'y']]
            mid_x = (from_x + to_x) / 2
            mid_y = (from_y + to_y) / 2
            name = net.circ_pump_pressure.loc[pump, 'name']
            deltap = net.res_circ_pump_pressure.loc[pump, 'p_to_bar'] - net.res_circ_pump_pressure.loc[pump, 'p_from_bar']
            #deltap = net.res_circ_pump_pressure.loc[pump, 'deltap_bar']
            mdot_flow = net.res_circ_pump_pressure.loc[pump, 'mdot_from_kg_per_s']
            text = f"Circulation Pump Pressure: {pump}\nPressure lift: {deltap:.2f} bar\nMass flow: {mdot_flow:.2f} kg/s"
            ann = make_annotation(text, mid_x, mid_y, "pump", pump)
            data_annotations.append(ann)

    # Add basemap if enabled
    if show_basemap:
        # Convert junction_geodata to a GeoDataFrame
        gdf = gpd.GeoDataFrame(
            net.junction_geodata,
            geometry=[Point(xy) for xy in zip(net.junction_geodata['x'], net.junction_geodata['y'])],
            crs="EPSG:25833"  # Adjust to your actual coordinate system
        )

        gdf = gdf.to_crs(epsg=25833)

        xmin, ymin, xmax, ymax = gdf.total_bounds
        ax.set_xlim(xmin - 10, xmax + 10)
        ax.set_ylim(ymin - 10, ymax + 10)

        if map_type == "OSM":
            # Add context map
            cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, crs=gdf.crs)

        elif map_type == "Satellite":
            # Add satellite image
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, crs=gdf.crs)

        elif map_type == "Topology":
            # Add topology map
            cx.add_basemap(ax, source=cx.providers.OpenTopoMap, crs=gdf.crs)

    # Add network plot
    pp_plot.simple_plot(net, junction_size=0.01, heat_consumer_size=0.1, pump_size=0.1, 
                        pump_color='green', pipe_color='black', heat_consumer_color="blue", ax=ax, show_plot=False, 
                        junction_geodata=net.junction_geodata)

    # Function to show all annotations
    def show_all_annotations():
        for ann_data in data_annotations:
            ann_data['annotation'].set_visible(True)
        ax.figure.canvas.draw_idle()

    # Show all annotations if the flag is set
    if show_all_annotations:
        show_all_annotations()

    # Event handling for interactivity
    def on_move(event):
        if event.inaxes != ax:
            return
        for ann_data in data_annotations:
            if ann_data['obj_type'] == 'pipe':
                # Calculate distance to line
                p1 = np.array(ann_data['line_points'][0])
                p2 = np.array(ann_data['line_points'][1])
                p3 = np.array([event.xdata, event.ydata])
                dist = np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)
            else:
                # Calculate direct distance to point
                dist = np.hypot(event.xdata - ann_data['x'], event.ydata - ann_data['y'])

            # Adjust visibility based on distance
            if dist < 0.5:  # Distance threshold
                ann_data['annotation'].set_visible(True)
            else:
                ann_data['annotation'].set_visible(False)
        ax.figure.canvas.draw_idle()

    ax.figure.canvas.mpl_connect('motion_notify_event', on_move)

    if show_plot:
        plt.show()