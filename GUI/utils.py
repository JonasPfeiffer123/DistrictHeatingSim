# utils.py
import os
import geopandas as gpd
import folium
import random
from PyQt5.QtCore import QUrl

def load_geojson_data(filename):
    """ Lädt GeoJSON-Daten und gibt ein Geopandas DataFrame zurück """
    return gpd.read_file(filename)

def add_geojson_to_map(m, filename):
    """ Fügt GeoJSON-Daten zu einer Folium-Karte hinzu """
    gdf = load_geojson_data(filename)
    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    folium.GeoJson(
        gdf,
        name=os.path.basename(filename),
        style_function=lambda feature: {
            'fillColor': color,
            'color': color,
            'weight': 1.5,
            'fillOpacity': 0.5,
        }
    ).add_to(m)

def update_map_view(mapView, map_obj):
    """ Aktualisiert die Kartenansicht in PyQt """
    map_file = 'map.html'
    map_obj.save(map_file)
    mapView.load(QUrl.fromLocalFile(os.path.abspath(map_file)))