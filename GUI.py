import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QHBoxLayout, QListWidget, QComboBox, QDialog, QTabWidget, QMenuBar, QAction, QInputDialog, QMessageBox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

from simulate_functions import *

from GUI_Dialogfenster import TechInputDialog


from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import os
import folium

import geopandas as gpd

import random

from net_generation_QGIS.import_osm_street_layer_geojson import download_osm_street_data

class HeatSystemDesignGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()
    
    def initFileInputs(self):
        # geojson 1
        self.EAFilenameInput = QLineEdit('net_generation_QGIS/Beispiel Zittau/Erzeugeranlagen.geojson')
        self.selectEAButton = QPushButton('geoJSON Erzeugeranlagen auswählen')
        self.selectEAButton.clicked.connect(lambda: self.selectFilename(self.EAFilenameInput))

        # geojson 2
        self.HASTFilenameInput = QLineEdit('net_generation_QGIS/Beispiel Zittau/HAST.geojson')
        self.selectHASTButton = QPushButton('geoJSON HAST auswählen')
        self.selectHASTButton.clicked.connect(lambda: self.selectFilename(self.HASTFilenameInput))

        # geojson 3
        self.vlFilenameInput = QLineEdit('net_generation_QGIS/Beispiel Zittau/Vorlauf.geojson')
        self.selectvlButton = QPushButton('geoJSON Vorlauf auswählen')
        self.selectvlButton.clicked.connect(lambda: self.selectFilename(self.vlFilenameInput))

        # geojson 4
        self.rlFilenameInput = QLineEdit('net_generation_QGIS/Beispiel Zittau/Rücklauf.geojson')
        self.selectrlButton = QPushButton('geoJSON Rücklauf auswählen')
        self.selectrlButton.clicked.connect(lambda: self.selectFilename(self.rlFilenameInput))
        
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
        self.setWindowTitle("Hier könnte ein cooler Softwarename stehen")
        layout = QVBoxLayout(self)

        # Erstellen des Tab-Widgets
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget)

        # Erstellen der einzelnen Tabs
        tab1 = QWidget()
        tab2 = QWidget()
        tab3 = QWidget()

        # Hinzufügen der Tabs zum Tab-Widget
        tabWidget.addTab(tab1, "Visualisierung GIS-Daten")
        tabWidget.addTab(tab2, "Netzberechnung")
        tabWidget.addTab(tab3, "Auslegung Erzeugermix")

        # Setzen des Layouts für tab1
        tab1Layout = QVBoxLayout()

        # Initialisieren der Karte
        self.m = folium.Map(location=[51.1657, 10.4515], zoom_start=6)
        self.mapView = QWebEngineView()
        # Erstellen der Menüleiste in tab1
        self.menuBar = QMenuBar(tab1)
        self.menuBar.setFixedHeight(30)  # Setzen Sie eine spezifische Höhe
        fileMenu = self.menuBar.addMenu('Datei')

        # Erstellen und Hinzufügen der Aktion "Import Netzdaten"
        importAction = QAction('Import Netzdaten', self)
        importAction.triggered.connect(self.importNetData)
        fileMenu.addAction(importAction)

        # Aktion für Straßendaten-Download hinzufügen
        downloadAction = QAction('Straßendaten herunterladen', self)
        downloadAction.triggered.connect(self.promptDownloadStreetData)
        fileMenu.addAction(downloadAction)

        # Fügen Sie die Menüleiste dem Layout von tab1 hinzu
        tab1Layout.addWidget(self.menuBar)
        
        # Fügen Sie das QWebEngineView-Widget zum Layout von tab1 hinzu
        self.updateMapView()
        tab1Layout.addWidget(self.mapView)
        tab1.setLayout(tab1Layout)

        #############################################################
        tab2Layout = QVBoxLayout()

        # Hinzufügen zum Layout
        geojsonImportLayoutEA = QHBoxLayout()
        geojsonImportLayoutEA.addWidget(self.EAFilenameInput)
        geojsonImportLayoutEA.addWidget(self.selectEAButton)
        tab2Layout.addLayout(geojsonImportLayoutEA)

        # Hinzufügen zum Layout
        geojsonImportLayoutHAST = QHBoxLayout()
        geojsonImportLayoutHAST.addWidget(self.HASTFilenameInput)
        geojsonImportLayoutHAST.addWidget(self.selectHASTButton)
        tab2Layout.addLayout(geojsonImportLayoutHAST)

        # Hinzufügen zum Layout
        geojsonImportLayoutvl = QHBoxLayout()
        geojsonImportLayoutvl.addWidget(self.vlFilenameInput)
        geojsonImportLayoutvl.addWidget(self.selectvlButton)
        tab2Layout.addLayout(geojsonImportLayoutvl)

        geojsonImportLayoutrl = QHBoxLayout()
        geojsonImportLayoutrl.addWidget(self.rlFilenameInput)
        geojsonImportLayoutrl.addWidget(self.selectrlButton)
        tab2Layout.addLayout(geojsonImportLayoutrl)

        ### In Karte importieren - Button einbauen
        # Buttons
        self.LayerImportButton = QPushButton('Layers in Karte importieren')
        self.LayerImportButton.clicked.connect(self.ImportLayers)
        tab2Layout.addWidget(self.LayerImportButton)
        ### Wärmebedarfe aus geojson anzeigen wenn vorhanden

        #Eingaben
        StartTimeLayout = QHBoxLayout()
        self.StartTimeStepLabel = QLabel('Zeitschritt Start (15 min Werte); Minimum: 0 :')
        self.StartTimeStepInput = QLineEdit("0")
        StartTimeLayout.addWidget(self.StartTimeStepLabel)
        StartTimeLayout.addWidget(self.StartTimeStepInput)

        tab2Layout.addLayout(StartTimeLayout)

        EndTimeLayout = QHBoxLayout()
        self.EndTimeStepLabel = QLabel('Zeitschritt Ende (15 min Werte); Maximum: 35040 (1 Jahr) :')
        self.EndTimeStepInput = QLineEdit("96")
        EndTimeLayout.addWidget(self.EndTimeStepLabel)
        EndTimeLayout.addWidget(self.EndTimeStepInput)

        tab2Layout.addLayout(EndTimeLayout)

        # Buttons
        self.calculateNetButton = QPushButton('Berechnen')
        self.calculateNetButton.clicked.connect(self.create_net)
        tab2Layout.addWidget(self.calculateNetButton)

        self.figure3 = plt.figure()
        self.canvas3 = FigureCanvas(self.figure3)
        tab2Layout.addWidget(self.canvas3)

        tab2.setLayout(tab2Layout)
        
        ###############################################################
        tab3Layout = QVBoxLayout()

        self.DatenEingabeLabel = QLabel('Dateneingaben')
        tab3Layout.addWidget(self.DatenEingabeLabel)

        # Hinzufügen zum Layout
        fileLayout1 = QHBoxLayout()
        fileLayout1.addWidget(self.FilenameInput)
        fileLayout1.addWidget(self.selectFileButton)
        tab3Layout.addLayout(fileLayout1)

        # Hinzufügen zum Layout
        fileLayout2 = QHBoxLayout()
        fileLayout2.addWidget(self.tryFilenameInput)
        fileLayout2.addWidget(self.selectTRYFileButton)
        tab3Layout.addLayout(fileLayout2)

        # Hinzufügen zum Layout
        fileLayout3 = QHBoxLayout()
        fileLayout3.addWidget(self.copFilenameInput)
        fileLayout3.addWidget(self.selectCOPFileButton)
        tab3Layout.addLayout(fileLayout3)
        
        self.costEingabeLabel = QLabel('Wirtschaftliche Vorgaben')
        tab3Layout.addWidget(self.costEingabeLabel)

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
        self.figure1 = plt.figure()
        self.canvas1 = FigureCanvas(self.figure1)
        
        # Zweites Diagramm
        self.figure2 = plt.figure()
        self.canvas2 = FigureCanvas(self.figure2)

        # Füge die Canvas-Widgets zum Diagramm-Layout hinzu
        chartLayout.addWidget(self.canvas1)
        chartLayout.addWidget(self.canvas2)


        # Add widgets to layout
        tab3Layout.addLayout(inputLayout)
        tab3Layout.addWidget(self.techEingabeLabel)
        tab3Layout.addWidget(self.techComboBox)
        tab3Layout.addLayout(buttonLayout)
        tab3Layout.addWidget(self.techList)
        tab3Layout.addWidget(self.load_scale_factorLabel)
        tab3Layout.addWidget(self.load_scale_factorInput)
        tab3Layout.addWidget(self.calculateEingabeLabel)
        tab3Layout.addWidget(self.calculateButton)
        tab3Layout.addWidget(self.optimizeEingabeLabel)
        tab3Layout.addWidget(self.optimizeButton)
        tab3Layout.addWidget(self.resultLabel)
        tab3Layout.addLayout(chartLayout)

        tab3.setLayout(tab3Layout)

        # Set the layout
        self.setLayout(layout)

    
    # Methode zum Anzeigen der Karte in PyQt5
    def display_map(self, m):
        # Speichern Sie die Karte als HTML-Datei
        map_file = 'map.html'
        m.save(map_file)

        # Verwenden Sie QWebEngineView, um die Karte anzuzeigen
        webView = QWebEngineView()
        webView.load(QUrl.fromLocalFile(os.path.abspath(map_file)))
        return webView
    
    def ImportLayers(self):
        vl = self.vlFilenameInput.text()
        rl = self.rlFilenameInput.text()
        HAST = self.HASTFilenameInput.text()
        WEA = self.EAFilenameInput.text()
                                
        self.loadNetData(vl)
        self.loadNetData(rl)
        self.loadNetData(HAST)
        self.loadNetData(WEA)
        self.updateMapView()
    
    def importNetData(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, 'Netzdaten importieren', '', 'GeoJSON Files (*.geojson);;All Files (*)')
        if fnames:
            for fname in fnames:
                self.loadNetData(fname)
            self.updateMapView()
    
    def loadNetData(self, filename):
        # Laden der GeoJSON-Datei mit Geopandas
        gdf = gpd.read_file(filename)

        # Generieren einer zufälligen Farbe für das GeoJSON-Feature
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))

        # Hinzufügen der GeoJSON-Daten zur Karte mit der generierten Farbe
        folium.GeoJson(
            gdf,
            name=os.path.basename(filename),
            style_function=lambda feature: {
                'fillColor': color,
                'color': color,
                'weight': 1.5,
                'fillOpacity': 0.5,
            }
        ).add_to(self.m)


    def updateMapView(self):
        # Speichern Sie die aktualisierte Karte als HTML-Datei
        map_file = 'map.html'
        self.m.save(map_file)

        # Aktualisieren Sie das QWebEngineView-Widget, um die neue Karte anzuzeigen
        self.mapView.load(QUrl.fromLocalFile(os.path.abspath(map_file)))

    def promptDownloadStreetData(self):
        area, okPressed = QInputDialog.getText(self, "Straßendaten herunterladen", "Geben Sie den Bereich ein:")
        if okPressed and area != '':
            self.downloadStreetData(area)

    def downloadStreetData(self, area):
        overpass_query = f"""
[out:json][timeout:25];
area[name="{area}"]->.area_0;
(
  node["highway"="primary"](area.area_0);
  node["highway"="secondary"](area.area_0);
  node["highway"="tertiary"](area.area_0);
  node["highway"="residential"](area.area_0);
  node["highway"="road"](area.area_0);
  node["highway"="living_street"](area.area_0);
  way["highway"="primary"](area.area_0);
  way["highway"="secondary"](area.area_0);
  way["highway"="tertiary"](area.area_0);
  way["highway"="residential"](area.area_0);
  way["highway"="road"](area.area_0);
  way["highway"="living_street"](area.area_0);
  relation["highway"="primary"](area.area_0);
  relation["highway"="secondary"](area.area_0);
  relation["highway"="tertiary"](area.area_0);
  relation["highway"="residential"](area.area_0);
  relation["highway"="road"](area.area_0);
  relation["highway"="living_street"](area.area_0);
);
(._;>;);
out body;
"""
        print(overpass_query)
        # Hier rufen Sie Ihr Download-Skript auf
        # Ausgabedateiname für GeoJSON-Datei
        output_geojson_file = "Straßen_TEST.geojson"

        # Download der Daten und Speichern als GeoJSON
        download_osm_street_data(overpass_query, output_geojson_file)
        # Beispiel: download_osm_street_data(overpass_query.format(area), output_geojson_file)
        QMessageBox.information(self, "Download", "Straßendaten für " + area + " heruntergeladen.")

        self.loadNetData(output_geojson_file)
        self.updateMapView()

        QMessageBox.information(self, "Import", "Straßendaten für " + area + " importiert.")


    def selectFilename(self, inputWidget):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'All Files (*);;CSV Files (*.csv);;Data Files (*.dat)')
        if fname:  # Prüfen, ob ein Dateiname ausgewählt wurde
            inputWidget.setText(fname)

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

    def loadFile(self):
        #fname = 'results_time_series_net.csv'
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', 'C:/Users/username/heating_network_generation')
        if fname:
            self.resultLabel.setText(f"Loaded file: {fname}")
            
            return fname
    
    def showResults(self, Jahreswärmebedarf, WGK_Gesamt, techs, Wärmemengen, WGK, Anteile):
        resultText = f"Jahreswärmebedarf: {Jahreswärmebedarf:.2f} MWh\n"
        resultText += f"Wärmegestehungskosten Gesamt: {WGK_Gesamt:.2f} €/MWh\n\n"

        for tech, wärmemenge, anteil, wgk in zip(techs, Wärmemengen, Anteile, WGK):
            resultText += f"Wärmemenge {tech.name}: {wärmemenge:.2f} MWh\n"
            resultText += f"Wärmegestehungskosten {tech.name}: {wgk:.2f} €/MWh\n"
            resultText += f"Anteil an Wärmeversorgung {tech.name}: {anteil:.2f}\n\n"

        self.resultLabel.setText(resultText)

    def optimize(self):
        self.calculate(True)

    def create_net(self, calc1=0, calc2=96):
        #calc1, calc2 = 0, 96 # min: 0; max: 35040
        calc1 = int(self.StartTimeStepInput.text())
        calc2 = int(self.EndTimeStepInput.text())

        output_filename = 'results_time_series_net1.csv'

        gdf_vl = gpd.read_file(self.vlFilenameInput.text())
        gdf_rl = gpd.read_file(self.rlFilenameInput.text())
        gdf_HAST = gpd.read_file(self.HASTFilenameInput.text())
        gdf_WEA = gpd.read_file(self.EAFilenameInput.text())

        time_15min, time_steps, net, net_results = thermohydraulic_time_series_net_calculation(calc1, calc2, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA)

        mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
            return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

        #plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)

        self.plot2(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)

        ###!!!!!this will overwrite the current csv file!!!!!#
        save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, output_filename)

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
        ax1.plot

        ax2.pie(Anteile, labels=data_labels_L, autopct='%1.1f%%', startangle=90)
        ax2.set_title("Anteile Wärmeerzeugung")
        ax2.legend(loc='lower left')
        ax2.axis("equal")
        ax2.plot

    def plot2(self, time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump):
        # Clear previous figure
        self.figure3.clear()
        ax1 = self.figure3.add_subplot(111)

        # Plot für Wärmeleistung auf der ersten Y-Achse
        ax1.plot(time_steps, qext_kW, 'b-', label="Gesamtlast")
        ax1.set_xlabel("Zeit in 15 min Schritten")
        ax1.set_ylabel("Wärmebedarf in kW / 15 min", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc='upper left')
        ax1.plot

        # Zweite Y-Achse für die Temperatur
        ax2 = ax1.twinx()
        ax2.plot(time_steps, return_temp_circ_pump, 'm-o', label="circ pump return temperature")
        ax2.plot(time_steps, flow_temp_circ_pump, 'c-o', label="circ pump flow temperature")
        ax2.set_ylabel("temperature [°C]", color='m')
        ax2.tick_params('y', colors='m')
        ax2.legend(loc='upper right')
        ax2.set_ylim(0,100)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())
