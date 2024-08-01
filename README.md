
# DistrictHeatSim

## Introduction

Welcome to the DistrictHeatSim project, a comprehensive tool for planning and optimizing sustainable district heating networks. This README provides an overview of the project's functionality, installation instructions, and usage guidelines. 

DistrictHeatSim is developed by Dipl.-Ing. (FH) Jonas Pfeiffer as part of the SMWK-NEUES TG70 project, which focuses on the development and testing of methods and tools for the conceptualization of sustainable heating networks. The software integrates technical and economic simulations to support the design and evaluation of district heating systems.

## Table of Contents
1. [Features](#features)
2. [Installation](#installation)
3. [Usage](#usage)
    - [Spatial Analysis](#spatial-analysis)
    - [Heat Network Calculation](#heat-network-calculation)
    - [Generator Sizing and Economic Analysis](#generator-sizing-and-economic-analysis)
4. [Requirements](#requirements)
5. [Project Structure](#project-structure)
6. [Contribution Guidelines](#contribution-guidelines)
7. [License](#license)
8. [Contact Information](#contact-information)

## Features

### User Interface
- **Project Definition**: Create croject project folders and your data input
- **Building Heat Demand Profile Calculation**: Calculate the heat demand profiles for your buildings
- **Geocoding**: Convert addresses to coordinates and visualize them on a map.
- **OSM Data Integration**: Download and process OpenStreetMap data for streets and buildings.
- **Spatial Clustering**: Cluster buildings into supply areas based on heat demand.
- **Automatic Heat Network Generation**: Generate heating networks based on building and generator locations.
- **GIS Data Handling**: Uniformly manage and store GIS data in the GeoJSON format.
- **LOD2 Data Processing**: Work with detailed 3D building data to analyze heating demands and simulate renovation options.
- **Thermohydraulic Network Calculation**: Simulate the generated heat networks with [pandapipes](https://github.com/e2nIEE/pandapipes).
- **Cost Calculation**: Calculate heat generation costs based on [VDI 2067](https://www.vdi.de/richtlinien/details/vdi-2067-blatt-1-wirtschaftlichkeit-gebaeudetechnischer-anlagen-grundlagen-und-kostenberechnung-1) methodology and various cost inputs.
- **Renovation Calculation**: Calculate the cost of building renovation based on calculated renovation variants.
- **PDF Report Generation**: Create detailed PDF reports with economic and technical results.
- **Save/Load Project Results**: Integrated options to save and load calculated results in most parts of the software

### Technical Capabilities
- **Heat Requirement Calculation**: Calculate heat demands based on different profiles and weather data.
- **Economic Scenario Analysis**: Evaluate the economic feasibility of various heating scenarios.
- **Optimization Algorithms**: Optimize heating network configurations for cost efficiency.
- **Integration of Renewable Technologies**: Support for solar thermal, biomass, geothermal, and other renewable sources.

## Installation

To install DistrictHeatSim, ensure you have Python installed on your system. Follow the steps below:

1. **Clone the repository**:
    ```sh
    git clone https://github.com/JonasPfeiffer123/DistrictHeatSim.git
    ```

2. **Navigate to the project directory**:
    ```sh
    cd DistrictHeatSim
    ```

3. **Install the required packages**:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

### Building Heat Demand Profile Calculation

1. **Load CSV-File**: Load CSV-file with project specific building informations.
2. **Choose Profiles**: Choose profiles for these building if not defined previously.
3. **Calculate Profiles**: Calculate the profiles based on weather data.
4. **View in Diagram**: Results are shown in the diagramm and saved as JSON

### Spatial Analysis

1. **Load Project**: Start the application and select or create a new project.
2. **Geocoding**: Use the built-in tool to convert address data in CSV format to coordinates.
3. **OSM Data**: Download and integrate street and building data from OpenStreetMap.
4. **Clustering**: Cluster buildings into supply areas based on heat demand density.
5. **Heat Network Generation**: Automatically generate a heat network based on building and generator locations.

### LOD2-Data Processing
1. **Filter LOD2 Data**: Filter LOD2 3D building data based on polygon or adresses
2. **Process LOD2 Data**: Process detailed 3D building data for heat demand analysis. Calculating building areas.
2. **Load TABULA Data**: Combine LOD2 data with [TABULA](https://webtool.building-typology.eu/#bm) building data.
2. **Calculate Heat Demand**: Use the LOD2 and TABULA data to calculate heat demands for different renovation options.

### Heat Network Calculation

1. **Load Data**: Import the generated heat network data into Pandapipes.
2. **Simulation**: Perform thermohydraulic calculations to simulate the heat network.
3. **Optimization**: Optimize the network for cost efficiency and operational performance.
4. **Results**: Visualize the results, including flow rates, pressures, and temperatures.

### Generator Sizing and Economic Analysis

1. **Define Parameters**: Set up economic parameters and cost factors.
2. **Generator Configuration**: Configure different types of heat generators and their capacities.
3. **Simulation**: Simulate the performance and cost of different heating scenarios.
4. **Report Generation**: Generate a PDF report with the simulation results, economic analysis, and recommendations.

### Buidling Renovation Cost Calculation
1. **Load Renovation Variants**: Load LOD2 results from LOD2 processing.
2. **Cost definition**: Define specifc renovation costs.
3. **Simulation**: Calculate total costs of renovation options. 

## Requirements

- Python 3.8 - Python 3.11 ; some libraries currently not working in 3.12
- Required Python packages listed in `requirements.txt`:
    ```text
    PyQt5
    geopandas
    PyQtWebEngine
    folium
    scipy
    matplotlib
    pandapipes
    geopy
    overpy
    geojson
    scikit-learn
    hdbscan
    PyPDF2
    reportlab
    numpy_financial
    ```

## Project Structure

- **src/districtheatsim**: Source code for DistrictHeatSim
- **docs**: Documentation for DistrictHeatSim
- **flow_chart**: Shows two flow charts describing data processing in DistrictHeatSim
- **requirements.txt**: List of dependencies
- **README.md**: This README file

- **currently_not_used**: Contains multiple python files with various functionality which are currently not integrated in DistrictHeatSim

## Documentation
The Code is documented with docstrings which are readable by [Sphinx](https://www.sphinx-doc.org/en/master/) and therefore a documentation can be created by doing

1. **Directing to the docs folder**:
    ```sh
    cd docs
    ```

2. **Generating the .rst-files**:
    ```sh
    sphinx-apidoc -o source/ ../src/districtheatsim
    ```

3. **Generate the htmls**:
    ```sh
    make clean
    make html
    ```

## Contribution Guidelines

I welcome contributions from the community. To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with descriptive messages.
4. Push your changes to your forked repository.
5. Open a pull request to the main repository.

Please ensure that your contributions align with the project's coding standards and add tests for new functionalities.

## License

DistrictHeatSim is licensed under the MIT License. See the `LICENSE` file for more details.

## Contact Information

For further information, questions, or feedback, please contact the project maintainer:

Jonas Pfeiffer  
[GitHub Profile](https://github.com/JonasPfeiffer123)  
Email: jonas.pfeiffer(at)hszg.de

[LinkedIn](https://de.linkedin.com/in/jonas-pfeiffer-0357691a2)
