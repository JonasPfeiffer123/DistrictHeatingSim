import numpy as np
import pandas as pd
# Importieren der erforderlichen Bibliotheken
import geopandas as gpd
from sklearn.cluster import DBSCAN # pip install scikit-learn
import hdbscan
"""To install hdbscan: 
Besuchen Sie die Webseite für die Microsoft C++ Build Tools.

Laden Sie den Installer herunter und führen Sie ihn aus.

Wählen Sie im Installer die Option "C++ build tools" aus, stellen Sie sicher, dass die neueste Version von MSVC v142 - VS 2019 C++ x64/x86 build tools (oder höher) ausgewählt ist, sowie die Windows 10 SDK.

Schließen Sie die Installation ab und starten Sie Ihren Computer neu, wenn dazu aufgefordert wird.

Versuchen Sie nach dem Neustart die Installation von hdbscan erneut mit dem Befehl, den Sie bereits verwendet haben:

pip install hdbscan"""

from shapely.geometry import Polygon, shape
from shapely.ops import unary_union
from geopandas.tools import overlay
import matplotlib.pyplot as plt

# Schwellwerte für die Entscheidung über die Versorgungsmethode festlegen
# Gebäude mit einem Wärmebedarf über dem Wärmenetz-Schwellwert erhalten eine Wärmenetzversorgung,
# Gebäude über dem Wasserstoff-Schwellwert erhalten eine Wasserstoffversorgung,
# alle anderen erhalten eine Einzelversorgungslösung.

def versorgungsgebiet_bestimmen(flaechenspezifischer_waermebedarf, schwellwert_waermenetz, schwellwert_wasserstoff):
    if flaechenspezifischer_waermebedarf > schwellwert_waermenetz:
        return 'Wärmenetzversorgung'
    elif flaechenspezifischer_waermebedarf > schwellwert_wasserstoff:
        return 'Wasserstoffversorgung'
    else:
        return 'Einzelversorgungslösung'

def clustering_quartiere_hdbscan(gdf, buffer_size=10, min_cluster_size=30, min_samples=1, schwellwert_waermenetz=90, schwellwert_wasserstoff=60):
    # Pufferzone um jedes Gebäude hinzufügen
    gdf['buffered_geometry'] = gdf.geometry.buffer(buffer_size)

    # Koordinaten der Gebäudezentren (unter Berücksichtigung des Puffers) für das Clustering vorbereiten
    coords = np.array(list(zip(gdf['buffered_geometry'].centroid.x, gdf['buffered_geometry'].centroid.y)))

    # HDBSCAN-Algorithmus zum Clustern der Koordinaten anwenden
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples, gen_min_span_tree=True)
    cluster_labels = clusterer.fit_predict(coords)

    # Hinzufügen der Cluster-Labels zum GeoDataFrame
    gdf['quartier_label'] = cluster_labels

    # Entfernen von Rauschen, das als '-1' gekennzeichnet ist
    gdf = gdf[gdf['quartier_label'] != -1]

    # Gruppieren der Gebäude in Cluster und Erstellen von Polygonen für jedes Cluster
    # Verwenden Sie eine angepasste Aggregationsfunktion für die Geometriedaten
    for index, row in gdf.iterrows():
        geom = shape(row['geometry'])
        if not geom.is_valid:
            # Wenn die Geometrie ungültig ist, können Sie sie reparieren oder entfernen
            # Hier verwenden wir `buffer(0)` zur Fehlerbehebung, um ungültige Geometrien zu entfernen
            gdf.at[index, 'geometry'] = geom.buffer(0)
    quartiere = gdf.dissolve(by='quartier_label', aggfunc={'buffered_geometry': lambda x: x.unary_union.convex_hull})

    # Definieren der Quartiersgrenzen mit konvexen Hüllen
    quartiere['geometry'] = quartiere['buffered_geometry']

    # Flächenspezifischen Wärmebedarf berechnen
    quartiere['gesamtwaermebedarf'] = gdf.groupby('quartier_label')['Jahreswärmebedarf [kWh/a]'].sum()
    quartiere['flaeche'] = quartiere.geometry.area
    quartiere['flaechenspezifischer_waermebedarf'] = quartiere['gesamtwaermebedarf'] / quartiere['flaeche']

    # Versorgungsgebiet auf Basis des flächenspezifischen Wärmebedarfs zuweisen
    quartiere['Versorgungsgebiet'] = quartiere.apply(lambda row: versorgungsgebiet_bestimmen(row['flaechenspezifischer_waermebedarf'], schwellwert_waermenetz, schwellwert_wasserstoff), axis=1)

    # Löschen aller unnötigen Spalten, behalten nur die relevanten
    quartiere = quartiere[['geometry', 'gesamtwaermebedarf', 'flaeche', 'flaechenspezifischer_waermebedarf', 'Versorgungsgebiet']]
    quartiere = quartiere.reset_index()

    return quartiere

