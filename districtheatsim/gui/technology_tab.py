from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QLineEdit, QListWidget, QDialog, \
                             QFileDialog, QMenuBar, QScrollArea, QAction, QAbstractItemView
from PyQt5.QtCore import pyqtSignal

from heat_generators.heat_generator_classes import *
from gui.mix_design_dialogs import TechInputDialog

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.parent().updateTechObjectsOrder()

class TechnologyTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.results = {}
        self.initFileInputs()
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
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

        mainScrollArea.setWidget(mainWidget)

        tabLayout = QVBoxLayout(self)
        tabLayout.addWidget(mainScrollArea)  # Scrollbereich darunter hinzufügen
        self.setLayout(tabLayout)

    def setupMenu(self):
        # Erstellen der Menüleiste
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)
        # Menü für das Hinzufügen von Wärmeerzeugern
        addHeatGeneratorMenu = self.menuBar.addMenu('Wärmeerzeuger hinzufügen')

        # Liste der verfügbaren Wärmeerzeuger
        heatGenerators = ["Solarthermie", "BHKW", "Holzgas-BHKW", "Geothermie", "Abwärme", 
                        "Flusswasser", "Biomassekessel", "Gaskessel"]
        # Aktionen für jeden Wärmeerzeuger erstellen
        for generator in heatGenerators:
            action = QAction(generator, self)
            # Wichtig: Der `lambda` Ausdruck sollte keine Referenz auf das `self` Objekt (MixDesignTab) enthalten
            # stattdessen übergeben wir `None` als `tech_data`, wenn das Dialogfenster geöffnet wird.
            action.triggered.connect(lambda checked, gen=generator: self.addTech(gen, None))
            addHeatGeneratorMenu.addAction(action)

        self.mainLayout.addWidget(self.menuBar)

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
        