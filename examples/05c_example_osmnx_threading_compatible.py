"""
Filename: 05c_example_osmnx_threading_compatible.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-11-22
Description: 
    Example demonstrating the threading-compatible OSMnx network generation function.
    
    This example shows how to use generate_and_export_osmnx_layers() which has
    the same interface as generate_and_export_layers() and can be used as a
    drop-in replacement in the GUI threading system.

Usage:
    Run this script to test the threading-compatible interface.
    
Example:
    $ python 05c_example_osmnx_threading_compatible.py
    
See Also:
    districtheatingsim.net_generation.osmnx_steiner_network.generate_and_export_osmnx_layers
    districtheatingsim.gui.LeafletTab.net_generation_threads.NetGenerationThread
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging

from src.districtheatingsim.net_generation.osmnx_steiner_network import generate_and_export_osmnx_layers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def main():
    """
    Test the threading-compatible OSMnx network generation function.
    
    This demonstrates the same interface as generate_and_export_layers()
    from import_and_create_layers module.
    """
    print("="*70)
    print("THREADING-COMPATIBLE OSMNX NETWORK GENERATION TEST")
    print("="*70)
    
    # -------------------------------------------------------------------------
    # Configuration (matches generate_and_export_layers interface)
    # -------------------------------------------------------------------------
    osm_street_layer_geojson_file_name = ""  # Not used in OSMnx mode
    data_csv_file_name = "examples/data/Quartier IST.csv"
    
    # Generator coordinates as list
    coordinates = [(480219, 5711597)]  # Single generator
    # coordinates = [(480219, 5711597), (480500, 5712000)]  # Multiple generators
    
    base_path = "examples/data"
    algorithm = "OSMnx"  # For interface compatibility
    offset_angle = 0  # Degrees
    offset_distance = 1.0  # Meters
    
    # OSMnx-specific parameters (optional)
    buffer_meters = 500.0
    network_type = 'drive_service'
    custom_filter = None  # Or use custom filter string
    node_threshold = 0.1
    remove_dead_ends_flag = True
    
    print(f"\nConfiguration:")
    print(f"  - Building data: {data_csv_file_name}")
    print(f"  - Generator(s): {len(coordinates)}")
    print(f"  - Output: {base_path}/Wärmenetz/")
    print(f"  - Algorithm: {algorithm}")
    print(f"  - Offset: {offset_distance}m at {offset_angle}°")
    print(f"  - Buffer: {buffer_meters}m")
    print(f"  - Network type: {network_type}")
    
    # -------------------------------------------------------------------------
    # Generate and export network
    # -------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("Calling generate_and_export_osmnx_layers...")
    print(f"{'='*70}\n")
    
    try:
        generate_and_export_osmnx_layers(
            osm_street_layer_geojson_file_name=osm_street_layer_geojson_file_name,
            data_csv_file_name=data_csv_file_name,
            coordinates=coordinates,
            base_path=base_path,
            algorithm=algorithm,
            offset_angle=offset_angle,
            offset_distance=offset_distance,
            buffer_meters=buffer_meters,
            network_type=network_type,
            custom_filter=custom_filter,
            node_threshold=node_threshold,
            remove_dead_ends_flag=remove_dead_ends_flag,
            target_crs='EPSG:25833'
        )
        
        print(f"\n{'='*70}")
        print("✓ SUCCESS: Network generated and exported")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"✗ ERROR: Network generation failed")
        print(f"{'='*70}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
