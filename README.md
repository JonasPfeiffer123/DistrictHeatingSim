# heating_network_generation

This project, led by Dipl.-Ing. (FH) Jonas Pfeiffer for the SMWK-NEUES TG-70 project "Entwicklung und Erprobung von Methoden und Werkzeugen zur Konzeptionierung nachhaltiger Wärmenetze" (Development and testing of methods and tools for designing sustainable heating networks) at Hochschule Zittau/Görlitz, aims to develop and test tools for creating sustainable heating networks using geospatial data, GIS functionalities.

# Usage

"geocoding"
- for the geocoding python files the libraries "Nominatim" and "Transformer" are needed
- There are 2 scripts which allow you to geocode given adresses
- the folder is also used for storage of example data

"gui"
- contains all gui related scripts

"heat_generators"
- heat_generator_classes defines different heat generator classes and a function to calculate the heat generation mix based on a given load and predefined heat generators and an optimize-function to minimize the cost of such a system

"heat_requirement"
- implementation of the VDI 4655 and BDEW load profile calculations (based on the available Excel-file from https://www.umwelt-campus.de/energietools)
- uses TRY-data

"net_generation"
The collection of Python scripts provides a comprehensive solution for designing and analyzing district heating (DH) networks, with a strong emphasis on geospatial data processing and network optimization.
- import_and_create_layers.py: Essential for importing, processing, and exporting geospatial data, this script uses geopandas and shapely. Key features include importing street layers, generating line objects based on spatial points, and creating GeoDataFrames for different layers. It effectively integrates multiple data sources into usable geographic layers, which are then exported as GeoJSON for further use.

- simple_MST.py: Focused on network structuring, this script utilizes networkx to construct Minimum Spanning Trees (MST) from geospatial data. It includes several geometric manipulation functions, like creating offset points and finding the nearest line to a point. The script is instrumental in generating network structures for both supply and return lines, ensuring efficient connectivity within the DH network based on geographic considerations.

Overall, these scripts work in tandem to facilitate the detailed creation, analysis, and optimization of district heating networks, addressing both the geometric complexities of urban environments and the specific requirements of efficient heat distribution systems.

"net_generation_QGIS"
- basically brings the same functionality as the net_generation-folder but is designed for the usage inside the QGIS application

"net_simulation_pandapipes"
- the "pandapipes" and "geopanda" libraries are needed.
- Purpose: Simulates the heating network using the pandapipes framework, focusing on pipe flow and network optimization.
- Key Functions:
  - Network Creation from GIS Data: Utilizes geospatial data to create detailed models of district heating networks.
  - Pipe Initialization: Supports both diameter-based and type-based pipe initialization for network modeling.
  - Heat Exchanger Integration: Automates the addition of heat exchangers into the network with specified heat output.
  - Flow Direction Optimization: Adjusts flow directions within the network to ensure optimal operation.
  - Diameter Optimization: Dynamically adjusts pipe diameters for improved flow and efficiency.
  - Network Export: Ability to export the network model as a GeoJSON file for geographical analysis.
  - Worst Point Calculation: Identifies the least efficient point in the network based on pressure differences, aiding in targeted improvements.
  - controllers.py
    - This module defines custom controller classes that extend the functionality of the basic controllers provided by Pandapipes. These controllers are responsible for dynamic regulation of network parameters during simulations.
    - ReturnTemperatureController: Regulates the temperature of the returning fluid in the network to achieve a specified target temperature.
    - WorstPointPressureController: Regulates the pressure lift at the circulation pump by setting a target pressure drop a the worst point in the network
    Both controllers utilize a proportional control approach to minimize the error between the current state and the desired state of the network.

"osm_data"
- contains functions for OSM download and analysis

"main-folder"
- "main_gui.py" is the main application
- "main.py" can also be used to test functionality

# Data
For the developement and testing of the algorithms and functions, geodata is required. In this case a few local adresses in Zittau were choosed and geocoded. Also some synthetic datapoints were added. This example-datasets are saved in the geocoding-folder. The district heating network will be generated for these datapoints.

# Heat System Design GUI

This Python script implements a graphical user interface (GUI) for designing and analyzing heat systems, using PyQt5 for the interface and matplotlib for plotting. It allows users to input various parameters like gas, electricity, and wood prices, and choose whether to consider BEW funding. Users can add or remove different heating technologies, such as solar thermal systems, biomass boilers, and gas boilers, using a customizable dialog window. The GUI provides functionality to calculate and optimize heat generation costs and visualize results with pie charts and stack plots.
Features
  - GUI for heat system design.
  - Customizable inputs for prices and technologies.
  - Visual representation of heating system performance.
  - Options to calculate and optimize heat generation mix.

This script is designed to be interactive and user-friendly, making it easier for users to experiment with different heating system configurations and understand their impact on overall system performance and cost.

# To Do

- Error Handling
- Introduce Project Files
    - Save and Load Features
    - Make Information Available Across Tabs
    - Ability to Work on Multiple Projects Simultaneously

Visualization and Import of GIS Data:
  - Expand Query Requests for Downloading OSM Data
  - Import of Generator Locations via CSV --> Multiple Entries Possible
  - Convert Stanet Network to GeoJSON and Enable Import into Map
  - Error Handling

Network Calculation:
  - Revise Calculation Parameters (Return Line Temperature, Profiles)
  - Add Profile Subtypes
  - Multiple Generators --> Determine Which One Uses Circulation Pump, Others Set as Fixed Injection (or Controlled by Main Generator Location)

Design of Generator Mix
  - Parameter Variation for Pricing
  - When Optimizing, a Copy of the Current Tab Should be Created and the Optimal Composition Displayed in a New Variant
  - Add CO2 Emission Factors for Fuels --> Calculate Emissions for Heat Supply --> CO2 Emissions as Another Optimization Metric
  - Further Customize PDF Export
  - Create Standard Components

- Evaluating integration with advanced simulation tools like SIM-VICUS, flixOpt, GHEtool and EnSySim.
  
# Contributing

Contributions and ideas are welcome, with standard coding practices and pull request submissions.

# License
Current version of software written and maintained by Jonas Pfeiffer (HSZG)
MIT license


# Contact
  - Software maintained by Dipl.-Ing. (FH) Jonas Pfeiffer, under the MIT license.
  - Contact via GitHub or LinkedIn for collaboration or queries.
