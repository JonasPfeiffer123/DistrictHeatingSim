"""
LOD2 Presenter Module
====================

Presenter class for managing LOD2 data visualization model-view interactions.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-03
"""

from PyQt6.QtWidgets import ( QFileDialog, QDialog, QMessageBox, QTreeWidgetItem)
from PyQt6.QtCore import pyqtSignal, QObject

from districtheatingsim.gui.LOD2Tab.lod2_dialogs import FilterDialog

import traceback

class DataVisualizationPresenter(QObject):
    """
    Presenter class for managing LOD2 data visualization model-view interactions.
    """
    data_loaded = pyqtSignal(dict)

    def __init__(self, model, view, folder_manager, data_manager, config_manager):
        """
        Initialize LOD2 data visualization presenter.

        Parameters
        ----------
        model : LOD2DataModel
            Data model instance.
        view : LOD2DataVisualizationTab
            View component instance.
        folder_manager : FolderManager
            Folder manager instance.
        data_manager : DataManager
            Data manager instance.
        config_manager : ConfigManager
            Configuration manager instance.
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
        Update model base path when project folder changes.

        Parameters
        ----------
        new_base_path : str
            New base path.
        """
        self.model.set_base_path(new_base_path)
        self.model.populateComboBoxes()

    def connect_signals(self):
        """Connect view signals to presenter slots."""
        self.view.data_selected.connect(self.highlight_building_3d)
        self.view.building_type_changed.connect(self.update_building_subtypes)
        self.view.building_state_changed.connect(self.update_data_value)
        self.view.combobox_changed.connect(self.update_data_value)
        self.view.data_changed.connect(self.update_data_value)
        self.view.pv_tab.treeWidget.itemSelectionChanged.connect(self.on_tree_item_selected)
        self.model.data_updated.connect(self.refresh_view)

    def update_data_value(self, row, key, value):
        """
        Update model with new values from view.

        Parameters
        ----------
        row : int
            Building row index.
        key : str
            Internal model key.
        value : str
            New value.
        """
        self.model.update_data_value(row, key, value)

    def refresh_view(self):
        """Refresh view after model changes."""
        self.view.update_table(
            self.model.building_info, 
            self.model.get_building_types(), 
            self.model.tabula_building_types, 
            self.model.building_subtypes
        )

    def show_filter_dialog(self):
        """Show LOD2 data filter dialog."""
        dialog = FilterDialog(self.model.get_base_path(), self.config_manager, self.view)
        if dialog.exec() == QDialog.Accepted:
            filter_method = dialog.filterMethodComboBox.currentText()
            lod_geojson_path = dialog.inputLOD2geojsonLineEdit.text()

            if filter_method == "Filter by Polygon":
                filter_file_path = dialog.inputfilterPolygonLineEdit.text()
            elif filter_method == "Filter by Building Data CSV":
                filter_file_path = dialog.inputfilterBuildingDataLineEdit.text()
                
            output_geojson_path = dialog.outputLOD2geojsonLineEdit.text()

            self.model.filter_data(filter_method, lod_geojson_path, filter_file_path, output_geojson_path)
            self.model.process_data(output_geojson_path)
            self.model.check_and_load_u_values()

            self.view.update_table(
                self.model.building_info, 
                self.model.get_building_types(), 
                self.model.tabula_building_types,
                self.model.building_subtypes
            )
            self.view.update_3d_view(self.model.building_info)

    def calculate_heat_demand(self):
        """Calculate heat demand for each building."""
        self.model.try_filename = self.data_manager.get_try_filename()
        self.model.calculate_heat_demand()
        self.view.update_table(self.model.building_info, self.model.get_building_types(), self.model.tabula_building_types, self.model.building_subtypes)

    def create_building_csv(self):
        """Create CSV file for building data."""
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.get_base_path(), "CSV-Dateien (*.csv)")
        if path:
            self.model.create_building_csv(path)

    def highlight_building_3d(self, col):
        """
        Highlight selected building in 3D view.

        Parameters
        ----------
        col : int
            Column index of selected building.
        """
        parent_id = list(self.model.building_info.keys())[col]
        self.view.highlight_building_3d(parent_id)

    def update_building_subtypes(self, row):
        """
        Update subtype ComboBox based on selected building type.

        Parameters
        ----------
        row : int
            Building row index.
        """
        building_type = self.view.get_combobox_building_type(row)
        subtypes = self.model.get_building_subtypes(building_type)

        self.view.update_subtype_combobox(row, subtypes)
        self.model.update_data_value(row, "Gebäudetyp", building_type)

    def calculate_pv_data(self, output_filename):
        """
        Calculate PV data for each building and roof.

        Parameters
        ----------
        output_filename : str
            Output file path for PV results.
        """
        try:
            self.model.try_filename = self.data_manager.get_try_filename()
            self.model.calculate_pv_data(output_filename)
            self.view.update_pv_tab(self.model.pv_results)
            self.view.show_info_message("PV-Daten berechnet", f"PV-Daten wurden erfolgreich berechnet und gespeichert unter: {output_filename}")
        except Exception as e:
            self.view.show_info_message("Fehler", f"Fehler bei der Berechnung: {str(e)}\n{traceback.format_exc()}")

    def on_tree_item_selected(self):
        """Handle tree item selection events."""
        selected_items = self.view.pv_tab.treeWidget.selectedItems()
        if selected_items:
            self.highlight_roof_3d(selected_items[0])

    def highlight_roof_3d(self, item):
        """
        Highlight specific building or roof in 3D plot based on selected tree item.

        Parameters
        ----------
        item : QTreeWidgetItem
            Selected tree item.
        """
        if isinstance(item, QTreeWidgetItem):
            if item.parent() is None:
                roof_name = item.text(0)
                parent_id = self.find_parent_id(roof_name)
                self.view.highlight_building_3d(parent_id, True, None, self.model.roof_info)
            else:
                parent_item = item.parent()
                roof_name = parent_item.text(0)
                roof_index = parent_item.indexOfChild(item)
                parent_id = self.find_parent_id(roof_name)
                self.view.highlight_building_3d(parent_id, True, roof_index, self.model.roof_info)
        else:
            self.view.highlight_building_3d(item, True, None, self.model.roof_info)

    def find_parent_id(self, roof_name):
        """
        Find parent ID associated with roof name.

        Parameters
        ----------
        roof_name : str
            Name of the roof.

        Returns
        -------
        str
            Parent ID corresponding to the roof.
        """
        for parent_id, info in self.model.roof_info.items():
            if info['Adresse'] == roof_name:
                return parent_id
        return None
    
    def save_data_as_geojson(self):
        """Save building data as GeoJSON file."""
        path, _ = QFileDialog.getSaveFileName(self.view, "Speichern unter", self.model.output_geojson_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                self.model.save_data_as_geojson(path)
                QMessageBox.information(self.view, "Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")
            except Exception as e:
                QMessageBox.critical(self.view, "Fehler beim Speichern", f"Ein Fehler ist beim Speichern aufgetreten: {str(e)}")

    def load_data_from_file(self):
        """Load building data from GeoJSON file."""
        path, _ = QFileDialog.getOpenFileName(self.view, "Öffnen", self.model.get_base_path(), "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                self.model.process_data(path)
                
                self.view.update_table(
                    self.model.building_info, 
                    self.model.get_building_types(), 
                    self.model.tabula_building_types, 
                    self.model.building_subtypes
                )

                self.view.display_data(self.model.roof_info)
                self.view.update_3d_view(self.model.building_info)
            
            except Exception as e:
                error_message = f"Failed to load or process data: {str(e)}\n\n{traceback.format_exc()}"
                self.view.show_info_message("Error", error_message)