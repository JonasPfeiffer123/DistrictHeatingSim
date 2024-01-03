import logging
import numpy as np
import geopandas as gpd

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, \
    QFileDialog, QHBoxLayout, QComboBox, QLineEdit, QFormLayout, \
        QScrollArea, QMessageBox, QProgressBar

from main import initialize_net_profile_calculation, calculate_results, save_results_csv
from gui.dialogs import HeatDemandEditDialog
from gui.threads import CalculationThread
from net_simulation_pandapipes.net_test import config_plot

class CalculationTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    DEFAULT_PATHS = {
        'Erzeugeranlagen': 'net_generation_QGIS/Beispiel Zittau/Erzeugeranlagen.geojson',
        'HAST': 'net_generation_QGIS/Beispiel Zittau/HAST.geojson',
        'Vorlauf': 'net_generation_QGIS/Beispiel Zittau/Vorlauf.geojson',
        'Rücklauf': 'net_generation_QGIS/Beispiel Zittau/Rücklauf.geojson',
        'Ausgabe': 'results/results_time_series_net1.csv'
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