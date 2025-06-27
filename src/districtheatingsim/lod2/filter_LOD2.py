"""
Filter LOD2 Building Data Module
================================

This module provides comprehensive filtering and processing capabilities for Level of Detail 2 (LOD2)
building data from German cadastral sources.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-31

It handles spatial filtering operations, address-based
matching with OpenStreetMap data, coordinate-based filtering, and complex 3D geometry calculations
including surface area computation, volume estimation, and roof orientation analysis.

The module supports various filtering strategies for LOD2 datasets, integrating geocoding services
for address resolution and providing specialized functions for photovoltaic potential assessment
through detailed roof geometry analysis with slope and orientation calculations.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from geopy.geocoders import Nominatim
from typing import Dict, List, Tuple, Optional, Union, Any

def filter_LOD2_with_OSM_and_adress(csv_file_path: str, 
                                   osm_geojson_path: str, 
                                   lod_shapefile_path: str, 
                                   output_geojson_path: str) -> None:
    """
    Filter LOD2 building data based on address matching with OpenStreetMap data.

    This function performs address-based spatial filtering by matching building addresses
    from a CSV file with OpenStreetMap building data, then spatially intersecting with
    LOD2 geometries to extract relevant building models for detailed analysis.

    Parameters
    ----------
    csv_file_path : str
        Path to CSV file containing building addresses with 'Stadt' and 'Adresse' columns.
        File should use semicolon separator and contain complete address information.
    osm_geojson_path : str
        Path to OpenStreetMap GeoJSON file with building footprints and address attributes.
        Must contain 'addr:city', 'addr:street', and 'addr:housenumber' fields.
    lod_shapefile_path : str
        Path to LOD2 building data in Shapefile format with 3D geometry information.
        Contains detailed building models with walls, roofs, and ground surfaces.
    output_geojson_path : str
        Output path for filtered LOD2 data in GeoJSON format.
        Contains only buildings matching the specified addresses.

    Notes
    -----
    Filtering Workflow:
        1. Load address list from CSV file with city and street information
        2. Create complete address strings for matching
        3. Filter OSM buildings matching the address list
        4. Spatially intersect LOD2 data with filtered OSM buildings
        5. Export matching LOD2 geometries with address information

    Address Matching Strategy:
        - Combines city, street, and house number for precise matching
        - Handles missing house numbers gracefully
        - Uses spatial intersection for geometric validation
        - Preserves all LOD2 attributes and 3D geometry information

    Data Requirements:
        - **CSV Format**: Semicolon-separated with Stadt/Adresse columns
        - **OSM Data**: Building polygons with standardized address attributes
        - **LOD2 Data**: 3D building models with parent-child relationships
        - **Coordinate Alignment**: All datasets must use compatible CRS

    Applications:
        - Address-based building selection for energy audits
        - Targeted LOD2 analysis for specific building lists
        - Integration of planning data with 3D building models
        - Quality control for address geocoding accuracy

    Examples
    --------
    >>> # Filter buildings for energy audit project
    >>> filter_LOD2_with_OSM_and_adress(
    ...     "building_addresses.csv",
    ...     "osm_buildings.geojson",
    ...     "lod2_city_buildings.shp",
    ...     "filtered_audit_buildings.geojson"
    ... )

    >>> # Process multiple address lists
    >>> address_files = ["residential.csv", "commercial.csv", "public.csv"]
    >>> for addr_file in address_files:
    ...     output_name = f"lod2_{addr_file.replace('.csv', '')}.geojson"
    ...     filter_LOD2_with_OSM_and_adress(
    ...         addr_file, "osm_buildings.geojson", 
    ...         "lod2_complete.shp", output_name
    ...     )

    Raises
    ------
    FileNotFoundError
        If any input file cannot be found or accessed.
    KeyError
        If required address columns are missing from CSV or OSM data.
    ValueError
        If coordinate reference systems are incompatible.

    See Also
    --------
    filter_LOD2_with_coordinates : Coordinate-based filtering
    spatial_filter_with_polygon : Polygon-based spatial filtering
    """
    # Load OpenStreetMap building data
    osm_gdf = gpd.read_file(osm_geojson_path)
    
    # Load address list from CSV
    df = pd.read_csv(csv_file_path, delimiter=';')
    df['VollständigeAdresse'] = df['Stadt'] + ', ' + df['Adresse']
    address_list = df['VollständigeAdresse'].unique().tolist()

    # Filter OSM buildings matching address list
    def matches_address(row):
        """Check if OSM building matches any address in the list."""
        osm_address = f"{row['addr:city']}, {row['addr:street']} {row.get('addr:housenumber', '')}".strip()
        return osm_address in address_list

    osm_gdf_filtered = osm_gdf[osm_gdf.apply(matches_address, axis=1)]
    
    # Load LOD2 data and perform spatial intersection
    lod_gdf = gpd.read_file(lod_shapefile_path)
    joined_gdf = gpd.sjoin(lod_gdf, osm_gdf_filtered, how='inner', predicate='intersects')

    # Extract matching LOD2 buildings
    matching_ids = joined_gdf.index.tolist()
    filtered_lod_gdf = lod_gdf[lod_gdf.index.isin(matching_ids)]

    # Export filtered results
    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')
    print(f"Address-filtered LOD2 data saved: {len(filtered_lod_gdf)} buildings")

def filter_LOD2_with_coordinates(lod_geojson_path: str, 
                                csv_file_path: str, 
                                output_geojson_path: str) -> None:
    """
    Filter LOD2 building data based on coordinate points from CSV file.

    This function performs point-in-polygon spatial filtering to extract LOD2 building
    models containing specified coordinate points. It's particularly useful for
    extracting building models for heat pump locations, measurement points, or
    other coordinate-based building selection criteria.

    Parameters
    ----------
    lod_geojson_path : str
        Path to LOD2 GeoJSON file containing 3D building geometry data.
        Must include buildings with Ground, Wall, and Roof components.
    csv_file_path : str
        Path to CSV file with coordinate points using 'UTM_X' and 'UTM_Y' columns.
        Coordinates should match the LOD2 data coordinate reference system.
    output_geojson_path : str
        Output path for filtered LOD2 data merged with coordinate point attributes.
        Contains building models with associated point data.

    Notes
    -----
    Filtering Process:
        1. Load coordinate points from CSV and create point geometries
        2. Extract ground surface polygons from LOD2 data
        3. Perform point-in-polygon tests for spatial containment
        4. Collect all building components (walls, roofs) for matching buildings
        5. Merge coordinate attributes with filtered LOD2 geometries

    Spatial Relationship:
        - Uses ground floor polygons for point containment testing
        - Includes all building components (walls, roofs, ground) in results
        - Handles parent-child relationships in LOD2 data structure
        - Preserves coordinate attributes for downstream analysis

    Data Structure Requirements:
        - **LOD2 Data**: Buildings with ID and Obj_Parent relationships
        - **CSV Data**: UTM_X, UTM_Y columns with additional attributes
        - **Geometry Types**: Ground polygons for spatial testing
        - **CRS Compatibility**: Coordinate systems must align

    Applications:
        - Building selection for energy monitoring installations
        - LOD2 extraction for heat pump site analysis
        - Building model retrieval for specific measurement locations
        - Integration of field survey data with 3D building models

    Examples
    --------
    >>> # Filter buildings containing measurement points
    >>> filter_LOD2_with_coordinates(
    ...     "city_lod2_buildings.geojson",
    ...     "measurement_locations.csv",
    ...     "buildings_with_measurements.geojson"
    ... )

    >>> # Process heat pump installation sites
    >>> filter_LOD2_with_coordinates(
    ...     "residential_lod2.geojson",
    ...     "heat_pump_sites.csv",
    ...     "hp_candidate_buildings.geojson"
    ... )

    >>> # Validate results
    >>> import geopandas as gpd
    >>> filtered_buildings = gpd.read_file("buildings_with_measurements.geojson")
    >>> print(f"Buildings found: {len(filtered_buildings['parent_id'].unique())}")
    >>> print(f"Components: {filtered_buildings['Geometr_3D'].value_counts()}")

    Raises
    ------
    FileNotFoundError
        If LOD2 or CSV files cannot be found.
    KeyError
        If required coordinate columns (UTM_X, UTM_Y) are missing.
    ValueError
        If coordinate data cannot be converted to valid geometries.

    See Also
    --------
    spatial_filter_with_polygon : Area-based spatial filtering
    process_lod2 : Complete LOD2 geometry processing
    """
    # Load coordinate points from CSV
    df = pd.read_csv(csv_file_path, delimiter=';')
    lod_gdf = gpd.read_file(lod_geojson_path)

    # Create point geometries from coordinates
    geometry = [Point(xy) for xy in zip(df.UTM_X, df.UTM_Y)]
    csv_gdf = gpd.GeoDataFrame(df, geometry=geometry)
    csv_gdf.set_crs(lod_gdf.crs, inplace=True)

    # Extract ground surface polygons for spatial testing
    parent_ids = set()
    ground_geometries = lod_gdf[lod_gdf['Geometr_3D'] == 'Ground']
    csv_gdf['parent_id'] = None

    # Perform point-in-polygon spatial analysis
    for idx, csv_row in csv_gdf.iterrows():
        point = csv_row.geometry
        for ground_idx, ground_row in ground_geometries.iterrows():
            if point.within(ground_row['geometry']):
                parent_id = ground_row['ID']
                parent_ids.add(parent_id)
                csv_gdf.at[idx, 'parent_id'] = parent_id
                break

    # Filter LOD2 data for buildings containing points
    filtered_lod_gdf = lod_gdf[
        lod_gdf['ID'].isin(parent_ids) | lod_gdf['Obj_Parent'].isin(parent_ids)
    ]
    
    # Add coordinate information to filtered results
    csv_gdf['Koordinate_X'] = csv_gdf.geometry.x
    csv_gdf['Koordinate_Y'] = csv_gdf.geometry.y

    # Merge coordinate attributes with LOD2 geometries
    filtered_lod_gdf = filtered_lod_gdf.merge(
        csv_gdf.drop(columns='geometry'), 
        how='left', 
        left_on='ID', 
        right_on='parent_id'
    )
    
    # Export filtered results
    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')
    print(f"Coordinate-filtered LOD2 data saved: {len(parent_ids)} buildings")

def spatial_filter_with_polygon(lod_geojson_path: str, 
                               polygon_shapefile_path: str, 
                               output_geojson_path: str) -> None:
    """
    Filter LOD2 building data within a specified polygon boundary.

    This function performs spatial filtering to extract all LOD2 building components
    that fall within a defined polygon area. It's commonly used for district-level
    analysis, urban planning studies, or extracting building data for specific
    administrative boundaries or study areas.

    Parameters
    ----------
    lod_geojson_path : str
        Path to LOD2 GeoJSON file containing 3D building geometry data.
        Should include complete building models with all components.
    polygon_shapefile_path : str
        Path to polygon shapefile defining the area of interest boundary.
        Can contain single or multiple polygons for filtering.
    output_geojson_path : str
        Output path for spatially filtered LOD2 data in GeoJSON format.
        Contains only buildings within the specified polygon area.

    Notes
    -----
    Spatial Operations:
        1. Load boundary polygon and transform to LOD2 coordinate system
        2. Apply geometry buffering to handle precision issues
        3. Create 2D projections of 3D LOD2 geometries for spatial testing
        4. Identify buildings with any component within polygon boundary
        5. Extract complete building models for matching building IDs

    Filtering Strategy:
        - Uses building ID relationships to maintain complete models
        - Includes all components (walls, roofs, ground) for each building
        - Handles parent-child relationships in LOD2 data structure
        - Preserves all original attributes and 3D geometry information

    Geometric Processing:
        - Coordinate system transformation for spatial compatibility
        - Buffer operations to handle geometric precision issues
        - 2D spatial operations on 3D geometry projections
        - Unary union for multiple polygon boundaries

    Applications:
        - District heating network planning area extraction
        - Municipal building stock analysis
        - Urban development impact assessment
        - Building energy audit area definition

    Examples
    --------
    >>> # Extract buildings within district boundary
    >>> spatial_filter_with_polygon(
    ...     "city_lod2_complete.geojson",
    ...     "district_boundary.shp",
    ...     "district_buildings.geojson"
    ... )

    >>> # Process multiple study areas
    >>> study_areas = ["downtown.shp", "residential.shp", "industrial.shp"]
    >>> for area_file in study_areas:
    ...     area_name = area_file.replace('.shp', '')
    ...     output_file = f"lod2_{area_name}.geojson"
    ...     spatial_filter_with_polygon(
    ...         "complete_lod2.geojson", area_file, output_file
    ...     )

    >>> # Analyze filtered results
    >>> import geopandas as gpd
    >>> buildings = gpd.read_file("district_buildings.geojson")
    >>> building_count = len(buildings['ID'].unique())
    >>> component_stats = buildings['Geometr_3D'].value_counts()
    >>> print(f"Filtered area contains {building_count} buildings")
    >>> print(f"Components: {component_stats.to_dict()}")

    Raises
    ------
    FileNotFoundError
        If LOD2 or polygon files cannot be found.
    ValueError
        If polygon geometry is invalid or coordinate systems incompatible.
    GeometryError
        If spatial operations fail due to geometry issues.

    See Also
    --------
    filter_LOD2_with_coordinates : Point-based filtering
    process_lod2 : Complete LOD2 processing workflow
    """
    # Load polygon boundary and LOD2 data
    polygon_gdf = gpd.read_file(polygon_shapefile_path)
    lod_gdf = gpd.read_file(lod_geojson_path)

    # Transform polygon to LOD2 coordinate system
    polygon_gdf = polygon_gdf.to_crs(lod_gdf.crs)
    polygon_gdf['geometry'] = polygon_gdf['geometry'].buffer(0)  # Fix geometry issues

    # Create 2D version of LOD2 data for spatial operations
    lod_gdf_2d = lod_gdf.copy()
    lod_gdf_2d['geometry'] = lod_gdf_2d['geometry'].buffer(0)  # Fix geometry issues
    
    # Identify buildings within polygon boundary
    ids_within_polygon = lod_gdf_2d[
        lod_gdf_2d.within(polygon_gdf.unary_union)
    ]['ID'].unique()
    
    # Filter complete building models
    filtered_lod_gdf = lod_gdf[lod_gdf['ID'].isin(ids_within_polygon)]

    # Export filtered results
    filtered_lod_gdf.to_file(output_geojson_path, driver='GeoJSON')
    print(f"Spatially filtered LOD2 data saved to {output_geojson_path}")
    print(f"Buildings within polygon: {len(ids_within_polygon)}")

def calculate_polygon_area_3d(polygon: Polygon) -> Optional[float]:
    """
    Calculate the true 3D surface area of a polygon by triangulation.

    This function computes the actual surface area of a 3D polygon by decomposing
    it into triangles and summing their areas. It's essential for accurate area
    calculations of sloped surfaces like roofs and inclined walls in LOD2 data.

    Parameters
    ----------
    polygon : shapely.geometry.Polygon
        3D polygon with Z-coordinates for which to calculate surface area.
        Must have at least 3 coordinate points for valid triangulation.

    Returns
    -------
    Optional[float]
        Surface area of the 3D polygon in square units of the coordinate system,
        or None if polygon is invalid or has insufficient points.

    Notes
    -----
    Triangulation Method:
        1. Extract exterior ring coordinates from polygon
        2. Remove duplicate closing coordinate if present
        3. Use fan triangulation from first vertex as origin
        4. Calculate individual triangle areas using 3D formula
        5. Sum all triangle areas for total polygon area

    3D Area Calculation:
        - Accounts for polygon orientation in 3D space
        - More accurate than 2D projected area for sloped surfaces
        - Essential for thermal calculations and material quantification
        - Handles complex polygon shapes through triangulation

    Geometric Considerations:
        - Assumes planar polygon (all points in same plane)
        - Uses first vertex as triangulation origin
        - Handles both convex and simple concave polygons
        - Requires minimum 3 vertices for valid calculation

    Applications:
        - Roof surface area calculation for solar potential
        - Wall area computation for thermal analysis
        - Material quantity estimation for building components
        - Heat transfer surface area determination

    Examples
    --------
    >>> from shapely.geometry import Polygon
    >>> import numpy as np
    >>> 
    >>> # Flat horizontal polygon
    >>> flat_roof = Polygon([(0,0,10), (10,0,10), (10,10,10), (0,10,10)])
    >>> area_flat = calculate_polygon_area_3d(flat_roof)
    >>> print(f"Flat roof area: {area_flat} m²")  # Should be 100 m²

    >>> # Sloped roof surface
    >>> sloped_roof = Polygon([(0,0,5), (10,0,5), (10,10,8), (0,10,8)])
    >>> area_sloped = calculate_polygon_area_3d(sloped_roof)
    >>> print(f"Sloped roof area: {area_sloped:.1f} m²")  # > 100 m² due to slope

    >>> # Compare with 2D projected area
    >>> area_2d = sloped_roof.area
    >>> area_factor = area_sloped / area_2d
    >>> print(f"3D/2D area ratio: {area_factor:.3f}")

    See Also
    --------
    calculate_triangle_area_3d : Individual triangle area calculation
    calculate_area_3d_for_feature : Multi-geometry area calculation
    """
    if not isinstance(polygon, Polygon):
        return None
        
    # Extract exterior coordinates
    coords = list(polygon.exterior.coords)
    if len(coords) < 3:
        return None
        
    # Remove duplicate closing coordinate
    if coords[0] == coords[-1]:
        coords.pop()
        
    if len(coords) < 3:
        return None

    # Fan triangulation from first vertex
    area = 0.0
    origin = coords[0]
    
    for i in range(1, len(coords) - 1):
        triangle_area = calculate_triangle_area_3d(origin, coords[i], coords[i+1])
        area += triangle_area
        
    return area

def calculate_triangle_area_3d(p1: Tuple[float, float, float], 
                             p2: Tuple[float, float, float], 
                             p3: Tuple[float, float, float]) -> float:
    """
    Calculate the area of a triangle in 3D space using Heron's formula.

    This function computes the true area of a triangle defined by three points
    in 3D space, accounting for the triangle's orientation and providing
    accurate area measurements for sloped surfaces in building geometry.

    Parameters
    ----------
    p1 : Tuple[float, float, float]
        First vertex of triangle as (x, y, z) coordinates.
    p2 : Tuple[float, float, float]
        Second vertex of triangle as (x, y, z) coordinates.
    p3 : Tuple[float, float, float]
        Third vertex of triangle as (x, y, z) coordinates.

    Returns
    -------
    float
        Area of the triangle in square units of the coordinate system.
        Returns 0.0 for degenerate triangles or invalid geometry.

    Notes
    -----
    Heron's Formula Implementation:
        1. Calculate edge lengths using 3D distance formula
        2. Compute semi-perimeter: s = (a + b + c) / 2
        3. Apply Heron's formula: area = √(s(s-a)(s-b)(s-c))
        4. Handle numerical precision issues and invalid cases

    Edge Cases:
        - Degenerate triangles (collinear points) return 0.0
        - Invalid side lengths result in 0.0 area
        - Numerical precision protected by max() function
        - Detailed error reporting for debugging

    Geometric Properties:
        - Works for any triangle orientation in 3D space
        - More robust than cross product for small triangles
        - Handles extreme aspect ratios and small angles
        - Provides stable results for building geometry calculations

    Applications:
        - Building surface area computation
        - Roof and wall area calculation
        - Solar panel area estimation
        - Thermal surface area determination

    Examples
    --------
    >>> # Horizontal triangle
    >>> p1, p2, p3 = (0,0,0), (3,0,0), (0,4,0)
    >>> area = calculate_triangle_area_3d(p1, p2, p3)
    >>> print(f"Right triangle area: {area} m²")  # Should be 6.0

    >>> # Sloped triangle in 3D
    >>> p1, p2, p3 = (0,0,0), (3,0,1), (0,4,2)
    >>> area = calculate_triangle_area_3d(p1, p2, p3)
    >>> print(f"3D triangle area: {area:.2f} m²")

    >>> # Degenerate triangle (collinear points)
    >>> p1, p2, p3 = (0,0,0), (1,1,1), (2,2,2)
    >>> area = calculate_triangle_area_3d(p1, p2, p3)
    >>> print(f"Degenerate triangle area: {area}")  # Should be 0.0

    See Also
    --------
    calculate_distance_3d : 3D distance calculation
    calculate_polygon_area_3d : Polygon area by triangulation
    """
    # Calculate edge lengths using 3D distance
    a = calculate_distance_3d(p1, p2)
    b = calculate_distance_3d(p2, p3)
    c = calculate_distance_3d(p3, p1)
    
    # Calculate semi-perimeter
    s = (a + b + c) / 2

    # Check for degenerate triangle
    discriminant = s * (s - a) * (s - b) * (s - c)
    if discriminant < 0:
        print(f"Invalid triangle edge lengths: a={a:.3f}, b={b:.3f}, c={c:.3f}")
        return 0.0

    # Apply Heron's formula with numerical stability
    return np.sqrt(max(discriminant, 0))

def calculate_distance_3d(point1: Tuple[float, float, float], 
                         point2: Tuple[float, float, float]) -> float:
    """
    Calculate the Euclidean distance between two points in 3D space.

    This function computes the straight-line distance between two 3D points
    using the standard Euclidean distance formula. It's fundamental for
    geometric calculations in 3D building analysis and surface computations.

    Parameters
    ----------
    point1 : Tuple[float, float, float]
        First point as (x, y, z) coordinates.
    point2 : Tuple[float, float, float]
        Second point as (x, y, z) coordinates.

    Returns
    -------
    float
        Euclidean distance between the points in coordinate system units.

    Notes
    -----
    Distance Formula:
        distance = √((x₂-x₁)² + (y₂-y₁)² + (z₂-z₁)²)

    Applications:
        - Edge length calculation for 3D triangles
        - Building dimension measurement
        - Geometric validation and quality control
        - Spatial relationship analysis

    Numerical Considerations:
        - Standard floating-point precision
        - No special handling for very small or large distances
        - Direct implementation of Euclidean formula
        - Suitable for building-scale measurements

    Examples
    --------
    >>> # Horizontal distance
    >>> p1, p2 = (0, 0, 0), (3, 4, 0)
    >>> dist = calculate_distance_3d(p1, p2)
    >>> print(f"2D distance: {dist}")  # Should be 5.0

    >>> # 3D distance with height difference
    >>> p1, p2 = (0, 0, 0), (3, 4, 12)
    >>> dist = calculate_distance_3d(p1, p2)
    >>> print(f"3D distance: {dist}")  # Should be 13.0

    >>> # Same point
    >>> p1, p2 = (1, 2, 3), (1, 2, 3)
    >>> dist = calculate_distance_3d(p1, p2)
    >>> print(f"Zero distance: {dist}")  # Should be 0.0

    See Also
    --------
    calculate_triangle_area_3d : Triangle area using 3D distances
    numpy.linalg.norm : Alternative distance calculation method
    """
    return np.sqrt(
        (point1[0] - point2[0])**2 + 
        (point1[1] - point2[1])**2 + 
        (point1[2] - point2[2])**2
    )

def calculate_area_3d_for_feature(geometry: Union[Polygon, MultiPolygon]) -> float:
    """
    Calculate the total 3D surface area for a geometric feature.

    This function handles both simple polygons and complex multi-polygon
    geometries to compute accurate 3D surface areas. It's essential for
    building component area calculations where geometries may consist of
    multiple disconnected surfaces.

    Parameters
    ----------
    geometry : Union[shapely.geometry.Polygon, shapely.geometry.MultiPolygon]
        Geometric feature for area calculation, supporting both single
        polygons and multi-polygon collections.

    Returns
    -------
    float
        Total 3D surface area of all polygon components in square units.
        Returns 0.0 for invalid or empty geometries.

    Notes
    -----
    Multi-Geometry Handling:
        - **Polygon**: Direct 3D area calculation
        - **MultiPolygon**: Sum of all constituent polygon areas
        - **Invalid geometries**: Return 0.0 with error handling
        - **Empty geometries**: Return 0.0 without error

    Area Calculation Method:
        Uses triangulation-based 3D area calculation for each polygon
        component to ensure accurate surface area measurement regardless
        of polygon orientation or slope in 3D space.

    Applications:
        - Building envelope surface area calculation
        - Roof area computation for solar analysis
        - Wall area determination for thermal calculations
        - Material quantity estimation

    Geometry Requirements:
        - Valid polygon geometries with 3D coordinates
        - Proper polygon topology (no self-intersections)
        - Minimum 3 vertices per polygon for valid calculation
        - Consistent coordinate units across all polygons

    Examples
    --------
    >>> from shapely.geometry import Polygon, MultiPolygon
    >>> 
    >>> # Simple polygon area
    >>> roof = Polygon([(0,0,10), (10,0,10), (10,10,12), (0,10,12)])
    >>> area = calculate_area_3d_for_feature(roof)
    >>> print(f"Roof area: {area:.1f} m²")

    >>> # Multi-polygon building component
    >>> roof1 = Polygon([(0,0,10), (5,0,10), (5,5,10), (0,5,10)])
    >>> roof2 = Polygon([(5,0,10), (10,0,10), (10,5,12), (5,5,12)])
    >>> multi_roof = MultiPolygon([roof1, roof2])
    >>> total_area = calculate_area_3d_for_feature(multi_roof)
    >>> print(f"Total roof area: {total_area:.1f} m²")

    >>> # Handle invalid geometry
    >>> invalid_geom = None
    >>> area = calculate_area_3d_for_feature(invalid_geom)
    >>> print(f"Invalid geometry area: {area}")  # Returns 0.0

    See Also
    --------
    calculate_polygon_area_3d : Single polygon 3D area calculation
    process_lod2 : Complete building area processing
    """
    if geometry is None:
        return 0.0
        
    total_area = 0.0
    
    if isinstance(geometry, Polygon):
        area = calculate_polygon_area_3d(geometry)
        total_area = area if area is not None else 0.0
    elif isinstance(geometry, MultiPolygon):
        for polygon in geometry.geoms:
            area = calculate_polygon_area_3d(polygon)
            if area is not None:
                total_area += area
    else:
        # Handle unsupported geometry types
        return 0.0
        
    return total_area

def calculate_area_from_wall_coordinates(wall_geometries: List[Union[Polygon, MultiPolygon]]) -> float:
    """
    Calculate ground floor area from wall geometry coordinates.

    This function reconstructs building ground area when direct ground surface
    data is missing or invalid by projecting wall geometries to 2D and creating
    a ground polygon from the wall base coordinates.

    Parameters
    ----------
    wall_geometries : List[Union[shapely.geometry.Polygon, shapely.geometry.MultiPolygon]]
        List of wall geometry objects containing 3D coordinate information.
        Each geometry represents a building wall surface.

    Returns
    -------
    float
        Calculated ground area in square units, or 0.0 if calculation fails.

    Notes
    -----
    Ground Area Reconstruction:
        1. Extract all coordinate points from wall geometries
        2. Handle both Polygon and MultiPolygon wall representations
        3. Project 3D coordinates to 2D ground plane (x, y only)
        4. Create ground polygon from projected coordinate points
        5. Calculate 2D area of reconstructed ground polygon

    Reconstruction Strategy:
        - Uses all wall coordinates to define building perimeter
        - Assumes walls define building boundary at ground level
        - Projects to horizontal plane by ignoring Z-coordinates
        - Creates single polygon from all collected points

    Limitations:
        - Assumes building has rectangular or simple ground plan
        - May not work correctly for complex building shapes
        - Requires wall geometries to properly define perimeter
        - No validation of coordinate point ordering

    Applications:
        - Fallback method when ground geometry is missing
        - Building volume calculation when ground area needed
        - Quality control for LOD2 data completeness
        - Area estimation for buildings with incomplete geometry

    Examples
    --------
    >>> from shapely.geometry import Polygon
    >>> 
    >>> # Wall geometries for rectangular building
    >>> wall1 = Polygon([(0,0,0), (10,0,0), (10,0,3), (0,0,3)])  # South wall
    >>> wall2 = Polygon([(10,0,0), (10,10,0), (10,10,3), (10,0,3)])  # East wall
    >>> wall3 = Polygon([(10,10,0), (0,10,0), (0,10,3), (10,10,3)])  # North wall
    >>> wall4 = Polygon([(0,10,0), (0,0,0), (0,0,3), (0,10,3)])  # West wall
    >>> 
    >>> walls = [wall1, wall2, wall3, wall4]
    >>> ground_area = calculate_area_from_wall_coordinates(walls)
    >>> print(f"Reconstructed ground area: {ground_area} m²")  # Should be 100.0

    >>> # Handle missing wall data
    >>> empty_walls = []
    >>> area = calculate_area_from_wall_coordinates(empty_walls)
    >>> print(f"Empty wall list area: {area}")  # Returns 0.0

    See Also
    --------
    process_lod2 : Complete building processing with area calculation
    calculate_area_3d_for_feature : 3D surface area calculation
    """
    if not wall_geometries:
        return 0.0

    # Collect all coordinate points from wall geometries
    all_points = []
    for geom in wall_geometries:
        if isinstance(geom, Polygon):
            all_points.extend(list(geom.exterior.coords))
        elif isinstance(geom, MultiPolygon):
            for poly in geom.geoms:
                all_points.extend(list(poly.exterior.coords))

    # Check if sufficient points for polygon creation
    if len(all_points) < 3:
        return 0.0

    try:
        # Create 2D ground polygon from projected coordinates
        ground_polygon = Polygon([(p[0], p[1]) for p in all_points])
        return ground_polygon.area
    except Exception as e:
        print(f"Error creating ground polygon from wall coordinates: {e}")
        return 0.0

def process_lod2(file_path: str, STANDARD_VALUES: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Process LOD2 building data to extract geometry, calculate areas and volumes.

    This function provides comprehensive processing of LOD2 building data,
    extracting 3D geometry components, calculating accurate surface areas
    and volumes, and integrating building attribute information for
    energy analysis and district heating applications.

    Parameters
    ----------
    file_path : str
        Path to LOD2 file in GeoJSON format containing 3D building geometry data.
        Must include buildings with Ground, Wall, and Roof components.
    STANDARD_VALUES : Dict[str, Any], optional
        Dictionary of default values for missing building properties.
        Used to fill gaps in building attribute data.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Nested dictionary with building IDs as keys and comprehensive building
        information including geometry, areas, volumes, and attributes.

    Notes
    -----
    Processing Workflow:
        1. Load LOD2 GeoJSON data with 3D building components
        2. Group geometry components by building ID (parent-child relationships)
        3. Calculate 3D surface areas for walls, roofs, and ground surfaces
        4. Estimate building volumes from height and ground area data
        5. Integrate building attributes and thermal properties
        6. Apply standard values for missing attributes

    Building Information Structure:
        - **Geometry Lists**: Ground, Wall, Roof geometries
        - **Area Calculations**: Ground_Area, Wall_Area, Roof_Area
        - **Volume Estimation**: Building volume from height or floor count
        - **Height Data**: H_Traufe (eave height), H_Boden (ground height)
        - **Address Information**: Complete geocoded address data
        - **Building Properties**: Type, state, thermal characteristics
        - **Energy Parameters**: U-values, heating system specifications

    Volume Calculation Methods:
        1. **Height-based**: Volume = (H_Traufe - H_Boden) × Ground_Area
        2. **Floor-based**: Volume = Floors × Average_Height × Ground_Area
        3. **Fallback**: Uses 3.0m average floor height when heights missing

    Area Calculation Validation:
        - Primary: 3D surface area calculation from geometry
        - Fallback: Ground area reconstruction from wall coordinates
        - Quality checks for reasonable area values
        - Error handling for invalid geometries

    Examples
    --------
    >>> # Process LOD2 building data
    >>> standard_props = {
    ...     'wall_u': 0.23, 'roof_u': 0.19, 'window_u': 1.3,
    ...     'air_change_rate': 0.5, 'room_temp': 20.0
    ... }
    >>> 
    >>> building_data = process_lod2("city_buildings.geojson", standard_props)
    >>> print(f"Processed {len(building_data)} buildings")

    >>> # Analyze building characteristics
    >>> for building_id, info in building_data.items():
    ...     print(f"Building {building_id}:")
    ...     print(f"  Ground area: {info.get('Ground_Area', 0):.1f} m²")
    ...     print(f"  Volume: {info.get('Volume', 0):.1f} m³")
    ...     print(f"  Address: {info.get('Adresse', 'Unknown')}")

    >>> # Calculate summary statistics
    >>> total_ground_area = sum(info.get('Ground_Area', 0) for info in building_data.values())
    >>> total_volume = sum(info.get('Volume', 0) for info in building_data.values() if info.get('Volume'))
    >>> print(f"Total ground area: {total_ground_area:.0f} m²")
    >>> print(f"Total volume: {total_volume:.0f} m³")

    Raises
    ------
    FileNotFoundError
        If LOD2 file cannot be found or accessed.
    ValueError
        If geometry data is invalid or coordinate calculations fail.
    KeyError
        If required LOD2 data structure is incomplete.

    See Also
    --------
    calculate_area_3d_for_feature : 3D surface area calculation
    calculate_centroid_and_geocode : Address resolution workflow
    normalize_subtype : Building type standardization
    """
    if STANDARD_VALUES is None:
        STANDARD_VALUES = {}
        
    # Load LOD2 GeoJSON data
    gdf = gpd.read_file(file_path)
    building_info = {}

    # Process each geometry record
    for _, row in gdf.iterrows():
        # Determine building ID (use parent ID if available)
        parent_id = row['Obj_Parent'] if row['Obj_Parent'] is not None else row['ID']
        
        # Initialize building record if new
        if parent_id not in building_info:
            building_info[parent_id] = {
                # Geometry lists
                'Ground': [], 'Wall': [], 'Roof': [],
                # Height information
                'H_Traufe': None, 'H_Boden': None,
                # Address information
                'Adresse': None, 'Stadt': None, 'Bundesland': None, 'Land': None,
                'Koordinate_X': None, 'Koordinate_Y': None,
                # Building characteristics
                'Gebäudetyp': None, 'Subtyp': None, 'Typ': None, 'Gebäudezustand': None,
                'Stockwerke': None,
                # Energy parameters
                'ww_demand_kWh_per_m2': None, 'air_change_rate': None,
                'fracture_windows': None, 'fracture_doors': None,
                'Normaußentemperatur': None, 'room_temp': None, 'max_air_temp_heating': None,
                'Wärmebedarf': None, 'WW_Anteil': None,
                # Heating system parameters
                'Typ_Heizflächen': None, 'VLT_max': None, 'Steigung_Heizkurve': None, 'RLT_max': None,
                # Thermal properties (U-values)
                'wall_u': None, 'roof_u': None, 'window_u': None, 'door_u': None, 'ground_u': None
            }

        # Collect geometry components by type
        if row['Geometr_3D'] in ['Ground', 'Wall', 'Roof']:
            building_info[parent_id][row['Geometr_3D']].append(row['geometry'])
        
        # Extract height information
        if 'H_Traufe' in row and (building_info[parent_id]['H_Traufe'] is None or 
                                 building_info[parent_id]['H_Traufe'] != row['H_Traufe']):
            building_info[parent_id]['H_Traufe'] = row['H_Traufe']
        if 'H_Boden' in row and (building_info[parent_id]['H_Boden'] is None or 
                                building_info[parent_id]['H_Boden'] != row['H_Boden']):
            building_info[parent_id]['H_Boden'] = row['H_Boden']

        # Extract address information if available
        if 'Adresse' in row and pd.notna(row['Adresse']):
            building_info[parent_id]['Adresse'] = row['Adresse']
            building_info[parent_id]['Stadt'] = row.get('Stadt')
            building_info[parent_id]['Bundesland'] = row.get('Bundesland')
            building_info[parent_id]['Land'] = row.get('Land')
            building_info[parent_id]['Koordinate_X'] = row.get('Koordinate_X')
            building_info[parent_id]['Koordinate_Y'] = row.get('Koordinate_Y')
        
        # Extract building characteristics and parameters
        attribute_fields = [
            'Stockwerke', 'Gebäudetyp', 'Subtyp', 'Typ', 'Gebäudezustand',
            'ww_demand_kWh_per_m2', 'air_change_rate', 'fracture_windows', 'fracture_doors',
            'Normaußentemperatur', 'room_temp', 'max_air_temp_heating', 'Wärmebedarf', 'WW_Anteil',
            'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max',
            'wall_u', 'roof_u', 'window_u', 'door_u', 'ground_u'
        ]
        
        for field in attribute_fields:
            if field in row and pd.notna(row[field]):
                if field == 'Subtyp':
                    building_info[parent_id][field] = normalize_subtype(row[field])
                else:
                    building_info[parent_id][field] = row[field]

    # Calculate areas and volumes for each building
    for parent_id, info in building_info.items():
        # Calculate 3D surface areas
        info['Ground_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Ground'])
        info['Wall_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Wall'])
        info['Roof_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Roof'])

        # Fallback ground area calculation from wall coordinates
        if not info['Ground_Area'] or np.isnan(info['Ground_Area']):
            info['Ground_Area'] = calculate_area_from_wall_coordinates(info['Wall'])

        # Calculate building volume
        h_traufe = info['H_Traufe']
        h_boden = info['H_Boden']
        
        if h_traufe and h_boden and info['Ground_Area']:
            # Primary method: height-based volume calculation
            info['Volume'] = (h_traufe - h_boden) * info['Ground_Area']
        elif info['Stockwerke'] and info['Ground_Area']:
            # Fallback method: floor-based volume estimation
            durchschnittliche_stockwerkshoehe = 3.0  # Average floor height
            info['Volume'] = info['Stockwerke'] * durchschnittliche_stockwerkshoehe * info['Ground_Area']
        else:
            info['Volume'] = None

        # Apply standard values for missing attributes
        for key, value in STANDARD_VALUES.items():
            if key not in info or info[key] is None:
                info[key] = value

    return building_info

