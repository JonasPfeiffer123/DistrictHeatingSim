# heating_network_generation

This project is being developed by Dipl.-Ing. (FH) Jonas Pfeiffer as part of the work being done for the SMWK-NEUES TG-70 project "Entwicklung und Erprobung von Methoden und Werkzeugen zur Konzeptionierung nachhaltiger Wärmenetze" (Development and testing of methods and tools for designing sustainable heating networks) at Hochschule Zittau/Görlitz.

This project focuses on generating and analyzing heating networks using geospatial data. It integrates geographic information system (GIS) functionality with network analysis to model and simulate heating networks.

# Usage

geocoding
- for the geocoding python files the libraries "Nominatim" and "Transformer" are needed

Net generation in QGIS
- To run this project, a QGIS installation is needed. This project was created in QGIS 3.34.0. 
- When opening the QGIS-file, the output of "net_generation_functions.py" and "net_generation_qgis_ETRS89_MST.py" will be already there as the output-files were already created and imported
- Alternatively you can open a new QGIS file. In this case, some things still have to be done manually. First of, change the crs (coordinate reference system) to EPSG:25833 (for the given data). 
- Install the QuickOSM plugin. 
- Import a street-layer with QuickOSM. For this project, I imported the key "highway" with the values "primary", "secondary", "tertiary" and "residential" in "Zittau". 
- Run the python file "net_generation_qgis_ETRS89_MST.py" in QGIS. 
Note: "net_generation_qgis_ETRS89_MST.py" calls functions from "net_generation_qgis_functions.py".

Net simulation with pandapipes
- To run the python file "net_simulation.py" the "pandapipes" and "geopanda" libraries are needed.
- "net_simulation.py" calls functions from "net_simulation_pandapipes.py" and "net_generation_test.py".
- "net_simulation.py" creates a pandapipes net from gis-data. Alternatively, "net_generation_test.py" can be used to create a test net with the same functionality to test future algorithms.

# Data
For the developement and testing of the algorithms and functions, geodata is required. In this case a few local adresses in Zittau were choosed and geocoded. Also some synthetic datapoints were added. This dataset is saved as the csv-file "Beispieldaten_ETRS89.csv". The district heating network will be generated for these datapoints.

# Scripts
# net_generation_qgis_functions.py

- Purpose: Provides utility functions for network generation within the GIS framework.
- Key Functions:
  - import_osm_layer(): Imports OpenStreetMap layer into the project.
  - import_street_layer(area, values): Imports street layer data based on specified area and criteria.
  - create_data_layer(text_file_path): Creates a data layer from a text file containing coordinates.
  - create_point_layer(x_coord, y_coord): Generates a point layer from given coordinates.
  - create_layer(layer_name, layer_type, crs_i): Generic function to create a new layer with specified parameters.
  - create_offset_points(point, distance, angle_degrees): Creates offset points based on a given point, distance, and angle.
  - generate_lines(layer, distance, angle_degrees, provider): Generates lines based on given parameters.
  - find_nearest_point(current_point, other_points): Finds the nearest point to a given point from a set of points.
  - find_nearest_line(point_geom, line_layer): Identifies the nearest line to a given point geometry.
  - create_perpendicular_line(point_geom, line_geom, provider): Creates a perpendicular line from a point to a line geometry.
  - process_layer_points(layer, provider, layer_lines): Processes points in a layer and finds corresponding street end points.
  - generate_return_lines(layer, distance, angle_degrees, provider, layer_lines): Generates return lines for a layer.
  - generate_mst(all_end_points, provider): Generates a Minimum Spanning Tree (MST) from a set of end points.
  - generate_network_fl(layer_points_fl, layer_wea, provider, layer_lines): Generates a network for forward lines.
  - generate_network_rl(layer_points_rl, layer_wea, fixed_distance_rl, fixed_angle_rl, provider, layer_lines): Generates a network for return lines.

# net_generation_qgis_ETRS89_MST.py

- Purpose: Automates the process of generating heating network components and exporting them as GeoJSON files using QGIS functionalities.
- Key Processes:
  - Imports and uses functions from net_generation_functions.py.
  - Creates data layers from provided CSV file paths and specified coordinates.
  - Prepares the environment by setting up necessary layers like 'Beispieldaten_ETRS89', 'Straßen', and 'Erzeugerstandorte'.
  - Generates heat exchanger and heat generator coordinates.
  - Creates forward and return line networks.
  - Commits changes to all layers and updates their extents.
  - Writes layers as GeoJSON files and applies color coding for visual differentiation.

# net_simulation_pandapipes.py

- Purpose: Simulates the heating network using the pandapipes framework, focusing on pipe flow and network optimization.
- Key Functions:
  - get_line_coords_and_lengths(gdf): Extracts coordinates and calculates lengths of lines from a GeoDataFrame.
  - create_network(gdf_vorlauf, gdf_rl, gdf_hast, gdf_wea): Creates the entire network with junctions, pipes, heat exchangers, and circulation pumps.
  - correct_flow_directions(net): Adjusts the flow directions in the network to ensure correctness.
  - optimize_diameter_parameters(initial_net, v_max, v_min, dx): Optimizes pipe diameters based on velocity constraints.
  - optimize_diameter_types(initial_net, v_max, v_min): Alters pipe types to optimize for velocity constraints.
  - export_net_geojson(net): Export the network data to a GeoJSON format.

# net_simulation_test.py

- simple heating network to test algorithms

# net_simulation.py

- Purpose: Coordinates the simulation of the heating network using the pandapipes framework, integrating network creation, flow correction, and optimization.
- Key Processes:
  - Reads GeoJSON files to create GeoDataFrames for different network components.
  - Calls create_network from net_simulation_pandapipes to build the network.
  - Utilizes correct_flow_directions and optimize_diameter_parameters from net_simulation_pandapipes for network adjustment and optimization.
  - Visualizes the network using pandapipes plotting utilities.

# To Do

- Some parts of the code are still in german, will be fixed soon
- Optimization and generalization
  
- In "net_generation_qgis_functions.py" a function named "import_street_layer(area, values)" is defined, but not used in "net_generation_qgis_ETRS89_MST.py" yet. This function is supposed to do the import of the street layer from the QuickOSM plugin. A working code for importing the necessary data still has to be figured out.
- A function needs to be defined to set the right crs (coordinate reference system) in QGIS when executing "net_generation_qgis_ETRS89_MST.py"
- A logic has to be programmed, which overwrites existing layers when executing the python file multiple times.

- The geoJSON format is used as it can be used in advanced simulation software like SIM-VICUS (https://www.sim-vicus.de)

- Currently the combination with further python-based simulation tools like flixOpt (https://github.com/flixOpt/flixOpt) or EnSySim (https://github.com/HSZittauGoerlitz/EnSySim) is being evaluated.
  
# Contributing

Contributions to the project are welcome. Please adhere to standard coding practices and submit pull requests for review.

# License



# Contact

For collaboration or queries, contact JonasPfeiffer123's GitHub profile or feel free to contact me over LinkedIn.
