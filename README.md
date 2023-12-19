# heating_network_generation

This project, led by Dipl.-Ing. (FH) Jonas Pfeiffer for the SMWK-NEUES TG-70 project "Entwicklung und Erprobung von Methoden und Werkzeugen zur Konzeptionierung nachhaltiger Wärmenetze" (Development and testing of methods and tools for designing sustainable heating networks) at Hochschule Zittau/Görlitz, aims to develop and test tools for creating sustainable heating networks using geospatial data and GIS functionalities.

# Usage

"geocoding"-folder
- for the geocoding python files the libraries "Nominatim" and "Transformer" are needed
- There are 2 scripts which allow you to geocode given adresses
- the folder is also used for storage of example data

"net_generation_QGIS"-folder
- To run this project, a QGIS installation is needed. This project was created in QGIS 3.34.0.
- there are currently different example folders with two different synthetic "projects" created with different net generation algorithms
- When opening a QGIS-file, the output of "net_generation_qgis.py" will be already there as the output-files were already created and imported
- Alternatively you can open a new QGIS file. In this case, some things still have to be done manually. First of, change the crs (coordinate reference system) to EPSG:25833 (for the given data). 
- Optional: Install the QuickOSM plugin if you want to download specific street data. Alternatively you can use the "import_osm_street_layer_geojson.py"-file. This requires a specific osm-query.
- For this project, I imported the key "highway" with the values "primary", "secondary", "tertiary", "residential", "road" and "living_street" for the cities "Zittau" and "Görlitz", but also tested a few variations 
Note: "net_generation_qgis.py" calls functions from "import_and_create_layers_qgis.py" and from "qgis_simple_MST.py".

"net_simulation_pandapipes"
- the "pandapipes" and "geopanda" libraries are needed.
- the main file is "simulate_functions.py" in the main folder, the net generation based on the gis data in its current form can be initiated with the generate_net()-function. This functions defines the Input-geojson-files and creates the pandapipes-net
- "simulate_functions.py" calls functions from "net_simulation", "net_simulation_calculation.py", "net_generation_test.py" and "my_controllers.py".
- "simulate_functions.py" creates a pandapipes net from gis-data. Alternatively, "net_generation_test.py" can be used to create a test net with the same functionality to test future algorithms.

