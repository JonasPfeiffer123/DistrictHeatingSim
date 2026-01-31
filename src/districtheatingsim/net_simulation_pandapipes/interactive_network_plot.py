"""
Interactive Network Plot Module
================================

Modern interactive visualization for pandapipes district heating networks using Plotly.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Features:

- Interactive hover tooltips with detailed component information
- Click events for component selection and inspection
- Color-coded visualization of any network parameter
- Multiple basemap options (OSM, Satellite, Topology)
- Layer visibility controls
- Dynamic parameter selection
- Export capabilities (HTML, PNG)
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
import geopandas as gpd
from shapely.geometry import Point, LineString
import pandapipes as pp

class InteractiveNetworkPlot:
    """
    Interactive Plotly-based network visualization with advanced features.
    
    :ivar net: Pandapipes network to visualize
    :vartype net: pandapipes.pandapipesNet
    :ivar crs: Coordinate reference system
    :vartype crs: str
    :ivar fig: Plotly figure object
    :vartype fig: Optional[go.Figure]
    :ivar available_parameters: Available parameters per component type
    :vartype available_parameters: Dict[str, List[str]]
    
    .. note::
       Color-coded parameter visualization, hover tooltips, click events, multiple basemap
       options for comprehensive network analysis.
    """
    
    def __init__(self, net, crs: str = "EPSG:25833"):
        """
        Initialize interactive network plot.
        
        :param net: Network to visualize
        :type net: pandapipes.pandapipesNet
        :param crs: Coordinate reference system, defaults to "EPSG:25833"
        :type crs: str
        """
        self.net = net
        self.crs = crs
        self.fig = None
        self.selected_parameter = None
        
        # Available parameters for visualization
        self.available_parameters = self._get_available_parameters()
        
    def _get_available_parameters(self) -> Dict[str, List[str]]:
        """
        Get all available parameters for each component type.
        
        :return: Dict with component types as keys, parameter lists as values
        :rtype: Dict[str, List[str]]
        """
        params = {
            'junction': [],
            'pipe': [],
            'heat_consumer': [],
            'pump': [],
            'flow_control': []
        }
        
        # Junction parameters - Pressure and Temperature
        if hasattr(self.net, 'res_junction'):
            params['junction'] = [
                'p_bar',  # Pressure [bar]
                't_k',    # Temperature [K]
            ]
            
        # Pipe parameters - Only most relevant ones
        if hasattr(self.net, 'res_pipe'):
            available_pipe_params = []
            res_pipe = self.net.res_pipe
            
            # Core flow parameters
            if 'mdot_from_kg_per_s' in res_pipe.columns:
                available_pipe_params.append('mdot_from_kg_per_s')  # Mass flow [kg/s]
            if 'v_mean_m_per_s' in res_pipe.columns:
                available_pipe_params.append('v_mean_m_per_s')      # Velocity [m/s]
            
            # Differential parameters (most useful for analysis)
            if 't_from_k' in res_pipe.columns and 't_to_k' in res_pipe.columns:
                available_pipe_params.append('dt_k')                # Temperature difference [K]
            if 'p_from_bar' in res_pipe.columns and 'p_to_bar' in res_pipe.columns:
                available_pipe_params.append('dp_bar')              # Pressure loss [bar]
            
            params['pipe'] = available_pipe_params
            
        # Heat consumer parameters - Only most relevant ones
        if hasattr(self.net, 'res_heat_consumer'):
            available_hc_params = []
            res_hc = self.net.res_heat_consumer
            
            if 'qext_w' in res_hc.columns:
                available_hc_params.append('qext_w')                # Heat demand [W]
            if 'mdot_from_kg_per_s' in res_hc.columns:
                available_hc_params.append('mdot_from_kg_per_s')    # Mass flow [kg/s]
            
            # Differential parameters (most useful for analysis)
            if 't_from_k' in res_hc.columns and 't_to_k' in res_hc.columns:
                available_hc_params.append('dt_k')                  # Temperature difference [K]
            if 'p_from_bar' in res_hc.columns and 'p_to_bar' in res_hc.columns:
                available_hc_params.append('dp_bar')                # Pressure drop [bar]
            
            params['heat_consumer'] = available_hc_params
            
        # Pump parameters - Only most relevant ones
        if hasattr(self.net, 'res_circ_pump_pressure') or hasattr(self.net, 'res_circ_pump_mass'):
            available_pump_params = []
            
            # Pressure pump results
            if hasattr(self.net, 'res_circ_pump_pressure') and len(self.net.res_circ_pump_pressure) > 0:
                res_pump = self.net.res_circ_pump_pressure
                if 'mdot_from_kg_per_s' in res_pump.columns:
                    available_pump_params.append('mdot_from_kg_per_s')  # Mass flow [kg/s]
                if 'deltap_bar' in res_pump.columns:
                    available_pump_params.append('deltap_bar')          # Pressure increase [bar]
                
                # Temperature difference
                if 't_from_k' in res_pump.columns and 't_to_k' in res_pump.columns:
                    available_pump_params.append('dt_k')                # Temperature difference [K]
            
            # Mass pump results (if exists)
            if hasattr(self.net, 'res_circ_pump_mass') and len(self.net.res_circ_pump_mass) > 0:
                res_pump_mass = self.net.res_circ_pump_mass
                if 'mdot_from_kg_per_s' in res_pump_mass.columns and 'mdot_from_kg_per_s' not in available_pump_params:
                    available_pump_params.append('mdot_from_kg_per_s')
            
            params['pump'] = list(set(available_pump_params))  # Remove duplicates
        
        # Flow control parameters
        if hasattr(self.net, 'res_flow_control') and len(self.net.flow_control) > 0:
            available_fc_params = []
            res_fc = self.net.res_flow_control
            
            if 'mdot_from_kg_per_s' in res_fc.columns:
                available_fc_params.append('mdot_from_kg_per_s')    # Mass flow [kg/s]
            if 'deltap_bar' in res_fc.columns:
                available_fc_params.append('deltap_bar')            # Pressure difference [bar]
            if 't_from_k' in res_fc.columns:
                available_fc_params.append('t_from_k')              # From temperature [K]
            if 't_to_k' in res_fc.columns:
                available_fc_params.append('t_to_k')                # To temperature [K]
            if 'p_from_bar' in res_fc.columns:
                available_fc_params.append('p_from_bar')            # From pressure [bar]
            if 'p_to_bar' in res_fc.columns:
                available_fc_params.append('p_to_bar')              # To pressure [bar]
            
            params['flow_control'] = available_fc_params
            
        return params
    
    def create_interactive_plot_with_controls(self, basemap_style: str = 'carto-positron', colorscale: str = 'Viridis') -> go.Figure:
        """
        Create interactive plot with dropdown controls for parameter selection.
        
        :param basemap_style: Mapbox style: 'open-street-map', 'carto-positron', 'white-bg', 'satellite'
        :type basemap_style: str
        :param colorscale: Plotly colorscale name, defaults to 'Viridis'
        :type colorscale: str
        :return: Interactive Plotly figure with dropdown controls
        :rtype: go.Figure
        
        .. note::
           Pre-generates all visualizations for dropdown functionality in standalone HTML.
        """
        gdf_junctions = self._get_junction_geodata()
        available_params = self._get_available_parameters()
        
        # Store parameters for reuse
        self._colorscale = colorscale
        self._basemap_style = basemap_style
        
        # Create list of all visualizations for dropdown
        visualizations = [('Standard (ohne Parameter)', None, None)]
        
        # Add all available parameter visualizations
        for comp_type, params in available_params.items():
            for param in params:
                visualizations.append((f'{comp_type.replace("_", " ").title()}: {self._get_parameter_label(param)}', 
                                     comp_type, param))
        
        # Add flow control parameters if available
        if hasattr(self.net, 'res_flow_control') and len(self.net.flow_control) > 0:
            for param in ['mdot_from_kg_per_s', 'deltap_bar']:
                if param in self.net.res_flow_control.columns:
                    visualizations.append((f'Flow Control: {self._get_parameter_label(param)}', 
                                         'flow_control', param))
        
        print(f"[Performance] Creating {len(visualizations)} visualizations for dropdown...")
        print(f"[Performance] Network: {len(self.net.junction)} junctions, {len(self.net.pipe)} pipes")
        
        # Pre-generate all visualizations efficiently
        all_traces = []
        trace_counts = []
        
        for i, (label, comp_type, param) in enumerate(visualizations):
            # Create temporary figure for this visualization
            temp_fig = go.Figure()
            self.fig = temp_fig
            
            # Add components with parameter coloring
            self._add_pipes(param if comp_type == 'pipe' else None, colorscale, show=True)
            self._add_heat_consumers(param if comp_type == 'heat_consumer' else None, colorscale, show=True)
            self._add_pumps(param if comp_type == 'pump' else None, colorscale, show=True)
            self._add_flow_controls(param if comp_type == 'flow_control' else None, colorscale, show=True)
            self._add_junctions(param if comp_type == 'junction' else None, colorscale, show=True)
            
            # Store trace count and traces
            trace_counts.append(len(temp_fig.data))
            all_traces.extend(list(temp_fig.data))
            
            if (i + 1) % 5 == 0:
                print(f"[Performance] Generated {i + 1}/{len(visualizations)} visualizations...")
        
        print(f"[Performance] Total traces: {len(all_traces)}")
        
        # Create final figure with all traces
        self.fig = go.Figure(data=all_traces)
        
        # Set initial visibility - only first visualization visible
        for i, trace in enumerate(self.fig.data):
            trace.visible = (i < trace_counts[0])
        
        # Create dropdown buttons with visibility control
        buttons = []
        for i, (label, comp_type, param) in enumerate(visualizations):
            # Calculate visibility array for this visualization
            visible = [False] * len(all_traces)
            start_idx = sum(trace_counts[:i])
            end_idx = start_idx + trace_counts[i]
            for j in range(start_idx, end_idx):
                visible[j] = True
            
            buttons.append({
                'label': label,
                'method': 'update',
                'args': [{'visible': visible}]
            })
        
        # Configure layout
        self._configure_layout(gdf_junctions, basemap_style)
        
        # Add dropdown menu
        self.fig.update_layout(
            updatemenus=[{
                'buttons': buttons,
                'direction': 'down',
                'pad': {'r': 10, 't': 10},
                'showactive': True,
                'active': 0,
                'x': 0.15,
                'xanchor': 'left',
                'y': 0.98,
                'yanchor': 'top',
                'bgcolor': 'rgba(255, 255, 255, 0.95)',
                'bordercolor': '#2c3e50',
                'borderwidth': 2,
                'font': {'size': 12}
            }]
        )
        
        print(f"[Performance] Interactive plot with dropdown ready!")
        
        return self.fig
    
    def create_plot_for_parameter(self, component_type: str, parameter: str, 
                                  basemap_style: str = 'carto-positron', 
                                  colorscale: str = 'Viridis') -> go.Figure:
        """
        Create plot for specific parameter visualization (on-demand loading).
        
        :param component_type: Component type: 'junction', 'pipe', 'heat_consumer', 'pump', 'flow_control'
        :type component_type: str
        :param parameter: Parameter name to visualize
        :type parameter: str
        :param basemap_style: Mapbox style, defaults to 'carto-positron'
        :type basemap_style: str
        :param colorscale: Plotly colorscale, defaults to 'Viridis'
        :type colorscale: str
        :return: Interactive plot for the specific parameter
        :rtype: go.Figure
        """
        self.fig = go.Figure()
        gdf_junctions = self._get_junction_geodata()
        
        # Add components with parameter coloring
        self._add_pipes(parameter if component_type == 'pipe' else None, colorscale, show=True)
        self._add_heat_consumers(parameter if component_type == 'heat_consumer' else None, colorscale, show=True)
        self._add_pumps(parameter if component_type == 'pump' else None, colorscale, show=True)
        self._add_flow_controls(parameter if component_type == 'flow_control' else None, colorscale, show=True)
        self._add_junctions(parameter if component_type == 'junction' else None, colorscale, show=True)
        
        # Configure layout
        self._configure_layout(gdf_junctions, basemap_style)
        
        return self.fig
    
    def create_plot(self, 
                   parameter: Optional[str] = None,
                   component_type: Optional[str] = None,
                   show_junctions: bool = True,
                   show_pipes: bool = True,
                   show_heat_consumers: bool = True,
                   show_pumps: bool = True,
                   show_flow_controls: bool = True,
                   basemap_style: str = 'open-street-map',
                   colorscale: str = 'Viridis') -> go.Figure:
        """
        Create interactive network plot with optional parameter visualization.
        
        :param parameter: Parameter to visualize (e.g., 'p_bar', 'v_mean_m_per_s'), optional
        :type parameter: Optional[str]
        :param component_type: Component type: 'junction', 'pipe', 'heat_consumer', 'pump', optional
        :type component_type: Optional[str]
        :param show_junctions: Show junction nodes, defaults to True
        :type show_junctions: bool
        :param show_pipes: Show pipe connections, defaults to True
        :type show_pipes: bool
        :param show_heat_consumers: Show heat consumers, defaults to True
        :type show_heat_consumers: bool
        :param show_pumps: Show circulation pumps, defaults to True
        :type show_pumps: bool
        :param show_flow_controls: Show flow control components, defaults to True
        :type show_flow_controls: bool
        :param basemap_style: Mapbox style: 'open-street-map', 'satellite', 'white-bg', 'carto-positron'
        :type basemap_style: str
        :param colorscale: Plotly colorscale name, defaults to 'Viridis'
        :type colorscale: str
        :return: Interactive Plotly figure
        :rtype: go.Figure
        """
        # Convert to WGS84 for Plotly mapbox
        gdf_junctions = self._get_junction_geodata()
        
        # Create figure
        self.fig = go.Figure()
        
        # Add pipes (always visible if show_pipes=True, colored only if selected)
        if show_pipes:
            self._add_pipes(
                parameter if component_type == 'pipe' else None, 
                colorscale,
                show=show_pipes
            )
            
        # Add heat consumers
        if show_heat_consumers:
            self._add_heat_consumers(
                parameter if component_type == 'heat_consumer' else None, 
                colorscale,
                show=show_heat_consumers
            )
            
        # Add pumps
        if show_pumps:
            self._add_pumps(
                parameter if component_type == 'pump' else None, 
                colorscale,
                show=show_pumps
            )
            
        # Add flow controls
        if show_flow_controls:
            self._add_flow_controls(
                parameter if component_type == 'flow_control' else None,
                colorscale,
                show=show_flow_controls
            )
            
        # Add junctions (on top for better interaction)
        if show_junctions:
            self._add_junctions(
                parameter if component_type == 'junction' else None, 
                colorscale,
                show=show_junctions
            )
        
        # Configure layout
        self._configure_layout(gdf_junctions, basemap_style)
        
        return self.fig
    
    def _get_junction_geodata(self) -> gpd.GeoDataFrame:
        """
        Get junction geodata in WGS84 for Plotly mapbox.
        
        :return: GeoDataFrame with junction coordinates in WGS84
        :rtype: gpd.GeoDataFrame
        """
        gdf = gpd.GeoDataFrame(
            self.net.junction_geodata,
            geometry=[Point(xy) for xy in zip(
                self.net.junction_geodata['x'], 
                self.net.junction_geodata['y']
            )],
            crs=self.crs
        )
        return gdf.to_crs('EPSG:4326')
    
    def _add_junctions(self, parameter: Optional[str], colorscale: str, show: bool = True):
        """
        Add junction nodes to plot with optional parameter coloring.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        gdf = self._get_junction_geodata()
        
        # Prepare data
        lats = gdf.geometry.y.values
        lons = gdf.geometry.x.values
        names = [self.net.junction.loc[idx, 'name'] for idx in gdf.index]
        
        # Hover text
        hover_texts = []
        for idx in gdf.index:
            junction_data = self.net.junction.loc[idx]
            text = f"<b>{junction_data['name']}</b><br>"
            
            if hasattr(self.net, 'res_junction'):
                res = self.net.res_junction.loc[idx]
                text += f"Druck: {res['p_bar']:.2f} bar<br>"
                text += f"Temperatur: {res['t_k'] - 273.15:.1f} °C<br>"
                
            hover_texts.append(text)
        
        # Color mapping
        if parameter and hasattr(self.net, 'res_junction'):
            values = self.net.res_junction.loc[gdf.index, parameter].values
            marker = dict(
                size=10,
                color=values,
                colorscale=colorscale,
                showscale=True,
                colorbar=dict(
                    title=dict(
                        text=self._get_parameter_label(parameter),
                        side='right',
                        font=dict(size=12)
                    ),
                    x=1.0,
                    xanchor='left',
                    thickness=15,
                    len=0.6,
                    y=0.5,
                    yanchor='middle'
                )
            )
        else:
            marker = dict(
                size=8,
                color='#3498db'
            )
        
        self.fig.add_trace(go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='markers',
            marker=marker,
            text=hover_texts,
            hovertemplate='%{text}<extra></extra>',
            name='junction',
            customdata=gdf.index.values,
            visible=show
        ))
    
    def _add_pipes(self, parameter: Optional[str], colorscale: str, show: bool = True):
        """
        Add pipes to plot with optional parameter coloring.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        if not hasattr(self.net, 'pipe') or len(self.net.pipe) == 0:
            return
            
        gdf_junctions = self._get_junction_geodata()
        
        # Helper function to build hover text for a pipe (SINGLE DEFINITION)
        def build_pipe_hover_text(idx, pipe_data, param_value=None):
            """
            Build hover text for pipe with optional parameter value.
            
            :param idx: Pipe index
            :param pipe_data: Pipe data row
            :param param_value: Optional parameter value for display
            :return: Formatted HTML hover text
            :rtype: str
            """
            hover_text = f"<b>{pipe_data['name']}</b><br>"
            hover_text += f"Typ: {pipe_data['std_type']}<br>"
            hover_text += f"Länge: {pipe_data['length_km']:.3f} km<br>"
            
            if hasattr(self.net, 'res_pipe'):
                res = self.net.res_pipe.loc[idx]
                if 'mdot_from_kg_per_s' in res.index:
                    hover_text += f"Massenstrom: {res['mdot_from_kg_per_s']:.2f} kg/s<br>"
                if 'v_mean_m_per_s' in res.index:
                    hover_text += f"Geschwindigkeit: {res['v_mean_m_per_s']:.2f} m/s<br>"
                if 't_from_k' in res.index and 't_to_k' in res.index:
                    dt = res['t_from_k'] - res['t_to_k']
                    hover_text += f"ΔT: {dt:.1f} K<br>"
                if 'p_from_bar' in res.index and 'p_to_bar' in res.index:
                    dp = res['p_from_bar'] - res['p_to_bar']
                    hover_text += f"Δp: {dp:.2f} bar<br>"
                
                # Add parameter value if provided
                if param_value is not None and parameter:
                    hover_text += f"{self._get_parameter_label(parameter)}: {param_value:.2f}<br>"
            
            return hover_text
        
        # Get parameter values for color mapping if needed
        if parameter and hasattr(self.net, 'res_pipe'):
            # Calculate parameter values (including derived ones like dt_k, dp_bar)
            param_values = []
            for idx in self.net.pipe.index:
                val = self._get_parameter_value(self.net.res_pipe, idx, parameter)
                if val is not None:
                    param_values.append(val)
            
            if param_values:
                param_values = np.array(param_values)
                vmin, vmax = param_values.min(), param_values.max()
                if vmax - vmin < 1e-10:
                    vmax = vmin + 1  # Avoid division by zero
            else:
                vmin, vmax = None, None
            
            # Add dummy marker for colorbar only if we have values
            if vmin is not None:
                self.fig.add_trace(go.Scattermapbox(
                    lat=[gdf_junctions.geometry.y.mean()],
                    lon=[gdf_junctions.geometry.x.mean()],
                    mode='markers',
                    marker=dict(
                        size=0.1,
                        color=[vmin],
                        colorscale=colorscale,
                        showscale=True,
                        cmin=vmin,
                        cmax=vmax,
                    colorbar=dict(
                        title=dict(
                            text=self._get_parameter_label(parameter),
                            side='right',
                            font=dict(size=12)
                        ),
                        x=1.0,
                        xanchor='left',
                        thickness=15,
                        len=0.6,
                        y=0.5,
                        yanchor='middle'
                    )
                ),          
                
                showlegend=False,
                hoverinfo='skip',
                visible=show
            ))
        
        # Add pipes as individual traces
        for i, idx in enumerate(self.net.pipe.index):
            pipe_data = self.net.pipe.loc[idx]
            from_junction = pipe_data['from_junction']
            to_junction = pipe_data['to_junction']
            
            try:
                from_coords = gdf_junctions.loc[from_junction].geometry
                to_coords = gdf_junctions.loc[to_junction].geometry
            except KeyError:
                continue
            
            # Calculate color and parameter value
            if parameter and hasattr(self.net, 'res_pipe') and vmin is not None:
                value = self._get_parameter_value(self.net.res_pipe, idx, parameter)
                if value is not None:
                    norm_value = (value - vmin) / (vmax - vmin)
                    color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
                    hover_text = build_pipe_hover_text(idx, pipe_data, param_value=value)
                else:
                    color = '#2c3e50'  # Default if value not available
                    hover_text = build_pipe_hover_text(idx, pipe_data)
            else:
                color = '#2c3e50'  # Default dark gray
                hover_text = build_pipe_hover_text(idx, pipe_data)
            
            # Calculate midpoint for better hover
            mid_lat = (from_coords.y + to_coords.y) / 2
            mid_lon = (from_coords.x + to_coords.x) / 2
            
            # Create customdata for click events - store pipe index and name
            pipe_name = pipe_data.get('name', f'Pipe {idx}')
            customdata = [[idx, pipe_name]] * 3  # Same for all three points
            
            self.fig.add_trace(go.Scattermapbox(
                lat=[from_coords.y, mid_lat, to_coords.y],
                lon=[from_coords.x, mid_lon, to_coords.x],
                mode='lines+markers',
                line=dict(width=4, color=color),
                marker=dict(size=0.1, color=color),  # Invisible markers for hover
                text=[hover_text, hover_text, hover_text],
                hovertemplate='%{text}<extra></extra>',
                customdata=customdata,  # Store pipe index for click events
                legendgroup='pipes',
                name='pipe',
                showlegend=(i == 0),
                visible=show
            ))
    
    def _add_heat_consumers(self, parameter: Optional[str], colorscale: str, show: bool = True):
        """
        Add heat consumers to plot as colored lines.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        if not hasattr(self.net, 'heat_consumer') or len(self.net.heat_consumer) == 0:
            return
            
        gdf_junctions = self._get_junction_geodata()
        
        # Get parameter values for color mapping if needed
        vmin, vmax = None, None
        if parameter and hasattr(self.net, 'res_heat_consumer'):
            # Collect parameter values using helper method (handles calculated parameters)
            param_values = []
            for idx in self.net.heat_consumer.index:
                value = self._get_parameter_value(self.net.res_heat_consumer, idx, parameter)
                if value is not None:
                    param_values.append(value)
            
            if param_values:
                vmin, vmax = min(param_values), max(param_values)
                if vmax - vmin < 1e-10:
                    vmax = vmin + 1
            
            # Add dummy trace for colorbar
            self.fig.add_trace(go.Scattermapbox(
                lat=[gdf_junctions.geometry.y.mean()],
                lon=[gdf_junctions.geometry.x.mean()],
                mode='markers',
                marker=dict(
                    size=0.1,
                    color=[vmin, vmax],
                    colorscale=colorscale,
                    showscale=True,
                    cmin=vmin,
                    cmax=vmax,
                    colorbar=dict(
                        title=dict(
                            text=self._get_parameter_label(parameter),
                            side='right',
                            font=dict(size=12)
                        ),
                        x=1.0,
                        xanchor='left',
                        thickness=15,
                        len=0.6,
                        y=0.5,
                        yanchor='middle'
                    )
                ),
                showlegend=False,
                hoverinfo='skip',
                visible=show
            ))
        
        for i, idx in enumerate(self.net.heat_consumer.index):
            hc_data = self.net.heat_consumer.loc[idx]
            
            try:
                from_coords = gdf_junctions.loc[hc_data['from_junction']].geometry
                to_coords = gdf_junctions.loc[hc_data['to_junction']].geometry
            except KeyError:
                continue
            
            # Calculate midpoint for better hover
            mid_lat = (from_coords.y + to_coords.y) / 2
            mid_lon = (from_coords.x + to_coords.x) / 2
            
            # Hover text
            hover_text = f"<b>{hc_data['name']}</b><br>"
            hover_text += f"Wärmebedarf: {hc_data['qext_w']/1000:.1f} kW<br>"
            
            if hasattr(self.net, 'res_heat_consumer'):
                res = self.net.res_heat_consumer.loc[idx]
                if 'mdot_from_kg_per_s' in res.index:
                    hover_text += f"Massenstrom: {res['mdot_from_kg_per_s']:.2f} kg/s<br>"
                if 't_from_k' in res.index:
                    hover_text += f"Vorlauftemp.: {res['t_from_k'] - 273.15:.1f} °C<br>"
                if 't_to_k' in res.index:
                    hover_text += f"Rücklauftemp.: {res['t_to_k'] - 273.15:.1f} °C<br>"
                if 'dt_k' in res.index:
                    hover_text += f"ΔT: {res['dt_k']:.1f} K<br>"
                elif 't_from_k' in res.index and 't_to_k' in res.index:
                    hover_text += f"ΔT: {res['t_from_k'] - res['t_to_k']:.1f} K<br>"
                if 'p_from_bar' in res.index:
                    hover_text += f"Vorlaufdruck: {res['p_from_bar']:.2f} bar<br>"
                if 'p_to_bar' in res.index:
                    hover_text += f"Rücklaufdruck: {res['p_to_bar']:.2f} bar<br>"
                if 'deltap_bar' in res.index:
                    hover_text += f"Δp: {res['deltap_bar']:.2f} bar<br>"
                elif 'p_from_bar' in res.index and 'p_to_bar' in res.index:
                    hover_text += f"Δp: {res['p_from_bar'] - res['p_to_bar']:.2f} bar<br>"
            
            # Color based on parameter
            if parameter and vmin is not None:
                value = self._get_parameter_value(self.net.res_heat_consumer, idx, parameter)
                if value is not None:
                    norm_value = (value - vmin) / (vmax - vmin) if (vmax - vmin) > 0 else 0
                    color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
                    hover_text += f"{self._get_parameter_label(parameter)}: {value:.2f}<br>"
                else:
                    color = '#e74c3c'  # Default if value not available
            else:
                color = '#e74c3c'  # Red for heat consumers
            
            # Add line with hover (using invisible markers for hover detection)
            self.fig.add_trace(go.Scattermapbox(
                lat=[from_coords.y, mid_lat, to_coords.y],
                lon=[from_coords.x, mid_lon, to_coords.x],
                mode='lines+markers',
                line=dict(width=5, color=color),
                marker=dict(size=0.1, color=color),  # Invisible markers for hover
                text=[hover_text, hover_text, hover_text],
                hovertemplate='%{text}<extra></extra>',
                legendgroup='heat_consumers',
                name='heat_consumer',
                showlegend=(i == 0),
                visible=show
            ))
    
    def _add_pumps(self, parameter: Optional[str], colorscale: str, show: bool = True):
        """
        Add circulation pumps to plot as colored lines.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        # Check for both pump types
        pump_types = []
        if hasattr(self.net, 'circ_pump_pressure') and len(self.net.circ_pump_pressure) > 0:
            pump_types.append(('circ_pump_pressure', 'res_circ_pump_pressure'))
        if hasattr(self.net, 'circ_pump_mass') and len(self.net.circ_pump_mass) > 0:
            pump_types.append(('circ_pump_mass', 'res_circ_pump_mass'))
        
        if not pump_types:
            return
            
        gdf_junctions = self._get_junction_geodata()
        
        # Check if we need to show colorbar for parameter
        vmin, vmax = None, None
        if parameter:
            # Collect all parameter values from all pump types using helper method
            all_values = []
            for pump_table, res_table in pump_types:
                if hasattr(self.net, res_table):
                    res_df = getattr(self.net, res_table)
                    pump_df = getattr(self.net, pump_table)
                    for idx in pump_df.index:
                        value = self._get_parameter_value(res_df, idx, parameter)
                        if value is not None:
                            all_values.append(value)
            
            if all_values:
                vmin, vmax = min(all_values), max(all_values)
                if vmax - vmin < 1e-10:
                    vmax = vmin + 1
                
                # Add dummy trace for colorbar
                self.fig.add_trace(go.Scattermapbox(
                    lat=[gdf_junctions.geometry.y.mean()],
                    lon=[gdf_junctions.geometry.x.mean()],
                    mode='markers',
                    marker=dict(
                        size=0.1,
                        color=[vmin, vmax],
                        colorscale=colorscale,
                        showscale=True,
                        cmin=vmin,
                        cmax=vmax,
                        colorbar=dict(
                            title=dict(
                                text=self._get_parameter_label(parameter),
                                side='right',
                                font=dict(size=12)
                            ),
                            x=1.0,
                            xanchor='left',
                            thickness=15,
                            len=0.6,
                            y=0.5,
                            yanchor='middle'
                        )
                    ),
                    showlegend=False,
                    hoverinfo='skip',
                    visible=show
                ))
        
        first_pump = True
        
        for pump_table, res_table in pump_types:
            pump_df = getattr(self.net, pump_table)
            
            for idx in pump_df.index:
                pump_data = pump_df.loc[idx]
                
                # Try to get coordinates - different pump types use different column names
                try:
                    if 'from_junction' in pump_data.index and 'to_junction' in pump_data.index:
                        from_coords = gdf_junctions.loc[pump_data['from_junction']].geometry
                        to_coords = gdf_junctions.loc[pump_data['to_junction']].geometry
                    elif 'flow_junction' in pump_data.index and 'return_junction' in pump_data.index:
                        from_coords = gdf_junctions.loc[pump_data['flow_junction']].geometry
                        to_coords = gdf_junctions.loc[pump_data['return_junction']].geometry
                    else:
                        continue
                except (KeyError, IndexError):
                    continue
                
                # Calculate midpoint for better hover
                mid_lat = (from_coords.y + to_coords.y) / 2
                mid_lon = (from_coords.x + to_coords.x) / 2
                
                # Hover text
                hover_text = f"<b>{pump_data['name']}</b><br>"
                
                # Get result data
                if hasattr(self.net, res_table):
                    try:
                        res = getattr(self.net, res_table).loc[idx]
                        
                        if 'mdot_from_kg_per_s' in res.index:
                            hover_text += f"Massenstrom: {res['mdot_from_kg_per_s']:.2f} kg/s<br>"
                        if 't_from_k' in res.index:
                            hover_text += f"Vorlauftemp.: {res['t_to_k'] - 273.15:.1f} °C<br>"
                        if 't_to_k' in res.index:
                            hover_text += f"Rücklauftemp.: {res['t_from_k'] - 273.15:.1f} °C<br>"
                        if 'dt_k' in res.index:
                            hover_text += f"ΔT: {res['dt_k']:.1f} K<br>"
                        elif 't_from_k' in res.index and 't_to_k' in res.index:
                            dt = res['t_to_k'] - res['t_from_k']
                            hover_text += f"ΔT: {dt:.1f} K<br>"
                        if 'p_from_bar' in res.index:
                            hover_text += f"Vorlaufdruck: {res['p_to_bar']:.2f} bar<br>"
                        if 'p_to_bar' in res.index:
                            hover_text += f"Rücklaufdruck: {res['p_from_bar']:.2f} bar<br>"
                        if 'deltap_bar' in res.index:
                            hover_text += f"Druckanhebung: {res['deltap_bar']:.2f} bar<br>"
                        elif 'p_from_bar' in res.index and 'p_to_bar' in res.index:
                            deltap = res['p_to_bar'] - res['p_from_bar']
                            hover_text += f"Druckanhebung: {deltap:.2f} bar<br>"
                    except (KeyError, IndexError):
                        pass
                
                # Color based on parameter
                if parameter and vmin is not None:
                    try:
                        res_df = getattr(self.net, res_table)
                        value = self._get_parameter_value(res_df, idx, parameter)
                        if value is not None:
                            norm_value = (value - vmin) / (vmax - vmin) if (vmax - vmin) > 0 else 0
                            pump_color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
                            hover_text += f"{self._get_parameter_label(parameter)}: {value:.2f}<br>"
                        else:
                            pump_color = '#27ae60'
                    except (KeyError, IndexError):
                        pump_color = '#27ae60'
                else:
                    pump_color = '#27ae60'  # Default green
                
                # Add line with hover (using invisible markers for hover detection)
                self.fig.add_trace(go.Scattermapbox(
                    lat=[from_coords.y, mid_lat, to_coords.y],
                    lon=[from_coords.x, mid_lon, to_coords.x],
                    mode='lines+markers',
                    line=dict(width=5, color=pump_color),
                    marker=dict(size=0.1, color=pump_color),  # Invisible markers for hover
                    text=[hover_text, hover_text, hover_text],
                    hovertemplate='%{text}<extra></extra>',
                    legendgroup='pumps',
                    name='circ_pump',
                    showlegend=first_pump,
                    visible=show
                ))
                first_pump = False
    
    def _add_flow_controls(self, parameter: Optional[str], colorscale: str, show: bool = True):
        """
        Add flow control components to plot as colored lines.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        if not hasattr(self.net, 'flow_control') or len(self.net.flow_control) == 0:
            return
            
        gdf_junctions = self._get_junction_geodata()
        
        # Get parameter values for color mapping if needed
        vmin, vmax = None, None
        if parameter and hasattr(self.net, 'res_flow_control') and parameter in self.net.res_flow_control.columns:
            param_values = self.net.res_flow_control[parameter].values
            vmin, vmax = param_values.min(), param_values.max()
            if vmax - vmin < 1e-10:
                vmax = vmin + 1
            
            # Add dummy trace for colorbar
            self.fig.add_trace(go.Scattermapbox(
                lat=[gdf_junctions.geometry.y.mean()],
                lon=[gdf_junctions.geometry.x.mean()],
                mode='markers',
                marker=dict(
                    size=0.1,
                    color=[vmin, vmax],
                    colorscale=colorscale,
                    showscale=True,
                    cmin=vmin,
                    cmax=vmax,
                    colorbar=dict(
                        title=dict(
                            text=self._get_parameter_label(parameter),
                            side='right',
                            font=dict(size=12)
                        ),
                        x=1.0,
                        xanchor='left',
                        thickness=15,
                        len=0.6,
                        y=0.5,
                        yanchor='middle'
                    )
                ),
                showlegend=False,
                hoverinfo='skip',
                visible=show
            ))
        
        for i, idx in enumerate(self.net.flow_control.index):
            fc_data = self.net.flow_control.loc[idx]
            
            try:
                from_coords = gdf_junctions.loc[fc_data['from_junction']].geometry
                to_coords = gdf_junctions.loc[fc_data['to_junction']].geometry
            except KeyError:
                continue
            
            # Calculate midpoint for better hover
            mid_lat = (from_coords.y + to_coords.y) / 2
            mid_lon = (from_coords.x + to_coords.x) / 2
            
            # Hover text
            hover_text = f"<b>{fc_data['name']}</b><br>"
            
            if 'controlled_mdot_kg_per_s' in fc_data.index:
                hover_text += f"Soll-Massenstrom: {fc_data['controlled_mdot_kg_per_s']:.2f} kg/s<br>"
            
            if hasattr(self.net, 'res_flow_control'):
                try:
                    res = self.net.res_flow_control.loc[idx]
                    if 'mdot_from_kg_per_s' in res.index:
                        hover_text += f"Massenstrom: {res['mdot_from_kg_per_s']:.2f} kg/s<br>"
                    if 'p_from_bar' in res.index:
                        hover_text += f"Vorlaufdruck: {res['p_from_bar']:.2f} bar<br>"
                    if 'p_to_bar' in res.index:
                        hover_text += f"Rücklaufdruck: {res['p_to_bar']:.2f} bar<br>"
                    if 'deltap_bar' in res.index:
                        hover_text += f"Druckdifferenz: {res['deltap_bar']:.2f} bar<br>"
                except (KeyError, IndexError):
                    pass
            
            # Color based on parameter
            if parameter and vmin is not None:
                try:
                    value = self.net.res_flow_control.loc[idx, parameter]
                    norm_value = (value - vmin) / (vmax - vmin) if (vmax - vmin) > 0 else 0
                    fc_color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
                    hover_text += f"{self._get_parameter_label(parameter)}: {value:.2f}<br>"
                except (KeyError, IndexError):
                    fc_color = '#9b59b6'
            else:
                fc_color = '#9b59b6'  # Default purple
            
            # Add line with hover (using invisible markers for hover detection)
            self.fig.add_trace(go.Scattermapbox(
                lat=[from_coords.y, mid_lat, to_coords.y],
                lon=[from_coords.x, mid_lon, to_coords.x],
                mode='lines+markers',
                line=dict(width=5, color=fc_color),
                marker=dict(size=0.1, color=fc_color),  # Invisible markers for hover
                text=[hover_text, hover_text, hover_text],
                hovertemplate='%{text}<extra></extra>',
                legendgroup='flow_controls',
                name='flow_control',
                showlegend=(i == 0),
                visible=show
            ))
    
    def _configure_layout(self, gdf_junctions: gpd.GeoDataFrame, basemap_style: str):
        """
        Configure plot layout, basemap, and zoom level.
        
        :param gdf_junctions: Junction geodata in WGS84
        :type gdf_junctions: gpd.GeoDataFrame
        :param basemap_style: Mapbox basemap style
        :type basemap_style: str
        """
        # Calculate center and zoom
        center_lat = gdf_junctions.geometry.y.mean()
        center_lon = gdf_junctions.geometry.x.mean()
        
        # Calculate appropriate zoom level based on bounds
        lat_range = gdf_junctions.geometry.y.max() - gdf_junctions.geometry.y.min()
        lon_range = gdf_junctions.geometry.x.max() - gdf_junctions.geometry.x.min()
        zoom = self._calculate_zoom(lat_range, lon_range)
        
        self.fig.update_layout(
            mapbox=dict(
                style=basemap_style,
                center=dict(lat=center_lat, lon=center_lon),
                zoom=zoom
            ),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="#2c3e50",
                borderwidth=1,
                font=dict(size=11)
            ),
            margin=dict(l=0, r=60, t=40, b=0),
            height=600,
            hovermode='closest',
            modebar=dict(
                orientation='v',
                bgcolor='rgba(255, 255, 255, 0.8)',
                color='#2c3e50',
                activecolor='#3498db'
            )
        )
    
    def _get_parameter_value(self, res_df, idx, parameter):
        """
        Get parameter value, calculating dt_k or dp_bar if needed.
        
        :param res_df: Result DataFrame
        :type res_df: pd.DataFrame
        :param idx: Component index
        :type idx: int
        :param parameter: Parameter name
        :type parameter: str
        :return: Parameter value or None
        :rtype: Optional[float]
        """
        if parameter == 'dt_k':
            # Calculate temperature difference
            if 't_from_k' in res_df.columns and 't_to_k' in res_df.columns:
                return res_df.loc[idx, 't_from_k'] - res_df.loc[idx, 't_to_k']
        elif parameter == 'dp_bar':
            # Calculate pressure difference
            if 'p_from_bar' in res_df.columns and 'p_to_bar' in res_df.columns:
                return res_df.loc[idx, 'p_from_bar'] - res_df.loc[idx, 'p_to_bar']
        elif parameter in res_df.columns:
            # Direct column access
            return res_df.loc[idx, parameter]
        return None
    
    def _calculate_zoom(self, lat_range: float, lon_range: float) -> int:
        """
        Calculate appropriate zoom level based on coordinate ranges.
        
        :param lat_range: Latitude range in degrees
        :type lat_range: float
        :param lon_range: Longitude range in degrees
        :type lon_range: float
        :return: Zoom level (5-15)
        :rtype: int
        """
        max_range = max(lat_range, lon_range)
        if max_range > 10:
            return 5
        elif max_range > 5:
            return 8
        elif max_range > 1:
            return 10
        elif max_range > 0.5:
            return 11
        elif max_range > 0.1:
            return 13
        else:
            return 15
    
    def _get_parameter_label(self, parameter: str) -> str:
        """
        Get formatted German label for parameter.
        
        :param parameter: Parameter name
        :type parameter: str
        :return: Formatted label with units
        :rtype: str
        """
        labels = {
            'p_bar': 'Druck [bar]',
            't_k': 'Temperatur [K]',
            'v_mean_m_per_s': 'Geschwindigkeit [m/s]',
            'mdot_from_kg_per_s': 'Massenstrom [kg/s]',
            'reynolds': 'Reynolds-Zahl [-]',
            'lambda': 'Reibungsbeiwert [-]',
            'qext_w': 'Wärmebedarf [W]',
            'deltap_bar': 'Druckdifferenz [bar]'
        }
        return labels.get(parameter, parameter)
    
    def export_html(self, filename: str):
        """
        Export plot to interactive HTML file.
        
        :param filename: Output HTML filename
        :type filename: str
        """
        if self.fig:
            self.fig.write_html(filename)
    
    def export_png(self, filename: str, width: int = 1920, height: int = 1080):
        """
        Export plot to PNG (requires kaleido package).
        
        :param filename: Output PNG filename
        :type filename: str
        :param width: Image width in pixels, defaults to 1920
        :type width: int
        :param height: Image height in pixels, defaults to 1080
        :type height: int
        """
        if self.fig:
            self.fig.write_image(filename, width=width, height=height)