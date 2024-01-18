import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget
from building_simulation import BuildingTab
from heat_pump_simulation import HeatPumpTab
from heat_generators_simulation import HeatGenTab

class HeatSystemDesignGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Simulationstool Wärmebedarfe Gebäude")
        self.setGeometry(0, 0, 1920, 1080)  # Optional, Standardgröße vor Vollbild

        # Starten Sie im Vollbildmodus
        #self.showFullScreen()

        layout = QVBoxLayout(self)
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget)

        self.buildSimTab = BuildingTab()
        self.heatPumpTab = HeatPumpTab()
        self.heatgenTab = HeatGenTab()

        # Hier stellen Sie die Verbindung her
        #self.visTab.connect_signals(self.calcTab)
        #self.visTab.layers_imported.connect(self.calcTab.updateFilePaths)

        # Hinzufügen der Tabs zum Tab-Widget
        tabWidget.addTab(self.buildSimTab, "Simulation Gebäudewärmebedarf")
        tabWidget.addTab(self.heatPumpTab, "Simulation Wärmepumpe")
        tabWidget.addTab(self.heatgenTab, "Simulation Versorgung")

        # Set the layout
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())