"heat_requirement"
- implementation of the VDI 4655 for load profile calculation (based on the available Excel-file from https://www.umwelt-campus.de/energietools)
- uses TRY-data
- call the "calculate"-function to get the timeseries-output

"heat_generators"
- I recently added a bunch of heat generator functions from a previous private project of mine, which are now being implemented in the whole calculation model
- I recently updated and restructured the code. "Photovoltaik.py" and "Wirtschaftlichkeitsbetrachtung.py" is currently not used. The functionality of "Wirtschaftlichkeitsbetrachtung.py" is already implemented in heat_generator classes.
- heat_generator_classes defines different heat generator classes and a function to calculate the heat generation mix based on a given load and predefined heat generators and an optimize-function to minimize the cost of such a system

"Example_Results"
- shows a few visual example outputs of the project

"main-folder"
- as already described, "simulate_functions.py" can be used for various calculations
- for a more user friendly experience I created the "GUI.py" which currently has the functionality to calculate the generation mix and optimize it

# Data
For the developement and testing of the algorithms and functions, geodata is required. In this case a few local adresses in Zittau were choosed and geocoded. Also some synthetic datapoints were added. This example-datasets are saved in the geocoding-folder. The district heating network will be generated for these datapoints.

# Scripts
# net_generation_qgis.py

- Purpose: Automates the process of generating heating network components and exporting them as GeoJSON files using QGIS functionalities.
- Key Processes:
  - GIS Integration: Integrates with QGIS for geospatial data processing.
  - Layer Import: Facilitates importing and creating layers in QGIS from various data sources.
  - Project Configuration: Supports different project settings based on geographic locations (e.g., Zittau, Görlitz).
  - Layer Generation: Generates network layers such as HAST (heating substations), Rücklauf (return lines), Vorlauf (supply lines), and Erzeugeranlagen (production facilities).
  - GeoJSON Export: Provides functionality to export generated network layers as GeoJSON files.
  - Layer Styling: Includes features for styling layers in QGIS for better visualization.
  - Error Handling: Implements error checking during layer loading and exporting processes.

# qgis_simple_MST.py

- Purpose: Provides utility functions for network generation within the GIS framework.
- Key Functions:
  - Nearest Line Finder: Identifies the nearest line feature to a given point in a QGIS layer.
  - Perpendicular Line Creation: Generates perpendicular lines from points to their nearest lines.
  - Layer Processing: Processes point layers to create connections to the nearest lines, forming a network.
  - Return Lines Generation: Creates return lines for a network with an offset and angle.
  - Minimum Spanning Tree (MST) Network: Utilizes NetworkX to generate a Minimum Spanning Tree, connecting all end points in the most efficient way.
  - Forward and Return Network Generation: Facilitates the creation of both forward and return line networks in a geospatial environment.

# net_simulation_calculation.py

- Purpose: Simulates the heating network using the pandapipes framework, focusing on pipe flow and network optimization.
- Key Functions:
  - Network Creation from GIS Data: Utilizes geospatial data to create detailed models of district heating networks.
  - Pipe Initialization: Supports both diameter-based and type-based pipe initialization for network modeling.
  - Heat Exchanger Integration: Automates the addition of heat exchangers into the network with specified heat output.
  - Flow Direction Optimization: Adjusts flow directions within the network to ensure optimal operation.
  - Diameter Optimization: Dynamically adjusts pipe diameters for improved flow and efficiency.
  - Network Export: Ability to export the network model as a GeoJSON file for geographical analysis.
  - Worst Point Calculation: Identifies the least efficient point in the network based on pressure differences, aiding in targeted improvements.

# my_controllers.py
- This module defines custom controller classes that extend the functionality of the basic controllers provided by Pandapipes. These controllers are responsible for dynamic regulation of network parameters during simulations.
  - ReturnTemperatureController: Regulates the temperature of the returning fluid in the network to achieve a specified target temperature.
  - WorstPointPressureController: Regulates the pressure lift at the circulation pump by setting a target pressure drop a the worst point in the network

Both controllers utilize a proportional control approach to minimize the error between the current state and the desired state of the network.

# net_simulation_test.py

- simple heating network to test algorithms

# net_simulation.py
  - initialize_net: Prepares and configures the network for simulation, setting up the necessary parameters and default conditions.
  - time_series_net: Conducts the actual simulation process, calculating the flow and pressure in each segment of the network.

# simulate_functions.py
This Python module, simulate_functions.py, is a comprehensive toolkit for simulating and analyzing district heating networks. It integrates various libraries such as matplotlib, pandapipes, pandas, and geopandas to facilitate complex thermohydraulic calculations and visualizations.

Key Features
  - Network Simulation: Initialize and simulate district heating networks using pandapipes.
  - Heat Requirement Calculation: Implement heat requirement calculations based on VDI4655 standard.
  - Data Import and Export: Functions to import weather data and export simulation results in CSV format.
  - Thermohydraulic Time Series Analysis: Perform detailed time series analysis for network hydraulics and thermodynamics.
  - Visualization: Plot results like network load, pump and temperature profiles.
  - Customizable Heat Generator Classes: Incorporate various heat generators like solar thermal, geothermal, and waste heat pumps for flexible simulations.

Usage
To use this module, import the necessary functions into your Python script. Ensure you have all the required dependencies installed. The module functions range from importing weather data, initializing test networks, calculating heat requirements, to plotting and saving results.

# Heat System Design GUI

This Python script implements a graphical user interface (GUI) for designing and analyzing heat systems, using PyQt5 for the interface and matplotlib for plotting. It allows users to input various parameters like gas, electricity, and wood prices, and choose whether to consider BEW funding. Users can add or remove different heating technologies, such as solar thermal systems, biomass boilers, and gas boilers, using a customizable dialog window. The GUI provides functionality to calculate and optimize heat generation costs and visualize results with pie charts and stack plots.
Features
  - User-friendly GUI for heat system design.
  - Customizable inputs for prices and technologies.
  - Visual representation of heating system performance.
  - Options to calculate and optimize heat generation mix.

This script is designed to be interactive and user-friendly, making it easier for users to experiment with different heating system configurations and understand their impact on overall system performance and cost.

# To Do
  
- A function needs to be defined to set the right crs (coordinate reference system) in QGIS when executing "net_generation_qgis.py"

- the network creation has to be modified to allow multiple pumps / entry points for heat
  
- the controller for the heat exchangers is not working perfectly at this point, maybe an alternative system has to be implemented

- Optimization and generalization

- Transition to English
- Evaluating integration with advanced simulation tools like SIM-VICUS, flixOpt, and EnSySim.
  
# Contributing

Contributions and ideas are welcome, with standard coding practices and pull request submissions.

# License
Current version of software written and maintained by Jonas Pfeiffer (HSZG)
MIT license


# Contact
  - Software maintained by Dipl.-Ing. (FH) Jonas Pfeiffer, under the MIT license.
  - Contact via GitHub or LinkedIn for collaboration or queries.
