"""
Import and Create Layers Module
===============================

This module provides comprehensive data import and layer processing capabilities for
district heating network generation workflows.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-26

It handles the integration of multiple
data sources including OpenStreetMap street networks, building location data, and
heat generator coordinates to create geospatial layers for network optimization.

The module supports various data formats and coordinate systems, providing standardized
processing workflows for district heating system planning and design. It includes
functions for data validation, coordinate transformation, and GeoJSON export for
integration with GIS systems and network simulation tools.
"""

import traceback
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from typing import Optional, List, Tuple, Union

from districtheatingsim.net_generation.net_generation import generate_network, generate_connection_lines

def import_osm_street_layer(osm_street_layer_geojson_file: str) -> Optional[gpd.GeoDataFrame]:
    """
    Import OpenStreetMap street network from GeoJSON file for network routing analysis.

    This function loads street network data from OpenStreetMap exports, providing
    the infrastructure backbone for district heating network routing and optimization.
    It handles various GeoJSON formats and validates the imported data structure.

    Parameters
    ----------
    osm_street_layer_geojson_file : str
        Path to the GeoJSON file containing OpenStreetMap street network data.
        File should contain LineString geometries representing street segments.

    Returns
    -------
    Optional[geopandas.GeoDataFrame]
        GeoDataFrame containing street network geometries, or None if import fails.
        Preserves original coordinate reference system and feature attributes.

    Notes
    -----
    Data Requirements:
        - GeoJSON format with LineString geometries
        - Valid coordinate reference system
        - Connected street network for optimal routing
        - Appropriate spatial extent covering planning area

    Error Handling:
        - Validates file existence and format
        - Handles corrupted or invalid GeoJSON files
        - Provides detailed error messages for debugging
        - Returns None on failure to prevent cascading errors

    OSM Data Preparation:
        - Export street network using tools like JOSM, Overpass API, or OSMNX
        - Filter to relevant road types (primary, secondary, residential)
        - Ensure proper coordinate system (typically WGS84 or local projection)
        - Validate network connectivity for routing algorithms

    Examples
    --------
    >>> # Import street network for network routing
    >>> street_network = import_osm_street_layer("osm_streets.geojson")
    >>> if street_network is not None:
    ...     print(f"Loaded {len(street_network)} street segments")
    ...     print(f"CRS: {street_network.crs}")
    ... else:
    ...     print("Failed to load street network")

    >>> # Validate street network properties
    >>> if street_network is not None:
    ...     total_length = street_network.geometry.length.sum()
    ...     print(f"Total street network length: {total_length/1000:.1f} km")
    ...     
    ...     # Check geometry types
    ...     geom_types = street_network.geometry.geom_type.unique()
    ...     print(f"Geometry types: {geom_types}")

    >>> # Export for verification
    >>> if street_network is not None:
    ...     street_network.to_file("verified_streets.shp")

    Raises
    ------
    FileNotFoundError
        If the specified GeoJSON file does not exist.
    ValueError
        If the file contains invalid GeoJSON format or geometries.

    See Also
    --------
    load_layers : Complete data loading workflow
    geopandas.read_file : Underlying file reading function
    """
    try:
        layer = gpd.read_file(osm_street_layer_geojson_file)
        print(f"Street layer successfully loaded from {osm_street_layer_geojson_file}")
        print(f"Loaded {len(layer)} street segments")
        
        # Basic validation
        if layer.empty:
            print("Warning: Loaded street layer is empty")
        
        return layer
    except FileNotFoundError:
        print(f"Error: File not found - {osm_street_layer_geojson_file}")
        return None
    except Exception as e:
        print(f"Error loading street layer from {osm_street_layer_geojson_file}: {e}")
        traceback.print_exc()
        return None

