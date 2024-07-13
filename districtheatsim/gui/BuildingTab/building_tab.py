import sys
import os
import csv
import json
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point, MultiPolygon

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from PyQt5.QtWidgets import QVBoxLayout, QComboBox, QFileDialog, QProgressBar, QWidget, QTableWidget, QTableWidgetItem, \
    QHeaderView, QAction, QMainWindow, QTabWidget, QDialog, QMessageBox, QHBoxLayout, QMenuBar, QScrollArea
from PyQt5.QtCore import pyqtSignal, Qt

from lod2.filter_LOD2 import spatial_filter_with_polygon, filter_LOD2_with_coordinates, process_lod2, calculate_centroid_and_geocode
from lod2.heat_requirement_DIN_EN_12831 import Building
from gui.BuildingTab.building_dialogs import FilterDialog

# defines the base path
def get_resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # Wenn die Anwendung eingefroren ist, ist der Basispfad der Temp-Ordner, wo PyInstaller alles extrahiert
        base_path = sys._MEIPASS
    else:
        # Wenn die Anwendung nicht eingefroren ist, ist der Basispfad der Ordner, in dem die Hauptdatei liegt
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, relative_path)

class BuildingTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, vis_tab, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.vis_tab = vis_tab
        self.parent = parent

        self.loaded_data = []
        self.loaded_filenames = []

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.updateDefaultPath(self.data_manager.project_folder)

        self.comboBoxBuildingTypesItems = pd.read_csv(get_resource_path('lod2/data/standard_u_values_TABULA.csv'), sep=";")['Typ'].unique().tolist()

        self.initUI()

        self.annotation = None
        self.selected_building = None

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # Menüleiste für CSV-Editor und Geocoding
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

        # Create tabs
        tabs = QTabWidget(self)
        main_layout.addWidget(tabs)

        # Data table and 3D Visualization tab
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
        self.tableWidget.setColumnCount(19)
        self.tableWidget.setHorizontalHeaderLabels(['Adresse', 'UTM_X', 'UTM_Y', 'Grundfläche', 'Wandfläche', 'Dachfläche', 'Volumen', 'Stockwerke', 'Nutzungstyp', 'Typ', 'Gebäudezustand', 
                                                    'ww_demand_Wh_per_m2', 'air_change_rate', 'fracture_windows', 'fracture_doors', 'min_air_temp', 
                                                    'room_temp', 'max_air_temp_heating', 'Wärmebedarf'])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tableWidget.setSortingEnabled(True)
        self.tableWidget.setMinimumSize(800, 400)
        scroll_layout.addWidget(self.tableWidget)

        self.figure_3d = plt.figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        self.canvas_3d.setMinimumSize(400, 400)
        data_vis_layout.addWidget(self.canvas_3d)

        # Visualization tab
        vis_tab = QWidget()
        tabs.addTab(vis_tab, "Balkendiagramm Wärmebedarf")

        vis_layout = QVBoxLayout(vis_tab)
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(800, 400)
        vis_layout.addWidget(self.canvas)

        self.progressBar = QProgressBar(self)
        main_layout.addWidget(self.progressBar)

        # Connect to table row selection event
        self.tableWidget.itemSelectionChanged.connect(self.on_table_row_select)
        
    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def showFilterDialog(self):
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

    def loadDataFromGeoJSON(self):
        self.vis_tab.loadNetData(self.outputLOD2geojsonfilename)

        self.building_info = process_lod2(self.outputLOD2geojsonfilename)

        address_missing = any(info['Adresse'] is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)

        self.tableWidget.setRowCount(len(self.building_info))

        for row, (parent_id, info) in enumerate(self.building_info.items()):
            self.tableWidget.setItem(row, 0, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(str((info['Koordinate_X']))))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(str((info['Koordinate_Y']))))
            self.tableWidget.setItem(row, 3, QTableWidgetItem(str(round(info['Ground_Area'], 1))))
            self.tableWidget.setItem(row, 4, QTableWidgetItem(str(round(info['Wall_Area'], 1))))
            self.tableWidget.setItem(row, 5, QTableWidgetItem(str(round(info['Roof_Area'], 1))))
            self.tableWidget.setItem(row, 6, QTableWidgetItem(str(round(info['Volume'], 1))))
            self.tableWidget.setItem(row, 7, QTableWidgetItem(str(info['Stockwerke'])))

            # Nutzungstyp ComboBox
            comboBoxTypes = QComboBox()
            comboBoxTypes.addItems(["HMF", "HEF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"])
            if info.get('Nutzungstyp') and info['Nutzungstyp'] in [comboBoxTypes.itemText(i) for i in range(comboBoxTypes.count())]:
                comboBoxTypes.setCurrentText(info['Nutzungstyp'])
            self.tableWidget.setCellWidget(row, 8, comboBoxTypes)

            # Gebäude Typ ComboBox
            comboBoxBuildingTypes = QComboBox()
            comboBoxBuildingTypes.addItems(self.comboBoxBuildingTypesItems)
            if info.get('Typ') and info['Typ'] in [comboBoxBuildingTypes.itemText(i) for i in range(comboBoxBuildingTypes.count())]:
                comboBoxBuildingTypes.setCurrentText(info['Typ'])
            self.tableWidget.setCellWidget(row, 9, comboBoxBuildingTypes)

            # Gebäude Zustand ComboBox
            comboBoxBuildingState = QComboBox()
            comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment"])
            if info.get('Gebäudezustand') and info['Gebäudezustand'] in [comboBoxBuildingState.itemText(i) for i in range(comboBoxBuildingState.count())]:
                comboBoxBuildingState.setCurrentText(info['Gebäudezustand'])
            self.tableWidget.setCellWidget(row, 10, comboBoxBuildingState)

            # Weitere Werte setzen, falls vorhanden, ansonsten Standardwerte verwenden
            self.tableWidget.setItem(row, 11, QTableWidgetItem(str(info['ww_demand_Wh_per_m2'])))
            self.tableWidget.setItem(row, 12, QTableWidgetItem(str(info['air_change_rate'])))
            self.tableWidget.setItem(row, 13, QTableWidgetItem(str(info['fracture_windows'])))
            self.tableWidget.setItem(row, 14, QTableWidgetItem(str(info['fracture_doors'])))
            self.tableWidget.setItem(row, 15, QTableWidgetItem(str(info['min_air_temp'])))
            self.tableWidget.setItem(row, 16, QTableWidgetItem(str(info['room_temp'])))
            self.tableWidget.setItem(row, 17, QTableWidgetItem(str(info['max_air_temp_heating'])))

            # Laden des Wärmebedarfs, wenn vorhanden
            waermebedarf = info.get('Wärmebedarf', None)
            if waermebedarf is not None:
                self.tableWidget.setItem(row, 18, QTableWidgetItem(str(waermebedarf)))

        # Load 2D and 3D Visualization
        self.load3DVisualization()

    def createComboBox(self, columnIndex):
        if columnIndex == 7:
            comboBoxItems = ["HMF", "HEF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"]
        elif columnIndex == 8:
            comboBoxItems = self.comboBoxBuildingTypesItems
        else:
            comboBoxItems = ["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment"]
        comboBox = QComboBox()
        comboBox.addItems(comboBoxItems)
        return comboBox
    
    ### calculate Heat Demand based on geometry and u-values ###
    def calculateHeatDemand(self):
        self.building_info = process_lod2(self.outputLOD2geojsonfilename)

        for row in range(self.tableWidget.rowCount()):
            ground_area = float(self.tableWidget.item(row, 3).text())
            wall_area = float(self.tableWidget.item(row, 4).text())
            roof_area = float(self.tableWidget.item(row, 5).text())
            volume = float(self.tableWidget.item(row, 6).text())
            u_type = self.tableWidget.cellWidget(row, 9).currentText()
            building_state = self.tableWidget.cellWidget(row, 10).currentText()

            building = Building(ground_area, wall_area, roof_area, volume, u_type=u_type, building_state=building_state, filename_TRY=self.parent.try_filename)
            building.calc_yearly_heat_demand()

            # Aktualisieren der GeoJSON-Datenstruktur mit den berechneten Daten
            parent_id = list(self.building_info.keys())[row]
            self.building_info[parent_id]['Wärmebedarf'] = building.yearly_heat_demand

            self.tableWidget.setItem(row, 18, QTableWidgetItem(f"{building.yearly_heat_demand:.2f}"))

        # Speichern der aktualisierten GeoJSON-Datenstruktur
        self.updated_building_info = self.building_info

    ### Plotting Data Comparison Heat Demands ###
    def addDataset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", "", "CSV-Dateien (*.csv)")
        if path:
            df = pd.read_csv(path, delimiter=';')
            self.loaded_data.append(df)
            self.loaded_filenames.append(os.path.basename(path))
            self.updatePlot()

    def removeDataset(self):
        if self.loaded_data:
            self.loaded_data.pop()
            self.loaded_filenames.pop()
            self.updatePlot()

    def updatePlot(self):
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
        
        colors = plt.cm.tab20.colors[:num_datasets]
        
        for i, (filename, color) in enumerate(zip(all_data_grouped.columns, colors)):
            ax.barh(indices + i * bar_width, all_data_grouped[filename], bar_width, label=filename, color=color)

        ax.set_yticks(indices + bar_width * (num_datasets - 1) / 2)
        ax.set_yticklabels(all_data_grouped.index)
        ax.set_ylabel('Adresse')
        ax.set_xlabel('Wärmebedarf in kWh')
        ax.legend()
        
        self.canvas.draw()

    ### LOD2 Visualization ###
    def on_table_row_select(self):
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            parent_id = list(self.building_info.keys())[row]
            info = self.building_info[parent_id]
            self.highlight_building_3d(info)

    def highlight_building_3d(self, info):
        self.load3DVisualization()  # Setze die vorherige Hervorhebung zurück
        ax = self.figure_3d.axes[0]  # Erhalte die aktuelle Achse, um das erneute Zeichnen zu vermeiden
        self.plot_polygon_3d(ax, info['Ground'], 'red')
        self.plot_polygon_3d(ax, info['Wall'], 'red')
        self.plot_polygon_3d(ax, info['Roof'], 'red')
        #self.add_annotation_3d(ax, info)
        self.canvas_3d.draw()

    def add_annotation_3d(self, ax, building_info):
        if hasattr(self, 'annotation') and self.annotation:
            self.annotation.remove()  # Entferne vorherige Annotation, falls vorhanden

        annotation_text = (f"ID: {building_info.get('parent_id', 'N/A')}\n"
                        f"Adresse: {building_info.get('Adresse', 'N/A')}\n"
                        f"Stadt: {building_info.get('Stadt', 'N/A')}\n"
                        f"Wärmebedarf: {building_info.get('Wärmebedarf', 'N/A')} kWh\n"
                        f"Nutzungstyp: {building_info.get('Nutzungstyp', 'N/A')}\n"
                        f"Typ: {building_info.get('Typ', 'N/A')}\n"
                        f"Gebäudezustand: {building_info.get('Gebäudezustand', 'N/A')}")

        centroid = self.get_building_centroid(building_info)
        x, y, z = centroid

        # Hinzufügen eines Offsets zur Annotation, um sie von der Mitte des Gebäudes zu verschieben
        offset = 50
        x_offset = x + offset
        y_offset = y + offset
        z_offset = z + offset

        self.annotation = ax.text(
            x_offset, y_offset, z_offset, annotation_text,
            bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="yellow", alpha=0.7),
            ha='center', va='bottom', fontsize=10, zorder=10  # Anpassen der vertikalen Ausrichtung
        )

    def get_building_centroid(self, building_info):
        ground_geoms = building_info.get('Ground', [])
        if ground_geoms:
            for geom in ground_geoms:
                if geom and geom.geom_type in ['Polygon', 'MultiPolygon']:
                    centroid = geom.centroid
                    z = 0
                    if geom.geom_type == 'Polygon':
                        z = sum(pt[2] for pt in geom.exterior.coords) / len(geom.exterior.coords)
                    elif geom.geom_type == 'MultiPolygon':
                        for poly in geom.geoms:
                            z = sum(pt[2] for pt in poly.exterior.coords) / len(poly.exterior.coords)
                    return centroid.x, centroid.y, z
        return 0, 0, 0  # Default if no valid geometry found

    def plot_polygon_3d(self, ax, geoms, color):
        if isinstance(geoms, (Polygon, MultiPolygon)):
            geoms = [geoms]  # Konvertiere einzelne Polygon oder MultiPolygon in eine Liste

        for geom in geoms:
            if geom is not None:
                if geom.geom_type == 'Polygon':
                    x, y, z = zip(*geom.exterior.coords)
                    verts = [list(zip(x, y, z))]
                    poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                    ax.add_collection3d(poly_collection)
                    #print(f"Plotted Polygon with {len(x)} points.")
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y, z = zip(*poly.exterior.coords)
                        verts = [list(zip(x, y, z))]
                        poly_collection = Poly3DCollection(verts, facecolors=color, alpha=0.5)
                        ax.add_collection3d(poly_collection)
                        #print(f"Plotted MultiPolygon with {len(x)} points in one of its polygons.")
                else:
                    print(f"Unsupported geometry type: {geom.geom_type}")

    def load3DVisualization(self):
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')

        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

        for parent_id, info in self.building_info.items():
            print(f"Processing building ID: {parent_id}")
            # Ground Geometries
            for ground_geom in info['Ground']:
                if ground_geom is not None:
                    self.plot_polygon_3d(ax, ground_geom, 'green')  # Ground level
                    if ground_geom.geom_type == 'Polygon':
                        x, y = ground_geom.exterior.xy
                        z = [pt[2] for pt in ground_geom.exterior.coords]
                    elif ground_geom.geom_type == 'MultiPolygon':
                        for poly in ground_geom.geoms:
                            x, y = poly.exterior.xy
                            z = [pt[2] for pt in poly.exterior.coords]
                    min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                    max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))
                else:
                    print("Ground geometry is None.")

            # Wall Geometries
            for wall_geom in info['Wall']:
                if wall_geom is not None:
                    self.plot_polygon_3d(ax, wall_geom, 'blue')  # Wall level
                    if wall_geom.geom_type == 'Polygon':
                        x, y = wall_geom.exterior.xy
                        z = [pt[2] for pt in wall_geom.exterior.coords]
                    elif wall_geom.geom_type == 'MultiPolygon':
                        for poly in wall_geom.geoms:
                            x, y = poly.exterior.xy
                            z = [pt[2] for pt in poly.exterior.coords]
                    min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                    max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))
                else:
                    print("Wall geometry is None.")

            # Roof Geometries
            for roof_geom in info['Roof']:
                if roof_geom is not None:
                    self.plot_polygon_3d(ax, roof_geom, 'brown')  # Roof level
                    if roof_geom.geom_type == 'Polygon':
                        x, y = roof_geom.exterior.xy
                        z = [pt[2] for pt in roof_geom.exterior.coords]
                    elif ground_geom.geom_type == 'MultiPolygon':
                        for poly in roof_geom.geoms:
                            x, y = poly.exterior.xy
                            z = [pt[2] for pt in poly.exterior.coords]
                    min_x, min_y, min_z = min(min_x, min(x)), min(min_y, min(y)), min(min_z, min(z))
                    max_x, max_y, max_z = max(max_x, max(x)), max(max_y, max(y)), max(max_z, max(z))
                else:
                    print("Roof geometry is None.")

        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_zlim(min_z, max_z)

        # Ensure equal scaling in all directions
        max_range = max(max_x - min_x, max_y - min_y, max_z - min_z)
        ax.set_box_aspect([max_x - min_x, max_y - min_y, max_z - min_z])  # Aspect ratio is 1:1:1

        ax.set_xlabel('UTM_X')
        ax.set_ylabel('UTM_Y')
        ax.set_zlabel('Höhe')
        ax.set_title('3D-Visualisierung der LOD2-Daten')

        self.canvas_3d.draw()

    ### save an load geojsons ###
    def saveDataAsGeoJSON(self):
        try:
            # Öffnen des Dateiauswahldialogs
            path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "GeoJSON-Dateien (*.geojson)")

            # Überprüfen, ob ein Pfad ausgewählt wurde
            if not path:
                print("Kein Pfad ausgewählt. Speichern abgebrochen.")
                return

            # Laden der ursprünglichen GeoJSON-Datei
            with open(self.outputLOD2geojsonfilename, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            for row in range(self.tableWidget.rowCount()):
                for feature in geojson_data['features']:
                    properties = feature['properties']
                    parent_id = properties.get('parent_id')  # Annahme, dass parent_id eindeutig ist

                    if parent_id == list(self.building_info.keys())[row]:
                        properties['Adresse'] = self.tableWidget.item(row, 0).text().split(", ")[0]
                        properties['Stadt'] = self.tableWidget.item(row, 0).text().split(", ")[1]
                        properties['Bundesland'] = self.tableWidget.item(row, 0).text().split(", ")[2]
                        properties['Land'] = self.tableWidget.item(row, 0).text().split(", ")[3]
                        properties['Koordinate_X'] = float(self.tableWidget.item(row, 1).text())
                        properties['Koordinate_Y'] = float(self.tableWidget.item(row, 2).text())
                        properties['Ground_Area'] = float(self.tableWidget.item(row, 3).text())
                        properties['Wall_Area'] = float(self.tableWidget.item(row, 4).text())
                        properties['Roof_Area'] = float(self.tableWidget.item(row, 5).text())
                        properties['Volume'] = float(self.tableWidget.item(row, 6).text())
                        properties['Stockwerke'] = int(self.tableWidget.item(row, 7).text()) if self.tableWidget.item(row, 7) else None
                        properties['Nutzungstyp'] = self.tableWidget.cellWidget(row, 8).currentText()
                        properties['Typ'] = self.tableWidget.cellWidget(row, 9).currentText()
                        properties['Gebäudezustand'] = self.tableWidget.cellWidget(row, 10).currentText()
                        properties['ww_demand_Wh_per_m2'] = float(self.tableWidget.item(row, 11).text()) if self.tableWidget.item(row, 11) else None
                        properties['air_change_rate'] = float(self.tableWidget.item(row, 12).text()) if self.tableWidget.item(row, 12) else None
                        properties['fracture_windows'] = float(self.tableWidget.item(row, 13).text()) if self.tableWidget.item(row, 13) else None
                        properties['fracture_doors'] = float(self.tableWidget.item(row, 14).text()) if self.tableWidget.item(row, 14) else None
                        properties['min_air_temp'] = float(self.tableWidget.item(row, 15).text()) if self.tableWidget.item(row, 15) else None
                        properties['room_temp'] = float(self.tableWidget.item(row, 16).text()) if self.tableWidget.item(row, 16) else None
                        properties['max_air_temp_heating'] = float(self.tableWidget.item(row, 17).text()) if self.tableWidget.item(row, 17) else None
                        properties['Wärmebedarf'] = float(self.tableWidget.item(row, 18).text()) if self.tableWidget.item(row, 18) else None

            # Schreiben der aktualisierten GeoJSON-Datei
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(geojson_data, file, ensure_ascii=False, indent=2)

            # Erfolgreiche Speicherung bestätigen
            QMessageBox.information(self, "Speichern erfolgreich", f"Daten wurden erfolgreich gespeichert unter: {path}")

        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
            QMessageBox.critical(self, "Fehler beim Speichern", f"Ein Fehler ist beim Speichern aufgetreten: {str(e)}")

    def loadDataFromFile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", "", "GeoJSON-Dateien (*.geojson)")
        if path:
            with open(path, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            building_info = {}
            for feature in geojson_data['features']:
                properties = feature['properties']
                parent_id = properties.get('parent_id')  # Annahme, dass parent_id eindeutig ist
                building_info[parent_id] = properties

            self.outputLOD2geojsonfilename = path
            self.updated_building_info = building_info
            self.vis_tab.loadNetData(self.outputLOD2geojsonfilename)
            self.loadDataFromGeoJSON()
    
    ### creating building csv for net generation ###
    def createBuildingCSV(self):
        standard_values = {
            'WW_Anteil': 0.2,
            'Typ_Heizflächen': 'HK',
            'VLT_max': 70,
            'Steigung_Heizkurve': 1.5,
            'RLT_max': 55
        }

        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', 'UTM_X', 'UTM_Y']
                writer.writerow(headers)

                for row in range(self.tableWidget.rowCount()):
                    land = self.tableWidget.item(row, 0).text().split(", ")[3]
                    bundesland = self.tableWidget.item(row, 0).text().split(", ")[2]
                    stadt = self.tableWidget.item(row, 0).text().split(", ")[1]
                    address = self.tableWidget.item(row, 0).text().split(", ")[0]
                    heat_demand = self.tableWidget.item(row, 18).text() if self.tableWidget.item(row, 18) else '0'
                    building_type = self.tableWidget.cellWidget(row, 8).currentText()
                    utm_x = self.tableWidget.item(row, 1).text()
                    utm_y = self.tableWidget.item(row, 2).text()

                    row_data = [
                        land,
                        bundesland,
                        stadt,
                        address,
                        heat_demand,
                        building_type,
                        standard_values['WW_Anteil'],
                        standard_values['Typ_Heizflächen'],
                        standard_values['VLT_max'],
                        standard_values['Steigung_Heizkurve'],
                        standard_values['RLT_max'],
                        utm_x,
                        utm_y
                    ]
                    writer.writerow(row_data)
                print(f"Daten wurden gespeichert: {path}")
