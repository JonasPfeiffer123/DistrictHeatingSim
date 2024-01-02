import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget
from GUI.tabs import VisualizationTab, CalculationTab, MixDesignTab

class CentralDataManager:
    def __init__(self):
        self.map_data = []

    def add_data(self, data):
        self.map_data.append(data)
        # Trigger any updates needed for the map

    def get_map_data(self):
        return self.map_data
    
class HeatSystemDesignGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Hier könnte ein cooler Softwarename stehen")
        self.setGeometry(100, 100, 800, 600)  # Optional, Standardgröße vor Vollbild

        # Starten Sie im Vollbildmodus
        #self.showFullScreen()

        layout = QVBoxLayout(self)
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget)

        # Erstellen der einzelnen Tabs
        self.data_manager = CentralDataManager()

        self.calcTab = CalculationTab(self.data_manager)
        self.mixDesignTab = MixDesignTab()
        self.visTab = VisualizationTab(self.data_manager)

        # Hier stellen Sie die Verbindung her
        self.visTab.connect_signals(self.calcTab)

        # Hinzufügen der Tabs zum Tab-Widget
        tabWidget.addTab(self.calcTab, "Netzberechnung")
        tabWidget.addTab(self.mixDesignTab, "Auslegung Erzeugermix")
        tabWidget.addTab(self.visTab, "Visualisierung GIS-Daten")

        # Set the layout
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())
