"""
Filename: lod2_visualization.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-28
Description: Contains the view class for LOD2 data visualization.
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (
    QVBoxLayout, QComboBox, QWidget, QTableWidget, QTableWidgetItem, 
    QHeaderView, QHBoxLayout, QScrollArea, QMessageBox, QTabWidget
)
from PyQt5.QtCore import pyqtSignal
from districtheatingsim.gui.LOD2Tab.lod2_3d_plot_matplotlib import LOD2Visualization3D

class LOD2DataVisualization(QWidget):
    """
    The view class for LOD2 data visualization.
    """
    data_selected = pyqtSignal(int)
    u_value_updated = pyqtSignal(int)
    building_type_changed = pyqtSignal(int, str, str)
    building_state_changed = pyqtSignal(int, str, str)  # Neu: Signal für Änderungen am Gebäudezustand
    combobox_changed = pyqtSignal(int, str, str)  # Zeile, Key, Wert für ComboBoxen
    data_changed = pyqtSignal(int, str, object)  # Zeile, Key, Wert

    def __init__(self, parent=None):
        """
        Initializes the LOD2DataVisualization with UI components.

        Args:
            parent (QWidget, optional): The parent widget.
        """
        super().__init__(parent)
        self.comboBoxBuildingTypesItems = []
        self.building_types = []
        self.building_subtypes = {}
        
        self.initUI()

        self.visualization_3d = LOD2Visualization3D(self.canvas_3d)  # Initialize the 3D visualization handler

        self.COLUMN_MAPPING = {
            "Adresse": "Adresse",
            "Koordinate_X": "UTM_X (m)",
            "Koordinate_Y": "UTM_Y (m)",
            "Ground_Area": "Grundfläche (m²)",
            "Wall_Area": "Wandfläche (m²)",
            "Roof_Area": "Dachfläche (m²)",
            "Volume": "Volumen (m³)",
            "Stockwerke": "Stockwerke",
            "Gebäudetyp": "Gebäudetyp SLP",
            "Subtyp": "Subtyp SLP",
            "Typ": "Gebäudetyp TABULA",
            "Gebäudezustand": "Gebäudezustand TABULA",
            "ww_demand_kWh_per_m2": "WW-Bedarf (kWh/m²)",
            "air_change_rate": "Luftwechselrate (1/h)",
            "fracture_windows": "Fensteranteil (%)",
            "fracture_doors": "Türanteil (%)",
            "Normaußentemperatur": "Normaußentemperatur (°C)",
            "room_temp": "Raumtemperatur (°C)",
            "max_air_temp_heating": "Heizgrenztemperatur (°C)",
            "Typ_Heizflächen": "Typ Heizflächen",
            "VLT_max": "VLT max (°C)",
            "Steigung_Heizkurve": "Steigung Heizkurve",
            "RLT_max": "RLT max (°C)",
            "wall_u": "U-Wert Wand (W/m²K)",
            "roof_u": "U-Wert Dach (W/m²K)",
            "window_u": "U-Wert Fenster (W/m²K)",
            "door_u": "U-Wert Tür (W/m²K)",
            "ground_u": "U-Wert Boden (W/m²K)",
            "Wärmebedarf": "Wärmebedarf (kWh)",
            "Warmwasseranteil": "Warmwasseranteil (%)"
        }

    def initUI(self):
        """
        Initializes the UI components of the LOD2DataVisualization.
        """
        main_layout = QVBoxLayout(self)
        data_vis_layout = QHBoxLayout()
        main_layout.addLayout(data_vis_layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        data_vis_layout.addWidget(scroll_area)

        scroll_content = QWidget(scroll_area)
        scroll_area.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(scroll_content)

        # Tabs für kategorisierte Daten
        self.tabs = QTabWidget()
        scroll_layout.addWidget(self.tabs)

        # Kategorien definieren
        self.categories = {
            "Lage und Geometrie": ['Adresse', 'UTM_X (m)', 'UTM_Y (m)', 'Grundfläche (m²)', 'Wandfläche (m²)', 'Dachfläche (m²)', 'Volumen (m³)', 'Stockwerke'],
            "Energiebedarf und Nutzung": ['Adresse', 'Gebäudetyp SLP', 'Subtyp SLP', 'WW-Bedarf (kWh/m²)', 'Typ Heizflächen', 'VLT max (°C)', 'Steigung Heizkurve', 'RLT max (°C)', 'Normaußentemperatur (°C)'],
            "Gebäudehülle und Typ": ['Adresse', 'Gebäudetyp TABULA', 'Gebäudezustand TABULA', 'U-Wert Wand (W/m²K)', 'U-Wert Dach (W/m²K)', 'U-Wert Fenster (W/m²K)', 'U-Wert Tür (W/m²K)', 'U-Wert Boden (W/m²K)'],
            "Zusätzliche Eingaben": ['Adresse', 'Luftwechselrate (1/h)', 'Fensteranteil (%)', 'Türanteil (%)', 'Raumtemperatur (°C)', 'Heizgrenztemperatur (°C)'], # umbennen in Heizgrenztempertur
            "Ergebnisse": ['Adresse', 'Wärmebedarf (kWh)', 'Warmwasseranteil (%)']
        }

    	# Tabellen für die Kategorien erstellen
        self.tables = {}
        for category, headers in self.categories.items():
            table = QTableWidget()
            table.setColumnCount(len(headers))
            table.setRowCount(0)
            table.setHorizontalHeaderLabels(headers)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            table.setSortingEnabled(False)

            # Verbindung zu itemChanged, damit Änderungen im UI direkt ins Datenmodell übernommen werden
            table.itemChanged.connect(self.on_item_changed)

            self.tables[category] = table
            self.tables[category].itemSelectionChanged.connect(self.on_table_row_select)
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.addWidget(table)
            tab.setLayout(tab_layout)
            self.tabs.addTab(tab, category)

        # 3D-Plot
        self.figure_3d = plt.figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.canvas_3d.setMinimumSize(800, 800)
        data_vis_layout.addWidget(self.canvas_3d)

    def on_table_row_select(self):
        """
        Handles the event when a table row is selected.
        """
        for category, table in self.tables.items():
            selected_rows = table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                self.data_selected.emit(row)  # Emit the signal to inform the presenter

    def on_item_changed(self, item):
        """
        Synchronisiert Änderungen aus der Tabelle mit dem internen Datenmodell.

        Args:
            item (QTableWidgetItem): Das geänderte Item.
        """
        table = item.tableWidget()
        category = next((cat for cat, tbl in self.tables.items() if tbl == table), None)
        if not category:
            return  # Sollte nicht passieren

        row = item.row()
        col = item.column()
        gui_label = table.horizontalHeaderItem(col).text()

        internal_key = next((key for key, value in self.COLUMN_MAPPING.items() if value == gui_label), None)
        if not internal_key:
            return

        value = item.text()

        # Konvertiere numerische Werte in den passenden Typ
        try:
            if "." in value:
                value = float(value)  # 🔹 Wandelt in `float` um
            else:
                value = int(value)  # 🔹 Wandelt in `int` um
        except ValueError:
            pass  # 🔹 Falls kein numerischer Wert, bleibt es `str`

        self.data_changed.emit(row, internal_key, value)  # Jetzt mit `object` als dritten Parameter

    def on_combobox_changed(self, row, key, comboBox):
        """
        Synchronisiert Änderungen aus der ComboBox mit dem Presenter.

        Args:
            row (int): Die Zeilenindex des Gebäudes.
            key (str): Der interne Schlüssel im Datenmodell.
            comboBox (QComboBox): Die ComboBox, die geändert wurde.
        """
        value = comboBox.currentText()
        self.combobox_changed.emit(row, key, value)  # Signal an Presenter senden

    def update_table(self, building_info, comboBoxBuildingTypesItems, building_types, building_subtypes):
        """
        Update the table with new data.

        Args:
            building_info (dict): A dictionary containing building information.
            comboBoxBuildingTypesItems (list): A list of items for the building types ComboBox.
            building_types (list): A list of building types.
            building_subtypes (dict): A dictionary mapping building types to their subtypes.
        """
        self.comboBoxBuildingTypesItems = comboBoxBuildingTypesItems
        self.building_types = building_types
        self.building_subtypes = building_subtypes

        for category, table in self.tables.items():
            table.setRowCount(len(building_info))
            table.setVerticalHeaderLabels([str(i + 1) for i in range(len(building_info))])

        for row, (parent_id, info) in enumerate(building_info.items()):
            self.update_table_row(row, info)

    def update_table_row(self, row, info):
        """
        Aktualisiert eine Zeile in den Tabellen mit den korrekten Spaltennamen.

        Args:
            row (int): Die Zeilenindex des Gebäudes.
            info (dict): Das Gebäudeinformations-Dictionary.
        """
        for category, table in self.tables.items():
            for col in range(table.columnCount()):
                gui_label = table.horizontalHeaderItem(col).text()

                # Suche das passende interne Datenfeld mit dem Mapping
                internal_key = next((key for key, value in self.COLUMN_MAPPING.items() if value == gui_label), None)

                if internal_key:
                    value = info.get(internal_key, "-")


                    # **Gebäudetyp SLP → Subtyp anpassen**
                    if gui_label == "Gebäudetyp SLP":
                        comboBoxSLPTypes = QComboBox()
                        comboBoxSLPTypes.addItems(self.comboBoxBuildingTypesItems)
                        comboBoxSLPTypes.setCurrentText(str(value))
                        
                        # Signal für Änderung Gebäudetyp SLP → ruft update_building_subtypes() im Presenter auf
                        comboBoxSLPTypes.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.building_type_changed.emit(r, k, comboBoxSLPTypes.currentText()))
                        
                        table.setCellWidget(row, col, comboBoxSLPTypes)

                    elif gui_label == "Subtyp SLP":
                        comboBoxSLPSubtypes = QComboBox()
                        # Die verfügbaren Subtypen basieren auf dem Gebäudetyp SLP
                        geb_typ = info.get("Gebäudetyp", "")
                        comboBoxSLPSubtypes.addItems(self.building_subtypes.get(geb_typ, []))
                        comboBoxSLPSubtypes.setCurrentText(str(value))

                        # Änderungen sofort speichern
                        comboBoxSLPSubtypes.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.combobox_changed.emit(r, k, comboBoxSLPSubtypes.currentText()))

                        table.setCellWidget(row, col, comboBoxSLPSubtypes)

                    # **TABULA-Gebäudetyp → U-Werte aktualisieren**
                    elif gui_label == "Gebäudetyp TABULA":
                        comboBoxBuildingTypes = QComboBox()
                        comboBoxBuildingTypes.addItems(self.building_types)
                        comboBoxBuildingTypes.setCurrentText(str(value))

                        # Signal für Änderung Gebäudetyp TABULA → ruft update_u_values() im Presenter auf
                        comboBoxBuildingTypes.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.building_state_changed.emit(r, k, comboBoxBuildingTypes.currentText()))
                        
                        table.setCellWidget(row, col, comboBoxBuildingTypes)

                    # **Gebäudezustand TABULA → U-Werte aktualisieren**
                    elif gui_label == "Gebäudezustand TABULA":
                        comboBoxBuildingState = QComboBox()
                        comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment", "Individuell"])
                        comboBoxBuildingState.setCurrentText(str(value))

                        # Signal für Änderung Gebäudezustand → ruft update_u_values() im Presenter auf
                        comboBoxBuildingState.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.building_state_changed.emit(r, k, comboBoxBuildingState.currentText()))
                        
                        table.setCellWidget(row, col, comboBoxBuildingState)

                    else:
                        # Setze reguläre Werte
                        if isinstance(value, float):
                            table.setItem(row, col, QTableWidgetItem(f"{value:.2f}"))
                        else:
                            table.setItem(row, col, QTableWidgetItem(str(value)))

    def update_subtype_combobox(self, row, subtypes):
        """
        Update the subtype ComboBox with the new subtypes.

        Args:
            col (int): The row index of the ComboBox.
            subtypes (list): A list of subtypes to populate the ComboBox.
        """
        comboBoxSubtypes = self.tables["Energiebedarf und Nutzung"].cellWidget(row, 2)
        comboBoxSubtypes.clear()
        comboBoxSubtypes.addItems(subtypes)

    def get_tabula_building_type(self, row):
        """
        Returns the currently selected TABULA building type from the ComboBox.

        Args:
            row (int): The row index of the building type ComboBox.

        Returns:
            str: The selected TABULA building type.
        """
        return self.tables["Gebäudehülle und Typ"].cellWidget(row, 1).currentText()

    def get_building_state(self, row):
        """
        Returns the currently selected building state from the ComboBox.

        Args:
            row (int): The row index of the building state ComboBox.

        Returns:
            str: The selected building state.
        """
        return self.tables["Gebäudehülle und Typ"].cellWidget(row, 2).currentText()

    def get_combobox_building_type(self, row):
        """
        Returns the current building type from the ComboBox.

        Args:
            row (int): The row index of the building type ComboBox.

        Returns:
            str: The current building type selected in the ComboBox.
        """
        return self.tables["Energiebedarf und Nutzung"].cellWidget(row, 1).currentText()

    def update_3d_view(self, building_info):
        """
        Delegate the update of the 3D view to the LOD2Visualization3D class.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        self.visualization_3d.update_3d_view(building_info)

    def highlight_building_3d(self, parent_id):
        """
        Highlights a building in the 3D plot.

        Args:
            parent_id (str): The ID of the building to highlight.
        """
        self.visualization_3d.highlight_building_3d(parent_id)

    def show_info_message(self, title, message):
        """
        Displays an informational message box.

        Args:
            title (str): The title of the message box.
            message (str): The message to be displayed.
        """
        QMessageBox.information(self, title, message)