"""
Filename: DistrictHeatSim_MVP.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-26
Description: Main GUI file of the DistrictHeatSim-Tool using the Model-View-Presenter (MVP) architecture.

This script initializes and runs the main graphical user interface (GUI) for the DistrictHeatSim tool, 
which is designed for district heating system simulation and management. The tool includes various tabs 
for project management, data visualization, building heating requirements, and heat network calculations.

Classes:
    ProjectConfigManager: Handles loading, saving, and managing project configurations, 
                          including recent projects and resource paths.
    CentralDataManager: Acts as the Model in the MVP architecture, managing central data 
                        and emitting signals related to the project folder.
    HeatSystemPresenter: Serves as the Presenter in the MVP architecture, mediating interactions 
                         between the GUI (View) and the CentralDataManager (Model).
    HeatSystemDesignGUI: The View in the MVP architecture, this class is responsible for 
                         initializing and managing the user interface, including handling user interactions 
                         and updating the display based on data from the Presenter.

Functions:
    - The functions previously defined have been encapsulated within the relevant classes:
        - ProjectConfigManager:
            - get_default_config_path(): Returns the default configuration file path.
            - load_config(): Loads configuration data from the config file.
            - save_config(config): Saves configuration data to the config file.
            - get_last_project(): Retrieves the last opened project path.
            - set_last_project(path): Sets the last opened project path.
            - get_recent_projects(): Retrieves a list of recent project paths.
            - get_resource_path(relative_path): Returns the absolute path to a resource, considering PyInstaller packaging.
        - CentralDataManager:
            - add_data(data): Adds data to the central map data list.
            - get_map_data(): Retrieves the map data list.
            - set_project_folder(path): Sets the project folder path and emits a signal.
            - load_last_project(): Loads the last opened project folder.
        - HeatSystemPresenter:
            - on_project_folder_changed(path): Handles updates when the project folder changes.
            - create_new_project(folder_path, project_name): Creates a new project with the specified name and folder path.
            - save_existing_project(): Saves the current project data.
            - open_existing_project(folder_path): Opens an existing project from the specified folder path.
            - create_project_variant(): Creates a variant of the current project.
            - update_temperature_data(): Updates temperature data based on user input.
            - update_heat_pump_data(): Updates heat pump data based on user input.
        - HeatSystemDesignGUI:
            - initUI(): Initializes the user interface, including the menu bar and tabs.
            - initMenuBar(): Sets up the menu bar and connects actions to methods.
            - update_project_folder_label(path): Updates the project folder label in the UI.
            - show_error_message(message): Displays an error message in a dialog box.
            - show_info_message(message): Displays an informational message in a dialog box.
            - on_create_new_project(): Handles the creation of a new project.
            - on_open_existing_project(): Handles the opening of an existing project.
            - on_save_existing_project(): Handles saving the current project.
            - on_create_project_variant(): Handles the creation of a project variant.
            - applyLightTheme(): Applies the light theme stylesheet.
            - applyDarkTheme(): Applies the dark theme stylesheet.
            - openTemperatureDataSelection(): Opens the temperature data selection dialog.
            - openCOPDataSelection(): Opens the COP data selection dialog.
            - updateTemperatureData(): Updates temperature data in the model based on dialog input.
            - updateHeatPumpData(): Updates heat pump data in the model based on dialog input.

Usage:
    Run this script to launch the DistrictHeatSim GUI. The GUI provides a fully-featured environment for managing 
    district heating projects, with options for creating new projects, opening existing ones, and customizing 
    the interface through light and dark themes.
"""

import sys
import os
import shutil
import warnings
import json
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
from gui.IndividualTab.individual_tab import IndividualTab

from gui.dialogs import TemperatureDataDialog, HeatPumpDataDialog