def normalize_subtype(subtype: Union[str, int, float]) -> str:
    """
    Normalize building subtype to consistent two-digit string format.

    This function standardizes building subtype identifiers to ensure
    consistent formatting across different data sources and to support
    proper integration with building typology databases.

    Parameters
    ----------
    subtype : Union[str, int, float]
        Building subtype identifier in various formats (string, integer, or float).
        Common inputs: 1, 1.0, "1", "01", etc.

    Returns
    -------
    str
        Normalized subtype as zero-padded two-digit string (e.g., "01", "15").

    Notes
    -----
    Normalization Process:
        1. Convert input to float then integer to handle decimal values
        2. Convert to string representation
        3. Apply zero-padding to ensure two-digit format
        4. Handle edge cases and invalid inputs gracefully

    Format Standardization:
        - Single digits become zero-padded (1 → "01")
        - Double digits remain unchanged (15 → "15")
        - Decimal values truncated to integer (1.0 → "01")
        - Consistent string output format for database integration

    Applications:
        - Building typology database integration
        - TABULA building type standardization
        - Data quality assurance for building classifications
        - Consistent identifier formatting across datasets

    Examples
    --------
    >>> # Various input formats
    >>> normalize_subtype(1)          # Returns "01"
    >>> normalize_subtype(1.0)        # Returns "01"
    >>> normalize_subtype("3")        # Returns "03"
    >>> normalize_subtype(15)         # Returns "15"
    >>> normalize_subtype("15")       # Returns "15"

    >>> # Batch processing
    >>> subtypes = [1, 2.0, "3", 15, "25"]
    >>> normalized = [normalize_subtype(st) for st in subtypes]
    >>> print(normalized)  # ["01", "02", "03", "15", "25"]

    See Also
    --------
    process_lod2 : Building data processing with subtype normalization
    """
    try:
        # Convert to integer via float to handle decimal inputs
        subtype_int = int(float(subtype))
        # Convert to zero-padded two-digit string
        return str(subtype_int).zfill(2)
    except (ValueError, TypeError):
        # Handle invalid inputs by returning original as string
        return str(subtype)

