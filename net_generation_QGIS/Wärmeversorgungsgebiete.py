import numpy as np
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

# Schwellwerte für die Entscheidung über die Versorgungsmethode festlegen
# Gebäude mit einem Wärmebedarf über dem Wärmenetz-Schwellwert erhalten eine Wärmenetzversorgung,
# Gebäude über dem Wasserstoff-Schwellwert erhalten eine Wasserstoffversorgung,
# alle anderen erhalten eine Einzelversorgungslösung.

schwellwert_waermenetz = 90  # kWh/m²*a Beispielwert für Wärmenetz
schwellwert_wasserstoff = 60  # kW/m²*a Beispielwert für Wasserstoff

def versorgungsgebiet_bestimmen(flaechenspezifischer_waermebedarf):
    if flaechenspezifischer_waermebedarf > schwellwert_waermenetz:
        return 'Wärmenetzversorgung'
    elif flaechenspezifischer_waermebedarf > schwellwert_wasserstoff:
        return 'Wasserstoffversorgung'
    else:
        return 'Einzelversorgungslösung'

# Funktion zum Clustern von Gebäuden
def clustering_gebäude(gdf):
    # Zuordnen eines Versorgungsgebiets basierend auf dem Jahreswärmebedarf für jedes Gebäude
    gdf['Versorgungsgebiet'] = gdf['spez. Wärmebedarf [kWh/m²*a]'].apply(versorgungsgebiet_bestimmen)

    # Koordinaten der Gebäudezentren für das Clustering vorbereiten
    coords = np.array(list(zip(gdf.geometry.centroid.x, gdf.geometry.centroid.y)))
    # DBSCAN-Algorithmus zum Clustern der Koordinaten anwenden
    db = DBSCAN(eps=50, min_samples=5).fit(coords)
    # Hinzufügen der Cluster-Labels zum GeoDataFrame
    gdf['cluster_label'] = db.labels_

    # Gruppieren der Gebäude in Cluster und Erstellen von Polygonen für jedes Cluster
    versorgungsgebiete = gdf.dissolve(by='cluster_label', as_index=False)

    # Ergebnis als GeoJSON-Datei exportieren
    versorgungsgebiete.to_file('versorgungsgebiete.geojson', driver='GeoJSON')

# Funktion zum Clustern von Gebäuden und Bilden von Quartieren mit DBSCAN
def clustering_quartiere_dbscan(gdf):
    # Koordinaten der Gebäudezentren für das Clustering vorbereiten
    coords = np.array(list(zip(gdf.centroid.x, gdf.centroid.y)))
    # DBSCAN-Algorithmus zum Clustern der Koordinaten anwenden
    db = DBSCAN(eps=38, min_samples=5).fit(coords)
    # Hinzufügen der Cluster-Labels zum GeoDataFrame
    gdf['quartier_label'] = db.labels_

    # Entfernen der Rauschpunkte, die von DBSCAN als -1 gekennzeichnet wurden
    gdf = gdf[gdf['quartier_label'] != -1]

    # Gruppieren der Gebäude in Cluster und Erstellen von Polygonen für jedes Cluster
    quartiere = gdf.dissolve(by='quartier_label')
    # Berechnen der konvexen Hüllen für jedes Quartier, um die Quartiersgrenzen zu definieren
    quartiere['geometry'] = quartiere.apply(lambda x: x.geometry.convex_hull, axis=1)

    # Flächenspezifischen Wärmebedarf berechnen
    quartiere['gesamtwaermebedarf'] = gdf.groupby('quartier_label')['Jahreswärmebedarf [kWh/a]'].sum()
    quartiere['flaeche'] = quartiere.geometry.area
    quartiere['flaechenspezifischer_waermebedarf'] = quartiere['gesamtwaermebedarf'] / quartiere['flaeche']

    # Versorgungsgebiet auf Basis des flächenspezifischen Wärmebedarfs zuweisen
    quartiere['Versorgungsgebiet'] = quartiere['flaechenspezifischer_waermebedarf'].apply(versorgungsgebiet_bestimmen)
    
    # Ergebnis als GeoJSON-Datei exportieren
    quartiere.to_file('quartiere_versorgungsgebiete.geojson', driver='GeoJSON')

def clustering_quartiere_hdbscan(gdf):
    # Koordinaten der Gebäudezentren für das Clustering vorbereiten
    coords = np.array(list(zip(gdf.geometry.centroid.x, gdf.geometry.centroid.y)))

    # HDBSCAN-Algorithmus zum Clustern der Koordinaten anwenden
    clusterer = hdbscan.HDBSCAN(min_cluster_size=30, min_samples=1, gen_min_span_tree=True)
    cluster_labels = clusterer.fit_predict(coords)

    # Hinzufügen der Cluster-Labels zum GeoDataFrame
    gdf['quartier_label'] = cluster_labels

    # Entfernen von Rauschen, das als '-1' gekennzeichnet ist
    gdf = gdf[gdf['quartier_label'] != -1]

    # Gruppieren der Gebäude in Cluster und Erstellen von Polygonen für jedes Cluster
    quartiere = gdf.dissolve(by='quartier_label')

    # Definieren der Quartiersgrenzen, z.B. mit konvexen Hüllen
    quartiere['geometry'] = quartiere.geometry.apply(lambda geom: geom.convex_hull)

    # Flächenspezifischen Wärmebedarf berechnen
    quartiere['gesamtwaermebedarf'] = gdf.groupby('quartier_label')['Jahreswärmebedarf [kWh/a]'].sum()
    quartiere['flaeche'] = quartiere.geometry.area
    quartiere['flaechenspezifischer_waermebedarf'] = quartiere['gesamtwaermebedarf'] / quartiere['flaeche']

    # Versorgungsgebiet auf Basis des flächenspezifischen Wärmebedarfs zuweisen
    quartiere['Versorgungsgebiet'] = quartiere['flaechenspezifischer_waermebedarf'].apply(versorgungsgebiet_bestimmen)
    
    # Ergebnis als GeoJSON-Datei exportieren
    quartiere.to_file('quartiere_hdbscan.geojson', driver='GeoJSON')

# Laden Sie Ihren GeoJSON-Datensatz
gdf = gpd.read_file('C:/Users/username/heating_network_generation/net_generation_QGIS/Gebäude Zittau berechnet.geojson')
#gdf = gpd.read_file('C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Beleg 2/gefilterte Gebäude Zittau Beleg 2 berechnet.geojson')

# Wählen Sie die zu verwendende Clustering-Funktion aus:
#clustering_gebäude(gdf)
#clustering_quartiere_dbscan(gdf)
clustering_quartiere_hdbscan(gdf)
