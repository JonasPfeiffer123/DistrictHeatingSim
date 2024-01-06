import logging
import numpy as np
import geopandas as gpd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, \
    QFileDialog, QHBoxLayout, QComboBox, QLineEdit, QFormLayout, \
        QScrollArea, QMessageBox, QProgressBar, QMenuBar, QAction

from main import calculate_results, save_results_csv
from gui.dialogs import HeatDemandEditDialog, GeojsonDialog, StanetDialog
from gui.threads import NetInitializationGEOJSONThread, NetInitializationSTANETThread, NetCalculationThread
from net_simulation_pandapipes.net_test import config_plot

class CalculationTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    DEFAULT_PATHS = {
        'Ausgabe': 'results/results_time_series_net1.csv'
    }

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.calc_method = "Datensatz"
        self.initUI()

        self.net_data = None  # Variable zum Speichern der Netzdaten

    def updateFilePaths(self, layerNames):
        for key, path in layerNames.items():
            if key in self.DEFAULT_PATHS:
                inputAttrName = f"{key}Input"
                if hasattr(self, inputAttrName):
                    getattr(self, inputAttrName).setText(path)

    def initMenuBar(self):
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        # Wärmenetz-Generierungsmenü
        networkMenu = self.menubar.addMenu('Wärmenetz generieren')

        # Unterpunkte für geojson und Stanet
        geojsonAction = QAction('Netz aus geojson generieren', self)
        stanetAction = QAction('Netz aus Stanet-CSV generieren', self)
        networkMenu.addAction(geojsonAction)
        networkMenu.addAction(stanetAction)

        # Fügen Sie die Menüleiste dem Layout von tab1 hinzu
        self.container_layout.addWidget(self.menubar)

        # Verbindungen zu den Funktionen
        geojsonAction.triggered.connect(self.openGeojsonDialog)
        stanetAction.triggered.connect(self.openStanetDialog)

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
        self.initMenuBar()
        self.setupFileInputs()
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
    
    def openGeojsonDialog(self):
        dialog = GeojsonDialog(
            self.create_and_initialize_net_geojson, 
            self.editHeatDemandData, 
            self.ImportLayers,
            self
        )
        dialog.exec_()

    def openStanetDialog(self):
        dialog = StanetDialog(self.create_and_initialize_net_stanet, self)
        dialog.exec_()

    def editHeatDemandData(self, hastInput):
        try:
            self.gdf_HAST = gpd.read_file(hastInput)
            if "Gebäudetyp" not in self.gdf_HAST.columns:
                self.gdf_HAST["Gebäudetyp"] = "HMF"

            self.dialog = HeatDemandEditDialog(self.gdf_HAST, hastInput, self)
            self.dialog.exec_()  # Öffnet den Dialog als Modal
        except Exception as e:
            logging.error(f"Fehler beim Laden der HAST-Daten: {e}")
            QMessageBox.critical(self, "Fehler", "Fehler beim Laden der HAST-Daten.")

    def ImportLayers(self, vorlaufInput, ruecklaufInput, hastInput, erzeugeranlagenInput):
        # Daten zur zentralen Datenquelle hinzufügen
        self.data_manager.add_data(vorlaufInput)
        self.data_manager.add_data(ruecklaufInput)
        self.data_manager.add_data(hastInput)
        self.data_manager.add_data(erzeugeranlagenInput)
        
        # Signal senden, dass Daten hinzugefügt wurden
        self.data_added.emit(self.data_manager.get_map_data())

    def updateLabelsForCalcMethod(self, calc_method):
        self.calc_method = calc_method
        if calc_method in ["BDEW", "Datensatz"]:  # Angenommen, diese Methoden verwenden 1h-Werte
            time_step_text = "Zeitschritt (1h Werte); Minimum: 0, Maximum: 8760 (1 Jahr) :"
        else:  # Für VDI4655 oder andere Methoden, die 15-min-Werte verwenden
            time_step_text = "Zeitschritt (15 min Werte); Minimum: 0, Maximum: 35040 (1 Jahr) :"

        self.StartTimeStepLabel.setText(time_step_text)
        self.EndTimeStepLabel.setText(time_step_text)

    def setupControlInputs(self):
        # Buttons für die Berechnung und Initialisierung
        self.calculateNetButton = QPushButton('Zeitreihenberechnung durchführen')
        self.LayerImportButton = QPushButton('Layers in Karte importieren')

        # Verbindungen für die Buttons
        self.calculateNetButton.clicked.connect(self.simulate_net)

        # Layout für die Steuerelemente
        controls_layout = QVBoxLayout()
        self.container_layout.addLayout(controls_layout)

        # Eingabefeld für den Startzeitpunkt der Simulation
        self.StartTimeStepLabel = QLabel("", self)
        self.StartTimeStepInput = QLineEdit("0", self)
        # Eingabefeld für den Endzeitpunkt der Simulation
        self.EndTimeStepLabel = QLabel("", self)
        self.EndTimeStepInput = QLineEdit("96", self)

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
    
    def selectFilename(self, inputWidget):
        fname, _ = QFileDialog.getOpenFileName(self, 'Datei auswählen', '', 'All Files (*);;CSV Files (*.csv);;Data Files (*.dat)')
        if fname:  # Prüfen, ob ein Dateiname ausgewählt wurde
            inputWidget.setText(fname)

    def create_and_initialize_net_geojson(self, vorlauf, ruecklauf, hast, erzeugeranlagen, calc_method, building_type):
        gdf_vl = gpd.read_file(vorlauf)
        gdf_rl = gpd.read_file(ruecklauf)
        gdf_HAST = gpd.read_file(hast)
        gdf_WEA = gpd.read_file(erzeugeranlagen)

        self.updateLabelsForCalcMethod(calc_method)

        self.initializationgeojsonThread = NetInitializationGEOJSONThread(gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type, calc_method)
        self.initializationgeojsonThread.calculation_done.connect(self.on_initialization_done)
        self.initializationgeojsonThread.calculation_error.connect(self.on_simulation_error)
        self.initializationgeojsonThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def create_and_initialize_net_stanet(self, stanet_csv):
        #stanet_csv = "C:/Users/username/heating_network_generation/net_simulation_pandapipes/stanet files/Beleg_1/Beleg_1.CSV"

        self.initializationstanetThread = NetInitializationSTANETThread(stanet_csv)
        self.initializationstanetThread.calculation_done.connect(self.on_initialization_done)
        self.initializationstanetThread.calculation_error.connect(self.on_simulation_error)
        self.initializationstanetThread.start()
        self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

    def on_initialization_done(self, results):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus

        self.net, self.yearly_time_steps, self.waerme_ges_W = results

        self.waerme_ges_kW = np.where(self.waerme_ges_W == 0, 0, self.waerme_ges_W / 1000)
        self.plot(self.yearly_time_steps, self.waerme_ges_kW, self.net)

        self.net_data = results

    def plot(self, time_steps, qext_kW, net):
        # Clear previous figure
        self.figure4.clear()
        ax1 = self.figure4.add_subplot(111)

        # Plot für Wärmeleistung auf der ersten Y-Achse
        qext_gesamt_kW = np.sum(qext_kW, axis=0)
        ax1.plot(time_steps, qext_gesamt_kW, 'b-', label=f"Gesamtlast Gebäude")
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
        try:
            calc1 = int(self.StartTimeStepInput.text())
            calc2 = int(self.EndTimeStepInput.text())

            if self.calc_method in ["BDEW", "Datensatz"]:  # Angenommen, diese Methoden verwenden 1h-Werte
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
        if self.net_data is None:
            QMessageBox.warning(self, "Keine Netzdaten", "Bitte generieren Sie zuerst ein Netz.")
            return
        
        self.net, self.yearly_time_steps, self.waerme_ges_W = self.net_data

        try:
            self.calc1, self.calc2 = self.adjustTimeParameters()
            if self.calc1 is None or self.calc2 is None:  # Ungültige Eingaben wurden bereits in adjustTimeParameters behandelt
                return

            self.calculationThread = NetCalculationThread(self.net, self.yearly_time_steps, self.waerme_ges_W, self.calc1, self.calc2)
            self.calculationThread.calculation_done.connect(self.on_simulation_done)
            self.calculationThread.calculation_error.connect(self.on_simulation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)  # Aktiviert den indeterministischen Modus

        except ValueError as e:
            QMessageBox.warning("Ungültige Eingabe", str(e))

    def on_simulation_done(self, results):
        self.progressBar.setRange(0, 1)  # Deaktiviert den indeterministischen Modus
        time_steps, net, net_results, waerme_ges_W = results
        mass_flow_circ_pump, deltap_circ_pump, rj_circ_pump, return_temp_circ_pump, flow_temp_circ_pump, \
            return_pressure_circ_pump, flows_pressure_circ_pump, qext_kW, pressure_junctions = calculate_results(net, net_results)

        self.plot2(time_steps, qext_kW, waerme_ges_W, return_temp_circ_pump, flow_temp_circ_pump)

        output_filename = self.AusgabeInput.text()
        save_results_csv(time_steps, qext_kW, flow_temp_circ_pump, return_temp_circ_pump, output_filename)

    def on_simulation_error(self, error_message):
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
    
    def plot2(self, time_steps, qext_kW, waerme_ges_W, return_temp_circ_pump, flow_temp_circ_pump):
        waermebedarf_gesamt_kW = np.sum(waerme_ges_W, axis=0)/1000
        # Clear previous figure
        self.figure3.clear()
        ax1 = self.figure3.add_subplot(111)

        # Plot für Wärmeleistung auf der ersten Y-Achse
        ax1.plot(time_steps, qext_kW, 'b-', label="Einspeiseleistung Heizzentrale in kW")
        ax1.plot(time_steps, waermebedarf_gesamt_kW[self.calc1:self.calc2], 'g-', label="Gesamtwärmebedarf Wärmeübertrager in kW")
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Wärmeleistung in kW", color='b')
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