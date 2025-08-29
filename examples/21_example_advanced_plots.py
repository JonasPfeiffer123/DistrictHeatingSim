"""
Advanced Plots Example
======================

Demonstriert die erweiterten Plot-Funktionen für DistrictHeatingSim.
Diese funktionsfähige Version umgeht pandapipes API-Limitierungen.

Features:
- Druckverteilungsplots
- Temperaturverteilungsplots  
- Geschwindigkeitsanalyse
- Druckprofile
- Dashboard-Ansichten
- Drop-in config_plot Ersatz

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-08-14
Version: 1.0 (Production Ready)
"""

import pandapipes as pp
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add the src directory to the path
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from districtheatingsim.net_simulation_pandapipes.advanced_plots import (
    create_pressure_plot, 
    create_temperature_plot,
    create_velocity_plot,
    create_pressure_profile,
    create_comparison_dashboard,
    enhanced_config_plot
)


def create_test_network():
    """Create a test network with supply and return lines (based on existing examples)."""
    print("Erstelle Test-Netzwerk mit Vor- und Rücklauf...")
    
    net = pp.create_empty_network(fluid="water", name="Test Network")
    
    # Supply temperature and other parameters
    supply_temperature_k = 85 + 273.15  # 85°C
    return_temperature_k = np.array([60, 55, 65]) + 273.15  # Different return temperatures
    
    # Create junctions for a simple vor-/rücklauf network
    # Supply line junctions
    j1 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Pump Supply", geodata=(0, 0))
    j2 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Main Split Supply", geodata=(20, 0))
    j3 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Consumer B Supply", geodata=(40, 0))
    j4 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Consumer C Supply", geodata=(60, 0))
    
    # Return line junctions  
    j5 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Consumer C Return", geodata=(60, 20))
    j6 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Consumer B Return", geodata=(40, 20))
    j7 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Main Split Return", geodata=(20, 20))
    j8 = pp.create_junction(net, pn_bar=4.0, tfluid_k=supply_temperature_k, name="Pump Return", geodata=(0, 20))
    
    # Create circulation pump
    pp.create_circ_pump_const_pressure(net, j8, j1, p_flow_bar=4.0, plift_bar=1.5, 
                                       t_flow_k=supply_temperature_k, type="auto", name="Main Pump")
    
    # Create supply line pipes
    pp.create_pipe(net, j1, j2, std_type="110/202 PLUS", length_km=0.02, k_mm=0.1, name="Supply Main 1")
    pp.create_pipe(net, j2, j3, std_type="110/202 PLUS", length_km=0.02, k_mm=0.1, name="Supply Main 2") 
    pp.create_pipe(net, j3, j4, std_type="110/202 PLUS", length_km=0.02, k_mm=0.1, name="Supply Main 3")
    
    # Create return line pipes
    pp.create_pipe(net, j5, j6, std_type="110/202 PLUS", length_km=0.02, k_mm=0.1, name="Return Main 3")
    pp.create_pipe(net, j6, j7, std_type="110/202 PLUS", length_km=0.02, k_mm=0.1, name="Return Main 2")
    pp.create_pipe(net, j7, j8, std_type="110/202 PLUS", length_km=0.02, k_mm=0.1, name="Return Main 1")
    
    # Create heat consumers (from supply to return)
    pp.create_heat_consumer(net, from_junction=j2, to_junction=j7, qext_w=30000, 
                           treturn_k=return_temperature_k[0], name="Consumer A")
    pp.create_heat_consumer(net, from_junction=j3, to_junction=j6, qext_w=25000, 
                           treturn_k=return_temperature_k[1], name="Consumer B")  
    pp.create_heat_consumer(net, from_junction=j4, to_junction=j5, qext_w=20000, 
                           treturn_k=return_temperature_k[2], name="Consumer C")
    
    print(f"Netzwerk erstellt mit {len(net.junction)} Knoten und {len(net.pipe)} Rohrleitungen")
    print(f"Heat Consumers: {len(net.heat_consumer)}")
    return net


