"""
Filename: Wärmeversorgungsgebiete.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Script with functionality to process OSM data and cluster buildings.

"""

import numpy as np
import geopandas as gpd
#from sklearn.cluster import DBSCAN # pip install scikit-learn
import hdbscan
"""To install hdbscan: 
Besuchen Sie die Webseite für die Microsoft C++ Build Tools.

Laden Sie den Installer herunter und führen Sie ihn aus.

Wählen Sie im Installer die Option "C++ build tools" aus, stellen Sie sicher, dass die neueste Version von MSVC v142 - VS 2019 C++ x64/x86 build tools (oder höher) ausgewählt ist, sowie die Windows 10 SDK.

Schließen Sie die Installation ab und starten Sie Ihren Computer neu, wenn dazu aufgefordert wird.

Installieren sie hdbscan mit pip install hdbscan"""

from shapely.geometry import Polygon, shape

# Set thresholds for deciding on the supply method
# Buildings with a heat requirement above the heating network threshold receive a heating network supply,
# Buildings above the hydrogen threshold receive a hydrogen supply,
# all others receive a single supply solution.

def versorgungsgebiet_bestimmen(area_specific_heat_requirement, threshold_heat_network, threshold_hydrogen):
    if area_specific_heat_requirement > threshold_heat_network:
        return 'Wärmenetzversorgung'
    elif area_specific_heat_requirement > threshold_hydrogen:
        return 'Wasserstoffversorgung'
    else:
        return 'Einzelversorgungslösung'

def clustering_districts_hdbscan(gdf, buffer_size=10, min_cluster_size=30, min_samples=1, threshold_heat_network=90, threshold_hydrogen=60):
    # Add buffer zone around each building
    gdf['buffered_geometry'] = gdf.geometry.buffer(buffer_size)

    # Prepare coordinates of building centers (taking the buffer into account) for clustering
    coords = np.array(list(zip(gdf['buffered_geometry'].centroid.x, gdf['buffered_geometry'].centroid.y)))

    # Apply HDBSCAN algorithm to cluster the coordinates
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples, gen_min_span_tree=True)
    cluster_labels = clusterer.fit_predict(coords)

    # Adding the cluster labels to the GeoDataFrame
    gdf['quartier_label'] = cluster_labels

    # Remove noise marked as '-1'
    gdf = gdf[gdf['quartier_label'] != -1]

    # Grouping the buildings into clusters and creating polygons for each cluster
    # Use a custom aggregation function on the geometry data
    for index, row in gdf.iterrows():
        geom = shape(row['geometry'])
        if not geom.is_valid:
            # If the geometry is invalid, you can repair or remove it
            # Here we use `buffer(0)` to debug to remove invalid geometries
            gdf.at[index, 'geometry'] = geom.buffer(0)
    quarters = gdf.dissolve(by='quartier_label', aggfunc={'buffered_geometry': lambda x: x.unary_union.convex_hull})

    # Defining neighborhood boundaries with convex hulls
    quarters['geometry'] = quarters['buffered_geometry']

    # Calculate area-specific heat requirements
    quarters['gesamtwaermebedarf'] = gdf.groupby('quartier_label')['Jahreswärmebedarf [kWh/a]'].sum()
    quarters['flaeche'] = quarters.geometry.area
    quarters['flaechenspezifischer_waermebedarf'] = quarters['gesamtwaermebedarf'] / quarters['flaeche']

    # Assign supply area based on area-specific heat requirements
    quarters['Versorgungsgebiet'] = quarters.apply(lambda row: versorgungsgebiet_bestimmen(row['flaechenspezifischer_waermebedarf'], threshold_heat_network, threshold_hydrogen), axis=1)

    # Delete all unnecessary columns, keeping only the relevant ones
    quarters = quarters[['geometry', 'gesamtwaermebedarf', 'flaeche', 'flaechenspezifischer_waermebedarf', 'Versorgungsgebiet']]
    quarters = quarters.reset_index()

    return quarters

