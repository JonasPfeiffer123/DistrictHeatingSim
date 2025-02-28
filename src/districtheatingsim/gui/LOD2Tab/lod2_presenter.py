"""
Filename: lod2_presenter.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-28
Description: Contains the presenter class for the LOD2 data visualization.
"""

from PyQt5.QtWidgets import ( QFileDialog, QDialog, QMessageBox)
from PyQt5.QtCore import pyqtSignal, QObject

from districtheatingsim.gui.LOD2Tab.lod2_dialogs import FilterDialog

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
        self.view.u_value_updated.connect(self.update_u_values)
        self.view.building_type_changed.connect(self.update_u_values)  # Neu: Reagiert auf Änderungen am Gebäudetyp
        self.view.building_state_changed.connect(self.update_u_values)  # Neu: Reagiert auf Änderungen am Gebäudezustand

    def load_data_from_file(self):
        """
        Loads data from a GeoJSON file.
        """
        path, _ = QFileDialog.getOpenFileName(self.view, "Öffnen", self.model.get_base_path(), "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                # Process the data (this includes functions like process_lod2 and calculate_centroid_and_geocode)
                self.model.process_data(path)
                
                # Überprüfen und Laden der U-Werte direkt nach dem Laden der Daten
                for parent_id, info in self.model.building_info.items():
                    self.model.check_and_load_u_values(info)
                
                # Update the view with the processed data
                self.view.update_table(
                    self.model.building_info, 
                    self.model.get_building_types(), 
                    self.model.tabula_building_types, 
                    self.model.building_subtypes
                )
                self.view.update_3d_view(self.model.building_info)
            
            except Exception as e:
                self.view.show_info_message("Error", f"Failed to load or process data: {str(e)}")

    def save_data_as_geojson(self):
        """
        Collects data from the view and passes it to the model for saving.
        """
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.output_geojson_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                # Daten aus der View (QTableWidget) sammeln
                data_from_view = self.collect_data_from_view()

                # Übergabe der Daten an das Model zur Speicherung
                self.model.save_data_as_geojson(path, data_from_view)

                QMessageBox.information(self.view, "Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")
            except Exception as e:
                QMessageBox.critical(self.view, "Fehler beim Speichern", f"Ein Fehler ist beim Speichern aufgetreten: {str(e)}")

    def collect_data_from_view(self):
        """
        Collects data from the QTableWidget in the view.

        Returns:
            list: A list of dictionaries representing the collected data.
        """
        data = []
        for col in range(self.view.tableWidget.columnCount()):
            column_data = {
                'Adresse': self.view.tableWidget.item(0, col).text().split(", ")[0],
                'Stadt': self.view.tableWidget.item(0, col).text().split(", ")[1],
                'Bundesland': self.view.tableWidget.item(0, col).text().split(", ")[2],
                'Land': self.view.tableWidget.item(0, col).text().split(", ")[3],
                'Koordinate_X': float(self.view.tableWidget.item(1, col).text()),
                'Koordinate_Y': float(self.view.tableWidget.item(2, col).text()),
                'Ground_Area': float(self.view.tableWidget.item(3, col).text()),
                'Wall_Area': float(self.view.tableWidget.item(4, col).text()),
                'Roof_Area': float(self.view.tableWidget.item(5, col).text()),
                'Volume': float(self.view.tableWidget.item(6, col).text()),
                'Stockwerke': int(self.view.tableWidget.item(7, col).text()) if self.view.tableWidget.item(7, col) else None,
                'Gebäudetyp': self.view.tableWidget.cellWidget(8, col).currentText(),
                'Subtyp': self.view.tableWidget.cellWidget(9, col).currentText(),
                'Typ': self.view.tableWidget.cellWidget(10, col).currentText(),
                'Gebäudezustand': self.view.tableWidget.cellWidget(11, col).currentText(),
                'ww_demand_kWh_per_m2': float(self.view.tableWidget.item(12, col).text()) if self.view.tableWidget.item(12, col) else None,
                'air_change_rate': float(self.view.tableWidget.item(13, col).text()) if self.view.tableWidget.item(13, col) else None,
                'fracture_windows': float(self.view.tableWidget.item(14, col).text()) if self.view.tableWidget.item(14, col) else None,
                'fracture_doors': float(self.view.tableWidget.item(15, col).text()) if self.view.tableWidget.item(15, col) else None,
                'Normaußentemperatur': float(self.view.tableWidget.item(16, col).text()) if self.view.tableWidget.item(16, col) else None,
                'room_temp': float(self.view.tableWidget.item(17, col).text()) if self.view.tableWidget.item(17, col) else None,
                'max_air_temp_heating': float(self.view.tableWidget.item(18, col).text()) if self.view.tableWidget.item(18, col) else None,
                'Typ_Heizflächen': self.view.tableWidget.item(24, col).text() if self.view.tableWidget.item(24, col) else None,
                'VLT_max': float(self.view.tableWidget.item(25, col).text()) if self.view.tableWidget.item(25, col) else None,
                'Steigung_Heizkurve': float(self.view.tableWidget.item(26, col).text()) if self.view.tableWidget.item(26, col) else None,
                'RLT_max': float(self.view.tableWidget.item(27, col).text()) if self.view.tableWidget.item(27, col) else None,
                'Wärmebedarf': float(self.view.tableWidget.item(28, col).text()) if self.view.tableWidget.item(28, col) else None,
                'Warmwasseranteil': float(self.view.tableWidget.item(29, col).text()) if self.view.tableWidget.item(29, col) else None,
                'wall_u': float(self.view.tableWidget.item(19, col).text()) if self.view.tableWidget.item(19, col) else None,
                'roof_u': float(self.view.tableWidget.item(20, col).text()) if self.view.tableWidget.item(20, col) else None,
                'window_u': float(self.view.tableWidget.item(21, col).text()) if self.view.tableWidget.item(21, col) else None,
                'door_u': float(self.view.tableWidget.item(22, col).text()) if self.view.tableWidget.item(22, col) else None,
                'ground_u': float(self.view.tableWidget.item(23, col).text()) if self.view.tableWidget.item(23, col) else None,
            }
            data.append(column_data)
        return data

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
            for parent_id, info in self.model.building_info.items():
                self.model.check_and_load_u_values(info)

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

    def update_building_subtypes(self, col):
        """
        Updates the subtypes ComboBox based on the selected building type.

        Args:
            col (int): The column index of the selected building.
        """
        building_type = self.view.get_combobox_building_type(col)
        subtypes = self.model.get_building_subtypes(building_type)
        self.view.update_subtype_combobox(col, subtypes)

    def update_u_values(self, col):
        """
        Update U-values when the user interacts with the ComboBoxes in the view.

        Args:
            col (int): The column index of the selected building.
        """
        # Aktuelle Auswahl für Gebäudetyp und Gebäudezustand TABULA abrufen
        building_type = self.view.get_tabula_building_type(col)
        building_state = self.view.get_building_state(col)

        # U-Werte basierend auf der Auswahl neu laden
        wall_u, roof_u, window_u, door_u, ground_u = self.model.get_u_values(building_type, building_state)

        # Aktualisieren der Werte im `info`-Daten
        parent_id = list(self.model.building_info.keys())[col]
        info = self.model.building_info[parent_id]
        info['wall_u'] = wall_u
        info['roof_u'] = roof_u
        info['window_u'] = window_u
        info['door_u'] = door_u
        info['ground_u'] = ground_u

        # Aktualisieren der View
        self.view.update_u_values(col, info)