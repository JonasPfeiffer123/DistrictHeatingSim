"""
Filename: DistrictHeatSim.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-30
Description: Main GUI file of the DistrictHeatSim-Tool.

This script initializes and runs the main graphical user interface (GUI) for the DistrictHeatSim tool. 
It includes various tabs for project management, data visualization, building heating requirements, 
and heat network calculations.

Classes:
    CentralDataManager: Manages central data and signals related to the project folder.
    HeatSystemDesignGUI: Main window class for the GUI, initializes all components and handles user interactions.

Functions:
    get_resource_path(relative_path): Returns the absolute path to a resource, considering PyInstaller packaging.
    get_config_path(): Returns the path to the configuration file.
    load_config(): Loads the configuration from the config file.
    save_config(config): Saves the configuration to the config file.
    get_last_project(): Retrieves the last opened project path from the config.
    set_last_project(path): Sets the last opened project path in the config.
    get_recent_projects(): Retrieves a list of recent projects from the config.

Usage:
    Run this script to launch the DistrictHeatSim GUI.
"""

import sys
import os
import shutil
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMenuBar, QAction, QFileDialog, QLabel, QMessageBox, QInputDialog
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from gui.ProjectTab.project_tab import ProjectTab
from gui.VisualizationTab.visualization_tab import VisualizationTab
from gui.LOD2Tab.lod2_tab import LOD2Tab
from gui.BuildingTab.building_tab import BuildingTab
from gui.RenovationTab.RenovationTab import RenovationTab
from gui.CalculationTab.calculation_tab import CalculationTab
from gui.MixDesignTab.mix_design_tab import MixDesignTab
from gui.ComparisonTab.comparison_tab import ComparisonTab

from gui.Dialogs import TemperatureDataDialog, HeatPumpDataDialog

def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, considering if the script is packaged with PyInstaller.
    
    Args:
        relative_path (str): Relative path to the resource.
    
    Returns:
        str: Absolute path to the resource.
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'DistrictHeatSim')
    return os.path.join(base_path, relative_path)

import json

