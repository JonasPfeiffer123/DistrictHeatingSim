# DistrictHeatSim

This project, led by Dipl.-Ing. (FH) Jonas Pfeiffer for the SMWK-NEUES TG-70 project "Entwicklung und Erprobung von Methoden und Werkzeugen zur Konzeptionierung nachhaltiger Wärmenetze" (Development and testing of methods and tools for designing sustainable heating networks) at Hochschule Zittau/Görlitz, aims to develop and test tools for creating sustainable heating networks using geospatial data, GIS functionalities.

# Usage
Install all required libraries with pip install -r requirements.txt.

In the tests-folder you can find different tests, which show the functionalities of the tool.

In the districtheatsim-folder you can find the tool, which can be run with "DistrictHeatSim.py".

# Data
For the developement and testing of the algorithms and functions, geodata is required. In this case data examples from the city of Bad Muskau were choosed and geocoded. Also some synthetic datapoints were added. This example-datasets are saved in the project_data-folder. The district heating network were generated for these datapoints.

# Heat System Design GUI

This Python script implements a graphical user interface (GUI) for designing and analyzing heat systems, using PyQt5 for the interface and matplotlib for plotting. It allows users to input various parameters like gas, electricity, and wood prices. Users can add different heating technologies, such as solar thermal systems, biomass boilers, and gas boilers, using a customizable dialog window. The GUI provides functionality to calculate and optimize heat generation costs and visualize results with pie charts and stack plots.
Features
  - GUI for heat system design.
  - Map-feature allows the import and visualisation of GIS-data
  - pandapipes-powered thermohydraulic net calculation simulates heating demand
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
  - Dipl.-Ing. (FH) Jonas Pfeiffer, Hochschule Zittau/Görlitz
  - Contact via GitHub or LinkedIn for collaboration or queries.
