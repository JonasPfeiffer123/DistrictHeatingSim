import itertools
import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QLineEdit, QListWidget, QDialog, QProgressBar, \
    QMessageBox, QFileDialog, QMenuBar, QScrollArea, QAction, QAbstractItemView, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from heat_generators.heat_generator_classes import *
from gui.mix_design_dialogs import TechInputDialog, EconomicParametersDialog, NetInfrastructureDialog, TemperatureDataDialog, HeatPumpDataDialog
from gui.checkable_combobox import CheckableComboBox
from gui.threads import CalculateMixThread
from gui.results_pdf import create_pdf

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.parent().updateTechObjectsOrder()

class MixDesignTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.results = {}
        self.initFileInputs()
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.economicParametersDialog = EconomicParametersDialog(self)
        self.netInfrastructureDialog = NetInfrastructureDialog(self)
        self.temperatureDataDialog = TemperatureDataDialog(self)
        self.heatPumpDataDialog = HeatPumpDataDialog(self)
        self.updateDefaultPath(self.data_manager.project_folder)
        self.setupParameters()
        self.tech_objects = []
        self.initUI()

    def initFileInputs(self):
        self.FilenameInput = QLineEdit('')
        self.selectFileButton = QPushButton('Ergebnis-CSV auswählen')
        self.selectFileButton.clicked.connect(lambda: self.selectFilename(self.FilenameInput))

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

        # Pfad für Ausgabe aktualisieren
        new_output_path = f"{self.base_path}\Lastgang\Lastgang.csv"
        # Dies setzt voraus, dass Ihre Eingabefelder oder deren Layouts entsprechend benannt sind
        self.FilenameInput.setText(new_output_path)

        self.netInfrastructureDialog.base_path = self.base_path

    def initUI(self):
        mainScrollArea = QScrollArea(self)
        mainScrollArea.setWidgetResizable(True)

        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)

        self.mainLayout = mainLayout
        self.setupMenu()
        self.setupFileInputs()
        self.setupScaleFactor(mainLayout)
        self.setupTechnologySelection(mainLayout)
        self.setupInfrastructureCostsTable(mainLayout)
        self.setupCalculationOptimization()
        self.setupDiagrams(mainLayout)

        self.progressBar = QProgressBar(self)
        mainLayout.addWidget(self.progressBar)

        mainScrollArea.setWidget(mainWidget)
        
        tabLayout = QVBoxLayout(self)
        tabLayout.addWidget(mainScrollArea)
        self.setLayout(tabLayout)
    
    def setupMenu(self):
        # Erstellen der Menüleiste
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)

        # Erstellen des 'Datei'-Menüs
        fileMenu = self.menuBar.addMenu('Datei')
        pdfAction = QAction('Ergebnisse als PDF speichern', self)
        pdfAction.triggered.connect(self.on_export_pdf_clicked)
        fileMenu.addAction(pdfAction)

        # Neues Menü für Einstellungen
        settingsMenu = self.menuBar.addMenu('Einstellungen')
        # Aktion für wirtschaftliche Parameter
        economicParametersAction = QAction('Wirtschaftliche Parameter...', self)
        economicParametersAction.triggered.connect(self.openEconomicParametersDialog)
        settingsMenu.addAction(economicParametersAction)
        # Aktion für Infrastrukturkosten
        infrastructureCostsAction = QAction('Infrastrukturkosten...', self)
        infrastructureCostsAction.triggered.connect(self.openInfrastructureCostsDialog)
        settingsMenu.addAction(infrastructureCostsAction)
        # Aktion für Temperaturdaten
        temperatureDataAction = QAction('Temperaturdaten...', self)
        temperatureDataAction.triggered.connect(self.opentemperatureDataDialog)
        settingsMenu.addAction(temperatureDataAction)
        # Aktion für Temperaturdaten
        heatPumpDataAction = QAction('COP-Kennfeld Wärmepumpe...', self)
        heatPumpDataAction.triggered.connect(self.openheatPumpDataDialog)
        settingsMenu.addAction(heatPumpDataAction)

        # Menü für das Hinzufügen von Wärmeerzeugern
        addHeatGeneratorMenu = self.menuBar.addMenu('Wärmeerzeuger hinzufügen')

        # Liste der verfügbaren Wärmeerzeuger
        heatGenerators = ["Solarthermie", "BHKW", "Holzgas-BHKW", "Geothermie", "Abwärme", \
                          "Flusswasser", "Biomassekessel", "Gaskessel"]
        # Aktionen für jeden Wärmeerzeuger erstellen
        for generator in heatGenerators:
            action = QAction(generator, self)
            # Wichtig: Der `lambda` Ausdruck sollte keine Referenz auf das `self` Objekt (MixDesignTab) enthalten
            # stattdessen übergeben wir `None` als `tech_data`, wenn das Dialogfenster geöffnet wird.
            action.triggered.connect(lambda checked, gen=generator: self.addTech(gen, None))
            addHeatGeneratorMenu.addAction(action)

        calculationsMenu = self.menuBar.addMenu('Berechnungen')
        # Aktion für die Berechnung starten
        calculateAction = QAction('Berechnen', self)
        calculateAction.triggered.connect(self.start_calculation)
        calculationsMenu.addAction(calculateAction)
        # Aktion für die Optimierung starten
        optimizeAction = QAction('Optimieren', self)
        optimizeAction.triggered.connect(self.optimize)
        calculationsMenu.addAction(optimizeAction)

        showAdditionalResultsMenu = self.menuBar.addMenu('weitere Ergebnisse Anzeigen')
        # Aktion für die Berechnung starten
        showAdditionalResultsAction = QAction('Kostenzusammensetzung über Betrachtungszeitraum', self)
        showAdditionalResultsAction.triggered.connect(self.show_additional_results)
        showAdditionalResultsMenu.addAction(showAdditionalResultsAction)

        self.mainLayout.addWidget(self.menuBar)

    ### Eingabe wirtschaftliche Randbedingungen ###
    def setupParameters(self):
        values = self.economicParametersDialog.getValues()
        self.gaspreis = values['Gaspreis in €/MWh']
        self.strompreis = values['Strompreis in €/MWh']
        self.holzpreis = values['Holzpreis in €/MWh']
        self.BEW = values['BEW-Förderung']
        self.kapitalzins = values['Kapitalzins in %']
        self.preissteigerungsrate = values['Preissteigerungsrate in %']
        self.betrachtungszeitraum = values['Betrachtungszeitraum in a']

        TRY = self.temperatureDataDialog.getValues()
        self.try_filename = TRY['TRY-filename']

        COP = self.heatPumpDataDialog.getValues()
        self.cop_filename = COP['COP-filename']

    ### Dialoge ###
    def openEconomicParametersDialog(self):
        if self.economicParametersDialog.exec_():
            values = self.economicParametersDialog.getValues()
            self.gaspreis = values['Gaspreis in €/MWh']
            self.strompreis = values['Strompreis in €/MWh']
            self.holzpreis = values['Holzpreis in €/MWh']
            self.BEW = values['BEW-Förderung']
            self.kapitalzins = values['Kapitalzins in %']
            self.preissteigerungsrate = values['Preissteigerungsrate in %']
            self.betrachtungszeitraum = values['Betrachtungszeitraum in a']

    def openInfrastructureCostsDialog(self):
        dialog = self.netInfrastructureDialog
        if dialog.exec_():
            updated_values = dialog.getValues()
            self.updateInfrastructureTable(updated_values)

    def opentemperatureDataDialog(self):
        if self.temperatureDataDialog.exec_():
            TRY = self.temperatureDataDialog.getValues()
            self.try_filename = TRY['TRY-filename']

    def openheatPumpDataDialog(self):
        if self.heatPumpDataDialog.exec_():
            COP = self.heatPumpDataDialog.getValues()
            self.cop_filename = COP['COP-filename']

    ### Eingabe Dateien ###
    def setupFileInputs(self):
        self.addLabel(self.mainLayout, 'Eingabe csv-Datei berechneter Lastgang Wärmenetz')
        self.addFileInputLayout(self.mainLayout, self.FilenameInput, self.selectFileButton)

    def addLabel(self, layout, text):
        label = QLabel(text)
        layout.addWidget(label)

    def addFileInputLayout(self, mainLayout, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        mainLayout.addLayout(layout)

    def selectFilename(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    ### Eingabe Skalierungsfaktor Last ###
    def setupScaleFactor(self, mainLayout):
        # Hinzufügen der Eingabe für den Lastgang-Skalierungsfaktor
        self.load_scale_factorLabel = QLabel('Lastgang skalieren?:')
        self.load_scale_factorInput = QLineEdit("1")  # Standardwert ist "1"

        # Hinzufügen zum Layout
        loadScaleFactorLayout = QHBoxLayout()
        loadScaleFactorLayout.addWidget(self.load_scale_factorLabel)
        loadScaleFactorLayout.addWidget(self.load_scale_factorInput)
        mainLayout.addLayout(loadScaleFactorLayout)

    ### Setup und Funktionen Wärmeerzeugertechnologien-Verwaltung ###
    def setupTechnologySelection(self, mainLayout):
        self.addLabel(mainLayout, 'Definierte Wärmeerzeuger')
        
        self.techList = QListWidget()
        self.techList.setDragDropMode(QAbstractItemView.InternalMove)
        self.techList.itemDoubleClicked.connect(self.editTech)
        mainLayout.addWidget(self.techList)

        buttonLayout = QHBoxLayout()

        self.btnDeleteSelectedTech = QPushButton("Ausgewählte Technologie entfernen")
        buttonLayout.addWidget(self.btnDeleteSelectedTech)

        self.btnRemoveTech = QPushButton("Alle Technologien entfernen")
        buttonLayout.addWidget(self.btnRemoveTech)

        mainLayout.addLayout(buttonLayout)

        self.btnDeleteSelectedTech.clicked.connect(self.removeSelectedTech)
        self.btnRemoveTech.clicked.connect(self.removeTech)

    ### Technologie erstellen ###
    def createTechnology(self, tech_type, inputs):
        if tech_type == "Solarthermie":
            return SolarThermal(name=tech_type, bruttofläche_STA=inputs["bruttofläche_STA"], vs=inputs["vs"], Typ=inputs["Typ"], kosten_speicher_spez=inputs["kosten_speicher_spez"], 
                                kosten_fk_spez=inputs["kosten_fk_spez"], kosten_vrk_spez=inputs["kosten_vrk_spez"], Tsmax=inputs["Tsmax"], Longitude=inputs["Longitude"], 
                                STD_Longitude=inputs["STD_Longitude"], Latitude=inputs["Latitude"], East_West_collector_azimuth_angle=inputs["East_West_collector_azimuth_angle"], 
                                Collector_tilt_angle=inputs["Collector_tilt_angle"], Tm_rl=inputs["Tm_rl"], Qsa=inputs["Qsa"], Vorwärmung_K=inputs["Vorwärmung_K"], 
                                DT_WT_Solar_K=inputs["DT_WT_Solar_K"], DT_WT_Netz_K=inputs["DT_WT_Netz_K"])
        elif tech_type == "Biomassekessel":
            return BiomassBoiler(name=tech_type, P_BMK=inputs["P_BMK"], Größe_Holzlager=inputs["Größe_Holzlager"], spez_Investitionskosten=inputs["spez_Investitionskosten"], spez_Investitionskosten_Holzlager=inputs["spez_Investitionskosten_Holzlager"])
        elif tech_type == "Gaskessel":
            return GasBoiler(name=tech_type, spez_Investitionskosten=inputs["spez_Investitionskosten"])  # Angenommen, GasBoiler benötigt keine zusätzlichen Eingaben
        elif tech_type == "BHKW":
            return CHP(name=tech_type, th_Leistung_BHKW=inputs["th_Leistung_BHKW"], spez_Investitionskosten_GBHKW=inputs["spez_Investitionskosten_GBHKW"])
        elif tech_type == "Holzgas-BHKW":
            return CHP(name=tech_type, th_Leistung_BHKW=inputs["th_Leistung_BHKW"], spez_Investitionskosten_HBHKW=inputs["spez_Investitionskosten_HBHKW"])  # Angenommen, Holzgas-BHKW verwendet dieselbe Klasse wie BHKW
        elif tech_type == "Geothermie":
            return Geothermal(name=tech_type, Fläche=inputs["Fläche"], Bohrtiefe=inputs["Bohrtiefe"], Temperatur_Geothermie=inputs["Temperatur_Geothermie"], Abstand_Sonden=inputs["Abstand_Sonden"], spez_Bohrkosten=inputs["spez_Bohrkosten"], spez_Entzugsleistung=inputs["spez_Entzugsleistung"], Vollbenutzungsstunden=inputs["Vollbenutzungsstunden"], spezifische_Investitionskosten_WP=inputs["spezifische_Investitionskosten_WP"])
        elif tech_type == "Abwärme":
            return WasteHeatPump(name=tech_type, Kühlleistung_Abwärme=inputs["Kühlleistung_Abwärme"], Temperatur_Abwärme=inputs["Temperatur_Abwärme"], spez_Investitionskosten_Abwärme=inputs["spez_Investitionskosten_Abwärme"], spezifische_Investitionskosten_WP=inputs["spezifische_Investitionskosten_WP"])
        elif tech_type == "Flusswasser":
            return RiverHeatPump(name=tech_type, Wärmeleistung_FW_WP=inputs["Wärmeleistung_FW_WP"], Temperatur_FW_WP=inputs["Temperatur_FW_WP"], dT=inputs["dT"], spez_Investitionskosten_Flusswasser=inputs["spez_Investitionskosten_Flusswasser"], spezifische_Investitionskosten_WP=inputs["spezifische_Investitionskosten_WP"])
        else:
            raise ValueError(f"Unbekannter Technologietyp: {tech_type}")
        
    def addTech(self, tech_type, tech_data):
        # Öffnet das Dialogfenster für den gegebenen Technologietyp
        # Hier übergeben wir `tech_data`, welches standardmäßig auf `None` gesetzt ist, falls es nicht spezifiziert wurde.
        dialog = TechInputDialog(tech_type, tech_data)
        if dialog.exec_() == QDialog.Accepted:
            new_tech = self.createTechnology(tech_type, dialog.getInputs())
            self.tech_objects.append(new_tech)
            self.updateTechList()
            #self.updateTechDataTable(self.tech_objects)

    def editTech(self, item):
        selected_tech_index = self.techList.row(item)
        selected_tech = self.tech_objects[selected_tech_index]
        tech_data = {k: v for k, v in selected_tech.__dict__.items() if not k.startswith('_')}
        
        dialog = TechInputDialog(selected_tech.name, tech_data)

        if dialog.exec_() == QDialog.Accepted:
            updated_inputs = dialog.getInputs()
            self.tech_objects[selected_tech_index] = self.createTechnology(selected_tech.name, updated_inputs)
            self.updateTechList()
            #self.updateTechDataTable(self.tech_objects)

    def removeSelectedTech(self):
        # Holt den Index des aktuell ausgewählten Items
        selected_row = self.techList.currentRow()
        if selected_row != -1:
            # Entfernt das Element aus der Liste
            self.techList.takeItem(selected_row)
            # Entfernt das Objekt aus der tech_objects Liste
            del self.tech_objects[selected_row]
            # Aktualisiert die Datenansichten, falls nötig
            self.updateTechList()
            #self.updateTechDataTable(self.tech_objects)

    def removeTech(self):
        self.techList.clear()
        self.tech_objects = []

    def updateTechList(self):
        self.techList.clear()
        for tech in self.tech_objects:
            self.techList.addItem(self.formatTechForDisplay(tech))

    def updateTechObjectsOrder(self):
        new_order = []
        for index in range(self.techList.count()):
            item_text = self.techList.item(index).text()
            # Finden Sie das entsprechende Tech-Objekt basierend auf dem Text
            for tech in self.tech_objects:
                if self.formatTechForDisplay(tech) == item_text:
                    new_order.append(tech)
                    break
        self.tech_objects = new_order

    def formatTechForDisplay(self, tech):
        # Formatieren Sie die Ausgabe basierend auf den Eigenschaften der Technologie
        display_text = f"{tech.name}: "
    
        if isinstance(tech, RiverHeatPump):
            display_text += f"Wärmeleistung FW WP: {tech.Wärmeleistung_FW_WP} kW, Temperatur FW WP: {tech.Temperatur_FW_WP} °C, dT: {tech.dT} K, spez. Investitionskosten Flusswärme: {tech.spez_Investitionskosten_Flusswasser} €/kW, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, WasteHeatPump):
            display_text += f"Kühlleistung Abwärme: {tech.Kühlleistung_Abwärme} kW, Temperatur Abwärme: {tech.Temperatur_Abwärme} °C, spez. Investitionskosten Abwärme: {tech.spez_Investitionskosten_Abwärme} €/kW, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, Geothermal):
            display_text += f"Fläche Sondenfeld: {tech.Fläche} m², Bohrtiefe: {tech.Bohrtiefe} m, Quelltemperatur Erdreich: {tech.Temperatur_Geothermie} °C, spez. Bohrkosten: {tech.spez_Bohrkosten} €/m, spez. Entzugsleistung: {tech.spez_Entzugsleistung} W/m, Vollbenutzungsstunden: {tech.Vollbenutzungsstunden} h, Abstand Sonden: {tech.Abstand_Sonden} m, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, CHP):
            display_text += f"th. Leistung: {tech.th_Leistung_BHKW} kW, spez. Investitionskosten Erdgas-BHKW: {tech.spez_Investitionskosten_GBHKW} €/BHKW, spez. Investitionskosten Holzgas-BHKW: {tech.spez_Investitionskosten_HBHKW} €/kW"
        elif isinstance(tech, BiomassBoiler):
            display_text += f"th. Leistung: {tech.P_BMK}, Größe Holzlager: {tech.Größe_Holzlager} t, spez. Investitionskosten Kessel: {tech.spez_Investitionskosten} €/kW, spez. Investitionskosten Holzlager: {tech.spez_Investitionskosten_Holzlager} €/t"
        elif isinstance(tech, GasBoiler):
            display_text += f"spez. Investitionskosten: {tech.spez_Investitionskosten} €/kW"
        elif isinstance(tech, SolarThermal):
            display_text += f"Bruttokollektorfläche: {tech.bruttofläche_STA} m², Volumen Solarspeicher: {tech.vs} m³, Kollektortyp: {tech.Typ}, spez. Kosten Speicher: {tech.kosten_speicher_spez} €/m³, spez. Kosten Flachkollektor: {tech.kosten_fk_spez} €/m², spez. Kosten Röhrenkollektor: {tech.kosten_vrk_spez} €/m²"
        else:
            return f"Unbekannte Technologieklasse: {type(tech).__name__}"
        
        return display_text
    
    ### Infrastrukturtabellen ###
    def setupInfrastructureCostsTable(self, mainLayout):
        self.addLabel(mainLayout, 'Wärmenetzinfrastruktur')
        self.infrastructure_costs = self.netInfrastructureDialog.getValues()
        self.infrastructureCostsTable = QTableWidget()
        self.infrastructureCostsTable.setColumnCount(7)  # Eine zusätzliche Spalte für Annuität
        self.infrastructureCostsTable.setHorizontalHeaderLabels(['Beschreibung', 'Kosten', 'Technische Nutzungsdauer', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Annuität'])
        mainLayout.addWidget(self.infrastructureCostsTable)
        self.updateInfrastructureTable(self.infrastructure_costs)  # Tabelle mit Standardwerten füllen

    def updateInfrastructureTable(self, values):
        # Hole die aktuellen Infrastruktur-Objekte aus dem Dialog
        infraObjects = self.netInfrastructureDialog.getCurrentInfraObjects()
        columns = ['Beschreibung', 'Kosten', 'Technische Nutzungsdauer', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Gesamtannuität']

        self.infrastructureCostsTable.setRowCount(len(infraObjects))
        self.infrastructureCostsTable.setColumnCount(len(columns))  # Hier 7 Spalten setzen
        self.infrastructureCostsTable.setHorizontalHeaderLabels(columns)

        # Summen initialisieren
        self.summe_investitionskosten = 0
        self.summe_annuität = 0

        for i, obj in enumerate(infraObjects):
            self.infrastructureCostsTable.setItem(i, 0, QTableWidgetItem(obj.capitalize()))
            for j, col in enumerate(columns[1:], 1):
                key = f"{obj}_{col.lower()}"
                value = values.get(key, "")
                self.infrastructureCostsTable.setItem(i, j, QTableWidgetItem(str(value)))

            # Annuität berechnen und hinzufügen
            A0 = float(values.get(f"{obj}_kosten", 0))
            TN = int(values.get(f"{obj}_technische nutzungsdauer", 0))
            f_Inst = float(values.get(f"{obj}_f_inst", 0))
            f_W_Insp = float(values.get(f"{obj}_f_w_insp", 0))
            Bedienaufwand = float(values.get(f"{obj}_bedienaufwand", 0))
            annuität = self.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)
            self.infrastructureCostsTable.setItem(i, 6, QTableWidgetItem("{:.1f}".format(annuität)))
            # Summen berechnen
            self.summe_investitionskosten += float(values.get(f"{obj}_kosten", 0))
            self.summe_annuität += annuität

        # Neue Zeile für Summen hinzufügen
        summen_row_index = self.infrastructureCostsTable.rowCount()
        self.infrastructureCostsTable.insertRow(summen_row_index)

        # Fettgedruckten Font erstellen
        boldFont = QFont()
        boldFont.setBold(True)

        # Summenzellen hinzufügen und formatieren
        summen_beschreibung_item = QTableWidgetItem("Summe Infrastruktur")
        summen_beschreibung_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 0, summen_beschreibung_item)

        # Formatieren der Zahlen auf eine Dezimalstelle
        summen_kosten_item = QTableWidgetItem("{:.0f}".format(self.summe_investitionskosten))
        summen_kosten_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 1, summen_kosten_item)

        summen_annuität_item = QTableWidgetItem("{:.0f}".format(self.summe_annuität))
        summen_annuität_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 6, summen_annuität_item)

        self.infrastructureCostsTable.resizeColumnsToContents()
        self.adjustTableSize(self.infrastructureCostsTable)

    def calc_annuität(self, A0, TN, f_Inst, f_W_Insp, Bedienaufwand):
        q = 1 + (self.kapitalzins / 100)
        r = 1 + (self.preissteigerungsrate / 100)
        t = int(self.betrachtungszeitraum)

        a = annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand, q=q, r=r, T=t)
        return a
    
    ### Setup der Berechnungsergebnistabellen ###
    def setupCalculationOptimization(self):
        self.resultLabel = QLabel('Kosten Erzeuger')
        self.mainLayout.addWidget(self.resultLabel)
        self.setupTechDataTable()

        self.resultLabel = QLabel('Übersicht Erzeugung')
        self.mainLayout.addWidget(self.resultLabel)
        self.setupResultsTable()

        self.resultLabel = QLabel('Ergebnisse Wirtschaftlichkeit')
        self.mainLayout.addWidget(self.resultLabel)
        self.setupAdditionalResultsTable()

    ### Tech Data Table ###
    def setupTechDataTable(self):
        self.techDataTable = QTableWidget()
        self.techDataTable.setColumnCount(4)  # Anpassen an die Anzahl der benötigten Spalten
        self.techDataTable.setHorizontalHeaderLabels(['Name', 'Dimensionen', 'Kosten', 'Gesamtkosten'])
        self.mainLayout.addWidget(self.techDataTable)
    
    def updateTechDataTable(self, tech_objects):
        self.techDataTable.setRowCount(len(tech_objects))

        for i, tech in enumerate(tech_objects):
            name, dimensions, costs, full_costs = self.extractTechData(tech)
            self.techDataTable.setItem(i, 0, QTableWidgetItem(name))
            self.techDataTable.setItem(i, 1, QTableWidgetItem(dimensions))
            self.techDataTable.setItem(i, 2, QTableWidgetItem(costs))
            self.techDataTable.setItem(i, 3, QTableWidgetItem(full_costs))

        self.techDataTable.resizeColumnsToContents()
        self.adjustTableSize(self.techDataTable)

    ### Extraktion Ergebnisse Berechnung ###
    def extractTechData(self, tech):
        if isinstance(tech, RiverHeatPump):
            dimensions = f"th. Leistung: {tech.Wärmeleistung_FW_WP} kW"
            costs = f"Investitionskosten Flusswärmenutzung: {tech.spez_Investitionskosten_Flusswasser*tech.Wärmeleistung_FW_WP:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP*tech.Wärmeleistung_FW_WP:.1f}"
            full_costs = f"{tech.spez_Investitionskosten_Flusswasser*tech.Wärmeleistung_FW_WP + tech.spezifische_Investitionskosten_WP*tech.Wärmeleistung_FW_WP:.1f}"

        elif isinstance(tech, WasteHeatPump):
            dimensions = f"Kühlleistung Abwärme: {tech.Kühlleistung_Abwärme} kW, Temperatur Abwärme: {tech.Temperatur_Abwärme} °C, th. Leistung: {tech.max_Wärmeleistung} kW"
            costs = f"Investitionskosten Abwärmenutzung: {tech.spez_Investitionskosten_Abwärme*tech.max_Wärmeleistung:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"
            full_costs = f"{tech.spez_Investitionskosten_Abwärme*tech.max_Wärmeleistung + tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"

        elif isinstance(tech, Geothermal):
            dimensions = f"Fläche: {tech.Fläche} m², Bohrtiefe: {tech.Bohrtiefe} m, Temperatur Geothermie: {tech.Temperatur_Geothermie} °C, Entzugsleistung: {tech.spez_Entzugsleistung} W/m, th. Leistung: {tech.max_Wärmeleistung} kW"
            costs = f"Investitionskosten Sondenfeld: {tech.Investitionskosten_Sonden:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"
            full_costs = f"{tech.Investitionskosten_Sonden + tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"

        elif isinstance(tech, CHP):
            dimensions = f"th. Leistung: {tech.th_Leistung_BHKW} kW, el. Leistung: {tech.el_Leistung_Soll} kW"
            costs = f"Investitionskosten: {tech.Investitionskosten:.1f}"
            full_costs = f"{tech.Investitionskosten:.1f}"

        elif isinstance(tech, BiomassBoiler):
            dimensions = f"th. Leistung: {tech.P_BMK} kW, Größe Holzlager: {tech.Größe_Holzlager} t"
            costs = f"Investitionskosten Kessel: {tech.Investitionskosten_Kessel:.1f} €, Investitionskosten Holzlager: {tech.Investitionskosten_Holzlager:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"

        elif isinstance(tech, GasBoiler):
            dimensions = f"th. Leistung: {tech.P_max:.1f} kW"
            costs = f"Investitionskosten: {tech.Investitionskosten:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"
            
        elif isinstance(tech, SolarThermal):
            dimensions = f"Bruttokollekttorfläche: {tech.bruttofläche_STA} m², Speichervolumen: {tech.vs} m³; Kollektortyp: {tech.Typ}"
            costs = f"Investitionskosten Speicher: {tech.Investitionskosten_Speicher:.1f} €, Investitionskosten STA: {tech.Investitionskosten_STA:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"

        else:
            dimensions = "N/A"
            costs = "N/A"
            full_costs = "N/A"

        return tech.name, dimensions, costs, full_costs

    ### Results Table ###
    def setupResultsTable(self):
        # Tabelle initialisieren
        self.resultsTable = QTableWidget()
        self.resultsTable.setColumnCount(4)  # Anzahl der Spalten
        self.resultsTable.setHorizontalHeaderLabels(['Technologie', 'Wärmemenge (MWh)', 'Kosten (€/MWh)', 'Anteil (%)'])
        self.resultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Spaltenbreite anpassen
        self.mainLayout.addWidget(self.resultsTable)

    def showResultsInTable(self, results):
        self.resultsTable.setRowCount(len(results['techs']))  # Zeilenanzahl basierend auf der Anzahl der Technologien

        for i, (tech, wärmemenge, wgk, anteil) in enumerate(zip(results['techs'], results['Wärmemengen'], results['WGK'], results['Anteile'])):
            # Setzen der Zellenwerte für jede Zeile
            self.resultsTable.setItem(i, 0, QTableWidgetItem(tech))
            self.resultsTable.setItem(i, 1, QTableWidgetItem(f"{wärmemenge:.2f}"))
            self.resultsTable.setItem(i, 2, QTableWidgetItem(f"{wgk:.2f}"))
            self.resultsTable.setItem(i, 3, QTableWidgetItem(f"{anteil*100:.2f}%"))

        self.resultsTable.resizeColumnsToContents()  # Passt die Spaltenbreite an den Inhalt an
        self.adjustTableSize(self.resultsTable)  # Anpassen der Größe der Tabelle
    
    ### Additional Results Table ###
    def setupAdditionalResultsTable(self):
        # Tabelle initialisieren
        self.additionalResultsTable = QTableWidget()
        self.additionalResultsTable.setColumnCount(3)  # Anzahl der Spalten
        self.additionalResultsTable.setHorizontalHeaderLabels(['Ergebnis', 'Wert', 'Einheit'])
        self.additionalResultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Spaltenbreite anpassen
        self.mainLayout.addWidget(self.additionalResultsTable)

    def showAdditionalResultsTable(self):
        self.WGK_Infra = self.summe_annuität/self.results['Jahreswärmebedarf']
        self.WGK_Gesamt = self.results['WGK_Gesamt'] + self.WGK_Infra

        # Daten für die Tabelle
        data = [
            ("Jahreswärmebedarf", round(self.results['Jahreswärmebedarf'],1), "MWh"),
            ("Stromerzeugung", round(self.results['Strommenge'], 2), "MWh"),
            ("Strombedarf", round(self.results['Strombedarf'], 2), "MWh"),
            ("Wärmegestehungskosten Erzeugeranlagen", round(self.results['WGK_Gesamt'], 2), "€/MWh"),
            ("Wärmegestehungskosten Netzinfrastruktur", round(self.WGK_Infra, 2), "€/MWh"),
            ("Wärmegestehungskosten Gesamt", round(self.WGK_Gesamt, 2), "€/MWh")
        ]

        self.additionalResultsTable.setRowCount(len(data))

        # Daten in die Tabelle einfügen
        for i, (description, value, unit) in enumerate(data):
            self.additionalResultsTable.setItem(i, 0, QTableWidgetItem(description))
            self.additionalResultsTable.setItem(i, 1, QTableWidgetItem(str(value)))
            self.additionalResultsTable.setItem(i, 2, QTableWidgetItem(unit))

        self.additionalResultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.additionalResultsTable)

    ### Table size adjustment function ###
    def adjustTableSize(self, table):
        # header row height
        header_height = table.horizontalHeader().height()
        # hight of all rows
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        # configuring table height
        table.setFixedHeight(header_height + rows_height)
                
    ### Setup Diagramm-Plots ###
    def setupDiagrams(self, mainLayout):
        diagramScrollArea, diagramWidget, diagramLayout = self.setupDiagramScrollArea()
        self.setupFigures(diagramLayout)
        diagramScrollArea.setWidget(diagramWidget)
        mainLayout.addWidget(diagramScrollArea)

    def setupDiagramScrollArea(self):
        diagramScrollArea = QScrollArea()
        diagramScrollArea.setWidgetResizable(True)
        diagramScrollArea.setMinimumSize(800, 1200)

        diagramWidget = QWidget()
        diagramLayout = QVBoxLayout(diagramWidget)

        return diagramScrollArea, diagramWidget, diagramLayout
    
    def setupFigures(self, diagramLayout):
        self.figure1, self.canvas1 = self.addFigure(diagramLayout)
        self.figure2, self.canvas2 = self.addFigure(diagramLayout)

    def addFigure(self, layout):
        figure = Figure(figsize=(8, 6))  # Breite und Höhe in Zoll einstellen
        canvas = FigureCanvas(figure)
        canvas.setMinimumSize(800, 600)  # Größe in Pixel
        layout.addWidget(canvas)
        return figure, canvas
        
    ### Berechnungsfunktionen ###
    def optimize(self):
        self.start_calculation(True)

    def start_calculation(self, optimize=False):
        if self.tech_objects != []:
            #self.updateTechObjectsOrder()

            filename = self.FilenameInput.text()
            load_scale_factor = float(self.load_scale_factorInput.text())

            self.calculationThread = CalculateMixThread(filename, load_scale_factor, self.try_filename, self.cop_filename, self.gaspreis, 
                                                        self.strompreis, self.holzpreis, self.BEW, self.tech_objects, optimize, self.kapitalzins, 
                                                        self.preissteigerungsrate, self.betrachtungszeitraum)
            self.calculationThread.calculation_done.connect(self.on_calculation_done)
            self.calculationThread.calculation_error.connect(self.on_calculation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)

        else:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(f"Es wurden keine Erzeugeranlagen definiert. Keine Berechnung möglich.")
            msgBox.setWindowTitle("Keine Erzeugeranlagen für die Berechnung vorhanden.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

    def on_calculation_done(self, result):
        self.progressBar.setRange(0, 1)
        self.results = result
        self.updateTechList()
        self.updateTechDataTable(self.tech_objects)
        self.showResultsInTable(result)
        self.showAdditionalResultsTable()
        self.save_results_to_csv(result)
        self.showConfirmationDialog()
        self.plotResults(result)

    def on_calculation_error(self, error_message):
        self.progressBar.setRange(0, 1)
        QMessageBox.critical(self, "Berechnungsfehler", str(error_message))

    def showConfirmationDialog(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(f"Die Berechnung des Erzeugermixes war erfolgreich. Die Ergebnisse wurden unter {self.base_path}\Lastgang\\results.csv gespeichert.")
        msgBox.setWindowTitle("Berechnung Erfolgreich")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()
    
    ### Speicherung der Berechnungsergebnisse der Erzeugerauslegung als csv ###
    def save_results_to_csv(self, results):
        # Initialisiere den DataFrame mit den Zeitstempeln
        df = pd.DataFrame({'time_steps': results['time_steps']})
        
        # Füge die Last hinzu
        df['Last_L'] = results['Last_L']
        
        # Hier müssen eindeutige Namen noch eingeführt werden
        # Füge die Daten für Wärmeleistung hinzu. Jede Technologie wird eine Spalte haben.
        #for i, tech in enumerate(results['techs']):
        #    df[tech] = results['Wärmeleistung_L'][i]

        for i, (tech_results, techs) in enumerate(zip(results['Wärmeleistung_L'], results['techs'])):
            df[techs] = tech_results
        
        # Füge die elektrischen Leistungsdaten hinzu
        df['el_Leistungsbedarf_L'] = results['el_Leistungsbedarf_L']
        df['el_Leistung_L'] = results['el_Leistung_L']
        df['el_Leistung_ges_L'] = results['el_Leistung_ges_L']
        
        # Speichere den DataFrame als CSV-Datei
        csv_filename = f"{self.base_path}\Lastgang\\results.csv"
        df.to_csv(csv_filename, index=False, sep=";")
        print(f"Ergebnisse wurden in '{csv_filename}' gespeichert.")

    ### Plotten der Ergebnisse ###
    def plotResults(self, results):
        self.results = results
        if not hasattr(self, 'dataSelectionDropdown'):
            self.createPlotControlDropdown()

        self.figure1.clear()
        self.figure2.clear()

        self.plotStackPlot(self.figure1, results['time_steps'], results['Wärmeleistung_L'], results['techs'], results['colors'], results['Last_L'])
        self.plotPieChart(self.figure2, results['Anteile'], results['techs'], results['colors'])
        self.canvas1.draw()
        self.canvas2.draw()

    def plotStackPlot(self, figure, t, data, labels, colors, Last):
        ax = figure.add_subplot(111)
        ax.stackplot(t, data, labels=labels, colors=colors)
        ax.set_title("Jahresdauerlinie")
        ax.set_xlabel("Jahresstunden")
        ax.set_ylabel("thermische Leistung in kW")
        ax.legend(loc='upper center')
        ax.grid()

        # Hinzufügen von Last_L als Linienplot
        ax1 = self.figure1.gca()  # Get current axis
        print(Last)
        ax1.plot(t, Last, color='blue')  # Zeichnen der Last_L Linie

    def plotPieChart(self, figure, Anteile, labels, colors):
        ax = figure.add_subplot(111)

        # Überprüfen, ob die Summe der Anteile weniger als 1 (100 %) beträgt
        summe = sum(Anteile)
        if summe < 1:
            # Fügen Sie den fehlenden Anteil hinzu, um die Lücke darzustellen
            Anteile.append(1 - summe)
            labels.append("ungedeckter Bedarf")  # Oder einen anderen passenden Text für den leeren Bereich

        ax.pie(Anteile, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.set_title("Anteile Wärmeerzeugung")
        ax.legend(loc='lower left')
        ax.axis("equal")  # Stellt sicher, dass der Pie-Chart kreisförmig bleibt

    def updatePlot(self):
        self.figure1.clear()
        ax = self.figure1.add_subplot(111)
        color_cycle = itertools.cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])

        # Gehen Sie alle Optionen im Dropdown-Menü durch und zeichnen Sie nur die ausgewählten
        for i in range(self.dataSelectionDropdown.count()):
            if self.dataSelectionDropdown.itemChecked(i):
                key = self.dataSelectionDropdown.itemText(i)
                data = self.results[key]
                color = next(color_cycle)
                if key == 'Wärmeleistung_L':
                    # Stackplot für Wärmeleistung_L
                    ax.stackplot(self.results['time_steps'], data, labels=self.results['techs'], colors=self.results['colors'])
                else:
                    # Plotten der anderen Daten als Linienplot
                    ax.plot(self.results['time_steps'], data, label=key, color=color)

        ax.set_xlabel("Zeit")
        ax.set_ylabel("Werte")
        ax.legend(loc='upper left')
        ax.grid()
        self.canvas1.draw()

    ### Dropdown Diagramm ###
    def createPlotControlDropdown(self):
        self.dropdownLayout = QHBoxLayout()
        self.dataSelectionDropdown = CheckableComboBox(self)

        # Hier wird angenommen, dass die erste Reihe von Daten standardmäßig geplottet wird.
        initial_checked = True

        # Füllen des Dropdown-Menüs mit Optionen und Setzen des Checkbox-Zustands
        for label in self.results.keys():
            if label.endswith('_L'):
                self.dataSelectionDropdown.addItem(label)
                item = self.dataSelectionDropdown.model().item(self.dataSelectionDropdown.count() - 1, 0)
                # Prüfen, ob es sich um "Wärmeleistung_L" oder "Last_L" handelt und entsprechend markieren
                if label == 'Wärmeleistung_L':
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Checked if initial_checked else Qt.Unchecked)
                    initial_checked = False  # Nur das erste Element wird standardmäßig ausgewählt

        self.dropdownLayout.addWidget(self.dataSelectionDropdown)
        self.mainLayout.addLayout(self.dropdownLayout)

        # Verbindung des Dropdown-Menüs mit der Aktualisierungsfunktion
        self.dataSelectionDropdown.checkedStateChanged.connect(self.updatePlot)

    def show_additional_results(self):
        if self.tech_objects != [] and self.results != {}:
            print(self.results)
            print(self.tech_objects)

            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(f"Hier gibts noch nichts zu sehen. Nur Konsolenausgabe.")
            msgBox.setWindowTitle("Hier könnten Ergebnisse Visualisiert werden.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

        else:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(f"Es sind keine Berechnungsergebnisse verfügbar. Führen Sie zunächst eine Berechnung durch.")
            msgBox.setWindowTitle("Keine Berechnungsergebnisse vorhanden.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

       
    def on_export_pdf_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'PDF speichern als...', filter='PDF Files (*.pdf)')
        if filename:
            create_pdf(self, filename)