def postprocessing_hdbscan(quartiere):
    # Laden Sie die ursprünglichen Cluster-Daten
    quartiere['geometry'] = quartiere['geometry'].buffer(0)  # Dies kann helfen, einige Geometrieprobleme zu beheben

    # Flag, um den Fortschritt der Überschneidungsauflösung zu verfolgen
    overlapping_exists = True
    while overlapping_exists:
        # Erstellen Sie eine Kopie für das Postprocessing
        quartiere_postprocessed = quartiere.copy()
        quartiere_postprocessed = quartiere_postprocessed.drop_duplicates(subset=['quartier_label'])
        quartiere_postprocessed = quartiere_postprocessed.dropna(subset=['Versorgungsgebiet'])
        
        # Führen Sie einen spatial join durch, um benachbarte Polygone zu identifizieren
        joined = gpd.sjoin(quartiere_postprocessed, quartiere_postprocessed, how='left', predicate='intersects')
        # Filtern Sie die Ergebnisse, um nur Paare mit derselben Versorgungsart zu behalten
        same_supply_type = joined[joined['Versorgungsgebiet_left'] == joined['Versorgungsgebiet_right']]

        overlapping_exists = False

        # Vereinigen Sie die Polygone, die die gleiche Versorgungsart haben und einander berühren
        for index, row in same_supply_type.iterrows():
            index_left = row['quartier_label_left']
            index_right = row['quartier_label_right']

            if index_left != index_right:
                left_geoms = quartiere_postprocessed[quartiere_postprocessed['quartier_label'] == index_left]['geometry']
                right_geoms = quartiere_postprocessed[quartiere_postprocessed['quartier_label'] == index_right]['geometry']

                if not left_geoms.is_empty.all() and not right_geoms.is_empty.all():
                    current_geometry = left_geoms.unary_union
                    touching_geometry = right_geoms.unary_union

                    if current_geometry is not None and touching_geometry is not None:
                        unified_geometry = current_geometry.union(touching_geometry)
                        
                        # Aktualisiere die Geometrie für jede Zeile einzeln
                        for idx in quartiere_postprocessed[quartiere_postprocessed['quartier_label'] == index_left].index:
                            quartiere_postprocessed.at[idx, 'geometry'] = unified_geometry
                        
                        # Lösche das zweite Polygon
                        quartiere_postprocessed = quartiere_postprocessed[quartiere_postprocessed['quartier_label'] != index_right]
                        overlapping_exists = True

        quartiere = quartiere_postprocessed

    # Reset Index außerhalb der Schleife
    quartiere_postprocessed.reset_index(drop=True, inplace=True)

    return quartiere_postprocessed

