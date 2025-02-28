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
    QHeaderView, QHBoxLayout, QScrollArea, QMessageBox
)
from PyQt5.QtCore import pyqtSignal
from districtheatingsim.gui.LOD2Tab.lod2_3d_plot_matplotlib import LOD2Visualization3D

class LOD2DataVisualization(QWidget):
    """
    The view class for LOD2 data visualization.
    """
    data_selected = pyqtSignal(int)
    u_value_updated = pyqtSignal(int)
    building_type_changed = pyqtSignal(int)
    building_state_changed = pyqtSignal(int)  # Neu: Signal für Änderungen am Gebäudezustand

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

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setRowCount(30)
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setVerticalHeaderLabels([
            'Adresse', 'UTM_X (m)', 'UTM_Y (m)', 'Grundfläche (m²)', 'Wandfläche (m²)',
            'Dachfläche (m²)', 'Volumen (m³)', 'Stockwerke', 'Gebäudetyp SLP', 'Subtyp SLP',
            'Gebäudetyp TABULA', 'Gebäudezustand TABULA', 'WW-Bedarf (kWh/m²)', 'Luftwechselrate (1/h)',
            'Fensteranteil (%)', 'Türanteil (%)', 'Normaußentemperatur (°C)', 'Raumtemperatur (°C)',
            'Max. Heiz-Außentemperatur (°C)', 'U-Wert Wand (W/m²K)', 'U-Wert Dach (W/m²K)',
            'U-Wert Fenster (W/m²K)', 'U-Wert Tür (W/m²K)', 'U-Wert Boden (W/m²K)',
            'Typ_Heizflächen', 'VLT_max (°C)', 'Steigung_Heizkurve', 'RLT_max (°C)',
            'Wärmebedarf (kWh)', 'Warmwasseranteil (%)'
        ])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setMinimumSize(800, 400)
        scroll_layout.addWidget(self.tableWidget)

        self.figure_3d = plt.figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.canvas_3d.setMinimumSize(800, 800)
        data_vis_layout.addWidget(self.canvas_3d)

        # Connect signals
        self.tableWidget.itemSelectionChanged.connect(self.on_table_column_select)

    def on_table_column_select(self):
        """
        Handles the event when a table column is selected.
        """
        selected_columns = self.tableWidget.selectionModel().selectedColumns()
        if selected_columns:
            col = selected_columns[0].column()
            self.data_selected.emit(col)  # Emit the signal to inform the presenter

    def initialize_u_values(self, building_info):
        """
        Initialize the U-values for all buildings in the table after loading data.

        Args:
            building_info (dict): A dictionary containing building information.
        """
        for col, (parent_id, info) in enumerate(building_info.items()):
            # Wir gehen sicher, dass die U-Werte neu geladen werden, wenn sie None sind
            self.update_u_values(col, info)

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

        self.tableWidget.setColumnCount(len(building_info))
        self.tableWidget.setHorizontalHeaderLabels([str(i + 1) for i in range(len(building_info))])

        for col, (parent_id, info) in enumerate(building_info.items()):
            self.update_table_column(col, info)

        # Initiale Ausgabe der U-Werte nach dem Aufbau der Tabelle
        self.initialize_u_values(building_info)

    def update_table_column(self, col, info):
        """
        Update a single column in the table.

        Args:
            col (int): The column index to update.
            info (dict): A dictionary containing building information.
        """
        self.tableWidget.setItem(0, col, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
        self.tableWidget.setItem(1, col, QTableWidgetItem(str(info['Koordinate_X'])))
        self.tableWidget.setItem(2, col, QTableWidgetItem(str(info['Koordinate_Y'])))
        self.tableWidget.setItem(3, col, QTableWidgetItem(str(round(info['Ground_Area'], 1))))
        self.tableWidget.setItem(4, col, QTableWidgetItem(str(round(info['Wall_Area'], 1))))
        self.tableWidget.setItem(5, col, QTableWidgetItem(str(round(info['Roof_Area'], 1))))
        self.tableWidget.setItem(6, col, QTableWidgetItem(str(round(info['Volume'], 1))))
        self.tableWidget.setItem(7, col, QTableWidgetItem(str(info['Stockwerke'])))

        comboBoxSLPTypes = QComboBox()
        comboBoxSLPTypes.addItems(self.comboBoxBuildingTypesItems)
        comboBoxSLPTypes.setCurrentText(info['Gebäudetyp'])
        comboBoxSLPTypes.currentIndexChanged.connect(lambda idx, col=col: self.building_type_changed.emit(col))
        self.tableWidget.setCellWidget(8, col, comboBoxSLPTypes)

        comboBoxSLPSubtypes = QComboBox()
        comboBoxSLPSubtypes.addItems(self.building_subtypes.get(comboBoxSLPTypes.currentText(), []))
        comboBoxSLPSubtypes.setCurrentText(str(info['Subtyp']))
        self.tableWidget.setCellWidget(9, col, comboBoxSLPSubtypes)

        comboBoxBuildingTypes = QComboBox()
        comboBoxBuildingTypes.addItems(self.building_types)
        comboBoxBuildingTypes.setCurrentText(info.get('Gebäudetyp'))
        comboBoxBuildingTypes.currentIndexChanged.connect(lambda idx, col=col: self.building_type_changed.emit(col))
        self.tableWidget.setCellWidget(10, col, comboBoxBuildingTypes)

        comboBoxBuildingState = QComboBox()
        comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment", "Individuell"])
        comboBoxBuildingState.setCurrentText(info.get('Gebäudezustand'))
        comboBoxBuildingState.currentIndexChanged.connect(lambda idx, col=col: self.building_state_changed.emit(col))
        self.tableWidget.setCellWidget(11, col, comboBoxBuildingState)

        self.set_default_or_existing_values(col, info)

    def update_subtype_combobox(self, col, subtypes):
        """
        Update the subtype ComboBox with the new subtypes.

        Args:
            col (int): The column index of the ComboBox.
            subtypes (list): A list of subtypes to populate the ComboBox.
        """
        comboBoxSubtypes = self.tableWidget.cellWidget(9, col)
        comboBoxSubtypes.clear()
        comboBoxSubtypes.addItems(subtypes)

    def update_u_values(self, col, info):
        """
        Update U-values in the table widget based on the current selections.

        Args:
            col (int): The column index to update.
            info (dict): A dictionary containing updated building information.
        """
        self.tableWidget.setItem(19, col, QTableWidgetItem(str(info.get('wall_u'))))
        self.tableWidget.setItem(20, col, QTableWidgetItem(str(info.get('roof_u'))))
        self.tableWidget.setItem(21, col, QTableWidgetItem(str(info.get('window_u'))))
        self.tableWidget.setItem(22, col, QTableWidgetItem(str(info.get('door_u'))))
        self.tableWidget.setItem(23, col, QTableWidgetItem(str(info.get('ground_u'))))

    def get_tabula_building_type(self, col):
        """
        Returns the currently selected TABULA building type from the ComboBox.

        Args:
            col (int): The column index of the building type ComboBox.

        Returns:
            str: The selected TABULA building type.
        """
        return self.tableWidget.cellWidget(10, col).currentText()

    def get_building_state(self, col):
        """
        Returns the currently selected building state from the ComboBox.

        Args:
            col (int): The column index of the building state ComboBox.

        Returns:
            str: The selected building state.
        """
        return self.tableWidget.cellWidget(11, col).currentText()

    def set_default_or_existing_values(self, col, info):
        """
        Set default or existing values in the table widget.

        Args:
            col (int): The column index to update.
            info (dict): A dictionary containing building information.
        """
        self.tableWidget.setItem(12, col, QTableWidgetItem(str(info['ww_demand_kWh_per_m2'])))
        self.tableWidget.setItem(13, col, QTableWidgetItem(str(info['air_change_rate'])))
        self.tableWidget.setItem(14, col, QTableWidgetItem(str(info['fracture_windows'])))
        self.tableWidget.setItem(15, col, QTableWidgetItem(str(info['fracture_doors'])))
        self.tableWidget.setItem(16, col, QTableWidgetItem(str(info['Normaußentemperatur'])))
        self.tableWidget.setItem(17, col, QTableWidgetItem(str(info['room_temp'])))
        self.tableWidget.setItem(18, col, QTableWidgetItem(str(info['max_air_temp_heating'])))
        self.tableWidget.setItem(19, col, QTableWidgetItem(str(info['wall_u'])))
        self.tableWidget.setItem(20, col, QTableWidgetItem(str(info['roof_u'])))
        self.tableWidget.setItem(21, col, QTableWidgetItem(str(info['window_u'])))
        self.tableWidget.setItem(22, col, QTableWidgetItem(str(info['door_u'])))
        self.tableWidget.setItem(23, col, QTableWidgetItem(str(info['ground_u'])))
        self.tableWidget.setItem(24, col, QTableWidgetItem(str(info['Typ_Heizflächen'])))
        self.tableWidget.setItem(25, col, QTableWidgetItem(str(info['VLT_max'])))
        self.tableWidget.setItem(26, col, QTableWidgetItem(str(info['Steigung_Heizkurve'])))
        self.tableWidget.setItem(27, col, QTableWidgetItem(str(info['RLT_max'])))
        self.tableWidget.setItem(28, col, QTableWidgetItem(str(info['Wärmebedarf'])))
        self.tableWidget.setItem(29, col, QTableWidgetItem(str(info['Warmwasseranteil'])))

    def get_combobox_building_type(self, col):
        """
        Returns the current building type from the ComboBox.

        Args:
            col (int): The column index of the building type ComboBox.

        Returns:
            str: The current building type selected in the ComboBox.
        """
        return self.tableWidget.cellWidget(8, col).currentText()

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