def get_config_path():
    """
    Get the path to the configuration file.
    
    Returns:
        str: Path to the config file.
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

def load_config():
    """
    Load the configuration from the config file.
    
    Returns:
        dict: Configuration data.
    """
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    """
    Save the configuration to the config file.
    
    Args:
        config (dict): Configuration data to be saved.
    """
    config_path = get_config_path()
    with open(config_path, 'w') as file:
        json.dump(config, file, indent=4)

def get_last_project():
    """
    Retrieve the last opened project path from the config.
    
    Returns:
        str: Last opened project path.
    """
    config = load_config()
    return config.get('last_project', '')

def set_last_project(path):
    """
    Set the last opened project path in the config.
    
    Args:
        path (str): Path to the last opened project.
    """
    config = load_config()
    config['last_project'] = path
    if 'recent_projects' not in config:
        config['recent_projects'] = []
    if path not in config['recent_projects']:
        config['recent_projects'].insert(0, path)
        config['recent_projects'] = config['recent_projects'][:5]  # Save only the last 5 projects
    save_config(config)

def get_recent_projects():
    """
    Retrieve a list of recent projects from the config.
    
    Returns:
        list: List of recent project paths.
    """
    config = load_config()
    return config.get('recent_projects', [])

class CentralDataManager(QObject):
    """
    Manages central data and signals related to the project folder.
    
    Attributes:
        project_folder_changed (pyqtSignal): Signal emitted when the project folder changes.
    """
    project_folder_changed = pyqtSignal(str)

    def __init__(self):
        """
        Initialize the CentralDataManager.
        """
        super(CentralDataManager, self).__init__()
        self.map_data = []
        self.project_folder = get_resource_path("project_data\\Beispiel")
        print(self.project_folder)

    def add_data(self, data):
        """
        Add data to the map data list.
        
        Args:
            data: Data to be added.
        """
        self.map_data.append(data)

    def get_map_data(self):
        """
        Get the map data list.
        
        Returns:
            list: Map data list.
        """
        return self.map_data

    def set_project_folder(self, path):
        """
        Set the project folder path and emit the project_folder_changed signal.
        
        Args:
            path (str): Path to the project folder.
        """
        self.project_folder = path
        self.project_folder_changed.emit(path)

class HeatSystemDesignGUI(QMainWindow):
    """
    Main window class for the GUI, initializes all components and handles user interactions.
    
    Attributes:
        data_manager (CentralDataManager): Instance of CentralDataManager.
        projectFolderPath (str): Path to the current project folder.
        temperatureDataDialog (TemperatureDataDialog): Dialog for selecting temperature data.
        heatPumpDataDialog (HeatPumpDataDialog): Dialog for selecting heat pump data.
        layout1 (QVBoxLayout): Main layout of the central widget.
        folderLabel (QLabel): Label displaying the current project folder path.
    """

    def __init__(self):
        """
        Initialize the HeatSystemDesignGUI.
        """
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

        # Ensure the window is maximized after all initializations
        self.showMaximized()

        # Load the last opened project after a short delay
        QTimer.singleShot(100, self.load_last_project)

    def initUI(self):
        """
        Initialize the user interface, including the menu bar and tabs.
        """
        self.setWindowTitle("DistrictHeatSim")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.layout1 = QVBoxLayout(central_widget)

        self.initMenuBar()

        tabWidget = QTabWidget()
        self.layout1.addWidget(tabWidget)

        self.projectTab = ProjectTab(self.data_manager)
        self.buildingTab = BuildingTab(self.data_manager, self)
        self.visTab = VisualizationTab(self.data_manager)
        self.lod2Tab = LOD2Tab(self.data_manager, self.visTab, self)
        self.calcTab = CalculationTab(self.data_manager, self)
        self.mixDesignTab = MixDesignTab(self.data_manager, self)
        self.renovationTab = RenovationTab(self.data_manager, self)
        self.comparisonTab = ComparisonTab(self.data_manager)

        tabWidget.addTab(self.projectTab, "Projektdefinition")
        tabWidget.addTab(self.buildingTab, "Wärmebedarf Gebäude")
        tabWidget.addTab(self.visTab, "Verarbeitung Geodaten")
        tabWidget.addTab(self.lod2Tab, "Verarbeitung LOD2-Daten")
        tabWidget.addTab(self.calcTab, "Wärmenetzberechnung")
        tabWidget.addTab(self.mixDesignTab, "Erzeugerauslegung und Wirtschaftlichkeitsrechnung")
        tabWidget.addTab(self.renovationTab, "Gebäudesanierung")
        tabWidget.addTab(self.comparisonTab, "Variantenvergleich")

        if self.data_manager.project_folder:
            self.folderLabel = QLabel(f"Standard-Projektordner: {self.data_manager.project_folder}")
        else:
            self.folderLabel = QLabel("Kein Ordner ausgewählt")
        self.layout1.addWidget(self.folderLabel)

    def initMenuBar(self):
        """
        Initialize the menu bar and its actions.
        """
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        fileMenu = self.menubar.addMenu('Datei')

        createNewProjectAction = QAction('Neues Projekt erstellen', self)
        chooseProjectAction = QAction('Projekt öffnen', self)
        saveProjectAction = QAction('Projekt speichern', self)
        fileMenu.addAction(createNewProjectAction)
        fileMenu.addAction(chooseProjectAction)
        fileMenu.addAction(saveProjectAction)

        # Always add the recent projects menu
        recentMenu = fileMenu.addMenu('Zuletzt geöffnet')
        recent_projects = get_recent_projects()
        if recent_projects:
            for project in recent_projects:
                action = QAction(project, self)
                action.triggered.connect(lambda checked, p=project: self.setProjectFolderPath(p))
                recentMenu.addAction(action)
        else:
            no_recent_action = QAction('Keine kürzlich geöffneten Projekte', self)
            no_recent_action.setEnabled(False)
            recentMenu.addAction(no_recent_action)

        createCopyAction = QAction('Projektkopie erstellen', self)
        createCopyAction.triggered.connect(self.createProjectVariant)
        fileMenu.addAction(createCopyAction)

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

        createNewProjectAction.triggered.connect(self.createNewProject)
        chooseProjectAction.triggered.connect(self.openExistingProject)
        saveProjectAction.triggered.connect(self.saveExistingProject)

        chooseTemperatureDataAction.triggered.connect(self.openTemperatureDataSelection)
        createCOPDataAction.triggered.connect(self.openCOPDataSelection)
        lightThemeAction.triggered.connect(self.applyLightTheme)
        darkThemeAction.triggered.connect(self.applyDarkTheme)

    def applyLightTheme(self):
        """
        Apply the light theme stylesheet.
        """
        qss_path = get_resource_path('styles/win11_light.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as file:
                self.setStyleSheet(file.read())
        else:
            print(f"Stylesheet {qss_path} not found.")

    def applyDarkTheme(self):
        """
        Apply the dark theme stylesheet.
        """
        qss_path = get_resource_path('styles/dark_mode.qss')
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as file:
                self.setStyleSheet(file.read())
        else:
            print(f"Stylesheet {qss_path} not found.")

    def createNewProject(self):
        """
        Create a new project by selecting a folder and entering a project name.
        """
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
        """
        Open an existing project by selecting a project folder.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Projektordner auswählen")
        if folder_path:
            self.setProjectFolderPath(folder_path)

        # Projektergebnisse laden
        # die einzelnen Ladefunktionen der Projekttabs nacheinander aufrufen
        # Netz in Karte laden
        # Koordinaten in Karte laden
        #self.visTab.loadNetData()
        
        # Pandapipes Netz laden
        #self.calcTab.loadNet()

        # Pandapipes Berechnungsergebnisse Zeitreihe laden
        #self.calcTab.load_net_results()

        # Erzeugerrechnung Ergebnisse laden
        #self.mixDesignTab.load_results_JSON()

        # ...
        pass


    def saveExistingProject(self):
        """
        Save the current project's results.
        """
        # Projektergebnisse speichern ...
        # die einzelnen Speicherfunktionen der Projekttabs nacheinander aufrufen, wenn vorhanden

        # Pandapipes Netz speichern
        #self.calcTab.saveNet()

        # dimensioniertes geoJSON Netz speichern
        #self.calcTab.exportNetGeoJSON()

        # Erzeugerrechnung Ergebnisse speichern
        #self.mixDesignTab.save_results_JSON()
        pass

    def createProjectVariant(self):
        """
        Create a variant of the current project by copying its folder.
        """
        if not self.projectFolderPath:
            QMessageBox.warning(self, "Warnung", "Kein Projektordner ausgewählt.", QMessageBox.Ok)
            return

        base_dir = os.path.dirname(self.projectFolderPath)
        base_name = os.path.basename(self.projectFolderPath)
        variant_num = 1

        while True:
            new_project_path = os.path.join(base_dir, f"{base_name} Variante {variant_num}")
            if not os.path.exists(new_project_path):
                break
            variant_num += 1

        try:
            shutil.copytree(self.projectFolderPath, new_project_path)
            QMessageBox.information(self, "Info", f"Projektvariante wurde erfolgreich erstellt: {new_project_path}")
            self.setProjectFolderPath(new_project_path)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Ein Fehler ist aufgetreten: {str(e)}")

    def load_last_project(self):
        """
        Load the last opened project after a short delay.
        """
        last_project = get_last_project()
        if last_project and os.path.exists(last_project):
            self.setProjectFolderPath(last_project)

    def setProjectFolderPath(self, path):
        """
        Set the project folder path and update related components.
        
        Args:
            path (str): Path to the project folder.
        """
        self.projectFolderPath = path
        self.data_manager.set_project_folder(path)
        self.folderLabel.setText(f"Ausgewählter Projektordner: {path}")
        set_last_project(path)  # Save the last opened project

    def openTemperatureDataSelection(self):
        """
        Open the temperature data selection dialog.
        """
        if self.temperatureDataDialog.exec_():
            self.updateTemperatureData()

    def openCOPDataSelection(self):
        """
        Open the COP data selection dialog.
        """
        if self.heatPumpDataDialog.exec_():
            self.updateHeatPumpData()

    def updateTemperatureData(self):
        """
        Update the temperature data based on the selection dialog.
        """
        TRY = self.temperatureDataDialog.getValues()
        self.try_filename = TRY['TRY-filename']

    def updateHeatPumpData(self):
        """
        Update the heat pump data based on the selection dialog.
        """
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
    else:
        print(f"Stylesheet {qss_path} not found.")

    ex = HeatSystemDesignGUI()
    ex.showMaximized()
    ex.show()
    sys.exit(app.exec_())