class ProjectConfigManager:
    """
    Handles loading and saving of project configuration.
    """

    def __init__(self, config_path=None):
        self.config_path = config_path or self.get_default_config_path()

    def get_default_config_path(self):
        """
        Get the path to the default configuration file.
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

    def load_config(self):
        """
        Load the configuration from the config file.
        
        Returns:
            dict: Configuration data.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as file:
                return json.load(file)
        return {}

    def save_config(self, config):
        """
        Save the configuration to the config file.
        
        Args:
            config (dict): Configuration data to be saved.
        """
        with open(self.config_path, 'w') as file:
            json.dump(config, file, indent=4)

    def get_last_project(self):
        """
        Retrieve the last opened project path from the config.
        
        Returns:
            str: Last opened project path.
        """
        config = self.load_config()
        return config.get('last_project', '')

    def set_last_project(self, path):
        """
        Set the last opened project path in the config.
        
        Args:
            path (str): Path to the last opened project.
        """
        config = self.load_config()
        config['last_project'] = path
        if 'recent_projects' not in config:
            config['recent_projects'] = []
        if path not in config['recent_projects']:
            config['recent_projects'].insert(0, path)
            config['recent_projects'] = config['recent_projects'][:5]  # Save only the last 5 projects
        self.save_config(config)

    def get_recent_projects(self):
        """
        Retrieve a list of recent projects from the config.
        
        Returns:
            list: List of recent project paths.
        """
        config = self.load_config()
        return config.get('recent_projects', [])
    
    def get_resource_path(self, relative_path):
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
            base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'districtheatsim')
        return os.path.join(base_path, relative_path)

class CentralDataManager(QObject):
    """
    Manages central data and signals related to the project folder.
    
    Attributes:
        project_folder_changed (pyqtSignal): Signal emitted when the project folder changes.
    """
    project_folder_changed = pyqtSignal(str)

    def __init__(self, config_manager=None):
        """
        Initialize the CentralDataManager.
        """
        super(CentralDataManager, self).__init__()
        self.map_data = []
        self.config_manager = config_manager or ProjectConfigManager()
        self.project_folder = self.config_manager.get_resource_path("project_data\\Beispiel")  # Aufruf der statischen Methode

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
        self.config_manager.set_last_project(path)

    def load_last_project(self):
        """
        Load the last opened project folder.
        """
        last_project = self.config_manager.get_last_project()
        if last_project and os.path.exists(last_project):
            self.set_project_folder(last_project)
        else:
            # Wenn kein Projekt geladen ist, einen leeren String senden, um das Label zu aktualisieren
            self.project_folder_changed.emit("")

