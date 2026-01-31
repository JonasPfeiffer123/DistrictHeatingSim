"""
Data import and layer processing for district heating network generation.

Handles integration of OpenStreetMap street networks, building locations, and
heat generator coordinates into geospatial layers for network optimization.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import warnings
# Suppress pyogrio warnings about GeoJSON driver not supporting DRIVER option
warnings.filterwarnings('ignore', message='.*driver GeoJSON does not support open option.*', category=RuntimeWarning)

import traceback
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from typing import Optional, List, Tuple, Union

from districtheatingsim.net_generation.net_generation import generate_network, generate_connection_lines
from districtheatingsim.net_generation.network_geojson_schema import NetworkGeoJSONSchema

def import_osm_street_layer(osm_street_layer_geojson_file: str) -> Optional[gpd.GeoDataFrame]:
    """
    Import OpenStreetMap street network from GeoJSON.

    :param osm_street_layer_geojson_file: Path to GeoJSON with street network LineStrings
    :type osm_street_layer_geojson_file: str
    :return: Street network GeoDataFrame or None on failure
    :rtype: Optional[gpd.GeoDataFrame]
    :raises FileNotFoundError: If GeoJSON file missing
    :raises ValueError: If invalid GeoJSON format
    
    .. note::
        Returns None on error to prevent cascading failures. Prints diagnostic messages.
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
    Load all spatial layers for network generation.

    :param osm_street_layer_geojson_file: Path to street network GeoJSON
    :type osm_street_layer_geojson_file: str
    :param data_csv_file_name: Path to CSV with building data (requires UTM_X, UTM_Y columns)
    :type data_csv_file_name: str
    :param coordinates: Heat generator coordinate tuples (x, y)
    :type coordinates: List[Tuple[float, float]]
    :return: Tuple of (street_layer, consumer_layer, generator_layer, consumer_df)
    :rtype: Tuple[Optional[gpd.GeoDataFrame], Optional[gpd.GeoDataFrame], Optional[gpd.GeoDataFrame], Optional[pd.DataFrame]]
    :raises FileNotFoundError: If files not found
    :raises KeyError: If UTM_X or UTM_Y missing from CSV
    :raises ValueError: If coordinate conversion fails
    
    .. note::
        CSV uses semicolon separator. Returns (None, None, None, None) on error.
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
    Generate district heating network and export as GeoJSON.

    :param osm_street_layer_geojson_file_name: Path to street network GeoJSON
    :type osm_street_layer_geojson_file_name: str
    :param data_csv_file_name: Path to building CSV (UTM_X, UTM_Y columns)
    :type data_csv_file_name: str
    :param coordinates: Heat generator coordinate tuples (x, y)
    :type coordinates: List[Tuple[float, float]]
    :param base_path: Output directory for generated network
    :type base_path: str
    :param algorithm: Network algorithm - MST, Advanced MST, or Steiner (default MST)
    :type algorithm: str
    :param offset_angle: Return line offset angle in degrees (default 0)
    :type offset_angle: float
    :param offset_distance: Return line offset distance in meters (default 0.5)
    :type offset_distance: float
    :raises FileNotFoundError: If input files not found
    :raises ValueError: If invalid algorithm or malformed data
    :raises OSError: If output directory cannot be created
    
    .. note::
        Exports unified GeoJSON to base_path/Wärmenetz/Wärmenetz.geojson in EPSG:25833.
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
    
    # Export in unified format
    try:
        unified_geojson = NetworkGeoJSONSchema.create_network_geojson(
            flow_lines=flow_lines_gdf,
            return_lines=return_lines_gdf,
            building_connections=heat_consumer_gdf,
            generator_connections=heat_producer_gdf,
            state="designed"
        )
        # Use default filename for unified network
        unified_filename = "Wärmenetz.geojson"
        unified_path = os.path.join(output_dir, unified_filename)
        NetworkGeoJSONSchema.export_to_file(unified_geojson, unified_path)
        print(f"✓ Exported unified network: {unified_filename} ({len(flow_lines_gdf) + len(return_lines_gdf) + len(heat_consumer_gdf) + len(heat_producer_gdf)} features)")
    except Exception as e:
        print(f"✗ Failed to export unified format: {e}")
        return

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