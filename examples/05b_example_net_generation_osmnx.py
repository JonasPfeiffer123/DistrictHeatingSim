"""
Filename: 05b_example_net_generation_osmnx.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-11-22
Description: 
    Example script demonstrating OSMnx-based district heating network generation.
    
    This example shows two approaches for generating district heating networks:
    1. Direct API: Using generate_osmnx_network() for programmatic access
    2. Threading-compatible: Using generate_and_export_osmnx_layers() for GUI integration
    
    Features demonstrated:
    - Street-based routing with OSMnx
    - Steiner Tree optimization
    - Edge-splitting connections with exact coordinate matching
    - Dead-end removal with connection protection
    - Dual network (supply/return) with offset
    - HAST connections with building metadata
    - Generator connections (single or multiple)
    - Visualization

Usage:
    Run this script to generate a complete district heating network from building data.
    Toggle USE_THREADING_API to switch between direct and threading-compatible API.
    
Example:
    $ python 05b_example_net_generation_osmnx.py
    
See Also:
    districtheatingsim.net_generation.osmnx_steiner_network : Main implementation module
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox
import logging
from shapely.geometry import Point

from src.districtheatingsim.net_generation.osmnx_steiner_network import (
    generate_osmnx_network,
    generate_and_export_osmnx_layers
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

# Configure OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False


def main():
    """
    Main execution function demonstrating OSMnx-based network generation.
    
    This example demonstrates two approaches:
    1. Direct API (USE_THREADING_API=False): Full programmatic control with result dict
    2. Threading-compatible API (USE_THREADING_API=True): GUI-compatible export function
    """
    print("="*70)
    print("OSMNX-BASED DISTRICT HEATING NETWORK GENERATION EXAMPLE")
    print("="*70)
    
    # -------------------------------------------------------------------------
    # API Selection
    # -------------------------------------------------------------------------
    USE_THREADING_API = False  # Toggle between direct API and threading-compatible API
    
    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------
    data_csv_file = "examples/data/Quartier IST.csv"
    
    # Generator coordinates as list (can be single or multiple)
    generator_coords = [(480219, 5711597)]  # Single generator (UTM Zone 33N)
    # generator_coords = [(480219, 5711597), (480600, 5710500)]  # Multiple generators
    
    output_dir = "examples/data/osmnx_steiner_output"
    
    # Network generation parameters
    return_offset = 1.0  # meters
    buffer_meters = 500.0
    network_type = 'drive_service'  # Default OSMnx network type
    node_threshold = 0.1
    remove_dead_ends = True
    include_building_data = True
    
    # Custom filter for specific highway types (like OSM download tags)
    # Uncomment to use custom filter instead of network_type:
    # custom_filter = '["highway"~"primary|secondary|tertiary|residential|living_street|service"]'
    custom_filter = None  # Use network_type instead
    
    # -------------------------------------------------------------------------
    # Display configuration
    # -------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("Configuration")
    print(f"{'='*70}")
    print(f"API Mode: {'Threading-compatible' if USE_THREADING_API else 'Direct'}")
    print(f"Building data: {data_csv_file}")
    print(f"Generator(s): {len(generator_coords)}")
    print(f"Output directory: {output_dir}")
    print(f"Return offset: {return_offset}m")
    print(f"Buffer: {buffer_meters}m")
    print(f"Network type: {network_type if not custom_filter else 'Custom filter'}")
    print(f"Remove dead ends: {remove_dead_ends}")
    
    # -------------------------------------------------------------------------
    # Load building data (only for direct API)
    # -------------------------------------------------------------------------
    if not USE_THREADING_API:
        print(f"\n{'='*70}")
        print("Loading building data from CSV")
        print(f"{'='*70}")
        
        df = pd.read_csv(data_csv_file, delimiter=';')
        buildings = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.UTM_X, df.UTM_Y),
            crs='EPSG:25833'
        )
        
        print(f"✓ Loaded {len(buildings)} buildings")
    
    # -------------------------------------------------------------------------
    # Generate network using selected API
    # -------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print(f"Generating network using {'threading-compatible' if USE_THREADING_API else 'direct'} API")
    print(f"{'='*70}")
    
    if USE_THREADING_API:
        # Threading-compatible API (same interface as generate_and_export_layers)
        generate_and_export_osmnx_layers(
            osm_street_layer_geojson_file_name="",  # Not used
            data_csv_file_name=data_csv_file,
            coordinates=generator_coords,
            base_path=os.path.dirname(output_dir),
            algorithm="OSMnx",
            offset_angle=0,
            offset_distance=return_offset,
            buffer_meters=buffer_meters,
            network_type=network_type,
            custom_filter=custom_filter,
            node_threshold=node_threshold,
            remove_dead_ends_flag=remove_dead_ends,
            target_crs='EPSG:25833'
        )
        
        # Load exported files for visualization
        print(f"\n{'='*70}")
        print("Loading exported networks for visualization")
        print(f"{'='*70}")
        
        from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema
        
        network_dir = os.path.join(os.path.dirname(output_dir), "Wärmenetz")
        unified_geojson = NetworkGeoJSONSchema.load_from_file(os.path.join(network_dir, "Wärmenetz.geojson"))
        supply_network, return_network, hast_connections, generator_connection = NetworkGeoJSONSchema.split_to_legacy_format(unified_geojson)
        
        # Load buildings for plotting
        df = pd.read_csv(data_csv_file, delimiter=';')
        buildings = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.UTM_X, df.UTM_Y),
            crs='EPSG:25833'
        )
        
        # Create summary dict for consistent output
        result = {
            'n_buildings': len(buildings),
            'n_generators': len(generator_coords),
            'n_supply_segments': len(supply_network),
            'n_return_segments': len(return_network),
            'n_hast': len(hast_connections),
            'total_length_km': (supply_network.geometry.length.sum() + return_network.geometry.length.sum()) / 1000.0,
            'output_files': {
                'vorlauf': os.path.join(network_dir, "Vorlauf.geojson"),
                'ruecklauf': os.path.join(network_dir, "Rücklauf.geojson"),
                'hast': os.path.join(network_dir, "HAST.geojson"),
                'erzeuger': os.path.join(network_dir, "Erzeugeranlagen.geojson")
            }
        }
    else:
        # Direct API (full programmatic control)
        result = generate_osmnx_network(
            buildings=buildings,
            generator_coords=generator_coords,
            output_dir=output_dir,
            return_offset=return_offset,
            buffer_meters=buffer_meters,
            network_type=network_type,
            custom_filter=custom_filter,
            node_threshold=node_threshold,
            remove_dead_ends_flag=remove_dead_ends,
            max_dead_end_iterations=10,
            include_building_data=include_building_data,
            export_geojson=True,
            target_crs='EPSG:25833'
        )
        
        # Extract results
        supply_network = result['supply_network']
        return_network = result['return_network']
        hast_connections = result['hast_connections']
        generator_connection = result['generator_connection']
    
    # -------------------------------------------------------------------------
    # Print summary
    # -------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("GENERATION SUMMARY")
    print(f"{'='*70}")
    print(f"Buildings: {result['n_buildings']}")
    print(f"Generators: {result['n_generators']}")
    print(f"Supply segments: {result['n_supply_segments']}")
    print(f"Return segments: {result['n_return_segments']}")
    print(f"HAST connections: {result['n_hast']}")
    print(f"Total pipe length: {result['total_length_km']:.2f} km")
    if 'execution_time_s' in result:
        print(f"Execution time: {result['execution_time_s']:.2f}s")
    
    if result.get('output_files'):
        print(f"\nExported files:")
        for key, path in result['output_files'].items():
            print(f"  - {key}: {path}")
    
    # -------------------------------------------------------------------------
    # Visualize (optional)
    # -------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("Creating visualization")
    print(f"{'='*70}")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(15, 15))
    
    # Plot supply and return networks
    supply_network.plot(ax=ax, color='red', linewidth=2, label='Vorlauf (Supply)', zorder=3)
    return_network.plot(ax=ax, color='blue', linewidth=2, label='Rücklauf (Return)', zorder=3)
    hast_connections.plot(ax=ax, color='green', linewidth=1.5, linestyle=':', 
                          label='HAST (Consumer Connections)', zorder=4)
    generator_connection.plot(ax=ax, color='purple', linewidth=2, linestyle=':', 
                              label='Generator Connection', zorder=4)
    
    # Plot buildings and generator
    buildings.plot(ax=ax, color='cyan', markersize=100, label='Buildings', zorder=5)
    
    # Plot generator locations
    generator_points = [Point(coords[0], coords[1]) for coords in generator_coords]
    generator_gdf = gpd.GeoDataFrame(
        geometry=generator_points,
        crs='EPSG:25833'
    )
    generator_gdf.plot(ax=ax, color='black', markersize=200, marker='s', 
                       label=f'Generator(s) (n={len(generator_coords)})', zorder=5)
    
    # Formatting
    api_mode = "Threading-compatible API" if USE_THREADING_API else "Direct API"
    ax.set_title(f'OSMnx-based District Heating Network\n({api_mode})', 
                 fontsize=16, fontweight='bold')
    ax.set_xlabel('UTM East (m)')
    ax.set_ylabel('UTM North (m)')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    plot_dir = output_dir if not USE_THREADING_API else os.path.join(os.path.dirname(output_dir), "Wärmenetz")
    plot_file = os.path.join(plot_dir, 'network_visualization.png')
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    print(f"✓ Plot saved: {plot_file}")
    
    # Show plot
    plt.show()
    
    print(f"\n{'='*70}")
    print("✓ Example completed successfully!")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()
