import sys
import os
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QComboBox, QPushButton, QGroupBox, \
    QHBoxLayout, QFileDialog, QProgressBar, QLabel, QWidget, QTableWidget, QTableWidgetItem, \
    QHeaderView, QScrollArea, QAction, QMainWindow
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal

from lod2.filter_LOD2 import spatial_filter_with_polygon, filter_LOD2_with_coordinates, process_lod2, calculate_centroid_and_geocode
from lod2.heat_requirement_DIN_EN_12831 import Building

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

class BuildingTab(QMainWindow):
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

        self.comboBoxBuildingTypesItems = pd.read_csv(get_resource_path('lod2\data\standard_u_values_TABULA.csv'), sep=";")['Typ'].unique().tolist()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Verarbeitung LOD2-Daten")
        self.setGeometry(200, 200, 1200, 1000)  # Anpassung der Fenstergröße

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create a scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        # Create a widget for scroll area contents
        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)

        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(10)  # Abstand zwischen den Widgets
        layout.setContentsMargins(10, 10, 10, 10)  # Rand des Layouts

        font = QFont()
        font.setPointSize(10)  # Größere Schrift für bessere Lesbarkeit
        
        # Group box for file inputs
        fileInputGroupBox = QGroupBox("File Inputs")
        fileInputLayout = QVBoxLayout(fileInputGroupBox)
        
        # Eingabefeld für die Eingabe-LOD2-geojson
        self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\lod2_data.geojson", font)
        fileInputLayout.addLayout(self.createFileInputLayout("Eingabe-LOD2-geojson:", self.inputLOD2geojsonLineEdit, self.inputLOD2geojsonButton, font))

        # Eingabefeld für die Eingabe-Filter-Polygon-shapefile
        self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\quartier_1.geojson", font)
        fileInputLayout.addLayout(self.createFileInputLayout("Eingabe-Filter-Polygon-shapefile:", self.inputfilterPolygonLineEdit, self.inputfilterPolygonButton, font))

        # Eingabefeld für die Eingabe-Filter-Gebäude-csv
        self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\data_output_ETRS89.csv", font)
        fileInputLayout.addLayout(self.createFileInputLayout("Eingabe-Filter-Gebäude-csv:", self.inputfilterBuildingDataLineEdit, self.inputfilterBuildingDataButton, font))

        # Eingabefeld für die Ausgabe-LOD2-geojson
        self.outputLOD2geojsonLineEdit, self.outputLOD2geojsonButton = self.createFileInput(f"{self.base_path}\\Gebäudedaten\\lod2_data\\filtered_LOD_quartier_1.geojson", font)
        fileInputLayout.addLayout(self.createFileInputLayout("Ausgabe-LOD2-geojson:", self.outputLOD2geojsonLineEdit, self.outputLOD2geojsonButton, font))
        
        layout.addWidget(fileInputGroupBox)
        
        # ComboBox for selecting filter method
        self.filterMethodComboBox = QComboBox(self)
        self.filterMethodComboBox.addItems(["Filter by Polygon", "Filter by Building Data CSV"])
        self.filterMethodComboBox.currentIndexChanged.connect(self.updateFilterInputVisibility)
        layout.addWidget(self.filterMethodComboBox)

        # Improved Table Widget
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(19)
        self.tableWidget.setHorizontalHeaderLabels(['Adresse', 'UTM_X', 'UTM_Y', 'Grundfläche', 'Wandfläche', 'Dachfläche', 'Volumen', 'Nutzungstyp', 'Typ', 'Gebäudezustand', 
                                                    'ww_demand_Wh_per_m2', 'air_change_rate', 'floors', 'fracture_windows', 'fracture_doors', 'min_air_temp', 
                                                    'room_temp', 'max_air_temp_heating', 'Jährlicher Wärmebedarf in kWh'])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.setSortingEnabled(True)  # Enable sorting
        self.tableWidget.setMinimumSize(800, 400)  # Set minimum size for the table
        layout.addWidget(self.tableWidget)

        # Matplotlib Figure
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(800, 400)  # Set minimum size for the canvas
        layout.addWidget(self.canvas)

        # Verbesserte Fortschrittsanzeige
        self.progressBar = QProgressBar(self)
        self.progressBar.setFont(font)
        layout.addWidget(self.progressBar)

        # Initial visibility setting
        self.updateFilterInputVisibility()

        # Create menu bar
        self.createMenuBar()

    def createMenuBar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        process_menu = menubar.addMenu("Process")
        dataset_menu = menubar.addMenu("Dataset")

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.loadDataFromFile)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.saveData)
        file_menu.addAction(save_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        process_filter_action = QAction("LOD2-Daten filtern und in Karte laden", self)
        process_filter_action.triggered.connect(self.processData)
        process_menu.addAction(process_filter_action)

        load_filtered_action = QAction("gefilterte Daten laden und anzeigen", self)
        load_filtered_action.triggered.connect(self.loadData)
        process_menu.addAction(load_filtered_action)

        calculate_heat_demand_action = QAction("Wärmebedarf berechnen", self)
        calculate_heat_demand_action.triggered.connect(self.calculateHeatDemand)
        process_menu.addAction(calculate_heat_demand_action)

        create_csv_action = QAction("Gebäude-csv für Netzgenerierung erstellen", self)
        create_csv_action.triggered.connect(self.createBuildingCSV)
        process_menu.addAction(create_csv_action)

        add_dataset_action = QAction("Datensatz hinzufügen", self)
        add_dataset_action.triggered.connect(self.addDataset)
        dataset_menu.addAction(add_dataset_action)

        remove_dataset_action = QAction("Datensatz entfernen", self)
        remove_dataset_action.triggered.connect(self.removeDataset)
        dataset_menu.addAction(remove_dataset_action)

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def createFileInput(self, default_path, font):
        lineEdit = QLineEdit(default_path)
        lineEdit.setFont(font)
        button = QPushButton("Durchsuchen")
        button.setFont(font)
        button.clicked.connect(lambda: self.selectFile(lineEdit))
        return lineEdit, button

    def createFileInputLayout(self, label_text, lineEdit, button, font):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        return layout

    def selectFile(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", "", "All Files (*)")
        if filename:
            lineEdit.setText(filename)

    def updateFilterInputVisibility(self):
        filter_method = self.filterMethodComboBox.currentText()
        if filter_method == "Filter by Polygon":
            self.inputfilterPolygonLineEdit.show()
            self.inputfilterBuildingDataLineEdit.hide()
            self.inputfilterPolygonButton.show()
            self.inputfilterBuildingDataButton.hide()
        elif filter_method == "Filter by Building Data CSV":
            self.inputfilterPolygonLineEdit.hide()
            self.inputfilterBuildingDataLineEdit.show()
            self.inputfilterPolygonButton.hide()
            self.inputfilterBuildingDataButton.show()

    def processData(self):
        filter_method = self.filterMethodComboBox.currentText()
        if filter_method == "Filter by Polygon":
            self.inputLOD2geojsonfilename = self.inputLOD2geojsonLineEdit.text()
            self.inputfilterPolygonfilename = self.inputfilterPolygonLineEdit.text()
            self.outputLOD2geojsonfilename = self.outputLOD2geojsonLineEdit.text()
            self.outputcsvfilename = f'{self.base_path}\\Gebäudedaten\\building_data.csv' # self.outputcsvLineEdit.text()
            spatial_filter_with_polygon(self.inputLOD2geojsonfilename, self.inputfilterPolygonfilename, self.outputLOD2geojsonfilename)
        elif filter_method == "Filter by Building Data CSV":
            self.inputLOD2geojsonfilename = self.inputLOD2geojsonLineEdit.text()
            self.inputfilterBuildingDatafilename = self.inputfilterBuildingDataLineEdit.text()
            self.outputLOD2geojsonfilename = self.outputLOD2geojsonLineEdit.text()
            self.outputcsvfilename = f'{self.base_path}\\Gebäudedaten\\building_data.csv' # self.outputcsvLineEdit.text()
            filter_LOD2_with_coordinates(self.inputLOD2geojsonfilename, self.inputfilterBuildingDatafilename, self.outputLOD2geojsonfilename)
        # Rufen Sie die loadNetData-Methode des Haupt-Tabs auf
        self.vis_tab.loadNetData(self.outputLOD2geojsonfilename)

    def loadData(self):
        STANDARD_VALUES = {
        'air_change_rate': 0.5, 'floors': 4, 'fracture_windows': 0.10, 'fracture_doors': 0.01,
        'min_air_temp': -15, 'room_temp': 20, 'max_air_temp_heating': 15, 'ww_demand_Wh_per_m2': 12800
        }
        # Annahme: Die process_lod2 Funktion wurde entsprechend erweitert, um Adressinformationen zu liefern
        self.outputLOD2geojsonfilename = self.outputLOD2geojsonLineEdit.text()
        building_info = process_lod2(self.outputLOD2geojsonfilename)

        # Überprüfen, ob die Adressinformationen fehlen und falls ja, die Berechnung durchführen
        address_missing = any(info['Adresse'] is None for info in building_info.values())
        if address_missing:
            building_info = calculate_centroid_and_geocode(building_info)

        self.tableWidget.setRowCount(len(building_info))  # Setze die Anzahl der Zeilen basierend auf den Daten

        for row, (parent_id, info) in enumerate(building_info.items()):
            self.tableWidget.setItem(row, 0, QTableWidgetItem(str(f"{info['Adresse']}, {info['Stadt']}, {info['Bundesland']}, {info['Land']}")))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(str((info['Koordinate_X']))))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(str((info['Koordinate_Y']))))
            self.tableWidget.setItem(row, 3, QTableWidgetItem(str(round(info['Ground_Area'],1))))
            self.tableWidget.setItem(row, 4, QTableWidgetItem(str(round(info['Wall_Area'],1))))
            self.tableWidget.setItem(row, 5, QTableWidgetItem(str(round(info['Roof_Area'],1))))
            self.tableWidget.setItem(row, 6, QTableWidgetItem(str(round(info['Volume'],1))))
            self.tableWidget.setItem(row, 10, QTableWidgetItem(str(STANDARD_VALUES['ww_demand_Wh_per_m2'])))
            self.tableWidget.setItem(row, 11, QTableWidgetItem(str(STANDARD_VALUES['air_change_rate'])))
            self.tableWidget.setItem(row, 12, QTableWidgetItem(str(STANDARD_VALUES['floors'])))
            self.tableWidget.setItem(row, 13, QTableWidgetItem(str(STANDARD_VALUES['fracture_windows'])))
            self.tableWidget.setItem(row, 14, QTableWidgetItem(str(STANDARD_VALUES['fracture_doors'])))
            self.tableWidget.setItem(row, 15, QTableWidgetItem(str(STANDARD_VALUES['min_air_temp'])))
            self.tableWidget.setItem(row, 16, QTableWidgetItem(str(STANDARD_VALUES['room_temp'])))
            self.tableWidget.setItem(row, 17, QTableWidgetItem(str(STANDARD_VALUES['max_air_temp_heating'])))

            comboBoxTypes = QComboBox()
            comboBoxTypes.addItems(["HMF", "HEF", "GHD", "GBD"])  # Dropdown-Optionen, hier muss noch erweitert werden und Möglichkeit geschaffen werden aus Datei zu laden
            self.tableWidget.setCellWidget(row, 7, comboBoxTypes)  # Korrigiere die Position für Nutzungstypen

            comboBoxBuildingTypes = QComboBox()
            comboBoxBuildingTypes.addItems(self.comboBoxBuildingTypesItems)  # Dropdown-Optionen
            self.tableWidget.setCellWidget(row, 8, comboBoxBuildingTypes)  # Korrigiere die Position für Nutzungstypen

            comboBoxBuildingState = QComboBox()
            comboBoxBuildingState.addItems(["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment"])  # Dropdown-Optionen
            self.tableWidget.setCellWidget(row, 9, comboBoxBuildingState)  # Korrigiere die Position für Nutzungstypen

    def saveData(self):
        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=";")
                headers = [self.tableWidget.horizontalHeaderItem(i).text() for i in range(self.tableWidget.columnCount())]
                writer.writerow(headers)
                for row in range(self.tableWidget.rowCount()):
                    rowData = []
                    for column in range(self.tableWidget.columnCount()):
                        if column in [7, 8, 9]:  # Spalten mit QComboBox
                            comboBox = self.tableWidget.cellWidget(row, column)
                            rowData.append(comboBox.currentText())
                        else:
                            item = self.tableWidget.item(row, column)
                            rowData.append(item.text() if item else '')
                    writer.writerow(rowData)

    def loadDataFromFile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'r', encoding='utf-8') as file:
                self.tableWidget.setRowCount(0)
                reader = csv.reader(file, delimiter=";")
                for rowIndex, row in enumerate(reader):
                    if rowIndex == 0:  # Überspringe die Kopfzeile
                        continue
                    self.tableWidget.insertRow(rowIndex - 1)
                    for columnIndex, value in enumerate(row):
                        if columnIndex in [7, 8, 9]:  # Spalten mit QComboBox
                            comboBox = self.createComboBox(columnIndex)
                            comboBox.setCurrentText(value)
                            self.tableWidget.setCellWidget(rowIndex - 1, columnIndex, comboBox)
                        else:
                            self.tableWidget.setItem(rowIndex - 1, columnIndex, QTableWidgetItem(value))

    def createComboBox(self, columnIndex):
        if columnIndex == 7:
            comboBoxItems = ["HMF", "HEF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"]
        elif columnIndex == 8:
            comboBoxItems = self.comboBoxBuildingTypesItems
        else:  # columnIndex == 9
            comboBoxItems = ["Existing_state", "Usual_Refurbishment", "Advanced_Refurbishment"]
        comboBox = QComboBox()
        comboBox.addItems(comboBoxItems)
        return comboBox
    
    def calculateHeatDemand(self):

        for row in range(self.tableWidget.rowCount()):
            ground_area = float(self.tableWidget.item(row, 3).text())
            wall_area = float(self.tableWidget.item(row, 4).text())
            roof_area = float(self.tableWidget.item(row, 5).text())
            volume = float(self.tableWidget.item(row, 6).text())
            u_type = self.tableWidget.cellWidget(row, 8).currentText()  # Typ
            building_state = self.tableWidget.cellWidget(row, 9).currentText()  # Gebäudezustand

            building = Building(ground_area, wall_area, roof_area, volume, u_type=u_type, building_state=building_state, filename_TRY=self.parent.try_filename)
            building.calc_yearly_heat_demand()
            
            print(building.yearly_heat_demand)
            self.tableWidget.setHorizontalHeaderLabels(['Adresse', 'UTM_X', 'UTM_Y','Grundfläche', 'Wandfläche', 'Dachfläche', 'Volumen', 'Nutzungstyp', 'Typ', 'Gebäudezustand', 
                                                    'ww_demand_Wh_per_m2', 'air_change_rate', 'floors', 'fracture_windows', 'fracture_doors', 'min_air_temp', 
                                                    'room_temp', 'max_air_temp_heating', 'Jährlicher Wärmebedarf in kWh'])
            self.tableWidget.setItem(row, 18, QTableWidgetItem(f"{building.yearly_heat_demand:.2f}"))  # Füge eine neue Spalte für die Ergebnisse hinzu

    def createBuildingCSV(self):
        # Standardwerte für die neuen Spalten
        standard_values = {
            'WW_Anteil': 0.2,  # Beispielwert, ersetze durch tatsächlichen Standardwert
            'Typ_Heizflächen': 'HK',  # Beispielwert
            'VLT_max': 70,  # Beispielwert
            'Steigung_Heizkurve': 1.5,  # Beispielwert
            'RLT_max': 55  # Beispielwert
        }

        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "CSV-Dateien (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                # Schreibe die Kopfzeile
                headers = ['Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf', 'Gebäudetyp', 'WW_Anteil', 'Typ_Heizflächen', 'VLT_max', 'Steigung_Heizkurve', 'RLT_max', 'UTM_X', 'UTM_Y']
                writer.writerow(headers)

                # Durchlaufe jede Zeile der Tabelle und extrahiere die benötigten Werte
                for row in range(self.tableWidget.rowCount()):
                    land = self.tableWidget.item(row, 0).text().split(", ")[3]
                    bundesland = self.tableWidget.item(row, 0).text().split(", ")[2]
                    stadt = self.tableWidget.item(row, 0).text().split(", ")[1]
                    address = self.tableWidget.item(row, 0).text().split(", ")[0]
                    heat_demand = self.tableWidget.item(row, 18).text() if self.tableWidget.item(row, 18) else '0'  # Beispiel, wie du auf den Wärmebedarf zugreifst
                    building_type = self.tableWidget.cellWidget(row, 7).currentText()  # Zugriff auf den Wert der ComboBox
                    utm_x = self.tableWidget.item(row, 1).text()
                    utm_y = self.tableWidget.item(row, 2).text()

                    # Erstelle eine Zeile mit den extrahierten und Standardwerten
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
                    # Schreibe die Zeile in die CSV-Datei
                    writer.writerow(row_data)
                print(f"Daten wurden gespeichert: {path}")

    def addDataset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Öffnen", "", "CSV-Dateien (*.csv)")
        if path:
            df = pd.read_csv(path, delimiter=';')
            self.loaded_data.append(df)
            self.loaded_filenames.append(os.path.basename(path))  # Speichern des Dateinamens
            self.updatePlot()

    def removeDataset(self):
        if self.loaded_data:
            self.loaded_data.pop()
            self.loaded_filenames.pop()  # Entfernen des zugehörigen Dateinamens
            self.updatePlot()

    def updatePlot(self):
        if not self.loaded_data:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Kombiniere alle geladenen Datensätze
        all_data = pd.concat(self.loaded_data, keys=self.loaded_filenames, names=['Filename', 'Index'])
        
        # Gruppiere die Daten nach Adresse und sammle die Wärmebedarfe
        all_data_grouped = all_data.groupby(['Adresse', 'Filename'])['Wärmebedarf'].sum().unstack('Filename').fillna(0)
        
        # Anzahl der Datensätze und Adressen
        num_datasets = len(self.loaded_data)
        num_addresses = len(all_data_grouped)
        
        # Balkenbreite und Positionen festlegen
        bar_width = 0.8 / num_datasets
        indices = np.arange(num_addresses)
        
        # Farben für die verschiedenen Datensätze
        colors = plt.cm.tab20.colors[:num_datasets]
        
        # Balken zeichnen
        for i, (filename, color) in enumerate(zip(all_data_grouped.columns, colors)):
            ax.barh(indices + i * bar_width, all_data_grouped[filename], bar_width, label=filename, color=color)

        # Achsenbeschriftungen und Legende
        ax.set_yticks(indices + bar_width * (num_datasets - 1) / 2)
        ax.set_yticklabels(all_data_grouped.index)
        ax.set_ylabel('Adresse')
        ax.set_xlabel('Wärmebedarf in kWh')
        ax.legend()
        
        self.canvas.draw()

