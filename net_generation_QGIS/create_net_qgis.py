from net_generation_qgis_ETRS89_MST import load_layers, generate_and_export_layers

# Ausgabedateiname für GeoJSON-Datei
osm_street_layer_geojson_file = "C:/Users/username/heating_network_generation/net_generation_QGIS/Beispiel Projekt/Straßen.geojson"

# data points csv file path
#data_csv_file_name = "data_output_ETRS89.csv"
data_csv_file_name = "data_output_gr_ETRS89.csv"

# Koordinaten für den Erzeugerstandort
#x_coord = 486267.306999999971595  # Longitude
#y_coord = 5637294.910000000149012  # Latitude
x_coord = 499827.91  # Longitude
y_coord = 5666288.22  # Latitude

layer_points, layer_lines, layer_WEA = load_layers(osm_street_layer_geojson_file, data_csv_file_name, x_coord, y_coord)
generate_and_export_layers(layer_points, layer_lines, layer_WEA)