def allocate_overlapping_area(quartiere):
    # Spatial Join für sich überschneidende Polygone
    overlapping = gpd.sjoin(quartiere, quartiere, how='inner', predicate='intersects')

    # Filtere nur Paare mit unterschiedlichen Versorgungsarten
    different_supply = overlapping[overlapping['Versorgungsgebiet_left'] != overlapping['Versorgungsgebiet_right']]

    for idx, row in different_supply.iterrows():
        idx_left = row['quartier_label_left']
        idx_right = row['quartier_label_right']

        # Finde die Zeilen, die den gegebenen Cluster-Labels entsprechen
        row_left = quartiere[quartiere['quartier_label'] == idx_left]
        row_right = quartiere[quartiere['quartier_label'] == idx_right]

        if not row_left.empty and not row_right.empty:
            # Finden Sie die zugehörigen Geometrien basierend auf den Cluster-Labels
            geom_left = row_left.geometry.iloc[0]
            geom_right = row_right.geometry.iloc[0]

            # Anwenden eines kleinen Buffers zur Bereinigung von Geometrieunregelmäßigkeiten
            buffered_geom_left = geom_left.buffer(0.0001)
            buffered_geom_right = geom_right.buffer(0.0001)

            intersection = buffered_geom_left.intersection(buffered_geom_right)

            if not intersection.is_empty and isinstance(intersection, Polygon):
                # Entscheide, welcher Cluster die Überschneidungsfläche erhält, basierend auf dem gesamten Wärmebedarf
                if row_left['gesamtwaermebedarf'].iloc[0] > row_right['gesamtwaermebedarf'].iloc[0]:
                    # Füge die Überschneidungsfläche zum linken Polygon hinzu
                    quartiere.loc[row_left.index, 'geometry'] = buffered_geom_left.union(intersection).buffer(-0.0001)
                    # Entferne die Überschneidungsfläche vom rechten Polygon
                    quartiere.loc[row_right.index, 'geometry'] = buffered_geom_right.difference(intersection).buffer(-0.0001)
                else:
                    # Füge die Überschneidungsfläche zum rechten Polygon hinzu
                    quartiere.loc[row_right.index, 'geometry'] = buffered_geom_right.union(intersection).buffer(-0.0001)
                    # Entferne die Überschneidungsfläche vom linken Polygon
                    quartiere.loc[row_left.index, 'geometry'] = buffered_geom_left.difference(intersection).buffer(-0.0001)

    return quartiere

### Ausführen ###

def run_here():
    # Laden Sie Ihren GeoJSON-Datensatz
    gdf = gpd.read_file('osm_data/output_buildings.geojson', driver='GeoJSON').to_crs(epsg=25833)

    def calculate_building_data(gdf, output_filename):
            # Berechnen der Fläche jedes Gebäudes in Quadratmetern
            gdf['area_sqm'] = gdf['geometry'].area
            # Hinzufügen der Spalte für spezifischen Wärmebedarf mit Zufallszahlen zwischen 50 und 200
            gdf['spez. Wärmebedarf [kWh/m²*a]'] = np.random.uniform(50, 200, gdf.shape[0])
            # Hinzufügen der Spalte für die Anzahl der Geschosse (konstanter Wert 3)
            gdf['Anzahl Geschosse'] = 3
            # Berechnen des Jahreswärmebedarfs
            gdf['Jahreswärmebedarf [kWh/a]'] = gdf['spez. Wärmebedarf [kWh/m²*a]'] * gdf['Anzahl Geschosse'] * gdf['area_sqm']
            # Speichern des erweiterten GeoDataFrame in eine neue GeoJSON-Datei
            gdf.to_file(output_filename, driver='GeoJSON')

            return gdf

    gdf = calculate_building_data(gdf, 'osm_data/output_buildings.geojson')

    quartiere = clustering_quartiere_hdbscan(gdf)
    #Ergebnis als GeoJSON-Datei exportieren
    quartiere.to_file('C:/Users/username/heating_network_generation/osm_data/quartiere_hdbscan.geojson', driver='GeoJSON')

    # Laden der GeoJSON-Daten
    #quartiere = gpd.read_file('C:/Users/username/heating_network_generation/osm_data/quartiere_hdbscan.geojson', driver='GeoJSON')

    # Füge Quartiere gleicher Versorgungsart zusammen
    quartiere_joined = postprocessing_hdbscan(quartiere)
    # Speichern der postprozessierten Daten
    quartiere_joined.to_file('quartiere_postprocessed.geojson', driver='GeoJSON')

    # allocate_overlapping_area-Ansatz anwenden
    quartiere_overlayed = allocate_overlapping_area(quartiere_joined)
    quartiere_overlayed.to_file('C:/Users/username/heating_network_generation/osm_data/quartiere_allocated.geojson', driver='GeoJSON')

#run_here()