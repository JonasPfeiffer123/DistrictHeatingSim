DistrictHeatingSim Documentation
=================================

.. image:: https://img.shields.io/badge/version-0.1.0-blue.svg
   :alt: Version

.. image:: https://img.shields.io/badge/python-3.11%2B-blue.svg
   :alt: Python Version

**DistrictHeatingSim** is a comprehensive simulation tool for district heating systems with GUI-based user interface and advanced calculation algorithms.

.. figure:: _static/images/workflow_chart.png
   :alt: DistrictHeatingSim Workflow
   :width: 80%
   :align: center
   :name: fig-workflow

   **Figure 1:** DistrictHeatingSim software workflow showing the integrated approach
   for district heating network planning and analysis.

📋 Key Features
---------------------

.. grid:: 2

   .. grid-item-card:: 🏗️ Network Generation
      :text-align: center
      
      Automated heating network topology from OpenStreetMap data

   .. grid-item-card:: 🏠 Building Modeling
      :text-align: center
      
      Building data and heat demand calculations

   .. grid-item-card:: ⚡ Energy Systems
      :text-align: center
      
      Heat pumps, CHP, solar and power-to-heat systems

   .. grid-item-card:: 📊 Simulation
      :text-align: center
      
      Thermo-hydraulic simulation with pandapipes

.. figure:: _static/images/project_management.png
   :alt: Project Management
   :width: 80%
   :align: center
   :name: fig-project-management

   **Figure 2:** Project management interface for organizing and managing district heating projects.

.. figure:: _static/images/building_load_profiles.png
   :alt: Building Load Profiles
   :width: 80%
   :align: center
   :name: fig-building-load-profiles

   **Figure 3:** Building load profiles based on building data and weather conditions.

.. figure:: _static/images/leaflet_map.png
   :alt: Leaflet Map
   :width: 80%
   :align: center
   :name: fig-leaflet-map

   **Figure 4:** Interactive map visualization of district heating networks using Leaflet.

.. figure:: _static/images/net_simulation_pandapipes_2.png
   :alt: Network Simulation with pandapipes
   :width: 80%
   :align: center
   :name: fig-net-simulation-pandapipes

   **Figure 5:** Thermo-hydraulic simulation of district heating networks using pandapipes.

.. figure:: _static/images/heat_generator_definition.png
   :alt: Heat Generation Definition
   :width: 80%
   :align: center
   :name: fig-heat-generation-definition

   **Figure 6:** Definition of heat generation systems including heat pumps and CHP units.

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

💡 Examples
--------------

The following examples demonstrate various aspects of the DistrictHeatingSim application. 
All example files are located in the ``examples/`` directory of the project repository.

.. grid:: 3

   .. grid-item-card:: 🚀 Getting Started
      :text-align: center
      
      Basic geocoding and data import examples
      
      See: ``01_example_geocoding.py``, ``02_example_import_osm_data_geojson.py``

   .. grid-item-card:: 🏠 Building Analysis
      :text-align: center
      
      Heat demand calculations
      
      See: ``03_example_simple_heat_requirement.py``, ``04_example_data_heat_requirement.py``

   .. grid-item-card:: 🌐 Network Design
      :text-align: center
      
      Network generation and optimization with MST and OSMnx
      
      See: ``05_example_net_generation.py``, ``05b_example_net_generation_osmnx.py``, ``05c_example_osmnx_threading_compatible.py``

   .. grid-item-card:: 📊 Simulation
      :text-align: center
      
      Thermo-hydraulic simulation with pandapipes
      
      See: ``06_example_simple_pandapipes.py``, ``06b_example_simple_pandapipes_osmnx.py``, ``07_example_timeseries_pandapipes.py``, ``08_example_complex_pandapipes_timeseries.py``

   .. grid-item-card:: ⚡ Heat Generators
      :text-align: center
      
      Heat pumps, CHP units, photovoltaics and system optimization
      
      See: ``09_example_heat_generators.py``, ``10_example_heat_generation_optimization.py``, ``14_example_photovoltaics.py``

   .. grid-item-card:: 🔋 Energy Systems
      :text-align: center
      
      Seasonal thermal storage and integrated energy systems
      
      See: ``17_energy_system_seasonal_storage.py``

   .. grid-item-card:: 💰 Economic Analysis
      :text-align: center
      
      Annuity calculations and financial evaluation
      
      See: ``15_example_annuity.py``

   .. grid-item-card:: 🔄 Data Import/Export
      :text-align: center
      
      STANET import and network data conversion
      
      See: ``18_stanet_to_pandapipes.py``

   .. grid-item-card:: 📈 Visualization
      :text-align: center
      
      Interactive plots, maps and network visualization
      
      See: ``16_interactive_matplotlib.py``, ``20_leaflet_test.py``, ``21_example_advanced_plots.py``

   .. grid-item-card:: 🧪 Testing & Development
      :text-align: center
      
      GUI component tests, benchmarks and development tools
      
      See: ``19_generator_schematic_test_window.py``, ``example_interactive_network_plot.py``, ``benchmark_synthetic_net_generation.py``

.. toctree::
   :maxdepth: 3
   :caption: Examples
   :glob:
   
   examples

📋 Example Data
----------------

Examples use various data sources and formats:

- **Geographic Data**: OpenStreetMap data, building coordinates
- **Building Data**: Heat demand parameters, building specifications
- **Weather Data**: TRY (Test Reference Year) files
- **System Data**: Heat pump performance curves, generator specifications
- **Network Data**: Pipe specifications, node configurations

Some examples generate their own test data, while others may require external data files from the ``examples/data/`` directory.

🤝 Community & Support
-----------------------

- 🐛 **Bug Reports**: `GitHub Issues <https://github.com/jonaspfeiffer123/DistrictHeatingSim/issues>`_
- 💬 **Discussions**: `GitHub Discussions <https://github.com/jonaspfeiffer123/DistrictHeatingSim/discussions>`_
- 📖 **Examples**: `GitHub Examples <https://github.com/jonaspfeiffer123/DistrictHeatingSim/tree/main/examples>`_

.. toctree::
   :maxdepth: 3
   :caption: Development

   references

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`