class HeatSystemPresenter:
    """
    Acts as a middleman between the Model (CentralDataManager) and the View (HeatSystemDesignGUI).
    """

    def __init__(self, view, model):
        """
        Initialize the HeatSystemPresenter.
        
        Args:
            view: The view instance (HeatSystemDesignGUI).
            model: The model instance (CentralDataManager).
        """
        self.view = view
        self.model = model

        # Connect the model signals to the view updates
        self.model.project_folder_changed.connect(self.on_project_folder_changed)

        # Nach der Initialisierung, prüfe, ob ein Projektordner existiert und aktualisiere das Label entsprechend
        QTimer.singleShot(0, self.update_folder_label_on_startup)

    def update_folder_label_on_startup(self):
        """
        Aktualisiere das Projektordner-Label nach dem Start, um sicherzustellen, 
        dass das Label korrekt initialisiert ist, bevor es verwendet wird.
        """
        self.on_project_folder_changed(self.model.project_folder)

    def on_project_folder_changed(self, path):
        """
        Respond to project folder changes.
        
        Args:
            path (str): The new project folder path.
        """
        self.view.update_project_folder_label(path)

    def create_new_project(self, folder_path, project_name):
        """
        Create a new project.
        
        Args:
            folder_path (str): The folder path to create the project in.
            project_name (str): The name of the new project.
        """
        if folder_path and project_name:
            try:
                full_path = os.path.join(folder_path, project_name)
                os.makedirs(full_path)
                for subdir in ["Gebäudedaten", "Lastgang", "Raumanalyse", "Wärmenetz", "results"]:
                    os.makedirs(os.path.join(full_path, subdir))
                self.model.set_project_folder(full_path)
                return True
            except Exception as e:
                self.view.show_error_message(f"Ein Fehler ist aufgetreten: {e}")
                return False
        return False

    def save_existing_project(self):
        """
        Save the current project.
        """
        if not self.model.project_folder:
            self.view.show_error_message("Kein Projektordner ausgewählt.")
            return

        try:
            # Hier fügen wir die Logik zum Speichern der Projektdaten hinzu
            # Zum Beispiel:
            project_data = self.model.get_map_data()
            save_path = os.path.join(self.model.project_folder, "project_data.json")
            with open(save_path, 'w') as file:
                json.dump(project_data, file, indent=4)
            self.view.show_info_message("Projekt gespeichert.")
        except Exception as e:
            self.view.show_error_message(f"Fehler beim Speichern des Projekts: {str(e)}")

    def open_existing_project(self, folder_path):
        """
        Open an existing project.
        """
        if folder_path and os.path.exists(folder_path):
            try:
                project_data_path = os.path.join(folder_path, "project_data.json")
                if os.path.exists(project_data_path):
                    with open(project_data_path, 'r') as file:
                        project_data = json.load(file)
                    self.model.set_project_folder(folder_path)
                    self.model.map_data = project_data
                    self.view.show_info_message("Projekt geladen.")
                else:
                    self.view.show_error_message("Projektdatei nicht gefunden.")
            except Exception as e:
                self.view.show_error_message(f"Fehler beim Öffnen des Projekts: {str(e)}")
        else:
            self.view.show_error_message("Ungültiger Projektordner.")

    def create_project_variant(self):
        """
        Create a variant of the current project by copying its folder.
        """
        base_dir = os.path.dirname(self.model.project_folder)
        base_name = os.path.basename(self.model.project_folder)
        variant_num = 1

        while True:
            new_project_path = os.path.join(base_dir, f"{base_name} Variante {variant_num}")
            if not os.path.exists(new_project_path):
                break
            variant_num += 1

        try:
            shutil.copytree(self.model.project_folder, new_project_path)
            self.model.set_project_folder(new_project_path)
            return True
        except Exception as e:
            self.view.show_error_message(f"Ein Fehler ist aufgetreten: {str(e)}")
            return False
        
    def update_temperature_data(self):
        """
        Update the temperature data based on the selection dialog.
        """
        TRY = self.view.temperatureDataDialog.getValues()
        self.model.try_filename = TRY.get('TRY-filename', '')

    def update_heat_pump_data(self):
        """
        Update the heat pump data based on the selection dialog.
        """
        COP = self.view.heatPumpDataDialog.getValues()
        self.model.cop_filename = COP.get('COP-filename', '')

