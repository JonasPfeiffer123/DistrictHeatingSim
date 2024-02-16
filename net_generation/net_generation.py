from import_and_create_layers import generate_and_export_layers

### this is an example on how to use the net generation features
### Project-specific inputs ###
# two example projects implemented
projekt = "Zittau"
#projekt = "Görlitz"

if projekt == "Zittau":
    # geojson with OSM street data needed
    osm_street_layer_geojson_file_name = "/osm_data/Straßen Zittau.geojson"
    
    # data points csv file path
    data_csv_file_name = "/geocoding/data_output_zi_ETRS89.csv"
    
    # coordinates for the heat supply
    x_coord = 486267.306999999971595  # Longitude
    y_coord = 5637294.910000000149012  # Latitude

if projekt == "Görlitz":
    # geojson with OSM street data needed
    #osm_street_layer_geojson_file_name = "/osm_data/Straßen Görlitz.geojson"
    
    # data points csv file path
    data_csv_file_name = "/geocoding/data_output_gr_ETRS89.csv"
    
    # coordinates for the heat supply
    x_coord = 499827.91  # Longitude
    y_coord = 5666288.22  # Latitude

generate_and_export_layers(osm_street_layer_geojson_file_name, data_csv_file_name, x_coord, y_coord)