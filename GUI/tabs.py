import os
import logging
import numpy as np
import random
import geopandas as gpd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QMenuBar, QAction, \
    QFileDialog, QHBoxLayout, QComboBox, QLineEdit, QListWidget, QDialog, QFormLayout, \
        QScrollArea, QMessageBox, QProgressBar, QColorDialog, QListWidgetItem
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWebEngineWidgets import QWebEngineView

import folium

from main import initialize_net_profile_calculation, calculate_results, save_results_csv, import_results_csv, import_TRY
from GUI.dialogs import TechInputDialog, HeatDemandEditDialog, LayerGenerationDialog
from GUI.threads import CalculationThread
from net_test import config_plot
from heat_generators.heat_generator_classes import *
from net_generation.import_and_create_layers import generate_and_export_layers

class VisualizationTab(QWidget):
    layers_imported = pyqtSignal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.layers = {}
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # Initialisieren der Karte
        self.m = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
        self.mapView = QWebEngineView()
        # Erstellen der Menüleiste in tab1
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)  # Setzen Sie eine spezifische Höhe
        fileMenu = self.menuBar.addMenu('Datei')

        # Erstellen und Hinzufügen der Aktion "Import Netzdaten"
        importAction = QAction('Import Netzdaten', self)
        importAction.triggered.connect(self.importNetData)
        fileMenu.addAction(importAction)

        generateAction = QAction('Layer generieren', self)
        generateAction.triggered.connect(self.openLayerGenerationDialog)
        fileMenu.addAction(generateAction)

        # Fügen Sie die Menüleiste dem Layout von tab1 hinzu
        layout.addWidget(self.menuBar)
        
        # Fügen Sie das QWebEngineView-Widget zum Layout von tab1 hinzu
        self.updateMapView()

        layout.addWidget(self.mapView)

        ### Liste importierter Layer ###
        self.layerList = QListWidget(self)
        self.layerList.setMaximumHeight(100)  # Setzen Sie eine maximale Höhe

        self.removeLayerButton = QPushButton("Layer entfernen", self)
        self.removeLayerButton.clicked.connect(self.removeSelectedLayer)

        self.changeColorButton = QPushButton("Farbe ändern", self)
        self.changeColorButton.clicked.connect(self.changeLayerColor)

        layerManagementLayout = QHBoxLayout()
        layerManagementLayout.addWidget(self.layerList)
        layerManagementLayout.addWidget(self.removeLayerButton)
        layerManagementLayout.addWidget(self.changeColorButton)
        layout.addLayout(layerManagementLayout)

        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)

        self.setLayout(layout)

    def connect_signals(self, calculation_tab):
        calculation_tab.data_added.connect(self.updateMapViewWithData)

    def updateMapViewWithData(self, map_data):
        for data in map_data:
            # Hinzufügen der Daten zur Karte
            self.loadNetData(data)
        self.updateMapView()

    def openLayerGenerationDialog(self):
        dialog = LayerGenerationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            inputs = dialog.getInputs()
            self.generateAndImportLayers(inputs)

    def generateAndImportLayers(self, inputs):
        # Hier rufen Sie Ihre Funktion generate_and_export_layers auf
        generate_and_export_layers(inputs["streetLayer"], inputs["dataCsv"], 
                                float(inputs["xCoord"]), float(inputs["yCoord"]))

        # Automatisches Importieren der generierten Layer
        # Die Pfade zu den generierten Dateien müssen angegeben werden
        generatedLayers = {
            'HAST': "C:/Users/username/heating_network_generation/net_generation/HAST.geojson",
            'Rücklauf': "C:/Users/username/heating_network_generation/net_generation/Rücklauf.geojson",
            'Vorlauf': "C:/Users/username/heating_network_generation/net_generation/Vorlauf.geojson",
            'Erzeugeranlagen': "C:/Users/username/heating_network_generation/net_generation/Erzeugeranlagen.geojson"
        }

        for layerName, layerFile in generatedLayers.items():
            self.loadNetData(layerFile)

        # Auslösen des Signals mit den Pfaden der generierten Layer
        self.layers_imported.emit(generatedLayers)

    def importNetData(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Netzdaten importieren', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fnames:
            layerNames = {}
            for fname in fnames:
                self.loadNetData(fname)
                basename = os.path.basename(fname)
                layerNames[basename.split('.')[0]] = fname  # Beispiel: 'HAST' : 'path/to/HAST.geojson'
            self.layers_imported.emit(layerNames)
            self.updateMapView()
    
    def calculate_map_center_and_zoom(self):
        if not self.layers:  # Wenn keine Layer vorhanden sind
            return [51.1657, 10.4515], 6  # Standardwerte

        # Berechnen der kombinierten Grenzen aller Layer
        minx, miny, maxx, maxy = None, None, None, None
        for layer in self.layers.values():
            bounds = layer.get_bounds()
            if minx is None or bounds[0][0] < minx:
                minx = bounds[0][0]
            if miny is None or bounds[0][1] < miny:
                miny = bounds[0][1]
            if maxx is None or bounds[1][0] > maxx:
                maxx = bounds[1][0]
            if maxy is None or bounds[1][1] > maxy:
                maxy = bounds[1][1]

        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        zoom = 15  # Sie müssen möglicherweise einen Algorithmus entwickeln, um ein geeignetes Zoomlevel zu berechnen

        return [center_x, center_y], zoom
    
    def updateMapView(self):
        center, zoom = self.calculate_map_center_and_zoom()
        self.m = folium.Map(location=center, zoom_start=zoom)
        for layer in self.layers.values():
            self.m.add_child(layer)
        self.update_map_view(self.mapView, self.m)

    def loadNetData(self, filename, color=None):
        if color is None:
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))  # Zufällige Farbe, falls keine angegeben

        layer = self.addGeoJsonLayer(self.m, filename, color)
        if layer is not None:
            self.layers[filename] = layer

            # Überprüfen, ob der Layer bereits in der Liste ist
            if filename not in [self.layerList.item(i).text() for i in range(self.layerList.count())]:
                # Fügen Sie den Layer-Namen zum QListWidget hinzu, wenn er neu ist
                listItem = QListWidgetItem(filename)
                listItem.setBackground(QColor(color))  # Setzen Sie die Hintergrundfarbe
                listItem.setForeground(QBrush(QColor('#FFFFFF')))  # Setzen Sie eine kontrastreiche Textfarbe
                self.layerList.addItem(listItem)

            self.updateMapView()

    def load_geojson_data(self, filename):
        """ Lädt GeoJSON-Daten und gibt ein Geopandas DataFrame zurück """
        return gpd.read_file(filename)

    def update_map_view(self, mapView, map_obj):
        """ Aktualisiert die Kartenansicht in PyQt """
        map_file = 'map.html'
        map_obj.save(map_file)
        mapView.load(QUrl.fromLocalFile(os.path.abspath(map_file)))

    def addGeoJsonLayer(self, m, filename, color):
        gdf = self.load_geojson_data(filename)
        geojson_layer = folium.GeoJson(
            gdf,
            name=os.path.basename(filename),
            style_function=lambda feature: {
                'fillColor': color,
                'color': color,
                'weight': 1.5,
                'fillOpacity': 0.5,
            }
        )
        geojson_layer.add_to(m)
        return geojson_layer

    def removeSelectedLayer(self):
        selectedItems = self.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            self.layerList.takeItem(self.layerList.row(selectedItem))
            del self.layers[layerName]
            self.updateMapView()

    def changeLayerColor(self):
        selectedItems = self.layerList.selectedItems()
        if selectedItems:
            selectedItem = selectedItems[0]
            layerName = selectedItem.text()
            
            color = QColorDialog.getColor()
            if color.isValid():
                self.updateLayerColor(layerName, color.name())

    def updateLayerColor(self, layerName, new_color):
        if layerName in self.layers:
            # Entfernen des alten Layers
            del self.layers[layerName]
            
            # Neuerstellen des Layers mit der neuen Farbe
            self.loadNetData(layerName, new_color)

            # Aktualisieren Sie die Farbe im QListWidget
            self.updateListItemColor(layerName, new_color)

    def updateListItemColor(self, layerName, new_color):
        for index in range(self.layerList.count()):
            listItem = self.layerList.item(index)
            if listItem.text() == layerName:
                listItem.setBackground(QColor(new_color))
                listItem.setForeground(QBrush(QColor('#FFFFFF')))  # Weiße Textfarbe für Kontrast
                break

class CalculationTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    DEFAULT_PATHS = {
        'Erzeugeranlagen': 'net_generation_QGIS/Beispiel Zittau/Erzeugeranlagen.geojson',
        'HAST': 'net_generation_QGIS/Beispiel Zittau/HAST.geojson',
        'Vorlauf': 'net_generation_QGIS/Beispiel Zittau/Vorlauf.geojson',
        'Rücklauf': 'net_generation_QGIS/Beispiel Zittau/Rücklauf.geojson',
        'Ausgabe': 'results_time_series_net1.csv'
    }

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.initUI()

    def updateFilePaths(self, layerNames):
        for key, path in layerNames.items():
            if key in self.DEFAULT_PATHS:
                inputAttrName = f"{key}Input"
                if hasattr(self, inputAttrName):
                    getattr(self, inputAttrName).setText(path)
                    
    def initUI(self):
        # Erstellen eines Scrollbereichs
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        # Erstellen eines Container-Widgets für den Scrollbereich
        container_widget = QWidget()
        scroll_area.setWidget(container_widget)

        # Erstellen eines Layouts für das Container-Widget
        self.container_layout = QVBoxLayout(container_widget)

        # Hier fügen Sie alle Ihre vorhandenen Setup-Funktionen hinzu
        self.setupFileInputs()
        self.setupHeatDemandEditor()
        self.setupControlInputs()
        self.setupPlotLayout()

        # Hauptlayout für das Tab
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(scroll_area)
        self.setLayout(self.main_layout)

        self.progressBar = QProgressBar(self)
        self.container_layout.addWidget(self.progressBar)

    def setupFileInputs(self):
        # Verwenden Sie ein Grid-Layout für eine saubere Anordnung
        form_layout = QFormLayout()

        # Erstellen Sie die Textfelder und Buttons und fügen Sie sie dem Layout hinzu
        form_layout.addRow(self.createFileInput('ErzeugeranlagenInput', self.DEFAULT_PATHS['Erzeugeranlagen'], 'geoJSON Erzeugeranlagen auswählen'))
        form_layout.addRow(self.createFileInput('HASTInput', self.DEFAULT_PATHS['HAST'], 'geoJSON Hausanschlussstationen auswählen'))
        form_layout.addRow(self.createFileInput('VorlaufInput', self.DEFAULT_PATHS['Vorlauf'], 'geoJSON Vorlaufleitungen auswählen'))
        form_layout.addRow(self.createFileInput('RücklaufInput', self.DEFAULT_PATHS['Rücklauf'], 'geoJSON Rücklaufleitungen auswählen'))
        form_layout.addRow(self.createFileInput('AusgabeInput', self.DEFAULT_PATHS['Ausgabe'], 'Ergebnis-CSV auswählen'))

        self.container_layout.addLayout(form_layout)

    def createFileInput(self, attr_name, default_text, button_tooltip):
        # Erstelle ein horizontales Layout
        file_input_layout = QHBoxLayout()

        # Erstelle das QLineEdit Widget
        line_edit = QLineEdit(default_text)
        line_edit.setPlaceholderText(button_tooltip)
        setattr(self, attr_name, line_edit)

        # Erstelle den Button
        button = QPushButton("Datei auswählen")
        button.setToolTip(button_tooltip)
        button.clicked.connect(lambda: self.selectFilename(line_edit))

        # Füge Widgets zum Layout hinzu
        file_input_layout.addWidget(line_edit)
        file_input_layout.addWidget(button)

        return file_input_layout
    
    def setupHeatDemandEditor(self):
        # Erstelle einen "Bearbeiten"-Button
        editButton = QPushButton("Hausanschlussstationen/Wärmeübertrager Bearbeiten", self)
        editButton.clicked.connect(self.editHeatDemandData)
        self.container_layout.addWidget(editButton)

    def editHeatDemandData(self):
        try:
            self.gdf_HAST = gpd.read_file(self.HASTInput.text())
            if "Gebäudetyp" not in self.gdf_HAST.columns:
                self.gdf_HAST["Gebäudetyp"] = "HMF"

            self.dialog = HeatDemandEditDialog(self.gdf_HAST, self)
            self.dialog.exec_()  # Öffnet den Dialog als Modal
        except Exception as e:
            logging.error(f"Fehler beim Laden der HAST-Daten: {e}")
            QMessageBox.critical(self, "Fehler", "Fehler beim Laden der HAST-Daten.")

    def updateLabelsForCalcMethod(self):
        calc_method = self.CalcMethodInput.currentText()
        if calc_method in ["BDEW", "Datensatz"]:  # Angenommen, diese Methoden verwenden 1h-Werte
            time_step_text = "Zeitschritt (1h Werte); Minimum: 0, Maximum: 8760 (1 Jahr) :"
        else:  # Für VDI4655 oder andere Methoden, die 15-min-Werte verwenden
            time_step_text = "Zeitschritt (15 min Werte); Minimum: 0, Maximum: 35040 (1 Jahr) :"

        self.StartTimeStepLabel.setText(time_step_text)
        self.EndTimeStepLabel.setText(time_step_text)

    def setupControlInputs(self):
        # Initialisiere Combobox für Berechnungsmethoden
        self.CalcMethodInput = QComboBox(self)
        self.CalcMethodInput.addItems(["Datensatz", "BDEW", "VDI4655"])
        self.CalcMethodInput.setToolTip("Wählen Sie die Berechnungsmethode")
        self.CalcMethodInput.currentIndexChanged.connect(self.updateBuildingType)

        # Initialisiere Combobox für Gebäudetypen
        self.BuildingTypeInput = QComboBox(self)
        self.BuildingTypeInput.setToolTip("Wählen Sie den Gebäudetyp")
        self.updateBuildingType()  # Aktualisierung der BuildingTypeInput beim Start

        # Buttons für die Berechnung und Initialisierung
        self.initializeNetButton = QPushButton('Netz generieren und initialisieren')
        self.calculateNetButton = QPushButton('Zeitreihenberechnung durchführen')
        self.LayerImportButton = QPushButton('Layers in Karte importieren')

        # Verbindungen für die Buttons
        self.initializeNetButton.clicked.connect(self.create_and_initialize_net)
        self.calculateNetButton.clicked.connect(self.simulate_net)
        self.LayerImportButton.clicked.connect(self.ImportLayers)

        # Layout für die Steuerelemente
        controls_layout = QVBoxLayout()
        controls_layout.addWidget(self.LayerImportButton)
        controls_layout.addWidget(self.CalcMethodInput)
        controls_layout.addWidget(self.BuildingTypeInput)
        controls_layout.addWidget(self.initializeNetButton)
        self.container_layout.addLayout(controls_layout)

        # Eingabefeld für den Startzeitpunkt der Simulation
        self.StartTimeStepLabel = QLabel("", self)
        self.StartTimeStepInput = QLineEdit("0", self)
        # Eingabefeld für den Endzeitpunkt der Simulation
        self.EndTimeStepLabel = QLabel("", self)
        self.EndTimeStepInput = QLineEdit("96", self)

        self.CalcMethodInput.currentIndexChanged.connect(self.updateBuildingType)
        self.CalcMethodInput.currentIndexChanged.connect(self.updateLabelsForCalcMethod)
        self.updateLabelsForCalcMethod()  # Aktualisiere Labels beim Start

        # Button zur Ausführung der Zeitreihenberechnung
        self.calculateNetButton = QPushButton('Zeitreihenberechnung durchführen', self)
        self.calculateNetButton.clicked.connect(self.simulate_net)

        # Layout für die Zeitsteuerungselemente
        startTimeLayout = QHBoxLayout()
        startTimeLayout.addWidget(self.StartTimeStepLabel)
        startTimeLayout.addWidget(self.StartTimeStepInput)

        endTimeLayout = QHBoxLayout()
        endTimeLayout.addWidget(self.EndTimeStepLabel)
        endTimeLayout.addWidget(self.EndTimeStepInput)

        # Hinzufügen der Layouts zum Hauptlayout
        self.container_layout.addLayout(startTimeLayout)
        self.container_layout.addLayout(endTimeLayout)
        self.container_layout.addWidget(self.calculateNetButton)

    def setupPlotLayout(self):
        self.scrollArea = QScrollArea(self)  # Erstelle ein ScrollArea-Widget
        self.scrollWidget = QWidget()  # Erstelle ein Widget für den Inhalt der ScrollArea
        self.scrollLayout = QVBoxLayout(self.scrollWidget)  # Erstelle ein Layout für das Scroll-Widget

        self.figure3 = Figure()
        self.canvas3 = FigureCanvas(self.figure3)
        self.canvas3.setMinimumSize(500, 500)  # Setze eine Mindestgröße für die Canvas
        self.toolbar3 = NavigationToolbar(self.canvas3, self)

        self.figure4 = Figure()
        self.canvas4 = FigureCanvas(self.figure4)
        self.canvas4.setMinimumSize(500, 500)  # Setze eine Mindestgröße für die Canvas
        self.toolbar4 = NavigationToolbar(self.canvas4, self)

        self.figure5 = Figure()
        self.canvas5 = FigureCanvas(self.figure5)
        self.canvas5.setMinimumSize(500, 500)  # Setze eine Mindestgröße für die Canvas
        self.toolbar5 = NavigationToolbar(self.canvas5, self)

        # Fügen Sie die Diagramme und Toolbars zum Container-Layout hinzu
        self.scrollLayout.addWidget(self.canvas4)
        self.scrollLayout.addWidget(self.toolbar4)
        self.scrollLayout.addWidget(self.canvas5)
        self.scrollLayout.addWidget(self.toolbar5)
        self.scrollLayout.addWidget(self.canvas3)
        self.scrollLayout.addWidget(self.toolbar3)

        # Setze das Scroll-Widget als Inhalt der ScrollArea
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)  # Erlaubt das Resize der Inhalte innerhalb der ScrollArea

        # Füge die ScrollArea zum Hauptlayout hinzu
        self.container_layout.addWidget(self.scrollArea)

    def ImportLayers(self):
        vl = self.VorlaufInput.text()
        rl = self.RücklaufInput.text()
        HAST = self.HASTInput.text()
        WEA = self.ErzeugeranlagenInput.text()
        
        # Daten zur zentralen Datenquelle hinzufügen
        self.data_manager.add_data(vl)
        self.data_manager.add_data(rl)
        self.data_manager.add_data(HAST)
        self.data_manager.add_data(WEA)
        
        # Signal senden, dass Daten hinzugefügt wurden
        self.data_added.emit(self.data_manager.get_map_data())
    
    def selectFilename(self, inputWidget):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'All Files (*);;CSV Files (*.csv);;Data Files (*.dat)')
        if fname:  # Prüfen, ob ein Dateiname ausgewählt wurde
            inputWidget.setText(fname)

    def updateBuildingType(self):
        # Aktualisieren der BuildingTypeInput-Elemente
        self.BuildingTypeInput.clear()
        if self.CalcMethodInput.currentText() == "VDI4655":
            self.BuildingTypeInput.setDisabled(False)
            self.BuildingTypeInput.addItems(["EFH", "MFH"])
        elif self.CalcMethodInput.currentText() == "BDEW":
            self.BuildingTypeInput.setDisabled(False)
            self.BuildingTypeInput.addItems(["HEF", "HMF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"])
        elif self.CalcMethodInput.currentText() == "Datensatz":
            self.BuildingTypeInput.setDisabled(True)  # Deaktiviere das Auswahlfeld für Gebäudetypen

    def create_and_initialize_net(self):
        gdf_vl = gpd.read_file(self.VorlaufInput.text())
        gdf_rl = gpd.read_file(self.RücklaufInput.text())
        gdf_HAST = gpd.read_file(self.HASTInput.text())
        gdf_WEA = gpd.read_file(self.ErzeugeranlagenInput.text())

        calc_method = self.CalcMethodInput.currentText()
        building_type = None if calc_method == "Datensatz" else self.BuildingTypeInput.currentText()

        net, yearly_time_steps, waerme_ges_W = initialize_net_profile_calculation(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type=building_type, calc_method=calc_method)
        
        waerme_ges_kW = np.where(waerme_ges_W == 0, 0, waerme_ges_W / 1000)

        self.plot(yearly_time_steps, waerme_ges_kW, net)

    def plot(self, time_steps, qext_kW, net):
        # Clear previous figure
        self.figure4.clear()
        ax1 = self.figure4.add_subplot(111)

        # Plot für Wärmeleistung auf der ersten Y-Achse
        for i, q in enumerate(qext_kW):
            ax1.plot(time_steps, q, 'b-', label=f"Last Gebäude {i}")
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Wärmebedarf in kW", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc='upper left')
        ax1.plot
        ax1.grid()
        self.canvas4.draw()

        self.figure5.clear()
        ax = self.figure5.add_subplot(111)
        config_plot(net, ax, show_junctions=True, show_pipes=True, show_flow_controls=False, show_heat_exchangers=True)
        self.canvas5.draw()

    def adjustTimeParameters(self):
        calc_method = self.CalcMethodInput.currentText()
        try:
            calc1 = int(self.StartTimeStepInput.text())
            calc2 = int(self.EndTimeStepInput.text())

            if calc_method in ["BDEW", "Datensatz"]:  # Angenommen, diese Methoden verwenden 1h-Werte
                max_time_step = 8760  # 1 Jahr in Stunden
            else:  # Für VDI4655 oder andere Methoden, die 15-min-Werte verwenden
                max_time_step = 35040  # 1 Jahr in 15-min-Intervallen

            if not (0 <= calc1 <= max_time_step and 0 <= calc2 <= max_time_step):
                raise ValueError("Zeitschritt außerhalb des gültigen Bereichs")
            
            if not calc1 < calc2:
                raise ValueError("Der 1. Zeitschritt muss kleiner als der 2. Zeitschritt sein")

            return calc1, calc2

        except ValueError as e:
            QMessageBox.warning(self, "Ungültige Eingabe", str(e))
            return None, None
        
    def simulate_net(self):
        gdf_vl = gpd.read_file(self.VorlaufInput.text())
        gdf_rl = gpd.read_file(self.RücklaufInput.text())
        gdf_HAST = gpd.read_file(self.HASTInput.text())
        gdf_WEA = gpd.read_file(self.ErzeugeranlagenInput.text())

        calc_method = self.CalcMethodInput.currentText()
        building_type = None if calc_method == "Datensatz" else self.BuildingTypeInput.currentText()

        try:
            calc1, calc2 = self.adjustTimeParameters()
            if calc1 is None or calc2 is None:  # Ungültige Eingaben wurden bereits in adjustTimeParameters behandelt
                return

            self.calculationThread = CalculationThread(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type, calc_method, calc1, calc2)
            self.calculationThread.calculation_done.connect(self.on_calculation_done)
            self.calculationThread.calculation_error.connect(self.on_calculation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

        except ValueError as e:
            QMessageBox.warning("Ungültige Eingabe", str(e))

    def on_calculation_done(self, results):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus
        time_steps, net, net_results = results
        mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
            return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

        self.plot2(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)

        output_filename = self.AusgabeInput.text()
        save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, output_filename)

    def on_calculation_error(self, error_message):
        QMessageBox.critical(self, "Berechnungsfehler", error_message)
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus

    def closeEvent(self, event):
        if hasattr(self, 'calculationThread') and self.calculationThread.isRunning():
            reply = QMessageBox.question(self, 'Thread läuft noch',
                                         "Eine Berechnung läuft noch. Wollen Sie wirklich beenden?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.calculationThread.stop()  # Stellen Sie sicher, dass der Thread beendet wird
                event.accept()  # Schließen Sie das Fenster
            else:
                event.ignore()  # Lassen Sie das Fenster offen
        else:
            event.accept()  # Schließen Sie das Fenster, wenn kein Thread läuft
    def plot2(self, time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump):
        # Clear previous figure
        self.figure3.clear()
        ax1 = self.figure3.add_subplot(111)

        # Plot für Wärmeleistung auf der ersten Y-Achse
        ax1.plot(time_steps, qext_kW, 'b-', label="Gesamtlast")
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Wärmebedarf in kW", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc='upper left')
        ax1.grid()
        ax1.plot

        # Zweite Y-Achse für die Temperatur
        ax2 = ax1.twinx()
        ax2.plot(time_steps, return_temp_circ_pump, 'm-o', label="circ pump return temperature")
        ax2.plot(time_steps, flow_temp_circ_pump, 'c-o', label="circ pump flow temperature")
        ax2.set_ylabel("temperature [°C]", color='m')
        ax2.tick_params('y', colors='m')
        ax2.legend(loc='upper right')
        ax2.set_ylim(0,100)

        self.canvas3.draw()

class MixDesignTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()

    def initFileInputs(self):
        # Ergebnis-CSV Input
        self.FilenameInput = QLineEdit('results_time_series_net.csv')
        self.selectFileButton = QPushButton('Ergebnis-CSV auswählen')
        self.selectFileButton.clicked.connect(lambda: self.selectFilename(self.FilenameInput))

        # TRY-Datei Input
        self.tryFilenameInput = QLineEdit('heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat')
        self.selectTRYFileButton = QPushButton('TRY-Datei auswählen')
        self.selectTRYFileButton.clicked.connect(lambda: self.selectFilename(self.tryFilenameInput))

        # COP-Datei Input
        self.copFilenameInput = QLineEdit('heat_generators/Kennlinien WP.csv')
        self.selectCOPFileButton = QPushButton('COP-Datei auswählen')
        self.selectCOPFileButton.clicked.connect(lambda: self.selectFilename(self.copFilenameInput))

    def initUI(self):
        layout = QVBoxLayout()
        
        self.DatenEingabeLabel = QLabel('Dateneingaben')
        layout.addWidget(self.DatenEingabeLabel)

        # Hinzufügen zum Layout
        filemain_layout = QHBoxLayout()
        filemain_layout.addWidget(self.FilenameInput)
        filemain_layout.addWidget(self.selectFileButton)
        layout.addLayout(filemain_layout)

        # Hinzufügen zum Layout
        fileLayout2 = QHBoxLayout()
        fileLayout2.addWidget(self.tryFilenameInput)
        fileLayout2.addWidget(self.selectTRYFileButton)
        layout.addLayout(fileLayout2)

        # Hinzufügen zum Layout
        fileLayout3 = QHBoxLayout()
        fileLayout3.addWidget(self.copFilenameInput)
        fileLayout3.addWidget(self.selectCOPFileButton)
        layout.addLayout(fileLayout3)
        
        self.costEingabeLabel = QLabel('Wirtschaftliche Vorgaben')
        layout.addWidget(self.costEingabeLabel)

        # Parameter Inputs
        self.gaspreisInput = QLineEdit("70")
        self.strompreisInput = QLineEdit("150")
        self.holzpreisInput = QLineEdit("50")
        self.BEWComboBox = QComboBox()
        self.BEWOptions = ["Nein", "Ja"]
        self.BEWComboBox.addItems(self.BEWOptions)

        # Labels
        self.gaspreisLabel = QLabel('Gaspreis (€/MWh):')
        self.strompreisLabel = QLabel('Strompreis (€/MWh):')
        self.holzpreisLabel = QLabel('Holzpreis (€/MWh):')
        self.BEWLabel = QLabel('Berücksichtigung BEW-Förderung?:')

        # Buttons
        self.calculateButton = QPushButton('Berechnen')
        self.calculateButton.clicked.connect(self.calculate)

        # Buttons
        self.optimizeButton = QPushButton('Optimieren')
        self.optimizeButton.clicked.connect(self.optimize)

         # Erstellen Sie das QListWidget
        self.techList = QListWidget()

        # ComboBox zur Auswahl der Technologie
        self.techComboBox = QComboBox()
        self.techOptions = ["Solarthermie", "BHKW", "Holzgas-BHKW", "Geothermie", "Abwärme", "Biomassekessel", "Gaskessel"]
        self.techComboBox.addItems(self.techOptions)

        # Buttons zum Hinzufügen und Entfernen
        self.btnAddTech = QPushButton("Technologie hinzufügen")
        self.btnRemoveTech = QPushButton("Alle Technologien entfernen")

        # Button-Events
        self.btnAddTech.clicked.connect(self.addTech)
        self.btnRemoveTech.clicked.connect(self.removeTech)

        # Erstellen eines horizontalen Layouts für die Buttons
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.btnAddTech)
        buttonLayout.addWidget(self.btnRemoveTech)

        # Layout for inputs
        inputLayout = QHBoxLayout()
        inputLayout.addWidget(self.gaspreisLabel)
        inputLayout.addWidget(self.gaspreisInput)
        inputLayout.addWidget(self.strompreisLabel)
        inputLayout.addWidget(self.strompreisInput)
        inputLayout.addWidget(self.holzpreisLabel)
        inputLayout.addWidget(self.holzpreisInput)
        inputLayout.addWidget(self.BEWLabel)
        inputLayout.addWidget(self.BEWComboBox)

        self.techEingabeLabel = QLabel('Auswahl Erzeugungstechnologien')
        self.calculateEingabeLabel = QLabel('Berechnung des Erzeugermixes und der Wärmegestehungskosten anhand der Inputdaten')
        self.optimizeEingabeLabel = QLabel('Optimierung der Zusammensetzung des Erzeugermixes zur Minimierung der Wärmegestehungskosten. Berechnung kann einige Zeit dauern.')

        self.load_scale_factorLabel = QLabel('Lastgang skalieren?:')
        self.load_scale_factorInput = QLineEdit("1")

        # Result Label
        self.resultLabel = QLabel('Ergebnisse werden hier angezeigt')

        # Diagramm-Layout
        chartLayout = QHBoxLayout()

        # Erstes Diagramm
        self.figure1 = Figure()
        self.canvas1 = FigureCanvas(self.figure1)
        
        # Zweites Diagramm
        self.figure2 = Figure()
        self.canvas2 = FigureCanvas(self.figure2)

        # Füge die Canvas-Widgets zum Diagramm-Layout hinzu
        chartLayout.addWidget(self.canvas1)
        chartLayout.addWidget(self.canvas2)


        # Add widgets to layout
        layout.addLayout(inputLayout)
        layout.addWidget(self.techEingabeLabel)
        layout.addWidget(self.techComboBox)
        layout.addLayout(buttonLayout)
        layout.addWidget(self.techList)
        layout.addWidget(self.load_scale_factorLabel)
        layout.addWidget(self.load_scale_factorInput)
        layout.addWidget(self.calculateEingabeLabel)
        layout.addWidget(self.calculateButton)
        layout.addWidget(self.optimizeEingabeLabel)
        layout.addWidget(self.optimizeButton)
        layout.addWidget(self.resultLabel)
        layout.addLayout(chartLayout)

        self.setLayout(layout)
        
    def optimize(self):
        self.calculate(True)

    def calculate(self, optimize=False, load_scale_factor=1):
        filename = self.FilenameInput.text()
        time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump = import_results_csv(filename)
        calc1, calc2 = 0, len(time_steps)

        load_scale_factor = float(self.load_scale_factorInput.text())
        qext_kW *= load_scale_factor

        #plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)
        initial_data = time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump

        TRY = import_TRY(self.tryFilenameInput.text())
        COP_data = np.genfromtxt(self.copFilenameInput.text(), delimiter=';')
        
        Gaspreis = float(self.gaspreisInput.text())
        Strompreis = float(self.strompreisInput.text())
        Holzpreis = float(self.holzpreisInput.text())
        BEW = self.BEWComboBox.itemText(self.BEWComboBox.currentIndex())
        techs = self.tech_objects 

        if optimize == True:
            techs = optimize_mix(techs, initial_data, calc1, calc2, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW)

        WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, Wärmemengen, WGK, Anteile, specific_emissions  = \
        Berechnung_Erzeugermix(techs, initial_data, calc1, calc2, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW)
        
        self.showResults(Jahreswärmebedarf, WGK_Gesamt, techs, Wärmemengen, WGK, Anteile)

        # Example of plotting
        self.plot1(time_steps, data_L, data_labels_L, Anteile, Last_L)

    def plot1(self, t, data_L, data_labels_L, Anteile, Last_L):
        # Clear previous figure
        self.figure1.clear()
        self.figure2.clear()

        ax1 = self.figure1.add_subplot(111)
        ax2 = self.figure2.add_subplot(111)

        #ax1.plot(t, Last_L, color="black", linewidth=0.05, label="Last in kW")
        ax1.stackplot(t, data_L, labels=data_labels_L)
        ax1.set_title("Jahresdauerlinie")
        ax1.set_xlabel("Jahresstunden")
        ax1.set_ylabel("thermische Leistung in kW")
        ax1.legend(loc='upper center')
        ax1.grid()
        ax1.plot
        self.canvas1.draw()

        ax2.pie(Anteile, labels=data_labels_L, autopct='%1.1f%%', startangle=90)
        ax2.set_title("Anteile Wärmeerzeugung")
        ax2.legend(loc='lower left')
        ax2.axis("equal")
        ax2.plot
        self.canvas2.draw()

    def showResults(self, Jahreswärmebedarf, WGK_Gesamt, techs, Wärmemengen, WGK, Anteile):
        resultText = f"Jahreswärmebedarf: {Jahreswärmebedarf:.2f} MWh\n"
        resultText += f"Wärmegestehungskosten Gesamt: {WGK_Gesamt:.2f} €/MWh\n\n"

        for tech, wärmemenge, anteil, wgk in zip(techs, Wärmemengen, Anteile, WGK):
            resultText += f"Wärmemenge {tech.name}: {wärmemenge:.2f} MWh\n"
            resultText += f"Wärmegestehungskosten {tech.name}: {wgk:.2f} €/MWh\n"
            resultText += f"Anteil an Wärmeversorgung {tech.name}: {anteil:.2f}\n\n"

        self.resultLabel.setText(resultText)

    def addTech(self):
        current_index = self.techComboBox.currentIndex()
        tech_type = self.techComboBox.itemText(current_index)
        dialog = TechInputDialog(tech_type)
        result = dialog.exec_()  # Öffnet den Dialog und wartet auf den Benutzer

        if result == QDialog.Accepted:
            # Wenn der Dialog mit "Ok" bestätigt wurde
            inputs = dialog.getInputs()
            
            # Erstellen Sie hier das entsprechende Technologieobjekt
            if tech_type == "Solarthermie":
                new_tech = SolarThermal(name=tech_type, bruttofläche_STA=inputs["bruttofläche_STA"], vs=inputs["vs"], Typ=inputs["Typ"])
            elif tech_type == "Biomassekessel":
                new_tech = BiomassBoiler(name=tech_type, P_BMK=inputs["P_BMK"])
            elif tech_type == "Gaskessel":
                new_tech = GasBoiler(name=tech_type)  # Angenommen, GasBoiler benötigt keine zusätzlichen Eingaben
            elif tech_type == "BHKW":
                new_tech = CHP(name=tech_type, th_Leistung_BHKW=inputs["th_Leistung_BHKW"])
            elif tech_type == "Holzgas-BHKW":
                new_tech = CHP(name=tech_type, th_Leistung_BHKW=inputs["th_Leistung_BHKW"])  # Angenommen, Holzgas-BHKW verwendet dieselbe Klasse wie BHKW
            elif tech_type == "Geothermie":
                new_tech = Geothermal(name=tech_type, Fläche=inputs["Fläche"], Bohrtiefe=inputs["Bohrtiefe"], Temperatur_Geothermie=inputs["Temperatur_Geothermie"])
            elif tech_type == "Abwärme":
                new_tech = WasteHeatPump(name=tech_type, Kühlleistung_Abwärme=inputs["Kühlleistung_Abwärme"], Temperatur_Abwärme=inputs["Temperatur_Abwärme"])

            self.techList.addItem(tech_type)
            self.tech_objects.append(new_tech)

    def removeTech(self):
        self.techList.clear()
        self.tech_objects = []

    def getListItems(self):
        items = []
        for index in range(self.techList.count()):
            items.append(self.techList.item(index).text())
        return items