"""
Config Plot Module
==================

This module provides comprehensive visualization capabilities for district heating network
analysis and presentation.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31

It combines pandapipes network plotting with interactive features,
contextual basemaps, and detailed component annotations to create professional-quality
network visualizations for engineering analysis and stakeholder presentations.

The module supports various basemap providers, interactive hover annotations, and customizable
component visibility to accommodate different visualization needs from technical analysis
to public presentations. It integrates seamlessly with matplotlib and geographic visualization
libraries for enhanced spatial context.
"""

import numpy as np
import matplotlib.pyplot as plt
import pandapipes.plotting as pp_plot
import contextily as cx
import geopandas as gpd
from shapely.geometry import Point
from typing import Optional, List, Tuple, Dict, Any

def config_plot(net, ax: plt.Axes, show_junctions: bool = True, show_pipes: bool = True, 
               show_heat_consumers: bool = True, show_pump: bool = True, show_plot: bool = False, 
               show_basemap: bool = True, map_type: str = "OSM", show_all_annotations: bool = False) -> None:
    """
    Configure and render an interactive visualization of a pandapipes district heating network.

    This function creates a comprehensive network visualization with interactive annotations,
    contextual basemaps, and customizable component display. It provides detailed technical
    information through hover interactions and supports various map backgrounds for enhanced
    spatial context and professional presentation quality.

    Parameters
    ----------
    net : pandapipes.pandapipesNet
        The pandapipes network object containing network topology, components, and simulation
        results. Must include geodata for proper geographic visualization.
    ax : matplotlib.axes.Axes
        The matplotlib axis object on which to render the network plot. Will be cleared
        before plotting to ensure clean visualization.
    show_junctions : bool, optional
        Display network junctions with pressure and temperature information.
        Default is True. Useful for detailed hydraulic analysis.
    show_pipes : bool, optional
        Display network pipes with flow rates, velocities, and pipe specifications.
        Default is True. Essential for pipe sizing and flow analysis.
    show_heat_consumers : bool, optional
        Display heat consumers with demand and mass flow information.
        Default is True. Critical for load analysis and system balancing.
    show_pump : bool, optional
        Display circulation pumps with pressure lift and flow rate data.
        Default is True. Important for pump sizing and energy analysis.
    show_plot : bool, optional
        Immediately display the plot using plt.show(). Default is False.
        Set to True for standalone plotting, False for integration into larger figures.
    show_basemap : bool, optional
        Include contextual basemap from online tile services. Default is True.
        Requires internet connection and proper coordinate reference system.
    map_type : str, optional
        Basemap provider type for geographic context. Default is "OSM".
        
        Available options:
            - **"OSM"** : OpenStreetMap standard layer (good general purpose)
            - **"Satellite"** : Esri WorldImagery satellite imagery (detailed terrain)
            - **"Topology"** : OpenTopoMap topographic layer (elevation contours)
            
    show_all_annotations : bool, optional
        Force display of all component annotations simultaneously. Default is False.
        When False, annotations appear on mouse hover for cleaner visualization.

    Returns
    -------
    None
        Function modifies the provided axis in-place and sets up interactive event handlers.

    Notes
    -----
    Interactive Features:
        - **Hover annotations** : Component details appear when cursor approaches
        - **Distance-based visibility** : Annotations show/hide based on cursor proximity
        - **Multi-component support** : Handles junctions, pipes, consumers, and pumps
        - **Real-time updates** : Smooth annotation transitions during mouse movement

    Geographic Requirements:
        - Network must include geodata (junction_geodata) with valid coordinates
        - Coordinate system should be projected (e.g., EPSG:25833) for accurate display
        - Internet connection required for basemap tiles

    Annotation Content:
        - **Junctions** : Name, pressure [bar], temperature [°C]
        - **Pipes** : Name, type, length [km], mass flow [kg/s], velocity [m/s]
        - **Heat consumers** : Name, heat demand [W], mass flow [kg/s]
        - **Pumps** : Type, pressure lift [bar], mass flow [kg/s]

    Performance Considerations:
        - Large networks may have slower hover response due to distance calculations
        - Basemap loading depends on internet connection speed
        - Use show_all_annotations=False for better performance with many components

    Examples
    --------
    >>> # Basic network visualization
    >>> fig, ax = plt.subplots(figsize=(12, 8))
    >>> config_plot(network, ax, show_basemap=True, map_type="OSM")
    >>> plt.title("District Heating Network Overview")
    >>> plt.show()

    >>> # Technical analysis plot without basemap
    >>> fig, ax = plt.subplots(figsize=(10, 8))
    >>> config_plot(network, ax, show_basemap=False, show_all_annotations=True)
    >>> ax.set_title("Network Technical Analysis")
    >>> ax.grid(True, alpha=0.3)

    >>> # Presentation-quality plot with satellite background
    >>> fig, ax = plt.subplots(figsize=(16, 12))
    >>> config_plot(network, ax, map_type="Satellite", show_junctions=False)
    >>> ax.set_title("District Heating Network - Satellite View", fontsize=16)

    >>> # Focus on specific components
    >>> config_plot(network, ax, show_junctions=False, show_pipes=False,
    ...              show_heat_consumers=True, show_pump=True)

    Raises
    ------
    AttributeError
        If network lacks required geodata or component tables.
    ConnectionError
        If basemap tiles cannot be downloaded (network connection issues).
    ValueError
        If coordinate reference system is invalid or incompatible.

    See Also
    --------
    pandapipes.plotting.simple_plot : Basic pandapipes network plotting
    contextily.add_basemap : Basemap integration for geographic context
    matplotlib.pyplot.annotate : Annotation creation and styling
    """
    ax.clear()  # Clear previous plots

    data_annotations: List[Dict[str, Any]] = []  # Store annotation references and data

    def make_annotation(text: str, x: float, y: float, obj_type: str, 
                       obj_id: Optional[int] = None, line_points: Optional[List[Tuple[float, float]]] = None, 
                       visible: bool = False) -> Dict[str, Any]:
        """
        Create an interactive annotation for a network component.

        Parameters
        ----------
        text : str
            Annotation text content with component information.
        x, y : float
            Annotation anchor coordinates in network coordinate system.
        obj_type : str
            Component type for styling and interaction ("junction", "pipe", "heat_consumer", "pump").
        obj_id : int, optional
            Component ID for data lookup and interaction tracking.
        line_points : List[Tuple[float, float]], optional
            Line segment endpoints for pipe distance calculations.
        visible : bool, optional
            Initial visibility state. Default is False for hover-based display.

        Returns
        -------
        Dict[str, Any]
            Annotation data structure containing matplotlib annotation object and metadata.
        """
        # Adjust annotation offset based on component type for optimal visibility
        if obj_type in ["heat_consumer", "pump"]:
            xytext = (50, 50)  # Larger offset for prominent components
        else:
            xytext = (10, 10)  # Standard offset for network infrastructure
            
        ann = ax.annotate(text, xy=(x, y), xytext=xytext,
                        textcoords='offset points', ha='center', va='bottom',
                        fontsize=8, visible=visible,
                        bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        return {
            "annotation": ann, 
            "x": x, 
            "y": y, 
            "obj_type": obj_type, 
            "obj_id": obj_id, 
            "line_points": line_points
        }

    # Create annotations for network junctions
    if show_junctions and hasattr(net, 'junction') and hasattr(net, 'junction_geodata'):
        for junction in net.junction.index:
            try:
                x, y = net.junction_geodata.loc[junction, ['x', 'y']]
                name = net.junction.loc[junction, 'name']
                pressure = net.res_junction.loc[junction, 'p_bar'] if hasattr(net, 'res_junction') else 0.0
                temperature = net.res_junction.loc[junction, 't_k'] if hasattr(net, 'res_junction') else 273.15
                text = f"{name}\nPressure: {pressure:.2f} bar\nTemperature: {temperature - 273.15:.2f} °C"
                ann = make_annotation(text, x, y, "junction", junction)
                data_annotations.append(ann)
            except (KeyError, IndexError):
                continue  # Skip junctions with missing data

    # Create annotations for network pipes
    if show_pipes and hasattr(net, 'pipe'):
        for pipe in net.pipe.index:
            try:
                from_junction = net.pipe.at[pipe, 'from_junction']
                to_junction = net.pipe.at[pipe, 'to_junction']
                from_x, from_y = net.junction_geodata.loc[from_junction, ['x', 'y']]
                to_x, to_y = net.junction_geodata.loc[to_junction, ['x', 'y']]
                name = net.pipe.loc[pipe, 'name']
                mid_x = (from_x + to_x) / 2
                mid_y = (from_y + to_y) / 2
                pipe_type = net.pipe.loc[pipe, 'std_type']
                pipe_length_km = net.pipe.loc[pipe, 'length_km']
                
                # Include flow results if available
                mdot = net.res_pipe.loc[pipe, 'mdot_from_kg_per_s'] if hasattr(net, 'res_pipe') else 0.0
                v = net.res_pipe.loc[pipe, 'v_mean_m_per_s'] if hasattr(net, 'res_pipe') else 0.0
                
                text = f"{name}: {pipe_type}\nLength: {pipe_length_km:.2f} km\nMass flow: {mdot:.2f} kg/s\nVelocity: {v:.2f} m/s"
                ann = make_annotation(text, mid_x, mid_y, "pipe", pipe, [(from_x, from_y), (to_x, to_y)])
                data_annotations.append(ann)
            except (KeyError, IndexError):
                continue  # Skip pipes with missing data

    # Create annotations for heat consumers
    if show_heat_consumers and hasattr(net, 'heat_consumer'):
        for hc in net.heat_consumer.index:
            try:
                from_x, from_y = net.junction_geodata.loc[net.heat_consumer.at[hc, 'from_junction'], ['x', 'y']]
                to_x, to_y = net.junction_geodata.loc[net.heat_consumer.at[hc, 'to_junction'], ['x', 'y']]
                mid_x = (from_x + to_x) / 2
                mid_y = (from_y + to_y) / 2
                name = net.heat_consumer.loc[hc, 'name']
                qext = net.heat_consumer.loc[hc, 'qext_w']
                
                # Include flow results if available
                mdot = net.res_heat_consumer.loc[hc, 'mdot_from_kg_per_s'] if hasattr(net, 'res_heat_consumer') else 0.0
                
                text = f"{name}\nHeat demand: {qext:.2f} W\nMass flow: {mdot:.2f} kg/s"
                ann = make_annotation(text, mid_x, mid_y, "heat_consumer", hc)
                data_annotations.append(ann)
            except (KeyError, IndexError):
                continue  # Skip consumers with missing data

    # Create annotations for circulation pumps
    if show_pump and hasattr(net, 'circ_pump_pressure'):
        for pump in net.circ_pump_pressure.index:
            try:
                from_x, from_y = net.junction_geodata.loc[net.circ_pump_pressure.at[pump, 'return_junction'], ['x', 'y']]
                to_x, to_y = net.junction_geodata.loc[net.circ_pump_pressure.at[pump, 'flow_junction'], ['x', 'y']]
                mid_x = (from_x + to_x) / 2
                mid_y = (from_y + to_y) / 2
                name = net.circ_pump_pressure.loc[pump, 'name']
                
                # Include pump results if available
                if hasattr(net, 'res_circ_pump_pressure'):
                    deltap = (net.res_circ_pump_pressure.loc[pump, 'p_to_bar'] - 
                             net.res_circ_pump_pressure.loc[pump, 'p_from_bar'])
                    mdot_flow = net.res_circ_pump_pressure.loc[pump, 'mdot_from_kg_per_s']
                else:
                    deltap = 0.0
                    mdot_flow = 0.0
                
                text = f"Circulation Pump: {name}\nPressure lift: {deltap:.2f} bar\nMass flow: {mdot_flow:.2f} kg/s"
                ann = make_annotation(text, mid_x, mid_y, "pump", pump)
                data_annotations.append(ann)
            except (KeyError, IndexError):
                continue  # Skip pumps with missing data

    # Add contextual basemap for geographic reference
    if show_basemap and hasattr(net, 'junction_geodata'):
        try:
            # Convert junction geodata to GeoDataFrame for basemap integration
            gdf = gpd.GeoDataFrame(
                net.junction_geodata,
                geometry=[Point(xy) for xy in zip(net.junction_geodata['x'], net.junction_geodata['y'])],
                crs="EPSG:25833"  # Adjust coordinate system as needed
            )

            # Ensure proper coordinate reference system
            gdf = gdf.to_crs(epsg=25833)

            # Set plot bounds with buffer for better visualization
            xmin, ymin, xmax, ymax = gdf.total_bounds
            buffer = max((xmax - xmin), (ymax - ymin)) * 0.05  # 5% buffer
            ax.set_xlim(xmin - buffer, xmax + buffer)
            ax.set_ylim(ymin - buffer, ymax + buffer)

            # Add selected basemap type
            basemap_sources = {
                "OSM": cx.providers.OpenStreetMap.Mapnik,
                "Satellite": cx.providers.Esri.WorldImagery,
                "Topology": cx.providers.OpenTopoMap
            }
            
            if map_type in basemap_sources:
                cx.add_basemap(ax, source=basemap_sources[map_type], crs=gdf.crs)
            else:
                print(f"Warning: Unknown map type '{map_type}'. Using OSM as default.")
                cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, crs=gdf.crs)
                
        except Exception as e:
            print(f"Warning: Could not add basemap. Error: {e}")

    # Render the network using pandapipes plotting
    pp_plot.simple_plot(net, junction_size=0.01, heat_consumer_size=0.1, pump_size=0.1, 
                        pump_color='green', pipe_color='black', heat_consumer_color="blue", 
                        ax=ax, show_plot=False, junction_geodata=net.junction_geodata)

    def show_all_annotations() -> None:
        """Display all component annotations simultaneously."""
        for ann_data in data_annotations:
            ann_data['annotation'].set_visible(True)
        ax.figure.canvas.draw_idle()

    # Display all annotations if requested
    if show_all_annotations:
        show_all_annotations()

    def on_move(event) -> None:
        """
        Handle mouse movement for interactive annotation display.
        
        Calculates distances to components and shows/hides annotations based on
        cursor proximity. Uses different distance calculation methods for point
        and line components.
        """
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            return
            
        for ann_data in data_annotations:
            if ann_data['obj_type'] == 'pipe' and ann_data['line_points'] is not None:
                # Calculate perpendicular distance to line segment
                try:
                    p1 = np.array(ann_data['line_points'][0])
                    p2 = np.array(ann_data['line_points'][1])
                    p3 = np.array([event.xdata, event.ydata])
                    
                    # Handle zero-length lines
                    line_length = np.linalg.norm(p2 - p1)
                    if line_length > 0:
                        dist = np.abs(np.cross(p2-p1, p1-p3)) / line_length
                    else:
                        dist = np.hypot(event.xdata - ann_data['x'], event.ydata - ann_data['y'])
                except (ValueError, ZeroDivisionError):
                    # Fallback to point distance for problematic line calculations
                    dist = np.hypot(event.xdata - ann_data['x'], event.ydata - ann_data['y'])
            else:
                # Calculate direct Euclidean distance to point
                dist = np.hypot(event.xdata - ann_data['x'], event.ydata - ann_data['y'])

            # Show/hide annotation based on proximity threshold
            proximity_threshold = 50.0  # Adjust based on coordinate system scale
            ann_data['annotation'].set_visible(dist < proximity_threshold)
            
        ax.figure.canvas.draw_idle()

    # Connect mouse movement event handler for interactivity
    ax.figure.canvas.mpl_connect('motion_notify_event', on_move)

    # Display plot immediately if requested
    if show_plot:
        plt.show()