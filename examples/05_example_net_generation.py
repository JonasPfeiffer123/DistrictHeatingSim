"""
Filename: 05_example_net_generation_test.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Script for testing the net generation functions.
Usage: Run the script to generate a heat network based on the given inputs.
Functions:
    generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_file_name, coordinates, base_path, algorithm) -> None
        Generates and exports the heat network layers based on the given inputs.
Example:
    $ python 05_example_net_generation_test.py
"""

import geopandas as gpd
import matplotlib.pyplot as plt

from districtheatingsim.geocoding.geocodingETRS89 import get_coordinates
from districtheatingsim.net_generation.import_and_create_layers import generate_and_export_layers

### this is an example on how to use the net generation features ###
### Project-specific inputs ###

# Data csv file can be created with the 01_example_geocoding.py script
# therefore the data_csv_input_file_name is the output of the geocoding script
data_csv_file_name = "examples\data\data_ETRS89.csv"

# Street data is imported with the 02_example_import_osm_data_geojson.py script
# therefore the osm_street_layer_geojson_file_name is the output of the osm import script
#osm_street_layer_geojson_file_name = "examples\data\osm_street_data.geojson"
# "examples\data\streets.geojson" is a reduced version of the original data, faster loading
osm_street_layer_geojson_file_name = "examples\data\streets.geojson"

# Coordinates for the heat source is needed to generate the heat network
# The coordinates can be obtained from the geocoding script with an address input

"""
try:
    address = "Brückenstraße 10"
    city = "Görlitz"
    state = "Sachsen"
    country = "Deutschland"
    coordinates = [get_coordinates(f"{address}, {city}, {state}, {country}")]
    print(f"Coordinates: {coordinates}")
except Exception as e:
    print(f"Error getting coordinates: {e}")
    coordinates = [(499829.047722075, 5666164.624415245)]
    print(f"Using default coordinates: {coordinates}")
"""
coordinates = [(499829.047722075, 5666164.624415245)]
print(f"Using default coordinates: {coordinates}")

# Choose the algorithm to generate the network
# mode = "MST"
mode = "Advanced MST"
# mode = "Steiner" 

base_path = "examples\data\Wärmenetz\Variante 1"
print(f"Starte die Generierung des Wärmenetzes in {base_path} mit dem Algorithmus {mode}...")

generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_file_name, coordinates, base_path, algorithm=mode)
print("Wärmenetz-Layer erfolgreich erstellt.")

hast = gpd.read_file(f"{base_path}\Wärmenetz\HAST.geojson", driver="GeoJSON")
rücklauf = gpd.read_file(f"{base_path}\Wärmenetz\Rücklauf.geojson", driver="GeoJSON")
vorlauf = gpd.read_file(f"{base_path}\Wärmenetz\Vorlauf.geojson", driver="GeoJSON")
erzeuger = gpd.read_file(f"{base_path}\Wärmenetz\Erzeugeranlagen.geojson", driver="GeoJSON")

print("Layer erfolgreich geladen.")

# Plotten der geographischen Daten
fig, ax = plt.subplots(figsize=(10, 10))  # Größe des Plots anpassen
hast.plot(ax=ax, color='green')  # Farbe und weitere Parameter anpassen
rücklauf.plot(ax=ax, color='blue')  # Farbe und weitere Parameter anpassen
vorlauf.plot(ax=ax, color='red')  # Farbe und weitere Parameter anpassen
erzeuger.plot(ax=ax, color='black')  # Farbe und weitere Parameter anpassen
plt.title('Wärmenetz')
plt.show()