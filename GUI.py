import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QHBoxLayout, QListWidget, QComboBox, QDialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

import heat_generators.heat_generator_classes as hgs
from simulate_functions import *
from heat_generators.Solarthermie import import_TRY

from GUI_Dialogfenster import TechInputDialog

class HeatSystemDesignGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.tech_objects = []
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
    
    def berechne_und_visualisiere_WGK(self, techs, time_steps, calc1, calc2, initial_data, TRY, COP_data, BEW):
        # Definieren Sie die Preisbereiche
        Gaspreis_Bereich = np.arange(40, 51, 10)  # Beispiel: von 40 bis 100 in Schritten von 10
        Strompreis_Bereich = np.arange(100, 121, 20)
        Holzpreis_Bereich = np.arange(40, 51, 10)

        # Initialisieren Sie ein leeres Array für die Ergebnisse
        WGK_Ergebnisse = []

        # Iterieren Sie über die Preisbereiche und führen Sie Berechnungen durch
        for Gaspreis in Gaspreis_Bereich:
            for Strompreis in Strompreis_Bereich:
                for Holzpreis in Holzpreis_Bereich:
                    WGK_Gesamt, _, _, _, _, _, _, _, _ = \
                        Berechnung_Erzeugermix(techs, time_steps, calc1, calc2, initial_data, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW)
                    WGK_Ergebnisse.append((Gaspreis, Strompreis, Holzpreis, WGK_Gesamt))

        # Visualisieren Sie die Ergebnisse
        plt.figure(figsize=(10, 6))
        for Gaspreis, Strompreis, Holzpreis, WGK in WGK_Ergebnisse:
            plt.scatter(Gaspreis, WGK, color='red', label='Gaspreis')
            plt.scatter(Strompreis, WGK, color='blue', label='Strompreis')
            plt.scatter(Holzpreis, WGK, color='green', label='Holzpreis')
        plt.xlabel('Energiepreis (€/Einheit)')
        plt.ylabel('Wärmegestehungskosten (€/MWh)')
        plt.title('Wärmegestehungskosten in Abhängigkeit von den Energiepreisen')
        plt.legend()
        plt.grid(True)
        plt.show()

    def create_net(self):
        calc1, calc2 = 0, 35040 # min: 0; max: 35040
        filename = 'results_time_series_net1.csv'
        #gdf_vl = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Vorlauf.geojson')
        #gdf_rl = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Rücklauf.geojson')
        #gdf_HAST = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/HAST.geojson')
        #gdf_WEA = gpd.read_file('net_generation_QGIS/Beispiel Zittau 2/Erzeugeranlagen.geojson')

        #time_15min, time_steps, net, net_results = thermohydraulic_time_series_net_calculation(calc1, calc2, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA)

        #mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
        #    return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

        ###!!!!!this will overwrite the current csv file!!!!!#
        #save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, filename)
        #plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)

    def calculate(self, optimize=False):
        calc1, calc2 = 0, 35040 # min: 0; max: 35040
        filename = 'results_time_series_net.csv'

        time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump = import_results_csv(filename)
        #plot_results(time_steps, qext_kW, return_temp_circ_pump, flow_temp_circ_pump)
        initial_data = qext_kW, flow_temp_circ_pump, return_temp_circ_pump

        TRY_filename = 'heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat'
        TRY = import_TRY(TRY_filename)
        COP_data = np.genfromtxt('heat_generators/Kennlinien WP.csv', delimiter=';')
        
        Gaspreis = float(self.gaspreisInput.text())
        Strompreis = float(self.strompreisInput.text())
        Holzpreis = float(self.holzpreisInput.text())
        BEW = self.BEWComboBox.itemText(self.BEWComboBox.currentIndex())
        techs = self.tech_objects  

        if optimize == True:
            techs = optimize_mix(techs, time_steps, calc1, calc2, initial_data, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW)

        WGK_Gesamt, Jahreswärmebedarf, Last_L, data_L, data_labels_L, Wärmemengen, WGK, Anteile, specific_emissions  = \
        Berechnung_Erzeugermix(techs, time_steps, calc1, calc2, initial_data, TRY, COP_data, Gaspreis, Strompreis, Holzpreis, BEW)
        
        self.showResults(Jahreswärmebedarf, WGK_Gesamt, techs, Wärmemengen, WGK, Anteile)

        #self.berechne_und_visualisiere_WGK(techs, time_steps, calc1, calc2, initial_data, TRY, COP_data, BEW)

        # Example of plotting
        self.plot(time_steps, data_L, data_labels_L, Anteile, Last_L)

    def plot(self, t, data_L, data_labels_L, Anteile, Last_L):
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())
