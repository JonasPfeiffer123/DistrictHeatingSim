import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget
from gui.visualization_tab import VisualizationTab
from gui.calculation_tab import CalculationTab
from gui.mix_design_main_window import MixDesignMainWindow

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
        self.setWindowTitle("Here could be a cool software name")
        self.setGeometry(100, 100, 800, 600)  # Optional, standard size before full-screen

        layout = QVBoxLayout(self)
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget)

        # Creating individual tabs
        self.data_manager = CentralDataManager()

        self.visTab = VisualizationTab(self.data_manager)
        self.calcTab = CalculationTab(self.data_manager)
        self.mixDesignTab1 = MixDesignMainWindow()

        # Establishing connections here
        self.visTab.connect_signals(self.calcTab)
        self.visTab.layers_imported.connect(self.calcTab.updateFilePaths)

        # Adding tabs to the tab widget
        tabWidget.addTab(self.visTab, "Visualization GIS Data")
        tabWidget.addTab(self.calcTab, "Network Calculation")
        tabWidget.addTab(self.mixDesignTab1, "Generator Mix Design")

        # Set the layout
        self.setLayout(layout)

        # Maximize the main window to the screen size
        self.showMaximized()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HeatSystemDesignGUI()
    ex.show()
    sys.exit(app.exec_())
