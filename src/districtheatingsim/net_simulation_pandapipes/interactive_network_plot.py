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


import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go

from districtheatingsim.net_simulation_pandapipes.plot_data import (
    available_plot_parameters,
    flow_control_plot_data,
    heat_consumer_plot_data,
    junction_geodata_wgs84,
    junction_plot_data,
    parameter_label,
    parameter_value,
    pipe_plot_data,
    pump_plot_data,
)


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
        
    def _get_available_parameters(self) -> dict[str, list[str]]:
        """
        Get all available parameters for each component type.

        Delegates to the Plotly-free data layer (BACKLOG B1/B3).

        :return: Dict with component types as keys, parameter lists as values
        :rtype: Dict[str, List[str]]
        """
        return available_plot_parameters(self.net)
    
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
        
        for i, (_label, comp_type, param) in enumerate(visualizations):
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
        for i, (label, _comp_type, _param) in enumerate(visualizations):
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
        
        print("[Performance] Interactive plot with dropdown ready!")
        
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
                   parameter: str | None = None,
                   component_type: str | None = None,
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

        Delegates to the Plotly-free data layer (BACKLOG B1/B3).

        :return: GeoDataFrame with junction coordinates in WGS84
        :rtype: gpd.GeoDataFrame
        """
        return junction_geodata_wgs84(self.net, self.crs)
    
    def _add_junctions(self, parameter: str | None, colorscale: str, show: bool = True):
        """
        Add junction nodes to plot with optional parameter coloring.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        data = junction_plot_data(self.net, self.crs, parameter)

        # Color mapping
        if data.values is not None:
            marker = dict(
                size=10,
                color=data.values,
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
            lat=data.lats,
            lon=data.lons,
            mode='markers',
            marker=marker,
            text=data.hover_texts,
            hovertemplate='%{text}<extra></extra>',
            name='junction',
            customdata=data.ids,
            visible=show
        ))
    
    def _add_pipes(self, parameter: str | None, colorscale: str, show: bool = True):
        """
        Add pipes to plot with optional parameter coloring.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        data = pipe_plot_data(self.net, self._get_junction_geodata(), parameter)
        if not data.segments:
            return

        # Add a near-invisible marker carrying the colorbar when colour-coding.
        if data.vmin is not None:
            self.fig.add_trace(go.Scattermapbox(
                lat=[data.center_lat],
                lon=[data.center_lon],
                mode='markers',
                marker=dict(
                    size=0.1,
                    color=[data.vmin],
                    colorscale=colorscale,
                    showscale=True,
                    cmin=data.vmin,
                    cmax=data.vmax,
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
        for i, seg in enumerate(data.segments):
            if data.vmin is not None and seg.value is not None:
                norm_value = (seg.value - data.vmin) / (data.vmax - data.vmin)
                color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
            else:
                color = '#2c3e50'  # Default dark gray

            self.fig.add_trace(go.Scattermapbox(
                lat=[seg.from_lat, seg.mid_lat, seg.to_lat],
                lon=[seg.from_lon, seg.mid_lon, seg.to_lon],
                mode='lines+markers',
                line=dict(width=4, color=color),
                marker=dict(size=0.1, color=color),  # Invisible markers for hover
                text=[seg.hover_text, seg.hover_text, seg.hover_text],
                hovertemplate='%{text}<extra></extra>',
                customdata=[[seg.idx, seg.name]] * 3,  # pipe index/name for click events
                legendgroup='pipes',
                name='pipe',
                showlegend=(i == 0),
                visible=show
            ))
    
    def _add_heat_consumers(self, parameter: str | None, colorscale: str, show: bool = True):
        """
        Add heat consumers to plot as colored lines.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        data = heat_consumer_plot_data(self.net, self._get_junction_geodata(), parameter)
        if not data.segments:
            return

        # Add a near-invisible marker carrying the colorbar when colour-coding.
        if data.vmin is not None:
            self.fig.add_trace(go.Scattermapbox(
                lat=[data.center_lat],
                lon=[data.center_lon],
                mode='markers',
                marker=dict(
                    size=0.1,
                    color=[data.vmin, data.vmax],
                    colorscale=colorscale,
                    showscale=True,
                    cmin=data.vmin,
                    cmax=data.vmax,
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

        for i, seg in enumerate(data.segments):
            if parameter and data.vmin is not None and seg.value is not None:
                span = data.vmax - data.vmin
                norm_value = (seg.value - data.vmin) / span if span > 0 else 0
                color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
            else:
                color = '#e74c3c'  # Red for heat consumers

            self.fig.add_trace(go.Scattermapbox(
                lat=[seg.from_lat, seg.mid_lat, seg.to_lat],
                lon=[seg.from_lon, seg.mid_lon, seg.to_lon],
                mode='lines+markers',
                line=dict(width=5, color=color),
                marker=dict(size=0.1, color=color),  # Invisible markers for hover
                text=[seg.hover_text, seg.hover_text, seg.hover_text],
                hovertemplate='%{text}<extra></extra>',
                legendgroup='heat_consumers',
                name='heat_consumer',
                showlegend=(i == 0),
                visible=show
            ))
    
    def _add_pumps(self, parameter: str | None, colorscale: str, show: bool = True):
        """
        Add circulation pumps to plot as colored lines.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        data = pump_plot_data(self.net, self._get_junction_geodata(), parameter)
        if not data.segments:
            return

        # Add a near-invisible marker carrying the colorbar when colour-coding.
        if data.vmin is not None:
            self.fig.add_trace(go.Scattermapbox(
                lat=[data.center_lat],
                lon=[data.center_lon],
                mode='markers',
                marker=dict(
                    size=0.1,
                    color=[data.vmin, data.vmax],
                    colorscale=colorscale,
                    showscale=True,
                    cmin=data.vmin,
                    cmax=data.vmax,
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

        for i, seg in enumerate(data.segments):
            if parameter and data.vmin is not None and seg.value is not None:
                span = data.vmax - data.vmin
                norm_value = (seg.value - data.vmin) / span if span > 0 else 0
                color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
            else:
                color = '#27ae60'  # Default green

            self.fig.add_trace(go.Scattermapbox(
                lat=[seg.from_lat, seg.mid_lat, seg.to_lat],
                lon=[seg.from_lon, seg.mid_lon, seg.to_lon],
                mode='lines+markers',
                line=dict(width=5, color=color),
                marker=dict(size=0.1, color=color),  # Invisible markers for hover
                text=[seg.hover_text, seg.hover_text, seg.hover_text],
                hovertemplate='%{text}<extra></extra>',
                legendgroup='pumps',
                name='circ_pump',
                showlegend=(i == 0),
                visible=show
            ))
    
    def _add_flow_controls(self, parameter: str | None, colorscale: str, show: bool = True):
        """
        Add flow control components to plot as colored lines.
        
        :param parameter: Parameter for color coding, optional
        :type parameter: Optional[str]
        :param colorscale: Plotly colorscale name
        :type colorscale: str
        :param show: Visibility flag, defaults to True
        :type show: bool
        """
        data = flow_control_plot_data(self.net, self._get_junction_geodata(), parameter)
        if not data.segments:
            return

        # Add a near-invisible marker carrying the colorbar when colour-coding.
        if data.vmin is not None:
            self.fig.add_trace(go.Scattermapbox(
                lat=[data.center_lat],
                lon=[data.center_lon],
                mode='markers',
                marker=dict(
                    size=0.1,
                    color=[data.vmin, data.vmax],
                    colorscale=colorscale,
                    showscale=True,
                    cmin=data.vmin,
                    cmax=data.vmax,
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

        for i, seg in enumerate(data.segments):
            if parameter and data.vmin is not None and seg.value is not None:
                span = data.vmax - data.vmin
                norm_value = (seg.value - data.vmin) / span if span > 0 else 0
                color = px.colors.sample_colorscale(colorscale, [norm_value])[0]
            else:
                color = '#9b59b6'  # Default purple

            self.fig.add_trace(go.Scattermapbox(
                lat=[seg.from_lat, seg.mid_lat, seg.to_lat],
                lon=[seg.from_lon, seg.mid_lon, seg.to_lon],
                mode='lines+markers',
                line=dict(width=5, color=color),
                marker=dict(size=0.1, color=color),  # Invisible markers for hover
                text=[seg.hover_text, seg.hover_text, seg.hover_text],
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
        """Parameter value (incl. derived dt_k/dp_bar). Delegates to the data layer."""
        return parameter_value(res_df, idx, parameter)
    
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
        """German label (with unit) for a parameter. Delegates to the data layer."""
        return parameter_label(parameter)
    
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