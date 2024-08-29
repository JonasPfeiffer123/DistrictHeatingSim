"""
Filename: lod2_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-28
Description: Contains the LOD2Tab as MVP structure.
"""

from PyQt5.QtWidgets import (QAction, QTabWidget, QMainWindow)
from PyQt5.QtCore import pyqtSignal, QObject

from gui.LOD2Tab.lod2_plot import LOD2PlotModel, PlotPresenter, LOD2PlotTab
from gui.LOD2Tab.lod2_data import LOD2DataModel, DataVisualizationPresenter, LOD2DataVisualizationTab

class LOD2Tab(QMainWindow):
    def __init__(self, folder_manager, data_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LOD2 Tab")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize the model
        self.data_model = LOD2DataModel()
        self.plot_model = LOD2PlotModel()

        # Initialize tabs
        self.data_vis_tab = LOD2DataVisualizationTab()
        self.plot_tab = LOD2PlotTab()

        # Initialize main view
        self.view = QTabWidget()
        self.view.addTab(self.data_vis_tab, "Tabelle und Visualisierung LOD2-Daten")
        self.view.addTab(self.plot_tab, "Balkendiagramm Wärmebedarf")

        # Initialize the presenters
        self.data_vis_presenter = DataVisualizationPresenter(self.data_model, self.data_vis_tab, folder_manager, data_manager)
        self.plot_presenter = PlotPresenter(self.plot_model, self.plot_tab, folder_manager)

        # Create the Menu Bar
        self.menuBar = self.menuBar()
        self.initMenuBar()

        self.setCentralWidget(self.view)

    def initMenuBar(self):
        """Initializes the menu bar with actions."""
        fileMenu = self.menuBar.addMenu('Datei')

        self.openAction = QAction('Öffnen', self)
        fileMenu.addAction(self.openAction)
        self.openAction.triggered.connect(self.data_vis_presenter.load_data_from_file)

        self.saveAction = QAction('Speichern', self)
        fileMenu.addAction(self.saveAction)
        self.saveAction.triggered.connect(self.data_vis_presenter.save_data_as_geojson)

        processMenu = self.menuBar.addMenu('Datenverarbeitung')

        self.processFilterAction = QAction('LOD2-Daten filtern laden', self)
        processMenu.addAction(self.processFilterAction)
        self.processFilterAction.triggered.connect(self.data_vis_presenter.show_filter_dialog)

        self.calculateHeatDemandAction = QAction('Wärmebedarf berechnen', self)
        processMenu.addAction(self.calculateHeatDemandAction)
        self.calculateHeatDemandAction.triggered.connect(self.data_vis_presenter.calculate_heat_demand)

        self.createCSVAction = QAction('Gebäude-csv für Netzgenerierung erstellen', self)
        processMenu.addAction(self.createCSVAction)
        self.createCSVAction.triggered.connect(self.data_vis_presenter.create_building_csv)

        datasetMenu = self.menuBar.addMenu('Datenvergleich')

        self.addDatasetAction = QAction('Datensatz hinzufügen', self)
        datasetMenu.addAction(self.addDatasetAction)
        self.addDatasetAction.triggered.connect(self.plot_presenter.add_dataset)

        self.removeDatasetAction = QAction('Datensatz entfernen', self)
        datasetMenu.addAction(self.removeDatasetAction)
        self.removeDatasetAction.triggered.connect(self.plot_presenter.remove_dataset)