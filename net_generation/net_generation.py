from import_and_create_layers import generate_and_export_layers

### Projektspezifische Eingaben ###
projekt = "Zittau"
#projekt = "Görlitz"

if projekt == "Zittau":
    osm_street_layer_geojson_file_name = "C:/Users/username/heating_network_generation/net_generation_QGIS/Straßen Zittau.geojson"
    
    # data points csv file path
    data_csv_file_name = "C:/Users/username/heating_network_generation/geocoding/data_output_zi_ETRS89.csv"
    
    x_coord = 486267.306999999971595  # Longitude
    y_coord = 5637294.910000000149012  # Latitude

if projekt == "Görlitz":
    #osm_street_layer_geojson_file_name = "C:/Users/username/heating_network_generation/net_generation_QGIS/Straßen Görlitz.geojson"
    
    # data points csv file path
    data_csv_file_name = "data_output_gr_ETRS89.csv"
    
    # Koordinaten für den Erzeugerstandort
    x_coord = 499827.91  # Longitude
    y_coord = 5666288.22  # Latitude

generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_file_name, x_coord, y_coord)