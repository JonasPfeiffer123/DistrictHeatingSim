Functionality examples
==========================

This section contains practical examples demonstrating the usage of DistrictHeatingSim.

Getting Started Examples
------------------------

Geocoding Example
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/01_example_geocoding.py
   :language: python
   :linenos:
   :caption: 01_example_geocoding.py

This example demonstrates how to geocode addresses to coordinates.

Import OSM Data Example
~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/02_example_import_osm_data_geojson.py
   :language: python
   :linenos:
   :caption: 02_example_import_osm_data_geojson.py

This example shows how to import OpenStreetMap data in GeoJSON format.

Heat Demand Examples
--------------------

Simple Heat Requirement
~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/03_example_simple_heat_requirement.py
   :language: python
   :linenos:
   :caption: 03_example_simple_heat_requirement.py

Basic heat demand calculation example.

Data-driven Heat Requirement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/04_example_data_heat_requirement.py
   :language: python
   :linenos:
   :caption: 04_example_data_heat_requirement.py

Data-driven heat demand analysis example.

Network Design Examples
-----------------------

Network Generation
~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/05_example_net_generation.py
   :language: python
   :linenos:
   :caption: 05_example_net_generation.py

Automated network topology generation example.

Simulation Examples
-------------------

Simple Pandapipes Simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/06_example_simple_pandapipes.py
   :language: python
   :linenos:
   :caption: 06_example_simple_pandapipes.py

Basic pandapipes simulation example.

Time Series Simulation
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/07_example_timeseries_pandapipes.py
   :language: python
   :linenos:
   :caption: 07_example_timeseries_pandapipes.py

Time series simulation with pandapipes.

Complex Time Series Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/08_example_complex_pandapipes_timeseries.py
   :language: python
   :linenos:
   :caption: 08_example_complex_pandapipes_timeseries.py

Complex time series analysis example.

Energy Systems Examples
-----------------------

Heat Generators
~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/09_example_heat_generators.py
   :language: python
   :linenos:
   :caption: 09_example_heat_generators.py

Heat generator configuration and analysis.

Heat Generation Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/10_example_heat_generation_optimization.py
   :language: python
   :linenos:
   :caption: 10_example_heat_generation_optimization.py

Heat generation system optimization example.

Building Analysis Examples
--------------------------

LOD2 Processing
~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/11_example_lod2.py
   :language: python
   :linenos:
   :caption: 11_example_lod2.py

Processing LOD2 building data example.

Renovation Analysis
~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/12_example_renovation_analysis.py
   :language: python
   :linenos:
   :caption: 12_example_renovation_analysis.py

Building renovation economic analysis example.

Visualization Examples
----------------------

Photovoltaics Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/14_example_photovoltaics.py
   :language: python
   :linenos:
   :caption: 14_example_photovoltaics.py

Photovoltaic system integration example.

Annuity Calculation
~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/15_example_annuity.py
   :language: python
   :linenos:
   :caption: 15_example_annuity.py

Annuity and financial calculations example.

Interactive Plotting
~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/16_interactive_matplotlib.py
   :language: python
   :linenos:
   :caption: 16_interactive_matplotlib.py

Interactive plotting and visualization example.

Seasonal Storage
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/17_energy_system_seasonal_storage.py
   :language: python
   :linenos:
   :caption: 17_energy_system_seasonal_storage.py

Seasonal energy storage systems example.

Utility Examples
----------------

STANET to Pandapipes Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/18_stanet_to_pandapipes.py
   :language: python
   :linenos:
   :caption: 18_stanet_to_pandapipes.py

STANET to pandapipes conversion example.

Generator Schematic Test
~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/19_generator_schematic_test_window.py
   :language: python
   :linenos:
   :caption: 19_generator_schematic_test_window.py

Generator schematic testing example.

Leaflet Map Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/20_leaflet_test.py
   :language: python
   :linenos:
   :caption: 20_leaflet_test.py

Interactive map visualization with Leaflet example.

Running Examples
================

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

.. tip::
   All example files are located in the ``examples/`` directory of the project repository.
   Each example is self-contained and demonstrates specific functionality of DistrictHeatingSim.