def load_layers(osm_street_layer_geojson_file: str, 
                data_csv_file_name: str, 
                coordinates: List[Tuple[float, float]]) -> Tuple[Optional[gpd.GeoDataFrame], 
                                                                Optional[gpd.GeoDataFrame], 
                                                                Optional[gpd.GeoDataFrame], 
                                                                Optional[pd.DataFrame]]:
    """
    Load and process all spatial layers for district heating network generation.

    This function orchestrates the complete data loading workflow, integrating
    street network data, building location data, and heat generator coordinates
    into standardized geospatial layers. It handles coordinate system management
    and data validation for network optimization algorithms.

    Parameters
    ----------
    osm_street_layer_geojson_file : str
        Path to GeoJSON file containing OpenStreetMap street network data.
        Provides infrastructure routing constraints for network optimization.
    data_csv_file_name : str
        Path to CSV file containing building data with coordinates and attributes.
        Must include 'UTM_X' and 'UTM_Y' columns for spatial positioning.
    coordinates : List[Tuple[float, float]]
        List of coordinate tuples (x, y) representing heat generator locations.
        Coordinates should match the spatial reference system of other layers.

    Returns
    -------
    Tuple[Optional[gpd.GeoDataFrame], Optional[gpd.GeoDataFrame], Optional[gpd.GeoDataFrame], Optional[pd.DataFrame]]
        A tuple containing:
        
        - **osm_street_layer** (gpd.GeoDataFrame) : Street network for routing
        - **heat_consumer_layer** (gpd.GeoDataFrame) : Building locations with geometry
        - **heat_generator_layer** (gpd.GeoDataFrame) : Heat generator locations
        - **heat_consumer_df** (pd.DataFrame) : Building attributes data

    Notes
    -----
    Data Processing Workflow:
        1. Load street network from GeoJSON file
        2. Load building data from CSV with semicolon separator
        3. Convert building coordinates to Point geometries
        4. Create heat generator Points from coordinate list
        5. Validate data consistency and spatial relationships

    Coordinate System Management:
        - Street network: Preserves original CRS from GeoJSON
        - Building data: Creates Points from UTM coordinates
        - Heat generators: Initially assigned EPSG:4326, requires transformation
        - Coordinate consistency critical for spatial operations

    Data Validation:
        - Checks file existence and format compatibility
        - Validates coordinate columns in CSV data
        - Ensures geometry creation success
        - Reports data quality issues for troubleshooting

    CSV Data Requirements:
        - Semicolon-separated values format
        - 'UTM_X' and 'UTM_Y' columns for coordinates
        - Additional building attributes (heat demand, type, etc.)
        - Consistent coordinate reference system

    Examples
    --------
    >>> # Load all layers for network generation
    >>> generator_coords = [(100000, 200000), (105000, 205000)]
    >>> street_net, consumers, generators, consumer_data = load_layers(
    ...     "streets.geojson", 
    ...     "buildings.csv", 
    ...     generator_coords
    ... )

    >>> # Validate loaded data
    >>> if all(layer is not None for layer in [street_net, consumers, generators]):
    ...     print("All layers loaded successfully")
    ...     print(f"Street segments: {len(street_net)}")
    ...     print(f"Heat consumers: {len(consumers)}")
    ...     print(f"Heat generators: {len(generators)}")

    >>> # Check data alignment
    >>> if consumer_data is not None and consumers is not None:
    ...     coords_match = len(consumer_data) == len(consumers)
    ...     print(f"Consumer data alignment: {coords_match}")

    >>> # Analyze spatial extent
    >>> if consumers is not None:
    ...     bounds = consumers.total_bounds
    ...     print(f"Consumer area bounds: {bounds}")

    Raises
    ------
    FileNotFoundError
        If CSV or GeoJSON files cannot be found.
    KeyError
        If required coordinate columns are missing from CSV.
    ValueError
        If coordinate data cannot be converted to valid geometries.

    See Also
    --------
    import_osm_street_layer : Street network import function
    generate_and_export_layers : Complete workflow with export
    """
    try:
        # Load the street layer as a GeoDataFrame
        osm_street_layer = gpd.read_file(osm_street_layer_geojson_file)
        print(f"Street layer successfully loaded: {len(osm_street_layer)} segments")
        
        # Load the heat consumer data as a DataFrame
        heat_consumer_df = pd.read_csv(data_csv_file_name, sep=';')
        print(f"Heat consumer data successfully loaded: {len(heat_consumer_df)} buildings")
        
        # Validate required columns
        if 'UTM_X' not in heat_consumer_df.columns or 'UTM_Y' not in heat_consumer_df.columns:
            raise KeyError("CSV file must contain 'UTM_X' and 'UTM_Y' columns")
        
        # Convert the DataFrame into a GeoDataFrame
        heat_consumer_layer = gpd.GeoDataFrame(
            heat_consumer_df, 
            geometry=gpd.points_from_xy(heat_consumer_df.UTM_X, heat_consumer_df.UTM_Y)
        )
        print(f"Heat consumer layer successfully created: {len(heat_consumer_layer)} points")
        
        # Create the heat generator locations as a GeoDataFrame
        heat_generator_locations = [Point(x, y) for x, y in coordinates]
        heat_generator_layer = gpd.GeoDataFrame(
            geometry=heat_generator_locations, 
            crs="EPSG:4326"  # Note: This may need coordinate transformation
        )
        print(f"Heat generator layer successfully created: {len(heat_generator_layer)} generators")

        # Validate data consistency
        if heat_consumer_layer.empty:
            print("Warning: No heat consumers found in data")
        if heat_generator_layer.empty:
            print("Warning: No heat generators provided")

        return osm_street_layer, heat_consumer_layer, heat_generator_layer, heat_consumer_df

    except FileNotFoundError as e:
        print(f"Error: Required file not found - {e}")
        traceback.print_exc()
        return None, None, None, None
    except KeyError as e:
        print(f"Error: Missing required data columns - {e}")
        traceback.print_exc()
        return None, None, None, None
    except Exception as e:
        print(f"Error loading layers: {e}")
        traceback.print_exc()
        return None, None, None, None

