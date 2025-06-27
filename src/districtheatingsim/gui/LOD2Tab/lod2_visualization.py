"""
LOD2 Visualization Module
========================

Widget for visualizing and editing LOD2 building data with tabbed interface.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-02
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (
    QVBoxLayout, QComboBox, QWidget, QTableWidget, QTableWidgetItem, 
    QHeaderView, QHBoxLayout, QScrollArea, QMessageBox, QTabWidget
)
from PyQt5.QtCore import pyqtSignal
from districtheatingsim.gui.LOD2Tab.lod2_3d_plot_matplotlib import LOD2Visualization3D
from districtheatingsim.gui.LOD2Tab.lod2_pv_tab import PVDataVisualizationTab

class LOD2DataVisualization(QWidget):
    """
    Widget for visualizing and editing LOD2 building data with tabbed interface.
    """
    data_selected = pyqtSignal(int)
    building_type_changed = pyqtSignal(int, str, str)
    building_state_changed = pyqtSignal(int, str, str)
    combobox_changed = pyqtSignal(int, str, str)
    data_changed = pyqtSignal(int, str, object)

    def __init__(self, parent=None):
        """
        Initialize LOD2 data visualization widget.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.comboBoxBuildingTypesItems = []
        self.building_types = []
        self.building_subtypes = {}
        
        self.initUI()

        self.visualization_3d = LOD2Visualization3D(self.canvas_3d)

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
            "WW_Anteil": "Warmwasseranteil (%)"
        }

    def initUI(self):
        """Initialize user interface components."""
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
            "Zusätzliche Eingaben": ['Adresse', 'Luftwechselrate (1/h)', 'Fensteranteil (%)', 'Türanteil (%)', 'Raumtemperatur (°C)', 'Heizgrenztemperatur (°C)'],
            "Ergebnisse Wärmebedarfe": ['Adresse', 'Wärmebedarf (kWh)', 'Warmwasseranteil (%)']
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

            table.itemChanged.connect(self.on_item_changed)

            self.tables[category] = table
            self.tables[category].itemSelectionChanged.connect(self.on_table_row_select)
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.addWidget(table)
            tab.setLayout(tab_layout)
            self.tabs.addTab(tab, category)

        # PV-Berechnung Tab
        self.pv_tab = PVDataVisualizationTab()
        self.tabs.addTab(self.pv_tab, "PV-Berechnung")

        # 3D-Plot
        self.figure_3d = plt.figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.canvas_3d.setMinimumSize(800, 800)
        data_vis_layout.addWidget(self.canvas_3d)

    def on_table_row_select(self):
        """Handle table row selection events."""
        for category, table in self.tables.items():
            selected_rows = table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                self.data_selected.emit(row)

    def on_item_changed(self, item):
        """
        Synchronize table changes with data model.

        Parameters
        ----------
        item : QTableWidgetItem
            Changed table item.
        """
        if self.updating_table:
            return
        
        table = item.tableWidget()
        category = next((cat for cat, tbl in self.tables.items() if tbl == table), None)
        if not category:
            return

        row = item.row()
        col = item.column()
        gui_label = table.horizontalHeaderItem(col).text()

        internal_key = next((key for key, value in self.COLUMN_MAPPING.items() if value == gui_label), None)
        if not internal_key:
            return

        value = item.text()

        try:
            if "." in value:
                value = float(value)
            else:
                value = int(value)
        except ValueError:
            pass

        self.data_changed.emit(row, internal_key, value)

    def on_combobox_changed(self, row, key, comboBox):
        """
        Synchronize ComboBox changes with presenter.

        Parameters
        ----------
        row : int
            Building row index.
        key : str
            Internal data key.
        comboBox : QComboBox
            Changed ComboBox widget.
        """
        value = comboBox.currentText()
        self.combobox_changed.emit(row, key, value)

    def update_table(self, building_info, comboBoxBuildingTypesItems, building_types, building_subtypes):
        """
        Update table with building data.

        Parameters
        ----------
        building_info : dict
            Building information dictionary.
        comboBoxBuildingTypesItems : list
            Building type ComboBox items.
        building_types : list
            Available building types.
        building_subtypes : dict
            Building subtypes by type.
        """
        self.comboBoxBuildingTypesItems = comboBoxBuildingTypesItems
        self.building_types = building_types
        self.building_subtypes = building_subtypes

        self.updating_table = True
        for category, table in self.tables.items():
            table.setRowCount(len(building_info))
            table.setVerticalHeaderLabels([str(i + 1) for i in range(len(building_info))])

        for row, (parent_id, info) in enumerate(building_info.items()):
            self.update_table_row(row, info)

        self.updating_table = False

    def update_table_row(self, row, info):
        """
        Update single table row with building information.

        Parameters
        ----------
        row : int
            Row index to update.
        info : dict
            Building information dictionary.
        """
        for category, table in self.tables.items():
            for col in range(table.columnCount()):
                gui_label = table.horizontalHeaderItem(col).text()
                internal_key = next((key for key, value in self.COLUMN_MAPPING.items() if value == gui_label), None)

                if internal_key:
                    value = info.get(internal_key, "-")

                    if gui_label == "Gebäudetyp SLP":
                        comboBoxSLPTypes = QComboBox()
                        comboBoxSLPTypes.addItems(self.comboBoxBuildingTypesItems)
                        if value is None or '':
                            value = "HMF"
                        else:
                            comboBoxSLPTypes.setCurrentText(str(value))
                        
                        comboBoxSLPTypes.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.building_type_changed.emit(r, k, comboBoxSLPTypes.currentText()))
                        table.setCellWidget(row, col, comboBoxSLPTypes)

                    elif gui_label == "Subtyp SLP":
                        comboBoxSLPSubtypes = QComboBox()
                        geb_typ = info.get("Gebäudetyp", "")
                        comboBoxSLPSubtypes.addItems(self.building_subtypes.get(geb_typ, []))
                        if value is None or '':
                            value = comboBoxSLPSubtypes.itemText(0)
                        else:
                            comboBoxSLPSubtypes.setCurrentText(str(value))

                        comboBoxSLPSubtypes.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.combobox_changed.emit(r, k, comboBoxSLPSubtypes.currentText()))
                        table.setCellWidget(row, col, comboBoxSLPSubtypes)

                    elif gui_label == "Gebäudetyp TABULA":
                        comboBoxBuildingTypes = QComboBox()
                        comboBoxBuildingTypes.addItems(self.building_types)
                        comboBoxBuildingTypes.setCurrentText(str(value))
                        comboBoxBuildingTypes.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.building_state_changed.emit(r, k, comboBoxBuildingTypes.currentText()))
                        table.setCellWidget(row, col, comboBoxBuildingTypes)

                    elif gui_label == "Gebäudezustand TABULA":
                        comboBoxBuildingState = QComboBox()
                        comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment", "Individuell"])
                        comboBoxBuildingState.setCurrentText(str(value))
                        comboBoxBuildingState.currentIndexChanged.connect(lambda idx, r=row, k=internal_key: self.building_state_changed.emit(r, k, comboBoxBuildingState.currentText()))
                        table.setCellWidget(row, col, comboBoxBuildingState)

                    elif gui_label == "Warmwasseranteil (%)" and isinstance(value, float) and isinstance(value, int):
                        table.setItem(row, col, QTableWidgetItem(f"{value*100:.2f}"))

                    else:
                        if isinstance(value, float):
                            table.setItem(row, col, QTableWidgetItem(f"{value:.2f}"))
                        else:
                            table.setItem(row, col, QTableWidgetItem(str(value)))

    def display_data(self, building_info):
        """
        Display building data in PV tab.
        
        Parameters
        ----------
        building_info : dict
            Building information dictionary.
        """
        self.pv_tab.display_data(building_info)

    def update_pv_tab(self, pv_results):
        """
        Update PV tab with calculation results.

        Parameters
        ----------
        pv_results : list
            PV calculation results.
        """
        self.pv_tab.treeWidget.clear()
        building_clusters = {}
        for result in pv_results:
            building = result['Building']
            if building not in building_clusters:
                building_clusters[building] = []
                building_clusters[building].append(result)

        for building, results in building_clusters.items():
            building_item = self.pv_tab.add_building(building, results[0]['Latitude'], results[0]['Longitude'])
            for result in results:
                self.pv_tab.add_roof(building_item, result['Roof Area (m²)'], result['Slope (°)'], result['Orientation (°)'], result['Yield (MWh)'], result['Max Power (kW)'])
        
    def update_subtype_combobox(self, row, subtypes):
        """
        Update subtype ComboBox with new options.

        Parameters
        ----------
        row : int
            Row index of ComboBox.
        subtypes : list
            Available subtypes.
        """
        comboBoxSubtypes = self.tables["Energiebedarf und Nutzung"].cellWidget(row, 2)
        comboBoxSubtypes.clear()
        comboBoxSubtypes.addItems(subtypes)

    def get_tabula_building_type(self, row):
        """
        Get selected TABULA building type.

        Parameters
        ----------
        row : int
            Row index.

        Returns
        -------
        str
            Selected building type.
        """
        return self.tables["Gebäudehülle und Typ"].cellWidget(row, 1).currentText()

    def get_building_state(self, row):
        """
        Get selected building state.

        Parameters
        ----------
        row : int
            Row index.

        Returns
        -------
        str
            Selected building state.
        """
        return self.tables["Gebäudehülle und Typ"].cellWidget(row, 2).currentText()

    def get_combobox_building_type(self, row):
        """
        Get selected building type from ComboBox.

        Parameters
        ----------
        row : int
            Row index.

        Returns
        -------
        str
            Selected building type.
        """
        return self.tables["Energiebedarf und Nutzung"].cellWidget(row, 1).currentText()

    def update_3d_view(self, building_info):
        """
        Update 3D visualization with building data.

        Parameters
        ----------
        building_info : dict
            Building information dictionary.
        """
        self.visualization_3d.update_3d_view(building_info)

    def highlight_building_3d(self, parent_id, roof=False, roof_id=None, roof_info=None):
        """
        Highlight building in 3D plot.

        Parameters
        ----------
        parent_id : str
            Building ID to highlight.
        roof : bool, optional
            Whether to highlight roof.
        roof_id : str, optional
            Roof ID to highlight.
        roof_info : dict, optional
            Roof information.
        """
        self.visualization_3d.highlight_building_3d(parent_id, roof, roof_id, roof_info)

    def show_info_message(self, title, message):
        """
        Display information message dialog.

        Parameters
        ----------
        title : str
            Dialog title.
        message : str
            Message text.
        """
        QMessageBox.information(self, title, message)