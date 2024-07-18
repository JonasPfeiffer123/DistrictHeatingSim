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

from PyQt5.QtWidgets import QVBoxLayout, QComboBox, QFileDialog, QProgressBar, QWidget, QTableWidget, QTableWidgetItem, \
    QHeaderView, QAction, QTabWidget, QDialog, QMessageBox, QHBoxLayout, QMenuBar, QScrollArea
from PyQt5.QtCore import pyqtSignal, QCoreApplication

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

        # U-Werte Datensatz laden
        self.u_values_df = pd.read_csv(get_resource_path('lod2/data/standard_u_values_TABULA.csv'), sep=";")

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
        self.tableWidget.setRowCount(29)  # Anzahl der Eigenschaften
        self.tableWidget.setColumnCount(0)  # Starten ohne Spalten, da diese dynamisch hinzugefügt werden
        self.tableWidget.setVerticalHeaderLabels(['Adresse', 'UTM_X (m)', 'UTM_Y (m)', 'Grundfläche (m²)', 'Wandfläche (m²)', 'Dachfläche (m²)', 'Volumen (m³)', 'Stockwerke', 'Nutzungstyp', 'Gebäudetyp', 
                                          'Gebäudezustand', 'WW-Bedarf (kWh/m²)', 'Luftwechselrate (1/h)', 'Fensteranteil (%)', 'Türanteil (%)', 'Mindest-Außentemperatur (°C)', 'Raumtemperatur (°C)', 
                                          'Max. Heiz-Außentemperatur (°C)', 'U-Wert Wand (W/m²K)', 'U-Wert Dach (W/m²K)', 'U-Wert Fenster (W/m²K)', 'U-Wert Tür (W/m²K)', 'U-Wert Boden (W/m²K)', 
                                          'Typ_Heizflächen', 'VLT_max (°C)', 'Steigung_Heizkurve', 'RLT_max (°C)', 'Wärmebedarf (kWh)', 'Warmwasseranteil (%)'])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tableWidget.setSortingEnabled(False)  # Deaktiviert das Sortieren der Tabelle
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

        # Connect to table column selection event
        self.tableWidget.itemSelectionChanged.connect(self.on_table_column_select)

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
            self.saveDataAsGeoJSON(self.outputLOD2geojsonfilename)  # Direkte Speicherung der GeoJSON nach dem Laden

    def loadDataFromGeoJSON(self):
        self.vis_tab.loadNetData(self.outputLOD2geojsonfilename)

        # Standardwerte definieren
        self.STANDARD_VALUES = {
            'Stockwerke': 4, 'ww_demand_kWh_per_m2': 12.8, 'air_change_rate': 0.5, 'fracture_windows': 0.10, 
            'fracture_doors': 0.01, 'min_air_temp': -12, 'room_temp': 20, 'max_air_temp_heating': 15,
            'Typ_Heizflächen': 'HK', 'VLT_max': 70, 'Steigung_Heizkurve': 1.5, 'RLT_max': 55
        }

        self.building_info = process_lod2(self.outputLOD2geojsonfilename, self.STANDARD_VALUES)

        address_missing = any(info['Adresse'] is None for info in self.building_info.values())
        if address_missing:
            self.building_info = calculate_centroid_and_geocode(self.building_info)

        self.tableWidget.setColumnCount(len(self.building_info))
        self.tableWidget.setHorizontalHeaderLabels([str(i + 1) for i in range(len(self.building_info))])

        for col, (parent_id, info) in enumerate(self.building_info.items()):
            self.tableWidget.setItem(0, col, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
            self.tableWidget.setItem(1, col, QTableWidgetItem(str((info['Koordinate_X']))))
            self.tableWidget.setItem(2, col, QTableWidgetItem(str((info['Koordinate_Y']))))
            self.tableWidget.setItem(3, col, QTableWidgetItem(str(round(info['Ground_Area'], 1))))
            self.tableWidget.setItem(4, col, QTableWidgetItem(str(round(info['Wall_Area'], 1))))
            self.tableWidget.setItem(5, col, QTableWidgetItem(str(round(info['Roof_Area'], 1))))
            self.tableWidget.setItem(6, col, QTableWidgetItem(str(round(info['Volume'], 1))))
            self.tableWidget.setItem(7, col, QTableWidgetItem(str(info['Stockwerke'])))

            # SLP-Gebäudetyp ComboBox
            comboBoxTypes = QComboBox()
            comboBoxTypes.addItems(["HMF", "HEF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"])
            if info.get('Gebäudetyp') and info['Gebäudetyp'] in [comboBoxTypes.itemText(i) for i in range(comboBoxTypes.count())]:
                comboBoxTypes.setCurrentText(info['Gebäudetyp'])
            self.tableWidget.setCellWidget(8, col, comboBoxTypes)

            # TABULA-Gebäudeyp  ComboBox
            comboBoxBuildingTypes = QComboBox()
            comboBoxBuildingTypes.addItems(self.comboBoxBuildingTypesItems)
            comboBoxBuildingTypes.currentIndexChanged.connect(lambda idx, col=col: self.update_u_values(col))
            if info.get('Typ') and info['Typ'] in [comboBoxBuildingTypes.itemText(i) for i in range(comboBoxBuildingTypes.count())]:
                comboBoxBuildingTypes.setCurrentText(info['Typ'])
            self.tableWidget.setCellWidget(9, col, comboBoxBuildingTypes)

            # Gebäude Zustand ComboBox
            comboBoxBuildingState = QComboBox()
            comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment", "Individuell"])
            comboBoxBuildingState.currentIndexChanged.connect(lambda idx, col=col: self.update_u_values(col))
            if info.get('Gebäudezustand') and info['Gebäudezustand'] in [comboBoxBuildingState.itemText(i) for i in range(comboBoxBuildingState.count())]:
                comboBoxBuildingState.setCurrentText(info['Gebäudezustand'])
            self.tableWidget.setCellWidget(10, col, comboBoxBuildingState)

            # Weitere Werte setzen, falls vorhanden, ansonsten Standardwerte verwenden
            self.tableWidget.setItem(11, col, QTableWidgetItem(str(info['ww_demand_kWh_per_m2'])))
            self.tableWidget.setItem(12, col, QTableWidgetItem(str(info['air_change_rate'])))
            self.tableWidget.setItem(13, col, QTableWidgetItem(str(info['fracture_windows'])))
            self.tableWidget.setItem(14, col, QTableWidgetItem(str(info['fracture_doors'])))
            self.tableWidget.setItem(15, col, QTableWidgetItem(str(info['min_air_temp'])))
            self.tableWidget.setItem(16, col, QTableWidgetItem(str(info['room_temp'])))
            self.tableWidget.setItem(17, col, QTableWidgetItem(str(info['max_air_temp_heating'])))

            # U-Werte hinzufügen und aktualisieren
            self.update_u_values(col)

            # Neue Felder hinzufügen
            self.tableWidget.setItem(23, col, QTableWidgetItem(str(info['Typ_Heizflächen'])))
            self.tableWidget.setItem(24, col, QTableWidgetItem(str(info['VLT_max'])))
            self.tableWidget.setItem(25, col, QTableWidgetItem(str(info['Steigung_Heizkurve'])))
            self.tableWidget.setItem(26, col, QTableWidgetItem(str(info['RLT_max'])))

            # Laden des Wärmebedarfs, wenn vorhanden
            waermebedarf = info.get('Wärmebedarf', None)
            if waermebedarf is not None:
                self.tableWidget.setItem(27, col, QTableWidgetItem(str(waermebedarf)))

            # Laden des Warmwasseranteils, wenn vorhanden
            Warmwasseranteil = info.get('Warmwasseranteil', None)
            if Warmwasseranteil is not None:
                self.tableWidget.setItem(28, col, QTableWidgetItem(str(Warmwasseranteil)))  # Initial leer, wird später berechnet

            # Load 2D and 3D Visualization
            self.load3DVisualization()

    def update_u_values(self, col):
        building_type = self.tableWidget.cellWidget(9, col).currentText()
        building_state = self.tableWidget.cellWidget(10, col).currentText()

        if building_state != "Individuell":
            u_values = self.u_values_df[(self.u_values_df['Typ'] == building_type) & (self.u_values_df['building_state'] == building_state)]
            if not u_values.empty:
                u_values = u_values.iloc[0].to_dict()
                self.tableWidget.setItem(18, col, QTableWidgetItem(str(u_values['wall_u'])))
                self.tableWidget.setItem(19, col, QTableWidgetItem(str(u_values['roof_u'])))
                self.tableWidget.setItem(20, col, QTableWidgetItem(str(u_values['window_u'])))
                self.tableWidget.setItem(21, col, QTableWidgetItem(str(u_values['door_u'])))
                self.tableWidget.setItem(22, col, QTableWidgetItem(str(u_values['ground_u'])))
        else:
            self.tableWidget.setItem(18, col, QTableWidgetItem(''))
            self.tableWidget.setItem(19, col, QTableWidgetItem(''))
            self.tableWidget.setItem(20, col, QTableWidgetItem(''))
            self.tableWidget.setItem(21, col, QTableWidgetItem(''))
            self.tableWidget.setItem(22, col, QTableWidgetItem(''))

    def calculateHeatDemand(self):
        self.building_info = process_lod2(self.outputLOD2geojsonfilename, self.STANDARD_VALUES)

        for col in range(self.tableWidget.columnCount()):
            try:
                ground_area = float(self.tableWidget.item(3, col).text())
                wall_area = float(self.tableWidget.item(4, col).text())
                roof_area = float(self.tableWidget.item(5, col).text())
                volume = float(self.tableWidget.item(6, col).text())
                u_type = self.tableWidget.cellWidget(9, col).currentText()
                building_state = self.tableWidget.cellWidget(10, col).currentText()
                ww_demand_kWh_per_m2 = float(self.tableWidget.item(11, col).text())

                u_values = {
                    'wall_u': float(self.tableWidget.item(18, col).text()),
                    'roof_u': float(self.tableWidget.item(19, col).text()),
                    'window_u': float(self.tableWidget.item(20, col).text()),
                    'door_u': float(self.tableWidget.item(21, col).text()),
                    'ground_u': float(self.tableWidget.item(22, col).text())
                }

                building = Building(ground_area, wall_area, roof_area, volume, u_type=u_type, building_state=building_state, filename_TRY=self.parent.try_filename, u_values=u_values)
                building.calc_yearly_heat_demand()

                # Aktualisieren der GeoJSON-Datenstruktur mit den berechneten Daten
                parent_id = list(self.building_info.keys())[col]
                self.building_info[parent_id]['Wärmebedarf'] = building.yearly_heat_demand

                self.tableWidget.setItem(27, col, QTableWidgetItem(f"{building.yearly_heat_demand:.2f}"))
                self.tableWidget.setItem(28, col, QTableWidgetItem(f"{building.warm_water_share:.2f}"))
            except ValueError:
                QMessageBox.critical(self, "Fehler", f"Alle Felder müssen ausgefüllt sein (Spalte {col + 1}).")
                return

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
    def on_table_column_select(self):
        selected_columns = self.tableWidget.selectionModel().selectedColumns()
        if selected_columns:
            col = selected_columns[0].column()
            parent_id = list(self.building_info.keys())[col]
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
            #print(f"Processing building ID: {parent_id}")
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
    def saveDataAsGeoJSON(self, filename=False):
        try:
            print(filename)
            # Überprüfen, ob ein Dateiname übergeben wurde
            if filename is False:
                print("HERE")
                path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "GeoJSON-Dateien (*.geojson)")
                if not path:
                    print("Kein Pfad ausgewählt. Speichern abgebrochen.")
                    return
            else:
                path = filename

            # Laden der ursprünglichen GeoJSON-Datei
            with open(self.outputLOD2geojsonfilename, 'r', encoding='utf-8') as file:
                geojson_data = json.load(file)

            for col in range(self.tableWidget.columnCount()):
                for feature in geojson_data['features']:
                    properties = feature['properties']
                    parent_id = properties.get('parent_id')  # Annahme, dass parent_id eindeutig ist

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
                        properties['Nutzungstyp'] = self.tableWidget.cellWidget(8, col).currentText()
                        properties['Typ'] = self.tableWidget.cellWidget(9, col).currentText()
                        properties['Gebäudezustand'] = self.tableWidget.cellWidget(10, col).currentText()
                        properties['ww_demand_kWh_per_m2'] = float(self.tableWidget.item(11, col).text()) if self.tableWidget.item(11, col) else None
                        properties['air_change_rate'] = float(self.tableWidget.item(12, col).text()) if self.tableWidget.item(12, col) else None
                        properties['fracture_windows'] = float(self.tableWidget.item(13, col).text()) if self.tableWidget.item(13, col) else None
                        properties['fracture_doors'] = float(self.tableWidget.item(14, col).text()) if self.tableWidget.item(14, col) else None
                        properties['min_air_temp'] = float(self.tableWidget.item(15, col).text()) if self.tableWidget.item(15, col) else None
                        properties['room_temp'] = float(self.tableWidget.item(16, col).text()) if self.tableWidget.item(16, col) else None
                        properties['max_air_temp_heating'] = float(self.tableWidget.item(17, col).text()) if self.tableWidget.item(17, col) else None
                        properties['Typ_Heizflächen'] = self.tableWidget.item(23, col).text() if self.tableWidget.item(23, col) else None
                        properties['VLT_max'] = float(self.tableWidget.item(24, col).text()) if self.tableWidget.item(24, col) else None
                        properties['Steigung_Heizkurve'] = float(self.tableWidget.item(25, col).text()) if self.tableWidget.item(25, col) else None
                        properties['RLT_max'] = float(self.tableWidget.item(26, col).text()) if self.tableWidget.item(26, col) else None
                        properties['Wärmebedarf'] = float(self.tableWidget.item(27, col).text()) if self.tableWidget.item(27, col) else None
                        properties['Warmwasseranteil'] = float(self.tableWidget.item(28, col).text()) if self.tableWidget.item(28, col) else None

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
            try:
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
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Ein Fehler ist beim Öffnen der Datei aufgetreten: {str(e)}")

        QCoreApplication.processEvents()

    ### creating building csv for net generation ###
    def createBuildingCSV(self):
        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', 'WW_Anteil (%)', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', 'UTM_X', 'UTM_Y']
                writer.writerow(headers)

                for col in range(self.tableWidget.columnCount()):
                    land = self.tableWidget.item(0, col).text().split(", ")[3]
                    bundesland = self.tableWidget.item(0, col).text().split(", ")[2]
                    stadt = self.tableWidget.item(0, col).text().split(", ")[1]
                    address = self.tableWidget.item(0, col).text().split(", ")[0]
                    heat_demand = self.tableWidget.item(27, col).text() if self.tableWidget.item(27, col) else '0'
                    building_type = self.tableWidget.cellWidget(8, col).currentText()
                    ww_share = self.tableWidget.item(28, col).text() if self.tableWidget.item(28, col) else '0'
                    utm_x = self.tableWidget.item(1, col).text()
                    utm_y = self.tableWidget.item(2, col).text()

                    typ_heizflaechen = self.tableWidget.item(23, col).text() if self.tableWidget.item(23, col) else ""
                    vlt_max = self.tableWidget.item(24, col).text() if self.tableWidget.item(24, col) else ""
                    steigung_heizkurve = self.tableWidget.item(25, col).text() if self.tableWidget.item(25, col) else ""
                    rlt_max = self.tableWidget.item(26, col).text() if self.tableWidget.item(26, col) else ""

                    row_data = [
                        land,
                        bundesland,
                        stadt,
                        address,
                        heat_demand,
                        building_type,
                        ww_share,
                        typ_heizflaechen,
                        vlt_max,
                        steigung_heizkurve,
                        rlt_max,
                        utm_x,
                        utm_y
                    ]
                    writer.writerow(row_data)
                print(f"Daten wurden gespeichert: {path}")

