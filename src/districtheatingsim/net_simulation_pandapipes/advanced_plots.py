"""
Advanced Plots for DistrictHeatingSim
=====================================

Funktionsfähige erweiterte Plot-Funktionen für pandapipes Netzwerke.
Diese Version umgeht die API-Limitierungen der pandapipes Collection-Funktionen
und bietet robuste, produktionsreife Plotting-Alternativen.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Features:

- Druckverteilungsplots mit Statistiken
- Temperaturverteilungsplots  
- Geschwindigkeitsanalyse
- Druckprofile
- Interaktive Dashboards
- Drop-in Ersatz für config_plot
"""

import numpy as np
import matplotlib.pyplot as plt
import pandapipes as pp
import pandapipes.plotting as pp_plot
import pandas as pd
from typing import Optional, Dict, List


def create_pressure_plot(net, ax: Optional[plt.Axes] = None, show_colorbar: bool = True):
    """
    Pressure distribution plot with data-driven colors and statistics.
    
    :param net: Pandapipes network with simulation results
    :type net: pandapipes.pandapipesNet
    :param ax: Matplotlib axis, creates new if None
    :type ax: Optional[plt.Axes]
    :param show_colorbar: Display pressure colorbar, defaults to True
    :type show_colorbar: bool
    :return: Matplotlib axis with pressure plot
    :rtype: plt.Axes
    
    .. note::
       Blue (low pressure) to red (high pressure). Plots junctions, pipes, consumers, pumps.
       Includes pressure range statistics.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))
    
    # Check if results are available
    if not hasattr(net, 'res_junction') or net.res_junction.empty:
        ax.text(0.5, 0.5, 'Keine Simulationsergebnisse verfügbar', 
                transform=ax.transAxes, ha='center', va='center')
        return ax
    
    try:
        import matplotlib.cm as cm
        
        # Get pressure data
        pressures = net.res_junction['p_bar']
        p_min, p_max = pressures.min(), pressures.max()
        
        # Create pressure colormap (blue = low, red = high)
        pressure_cmap = cm.get_cmap('coolwarm')
        pressure_norm = plt.Normalize(vmin=p_min, vmax=p_max)
        
        # Plot junctions with pressure-based colors
        if hasattr(net, 'junction_geodata') and not net.junction_geodata.empty:
            for idx, junction in net.junction.iterrows():
                if idx in net.junction_geodata.index:
                    x = net.junction_geodata.loc[idx, 'x']
                    y = net.junction_geodata.loc[idx, 'y']
                    pressure = net.res_junction.loc[idx, 'p_bar']
                    color = pressure_cmap(pressure_norm(pressure))
                    ax.scatter(x, y, c=[color], s=100, edgecolors='black', linewidth=1, zorder=5)
        
        # Plot pipes with pressure gradient colors
        if hasattr(net, 'res_pipe') and not net.res_pipe.empty and hasattr(net, 'junction_geodata'):
            for idx, pipe in net.pipe.iterrows():
                from_junction = pipe['from_junction']
                to_junction = pipe['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    # Use average pressure of connected junctions
                    p_from = net.res_junction.loc[from_junction, 'p_bar']
                    p_to = net.res_junction.loc[to_junction, 'p_bar']
                    avg_pressure = (p_from + p_to) / 2
                    pipe_color = pressure_cmap(pressure_norm(avg_pressure))
                    
                    ax.plot([from_x, to_x], [from_y, to_y], 
                           color=pipe_color, linewidth=4, alpha=0.8, zorder=2)
        
        # Plot heat consumers
        if hasattr(net, 'heat_consumer') and len(net.heat_consumer) > 0 and hasattr(net, 'junction_geodata'):
            for idx, consumer in net.heat_consumer.iterrows():
                from_junction = consumer['from_junction']
                to_junction = consumer['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    mid_x = (from_x + to_x) / 2
                    mid_y = (from_y + to_y) / 2
                    ax.scatter(mid_x, mid_y, c='green', s=200, marker='s', 
                             edgecolors='black', linewidth=2, zorder=6)
        
        # Plot pumps
        if hasattr(net, 'circ_pump_const_pressure') and len(net.circ_pump_const_pressure) > 0 and hasattr(net, 'junction_geodata'):
            for idx, pump in net.circ_pump_const_pressure.iterrows():
                from_junction = pump['from_junction']
                to_junction = pump['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    mid_x = (from_x + to_x) / 2
                    mid_y = (from_y + to_y) / 2
                    ax.scatter(mid_x, mid_y, c='orange', s=200, marker='o', 
                             edgecolors='black', linewidth=2, zorder=6)
        
        # Set axis limits
        coords = net.junction_geodata
        if not coords.empty:
            margin = 5
            ax.set_xlim(coords.x.min() - margin, coords.x.max() + margin)
            ax.set_ylim(coords.y.min() - margin, coords.y.max() + margin)
        
        # Add colorbar
        if show_colorbar and p_max > p_min:
            sm = cm.ScalarMappable(cmap=pressure_cmap, norm=pressure_norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
            cbar.set_label('Druck [bar]', fontsize=12)
        
        ax.set_title('Druckverteilung im Fernwärmenetz (datenbasiert)', fontsize=14, fontweight='bold')
        
        # Add pressure statistics
        stats_text = f'Druckbereich: {p_min:.2f} - {p_max:.2f} bar'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                verticalalignment='top')
        
    except Exception as e:
        ax.text(0.5, 0.5, f'Fehler beim Plotten: {str(e)}', 
                transform=ax.transAxes, ha='center', va='center')
    
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    return ax


def create_temperature_plot(net, ax: Optional[plt.Axes] = None):
    """
    Temperature distribution plot with data-driven colors and statistics.
    
    :param net: Pandapipes network with simulation results
    :type net: pandapipes.pandapipesNet
    :param ax: Matplotlib axis, creates new if None
    :type ax: Optional[plt.Axes]
    :return: Matplotlib axis with temperature plot
    :rtype: plt.Axes
    
    .. note::
       Plasma colormap (blue=cold, red=hot). Converts Kelvin to Celsius.
       Shows temperature range statistics.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))
    
    # Check if results are available
    if not hasattr(net, 'res_junction') or net.res_junction.empty:
        ax.text(0.5, 0.5, 'Keine Simulationsergebnisse verfügbar', 
                transform=ax.transAxes, ha='center', va='center')
        return ax
    
    try:
        import matplotlib.cm as cm
        
        # Get temperature data (convert to Celsius)
        temperatures_k = net.res_junction['t_k']
        temperatures_c = temperatures_k - 273.15
        t_min, t_max = temperatures_c.min(), temperatures_c.max()
        
        # Create temperature colormap (blue = cold, red = hot)
        temp_cmap = cm.get_cmap('plasma')
        temp_norm = plt.Normalize(vmin=t_min, vmax=t_max)
        
        # Plot junctions with temperature-based colors
        if hasattr(net, 'junction_geodata') and not net.junction_geodata.empty:
            for idx, junction in net.junction.iterrows():
                if idx in net.junction_geodata.index:
                    x = net.junction_geodata.loc[idx, 'x']
                    y = net.junction_geodata.loc[idx, 'y']
                    temp_c = net.res_junction.loc[idx, 't_k'] - 273.15
                    color = temp_cmap(temp_norm(temp_c))
                    ax.scatter(x, y, c=[color], s=100, edgecolors='black', linewidth=1, zorder=5)
        
        # Plot pipes with temperature gradient colors
        if hasattr(net, 'res_pipe') and not net.res_pipe.empty and hasattr(net, 'junction_geodata'):
            for idx, pipe in net.pipe.iterrows():
                from_junction = pipe['from_junction']
                to_junction = pipe['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    # Use pipe temperature data if available
                    if 't_from_k' in net.res_pipe.columns and 't_to_k' in net.res_pipe.columns:
                        t_from = net.res_pipe.loc[idx, 't_from_k'] - 273.15
                        t_to = net.res_pipe.loc[idx, 't_to_k'] - 273.15
                        avg_temp = (t_from + t_to) / 2
                    else:
                        # Fallback: use junction temperatures
                        t_from = net.res_junction.loc[from_junction, 't_k'] - 273.15
                        t_to = net.res_junction.loc[to_junction, 't_k'] - 273.15
                        avg_temp = (t_from + t_to) / 2
                    
                    pipe_color = temp_cmap(temp_norm(avg_temp))
                    ax.plot([from_x, to_x], [from_y, to_y], 
                           color=pipe_color, linewidth=4, alpha=0.8, zorder=2)
        
        # Plot heat consumers (blue = cooling effect)
        if hasattr(net, 'heat_consumer') and len(net.heat_consumer) > 0 and hasattr(net, 'junction_geodata'):
            for idx, consumer in net.heat_consumer.iterrows():
                from_junction = consumer['from_junction']
                to_junction = consumer['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    mid_x = (from_x + to_x) / 2
                    mid_y = (from_y + to_y) / 2
                    ax.scatter(mid_x, mid_y, c='blue', s=200, marker='s', 
                             edgecolors='white', linewidth=2, zorder=6)
        
        # Plot pumps
        if hasattr(net, 'circ_pump_const_pressure') and len(net.circ_pump_const_pressure) > 0 and hasattr(net, 'junction_geodata'):
            for idx, pump in net.circ_pump_const_pressure.iterrows():
                from_junction = pump['from_junction']
                to_junction = pump['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    mid_x = (from_x + to_x) / 2
                    mid_y = (from_y + to_y) / 2
                    ax.scatter(mid_x, mid_y, c='green', s=200, marker='o', 
                             edgecolors='black', linewidth=2, zorder=6)
        
        # Set axis limits
        coords = net.junction_geodata
        if not coords.empty:
            margin = 5
            ax.set_xlim(coords.x.min() - margin, coords.x.max() + margin)
            ax.set_ylim(coords.y.min() - margin, coords.y.max() + margin)
        
        # Add colorbar
        if t_max > t_min:
            sm = cm.ScalarMappable(cmap=temp_cmap, norm=temp_norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
            cbar.set_label('Temperatur [°C]', fontsize=12)
        
        ax.set_title('Temperaturverteilung im Fernwärmenetz (datenbasiert)', fontsize=14, fontweight='bold')
        
        # Add temperature statistics
        stats_text = f'Temperaturbereich: {t_min:.1f} - {t_max:.1f} °C'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
                verticalalignment='top')
        
    except Exception as e:
        ax.text(0.5, 0.5, f'Fehler beim Plotten: {str(e)}', 
                transform=ax.transAxes, ha='center', va='center')
    
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    return ax


def create_velocity_plot(net, ax: Optional[plt.Axes] = None):
    """
    Velocity distribution plot for pipe flow analysis.
    
    :param net: Pandapipes network with simulation results
    :type net: pandapipes.pandapipesNet
    :param ax: Matplotlib axis, creates new if None
    :type ax: Optional[plt.Axes]
    :return: Matplotlib axis with velocity plot
    :rtype: plt.Axes
    
    .. note::
       Viridis colormap (green=low, yellow=high). Plots pipe velocities with colorbar.
       Includes velocity range statistics.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))
    
    # Check if results are available
    if not hasattr(net, 'res_pipe') or net.res_pipe.empty:
        ax.text(0.5, 0.5, 'Keine Rohrleitungsergebnisse verfügbar', 
                transform=ax.transAxes, ha='center', va='center')
        return ax
    
    try:
        import matplotlib.cm as cm
        
        # Plot junctions in neutral color
        if hasattr(net, 'junction_geodata') and not net.junction_geodata.empty:
            for idx, junction in net.junction.iterrows():
                if idx in net.junction_geodata.index:
                    x = net.junction_geodata.loc[idx, 'x']
                    y = net.junction_geodata.loc[idx, 'y']
                    ax.scatter(x, y, c='black', s=80, edgecolors='gray', linewidth=1, zorder=5)
        
        # Plot pipes with velocity-based colors
        if 'v_mean_m_per_s' in net.res_pipe.columns and hasattr(net, 'junction_geodata'):
            velocities = net.res_pipe['v_mean_m_per_s']
            v_min, v_max = velocities.min(), velocities.max()
            
            # Create velocity colormap (green = low, red = high)
            vel_cmap = cm.get_cmap('viridis')
            vel_norm = plt.Normalize(vmin=v_min, vmax=v_max)
            
            for idx, pipe in net.pipe.iterrows():
                from_junction = pipe['from_junction']
                to_junction = pipe['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    velocity = net.res_pipe.loc[idx, 'v_mean_m_per_s']
                    pipe_color = vel_cmap(vel_norm(velocity))
                    # Thicker lines for higher velocities
                    line_width = 2 + (velocity / v_max) * 6
                    ax.plot([from_x, to_x], [from_y, to_y], 
                           color=pipe_color, linewidth=line_width, alpha=0.8, zorder=2)
            
            # Add colorbar
            if v_max > v_min:
                sm = cm.ScalarMappable(cmap=vel_cmap, norm=vel_norm)
                sm.set_array([])
                cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
                cbar.set_label('Geschwindigkeit [m/s]', fontsize=12)
            
            # Add velocity statistics
            stats_text = f'Geschwindigkeitsbereich: {v_min:.3f} - {v_max:.3f} m/s'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8),
                    verticalalignment='top')
        else:
            # Fallback if no velocity data
            if hasattr(net, 'junction_geodata'):
                for idx, pipe in net.pipe.iterrows():
                    from_junction = pipe['from_junction']
                    to_junction = pipe['to_junction']
                    if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                        from_x = net.junction_geodata.loc[from_junction, 'x']
                        from_y = net.junction_geodata.loc[from_junction, 'y']
                        to_x = net.junction_geodata.loc[to_junction, 'x']
                        to_y = net.junction_geodata.loc[to_junction, 'y']
                        ax.plot([from_x, to_x], [from_y, to_y], 
                               'purple', linewidth=3, alpha=0.7, zorder=1)
        
        # Plot heat consumers
        if hasattr(net, 'heat_consumer') and len(net.heat_consumer) > 0 and hasattr(net, 'junction_geodata'):
            for idx, consumer in net.heat_consumer.iterrows():
                from_junction = consumer['from_junction']
                to_junction = consumer['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    mid_x = (from_x + to_x) / 2
                    mid_y = (from_y + to_y) / 2
                    ax.scatter(mid_x, mid_y, c='blue', s=150, marker='s', 
                             edgecolors='white', linewidth=2, zorder=6)
        
        # Plot pumps
        if hasattr(net, 'circ_pump_const_pressure') and len(net.circ_pump_const_pressure) > 0 and hasattr(net, 'junction_geodata'):
            for idx, pump in net.circ_pump_const_pressure.iterrows():
                from_junction = pump['from_junction']
                to_junction = pump['to_junction']
                if from_junction in net.junction_geodata.index and to_junction in net.junction_geodata.index:
                    from_x = net.junction_geodata.loc[from_junction, 'x']
                    from_y = net.junction_geodata.loc[from_junction, 'y']
                    to_x = net.junction_geodata.loc[to_junction, 'x']
                    to_y = net.junction_geodata.loc[to_junction, 'y']
                    mid_x = (from_x + to_x) / 2
                    mid_y = (from_y + to_y) / 2
                    ax.scatter(mid_x, mid_y, c='orange', s=150, marker='o', 
                             edgecolors='black', linewidth=2, zorder=6)
        
        # Set axis limits
        coords = net.junction_geodata
        if not coords.empty:
            margin = 5
            ax.set_xlim(coords.x.min() - margin, coords.x.max() + margin)
            ax.set_ylim(coords.y.min() - margin, coords.y.max() + margin)
        
        ax.set_title('Geschwindigkeitsverteilung in Rohrleitungen (datenbasiert)', fontsize=14, fontweight='bold')
        
    except Exception as e:
        ax.text(0.5, 0.5, f'Fehler beim Plotten: {str(e)}', 
                transform=ax.transAxes, ha='center', va='center')
    
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    return ax


def create_pressure_profile(net, ax: Optional[plt.Axes] = None):
    """
    Pressure profile along network path showing pressure drop.
    
    :param net: Pandapipes network with simulation results
    :type net: pandapipes.pandapipesNet
    :param ax: Matplotlib axis, creates new if None
    :type ax: Optional[plt.Axes]
    :return: Matplotlib axis with pressure profile
    :rtype: plt.Axes
    
    .. note::
       Distance vs pressure plot. Shows total pressure drop statistics.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    
    try:
        # Use pandapipes pressure profile function
        pp_plot.plot_pressure_profile(net, ax=ax, 
                                     xlabel='Entfernung vom Startpunkt [km]',
                                     ylabel='Druck [bar]',
                                     pipe_color='steelblue',
                                     junction_color='darkblue')
        
        ax.set_title('Druckprofil im Fernwärmenetz', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add statistics
        if hasattr(net, 'res_junction'):
            pressures = net.res_junction['p_bar']
            pressure_drop = pressures.max() - pressures.min()
            stats_text = f'Gesamtdruckverlust: {pressure_drop:.2f} bar'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                    verticalalignment='top')
        
    except Exception as e:
        ax.text(0.5, 0.5, f'Druckprofil nicht verfügbar\nFehler: {str(e)}', 
                transform=ax.transAxes, ha='center', va='center')
        ax.set_title('Druckprofil - Fehler', fontsize=14, fontweight='bold')
    
    return ax


def create_comparison_dashboard(net, figsize=(16, 12)):
    """
    Comprehensive analysis dashboard with 4 plot types.
    
    :param net: Pandapipes network with simulation results
    :type net: pandapipes.pandapipesNet
    :param figsize: Figure size tuple (width, height), defaults to (16, 12)
    :type figsize: tuple
    :return: Figure and axes array (2x2)
    :rtype: Tuple[plt.Figure, np.ndarray]
    
    .. note::
       4 subplots: topology, pressure profile, pressure distribution, temperature distribution.
       Includes network statistics text box.
    """
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.suptitle('Fernwärmenetz Analyse Dashboard', fontsize=16, fontweight='bold')
    
    # 1. Original network view
    try:
        pp_plot.simple_plot(net, ax=axes[0,0], show_plot=False,
                           junction_size=0.02, heat_consumer_size=0.1, pump_size=0.1)
        axes[0,0].set_title('Netzwerk Topologie')
    except:
        axes[0,0].text(0.5, 0.5, 'Netzwerk Topologie\nnicht verfügbar', 
                      transform=axes[0,0].transAxes, ha='center', va='center')
    
    # 2. Pressure profile
    create_pressure_profile(net, ax=axes[0,1])
    
    # 3. Pressure plot
    create_pressure_plot(net, ax=axes[1,0], show_colorbar=False)
    
    # 4. Temperature plot
    create_temperature_plot(net, ax=axes[1,1])
    
    # Add network statistics
    stats_text = get_network_statistics(net)
    fig.text(0.02, 0.02, stats_text, transform=fig.transFigure,
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
             fontsize=9, verticalalignment='bottom')
    
    plt.tight_layout()
    return fig, axes


def get_network_statistics(net):
    """
    Extract network statistics as formatted text string.
    
    :param net: Pandapipes network
    :type net: pandapipes.pandapipesNet
    :return: Formatted statistics string
    :rtype: str
    
    .. note::
       Returns junction count, pipe count, consumer count, total load [kW], pressure range [bar].
    """
    stats = []
    stats.append("Netzwerk Statistiken:")
    stats.append(f"• Knotenpunkte: {len(net.junction)}")
    stats.append(f"• Rohrleitungen: {len(net.pipe)}")
    
    if hasattr(net, 'heat_consumer') and len(net.heat_consumer) > 0:
        total_demand = net.heat_consumer['qext_w'].sum() / 1000  # kW
        stats.append(f"• Wärmeverbraucher: {len(net.heat_consumer)}")
        stats.append(f"• Gesamtlast: {total_demand:.1f} kW")
    
    if hasattr(net, 'res_junction') and not net.res_junction.empty:
        p_max = net.res_junction['p_bar'].max()
        p_min = net.res_junction['p_bar'].min()
        stats.append(f"• Druckbereich: {p_min:.2f} - {p_max:.2f} bar")
    
    return '\n'.join(stats)


def enhanced_config_plot(net, ax, plot_mode='traditional', **kwargs):
    """
    Enhanced config_plot replacement with multiple visualization modes.
    
    :param net: Pandapipes network to visualize
    :type net: pandapipes.pandapipesNet
    :param ax: Matplotlib axis for plotting
    :type ax: matplotlib.axes.Axes
    :param plot_mode: Mode: 'traditional', 'pressure', 'temperature', 'velocity', 'dashboard'
    :type plot_mode: str
    :param \**kwargs: Additional arguments for plotting functions
    :return: Matplotlib axis (or figure for dashboard mode)
    :rtype: plt.Axes
    
    .. note::
       Drop-in replacement for config_plot. Dashboard mode returns new figure.
    """
    
    if plot_mode == 'traditional':
        # Traditional view - use your existing config_plot if available
        try:
            from districtheatingsim.net_simulation_pandapipes.config_plot import config_plot
            config_plot(net, ax, **kwargs)
        except:
            # Fallback to simple plot
            pp_plot.simple_plot(net, ax=ax, show_plot=False, **kwargs)
            
    elif plot_mode == 'pressure':
        create_pressure_plot(net, ax)
        
    elif plot_mode == 'temperature': 
        create_temperature_plot(net, ax)
        
    elif plot_mode == 'velocity':
        create_velocity_plot(net, ax)
        
    elif plot_mode == 'dashboard':
        # For dashboard, return new figure
        return create_comparison_dashboard(net)
        
    else:
        # Default to traditional
        pp_plot.simple_plot(net, ax=ax, show_plot=False)
    
    return ax