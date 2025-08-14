"""
Advanced Plots for DistrictHeatingSim
=====================================

Funktionsfähige erweiterte Plot-Funktionen für pandapipes Netzwerke.
Diese Version umgeht die API-Limitierungen der pandapipes Collection-Funktionen
und bietet robuste, produktionsreife Plotting-Alternativen.

Features:
- Druckverteilungsplots mit Statistiken
- Temperaturverteilungsplots  
- Geschwindigkeitsanalyse
- Druckprofile
- Interaktive Dashboards
- Drop-in Ersatz für config_plot

Author: Dipl.-Ing. (FH) Jonas Pfeiffer  
Date: 2025-08-14
Version: 1.0 (Production Ready)
"""

import numpy as np
import matplotlib.pyplot as plt
import pandapipes as pp
import pandapipes.plotting as pp_plot
import pandas as pd
from typing import Optional, Dict, List


def create_pressure_plot(net, ax: Optional[plt.Axes] = None, show_colorbar: bool = True):
    """Create a pressure-based plot with statistics."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))
    
    # Check if results are available
    if not hasattr(net, 'res_junction') or net.res_junction.empty:
        ax.text(0.5, 0.5, 'Keine Simulationsergebnisse verfügbar', 
                transform=ax.transAxes, ha='center', va='center')
        return ax
    
    try:
        # Use simple_plot with pressure-focused colors
        pp_plot.simple_plot(net, ax=ax, show_plot=False,
                           junction_size=0.02, 
                           pipe_width=3,
                           heat_consumer_size=0.1, 
                           pump_size=0.1,
                           junction_color='red',  # High pressure color
                           pipe_color='blue',
                           heat_consumer_color='green',
                           pump_color='orange')
        
        ax.set_title('Druckverteilung im Fernwärmenetz', fontsize=14, fontweight='bold')
        
        # Add pressure statistics
        pressures = net.res_junction['p_bar']
        stats_text = f'Druckbereich: {pressures.min():.2f} - {pressures.max():.2f} bar'
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
    """Create a temperature-based plot with statistics."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))
    
    # Check if results are available
    if not hasattr(net, 'res_junction') or net.res_junction.empty:
        ax.text(0.5, 0.5, 'Keine Simulationsergebnisse verfügbar', 
                transform=ax.transAxes, ha='center', va='center')
        return ax
    
    try:
        # Use simple plot with temperature-based colors
        pp_plot.simple_plot(net, ax=ax, show_plot=False,
                           junction_size=0.02,
                           pipe_width=3, 
                           heat_consumer_size=0.1,
                           pump_size=0.1,
                           junction_color='red',     # Hot color for supply
                           pipe_color='darkred',     # Temperature focus
                           heat_consumer_color='blue',  # Cold color for consumers
                           pump_color='green')
        
        ax.set_title('Temperaturverteilung im Fernwärmenetz', fontsize=14, fontweight='bold')
        
        # Add temperature statistics
        temperatures = net.res_junction['t_k'] - 273.15  # Convert to Celsius
        stats_text = f'Temperaturbereich: {temperatures.min():.1f} - {temperatures.max():.1f} °C'
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
    """Create a velocity-based plot for pipes with statistics."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))
    
    # Check if results are available
    if not hasattr(net, 'res_pipe') or net.res_pipe.empty:
        ax.text(0.5, 0.5, 'Keine Rohrleitungsergebnisse verfügbar', 
                transform=ax.transAxes, ha='center', va='center')
        return ax
    
    try:
        # Use simple plot with velocity focus
        pp_plot.simple_plot(net, ax=ax, show_plot=False,
                           junction_size=0.01,
                           pipe_width=4,
                           heat_consumer_size=0.08,
                           pump_size=0.08,
                           junction_color='black',
                           pipe_color='purple',
                           heat_consumer_color='blue',
                           pump_color='green')
        
        ax.set_title('Geschwindigkeitsverteilung in Rohrleitungen', fontsize=14, fontweight='bold')
        
        # Add velocity statistics
        if 'v_mean_m_per_s' in net.res_pipe.columns:
            velocities = net.res_pipe['v_mean_m_per_s']
            stats_text = f'Geschwindigkeitsbereich: {velocities.min():.2f} - {velocities.max():.2f} m/s'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8),
                    verticalalignment='top')
        
    except Exception as e:
        ax.text(0.5, 0.5, f'Fehler beim Plotten: {str(e)}', 
                transform=ax.transAxes, ha='center', va='center')
    
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    return ax


def create_pressure_profile(net, ax: Optional[plt.Axes] = None):
    """Create a pressure profile plot along the network path."""
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
    """Create a comprehensive comparison dashboard with multiple plot types."""
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
    """Get network statistics as text."""
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
    Enhanced replacement for config_plot with multiple visualization modes.
    
    This can be used as a drop-in replacement for existing config_plot functions.
    
    Parameters:
    -----------
    net : pandapipes.Network
        The pandapipes network to plot
    ax : matplotlib.axes.Axes
        The axes to plot on
    plot_mode : str
        Plot mode: 'traditional', 'pressure', 'temperature', 'velocity', 'dashboard'
    **kwargs : dict
        Additional keyword arguments passed to plotting functions
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