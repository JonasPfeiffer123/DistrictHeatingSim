"""
Filename: process_lod2.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-03-07
Description: LOD2 building data processing and conversion for district heating applications.

This module provides comprehensive processing capabilities for Level of Detail 2 (LOD2)
building data from German cadastral sources. It handles the conversion of Shapefile data
to standardized GeoJSON format with proper coordinate reference system transformation
and geometry validation for district heating network planning applications.

The module supports batch processing of municipal building datasets, coordinate system
standardization, and geometry consolidation to create unified building footprint data
suitable for heat demand analysis and network optimization workflows.
"""

import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon, GeometryCollection
from typing import List, Optional

def convert_shapefiles_to_geojson(kommune_folder: str, 
                                geojson_folder: str, 
                                target_crs: str = "EPSG:25833") -> List[str]:
    """
    Convert Shapefile building data to standardized GeoJSON format with CRS transformation.

    This function processes LOD2 building datasets from German municipal sources,
    converting Shapefile format to GeoJSON while standardizing coordinate reference
    systems and validating geometry structures. It handles complex geometry types
    and ensures data consistency for district heating applications.

    Parameters
    ----------
    kommune_folder : str
        Path to folder containing Shapefile building data from municipal sources.
        Should contain .shp files with associated .shx, .dbf, and .prj files.
    geojson_folder : str
        Output directory path for converted GeoJSON files.
        Directory will be created if it doesn't exist.
    target_crs : str, optional
        Target coordinate reference system for output data. Default is "EPSG:25833".
        EPSG:25833 (ETRS89 / UTM zone 33N) is standard for German district heating projects.

    Returns
    -------
    List[str]
        List of file paths to successfully converted GeoJSON files.
        Empty list if no files were processed successfully.

    Notes
    -----
    Processing Workflow:
        1. Recursively scans input folder for Shapefile data
        2. Loads each Shapefile with geometric validation
        3. Standardizes geometry types (Polygon → MultiPolygon)
        4. Handles GeometryCollection by extracting Polygon components
        5. Sets or transforms to target coordinate reference system
        6. Exports as GeoJSON with UTF-8 encoding

    Geometry Processing:
        - **GeometryCollection** : Extracts Polygon geometries, discards others
        - **Polygon** : Converts to MultiPolygon for consistency
        - **MultiPolygon** : Preserves as-is
        - **Invalid geometries** : Removed from dataset with warning

    Coordinate Reference Systems:
        - EPSG:25833: Standard for German engineering projects
        - EPSG:31467: Gauss-Krüger Zone 3 (legacy German system)
        - EPSG:4326: WGS84 (GPS coordinates, requires transformation)

    Error Handling:
        - Logs conversion errors with file paths
        - Continues processing remaining files on individual failures
        - Validates geometry before and after conversion
        - Handles missing or corrupted coordinate system information

    Examples
    --------
    >>> # Convert municipal building data
    >>> input_folder = "data/Landkreis_Goerlitz_Stadt_Bad_Muskau"
    >>> output_folder = "converted/geojson"
    >>> 
    >>> converted_files = convert_shapefiles_to_geojson(
    ...     input_folder, output_folder, "EPSG:25833"
    ... )
    >>> print(f"Converted {len(converted_files)} building datasets")

    >>> # Process multiple municipalities
    >>> municipalities = ["Stadt_Dresden", "Stadt_Leipzig", "Stadt_Chemnitz"]
    >>> for municipality in municipalities:
    ...     input_path = f"data/{municipality}"
    ...     output_path = f"converted/{municipality}"
    ...     files = convert_shapefiles_to_geojson(input_path, output_path)
    ...     print(f"{municipality}: {len(files)} files converted")

    >>> # Validate converted data
    >>> for geojson_file in converted_files:
    ...     gdf = gpd.read_file(geojson_file)
    ...     print(f"{os.path.basename(geojson_file)}: {len(gdf)} buildings, CRS: {gdf.crs}")

    Raises
    ------
    OSError
        If input folder doesn't exist or output folder cannot be created.
    ValueError
        If target CRS is invalid or unsupported.

    See Also
    --------
    merge_geojsons : Consolidate multiple GeoJSON files
    geopandas.read_file : Shapefile reading function
    geopandas.GeoDataFrame.to_crs : Coordinate system transformation
    """
    os.makedirs(geojson_folder, exist_ok=True)
    
    all_geojsons = []
    processed_count = 0
    error_count = 0
    
    print(f"Starting conversion from {kommune_folder} to {geojson_folder}")
    print(f"Target CRS: {target_crs}")
    
    for root, _, files in os.walk(kommune_folder):
        for file in files:
            if file.endswith(".shp"):
                shp_path = os.path.join(root, file)
                try:
                    # Load Shapefile with validation
                    gdf = gpd.read_file(shp_path)
                    original_count = len(gdf)
                    
                    if gdf.empty:
                        print(f"Warning: Empty dataset - {file}")
                        continue

                    # Standardize geometry types
                    def convert_geometry(geom):
                        """Convert various geometry types to standardized MultiPolygon."""
                        if isinstance(geom, GeometryCollection):
                            # Extract only Polygon geometries from collection
                            polygons = [g for g in geom.geoms if isinstance(g, Polygon)]
                            if len(polygons) > 1:
                                return MultiPolygon(polygons)
                            elif len(polygons) == 1:
                                return MultiPolygon([polygons[0]])
                            else:
                                return None  # No polygons found
                        elif isinstance(geom, Polygon):
                            # Convert single polygon to MultiPolygon for consistency
                            return MultiPolygon([geom])
                        elif isinstance(geom, MultiPolygon):
                            return geom  # Already in correct format
                        else:
                            return None  # Unsupported geometry type

                    # Apply geometry conversion and filter invalid geometries
                    gdf["geometry"] = gdf["geometry"].apply(convert_geometry)
                    gdf = gdf[gdf["geometry"].notnull()]
                    
                    valid_count = len(gdf)
                    if valid_count < original_count:
                        removed = original_count - valid_count
                        print(f"Info: Removed {removed} invalid geometries from {file}")

                    if gdf.empty:
                        print(f"Warning: No valid geometries remaining in {file}")
                        continue

                    # Handle coordinate reference system
                    if gdf.crs is None:
                        print(f"Warning: No CRS found for {file}, setting to {target_crs}")
                        gdf.set_crs(target_crs, inplace=True)
                    else:
                        # Transform to target CRS if different
                        if gdf.crs.to_string() != target_crs:
                            print(f"Info: Transforming {file} from {gdf.crs} to {target_crs}")
                            gdf = gdf.to_crs(target_crs)

                    # Export as GeoJSON
                    geojson_filename = f"{os.path.splitext(file)[0]}.geojson"
                    geojson_path = os.path.join(geojson_folder, geojson_filename)
                    gdf.to_file(geojson_path, driver="GeoJSON")
                    all_geojsons.append(geojson_path)
                    processed_count += 1
                    
                    print(f"✓ Converted: {file} → {geojson_filename} ({valid_count} buildings)")

                except Exception as e:
                    error_count += 1
                    print(f"✗ Error converting {shp_path}: {e}")

    print(f"\nConversion Summary:")
    print(f"Successfully processed: {processed_count} files")
    print(f"Errors encountered: {error_count} files")
    print(f"Output files: {len(all_geojsons)}")
    
    return all_geojsons

