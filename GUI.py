import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QHBoxLayout, QListWidget, QComboBox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

import heat_generators.heat_generator_classes as hgs
from simulate_functions import *
from heat_generators.Solarthermie import import_TRY

class HeatSystemDesignGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # Create widgets
        #self.loadDataFileButton = QPushButton('Load Data File')
        #self.loadDataFileButton.clicked.connect(self.loadFile)
        #layout.addWidget(self.loadDataFileButton)

        #self.loadTRYFileButton = QPushButton('Load TRY File')
        #self.loadTRYFileButton.clicked.connect(self.loadFile)
        #layout.addWidget(self.loadTRYFileButton)

        #self.loadCOPFileButton = QPushButton('Load COP File')
        #self.loadCOPFileButton.clicked.connect(self.loadFile)
        #layout.addWidget(self.loadCOPFileButton)

        # Parameter Inputs
        self.bruttoflächeSTAInput = QLineEdit("100")
        self.vsInput = QLineEdit("10")
        self.PBMKInput = QLineEdit("50")
        self.thLeistungBHKWInput = QLineEdit("30")
        self.gaspreisInput = QLineEdit("70")
        self.strompreisInput = QLineEdit("150")
        self.holzpreisInput = QLineEdit("50")
        self.flächeInput = QLineEdit("100")
        self.bohrtiefeInput = QLineEdit("100")
        self.temperaturGeothermieInput = QLineEdit("10")
        self.KühlleistungAbwärmeInput = QLineEdit("20")
        self.TemperaturAbwärmeInput = QLineEdit("30")

        # Labels
        self.bruttoflächeSTALabel = QLabel('Bruttofläche STA (m²):')
        self.vsLabel = QLabel('VS (m³):')
        self.PBMKLabel = QLabel('P BMK (kW):')
        self.thLeistungBHKWLabel = QLabel('th Leistung BHKW (kW):')
        self.gaspreisLabel = QLabel('Gaspreis:')
        self.strompreisLabel = QLabel('Strompreis:')
        self.holzpreisLabel = QLabel('Holzpreis:')
        self.flächeLabel = QLabel('Fläche:')
        self.bohrtiefeLabel = QLabel('Bohrtiefe:')
        self.temperaturGeothermieLabel = QLabel('Temperatur Geothermie:')
        self.KühlleistungAbwärmeLabel = QLabel('Kühlleistung Abwärme:')
        self.TemperaturAbwärmeLabel = QLabel('Temperatur Abwärme:')
        
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
        inputLayout.addWidget(self.bruttoflächeSTALabel)
        inputLayout.addWidget(self.bruttoflächeSTAInput)
        inputLayout.addWidget(self.vsLabel)
        inputLayout.addWidget(self.vsInput)
        inputLayout.addWidget(self.PBMKLabel)
        inputLayout.addWidget(self.PBMKInput)
        inputLayout.addWidget(self.thLeistungBHKWLabel)
        inputLayout.addWidget(self.thLeistungBHKWInput)
        inputLayout.addWidget(self.gaspreisLabel)
        inputLayout.addWidget(self.gaspreisInput)
        inputLayout.addWidget(self.strompreisLabel)
        inputLayout.addWidget(self.strompreisInput)
        inputLayout.addWidget(self.holzpreisLabel)
        inputLayout.addWidget(self.holzpreisInput)
        inputLayout.addWidget(self.flächeLabel)
        inputLayout.addWidget(self.flächeInput)
        inputLayout.addWidget(self.bohrtiefeLabel)
        inputLayout.addWidget(self.bohrtiefeInput)
        inputLayout.addWidget(self.temperaturGeothermieLabel)
        inputLayout.addWidget(self.temperaturGeothermieInput)
        inputLayout.addWidget(self.KühlleistungAbwärmeLabel)
        inputLayout.addWidget(self.KühlleistungAbwärmeInput)
        inputLayout.addWidget(self.TemperaturAbwärmeLabel)
        inputLayout.addWidget(self.TemperaturAbwärmeInput)


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
        layout.addLayout(inputLayout)
        layout.addWidget(self.techComboBox)
        layout.addLayout(buttonLayout)
        layout.addWidget(self.techList)
        layout.addWidget(self.calculateButton)
        layout.addWidget(self.optimizeButton)
        layout.addWidget(self.resultLabel)
        layout.addLayout(chartLayout)

        # Set the layout
        self.setLayout(layout)

    def addTech(self):
        selectedTech = self.techComboBox.currentText()
        self.techList.addItem(selectedTech)

    def removeTech(self):
        self.techList.clear()

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
    
    def showResults(self, Jahreswärmebedarf, WGK_Gesamt, tech_order, Wärmemengen, WGK, Anteile):
        resultText = f"Jahreswärmebedarf: {Jahreswärmebedarf:.2f} MWh\n"
        resultText += f"Wärmegestehungskosten Gesamt: {WGK_Gesamt:.2f} €/MWh\n\n"

        for t, wärmemenge, anteil, wgk in zip(tech_order, Wärmemengen, Anteile, WGK):
            resultText += f"Wärmemenge {t}: {wärmemenge:.2f} MWh\n"
            resultText += f"Wärmegestehungskosten {t}: {wgk:.2f} €/MWh\n"
            resultText += f"Anteil an Wärmeversorgung {t}: {anteil:.2f}\n\n"

        self.resultLabel.setText(resultText)

    def optimize(self):
        self.calculate(True)
    
    def calculate(self, optimize=False):
        ############## CALCULATION #################
        calc1, calc2 = 0, 35040 # min: 0; max: 35040
        filename = 'results_time_series_net.csv'

        #gdf_vl = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Vorlauf.geojson')
        #gdf_rl = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Rücklauf.geojson')
        #gdf_HAST = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/HAST.geojson')
        #gdf_WEA = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Erzeugeranlagen.geojson')

        #time_15min, time_steps, net, net_results = thermohydraulic_time_series_net_calculation(calc1, calc2, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA)

        #mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
        #    return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

        ###!!!!!this will overwrite the current csv file!!!!!#
        #save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, filename)

        time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump = import_results_csv(filename)

        #plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)

        initial_data = qext_kW, flow_temp_circ_pump, return_temp_circ_pump

        TRY_filename = 'heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat'
        TRY = import_TRY(TRY_filename)
        COP_data = np.genfromtxt('heat_generators/Kennlinien WP.csv', delimiter=';')
        
        Typ = "Vakuumröhrenkollektor"
        BEW = "Nein"

        bruttofläche_STA = float(self.bruttoflächeSTAInput.text())
        vs = float(self.vsInput.text())
        P_BMK = float(self.PBMKInput.text())
        th_Leistung_BHKW = float(self.thLeistungBHKWInput.text())
        Gaspreis = float(self.gaspreisInput.text())
        Strompreis = float(self.strompreisInput.text())
        Holzpreis = float(self.holzpreisInput.text())
        Fläche = float(self.flächeInput.text())
        Bohrtiefe = float(self.bohrtiefeInput.text())
        Temperatur_Geothermie = float(self.temperaturGeothermieInput.text())
        Kühlleistung_Abwärme = float(self.KühlleistungAbwärmeInput.text())
        Temperatur_Abwärme = float(self.TemperaturAbwärmeInput.text())

        tech_order = self.getListItems()

        if optimize == True:
            initial_values = [10, 10, 10, 10]

            optimized_values = hgs.optimize_mix(initial_values, time_steps, calc1, calc2, initial_data, TRY, \
                                         COP_data, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, Gaspreis, \
                                         Strompreis, Holzpreis, BEW, tech_order, Kühlleistung_Abwärme, Temperatur_Abwärme)
            
            bruttofläche_STA, vs,  P_BMK, th_Leistung_BHKW = optimized_values

        WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, Wärmemengen, WGK, Anteile = \
                hgs.Berechnung_Erzeugermix(time_steps, calc1, calc2, bruttofläche_STA, vs, Typ, Fläche, Bohrtiefe, Temperatur_Geothermie, P_BMK, Gaspreis, Strompreis, \
                                            Holzpreis, initial_data, TRY, tech_order, BEW, th_Leistung_BHKW, Kühlleistung_Abwärme, Temperatur_Abwärme, COP_data)
        
        self.showResults(Jahreswärmebedarf, WGK_Gesamt, tech_order, Wärmemengen, WGK, Anteile)

        # Example of plotting
        self.plot(time_steps, data_L, data_labels_L, Anteile)

    def plot(self, t, data_L, data_labels_L, Anteile):
        # Clear previous figure
        self.figure1.clear()
        self.figure2.clear()

        ax1 = self.figure1.add_subplot(111)
        ax2 = self.figure2.add_subplot(111)

        #ax.plot(t, Last_L, color="black", linewidth=0.1, label="Last in kW")
        ax1.stackplot(t, data_L, labels=data_labels_L)
        ax1.set_title("Jahresdauerlinie")
        ax1.set_xlabel("Jahresstunden")
        ax1.set_ylabel("thermische Leistung in kW")
        ax1.legend(loc='upper center')
        ax1.plot

        ax2.pie(Anteile, labels=data_labels_L, autopct='%1.1f%%', startangle=90)
        ax2.set_title("Anteile Wärmeerzeugung")
        ax2.legend(loc='center right')
        ax2.axis("equal")
        ax2.plot

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())
