# heating_network_generation

This project focuses on generating and analyzing heating networks using geospatial data. It integrates geographic information system (GIS) functionality with network analysis to model and simulate heating networks.

# Usage

Net generation in QGIS

To run this, a QGIS installation is needed. This project was created in QGIS 3.34.0. When opening the QGIS-file with all files in one folder, the output of "net_generation_functions.py" and "net_generation_qgis_ETRS89_MST.py" will be already there.
Alternatively you can open a new QGIS file. In this case, some things still have to be done manually. First of, change the crs (coordinate reference system) to EPSG:25833. Install the QuickOSM plugin. Import a street-layer with QuickOSM. For this project, I downloaded the key "highway" with the values "primary", "secondary", "tertiary" and "residential in Zittau. After that, the python file "net_generation_qgis_ETRS89_MST.py" can be run. "net_generation_qgis_ETRS89_MST.py" calls functions from "net_generation_functions.py". Note, that due to system specific file paths, some of them might have to be changed.

Net calculation and optimization

To run the python file "net_simulation.py" the pandapipes and geopanda libraries are needed. "net_simulation.py" calls functions from "net_simulation_pandapipes.py"


# Scripts
# net_generation_functions.py

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
        - export_net_geojson(net): Placeholder for a function to export the network data to a GeoJSON format.

# net_simulation.py

    - Purpose: Coordinates the simulation of the heating network using the pandapipes framework, integrating network creation, flow correction, and optimization.
    - Key Processes:
        - Reads GeoJSON files to create GeoDataFrames for different network components.
        - Calls create_network from net_simulation_pandapipes to build the network.
        - Utilizes correct_flow_directions and optimize_diameter_parameters from net_simulation_pandapipes for network adjustment and optimization.
        - Visualizes the network using pandapipes plotting utilities.
        - Exports the simulated network data to GeoJSON format using a function from net_simulation_pandapipes.

# Contributing

Contributions to the project are welcome. Please adhere to standard coding practices and submit pull requests for review.

# License

This project is licensed under the GPL-3.0 license.

# Contact

For collaboration or queries, contact JonasPfeiffer123's GitHub profile.
