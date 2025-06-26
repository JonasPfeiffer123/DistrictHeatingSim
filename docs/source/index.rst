DistrictHeatingSim Documentation
=================================

.. image:: https://img.shields.io/badge/version-0.1.0-blue.svg
   :alt: Version

.. image:: https://img.shields.io/badge/python-3.11%2B-blue.svg
   :alt: Python Version

**DistrictHeatingSim** ist ein umfassendes Simulationswerkzeug für Fernwärmesysteme mit GUI-basierter Benutzeroberfläche und fortschrittlichen Berechnungsalgorithmen.

🚀 Quick Start
----------------

.. code-block:: python

   from districtheatingsim import DistrictHeatingSim
   
   # Starte die GUI-Anwendung
   app = DistrictHeatingSim()
   app.run()

📋 Hauptfunktionen
---------------------

.. grid:: 2

   .. grid-item-card:: 🏗️ Netzgenerierung
      :text-align: center
      
      Automatisierte Wärmenetz-Topologie aus OpenStreetMap-Daten

   .. grid-item-card:: 🏠 Gebäudemodellierung
      :text-align: center
      
      LOD2-Gebäudedaten und Wärmebedarfsberechnungen

   .. grid-item-card:: ⚡ Energiesysteme
      :text-align: center
      
      Wärmepumpen, KWK, Solar und Power-to-Heat Systeme

   .. grid-item-card:: 📊 Simulation
      :text-align: center
      
      Thermisch-hydraulische Simulation mit pandapipes

🛠️ Installation
-----------------

.. code-block:: bash

   pip install districtheatingsim
   
   # Oder für Entwicklung:
   git clone https://github.com/jonaspfeiffer123/DistrictHeatingSim.git
   cd DistrictHeatingSim
   pip install -e .

📚 Dokumentation
--------------------

.. toctree::
   :maxdepth: 3
   :caption: districtheatingsim package

   districtheatingsim

.. toctree::
   :maxdepth: 2
   :caption: 📖 Benutzerhandbuch

   installation
   getting_started
   tutorials/index
   gui_reference

.. toctree::
   :maxdepth: 1
   :caption: 👩‍💻 Entwicklung

   contributing
   changelog
   license

💡 Beispiele
--------------

.. grid:: 3

   .. grid-item-card:: Tutorial 1: Erstes Projekt
      :link: tutorials/first_project
      :text-align: center
      
      Erstelle dein erstes Fernwärme-Projekt

   .. grid-item-card:: Tutorial 2: Wärmepumpen
      :link: tutorials/heat_pumps  
      :text-align: center
      
      Integration von Wärmepumpen-Systemen

   .. grid-item-card:: Tutorial 3: Optimierung
      :link: tutorials/optimization
      :text-align: center
      
      Systemoptimierung und Vergleich

🤝 Community & Support
-----------------------

- 🐛 **Bug Reports**: `GitHub Issues <https://github.com/jonaspfeiffer123/DistrictHeatingSim/issues>`_
- 💬 **Diskussionen**: `GitHub Discussions <https://github.com/jonaspfeiffer123/DistrictHeatingSim/discussions>`_

Indizes und Tabellen
=====================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`