def geocode(lat: float, lon: float) -> str:
    """
    Convert latitude and longitude coordinates to a human-readable address.

    This function uses the Nominatim geocoding service to perform reverse
    geocoding, converting geographic coordinates to structured address
    information for building location identification and data enrichment.

    Parameters
    ----------
    lat : float
        Latitude coordinate in decimal degrees (WGS84).
    lon : float
        Longitude coordinate in decimal degrees (WGS84).

    Returns
    -------
    str
        Complete address string with hierarchical components,
        or error message if geocoding fails.

    Notes
    -----
    Geocoding Service:
        - Uses OpenStreetMap Nominatim service
        - Requires internet connection for operation
        - Subject to usage limits and fair use policy
        - Returns most specific address available

    Address Components:
        Typical German address format includes:
        - House number and street name
        - Postal code and city
        - State (Bundesland) and country
        - Additional location identifiers

    Error Handling:
        - Network connectivity issues
        - Invalid coordinate inputs
        - Service unavailable responses
        - Rate limiting and timeout handling

    Usage Considerations:
        - Respect Nominatim usage policy
        - Implement delays for batch processing
        - Cache results to avoid repeated requests
        - Handle service interruptions gracefully

    Examples
    --------
    >>> # Geocode building location
    >>> lat, lon = 51.0504, 13.7373  # Dresden coordinates
    >>> address = geocode(lat, lon)
    >>> print(f"Address: {address}")
    >>> # Output: "Hauptstraße 1, 01067 Dresden, Sachsen, Deutschland"

    >>> # Handle geocoding failure
    >>> lat, lon = 0.0, 0.0  # Invalid coordinates
    >>> address = geocode(lat, lon)
    >>> print(f"Result: {address}")
    >>> # Output: "Adresse konnte nicht gefunden werden"

    >>> # Batch geocoding with delay
    >>> import time
    >>> coordinates = [(51.05, 13.74), (52.52, 13.40)]
    >>> for lat, lon in coordinates:
    ...     address = geocode(lat, lon)
    ...     print(f"({lat}, {lon}): {address}")
    ...     time.sleep(1)  # Respect rate limits

    Raises
    ------
    GeopyError
        If geocoding service encounters errors.
    TimeoutError
        If service request times out.

    See Also
    --------
    calculate_centroid_and_geocode : Building centroid address resolution
    geopy.geocoders.Nominatim : Underlying geocoding service
    """
    try:
        # Initialize Nominatim geocoder with user agent
        geolocator = Nominatim(user_agent="LOD2_heating_demand")
        
        # Perform reverse geocoding
        location = geolocator.reverse((lat, lon), exactly_one=True)
        
        # Return address or error message
        return location.address if location else "Adresse konnte nicht gefunden werden"
    except Exception as e:
        print(f"Geocoding error for coordinates ({lat}, {lon}): {e}")
        return "Adresse konnte nicht gefunden werden"