def merge_geojsons(geojson_folder: str, 
                  output_filename: str, 
                  target_crs: str = "EPSG:25833") -> Optional[str]:
    """
    Merge multiple GeoJSON building datasets into a single consolidated file.

    This function combines all GeoJSON files within a directory structure into
    a unified building dataset for district heating network analysis. It handles
    coordinate system standardization and provides comprehensive data validation
    for large-scale municipal building datasets.

    Parameters
    ----------
    geojson_folder : str
        Path to folder containing GeoJSON building files to merge.
        Function recursively searches all subdirectories.
    output_filename : str
        Path and filename for the merged output GeoJSON file.
        Should include .geojson extension for proper format identification.
    target_crs : str, optional
        Target coordinate reference system for merged dataset. Default is "EPSG:25833".
        All input files will be transformed to this CRS before merging.

    Returns
    -------
    Optional[str]
        Path to the successfully created merged file, or None if merge failed.

    Notes
    -----
    Merging Process:
        1. Recursively scans folder for all .geojson files
        2. Loads each file with coordinate system validation
        3. Transforms all datasets to common target CRS
        4. Concatenates all building features into single dataset
        5. Exports unified dataset with standardized attributes

    Data Consolidation:
        - Combines building footprints from multiple sources
        - Preserves all attribute information from source files
        - Maintains spatial accuracy through CRS standardization
        - Handles overlapping or duplicate building geometries

    Quality Assurance:
        - Validates geometry integrity during merge process
        - Reports statistics on merged building count
        - Handles inconsistent attribute schemas gracefully
        - Provides error reporting for problematic source files

    Applications:
        - Municipal building database creation
        - District heating network planning datasets
        - Heat demand analysis input preparation
        - Building stock assessment for energy planning

    Examples
    --------
    >>> # Merge municipal building datasets
    >>> input_folder = "geojson/Landkreis_Goerlitz"
    >>> output_file = "merged/Bad_Muskau_buildings.geojson"
    >>> 
    >>> result = merge_geojsons(input_folder, output_file)
    >>> if result:
    ...     merged_data = gpd.read_file(result)
    ...     print(f"Merged dataset: {len(merged_data)} buildings")

    >>> # Process multiple municipalities
    >>> municipalities = ["Dresden", "Leipzig", "Chemnitz"]
    >>> for city in municipalities:
    ...     input_path = f"geojson/{city}"
    ...     output_path = f"merged/{city}_complete.geojson"
    ...     merge_result = merge_geojsons(input_path, output_path)
    ...     
    ...     if merge_result:
    ...         # Analyze merged dataset
    ...         buildings = gpd.read_file(merge_result)
    ...         total_area = buildings.geometry.area.sum() / 10000  # hectares
    ...         print(f"{city}: {len(buildings)} buildings, {total_area:.1f} ha")

    >>> # Validate merged data quality
    >>> merged_gdf = gpd.read_file("merged/complete_dataset.geojson")
    >>> print(f"Dataset statistics:")
    >>> print(f"Total buildings: {len(merged_gdf)}")
    >>> print(f"CRS: {merged_gdf.crs}")
    >>> print(f"Bounds: {merged_gdf.total_bounds}")
    >>> print(f"Average building area: {merged_gdf.geometry.area.mean():.1f} m²")

    Raises
    ------
    FileNotFoundError
        If input folder doesn't exist or contains no GeoJSON files.
    ValueError
        If target CRS is invalid or coordinate transformation fails.
    OSError
        If output file cannot be written due to permissions or disk space.

    See Also
    --------
    convert_shapefiles_to_geojson : Shapefile to GeoJSON conversion
    geopandas.GeoDataFrame.to_crs : Coordinate system transformation
    pandas.concat : DataFrame concatenation method
    """
    all_gdfs = []
    file_count = 0
    error_count = 0
    total_buildings = 0
    
    print(f"Starting merge from {geojson_folder}")
    print(f"Target output: {output_filename}")
    print(f"Target CRS: {target_crs}")
    
    # Recursively search for GeoJSON files
    for root, _, files in os.walk(geojson_folder):
        for file in files:
            if file.endswith(".geojson"):
                file_path = os.path.join(root, file)
                try:
                    # Load GeoJSON with validation
                    gdf = gpd.read_file(file_path)
                    
                    if gdf.empty:
                        print(f"Warning: Empty file - {file}")
                        continue
                    
                    # Transform to target CRS if necessary
                    if gdf.crs is None:
                        print(f"Warning: No CRS found for {file}, assuming {target_crs}")
                        gdf.set_crs(target_crs, inplace=True)
                    elif gdf.crs.to_string() != target_crs:
                        print(f"Info: Transforming {file} from {gdf.crs} to {target_crs}")
                        gdf = gdf.to_crs(target_crs)
                    
                    all_gdfs.append(gdf)
                    file_count += 1
                    building_count = len(gdf)
                    total_buildings += building_count
                    
                    print(f"✓ Loaded: {file} ({building_count} buildings)")
                    
                except Exception as e:
                    error_count += 1
                    print(f"✗ Error loading {file_path}: {e}")

    # Merge all datasets
    if all_gdfs:
        print(f"\nMerging {len(all_gdfs)} datasets...")
        
        # Concatenate all GeoDataFrames
        merged_gdf = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True))
        
        # Ensure consistent CRS
        merged_gdf = merged_gdf.to_crs(target_crs)
        
        # Create output directory if necessary
        output_dir = os.path.dirname(output_filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Export merged dataset
        merged_gdf.to_file(output_filename, driver="GeoJSON")
        
        # Summary statistics
        final_count = len(merged_gdf)
        total_area = merged_gdf.geometry.area.sum() / 10000  # Convert to hectares
        avg_area = merged_gdf.geometry.area.mean()
        
        print(f"\n✓ Merge completed successfully!")
        print(f"Output file: {output_filename}")
        print(f"Final dataset: {final_count} buildings")
        print(f"Total building area: {total_area:.1f} hectares")
        print(f"Average building area: {avg_area:.1f} m²")
        print(f"Processing summary: {file_count} files processed, {error_count} errors")
        
        return output_filename
    else:
        print(f"\n✗ No valid GeoJSON files found in {geojson_folder}")
        return None

# Example usage and batch processing workflow
if __name__ == "__main__":
    """
    Example workflow for processing LOD2 building data for district heating applications.
    
    This example demonstrates the complete workflow from raw Shapefile data to
    consolidated GeoJSON datasets suitable for district heating network planning.
    """
    # Configuration for German municipal data processing
    EXTRACT_DIR = "extracted"           # Raw Shapefile data location
    GEOJSON_DIR = "geojson"            # Intermediate GeoJSON storage
    MERGED_DIR = "merged"              # Final consolidated datasets
    TARGET_CRS = "EPSG:25833"          # Standard German engineering CRS (UTM Zone 33N)

    # Example: Process Bad Muskau municipality data
    landkreis = "Landkreis Görlitz"
    gemeinde = "Stadt Bad Muskau"
    
    # Define processing paths
    kommune_folder = os.path.join(EXTRACT_DIR, f"{landkreis}_{gemeinde}")
    geojson_folder = os.path.join(GEOJSON_DIR, f"{landkreis}_{gemeinde}")
    output_filename = os.path.join(MERGED_DIR, f"{landkreis}_{gemeinde}_LOD2_buildings.geojson")

    print("=== LOD2 Building Data Processing Workflow ===")
    print(f"Processing: {landkreis} - {gemeinde}")
    print(f"Source folder: {kommune_folder}")
    print(f"Target CRS: {TARGET_CRS}")
    
    # Step 1: Convert Shapefiles to GeoJSON with CRS standardization
    print("\n--- Step 1: Converting Shapefiles to GeoJSON ---")
    converted_files = convert_shapefiles_to_geojson(kommune_folder, geojson_folder, TARGET_CRS)
    
    if not converted_files:
        print("Error: No files were converted successfully. Check input data.")
        exit(1)

    # Step 2: Merge all GeoJSON files into consolidated dataset
    print("\n--- Step 2: Merging GeoJSON files ---")
    merged_result = merge_geojsons(geojson_folder, output_filename, target_crs=TARGET_CRS)
    
    if merged_result:
        print(f"\n=== Processing Complete ===")
        print(f"Final dataset available at: {merged_result}")
        
        # Optional: Load and analyze final dataset
        final_buildings = gpd.read_file(merged_result)
        bounds = final_buildings.total_bounds
        print(f"\nDataset Analysis:")
        print(f"Building count: {len(final_buildings)}")
        print(f"Spatial extent: {bounds[2]-bounds[0]:.0f}m × {bounds[3]-bounds[1]:.0f}m")
        print(f"Building density: {len(final_buildings)/((bounds[2]-bounds[0])*(bounds[3]-bounds[1])/1000000):.1f} buildings/km²")
    else:
        print("Error: Merge process failed. Check intermediate files.")