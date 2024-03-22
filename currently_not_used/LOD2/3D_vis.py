import geopandas as gpd
import numpy as np
import pyvista as pv

# Shapefile laden
gdf = gpd.read_file('C:/Users/username/heating_network_generation/currently_not_used/LOD2/shape/lod2_33484_5636_2_sn_shape/lod2_33484_5636_2_sn.shp')

# Einzigartige Geometrietypen ermitteln
unique_geometry_types = gdf.geometry.type.unique()

print(unique_geometry_types)

# Funktion, um die Koordinaten aus einer Geometrie zu extrahieren
def extract_coordinates(geom):
    coords_list = []
    if geom.type == 'MultiPolygon' or geom.type == 'Polygon':
        if geom.type == 'MultiPolygon':
            for polygon in geom.geoms:
                exterior_coords = np.array(polygon.exterior.coords)
                if exterior_coords.shape[1] == 2:
                    exterior_coords = np.hstack((exterior_coords, np.zeros((exterior_coords.shape[0], 1))))
                coords_list.append(exterior_coords)
        else:
            exterior_coords = np.array(geom.exterior.coords)
            if exterior_coords.shape[1] == 2:
                exterior_coords = np.hstack((exterior_coords, np.zeros((exterior_coords.shape[0], 1))))
            coords_list.append(exterior_coords)
    elif geom.type == 'GeometryCollection':
        for geometry in geom.geoms:
            if geometry.type == 'Polygon':
                exterior_coords = np.array(geometry.exterior.coords)
                if exterior_coords.shape[1] == 2:
                    exterior_coords = np.hstack((exterior_coords, np.zeros((exterior_coords.shape[0], 1))))
                coords_list.append(exterior_coords)
            elif geometry.type == 'MultiPolygon':
                for polygon in geometry.geoms:
                    exterior_coords = np.array(polygon.exterior.coords)
                    if exterior_coords.shape[1] == 2:
                        exterior_coords = np.hstack((exterior_coords, np.zeros((exterior_coords.shape[0], 1))))
                    coords_list.append(exterior_coords)
            # Hier können Sie weitere Geometrietypen hinzufügen, z.B. 'LineString' oder 'Point'
    return coords_list

# Initialisieren eines leeren Meshes für PyVista
mesh = pv.PolyData()

# Durchlaufen aller Geometrien im GeoDataFrame
for geom in gdf.geometry:
    coords_list = extract_coordinates(geom)
    for coords in coords_list:
        if coords.size > 0:
            # Erstellen des PyVista PolyData Objekts für die aktuelle Geometrie
            poly_data = pv.PolyData(coords)
            
            # Optional: Erstellen eines Meshes für die Geometrie
            faces = np.hstack([[coords.shape[0]-1], np.arange(coords.shape[0]-1)])
            poly_data.faces = faces
            
            # Hinzufügen der aktuellen Geometrie zum Gesamt-Mesh
            mesh += poly_data

# Überprüfung, ob das Mesh Punkte enthält
if mesh.n_points > 0:
    # Visualisierung des gesamten Meshes
    mesh.plot(show_edges=True, color=True)
else:
    print("Das Mesh enthält keine Punkte.")