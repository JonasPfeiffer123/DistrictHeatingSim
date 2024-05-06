# Erstellt von Jonas Pfeiffer

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from geocoding.geocodingETRS89 import process_data
from net_generation.import_and_create_layers import generate_and_export_layers

### this is an example on how to use the net generation features ###
### Project-specific inputs ###

# geojson with OSM street data needed
osm_street_layer_geojson_file_name = "project_data\Bad Muskau\Straßen.geojson"
    
# data points csv file path
#data_csv_input_file_name = "tests\data\data_input.csv"
data_csv_output_file_name = "project_data\Bad Muskau\data_output_ETRS89.csv"

#process_data(data_csv_input_file_name, data_csv_output_file_name)
#print("Geocoding complete.")
    
# coordinates for the heat supply
x_coord = 480198.58  # Longitude
y_coord = 5711044.00  # Latitude

coordinates = (480198.58, 5711044.00)


generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_output_file_name, coordinates, "project_data\Bad Muskau")
print("Wärmenetz-Layer erfolgreich erstellt.")