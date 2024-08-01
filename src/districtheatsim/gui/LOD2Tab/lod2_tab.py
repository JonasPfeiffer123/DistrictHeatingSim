"""
Filename: lod2_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the LOD2Tab.
"""

import sys
import os
import csv
import json
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from PyQt5.QtWidgets import (
    QVBoxLayout, QComboBox, QFileDialog, QProgressBar, QWidget, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAction, QTabWidget, 
    QDialog, QMessageBox, QHBoxLayout, QMenuBar, QScrollArea
)
from PyQt5.QtCore import pyqtSignal, QCoreApplication

from lod2.filter_LOD2 import spatial_filter_with_polygon, filter_LOD2_with_coordinates, process_lod2, calculate_centroid_and_geocode
from lod2.heat_requirement_LOD2 import Building
from gui.LOD2Tab.lod2_dialogs import FilterDialog


def get_resource_path(relative_path):
    """
    Get the absolute path to the resource, works for dev and for PyInstaller.
    
    Args:
        relative_path (str): The relative path to the resource.
    
    Returns:
        str: The absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    return os.path.join(base_path, relative_path)


class LOD2Tab(QWidget):
    """
    A QWidget subclass that represents the LOD2Tab, which is part of a larger PyQt application.
    
    Attributes:
        data_added (pyqtSignal): A signal that emits data as an object.
        data_manager (DataManager): An instance of the DataManager class for managing data.
        vis_tab (VisTab): An instance of the VisTab class for visualization.
        parent (QWidget): The parent widget.
        loaded_data (list): A list of loaded datasets.
        loaded_filenames (list): A list of filenames of loaded datasets.
        comboBoxBuildingTypesItems (list): A list of building types for the ComboBox.
        slp_df (DataFrame): A DataFrame containing the SLP database.
        annotation (Annotation): The current annotation in the 3D plot.
        selected_building (Building): The currently selected building.
        u_values_df (DataFrame): A DataFrame containing U-values for buildings.
    """
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, vis_tab, parent=None):
        """
        Initializes the LOD2Tab.
        
        Args:
            data_manager (DataManager): The data manager.
            vis_tab (VisTab): The visualization tab.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.vis_tab = vis_tab
        self.parent = parent

        self.loaded_data = []
        self.loaded_filenames = []

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)

        self.comboBoxBuildingTypesItems = pd.read_csv(get_resource_path('data\\TABULA\\standard_u_values_TABULA.csv'), sep=";")['Typ'].unique().tolist()

        self.slp_df = pd.read_csv(get_resource_path('data\\BDEW profiles\\daily_coefficients.csv'), delimiter=';', dtype=str)
        self.populateComboBoxes()

        self.initUI()

        self.annotation = None
        self.selected_building = None

        self.u_values_df = pd.read_csv(get_resource_path('data\\TABULA\\standard_u_values_TABULA.csv'), sep=";")

    def initUI(self):
        """
        Initializes the UI components of the LOD2Tab.
        """
        main_layout = QVBoxLayout(self)

        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)
        fileMenu = self.menuBar.addMenu('Datei')

        open_action = QAction('Öffnen', self)
        open_action.triggered.connect(self.loadDataFromFile)
        fileMenu.addAction(open_action)

        save_action = QAction('Speichern', self)
        save_action.triggered.connect(self.saveDataAsGeoJSON)
        fileMenu.addAction(save_action)

        process_menu = self.menuBar.addMenu('Datenverarbeitung')

        process_filter_action = QAction('LOD2-Daten filtern laden', self)
        process_filter_action.triggered.connect(self.showFilterDialog)
        process_menu.addAction(process_filter_action)

        calculate_heat_demand_action = QAction('Wärmebedarf berechnen', self)
        calculate_heat_demand_action.triggered.connect(self.calculateHeatDemand)
        process_menu.addAction(calculate_heat_demand_action)

        create_csv_action = QAction('Gebäude-csv für Netzgenerierung erstellen', self)
        create_csv_action.triggered.connect(self.createBuildingCSV)
        process_menu.addAction(create_csv_action)

        dataset_menu = self.menuBar.addMenu('Datenvergleich')

        add_dataset_action = QAction('Datensatz hinzufügen', self)
        add_dataset_action.triggered.connect(self.addDataset)
        dataset_menu.addAction(add_dataset_action)

        remove_dataset_action = QAction('Datensatz entfernen', self)
        remove_dataset_action.triggered.connect(self.removeDataset)
        dataset_menu.addAction(remove_dataset_action)

        main_layout.addWidget(self.menuBar)

        tabs = QTabWidget(self)
        main_layout.addWidget(tabs)

        data_vis_tab = QWidget()
        tabs.addTab(data_vis_tab, "Tabelle und Visualisierung LOD2-Daten")

        data_vis_layout = QHBoxLayout(data_vis_tab)

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
        self.canvas_3d.setMinimumSize(400, 400)
        data_vis_layout.addWidget(self.canvas_3d)

        vis_tab = QWidget()
        tabs.addTab(vis_tab, "Balkendiagramm Wärmebedarf")

        vis_layout = QVBoxLayout(vis_tab)
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(800, 400)
        vis_layout.addWidget(self.canvas)

        self.progressBar = QProgressBar(self)
        main_layout.addWidget(self.progressBar)

        self.tableWidget.itemSelectionChanged.connect(self.on_table_column_select)

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default base path.
        
        Args:
            new_base_path (str): The new base path.
        """
        self.base_path = new_base_path

    def showFilterDialog(self):
        """
        Shows the filter dialog for LOD2 data filtering.
        """
        dialog = FilterDialog(self.base_path, self)
        if dialog.exec_() == QDialog.Accepted:
            self.inputLOD2geojsonfilename = dialog.inputLOD2geojsonLineEdit.text()
            self.inputfilterPolygonfilename = dialog.inputfilterPolygonLineEdit.text()
            self.inputfilterBuildingDatafilename = dialog.inputfilterBuildingDataLineEdit.text()
            self.outputLOD2geojsonfilename = dialog.outputLOD2geojsonLineEdit.text()
            self.filterMethod = dialog.filterMethodComboBox.currentText()

            if self.filterMethod == "Filter by Polygon":
                spatial_filter_with_polygon(self.inputLOD2geojsonfilename, self.inputfilterPolygonfilename, self.outputLOD2geojsonfilename)
            elif self.filterMethod == "Filter by Building Data CSV":
                filter_LOD2_with_coordinates(self.inputLOD2geojsonfilename, self.inputfilterBuildingDatafilename, self.outputLOD2geojsonfilename)

            self.loadDataFromGeoJSON()
            self.saveDataAsGeoJSON(self.outputLOD2geojsonfilename)

    def loadDataFromGeoJSON(self):
        """
        Loads data from a GeoJSON file and updates the UI components.
        """
        self.vis_tab.loadNetData(self.outputLOD2geojsonfilename)

        self.STANDARD_VALUES = {
            'Stockwerke': 4, 'ww_demand_kWh_per_m2': 12.8, 'air_change_rate': 0.5, 'fracture_windows': 0.10, 
            'fracture_doors': 0.01, 'Normaußentemperatur': -15, 'room_temp': 20, 'max_air_temp_heating': 15,
            'Typ_Heizflächen': 'HK', 'VLT_max': 70, 'Steigung_Heizkurve': 1.5, 'RLT_max': 55
        }

        self.building_info = process_lod2(self.outputLOD2geojsonfilename, self.STANDARD_VALUES)

        address_missing = any(info['Adresse'] is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)

        self.tableWidget.setColumnCount(len(self.building_info))
        self.tableWidget.setHorizontalHeaderLabels([str(i + 1) for i in range(len(self.building_info))])

        for col, (parent_id, info) in enumerate(self.building_info.items()):
            self.updateTableWidget(col, info)

        self.load3DVisualization()

    def updateTableWidget(self, col, info):
        """
        Updates the table widget with building information.
        
        Args:
            col (int): The column index.
            info (dict): The building information.
        """
        self.tableWidget.setItem(0, col, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
        self.tableWidget.setItem(1, col, QTableWidgetItem(str((info['Koordinate_X']))))
        self.tableWidget.setItem(2, col, QTableWidgetItem(str((info['Koordinate_Y']))))
        self.tableWidget.setItem(3, col, QTableWidgetItem(str(round(info['Ground_Area'], 1))))
        self.tableWidget.setItem(4, col, QTableWidgetItem(str(round(info['Wall_Area'], 1))))
        self.tableWidget.setItem(5, col, QTableWidgetItem(str(round(info['Roof_Area'], 1))))
        self.tableWidget.setItem(6, col, QTableWidgetItem(str(round(info['Volume'], 1))))
        self.tableWidget.setItem(7, col, QTableWidgetItem(str(info['Stockwerke'])))

        comboBoxTypes = QComboBox()
        comboBoxTypes.addItems(self.building_types)
        comboBoxTypes.setCurrentText(info['Gebäudetyp'])
        comboBoxTypes.currentIndexChanged.connect(lambda idx, col=col: self.updateSubtypComboBox(col))
        self.tableWidget.setCellWidget(8, col, comboBoxTypes)

        comboBoxSubtypes = QComboBox()
        current_building_type = comboBoxTypes.currentText()
        subtypes = self.building_subtypes.get(current_building_type, [])
        comboBoxSubtypes.addItems(subtypes)
        comboBoxSubtypes.setCurrentText(str(info['Subtyp']))
        self.tableWidget.setCellWidget(9, col, comboBoxSubtypes)

        comboBoxBuildingTypes = QComboBox()
        comboBoxBuildingTypes.addItems(self.comboBoxBuildingTypesItems)
        comboBoxBuildingTypes.currentIndexChanged.connect(lambda idx, col=col: self.update_u_values(col))
        if info.get('Typ') and info['Typ'] in [comboBoxBuildingTypes.itemText(i) for i in range(comboBoxBuildingTypes.count())]:
            comboBoxBuildingTypes.setCurrentText(info['Typ'])
        self.tableWidget.setCellWidget(10, col, comboBoxBuildingTypes)

        comboBoxBuildingState = QComboBox()
        comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment", "Individuell"])
        comboBoxBuildingState.currentIndexChanged.connect(lambda idx, col=col: self.update_u_values(col))
        if info.get('Gebäudezustand') and info['Gebäudezustand'] in [comboBoxBuildingState.itemText(i) for i in range(comboBoxBuildingState.count())]:
            comboBoxBuildingState.setCurrentText(info['Gebäudezustand'])
        self.tableWidget.setCellWidget(11, col, comboBoxBuildingState)

        self.setDefaultOrExistingValues(col, info)

    def setDefaultOrExistingValues(self, col, info):
        """
        Sets default or existing values in the table widget.
        
        Args:
            col (int): The column index.
            info (dict): The building information.
        """
        self.tableWidget.setItem(12, col, QTableWidgetItem(str(info['ww_demand_kWh_per_m2'])))
        self.tableWidget.setItem(13, col, QTableWidgetItem(str(info['air_change_rate'])))
        self.tableWidget.setItem(14, col, QTableWidgetItem(str(info['fracture_windows'])))
        self.tableWidget.setItem(15, col, QTableWidgetItem(str(info['fracture_doors'])))
        self.tableWidget.setItem(16, col, QTableWidgetItem(str(info['Normaußentemperatur'])))
        self.tableWidget.setItem(17, col, QTableWidgetItem(str(info['room_temp'])))
        self.tableWidget.setItem(18, col, QTableWidgetItem(str(info['max_air_temp_heating'])))

        self.update_u_values(col, self.building_info)

        self.tableWidget.setItem(24, col, QTableWidgetItem(str(info['Typ_Heizflächen'])))
        self.tableWidget.setItem(25, col, QTableWidgetItem(str(info['VLT_max'])))
        self.tableWidget.setItem(26, col, QTableWidgetItem(str(info['Steigung_Heizkurve'])))
        self.tableWidget.setItem(27, col, QTableWidgetItem(str(info['RLT_max'])))

        waermebedarf = info.get('Wärmebedarf', None)
        if waermebedarf is not None:
            self.tableWidget.setItem(28, col, QTableWidgetItem(str(waermebedarf)))

        Warmwasseranteil = info.get('Warmwasseranteil', None)
        if Warmwasseranteil is not None:
            self.tableWidget.setItem(29, col, QTableWidgetItem(str(Warmwasseranteil)))

    def updateSubtypComboBox(self, col):
        """
        Updates the subtyp ComboBox based on the selected building type.
        
        Args:
            col (int): The column index.
        """
        comboBoxTypes = self.tableWidget.cellWidget(8, col)
        comboBoxSubtypes = self.tableWidget.cellWidget(9, col)
        current_building_type = comboBoxTypes.currentText()
        subtypes = self.building_subtypes.get(current_building_type, [])
        comboBoxSubtypes.clear()
        comboBoxSubtypes.addItems(subtypes)

    def populateComboBoxes(self):
        """
        Populates the building types and subtypes ComboBoxes.
        """
        building_types = self.slp_df['Standardlastprofil'].str[:3].unique()
        self.building_types = sorted(building_types)
        self.building_subtypes = {}
        for building_type in self.building_types:
            subtypes = self.slp_df[self.slp_df['Standardlastprofil'].str.startswith(building_type)]['Standardlastprofil'].str[-2:].unique()
            self.building_subtypes[building_type] = sorted(subtypes)

    def update_u_values(self, col, building_info=None):
        """
        Updates the U-values in the table widget.
        
        Args:
            col (int): The column index.
            building_info (dict, optional): The building information. Defaults to None.
        """
        if building_info is None:
            building_info = self.building_info

        parent_id = list(building_info.keys())[col]
        info = building_info[parent_id]

        building_type = self.tableWidget.cellWidget(10, col).currentText()
        building_state = self.tableWidget.cellWidget(11, col).currentText()

        wall_u, roof_u, window_u, door_u, ground_u = self.get_u_values(building_type, building_state, info)

        self.tableWidget.setItem(19, col, QTableWidgetItem(str(wall_u)))
        self.tableWidget.setItem(20, col, QTableWidgetItem(str(roof_u)))
        self.tableWidget.setItem(21, col, QTableWidgetItem(str(window_u)))
        self.tableWidget.setItem(22, col, QTableWidgetItem(str(door_u)))
        self.tableWidget.setItem(23, col, QTableWidgetItem(str(ground_u)))

    def get_u_values(self, building_type, building_state, info):
        """
        Gets the U-values based on the building type and state.
        
        Args:
            building_type (str): The building type.
            building_state (str): The building state.
            info (dict): The building information.
        
        Returns:
            tuple: A tuple containing the U-values for wall, roof, window, door, and ground.
        """
        if info.get('wall_u') is not None:
            wall_u = info['wall_u']
        elif building_state != "Individuell":
            wall_u = self.get_u_value('wall_u', building_type, building_state)
        else:
            wall_u = ''

        if info.get('roof_u') is not None:
            roof_u = info['roof_u']
        elif building_state != "Individuell":
            roof_u = self.get_u_value('roof_u', building_type, building_state)
        else:
            roof_u = ''

        if info.get('window_u') is not None:
            window_u = info['window_u']
        elif building_state != "Individuell":
            window_u = self.get_u_value('window_u', building_type, building_state)
        else:
            window_u = ''

        if info.get('door_u') is not None:
            door_u = info['door_u']
        elif building_state != "Individuell":
            door_u = self.get_u_value('door_u', building_type, building_state)
        else:
            door_u = ''

        if info.get('ground_u') is not None:
            ground_u = info['ground_u']
        elif building_state != "Individuell":
            ground_u = self.get_u_value('ground_u', building_type, building_state)
        else:
            ground_u = ''

        return wall_u, roof_u, window_u, door_u, ground_u

    def get_u_value(self, u_value_column, building_type, building_state):
        """
        Gets the U-value for a specific column, building type, and state.
        
        Args:
            u_value_column (str): The U-value column name.
            building_type (str): The building type.
            building_state (str): The building state.
        
        Returns:
            float: The U-value.
        """
        u_values = self.u_values_df[(self.u_values_df['Typ'] == building_type) & (self.u_values_df['building_state'] == building_state)]
        return u_values.iloc[0][u_value_column] if not u_values.empty else ''

    def calculateHeatDemand(self):
        """
        Calculates the heat demand for each building and updates the table.
        """
        self.building_info = process_lod2(self.outputLOD2geojsonfilename, self.STANDARD_VALUES)

        for col in range(self.tableWidget.columnCount()):
            try:
                self.updateHeatDemandForColumn(col)
            except ValueError:
                QMessageBox.critical(self, "Fehler", f"Alle Felder müssen ausgefüllt sein (Spalte {col + 1}).")
                return

        self.updated_building_info = self.building_info

    def updateHeatDemandForColumn(self, col):
        """
        Updates the heat demand for a specific column.
        
        Args:
            col (int): The column index.
        """
        ground_area = float(self.tableWidget.item(3, col).text())
        wall_area = float(self.tableWidget.item(4, col).text())
        roof_area = float(self.tableWidget.item(5, col).text())
        volume = float(self.tableWidget.item(6, col).text())
        u_type = self.tableWidget.cellWidget(10, col).currentText()
        building_state = self.tableWidget.cellWidget(11, col).currentText()
        ww_demand_kWh_per_m2 = float(self.tableWidget.item(12, col).text())

        u_values = {
            'wall_u': float(self.tableWidget.item(19, col).text()),
            'roof_u': float(self.tableWidget.item(20, col).text()),
            'window_u': float(self.tableWidget.item(21, col).text()),
            'door_u': float(self.tableWidget.item(22, col).text()),
            'ground_u': float(self.tableWidget.item(23, col).text())
        }

        building = Building(ground_area, wall_area, roof_area, volume, u_type=u_type, building_state=building_state, filename_TRY=self.parent.try_filename, u_values=u_values)
        building.calc_yearly_heat_demand()

        parent_id = list(self.building_info.keys())[col]
        self.building_info[parent_id]['Wärmebedarf'] = building.yearly_heat_demand

        self.tableWidget.setItem(28, col, QTableWidgetItem(f"{building.yearly_heat_demand:.2f}"))
        self.tableWidget.setItem(29, col, QTableWidgetItem(f"{building.warm_water_share:.2f}"))

    def addDataset(self):
        """
        Adds a dataset for comparison.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", self.base_path, "CSV-Dateien (*.csv)")
        if path:
            df = pd.read_csv(path, delimiter=';')
            self.loaded_data.append(df)
            self.loaded_filenames.append(os.path.basename(path))
            self.updatePlot()

    def removeDataset(self):
        """
        Removes the last added dataset.
        """
        if self.loaded_data:
            self.loaded_data.pop()
            self.loaded_filenames.pop()
            self.updatePlot()

    def updatePlot(self):
        """
        Updates the plot with the current datasets.
        """
        if not self.loaded_data:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        all_data = pd.concat(self.loaded_data, keys=self.loaded_filenames, names=['Filename', 'Index'])
        all_data_grouped = all_data.groupby(['Adresse', 'Filename'])['Wärmebedarf'].sum().unstack('Filename').fillna(0)
        
        num_datasets = len(self.loaded_data)
        num_addresses = len(all_data_grouped)
        
        bar_width = 0.8 / num_datasets
        indices = np.arange(num_addresses)
        
        colors = plt.cm.Set1.colors[:num_datasets]

        for i, (filename, color) in enumerate(zip(all_data_grouped.columns, colors)):
            ax.barh(indices + i * bar_width, all_data_grouped[filename], bar_width, label=filename, color=color)

        ax.set_yticks(indices + bar_width * (num_datasets - 1) / 2)
        ax.set_yticklabels(all_data_grouped.index)
        ax.set_ylabel('Adresse')
        ax.set_xlabel('Wärmebedarf in kWh')
        ax.legend()
        
        self.canvas.draw()

    def on_table_column_select(self):
        """
        Handles the event when a table column is selected.
        """
        selected_columns = self.tableWidget.selectionModel().selectedColumns()
        if selected_columns:
            col = selected_columns[0].column()
            parent_id = list(self.building_info.keys())[col]
            info = self.building_info[parent_id]
            self.highlight_building_3d(info)

    def highlight_building_3d(self, info):
        """
        Highlights a building in the 3D plot.
        
        Args:
            info (dict): The building information.
        """
        self.load3DVisualization()
        ax = self.figure_3d.axes[0]
        self.plot_polygon_3d(ax, info['Ground'], 'red')
        self.plot_polygon_3d(ax, info['Wall'], 'red')
        self.plot_polygon_3d(ax, info['Roof'], 'red')
        self.canvas_3d.draw()

    def plot_polygon_3d(self, ax, geoms, color):
        """
        Plots a polygon in the 3D plot.
        
        Args:
            ax (Axes3D): The 3D axes.
            geoms (Polygon or MultiPolygon): The geometries to plot.
            color (str): The color of the polygon.
        """
        if isinstance(geoms, (Polygon, MultiPolygon)):
            geoms = [geoms]

        for geom in geoms:
            if geom is not None:
                if geom.geom_type == 'Polygon':
                    x, y, z = zip(*geom.exterior.coords)
                    verts = [list(zip(x, y, z))]
                    poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                    ax.add_collection3d(poly_collection)
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y, z = zip(*poly.exterior.coords)
                        verts = [list(zip(x, y, z))]
                        poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                        ax.add_collection3d(poly_collection)

    def load3DVisualization(self):
        """
        Loads the 3D visualization of the LOD2 data.
        """
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')

        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        for parent_id, info in self.building_info.items():
            min_x, min_y, min_z, max_x, max_y, max_z = self.plot_building_parts(ax, info, min_x, min_y, min_z, max_x, max_y, max_z)

        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_zlim(min_z, max_z)

        max_range = max(max_x - min_x, max_y - min_y, max_z - min_z)
        ax.set_box_aspect([max_x - min_x, max_y - min_y, max_z - min_z])

        ax.set_xlabel('UTM_X')
        ax.set_ylabel('UTM_Y')
        ax.set_zlabel('Höhe')
        ax.set_title('3D-Visualisierung der LOD2-Daten')

        self.canvas_3d.draw()

    def plot_building_parts(self, ax, info, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        Plots the building parts in the 3D plot.
        
        Args:
            ax (Axes3D): The 3D axes.
            info (dict): The building information.
            min_x (float): The minimum x-coordinate.
            min_y (float): The minimum y-coordinate.
            min_z (float): The minimum z-coordinate.
            max_x (float): The maximum x-coordinate.
            max_y (float): The maximum y-coordinate.
            max_z (float): The maximum z-coordinate.
        
        Returns:
            tuple: Updated minimum and maximum coordinates.
        """
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(ax, info['Ground'], 'green', min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(ax, info['Wall'], 'blue', min_x, min_y, min_z, max_x, max_y, max_z)
        min_x, min_y, min_z, max_x, max_y, max_z = self.plot_geometry(ax, info['Roof'], 'brown', min_x, min_y, min_z, max_x, max_y, max_z)

        return min_x, min_y, min_z, max_x, max_y, max_z

    def plot_geometry(self, ax, geoms, color, min_x, min_y, min_z, max_x, max_y, max_z):
        """
        Plots the geometry in the 3D plot.
        
        Args:
            ax (Axes3D): The 3D axes.
            geoms (Polygon or MultiPolygon): The geometries to plot.
            color (str): The color of the polygon.
            min_x (float): The minimum x-coordinate.
            min_y (float): The minimum y-coordinate.
            min_z (float): The minimum z-coordinate.
            max_x (float): The maximum x-coordinate.
            max_y (float): The maximum y-coordinate.
            max_z (float): The maximum z-coordinate.
        
        Returns:
            tuple: Updated minimum and maximum coordinates.
        """
        if geoms:
            for geom in geoms:
                self.plot_polygon_3d(ax, geom, color)
                if geom.geom_type == 'Polygon':
                    x, y = geom.exterior.xy
                    z = [pt[2] for pt in geom.exterior.coords]
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y = poly.exterior.xy
                        z = [pt[2] for pt in poly.exterior.coords]
                min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))

        return min_x, min_y, min_z, max_x, max_y, max_z

    def saveDataAsGeoJSON(self, filename=False):
        """
        Saves the data as a GeoJSON file.
        
        Args:
            filename (str, optional): The filename to save the data. Defaults to False.
        """
        try:
            if filename is False:
                path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", self.base_path, "GeoJSON-Dateien (*.geojson)")
                if not path:
                    return
            else:
                path = filename

            with open(self.outputLOD2geojsonfilename, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            for col in range(self.tableWidget.columnCount()):
                self.updateGeoJSONProperties(geojson_data, col)

            with open(path, 'w', encoding='utf-8') as file:
                json.dump(geojson_data, file, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern", f"Ein Fehler ist beim Speichern aufgetreten: {str(e)}")

        QCoreApplication.processEvents()

    def updateGeoJSONProperties(self, geojson_data, col):
        """
        Updates the properties of the GeoJSON data.
        
        Args:
            geojson_data (dict): The GeoJSON data.
            col (int): The column index.
        """
        for feature in geojson_data['features']:
            properties = feature['properties']
            parent_id = properties.get('parent_id')

            if parent_id == list(self.building_info.keys())[col]:
                properties['Adresse'] = self.tableWidget.item(0, col).text().split(", ")[0]
                properties['Stadt'] = self.tableWidget.item(0, col).text().split(", ")[1]
                properties['Bundesland'] = self.tableWidget.item(0, col).text().split(", ")[2]
                properties['Land'] = self.tableWidget.item(0, col).text().split(", ")[3]
                properties['Koordinate_X'] = float(self.tableWidget.item(1, col).text())
                properties['Koordinate_Y'] = float(self.tableWidget.item(2, col).text())
                properties['Ground_Area'] = float(self.tableWidget.item(3, col).text())
                properties['Wall_Area'] = float(self.tableWidget.item(4, col).text())
                properties['Roof_Area'] = float(self.tableWidget.item(5, col).text())
                properties['Volume'] = float(self.tableWidget.item(6, col).text())
                properties['Stockwerke'] = int(self.tableWidget.item(7, col).text()) if self.tableWidget.item(7, col) else None
                properties['Gebäudetyp'] = self.tableWidget.cellWidget(8, col).currentText()
                properties['Subtyp'] = self.tableWidget.cellWidget(9, col).currentText()
                properties['Typ'] = self.tableWidget.cellWidget(10, col).currentText()
                properties['Gebäudezustand'] = self.tableWidget.cellWidget(11, col).currentText()
                properties['ww_demand_kWh_per_m2'] = float(self.tableWidget.item(12, col).text()) if self.tableWidget.item(12, col) else None
                properties['air_change_rate'] = float(self.tableWidget.item(13, col).text()) if self.tableWidget.item(13, col) else None
                properties['fracture_windows'] = float(self.tableWidget.item(14, col).text()) if self.tableWidget.item(14, col) else None
                properties['fracture_doors'] = float(self.tableWidget.item(15, col).text()) if self.tableWidget.item(15, col) else None
                properties['Normaußentemperatur'] = float(self.tableWidget.item(16, col).text()) if self.tableWidget.item(16, col) else None
                properties['room_temp'] = float(self.tableWidget.item(17, col).text()) if self.tableWidget.item(17, col) else None
                properties['max_air_temp_heating'] = float(self.tableWidget.item(18, col).text()) if self.tableWidget.item(18, col) else None
                properties['Typ_Heizflächen'] = self.tableWidget.item(24, col).text() if self.tableWidget.item(24, col) else None
                properties['VLT_max'] = float(self.tableWidget.item(25, col).text()) if self.tableWidget.item(25, col) else None
                properties['Steigung_Heizkurve'] = float(self.tableWidget.item(26, col).text()) if self.tableWidget.item(26, col) else None
                properties['RLT_max'] = float(self.tableWidget.item(27, col).text()) if self.tableWidget.item(27, col) else None
                properties['Wärmebedarf'] = float(self.tableWidget.item(28, col).text()) if self.tableWidget.item(28, col) else None
                properties['Warmwasseranteil'] = float(self.tableWidget.item(29, col).text()) if self.tableWidget.item(29, col) else None
                properties['wall_u'] = float(self.tableWidget.item(19, col).text()) if self.tableWidget.item(19, col) else None
                properties['roof_u'] = float(self.tableWidget.item(20, col).text()) if self.tableWidget.item(20, col) else None
                properties['window_u'] = float(self.tableWidget.item(21, col).text()) if self.tableWidget.item(21, col) else None
                properties['door_u'] = float(self.tableWidget.item(22, col).text()) if self.tableWidget.item(22, col) else None
                properties['ground_u'] = float(self.tableWidget.item(23, col).text()) if self.tableWidget.item(23, col) else None

    def loadDataFromFile(self):
        """
        Loads data from a file.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", self.base_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    geojson_data = json.load(file)

                building_info = {}
                for feature in geojson_data['features']:
                    properties = feature['properties']
                    parent_id = properties.get('parent_id')
                    building_info[parent_id] = properties

                self.outputLOD2geojsonfilename = path
                self.updated_building_info = building_info
                self.vis_tab.loadNetData(self.outputLOD2geojsonfilename)
                self.loadDataFromGeoJSON()

            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Ein Fehler ist beim Öffnen der Datei aufgetreten: {str(e)}")

        QCoreApplication.processEvents()

    def createBuildingCSV(self):
        """
        Creates a CSV file for building data.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", self.base_path, "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                headers = [
                    'Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', 
                    'Subtyp', 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 
                    'RLT_max', 'Normaußentemperatur', 'UTM_X', 'UTM_Y'
                ]
                writer.writerow(headers)

                for col in range(self.tableWidget.columnCount()):
                    row_data = self.getBuildingCSVRowData(col)
                    writer.writerow(row_data)
                print(f"Daten wurden gespeichert: {path}")

    def getBuildingCSVRowData(self, col):
        """
        Gets the row data for the building CSV.
        
        Args:
            col (int): The column index.
        
        Returns:
            list: The row data.
        """
        land = self.tableWidget.item(0, col).text().split(", ")[3]
        bundesland = self.tableWidget.item(0, col).text().split(", ")[2]
        stadt = self.tableWidget.item(0, col).text().split(", ")[1]
        address = self.tableWidget.item(0, col).text().split(", ")[0]
        heat_demand = self.tableWidget.item(28, col).text() if self.tableWidget.item(28, col) else '0'
        building_type = self.tableWidget.cellWidget(8, col).currentText()
        subtype = self.tableWidget.cellWidget(9, col).currentText()
        ww_share = self.tableWidget.item(29, col).text() if self.tableWidget.item(29, col) else '0'
        utm_x = self.tableWidget.item(1, col).text()
        utm_y = self.tableWidget.item(2, col).text()

        typ_heizflaechen = self.tableWidget.item(24, col).text() if self.tableWidget.item(24, col) else ""
        vlt_max = self.tableWidget.item(25, col).text() if self.tableWidget.item(25, col) else ""
        steigung_heizkurve = self.tableWidget.item(26, col).text() if self.tableWidget.item(26, col) else ""
        rlt_max = self.tableWidget.item(27, col).text() if self.tableWidget.item(27, col) else ""
        air_temp_min = self.tableWidget.item(16, col).text() if self.tableWidget.item(16, col) else ""

        row_data = [
            land, bundesland, stadt, address, heat_demand, building_type, subtype, 
            ww_share, typ_heizflaechen, vlt_max, steigung_heizkurve, rlt_max, 
            air_temp_min, utm_x, utm_y
        ]
        return row_data