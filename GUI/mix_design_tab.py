import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, \
    QHBoxLayout, QComboBox, QLineEdit, QListWidget, QDialog, QProgressBar, \
        QMessageBox, QFileDialog, QScrollArea

from gui.dialogs import TechInputDialog
from heat_generators.heat_generator_classes import *
from gui.threads import CalculateMixThread

class MixDesignTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()

    def initFileInputs(self):
        # Ergebnis-CSV Input
        self.FilenameInput = QLineEdit('results/results_time_series_net.csv')
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
        # Haupt-Scrollbereich für den gesamten Tab
        mainScrollArea = QScrollArea(self)
        mainScrollArea.setWidgetResizable(True)

        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)
        
        self.DatenEingabeLabel = QLabel('Dateneingaben')
        mainLayout.addWidget(self.DatenEingabeLabel)

        # Hinzufügen zum Layout
        filemain_layout = QHBoxLayout()
        filemain_layout.addWidget(self.FilenameInput)
        filemain_layout.addWidget(self.selectFileButton)
        mainLayout.addLayout(filemain_layout)

        # Hinzufügen zum Layout
        fileLayout2 = QHBoxLayout()
        fileLayout2.addWidget(self.tryFilenameInput)
        fileLayout2.addWidget(self.selectTRYFileButton)
        mainLayout.addLayout(fileLayout2)

        # Hinzufügen zum Layout
        fileLayout3 = QHBoxLayout()
        fileLayout3.addWidget(self.copFilenameInput)
        fileLayout3.addWidget(self.selectCOPFileButton)
        mainLayout.addLayout(fileLayout3)
        
        self.costEingabeLabel = QLabel('Wirtschaftliche Vorgaben')
        mainLayout.addWidget(self.costEingabeLabel)

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
        self.calculateButton.clicked.connect(self.start_calculation)

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

        # ScrollArea für Diagramme
        diagramScrollArea = QScrollArea()
        diagramScrollArea.setWidgetResizable(True)
        diagramScrollArea.setMinimumSize(800, 1200) 

        # Widget und Layout für Diagramme
        diagramWidget = QWidget()
        diagramLayout = QVBoxLayout(diagramWidget)

        # Erstes Diagramm
        self.figure1 = Figure()
        self.canvas1 = FigureCanvas(self.figure1)
        self.canvas1.setMinimumSize(800, 600)
        diagramLayout.addWidget(self.canvas1)

        # Zweites Diagramm
        self.figure2 = Figure()
        self.canvas2 = FigureCanvas(self.figure2)
        self.canvas2.setMinimumSize(800, 600)
        diagramLayout.addWidget(self.canvas2)

        # Fügen Sie das Diagramm-Widget der ScrollArea hinzu
        diagramScrollArea.setWidget(diagramWidget)

        # Add widgets to layout
        mainLayout.addLayout(inputLayout)
        mainLayout.addWidget(self.techEingabeLabel)
        mainLayout.addWidget(self.techComboBox)
        mainLayout.addLayout(buttonLayout)
        mainLayout.addWidget(self.techList)
        mainLayout.addWidget(self.load_scale_factorLabel)
        mainLayout.addWidget(self.load_scale_factorInput)
        mainLayout.addWidget(self.calculateEingabeLabel)
        mainLayout.addWidget(self.calculateButton)
        mainLayout.addWidget(self.optimizeEingabeLabel)
        mainLayout.addWidget(self.optimizeButton)
        mainLayout.addWidget(self.resultLabel)
        mainLayout.addWidget(diagramScrollArea)

        self.progressBar = QProgressBar(self)
        mainLayout.addWidget(self.progressBar)

        # Setzen Sie das Haupt-Widget in die Haupt-ScrollArea
        mainScrollArea.setWidget(mainWidget)

        # Setzen Sie das Layout des Tabs auf ein Layout, das nur die Haupt-ScrollArea enthält
        tabLayout = QVBoxLayout(self)
        tabLayout.addWidget(mainScrollArea)
        self.setLayout(tabLayout)

    def selectFilename(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def optimize(self):
        self.start_calculation(True)

    def start_calculation(self, optimize=False):
        filename = self.FilenameInput.text()
        load_scale_factor = float(self.load_scale_factorInput.text())
        try_filename = self.tryFilenameInput.text()
        cop_filename = self.copFilenameInput.text()
        gaspreis = float(self.gaspreisInput.text())
        strompreis = float(self.strompreisInput.text())
        holzpreis = float(self.holzpreisInput.text())
        BEW = self.BEWComboBox.itemText(self.BEWComboBox.currentIndex())
        tech_objects = self.tech_objects  # Stellen Sie sicher, dass dies thread-sicher ist!

        self.calculationThread = CalculateMixThread(
            filename, load_scale_factor, try_filename, cop_filename,
            gaspreis, strompreis, holzpreis, BEW, tech_objects, optimize
        )
        self.calculationThread.calculation_done.connect(self.on_calculation_done)
        self.calculationThread.calculation_error.connect(self.on_calculation_error)
        self.calculationThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def on_calculation_done(self, result):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus
        # Extrahieren Sie die benötigten Daten aus dem Ergebnis
        WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, Wärmemengen, WGK, Anteile, specific_emissions, techs, time_steps = result
        
        # Aktualisieren Sie die GUI mit den Ergebnissen
        self.showResults(Jahreswärmebedarf, WGK_Gesamt, techs, Wärmemengen, WGK, Anteile)
    
        # Beispiel für das Plotten der Ergebnisse
        self.plot1(time_steps, data_L, data_labels_L, Anteile, Last_L)

    def on_calculation_error(self, error_message):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus
        QMessageBox.critical(self, "Berechnungsfehler", error_message)

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