def calculate_centroid_and_geocode(building_info: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate building centroids and resolve addresses through geocoding.

    This function computes the geometric centroid of each building from its
    ground surface geometries and uses reverse geocoding to determine the
    building's address information for data enrichment and location identification.

    Parameters
    ----------
    building_info : Dict[str, Dict[str, Any]]
        Dictionary containing building information with Ground geometry lists.
        Each building should have a 'Ground' key with geometry objects.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Updated building information dictionary with centroid coordinates
        and geocoded address components added to each building record.

    Notes
    -----
    Centroid Calculation:
        1. Create geometric union of all ground surface polygons
        2. Calculate centroid point of unified ground geometry
        3. Extract UTM coordinates for local reference
        4. Transform to WGS84 coordinates for geocoding

    Address Resolution Process:
        1. Transform centroid to geographic coordinates (lat/lon)
        2. Perform reverse geocoding using Nominatim service
        3. Parse address components into structured fields
        4. Store hierarchical address information

    Address Component Structure:
        - **Land**: Country (Deutschland)
        - **Bundesland**: State (e.g., Sachsen, Bayern)
        - **PLZ**: Postal code
        - **Stadt**: City or municipality
        - **Stadtteil**: District or neighborhood
        - **Adresse**: Street name and house number

    Coordinate Systems:
        - **Input**: EPSG:25833 (UTM Zone 33N for Germany)
        - **Geocoding**: EPSG:4326 (WGS84 lat/lon)
        - **Storage**: Both UTM and geographic coordinates

    Examples
    --------
    >>> # Process building centroids and addresses
    >>> building_data = {
    ...     'building_1': {
    ...         'Ground': [ground_polygon_1, ground_polygon_2],
    ...         'Wall': [...], 'Roof': [...]
    ...     }
    ... }
    >>> 
    >>> updated_data = calculate_centroid_and_geocode(building_data)
    >>> 
    >>> # Access address information
    >>> building = updated_data['building_1']
    >>> print(f"Address: {building['Adresse']}")
    >>> print(f"City: {building['Stadt']}")
    >>> print(f"Coordinates: {building['Koordinate_X']}, {building['Koordinate_Y']}")

    >>> # Batch process multiple buildings
    >>> for building_id, info in updated_data.items():
    ...     if info.get('Adresse'):
    ...         print(f"{building_id}: {info['Adresse']}, {info['Stadt']}")
    ...     else:
    ...         print(f"{building_id}: Address not resolved")

    >>> # Validate coordinate transformation
    >>> building = updated_data['building_1']
    >>> utm_x, utm_y = building['Koordinate_X'], building['Koordinate_Y']
    >>> print(f"UTM coordinates: {utm_x:.1f}, {utm_y:.1f}")

    Error Handling:
        - Missing ground geometries result in None coordinates
        - Geocoding failures are logged and handled gracefully
        - Invalid geometries are skipped with warning messages
        - Network errors during geocoding are captured

    Raises
    ------
    ValueError
        If coordinate transformation fails.
    GeometryError
        If ground geometry union operation fails.

    See Also
    --------
    geocode : Address resolution from coordinates
    process_lod2 : Complete building processing workflow
    """
    for parent_id, info in building_info.items():
        try:
            # Check for ground geometry availability
            if 'Ground' in info and info['Ground']:
                # Create geometric union of all ground surfaces
                ground_union = gpd.GeoSeries(info['Ground']).unary_union
                centroid = ground_union.centroid

                # Extract UTM coordinates (EPSG:25833)
                gdf = gpd.GeoDataFrame([{'geometry': centroid}], crs="EPSG:25833")
                info['Koordinate_X'] = gdf.geometry.iloc[0].x
                info['Koordinate_Y'] = gdf.geometry.iloc[0].y

                # Transform to geographic coordinates for geocoding
                gdf = gdf.to_crs(epsg=4326)
                centroid_transformed = gdf.geometry.iloc[0]
                lat, lon = centroid_transformed.y, centroid_transformed.x

                # Perform reverse geocoding
                address_components = geocode(lat, lon)

                # Parse address components
                if address_components != "Adresse konnte nicht gefunden werden":
                    # Split and reverse address components for hierarchical parsing
                    address_parts = address_components.split(", ")
                    address_parts = address_parts[::-1]  # Reverse for easier indexing

                    # Extract address components with safe indexing
                    info['Land'] = address_parts[0] if len(address_parts) > 0 else None
                    info['Bundesland'] = address_parts[1] if len(address_parts) > 1 else None
                    info['PLZ'] = address_parts[2] if len(address_parts) > 2 else None
                    info['Stadt'] = address_parts[3] if len(address_parts) > 3 else None
                    info['Stadtteil'] = address_parts[4] if len(address_parts) > 4 else None
                    
                    # Combine street and house number
                    strasse = address_parts[5] if len(address_parts) > 5 else None
                    hausnummer = address_parts[6] if len(address_parts) > 6 else None
                    info['Adresse'] = f"{strasse} {hausnummer}" if strasse and hausnummer else strasse
                else:
                    # Set all address fields to None for failed geocoding
                    address_fields = ['Land', 'Bundesland', 'PLZ', 'Stadt', 'Stadtteil', 'Adresse']
                    for field in address_fields:
                        info[field] = None

            else:
                # Handle buildings without ground geometry
                print(f"No ground geometry found for building {parent_id}. Skipping centroid calculation.")
                coordinate_fields = ['Koordinate_X', 'Koordinate_Y', 'Land', 'Bundesland', 
                                   'PLZ', 'Stadt', 'Stadtteil', 'Adresse']
                for field in coordinate_fields:
                    info[field] = None

        except Exception as e:
            print(f"Error processing centroid and geocoding for building {parent_id}: {e}")
            # Set coordinate and address fields to None on error
            error_fields = ['Koordinate_X', 'Koordinate_Y', 'Land', 'Bundesland', 
                          'PLZ', 'Stadt', 'Stadtteil', 'Adresse']
            for field in error_fields:
                info[field] = None

    return building_info

def calculate_normal_and_angles(roof_geom: Union[Polygon, MultiPolygon]) -> List[Tuple[np.ndarray, float, float, float]]:
    """
    Calculate the normal vector, slope (inclination), azimuth (orientation), and area of each polygon within a roof geometry.

    This function analyzes 3D roof geometry to determine surface orientation and geometric
    properties essential for solar photovoltaic potential assessment, thermal analysis,
    and building energy modeling. It handles both simple and complex roof structures
    with multiple surfaces and orientations.

    Parameters
    ----------
    roof_geom : Union[shapely.geometry.Polygon, shapely.geometry.MultiPolygon]
        3D roof geometry containing surface polygons with Z-coordinates.
        Can be either a single polygon for simple roofs or MultiPolygon for complex roof structures.

    Returns
    -------
    List[Tuple[numpy.ndarray, float, float, float]]
        List of tuples, each containing:
        
        - **normal_vector** (numpy.ndarray) : 3D unit normal vector [x, y, z]
        - **slope** (float) : Surface inclination angle in degrees [0-90°]
        - **azimuth** (float) : Surface orientation angle in degrees [-180° to 180°]
        - **area** (float) : 2D projected surface area in coordinate system units

    Notes
    -----
    Geometric Calculations:
        The function uses vector cross product to determine surface normal vectors
        from the first three vertices of each polygon, then derives slope and
        azimuth angles from the normal vector components.

    Normal Vector Calculation:
        1. Extract first three coordinate points from polygon exterior
        2. Calculate edge vectors: v1 = p2 - p1, v2 = p3 - p1
        3. Compute cross product: normal = v1 × v2
        4. Normalize to unit vector: normal = normal / ||normal||

    Angle Derivation:
        - **Slope (Inclination)**: arccos(normal_z) - angle from vertical
        - **Azimuth (Orientation)**: arctan2(normal_y, normal_x) - compass direction

    Azimuth Convention:
        - 0° = East (positive X-axis)
        - 90° = North (positive Y-axis)
        - 180°/-180° = West (negative X-axis)
        - -90° = South (negative Y-axis)

    Slope Interpretation:
        - 0° = Horizontal surface (flat roof)
        - 30° = Typical residential roof pitch
        - 45° = Steep roof surface
        - 90° = Vertical surface (wall)

    Applications:
        - **Solar PV Analysis**: Optimal panel placement and energy yield estimation
        - **Thermal Modeling**: Heat transfer calculations for building envelope
        - **Rainwater Management**: Drainage pattern analysis and capacity planning
        - **Wind Load Assessment**: Aerodynamic force calculations for structural design

    Examples
    --------
    >>> from shapely.geometry import Polygon, MultiPolygon
    >>> import numpy as np
    >>> 
    >>> # Simple south-facing sloped roof
    >>> south_roof = Polygon([
    ...     (0, 0, 5),    # Ridge line
    ...     (10, 0, 5),   # Ridge line
    ...     (10, 10, 2),  # Eave line
    ...     (0, 10, 2)    # Eave line
    ... ])
    >>> results = calculate_normal_and_angles(south_roof)
    >>> normal, slope, azimuth, area = results[0]
    >>> print(f"South roof: {slope:.1f}° slope, {azimuth:.1f}° azimuth")

    >>> # Complex gabled roof with east and west faces
    >>> east_face = Polygon([(0,0,5), (5,0,8), (5,10,8), (0,10,5)])
    >>> west_face = Polygon([(5,0,8), (10,0,5), (10,10,5), (5,10,8)])
    >>> gabled_roof = MultiPolygon([east_face, west_face])
    >>> 
    >>> results = calculate_normal_and_angles(gabled_roof)
    >>> for i, (normal, slope, azimuth, area) in enumerate(results):
    ...     print(f"Face {i+1}: {slope:.1f}° slope, {azimuth:.1f}° azimuth, {area:.1f}m²")

    >>> # Analyze solar potential
    >>> def assess_solar_potential(slope, azimuth):
    ...     # Optimal conditions: 30-45° slope, south-facing (-90° to 90°)
    ...     slope_factor = 1.0 - abs(slope - 37.5) / 37.5  # Optimal at 37.5°
    ...     azimuth_factor = 1.0 - abs(azimuth) / 180.0    # Optimal at 0° (south)
    ...     return slope_factor * azimuth_factor
    >>> 
    >>> for normal, slope, azimuth, area in results:
    ...     potential = assess_solar_potential(slope, azimuth)
    ...     print(f"Solar potential: {potential:.2f} (area: {area:.1f}m²)")

    Error Handling:
        - Polygons with fewer than 3 vertices return None values
        - Invalid geometries are skipped with warning
        - Zero-length vectors handled by normalization check
        - Degenerate polygons (collinear points) filtered out

    See Also
    --------
    process_roof : Complete roof analysis workflow
    calculate_area_3d_for_feature : 3D surface area calculation
    numpy.cross : Vector cross product calculation
    numpy.arccos, numpy.arctan2 : Angle calculation functions
    """

    def calculate_single_polygon(polygon: Polygon) -> Tuple[Optional[np.ndarray], Optional[float], Optional[float], Optional[float]]:
        """
        Helper function to calculate geometric properties for a single polygon.
        
        Parameters
        ----------
        polygon : shapely.geometry.Polygon
            3D polygon representing a roof surface section.
            
        Returns
        -------
        Tuple[Optional[numpy.ndarray], Optional[float], Optional[float], Optional[float]]
            Normal vector, slope, azimuth, and area, or None values if calculation fails.
        """
        coords = list(polygon.exterior.coords)
        if len(coords) < 3:
            return None, None, None, None

        try:
            # Extract first three points for normal vector calculation
            p1 = np.array(coords[0])
            p2 = np.array(coords[1])
            p3 = np.array(coords[2])
            
            # Calculate edge vectors
            v1 = p2 - p1
            v2 = p3 - p1
            
            # Compute surface normal vector
            normal = np.cross(v1, v2)
            normal_magnitude = np.linalg.norm(normal)
            
            # Check for degenerate polygon (collinear points)
            if normal_magnitude == 0:
                return None, None, None, None
                
            # Normalize to unit vector
            normal = normal / normal_magnitude
            
            # Calculate inclination angle (slope from horizontal)
            # normal[2] is the Z-component of the unit normal vector
            inclination = np.degrees(np.arccos(np.clip(abs(normal[2]), 0, 1)))
            
            # Calculate azimuth angle (orientation from east)
            # Uses atan2 for proper quadrant handling
            azimuth = np.degrees(np.arctan2(normal[1], normal[0]))

            # Calculate 2D projected area of polygon
            area = polygon.area

            return normal, inclination, azimuth, area
            
        except Exception as e:
            print(f"Error calculating polygon properties: {e}")
            return None, None, None, None

    results = []

    if isinstance(roof_geom, MultiPolygon):
        # Process each polygon in the MultiPolygon collection
        for polygon in roof_geom.geoms:
            result = calculate_single_polygon(polygon)
            if result[0] is not None:  # Check if calculation was successful
                results.append(result)

    elif isinstance(roof_geom, Polygon):
        # Process single polygon
        result = calculate_single_polygon(roof_geom)
        if result[0] is not None:  # Check if calculation was successful
            results.append(result)
    else:
        print(f"Unsupported geometry type: {type(roof_geom)}")

    return results

def process_roof(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Process LOD2 data to calculate comprehensive roof geometry analysis for photovoltaic potential assessment.

    This function performs detailed analysis of roof surfaces from LOD2 building data,
    calculating geometric properties, orientation parameters, and surface areas
    essential for solar photovoltaic system planning, building energy modeling,
    and renewable energy potential assessment.

    Parameters
    ----------
    file_path : str
        Path to LOD2 GeoJSON file containing 3D building geometry data.
        Must include buildings with Ground, Wall, and Roof components with 3D coordinates.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Nested dictionary containing comprehensive building and roof analysis data:
        
        - **Building ID** (str) : Dictionary key for each building
        - **Geometry Collections** (List) : Ground, Wall, Roof geometry objects
        - **Area Calculations** (float) : Ground_Area, Wall_Area, Roof_Area in m²
        - **Roof Analysis** (List[Dict]) : Detailed roof surface data including:
            - geometry : Original roof surface geometry
            - Roof_Slope : Surface inclination angle [degrees]
            - Roof_Orientation : Surface azimuth angle [degrees]
            - Area : Surface area [m²]
            - Normal_Vector : 3D surface normal vector
            - parent_id : Building identifier for relationship tracking
        - **Location Data** (Optional) : Address and coordinate information

    Notes
    -----
    Processing Workflow:
        1. Load LOD2 GeoJSON data with 3D building components
        2. Group geometry components by building ID using parent-child relationships
        3. Process roof geometries to calculate slope, orientation, and area
        4. Calculate total building surface areas for thermal analysis
        5. Integrate address information where available
        6. Apply fallback area calculations for missing ground data

    Roof Analysis Details:
        For each roof surface segment:
        - **Normal Vector Calculation**: 3D surface orientation vector
        - **Slope Analysis**: Inclination angle for drainage and PV optimization
        - **Azimuth Determination**: Compass orientation for solar exposure
        - **Area Computation**: Surface area for system sizing
        - **Geometry Preservation**: Original 3D polygon for visualization

    Building Component Integration:
        - **Ground Surfaces**: Foundation footprint and area calculation
        - **Wall Surfaces**: Envelope area for thermal analysis
        - **Roof Surfaces**: Detailed analysis for PV and thermal applications
        - **Address Data**: Location context for project planning

    Data Quality Assurance:
        - Fallback ground area calculation from wall coordinates
        - Validation of geometry relationships and areas
        - Error handling for incomplete or invalid geometries
        - Preservation of all original geometry data

    Applications:
        - **Solar PV Planning**: Roof surface analysis for panel placement
        - **Building Energy Modeling**: Envelope surface area calculations
        - **Urban Planning**: Building stock renewable energy potential
        - **Architectural Analysis**: Roof design and orientation assessment

    Examples
    --------
    >>> # Process LOD2 building data for PV analysis
    >>> building_data = process_roof("municipal_buildings_lod2.geojson")
    >>> print(f"Analyzed {len(building_data)} buildings")

    >>> # Analyze roof characteristics
    >>> for building_id, info in building_data.items():
    ...     print(f"\nBuilding {building_id}:")
    ...     print(f"  Address: {info.get('Adresse', 'Unknown')}")
    ...     print(f"  Total roof area: {info['Roof_Area']:.1f} m²")
    ...     print(f"  Roof surfaces: {len(info['Roofs'])}")
    ...     
    ...     # Analyze individual roof surfaces
    ...     for i, roof in enumerate(info['Roofs']):
    ...         slope = roof['Roof_Slope']
    ...         orientation = roof['Roof_Orientation']
    ...         area = roof['Area']
    ...         print(f"    Surface {i+1}: {slope:.1f}° slope, {orientation:.1f}° azimuth, {area:.1f}m²")

    >>> # Assess solar potential
    >>> def assess_pv_suitability(slope, azimuth, area):
    ...     # Optimal: 30-45° slope, south-facing (azimuth ±90°)
    ...     if 20 <= slope <= 50 and -120 <= azimuth <= 120:
    ...         return area * (1 - abs(slope - 35)/15) * (1 - abs(azimuth)/120)
    ...     return 0
    >>> 
    >>> total_suitable_area = 0
    >>> for building_id, info in building_data.items():
    ...     building_suitable = 0
    ...     for roof in info['Roofs']:
    ...         suitable_area = assess_pv_suitability(
    ...             roof['Roof_Slope'], roof['Roof_Orientation'], roof['Area']
    ...         )
    ...         building_suitable += suitable_area
    ...     
    ...     total_suitable_area += building_suitable
    ...     print(f"Building {building_id}: {building_suitable:.1f}m² suitable for PV")
    >>> 
    >>> print(f"Total suitable roof area: {total_suitable_area:.1f}m²")

    >>> # Export roof analysis results
    >>> import pandas as pd
    >>> roof_data = []
    >>> for building_id, info in building_data.items():
    ...     for i, roof in enumerate(info['Roofs']):
    ...         roof_data.append({
    ...             'Building_ID': building_id,
    ...             'Surface_ID': i+1,
    ...             'Slope_deg': roof['Roof_Slope'],
    ...             'Azimuth_deg': roof['Roof_Orientation'],
    ...             'Area_m2': roof['Area'],
    ...             'Address': info.get('Adresse', 'Unknown')
    ...         })
    >>> 
    >>> df = pd.DataFrame(roof_data)
    >>> df.to_csv('roof_analysis_results.csv', index=False)

    Error Handling:
        - Missing geometry components handled gracefully
        - Invalid roof geometries skipped with logging
        - Fallback calculations for missing ground areas
        - Address data integration with null value handling

    Raises
    ------
    FileNotFoundError
        If LOD2 file cannot be found or accessed.
    ValueError
        If geometry data is invalid or coordinate calculations fail.
    KeyError
        If required LOD2 data structure is incomplete.

    See Also
    --------
    calculate_normal_and_angles : Roof surface geometric analysis
    calculate_area_3d_for_feature : 3D surface area calculation
    calculate_area_from_wall_coordinates : Fallback ground area calculation
    process_lod2 : Complete building geometry processing
    """
    # Load LOD2 GeoJSON data
    gdf = gpd.read_file(file_path)
    building_info = {}

    # Process each geometry record in the dataset
    for _, row in gdf.iterrows():
        # Determine building ID using parent-child relationships
        parent_id = row['Obj_Parent'] if 'Obj_Parent' in row and row['Obj_Parent'] is not None else row['ID']
        
        # Initialize building record if not exists
        if parent_id not in building_info:
            building_info[parent_id] = {
                # Geometry component collections
                'Ground': [], 'Wall': [], 'Roofs': [],
                # Location and address information
                'Koordinate_X': None, 'Koordinate_Y': None,
                'Adresse': None, 'Stadt': None, 'Bundesland': None, 'Land': None
            }

        # Collect geometry components by type
        if row['Geometr_3D'] == 'Ground':
            building_info[parent_id]['Ground'].append(row['geometry'])
        elif row['Geometr_3D'] == 'Wall':
            building_info[parent_id]['Wall'].append(row['geometry'])
        elif row['Geometr_3D'] == 'Roof':
            # Perform detailed roof surface analysis
            roof_segments = calculate_normal_and_angles(row['geometry'])
            
            # Process each roof surface segment
            for normal, roof_slope, roof_orientation, area in roof_segments:
                if normal is not None:  # Ensure valid calculation results
                    roof_data = {
                        'geometry': row['geometry'],
                        'Roof_Slope': roof_slope,
                        'Roof_Orientation': roof_orientation,
                        'Area': area,
                        'Normal_Vector': normal,
                        'parent_id': parent_id
                    }
                    building_info[parent_id]['Roofs'].append(roof_data)

        # Extract and store address information if available
        if 'Adresse' in row and pd.notna(row['Adresse']):
            building_info[parent_id]['Adresse'] = row['Adresse']
            building_info[parent_id]['Stadt'] = row.get('Stadt')
            building_info[parent_id]['Bundesland'] = row.get('Bundesland')
            building_info[parent_id]['Land'] = row.get('Land')
            building_info[parent_id]['Koordinate_X'] = row.get('Koordinate_X')
            building_info[parent_id]['Koordinate_Y'] = row.get('Koordinate_Y')

    # Calculate comprehensive area measurements for each building
    for parent_id, info in building_info.items():
        # Calculate 3D surface areas for building components
        info['Ground_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Ground'])
        info['Wall_Area'] = sum(calculate_area_3d_for_feature(geom) for geom in info['Wall'])
        info['Roof_Area'] = sum(roof['Area'] for roof in info['Roofs'])

        # Apply fallback ground area calculation if needed
        if not info['Ground_Area'] or np.isnan(info['Ground_Area']):
            info['Ground_Area'] = calculate_area_from_wall_coordinates(info['Wall'])
            if info['Ground_Area'] > 0:
                print(f"Building {parent_id}: Used wall-based ground area calculation")

    print(f"Processed {len(building_info)} buildings with roof analysis")
    return building_info
