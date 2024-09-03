# Filename: pv_tab.py
# Author: Dipl.-Ing. (FH) Jonas Pfeiffer
# Date: 2024-09-03
# Description: Contains the PVTab as MVP structure.

import pandas as pd

from PyQt5.QtWidgets import (QAction, QTabWidget, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QMessageBox, QTableWidgetItem)
from gui.PVTab.pv_mvp import PVDataModel, DataVisualizationPresenter, PVDataVisualizationTab
from heat_generators.photovoltaics import Calculate_PV

class PVTab(QMainWindow):
    def __init__(self, folder_manager, data_manager, parent=None):
        super().__init__(parent)

        # Connect the folder manager signal
        self.folder_manager = folder_manager
        self.data_manager = data_manager

        self.folder_manager.project_folder_changed.connect(self.on_project_folder_changed)
        self.on_project_folder_changed(self.folder_manager.project_folder)

        self.setWindowTitle("PV Tab")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize the model
        self.data_model = PVDataModel()

        # Initialize tabs
        self.data_vis_tab = PVDataVisualizationTab()

        # Initialize main view
        self.view = QTabWidget()
        self.view.addTab(self.data_vis_tab, "Tabelle und Visualisierung LOD2-Daten")

        # Initialize the presenters
        self.data_vis_presenter = DataVisualizationPresenter(self.data_model, self.data_vis_tab, folder_manager, data_manager)

        # Create the Menu Bar
        self.menuBar = self.menuBar()
        self.initMenuBar()

        # Create the Calculate Button
        self.calculate_button = QPushButton("Berechnen", self)
        self.calculate_button.clicked.connect(self.calculate_pv_yield)
        layout = QVBoxLayout()
        layout.addWidget(self.calculate_button)
        layout.addWidget(self.view)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def initMenuBar(self):
        """Initializes the menu bar with actions."""
        fileMenu = self.menuBar.addMenu('Datei')

        self.openAction = QAction('Öffnen', self)
        fileMenu.addAction(self.openAction)
        self.openAction.triggered.connect(self.data_vis_presenter.load_data_from_file)

    def on_project_folder_changed(self, new_base_path):
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.set_base_path(new_base_path)

    def set_base_path(self, base_path):
        """
        Set the base path for file operations.

        Args:
            base_path (str): The base path for file operations.
        """
        self.base_path = base_path

    def get_base_path(self):
        """
        Get the current base path.

        Returns:
            str: The current base path.
        """
        return self.base_path

    def calculate_pv_yield(self):
        """Handles the PV yield calculation when the 'Berechnen' button is pressed."""
        try:
            # Get the output file name
            output_filename, _ = QFileDialog.getSaveFileName(self, "Speichern unter", f"{self.get_base_path()}/results/pv_results.csv", "CSV-Dateien (*.csv)")

            if not output_filename:
                return

            # Assume we have a pre-defined path to the TRY data file
            try_data_file = f"{self.data_manager.get_try_filename()}"

            if not try_data_file:
                return

            results = []

            # Clear the existing Tree View before recalculating
            self.data_vis_tab.treeWidget.clear()

            # Loop through each building and each roof for calculation
            for parent_id, building_info in self.data_model.building_info.items():
                building_item = self.data_vis_tab.add_building(building_info['Adresse'], building_info['Koordinate_X'], building_info['Koordinate_Y'])
                for roof in building_info.get('Roofs', []):
                    roof_areas = roof['Area'] if isinstance(roof['Area'], list) else [roof['Area']]
                    roof_slopes = roof['Roof_Slope'] if isinstance(roof['Roof_Slope'], list) else [roof['Roof_Slope']]
                    roof_orientations = roof['Roof_Orientation'] if isinstance(roof['Roof_Orientation'], list) else [roof['Roof_Orientation']]

                    for i in range(len(roof_areas)):
                        roof_area = float(roof_areas[i])
                        roof_slope = float(roof_slopes[i])
                        roof_orientation = float(roof_orientations[i])

                        # Calculate PV for the current roof segment
                        yield_kWh, max_power, _ = Calculate_PV(
                            try_data_file,
                            Gross_area=roof_area,
                            Longitude=building_info['Koordinate_X'],
                            STD_Longitude=15,  # Replace with the correct standard longitude
                            Latitude=building_info['Koordinate_Y'],
                            Albedo=0.2,  # Example albedo value, adjust as necessary
                            East_West_collector_azimuth_angle=roof_orientation,
                            Collector_tilt_angle=roof_slope
                        )

                        results.append({
                            'Building': building_info['Adresse'],
                            'Roof Area (m²)': roof_area,
                            'Slope (°)': roof_slope,
                            'Orientation (°)': roof_orientation,
                            'Yield (kWh)': yield_kWh,
                            'Max Power (kW)': max_power
                        })

                        # Add roof details as a child item to the building in the tree view
                        self.data_vis_tab.add_roof(building_item, roof_area, roof_slope, roof_orientation, yield_kWh, max_power)

            # Save results to CSV
            results_df = pd.DataFrame(results)
            results_df.to_csv(output_filename, index=False, sep=';')

            QMessageBox.information(self, "Berechnung abgeschlossen", f"PV-Ertragsberechnung erfolgreich abgeschlossen.\nErgebnisse gespeichert in: {output_filename}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler bei der Berechnung: {str(e)}")