class HeatSystemDesignGUI(QMainWindow):
    """
    Main window class for the GUI, initializes all components and handles user interactions.
    
    Attributes:
        presenter (HeatSystemPresenter): The Presenter instance managing logic.
    """

    def __init__(self):
        """
        Initialize the HeatSystemDesignGUI.
        """
        super().__init__()
        self.presenter = None  # Initially, no presenter is set

    def set_presenter(self, presenter):
        """
        Set the presenter for this view and initialize the UI.
        
        Args:
            presenter (HeatSystemPresenter): The Presenter instance to manage logic.
        """
        self.presenter = presenter

        self.temperatureDataDialog = TemperatureDataDialog(self)
        self.heatPumpDataDialog = HeatPumpDataDialog(self)

        self.initUI()  # Now it's safe to initialize the UI

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

        # Initialize the folderLabel
        self.folderLabel = QLabel("Kein Projektordner ausgewählt")
        self.layout1.addWidget(self.folderLabel)

        # Initialize tabs
        self.projectTab = ProjectTab(self.presenter.model)
        self.buildingTab = BuildingTab(self.presenter.model, self)
        self.visTab = VisualizationTab(self.presenter.model)
        self.lod2Tab = LOD2Tab(self.presenter.model, self.visTab, self)
        self.individualTab = IndividualTab(self.presenter.model, self)
        self.calcTab = CalculationTab(self.presenter.model, self)
        self.mixDesignTab = MixDesignTab(self.presenter.model, self)
        self.renovationTab = RenovationTab(self.presenter.model, self)
        self.comparisonTab = ComparisonTab(self.presenter.model)

        tabWidget.addTab(self.projectTab, "Projektdefinition")
        tabWidget.addTab(self.buildingTab, "Wärmebedarf Gebäude")
        tabWidget.addTab(self.visTab, "Verarbeitung Geodaten")
        tabWidget.addTab(self.lod2Tab, "Verarbeitung LOD2-Daten")
        tabWidget.addTab(self.individualTab, "Einzelversorgungslösung")
        tabWidget.addTab(self.calcTab, "Wärmenetzberechnung")
        tabWidget.addTab(self.mixDesignTab, "Erzeugerauslegung und Wirtschaftlichkeitsrechnung")
        tabWidget.addTab(self.renovationTab, "Gebäudesanierung")
        tabWidget.addTab(self.comparisonTab, "Variantenvergleich")

        self.temperatureDataDialog = TemperatureDataDialog(self)
        self.heatPumpDataDialog = HeatPumpDataDialog(self)

        # Connect the model signals to the view updates
        self.presenter.model.project_folder_changed.connect(self.update_project_folder_label)
        self.presenter.model.project_folder_changed.connect(self.updateTemperatureData)
        self.presenter.model.project_folder_changed.connect(self.updateHeatPumpData)

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

        createCopyAction = QAction('Projektkopie erstellen', self)
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

        createNewProjectAction.triggered.connect(self.on_create_new_project)
        chooseProjectAction.triggered.connect(self.on_open_existing_project)
        saveProjectAction.triggered.connect(self.on_save_existing_project)
        createCopyAction.triggered.connect(self.on_create_project_variant)

        chooseTemperatureDataAction.triggered.connect(self.openTemperatureDataSelection)
        createCOPDataAction.triggered.connect(self.openCOPDataSelection)
        lightThemeAction.triggered.connect(lambda: self.applyTheme('styles\\win11_light.qss'))
        darkThemeAction.triggered.connect(lambda: self.applyTheme('styles\\dark_mode.qss'))

    def update_project_folder_label(self, path):
        """
        Update the project folder label in the UI.
        
        Args:
            path (str): The current project folder path.
        """
        if path:
            self.folderLabel.setText(f"Ausgewählter Projektordner: {path}")
        else:
            self.folderLabel.setText("Kein Projektordner ausgewählt")

    def show_error_message(self, message):
        """
        Display an error message to the user.
        
        Args:
            message (str): The error message to display.
        """
        QMessageBox.critical(self, "Fehler", message)

    def on_create_new_project(self):
        """
        Handle the creation of a new project.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Speicherort für neues Projekt wählen")
        if folder_path:
            projectName, ok = QInputDialog.getText(self, 'Neues Projekt', 'Projektnamen eingeben:')
            if ok and projectName:
                success = self.presenter.create_new_project(folder_path, projectName)
                if success:
                    QMessageBox.information(self, "Projekt erstellt", f"Projekt '{projectName}' wurde erfolgreich erstellt.")

    def on_open_existing_project(self):
        """
        Handle opening an existing project.
        """
        folder_path = QFileDialog.getExistingDirectory(self, "Projektordner auswählen")
        if folder_path:
            self.presenter.open_existing_project(folder_path)

    def on_save_existing_project(self):
        """
        Handle saving the current project.
        """
        self.presenter.save_existing_project()

    def on_create_project_variant(self):
        """
        Handle creating a project variant.
        """
        success = self.presenter.create_project_variant()
        if success:
            QMessageBox.information(self, "Info", "Projektvariante wurde erfolgreich erstellt.")

    def applyTheme(self, theme_path):
        qss_path = self.presenter.model.config_manager.get_resource_path(theme_path)
        if os.path.exists(qss_path):
            with open(qss_path, 'r') as file:
                self.setStyleSheet(file.read())
        else:
            self.show_error_message(f"Stylesheet {qss_path} nicht gefunden.")

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

    model = CentralDataManager()
    view = HeatSystemDesignGUI()
    presenter = HeatSystemPresenter(view, model)

    view.set_presenter(presenter)
    view.applyTheme("styles\\win11_light.qss")

    # Show the window maximized after a short delay; time delay is needed to show the window maximized
    QTimer.singleShot(100, view.showMaximized)

    view.show()
    sys.exit(app.exec_())