DistrictHeatingSim Documentation
=================================

.. image:: https://img.shields.io/badge/version-0.1.0-blue.svg
   :alt: Version

.. image:: https://img.shields.io/badge/python-3.11%2B-blue.svg
   :alt: Python Version

**DistrictHeatingSim** is a comprehensive simulation tool for district heating systems with GUI-based user interface and advanced calculation algorithms.

📋 Key Features
---------------------

.. grid:: 2

   .. grid-item-card:: 🏗️ Network Generation
      :text-align: center
      
      Automated heating network topology from OpenStreetMap data

   .. grid-item-card:: 🏠 Building Modeling
      :text-align: center
      
      LOD2 building data and heat demand calculations

   .. grid-item-card:: ⚡ Energy Systems
      :text-align: center
      
      Heat pumps, CHP, solar and power-to-heat systems

   .. grid-item-card:: 📊 Simulation
      :text-align: center
      
      Thermo-hydraulic simulation with pandapipes

🛠️ Installation
-----------------

.. code-block:: bash

   pip install districtheatingsim
   
   # Or for development:
   git clone https://github.com/jonaspfeiffer123/DistrictHeatingSim.git
   cd DistrictHeatingSim
   pip install -e .

🚀 Quick Start
----------------

To start the application directly, run the following in the terminal:

.. code-block:: bash

   python src/districtheatingsim/DistrictHeatingSim.py

📚 Documentation
--------------------

.. toctree::
   :maxdepth: 3
   :caption: DistrictHeatingSim

   districtheatingsim

.. toctree::
   :maxdepth: 3
   :caption: Development

   references

💡 Examples
--------------

The following examples demonstrate various aspects of the DistrictHeatingSim application. 
All example files are located in the ``examples/`` directory of the project repository.

.. toctree::
   :maxdepth: 3
   :caption: 📚 Examples
   :glob:
   
   examples/*

.. grid:: 3

   .. grid-item-card:: 🚀 Getting Started
      :text-align: center
      
      Basic geocoding and data import examples
      
      See: ``01_example_geocoding.py``, ``02_example_import_osm_data_geojson.py``

   .. grid-item-card:: 🏠 Building Analysis
      :text-align: center
      
      Heat demand calculations and LOD2 processing
      
      See: ``03_example_simple_heat_requirement.py``, ``04_example_data_heat_requirement.py``, ``11_example_lod2.py``

   .. grid-item-card:: 🌐 Network Design
      :text-align: center
      
      Network generation and optimization
      
      See: ``05_example_net_generation.py``, ``10_example_heat_generation_optimization.py``

   .. grid-item-card:: ⚡ Energy Systems
      :text-align: center
      
      Heat generators and seasonal storage
      
      See: ``09_example_heat_generators.py``, ``17_energy_system_seasonal_storage.py``

   .. grid-item-card:: 📊 Simulation
      :text-align: center
      
      Pandapipes simulation and time series analysis
      
      See: ``06_example_simple_pandapipes.py``, ``07_example_timeseries_pandapipes.py``, ``08_example_complex_pandapipes_timeseries.py``

   .. grid-item-card:: 💰 Economic Analysis
      :text-align: center
      
      Renovation analysis and financial calculations
      
      See: ``12_example_renovation_analysis.py``, ``15_example_annuity.py``

📁 Available Examples
----------------------

The examples are organized by functionality:

**Data Processing & Import:**

- ``01_example_geocoding.py`` - Geocoding addresses to coordinates
- ``02_example_import_osm_data_geojson.py`` - Import OpenStreetMap data in GeoJSON format
- ``11_example_lod2.py`` - Processing LOD2 building data

**Heat Demand Calculations:**

- ``03_example_simple_heat_requirement.py`` - Basic heat demand calculation
- ``04_example_data_heat_requirement.py`` - Data-driven heat demand analysis

**Network Design & Generation:**

- ``05_example_net_generation.py`` - Automated network topology generation
- ``10_example_heat_generation_optimization.py`` - Heat generation system optimization

**Simulation & Analysis:**

- ``06_example_simple_pandapipes.py`` - Basic pandapipes simulation
- ``07_example_timeseries_pandapipes.py`` - Time series simulation with pandapipes  
- ``08_example_complex_pandapipes_timeseries.py`` - Complex time series analysis

**Energy Systems:**

- ``09_example_heat_generators.py`` - Heat generator configuration and analysis
- ``17_energy_system_seasonal_storage.py`` - Seasonal energy storage systems

**Economic Analysis:**

- ``12_example_renovation_analysis.py`` - Building renovation economic analysis
- ``15_example_annuity.py`` - Annuity and financial calculations

**Visualization & Tools:**

- ``14_example_photovoltaics.py`` - Photovoltaic system integration
- ``16_interactive_matplotlib.py`` - Interactive plotting and visualization
- ``18_stanet_to_pandapipes.py`` - STANET to pandapipes conversion
- ``19_generator_schematic_test_window.py`` - Generator schematic testing
- ``20_leaflet_test.py`` - Interactive map visualization with Leaflet

🔗 Running Examples
--------------------

To run the examples, navigate to the project root directory and execute:

.. code-block:: bash

   # Navigate to project root
   cd DistrictHeatingSim
   
   # Run a specific example
   python examples/01_example_geocoding.py
   
   # Run heat demand calculation example
   python examples/03_example_simple_heat_requirement.py
   
   # Run network generation example
   python examples/05_example_net_generation.py

.. note::
   Make sure you have installed DistrictHeatingSim in development mode before running examples:
   
   .. code-block:: bash
   
      pip install -e .

📋 Example Data
----------------

Examples use various data sources and formats:

- **Geographic Data**: OpenStreetMap data, building coordinates
- **Building Data**: LOD2 models, heat demand parameters
- **Weather Data**: TRY (Test Reference Year) files
- **System Data**: Heat pump performance curves, generator specifications
- **Network Data**: Pipe specifications, node configurations

Some examples generate their own test data, while others may require external data files from the ``examples/data/`` directory.

🤝 Community & Support
-----------------------

- 🐛 **Bug Reports**: `GitHub Issues <https://github.com/jonaspfeiffer123/DistrictHeatingSim/issues>`_
- 💬 **Discussions**: `GitHub Discussions <https://github.com/jonaspfeiffer123/DistrictHeatingSim/discussions>`_
- 📖 **Examples**: `GitHub Examples <https://github.com/jonaspfeiffer123/DistrictHeatingSim/tree/main/examples>`_

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`