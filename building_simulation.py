import sys

import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QScrollArea, QApplication, QPushButton, QLineEdit

from heat_requirement import heat_requirement_VDI4655, heat_requirement_BDEW

class BuildingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def resizeEvent(self, event):
        # Passen Sie die Größe der ScrollArea an die neue Fenstergröße an
        self.scrollArea.resize(self.width(), self.height())
        # Rufen Sie die Basisklasse resizeEvent auf, um die Standard-Resize-Events zu handhaben
        super(BuildingTab, self).resizeEvent(event)

    def initUI(self):
        self.setWindowTitle("Gebäudesimulator")
        self.setGeometry(0, 0, 1920, 1080)  # Optional, Standardgröße vor Vollbild

        # Haupt-Scrollbereich für den gesamten Tab
        layout = QVBoxLayout(self)

        mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(mainWidget)

        self.setupInputs()

        # Button zur Ausführung der Zeitreihenberechnung
        self.calculateNetButton = QPushButton('Lastgang berechnen', self)
        self.calculateNetButton.clicked.connect(self.calculate)
        self.mainLayout.addWidget(self.calculateNetButton)

        self.setupPlotLayout()

        # Setzen Sie das Haupt-Widget in die Haupt-ScrollArea
        layout.addWidget(mainWidget)

    def setupInputs(self):
        # Eingabefeld für den Startzeitpunkt der Simulation
        self.mainLayout.addWidget(QLabel("Jahreswärmebedarf in kWh", self))
        self.JahreswärmebedarfInput = QLineEdit("15000", self)
        self.mainLayout.addWidget(self.JahreswärmebedarfInput)

        # Eingabefeld für den Endzeitpunkt der Simulation
        self.mainLayout.addWidget(QLabel("Jahresstrombedarf in kWh", self))
        self.JahresstrombedarfInput = QLineEdit("4000", self)
        self.mainLayout.addWidget(self.JahresstrombedarfInput)

        # Hinzufügen der Berechnungsmethoden-Auswahl
        self.calcMethodInput = QComboBox(self)
        self.calcMethodInput.addItems(["BDEW", "VDI4655"])
        self.mainLayout.addWidget(QLabel("Berechnungsmethode:"))
        self.mainLayout.addWidget(self.calcMethodInput)

        # Hinzufügen der Gebäudetypen-Auswahl
        self.buildingTypeInput = QComboBox(self)
        self.mainLayout.addWidget(QLabel("Gebäudetyp:"))
        self.mainLayout.addWidget(self.buildingTypeInput)
        self.updateBuildingType()  # Initialisiert die Gebäudetypen basierend auf der Berechnungsmethode

        self.calcMethodInput.currentIndexChanged.connect(self.updateBuildingType)

    def setupPlotLayout(self):
        self.scrollArea = QScrollArea(self)  # Erstelle ein ScrollArea-Widget
        self.scrollWidget = QWidget()  # Erstelle ein Widget für den Inhalt der ScrollArea
        self.scrollLayout = QVBoxLayout(self.scrollWidget)  # Erstelle ein Layout für das Scroll-Widget

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(800, 800)  # Setze eine Mindestgröße für die Canvas
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.scrollLayout.addWidget(self.canvas)
        self.scrollLayout.addWidget(self.toolbar)

        # Setze das Scroll-Widget als Inhalt der ScrollArea
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)  # Erlaubt das Resize der Inhalte innerhalb der ScrollArea

        # Füge die ScrollArea zum Hauptlayout hinzu
        self.mainLayout.addWidget(self.scrollArea)

    def updateBuildingType(self):
        self.buildingTypeInput.clear()
        if self.calcMethodInput.currentText() == "VDI4655":
            self.buildingTypeInput.setDisabled(False)
            self.buildingTypeInput.addItems(["EFH", "MFH"])
        elif self.calcMethodInput.currentText() == "BDEW":
            self.buildingTypeInput.setDisabled(False)
            self.buildingTypeInput.addItems(["HEF", "HMF", "GKO", "GHA", "GMK", "GBD", "GBH", "GWA", "GGA", "GBA", "GGB", "GPD", "GMF", "GHD"])
    
    def calculate(self):
        JEB_Wärme_ges_kWh = int(self.JahreswärmebedarfInput.text())
        JEB_Strom_kWh = int(self.JahresstrombedarfInput.text())
        building_type = self.buildingTypeInput.currentText()
        calc_method = self.calcMethodInput.currentText()
        
        JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh = JEB_Wärme_ges_kWh * 0.2, JEB_Wärme_ges_kWh * 0.8

        time_steps = None

        if calc_method == "VDI4655":
            time_steps, strom_W, _, _, waerme_ges_kW = heat_requirement_VDI4655.calculate(JEB_Heizwärme_kWh, JEB_Trinkwarmwasser_kWh, JEB_Strom_kWh, building_type=building_type)

        if calc_method == "BDEW":
            time_steps, waerme_ges_kW  = heat_requirement_BDEW.calculate(JEB_Wärme_ges_kWh, building_type, subtyp="03")

        waerme_ges_kW = np.array(waerme_ges_kW)

        self.plot(time_steps, waerme_ges_kW)
    
    def plot(self, time_steps, waerme_ges_kW):
        # Clear previous figure
        self.figure.clear()
        ax1 = self.figure.add_subplot(111)

        ax1.plot(time_steps, waerme_ges_kW, 'b-', label=f"Gesamtlast Gebäude")
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Wärmebedarf in kW", color='b')
        ax1.tick_params('y', colors='b')
        ax1.legend(loc='upper left')
        ax1.plot
        ax1.grid()
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BuildingTab()
    ex.show()
    sys.exit(app.exec_())