"""
Filename: lod2_presenter.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-02
Description: Contains the presenter class for the LOD2 data visualization.
"""

from PyQt5.QtWidgets import ( QFileDialog, QDialog, QMessageBox)
from PyQt5.QtCore import pyqtSignal, QObject

from districtheatingsim.gui.LOD2Tab.lod2_dialogs import FilterDialog

import traceback

class DataVisualizationPresenter(QObject):
    """
    The presenter class for managing the interaction between the model and the view in the LOD2 data visualization.
    """
    data_loaded = pyqtSignal(dict)

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initializes the DataVisualizationPresenter with references to the model, view, folder manager, and data manager.

        Args:
            model (LOD2DataModel): The data model.
            view (LOD2DataVisualizationTab): The view component.
            folder_manager (FolderManager): The folder manager.
            data_manager (DataManager): The data manager.
        """
        super().__init__()
        self.model = model
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        self.folder_manager.project_folder_changed.connect(self.on_project_folder_changed)
        self.on_project_folder_changed(self.folder_manager.variant_folder)

        self.connect_signals()

    def on_project_folder_changed(self, new_base_path):
        """
        Updates the base path in the model when the project folder changes.

        Args:
            new_base_path (str): The new base path.
        """
        self.model.set_base_path(new_base_path)
        self.model.populateComboBoxes()  # Populate ComboBox data

    def connect_signals(self):
        """
        Connects view signals to presenter slots.
        """
        self.view.data_selected.connect(self.highlight_building_3d)
        self.view.building_type_changed.connect(self.update_building_subtypes)
        self.view.building_state_changed.connect(self.update_data_value)
        self.view.combobox_changed.connect(self.update_data_value)
        self.view.data_changed.connect(self.update_data_value)
        self.model.data_updated.connect(self.refresh_view)  # Reaktion auf Model-Änderungen

    def update_data_value(self, row, key, value):
        """
        Aktualisiert das Model mit neuen Werten aus der View.

        Args:
            row (int): Die Zeilenindex des Gebäudes.
            key (str): Der interne Key im Model.
            value (str): Der neue Wert.
        """
        self.model.update_data_value(row, key, value)

    def refresh_view(self):
        """
        Aktualisiert die View nach einer Änderung im Model.
        """
        self.view.update_table(
            self.model.building_info, 
            self.model.get_building_types(), 
            self.model.tabula_building_types, 
            self.model.building_subtypes
        )

    def show_filter_dialog(self):
        """
        Shows the filter dialog for LOD2 data filtering.
        """
        dialog = FilterDialog(self.model.get_base_path(), self.config_manager, self.view)
        if dialog.exec_() == QDialog.Accepted:
            filter_method = dialog.filterMethodComboBox.currentText()
            lod_geojson_path = dialog.inputLOD2geojsonLineEdit.text()

            if filter_method == "Filter by Polygon":
                filter_file_path = dialog.inputfilterPolygonLineEdit.text()
            elif filter_method == "Filter by Building Data CSV":
                filter_file_path = dialog.inputfilterBuildingDataLineEdit.text()
                
            output_geojson_path = dialog.outputLOD2geojsonLineEdit.text()

            self.model.filter_data(filter_method, lod_geojson_path, filter_file_path, output_geojson_path)
            self.model.process_data(output_geojson_path)

            # Überprüfen und Laden der U-Werte direkt nach dem Laden der Daten
            self.model.check_and_load_u_values()

            self.view.update_table(
                self.model.building_info, 
                self.model.get_building_types(), 
                self.model.tabula_building_types,  # Dieser Wert war vorher ausgelassen
                self.model.building_subtypes
            )
            self.view.update_3d_view(self.model.building_info)

    def calculate_heat_demand(self):
        """
        Calculates the heat demand for each building.
        """
        # takes the TRY file from the data manager, could also be implemented as a file dialog
        self.model.try_filename = self.data_manager.get_try_filename()
        self.model.calculate_heat_demand()
        self.view.update_table(self.model.building_info, self.model.get_building_types(), self.model.tabula_building_types, self.model.building_subtypes)

    def create_building_csv(self):
        """
        Creates a CSV file for building data.
        """
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.get_base_path(), "CSV-Dateien (*.csv)")
        if path:
            self.model.create_building_csv(path)

    def highlight_building_3d(self, col):
        """
        Highlight the selected building in the 3D view.

        Args:
            col (int): The column index of the selected building.
        """
        parent_id = list(self.model.building_info.keys())[col]
        self.view.highlight_building_3d(parent_id)

    def update_building_subtypes(self, row):
        """
        Aktualisiert die Subtypen-ComboBox basierend auf dem gewählten Gebäudetyp SLP.

        Args:
            row (int): Die Zeilenindex des Gebäudes.
        """
        building_type = self.view.get_combobox_building_type(row)
        subtypes = self.model.get_building_subtypes(building_type)

        # **Subtypen-Liste in der View aktualisieren**
        self.view.update_subtype_combobox(row, subtypes)

        # **Den neuen Gebäudetyp SLP auch im Modell speichern**
        self.model.update_data_value(row, "Gebäudetyp", building_type)

    def save_data_as_geojson(self):
        """
        Collects data from the view and passes it to the model for saving.
        """
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.output_geojson_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                # Übergabe der Daten an das Model zur Speicherung
                self.model.save_data_as_geojson(path)

                QMessageBox.information(self.view, "Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")
            except Exception as e:
                QMessageBox.critical(self.view, "Fehler beim Speichern", f"Ein Fehler ist beim Speichern aufgetreten: {str(e)}")

    def load_data_from_file(self):
        """
        Loads data from a GeoJSON file.
        """
        path, _ = QFileDialog.getOpenFileName(self.view, "Öffnen", self.model.get_base_path(), "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                # Process the data (this includes functions like process_lod2 and calculate_centroid_and_geocode)
                self.model.process_data(path)
                
                # Update the view with the processed data
                self.view.update_table(
                    self.model.building_info, 
                    self.model.get_building_types(), 
                    self.model.tabula_building_types, 
                    self.model.building_subtypes
                )
                self.view.update_3d_view(self.model.building_info)
            
            except Exception as e:
                # add traceback to error message
                error_message = f"Failed to load or process data: {str(e)}\n\n{traceback.format_exc()}"
                self.view.show_info_message("Error", error_message)