def postprocessing_hdbscan(quarters):
    # Load the original cluster data
    quarters['geometry'] = quarters['geometry'].buffer(0)  # This can help fix some geometry problems

    # Flag to track overlap resolution progress
    overlapping_exists = True
    while overlapping_exists:
        # Make a copy for postprocessing
        quarters_postprocessed = quarters.copy()
        quarters_postprocessed = quarters_postprocessed.drop_duplicates(subset=['quartier_label'])
        quarters_postprocessed = quarters_postprocessed.dropna(subset=['Versorgungsgebiet'])
        
        # Perform a spatial join to identify neighboring polygons
        joined = gpd.sjoin(quarters_postprocessed, quarters_postprocessed, how='left', predicate='intersects')
        # Filter results to only keep couples with the same care type
        same_supply_type = joined[joined['Versorgungsgebiet_left'] == joined['Versorgungsgebiet_right']]

        overlapping_exists = False

        # Merge the polygons that have the same supply type and touch each other
        for index, row in same_supply_type.iterrows():
            index_left = row['quartier_label_left']
            index_right = row['quartier_label_right']

            if index_left != index_right:
                left_geoms = quarters_postprocessed[quarters_postprocessed['quartier_label'] == index_left]['geometry']
                right_geoms = quarters_postprocessed[quarters_postprocessed['quartier_label'] == index_right]['geometry']

                if not left_geoms.is_empty.all() and not right_geoms.is_empty.all():
                    current_geometry = left_geoms.unary_union
                    touching_geometry = right_geoms.unary_union

                    if current_geometry is not None and touching_geometry is not None:
                        unified_geometry = current_geometry.union(touching_geometry)
                        
                        # Update geometry for each line individually
                        for idx in quarters_postprocessed[quarters_postprocessed['quartier_label'] == index_left].index:
                            quarters_postprocessed.at[idx, 'geometry'] = unified_geometry
                        
                        # Delete the second polygon
                        quarters_postprocessed = quarters_postprocessed[quarters_postprocessed['quartier_label'] != index_right]
                        overlapping_exists = True

        quarters = quarters_postprocessed

    # Reset index outside the loop
    quarters_postprocessed.reset_index(drop=True, inplace=True)

    return quarters_postprocessed

def allocate_overlapping_area(quarters):
    # Spatial join for intersecting polygons
    overlapping = gpd.sjoin(quarters, quarters, how='inner', predicate='intersects')

    # Filter only couples with different care types
    different_supply = overlapping[overlapping['Versorgungsgebiet_left'] != overlapping['Versorgungsgebiet_right']]

    for idx, row in different_supply.iterrows():
        idx_left = row['quartier_label_left']
        idx_right = row['quartier_label_right']

        # Find the rows corresponding to the given cluster labels
        row_left = quarters[quarters['quartier_label'] == idx_left]
        row_right = quarters[quarters['quartier_label'] == idx_right]

        if not row_left.empty and not row_right.empty:
            # Find the associated geometries based on the cluster labels
            geom_left = row_left.geometry.iloc[0]
            geom_right = row_right.geometry.iloc[0]

            # Applying a small buffer to clean up geometry irregularities
            buffered_geom_left = geom_left.buffer(0.0001)
            buffered_geom_right = geom_right.buffer(0.0001)

            intersection = buffered_geom_left.intersection(buffered_geom_right)

            if not intersection.is_empty and isinstance(intersection, Polygon):
                # Decide which cluster gets the overlap area based on the total heat demand
                if row_left['gesamtwaermebedarf'].iloc[0] > row_right['gesamtwaermebedarf'].iloc[0]:
                    # Add the intersection area to the left polygon
                    quarters.loc[row_left.index, 'geometry'] = buffered_geom_left.union(intersection).buffer(-0.0001)
                    # Remove the intersection area from the right polygon
                    quarters.loc[row_right.index, 'geometry'] = buffered_geom_right.difference(intersection).buffer(-0.0001)
                else:
                    # Add the intersection area to the right polygon
                    quarters.loc[row_right.index, 'geometry'] = buffered_geom_right.union(intersection).buffer(-0.0001)
                    # Remove the intersection area from the left polygon
                    quarters.loc[row_left.index, 'geometry'] = buffered_geom_left.difference(intersection).buffer(-0.0001)

    return quarters