def test_single_plots(net):
    """Test individual plot functions."""
    print("\nTeste Einzelplot-Funktionen...")
    
    # Create a 2x2 subplot grid
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Test der einzelnen Plot-Funktionen', fontsize=16, fontweight='bold')
    
    # Test pressure plot
    print("- Teste Druckplot...")
    create_pressure_plot(net, ax=axes[0,0])
    
    # Test temperature plot  
    print("- Teste Temperaturplot...")
    create_temperature_plot(net, ax=axes[0,1])
    
    # Test velocity plot
    print("- Teste Geschwindigkeitsplot...")
    create_velocity_plot(net, ax=axes[1,0])
    
    # Test pressure profile
    print("- Teste Druckprofil...")
    create_pressure_profile(net, ax=axes[1,1])
    
    plt.tight_layout()
    plt.savefig('examples/results/advanced_plots_single.png', dpi=150, bbox_inches='tight')
    print("Einzelplots gespeichert als 'examples/results/advanced_plots_single.png'")
    return fig


def test_dashboard(net):
    """Test the dashboard function."""
    print("\nTeste Dashboard-Funktion...")
    
    fig, axes = create_comparison_dashboard(net)
    
    plt.savefig('examples/results/advanced_plots_dashboard.png', dpi=150, bbox_inches='tight')
    print("Dashboard gespeichert als 'examples/results/advanced_plots_dashboard.png'")
    return fig


def test_enhanced_config_plot_replacement(net):
    """Test the enhanced config plot replacement."""
    print("\nTeste erweiterte config_plot Ersatzfunktion...")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Test der erweiterten config_plot Ersatzfunktion', fontsize=16, fontweight='bold')
    
    # Test different modes
    modes = ['traditional', 'pressure', 'temperature', 'velocity']
    
    for i, mode in enumerate(modes):
        ax = axes[i//3, i%3] if i < 6 else None
        if ax is not None:
            print(f"- Teste Modus: {mode}")
            enhanced_config_plot(net, ax, plot_mode=mode)
            ax.set_title(f'Modus: {mode}', fontweight='bold')
    
    # Remove empty subplots
    for i in range(len(modes), 6):
        axes[i//3, i%3].remove()
    
    plt.tight_layout()
    plt.savefig('examples/results/advanced_plots_config_modes.png', dpi=150, bbox_inches='tight')
    print("Erweiterte config_plot Tests gespeichert als 'examples/results/advanced_plots_config_modes.png'")
    return fig


def main():
    """Main test function."""
    print("=" * 60)
    print("Test der erweiterten Plot-Funktionen für DistrictHeatingSim")
    print("=" * 60)
    
    # Create test network
    net = create_test_network()
    
    # Run simulation
    print("\nFühre Netzwerksimulation durch...")
    try:
        pp.pipeflow(net, mode='bidirectional', iter=100, alpha=0.2)
        print("Simulation erfolgreich abgeschlossen")
        print(f"Simulierte Druckwerte: {net.res_junction['p_bar'].min():.2f} - {net.res_junction['p_bar'].max():.2f} bar")
        print(f"Temperaturbereich: {net.res_junction['t_k'].min()-273.15:.1f} - {net.res_junction['t_k'].max()-273.15:.1f} °C")
    except Exception as e:
        print(f"Simulation fehlgeschlagen: {e}")
        return
    
    # Test all plot functions
    try:
        fig1 = test_single_plots(net)
        fig2 = test_dashboard(net) 
        fig3 = test_enhanced_config_plot_replacement(net)
        
        print("\n" + "=" * 60)
        print("Alle Tests erfolgreich abgeschlossen!")
        print("Ergebnisse gespeichert in:")
        print("- examples/results/advanced_plots_single.png")
        print("- examples/results/advanced_plots_dashboard.png") 
        print("- examples/results/advanced_plots_config_modes.png")
        print("=" * 60)
        
        # Show plots
        plt.show()
        
    except Exception as e:
        print(f"\nFehler beim Plotten: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