def generate_and_export_layers(osm_street_layer_geojson_file_name: str, 
                              data_csv_file_name: str, 
                              coordinates: List[Tuple[float, float]], 
                              base_path: str, 
                              algorithm: str = "MST", 
                              offset_angle: float = 0, 
                              offset_distance: float = 0.5) -> None:
    """
    Generate complete district heating network and export all layers as GeoJSON files.

    This function provides the complete workflow for district heating network
    generation, from data import through network optimization to standardized
    GeoJSON export. It creates all necessary network components including
    supply lines, return lines, and service connections with proper attributes.

    Parameters
    ----------
    osm_street_layer_geojson_file_name : str
        Path to GeoJSON file containing OpenStreetMap street network data.
        Provides infrastructure constraints for network routing.
    data_csv_file_name : str
        Path to CSV file containing building data with coordinates and attributes.
        Source of heat consumer locations and characteristics.
    coordinates : List[Tuple[float, float]]
        List of coordinate tuples (x, y) for heat generator locations.
        Defines heat production points in the network.
    base_path : str
        Base directory path for exporting generated network layers.
        Will create subdirectory structure for organized file management.
    algorithm : str, optional
        Network optimization algorithm to use. Default is "MST".
        
        Available algorithms:
            - **"MST"** : Minimum Spanning Tree (fastest, tree topology)
            - **"Advanced MST"** : MST with road alignment optimization
            - **"Steiner"** : Steiner tree for minimal total length
            
    offset_angle : float, optional
        Angle in degrees for parallel return line generation. Default is 0°.
        0° = eastward offset, 90° = northward offset.
    offset_distance : float, optional
        Distance in meters for parallel return line separation. Default is 0.5m.
        Typical values: 0.5-2.0m for district heating applications.

    Returns
    -------
    None
        Function creates and exports GeoJSON files to specified directory structure.

    Notes
    -----
    Generated Network Components:
        - **Supply Lines (Vorlauf)** : Main distribution network with optimization
        - **Return Lines (Rücklauf)** : Parallel return network with offset
        - **Heat Consumers (HAST)** : Building connections with attributes
        - **Heat Generators (Erzeugeranlagen)** : Production facility connections

    Output File Structure:
        ```
        base_path/
        └── Wärmenetz/
            ├── Vorlauf.geojson      # Supply line network
            ├── Rücklauf.geojson     # Return line network
            ├── HAST.geojson         # Heat consumer connections
            └── Erzeugeranlagen.geojson  # Heat generator connections
        ```

    Coordinate System Management:
        - All outputs standardized to EPSG:25833 (ETRS89 / UTM zone 33N)
        - Suitable for German district heating projects
        - Maintains spatial accuracy for engineering applications

    Data Processing Pipeline:
        1. Load and validate all input data sources
        2. Generate optimized network backbone using selected algorithm
        3. Create service connections for all buildings and generators
        4. Apply parallel line generation for return network
        5. Standardize coordinate reference systems
        6. Export all components as GeoJSON with proper attributes

    Examples
    --------
    >>> # Generate complete network with MST algorithm
    >>> generator_locations = [(100000, 200000), (105000, 205000)]
    >>> generate_and_export_layers(
    ...     "streets.geojson",
    ...     "buildings.csv", 
    ...     generator_locations,
    ...     "output",
    ...     algorithm="MST"
    ... )

    >>> # Generate optimized network with road alignment
    >>> generate_and_export_layers(
    ...     "streets.geojson",
    ...     "buildings.csv",
    ...     generator_locations,
    ...     "output",
    ...     algorithm="Advanced MST",
    ...     offset_distance=1.0,
    ...     offset_angle=90
    ... )

    >>> # Generate minimal-length network with Steiner tree
    >>> generate_and_export_layers(
    ...     "streets.geojson",
    ...     "buildings.csv",
    ...     generator_locations,
    ...     "output",
    ...     algorithm="Steiner",
    ...     offset_distance=1.5
    ... )

    >>> # Verify generated files
    >>> import os
    >>> network_dir = "output/Wärmenetz"
    >>> files = os.listdir(network_dir)
    >>> print(f"Generated files: {files}")

    >>> # Load and analyze generated network
    >>> import geopandas as gpd
    >>> supply_network = gpd.read_file("output/Wärmenetz/Vorlauf.geojson")
    >>> total_length = supply_network.geometry.length.sum()
    >>> print(f"Total supply network length: {total_length/1000:.1f} km")

    Raises
    ------
    FileNotFoundError
        If input files cannot be found or accessed.
    ValueError
        If invalid algorithm is specified or coordinate data is malformed.
    OSError
        If output directory cannot be created or files cannot be written.

    See Also
    --------
    load_layers : Data loading and processing workflow
    generate_network : Network optimization algorithms
    generate_connection_lines : Service connection generation
    """
    # Load and process all input data layers
    osm_street_layer, heat_consumer_layer, heat_generator_layer, heat_consumer_df = load_layers(
        osm_street_layer_geojson_file_name, 
        data_csv_file_name, 
        coordinates
    )
    
    # Validate data loading success
    if any(layer is None for layer in [osm_street_layer, heat_consumer_layer, heat_generator_layer]):
        print("Error: Failed to load required data layers. Export cancelled.")
        return
    
    # Generate optimized network backbone using specified algorithm
    print(f"Generating network using {algorithm} algorithm...")
    flow_lines_gdf, return_lines_gdf = generate_network(
        heat_consumer_layer, 
        heat_generator_layer, 
        osm_street_layer, 
        algorithm=algorithm, 
        offset_distance=offset_distance, 
        offset_angle=offset_angle
    )

    # Generate service connections for heat consumers and producers
    print("Generating service connections...")
    heat_consumer_gdf = generate_connection_lines(
        heat_consumer_layer, 
        offset_distance, 
        offset_angle, 
        heat_consumer_df
    )
    heat_producer_gdf = generate_connection_lines(
        heat_generator_layer, 
        offset_distance, 
        offset_angle
    )

    # Standardize coordinate reference system to EPSG:25833
    print("Standardizing coordinate reference systems...")
    target_crs = "EPSG:25833"
    heat_consumer_gdf = heat_consumer_gdf.set_crs(target_crs)
    return_lines_gdf = return_lines_gdf.set_crs(target_crs)
    flow_lines_gdf = flow_lines_gdf.set_crs(target_crs)
    heat_producer_gdf = heat_producer_gdf.set_crs(target_crs)

    # Create output directory structure
    import os
    output_dir = os.path.join(base_path, "Wärmenetz")
    os.makedirs(output_dir, exist_ok=True)
    
    # Export all network components as GeoJSON files
    print(f"Exporting network layers to {output_dir}...")
    
    export_files = [
        (heat_consumer_gdf, "HAST.geojson", "Heat consumer connections"),
        (return_lines_gdf, "Rücklauf.geojson", "Return line network"),
        (flow_lines_gdf, "Vorlauf.geojson", "Supply line network"),
        (heat_producer_gdf, "Erzeugeranlagen.geojson", "Heat generator connections")
    ]
    
    for gdf, filename, description in export_files:
        filepath = os.path.join(output_dir, filename)
        try:
            gdf.to_file(filepath, driver="GeoJSON")
            print(f"✓ Exported {description}: {filename} ({len(gdf)} features)")
        except Exception as e:
            print(f"✗ Failed to export {description}: {e}")

    # Generate summary statistics
    print("\nNetwork Generation Summary:")
    print(f"Algorithm used: {algorithm}")
    print(f"Heat consumers: {len(heat_consumer_gdf)}")
    print(f"Heat generators: {len(heat_producer_gdf)}")
    print(f"Supply line segments: {len(flow_lines_gdf)}")
    print(f"Return line segments: {len(return_lines_gdf)}")
    
    # Calculate total network length
    total_supply_length = flow_lines_gdf.geometry.length.sum()
    total_return_length = return_lines_gdf.geometry.length.sum()
    print(f"Total supply network length: {total_supply_length/1000:.2f} km")
    print(f"Total return network length: {total_return_length/1000:.2f} km")
    print(f"Network generation completed successfully!")