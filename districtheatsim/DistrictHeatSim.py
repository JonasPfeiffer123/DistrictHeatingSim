import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMenuBar, QAction, QFileDialog, QLabel, QMessageBox, QInputDialog
from PyQt5.QtCore import QObject, pyqtSignal

from gui.ProjectTab.project_tab import ProjectTab
from gui.VisualizationTab.visualization_tab import VisualizationTab
from gui.BuildingTab.building_tab import BuildingTab
from gui.RenovationTab.RenovationTab import RenovationTab
from gui.CalculationTab.calculation_tab import CalculationTab
from gui.MixDesignTab.mix_design_tab import MixDesignTab
from gui.ComparisonTab.comparison_tab import ComparisonTab

from gui.Dialogs import TemperatureDataDialog, HeatPumpDataDialog

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'DistrictHeatSim')
    return os.path.join(base_path, relative_path)

class CentralDataManager(QObject):
    project_folder_changed = pyqtSignal(str)

    def __init__(self):
        super(CentralDataManager, self).__init__()
        self.map_data = []
        self.project_folder = get_resource_path("project_data\\Beispiel")
        print(self.project_folder)

    def add_data(self, data):
        self.map_data.append(data)

    def get_map_data(self):
        return self.map_data

    def set_project_folder(self, path):
        self.project_folder = path
        self.project_folder_changed.emit(path)

class HeatSystemDesignGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_manager = CentralDataManager()
        self.projectFolderPath = None

        self.temperatureDataDialog = TemperatureDataDialog(self)
        self.heatPumpDataDialog = HeatPumpDataDialog(self)

        self.updateTemperatureData()
        self.updateHeatPumpData()

        self.initUI()

        self.data_manager.project_folder_changed.connect(self.projectTab.updateDefaultPath)
        self.data_manager.project_folder_changed.connect(self.visTab.updateDefaultPath)
        self.data_manager.project_folder_changed.connect(self.calcTab.updateDefaultPath)
        self.data_manager.project_folder_changed.connect(self.mixDesignTab.updateDefaultPath)

    def initUI(self):
        self.setWindowTitle("DistrictHeatSim")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.layout1 = QVBoxLayout(central_widget)

        self.initMenuBar()

        tabWidget = QTabWidget()
        self.layout1.addWidget(tabWidget)

        self.projectTab = ProjectTab(self.data_manager)
        self.visTab = VisualizationTab(self.data_manager)
        self.buildingTab = BuildingTab(self.data_manager, self.visTab, self)
        self.renovationTab = RenovationTab()
        self.calcTab = CalculationTab(self.data_manager, self)
        self.mixDesignTab = MixDesignTab(self.data_manager, self)
        self.comparisonTab = ComparisonTab(self.data_manager)

        tabWidget.addTab(self.projectTab, "Projektdefinition")
        tabWidget.addTab(self.visTab, "Verarbeitung Geodaten")
        tabWidget.addTab(self.buildingTab, "Gebäudedefinition")
        tabWidget.addTab(self.renovationTab, "Gebäudesanierung")
        tabWidget.addTab(self.calcTab, "Wärmenetzberechnung")
        tabWidget.addTab(self.mixDesignTab, "Erzeugerauslegung und Wirtschaftlichkeitsrechnung")
        tabWidget.addTab(self.comparisonTab, "Variantenvergleich")

        if self.data_manager.project_folder:
            self.folderLabel = QLabel(f"Standard-Projektordner: {self.data_manager.project_folder}")
        else:
            self.folderLabel = QLabel("Kein Ordner ausgewählt")
        self.layout1.addWidget(self.folderLabel)

    def initMenuBar(self):
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        fileMenu = self.menubar.addMenu('Datei')

        chooseProjectFolderAction = QAction('Projektordner festlegen', self)
        createNewProjectFolderAction = QAction('Neues Projekt erstellen', self)
        fileMenu.addAction(chooseProjectFolderAction)
        fileMenu.addAction(createNewProjectFolderAction)

        dataMenu = self.menubar.addMenu('Datenbasis')
        chooseTemperatureDataAction = QAction('Temperaturdaten festlegen', self)
        createCOPDataAction = QAction('COP-Kennfeld festlegen', self)
        dataMenu.addAction(chooseTemperatureDataAction)
        dataMenu.addAction(createCOPDataAction)

        themeMenu = self.menubar.addMenu('Thema')
        lightThemeAction = QAction('Lichtmodus', self)
        darkThemeAction = QAction('Dunkelmodus', self)
        themeMenu.addAction(lightThemeAction)
        themeMenu.addAction(darkThemeAction)

        self.layout1.addWidget(self.menubar)

        chooseProjectFolderAction.triggered.connect(self.openExistingProject)
        createNewProjectFolderAction.triggered.connect(self.createNewProject)
        chooseTemperatureDataAction.triggered.connect(self.openTemperatureDataSelection)
        createCOPDataAction.triggered.connect(self.openCOPDataSelection)
        lightThemeAction.triggered.connect(self.applyLightTheme)
        darkThemeAction.triggered.connect(self.applyDarkTheme)

    def applyLightTheme(self):
        qss_path = get_resource_path('styles/win11_light.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as file:
                self.setStyleSheet(file.read())
            print(f"Light theme applied from {qss_path}")
        else:
            print(f"Stylesheet {qss_path} not found.")

    def applyDarkTheme(self):
        qss_path = get_resource_path('styles/dark_mode.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as file:
                self.setStyleSheet(file.read())
            print(f"Dark theme applied from {qss_path}")
        else:
            print(f"Stylesheet {qss_path} not found.")

    def createNewProject(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Speicherort für neues Projekt wählen")
        if folder_path:
            projectName, ok = QInputDialog.getText(self, 'Neues Projekt', 'Projektnamen eingeben:')
            if ok and projectName:
                try:
                    full_path = os.path.join(folder_path, projectName)
                    os.makedirs(full_path)
                    for subdir in ["Gebäudedaten", "Lastgang", "Raumanalyse", "Wärmenetz", "results"]:
                        os.makedirs(os.path.join(full_path, subdir))
                    QMessageBox.information(self, "Projekt erstellt", f"Projekt '{projectName}' wurde erfolgreich erstellt.")
                    self.setProjectFolderPath(full_path)
                except Exception as e:
                    QMessageBox.critical(self, "Fehler", f"Ein Fehler ist aufgetreten: {e}")

    def openExistingProject(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Projektordner auswählen")
        if folder_path:
            self.setProjectFolderPath(folder_path)

    def setProjectFolderPath(self, path):
        self.projectFolderPath = path
        self.data_manager.set_project_folder(path)
        self.folderLabel.setText(f"Ausgewählter Projektordner: {path}")

    def openTemperatureDataSelection(self):
        if self.temperatureDataDialog.exec_():
            self.updateTemperatureData()

    def openCOPDataSelection(self):
        if self.heatPumpDataDialog.exec_():
            self.updateHeatPumpData()

    def updateTemperatureData(self):
        TRY = self.temperatureDataDialog.getValues()
        self.try_filename = TRY['TRY-filename']

    def updateHeatPumpData(self):
        COP = self.heatPumpDataDialog.getValues()
        self.cop_filename = COP['COP-filename']

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Set Light Theme
    qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'styles', 'win11_light.qss')
    if os.path.exists(qss_path):
        with open(qss_path, 'r') as file:
            app.setStyleSheet(file.read())
        print(f"Light theme applied from {qss_path}")
    else:
        print(f"Stylesheet {qss_path} not found.")

    ex = HeatSystemDesignGUI()
    ex.showMaximized()
    ex.show()
    sys.exit(app.exec_())