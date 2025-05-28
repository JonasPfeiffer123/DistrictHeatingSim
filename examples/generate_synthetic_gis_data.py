import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import random
import matplotlib.pyplot as plt
import networkx as nx
from scipy.spatial import distance_matrix

def generate_mst_street_network(xmin, ymin, xmax, ymax, n_support_points=20, seed=None):
    """
    Erzeugt ein Straßennetz als MST zwischen zufälligen Stützpunkten.
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    # Stützpunkte erzeugen
    xs = np.random.uniform(xmin, xmax, n_support_points)
    ys = np.random.uniform(ymin, ymax, n_support_points)
    points = np.column_stack((xs, ys))
    # Distanzmatrix
    dist_mat = distance_matrix(points, points)
    # Graph aufbauen
    G = nx.Graph()
    for i, (x, y) in enumerate(points):
        G.add_node(i, pos=(x, y))
    for i in range(n_support_points):
        for j in range(i+1, n_support_points):
            G.add_edge(i, j, weight=dist_mat[i, j])
    # MST berechnen
    mst = nx.minimum_spanning_tree(G)
    # Kanten als LineStrings
    lines = []
    for u, v in mst.edges():
        x0, y0 = G.nodes[u]['pos']
        x1, y1 = G.nodes[v]['pos']
        lines.append(LineString([(x0, y0), (x1, y1)]))
    return gpd.GeoDataFrame(geometry=lines, crs="EPSG:25833")

def generate_random_buildings(xmin, ymin, xmax, ymax, n_buildings=50, seed=None):
    """
    Erzeugt zufällige Gebäude als GeoDataFrame und DataFrame mit UTM_X/UTM_Y.
    """
    if seed is not None:
        np.random.seed(seed)
    xs = np.random.uniform(xmin, xmax, n_buildings)
    ys = np.random.uniform(ymin, ymax, n_buildings)
    points = [Point(x, y) for x, y in zip(xs, ys)]
    gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:25833")
    df = pd.DataFrame({'Land': None,
                    'Bundesland': None,
                    'Stadt': None,
                    'Adresse': None,
                    'Wärmebedarf': None,
                    'Gebäudetyp': None,
                    'Subtyp': None,
                    'WW_Anteil': None,
                    'Typ_Heizflächen': None,
                    'VLT_max': None,
                    'Steigung_Heizkurve': None,
                    'RLT_max': None,
                    'Normaußentemperatur': None,
                    'UTM_X': xs,
                    'UTM_Y': ys}
    )
        
    return gdf, df

def generate_synthetic_benchmark_data(km_size=1, n_buildings=50, n_support_points=20, seed=None):
    """
    Erzeugt ein synthetisches Kataster mit MST-basiertem Straßennetz und Gebäuden.
    """
    #497820.6,5665874.8, 497910.1,5667508.7, 499651.4,5665903.5, 499690.9,5667469.3
    xmin, ymin = 497820, 5665874
    xmax, ymax = xmin + km_size * 1000, ymin + km_size * 1000
    streets = generate_mst_street_network(xmin, ymin, xmax, ymax, n_support_points, seed)
    buildings_gdf, buildings_df = generate_random_buildings(xmin, ymin, xmax, ymax, n_buildings, seed)
    return streets, buildings_gdf, buildings_df

# Beispiel-Aufruf:
if __name__ == "__main__":
    km_size = 1.5
    n_support_points = 100
    seeds = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]  # Optional: verschiedene Seeds für Varianz

    for n_buildings in [25, 50, 75, 100, 150, 200, 250, 300]:
        # Optional: für jede Gebäudeanzahl einen eigenen Seed verwenden
        seed = 42 + n_buildings
        streets, buildings_gdf, buildings_df = generate_synthetic_benchmark_data(
            km_size=km_size,
            n_buildings=n_buildings,
            n_support_points=n_support_points,
            seed=seed
        )
        out_dir = f"examples\\data\\synthetic_gis_data\\{n_buildings}_buildings"
        import os
        os.makedirs(out_dir, exist_ok=True)
        streets.to_file(f"{out_dir}\\synthetic_streets.geojson", driver="GeoJSON")
        buildings_gdf.to_file(f"{out_dir}\\synthetic_buildings.geojson", driver="GeoJSON")
        buildings_df.to_csv(f"{out_dir}\\synthetic_buildings.csv", sep=";", index=False)
        print(f"{n_buildings} Gebäude: Daten gespeichert in {out_dir}")

    print("Alle synthetischen GIS-Datensätze erfolgreich generiert.")

    # Optional: Plot für die letzte Variante
    fig, ax = plt.subplots(figsize=(10, 10))
    streets.plot(ax=ax, color='blue', linewidth=1, label='Streets')
    buildings_gdf.plot(ax=ax, color='red', markersize=5, label='Buildings')
    ax.set_title(f"Synthetisches Straßennetz (MST) und Gebäude ({n_buildings} Gebäude)")
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.legend()
    plt.show()