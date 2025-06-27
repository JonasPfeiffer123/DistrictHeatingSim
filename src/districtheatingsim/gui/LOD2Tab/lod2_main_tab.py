"""
LOD2 Main Tab Module
===================

Main tab for LOD2 building data visualization and processing.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-07
"""

import os
import traceback

from PyQt5.QtWidgets import (QAction, QWidget, QVBoxLayout, QMenuBar, QMessageBox, QFileDialog)

from districtheatingsim.gui.LOD2Tab.lod2_data_model import LOD2DataModel
from districtheatingsim.gui.LOD2Tab.lod2_presenter import DataVisualizationPresenter
from districtheatingsim.gui.LOD2Tab.lod2_visualization import LOD2DataVisualization
from districtheatingsim.gui.LOD2Tab.lod2_dialogs import LOD2DownloadDialog

class LOD2Tab(QWidget):
    """
    Main tab widget for LOD2 building data visualization and processing.
    """
    
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize LOD2 main tab.

        Parameters
        ----------
        folder_manager : FolderManager
            Project folder manager.
        data_manager : DataManager
            Application data manager.
        config_manager : ConfigManager
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        self.folder_manager.project_folder_changed.connect(self.on_project_folder_changed)
        self.on_project_folder_changed(self.folder_manager.variant_folder)

        self.setWindowTitle("LOD2 Tab")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize the model
        self.data_model = LOD2DataModel()

        # Initialize tabs
        self.data_vis_tab = LOD2DataVisualization()

        # Initialize the presenters
        self.data_vis_presenter = DataVisualizationPresenter(self.data_model, self.data_vis_tab, self.folder_manager, self.data_manager, self.config_manager)

        # Set up the layout
        self.main_layout = QVBoxLayout()

        # Create the Menu Bar
        self.initMenuBar()

        # Add the data visualization tab to the layout
        self.main_layout.addWidget(self.data_vis_tab)

        self.setLayout(self.main_layout)

    def on_project_folder_changed(self, new_base_path):
        """
        Update base path when project folder changes.

        Parameters
        ----------
        new_base_path : str
            New base path.
        """
        self.set_base_path(new_base_path)

    def set_base_path(self, base_path):
        """
        Set base path for file operations.

        Parameters
        ----------
        base_path : str
            Base path to set.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get current base path.

        Returns
        -------
        str
            Current base path.
        """
        return self.base_path

    def initMenuBar(self):
        """Initialize menu bar with file and processing actions."""
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

        self.lod2DownloadAction = QAction('LOD2-Daten herunterladen', self)
        processMenu.addAction(self.lod2DownloadAction)
        self.lod2DownloadAction.triggered.connect(self.open_lod2_download_dialog)

        self.processFilterAction = QAction('LOD2-Daten filtern laden', self)
        processMenu.addAction(self.processFilterAction)
        self.processFilterAction.triggered.connect(self.data_vis_presenter.show_filter_dialog)

        self.calculateHeatDemandAction = QAction('Wärmebedarf berechnen', self)
        processMenu.addAction(self.calculateHeatDemandAction)
        self.calculateHeatDemandAction.triggered.connect(self.data_vis_presenter.calculate_heat_demand)

        self.createCSVAction = QAction('Gebäude-csv für Netzgenerierung erstellen', self)
        processMenu.addAction(self.createCSVAction)
        self.createCSVAction.triggered.connect(self.data_vis_presenter.create_building_csv)

        self.createPVAction = QAction('PV-Daten für Gebäudedachflächen berechnen', self)
        processMenu.addAction(self.createPVAction)
        self.createPVAction.triggered.connect(self.pv_file_dialog)

        self.main_layout.setMenuBar(self.menubar)

    def open_lod2_download_dialog(self):
        """Open LOD2 data download dialog."""
        dialog = LOD2DownloadDialog(self.folder_manager, self.config_manager, self)
        dialog.exec_()
    
    def pv_file_dialog(self):
        """Open file dialog for PV data calculation output."""
        try:
            # Get the output file name
            output_filename, _ = QFileDialog.getSaveFileName(
                self, "Speichern unter", os.path.join(self.get_base_path(), self.config_manager.get_relative_path("pv_results")), "CSV-Dateien (*.csv)")
            
            if not output_filename:
                return
            
            self.data_vis_presenter.calculate_pv_data(output_filename)
        
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern", f"Beim Speichern der Datei ist ein Fehler aufgetreten: {e}\n\n{traceback.format_exc()}")
            return