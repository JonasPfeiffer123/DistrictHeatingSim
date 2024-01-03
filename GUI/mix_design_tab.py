import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, \
    QHBoxLayout, QComboBox, QLineEdit, QListWidget, QDialog

from main import import_results_csv, import_TRY
from gui.dialogs import TechInputDialog
from heat_generators.heat_generator_classes import *

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