"""
Filename: simple_net_generation_test.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Script for testing the net generation functionality.

"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import geopandas as gpd
import matplotlib.pyplot as plt

from src.districtheatingsim.geocoding.geocodingETRS89 import process_data
from src.districtheatingsim.net_generation.import_and_create_layers import generate_and_export_layers

### this is an example on how to use the net generation features ###
### Project-specific inputs ###

# geojson with OSM street data needed
#osm_street_layer_geojson_file_name = "C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau\Raumanalyse\Straßen.geojson"
osm_street_layer_geojson_file_name = "H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Projektdateien_DistrictHeatSim\Görlitz Stadthalle und HS\Raumanalyse\Straßen.geojson"
#osm_street_layer_geojson_file_name = "H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Python\Zittau\Raumanalyse\Straßen.geojson"   

# data points csv file path
#data_csv_input_file_name = "tests\data\data_input.csv"
#data_csv_output_file_name = "C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau\Gebäudedaten\data_output_ETRS89.csv"
#data_csv_output_file_name = "C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau\Gebäudedaten\data_output_LOD2.csv"
data_csv_output_file_name = "H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Projektdateien_DistrictHeatSim\Görlitz Stadthalle und HS/Gebäudedaten/data_output_ETRS89.csv"
#data_csv_output_file_name = "H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Python/Zittau/Gebäudedaten/data_output_ETRS89.csv"

#process_data(data_csv_input_file_name, data_csv_output_file_name)
#print("Geocoding complete.")
    
#coordinates = [(480198.58, 5711044.00)]
coordinates = [(499818.1361370679,5666172.053389446)]
#coordinates = [(486268.03,5637295.12)]

#mode = "A*-Star"
#mode = "MST"
#mode = "pre_MST"
mode = "Advanced MST"

#generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_output_file_name, coordinates, "C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau", algorithm=mode)
generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_output_file_name, coordinates, "H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Projektdateien_DistrictHeatSim\Görlitz Stadthalle und HS", algorithm=mode)
#generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_output_file_name, coordinates, "H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Python\Zittau", algorithm=mode)
print("Wärmenetz-Layer erfolgreich erstellt.")

#hast = gpd.read_file("C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau\Wärmenetz\HAST.geojson", driver="GeoJSON")
#rücklauf = gpd.read_file("C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau\Wärmenetz\Rücklauf.geojson", driver="GeoJSON")
#vorlauf = gpd.read_file("C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau\Wärmenetz\Vorlauf.geojson", driver="GeoJSON")
#erzeuger = gpd.read_file("C:/Users/jp66tyda\DistrictHeatSim\districtheatsim\project_data\Bad Muskau\Wärmenetz\Erzeugeranlagen.geojson", driver="GeoJSON")

hast = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Projektdateien_DistrictHeatSim\Görlitz Stadthalle und HS\Wärmenetz\HAST.geojson", driver="GeoJSON")
rücklauf = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Projektdateien_DistrictHeatSim\Görlitz Stadthalle und HS\Wärmenetz\Rücklauf.geojson", driver="GeoJSON")
vorlauf = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Projektdateien_DistrictHeatSim\Görlitz Stadthalle und HS\Wärmenetz\Vorlauf.geojson", driver="GeoJSON")
erzeuger = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Projektdateien_DistrictHeatSim\Görlitz Stadthalle und HS\Wärmenetz\Erzeugeranlagen.geojson", driver="GeoJSON")

#hast = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Python\Zittau\Wärmenetz\HAST.geojson", driver="GeoJSON")
#rücklauf = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Python\Zittau\Wärmenetz\Rücklauf.geojson", driver="GeoJSON")
#vorlauf = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Python\Zittau\Wärmenetz\Vorlauf.geojson", driver="GeoJSON")
#erzeuger = gpd.read_file("H:/Arbeit/01_SMWK-NEUES Bearbeitung/02_Python\Zittau\Wärmenetz\Erzeugeranlagen.geojson", driver="GeoJSON")

# Plotten der geographischen Daten
fig, ax = plt.subplots(figsize=(10, 10))  # Größe des Plots anpassen
#hast.plot(ax=ax, color='green')  # Farbe und weitere Parameter anpassen
#rücklauf.plot(ax=ax, color='blue')  # Farbe und weitere Parameter anpassen
vorlauf.plot(ax=ax, color='red')  # Farbe und weitere Parameter anpassen
#erzeuger.plot(ax=ax, color='black')  # Farbe und weitere Parameter anpassen
plt.title('Wärmenetz')
plt.show()