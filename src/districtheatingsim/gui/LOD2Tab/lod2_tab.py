"""
Filename: lod2_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-30
Description: Contains the LOD2Tab as MVP structure.
"""

from PyQt5.QtWidgets import (QAction, QWidget, QVBoxLayout, QMenuBar)

from gui.LOD2Tab.lod2_data import LOD2DataModel, DataVisualizationPresenter, LOD2DataVisualization

class LOD2Tab(QWidget):
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LOD2 Tab")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize the model
        self.data_model = LOD2DataModel()

        # Initialize tabs
        self.data_vis_tab = LOD2DataVisualization()

        # Initialize the presenters
        self.data_vis_presenter = DataVisualizationPresenter(self.data_model, self.data_vis_tab, folder_manager, data_manager, config_manager)

        # Set up the layout
        self.main_layout = QVBoxLayout()

        # Create the Menu Bar
        self.initMenuBar()

        # Add the data visualization tab to the layout
        self.main_layout.addWidget(self.data_vis_tab)

        self.setLayout(self.main_layout)

    def initMenuBar(self):
        """Initializes the menu bar with actions."""
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)
        fileMenu = self.menubar.addMenu('Datei')

        self.openAction = QAction('Öffnen', self)
        fileMenu.addAction(self.openAction)
        self.openAction.triggered.connect(self.data_vis_presenter.load_data_from_file)

        self.saveAction = QAction('Speichern', self)
        fileMenu.addAction(self.saveAction)
        self.saveAction.triggered.connect(self.data_vis_presenter.save_data_as_geojson)

        processMenu = self.menubar.addMenu('Datenverarbeitung')

        self.processFilterAction = QAction('LOD2-Daten filtern laden', self)
        processMenu.addAction(self.processFilterAction)
        self.processFilterAction.triggered.connect(self.data_vis_presenter.show_filter_dialog)

        self.calculateHeatDemandAction = QAction('Wärmebedarf berechnen', self)
        processMenu.addAction(self.calculateHeatDemandAction)
        self.calculateHeatDemandAction.triggered.connect(self.data_vis_presenter.calculate_heat_demand)

        self.createCSVAction = QAction('Gebäude-csv für Netzgenerierung erstellen', self)
        processMenu.addAction(self.createCSVAction)
        self.createCSVAction.triggered.connect(self.data_vis_presenter.create_building_csv)

        self.main_layout.setMenuBar(self.menubar)