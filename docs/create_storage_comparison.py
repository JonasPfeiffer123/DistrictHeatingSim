"""
Thermal Storage Model Comparison Script
========================================

This script generates a comprehensive comparison of the three thermal storage models
in DistrictHeatingSim: SimpleThermalStorage, StratifiedThermalStorage, and STES.

It creates visualizations and tables comparing:
- Model complexity features
- Physical accuracy features

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: October 2025
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import pandas as pd

def create_hierarchy_diagram():
    """
    Create a visual representation of the storage class hierarchy.
    """
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Title
    ax.text(5, 11.5, 'Thermal Storage System Architecture', 
            ha='center', va='top', fontsize=18, fontweight='bold')
    ax.text(5, 11, 'Storage Class Hierarchy in DistrictHeatingSim', 
            ha='center', va='top', fontsize=12, style='italic')
    
    # Base class
    base_box = FancyBboxPatch((3.5, 9), 3, 0.8, boxstyle="round,pad=0.1", 
                              edgecolor='black', facecolor='lightgray', linewidth=2)
    ax.add_patch(base_box)
    ax.text(5, 9.4, 'BaseHeatGenerator', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    # Arrow to ThermalStorage
    arrow1 = FancyArrowPatch((5, 9), (5, 8.2), arrowstyle='->', 
                            mutation_scale=30, linewidth=2, color='black')
    ax.add_artist(arrow1)
    
    # ThermalStorage (abstract base)
    thermal_box = FancyBboxPatch((3, 7.2), 4, 1, boxstyle="round,pad=0.1", 
                                edgecolor='darkblue', facecolor='lightblue', linewidth=2)
    ax.add_patch(thermal_box)
    ax.text(5, 7.9, 'ThermalStorage (Abstract Base)', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    ax.text(5, 7.5, 'Geometry, Heat Losses, Core Functions', 
            ha='center', va='center', fontsize=9, style='italic')
    
    # Arrows to three implementations
    arrow2a = FancyArrowPatch((4, 7.2), (2.5, 5.8), arrowstyle='->', 
                             mutation_scale=25, linewidth=2, color='darkgreen')
    arrow2b = FancyArrowPatch((5, 7.2), (5, 5.8), arrowstyle='->', 
                             mutation_scale=25, linewidth=2, color='darkorange')
    arrow2c = FancyArrowPatch((6, 7.2), (7.5, 5.8), arrowstyle='->', 
                             mutation_scale=25, linewidth=2, color='darkred')
    ax.add_artist(arrow2a)
    ax.add_artist(arrow2b)
    ax.add_artist(arrow2c)
    
    # SimpleThermalStorage
    simple_box = FancyBboxPatch((0.5, 4), 3.5, 1.8, boxstyle="round,pad=0.1", 
                               edgecolor='darkgreen', facecolor='lightgreen', linewidth=2.5)
    ax.add_patch(simple_box)
    ax.text(2.25, 5.6, 'SimpleThermalStorage', ha='center', va='center', 
            fontsize=11, fontweight='bold', color='darkgreen')
    ax.text(2.25, 5.25, 'Complexity 1', ha='center', va='center', 
            fontsize=9, fontweight='bold', style='italic')
    ax.text(2.25, 4.9, '• Uniform (1 Node)', ha='center', va='center', fontsize=8)
    ax.text(2.25, 4.6, '• No Stratification', ha='center', va='center', fontsize=8)
    ax.text(2.25, 4.3, '• Preliminary Studies', ha='center', va='center', fontsize=8)
    
    # StratifiedThermalStorage
    stratified_box = FancyBboxPatch((3.5, 4), 3, 1.8, boxstyle="round,pad=0.1", 
                                   edgecolor='darkorange', facecolor='lightyellow', linewidth=2.5)
    ax.add_patch(stratified_box)
    ax.text(5, 5.6, 'StratifiedThermalStorage', ha='center', va='center', 
            fontsize=11, fontweight='bold', color='darkorange')
    ax.text(5, 5.25, 'Complexity 2', ha='center', va='center', 
            fontsize=9, fontweight='bold', style='italic')
    ax.text(5, 4.9, '• Stratified (5-20)', ha='center', va='center', fontsize=8)
    ax.text(5, 4.6, '• Temperature Profiles', ha='center', va='center', fontsize=8)
    ax.text(5, 4.3, '• PTES Design', ha='center', va='center', fontsize=8)
    
    # STES Animation box (right side)
    animation_box = FancyBboxPatch((6.5, 4), 3, 1.8, boxstyle="round,pad=0.1", 
                                  edgecolor='purple', facecolor='plum', linewidth=1.5,
                                  linestyle='dashed')
    ax.add_patch(animation_box)
    ax.text(8, 5.6, 'STES_Animation', ha='center', va='center', 
            fontsize=10, fontweight='bold', color='purple')
    ax.text(8, 5.25, 'Visualization', ha='center', va='center', 
            fontsize=9, fontweight='bold', style='italic')
    ax.text(8, 4.9, '• 3D Representation', ha='center', va='center', fontsize=8)
    ax.text(8, 4.6, '• Interactive', ha='center', va='center', fontsize=8)
    ax.text(8, 4.3, '• Animation', ha='center', va='center', fontsize=8)
    
    # Arrow from StratifiedThermalStorage to STES
    arrow3 = FancyArrowPatch((5, 4), (5, 2.8), arrowstyle='->', 
                            mutation_scale=25, linewidth=2.5, color='darkred')
    ax.add_artist(arrow3)
    
    # STES
    stes_box = FancyBboxPatch((3, 1), 4, 1.8, boxstyle="round,pad=0.1", 
                             edgecolor='darkred', facecolor='lightcoral', linewidth=3)
    ax.add_patch(stes_box)
    ax.text(5, 2.6, 'STES (Seasonal Thermal Energy Storage)', ha='center', va='center', 
            fontsize=11, fontweight='bold', color='darkred')
    ax.text(5, 2.25, 'Complexity 3 - Complete', ha='center', va='center', 
            fontsize=9, fontweight='bold', style='italic')
    ax.text(5, 1.9, '• Mass Flows', ha='center', va='center', fontsize=8)
    ax.text(5, 1.6, '• System Integration', ha='center', va='center', fontsize=8)
    ax.text(5, 1.3, '• Operating Limits', ha='center', va='center', fontsize=8)
    
    # Arrow from STES to Animation (dashed)
    arrow_anim = FancyArrowPatch((7, 2), (8, 4), arrowstyle='->', 
                                mutation_scale=20, linewidth=1.5, 
                                color='purple', linestyle='dashed')
    ax.add_artist(arrow_anim)
    
    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='lightgreen', edgecolor='darkgreen', label='Complexity 1: Basic'),
        mpatches.Patch(facecolor='lightyellow', edgecolor='darkorange', label='Complexity 2: Stratified'),
        mpatches.Patch(facecolor='lightcoral', edgecolor='darkred', label='Complexity 3: Complete'),
        mpatches.Patch(facecolor='plum', edgecolor='purple', label='Visualization', linestyle='dashed')
    ]
    ax.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=9,
             bbox_to_anchor=(0.5, -0.05), frameon=True)
    
    plt.tight_layout()
    return fig


def create_physics_comparison():
    """
    Create comparison of physical modeling approaches.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    
    # SimpleThermalStorage - Uniform temperature
    ax1 = axes[0]
    ax1.set_xlim(-1, 1)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    
    # Draw storage tank
    tank = FancyBboxPatch((-0.5, 0), 1, 8, boxstyle="round,pad=0.05", 
                         edgecolor='darkgreen', facecolor='lightgreen', linewidth=2)
    ax1.add_patch(tank)
    
    # Single temperature
    ax1.text(0, 4, 'T = const.', ha='center', va='center', 
            fontsize=14, fontweight='bold', color='darkgreen')
    ax1.text(0, 9, 'SimpleThermalStorage', ha='center', va='center', 
            fontsize=12, fontweight='bold')
    ax1.text(0, -0.5, '1 Temperature Node', ha='center', va='center', 
            fontsize=10, style='italic')
    
    # StratifiedThermalStorage - Layers
    ax2 = axes[1]
    ax2.set_xlim(-1, 1)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    
    # Draw layered storage
    n_layers = 5
    layer_height = 8 / n_layers
    temps = np.linspace(25, 85, n_layers)  # Cold at bottom (25°C) to hot at top (85°C)
    colors_gradient = plt.cm.coolwarm(np.linspace(0.2, 0.8, n_layers))  # Blue (cold) to red (hot)
    
    for i in range(n_layers):
        y_pos = i * layer_height
        layer = FancyBboxPatch((-0.5, y_pos), 1, layer_height, 
                              edgecolor='darkorange', facecolor=colors_gradient[i], 
                              linewidth=1.5)
        ax2.add_patch(layer)
        ax2.text(0, y_pos + layer_height/2, f'{temps[i]:.0f}°C', 
                ha='center', va='center', fontsize=9, fontweight='bold')
    
    ax2.text(0, 9, 'StratifiedThermalStorage', ha='center', va='center', 
            fontsize=12, fontweight='bold')
    ax2.text(0, -0.5, f'{n_layers} Temperature Layers', ha='center', va='center', 
            fontsize=10, style='italic')
    
    # STES - Layers with flows
    ax3 = axes[2]
    ax3.set_xlim(-1.5, 1.5)
    ax3.set_ylim(0, 10)
    ax3.axis('off')
    
    # Draw layered storage with flows
    for i in range(n_layers):
        y_pos = i * layer_height
        layer = FancyBboxPatch((-0.5, y_pos), 1, layer_height, 
                              edgecolor='darkred', facecolor=colors_gradient[i], 
                              linewidth=1.5)
        ax3.add_patch(layer)
        ax3.text(0, y_pos + layer_height/2, f'{temps[i]:.0f}°C', 
                ha='center', va='center', fontsize=9, fontweight='bold')
    
    # Inlet/Outlet arrows
    # Inlet (top) - charging
    arrow_in = FancyArrowPatch((-1.2, 8), (-0.5, 8), arrowstyle='->', 
                              mutation_scale=20, linewidth=2.5, color='red')
    ax3.add_artist(arrow_in)
    ax3.text(-1.35, 8, 'Q_in\n(Generator)', ha='right', va='center', 
            fontsize=8, fontweight='bold', color='red')
    
    # Outlet (top) - to consumers
    arrow_out_top = FancyArrowPatch((0.5, 8), (1.2, 8), arrowstyle='->', 
                                   mutation_scale=20, linewidth=2.5, color='darkred')
    ax3.add_artist(arrow_out_top)
    ax3.text(1.35, 8, 'Q_out\n(Consumer)', ha='left', va='center', 
            fontsize=8, fontweight='bold', color='darkred')
    
    # Return (bottom) - from consumers
    arrow_return = FancyArrowPatch((1.2, 0), (0.5, 0), arrowstyle='->', 
                                  mutation_scale=20, linewidth=2.5, color='blue')
    ax3.add_artist(arrow_return)
    ax3.text(1.35, 0, 'Return\n(Consumer)', ha='left', va='center', 
            fontsize=8, fontweight='bold', color='blue')
    
    # Return to generators (bottom)
    arrow_return_gen = FancyArrowPatch((-0.5, 0), (-1.2, 0), arrowstyle='->', 
                                      mutation_scale=20, linewidth=2.5, color='lightblue')
    ax3.add_artist(arrow_return_gen)
    ax3.text(-1.35, 0, 'Return\n(Generator)', ha='right', va='center', 
            fontsize=8, fontweight='bold', color='lightblue')
    
    ax3.text(0, 9, 'STES', ha='center', va='center', 
            fontsize=12, fontweight='bold')
    ax3.text(0, -0.5, f'{n_layers} Layers + Mass Flows', ha='center', va='center', 
            fontsize=10, style='italic')
    
    plt.suptitle('Physical Modeling Approaches', fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    return fig

def main():
    """
    Main function to generate all comparison visualizations.
    """
    print("Generating Thermal Storage Model Comparison Visualizations...")
    
    # Create output directory
    import os
    output_dir = "docs/images"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate hierarchy diagram
    print("1. Creating hierarchy diagram...")
    fig1 = create_hierarchy_diagram()
    fig1.savefig(f"{output_dir}/thermal_storage_hierarchy.png", dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir}/thermal_storage_hierarchy.png")
    
    # Generate physics comparison
    print("2. Creating physics modeling comparison...")
    fig2 = create_physics_comparison()
    fig2.savefig(f"{output_dir}/thermal_storage_physics.png", dpi=300, bbox_inches='tight')
    print(f"   Saved: {output_dir}/thermal_storage_physics.png")
    
    print("\n✅ All visualizations generated successfully!")
    print(f"   Output directory: {output_dir}")
    
    # Show plots
    plt.show()

if __name__ == "__main__":
    main()
