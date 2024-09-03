"""
Filename: DistrictHeatSim_MVP.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-28
Description: Main GUI file of the DistrictHeatSim-Tool utilizing the Model-View-Presenter (MVP) architecture.

This script initializes and runs the main graphical user interface (GUI) for the DistrictHeatSim tool,
which is designed for simulating and managing district heating systems. The tool includes various tabs
for project management, data visualization, building heating requirements, and heat network calculations.

The script has been modularized for better maintainability and separation of concerns, dividing the responsibilities
among several distinct classes:

Classes:
    1. ProjectConfigManager:
        - Handles the loading, saving, and management of project configurations, including maintaining a history
          of recent projects and resolving resource paths.

    2. DataManager:
        - Responsible for managing central data related to the application, such as map data, which can be accessed
          and modified as needed.

    3. ProjectFolderManager:
        - Manages operations related to the project folder, such as setting the project folder path and emitting
          signals when changes occur. This class also handles loading the last opened project.

    4. HeatSystemPresenter:
        - Acts as the Presenter in the MVP architecture, mediating interactions between the GUI (View) and
          the underlying data and configuration managers (Model). It facilitates project creation, opening,
          variant creation, and updates to the data based on user actions.

    5. HeatSystemDesignGUI:
        - Serves as the View in the MVP architecture, responsible for initializing and managing the user interface.
          This class handles user interactions, updates the display based on data from the Presenter, and manages
          the GUI's various components, such as tabs and dialogs.

Functions:
    - The functionality is encapsulated within the relevant classes, promoting modularity and clarity:
        - ProjectConfigManager:
            - get_default_config_path(): Returns the path to the default configuration file.
            - load_config(): Loads configuration data from the config file.
            - save_config(config): Saves configuration data to the config file.
            - get_last_project(): Retrieves the path of the last opened project.
            - set_last_project(path): Sets the path of the last opened project.
            - get_recent_projects(): Retrieves a list of recently opened project paths.
            - get_resource_path(relative_path): Resolves the absolute path to a resource, considering PyInstaller packaging.

        - DataManager:
            - add_data(data): Adds data to the map data list.
            - get_map_data(): Retrieves the current map data list.

        - ProjectFolderManager:
            - set_project_folder(path): Sets the project folder path and emits a signal upon change.
            - load_last_project(): Loads the last opened project folder, emitting a signal if not found.

        - HeatSystemPresenter:
            - create_new_project(folder_path, project_name): Creates a new project with the specified name and folder path.
            - open_existing_project(folder_path): Opens an existing project from the specified folder path.
            - create_project_variant(): Creates a variant of the current project by duplicating its folder.
            - update_temperature_data(): Updates temperature data based on user input.
            - update_heat_pump_data(): Updates heat pump data based on user input.

        - HeatSystemDesignGUI:
            - initUI(): Initializes the user interface, including the menu bar and tabs.
            - initMenuBar(): Sets up the menu bar and connects actions to their respective methods.
            - update_project_folder_label(path): Updates the project folder label in the UI.
            - show_error_message(message): Displays an error message in a dialog box.
            - show_info_message(message): Displays an informational message in a dialog box.
            - on_create_new_project(): Handles the creation of a new project by the user.
            - on_open_existing_project(): Handles the opening of an existing project by the user.
            - on_create_project_variant(): Handles the creation of a project variant by the user.
            - applyTheme(theme_path): Applies the selected theme stylesheet to the GUI.
            - openTemperatureDataSelection(): Opens the temperature data selection dialog.
            - openCOPDataSelection(): Opens the COP data selection dialog.
            - updateTemperatureData(): Updates the temperature data in the model based on dialog input.
            - updateHeatPumpData(): Updates heat pump data in the model based on dialog input.

Usage:
    To launch the DistrictHeatSim GUI, run this script. The GUI offers a comprehensive environment for managing
    district heating projects, providing features such as project creation, data visualization, and configuration
    customization through light and dark themes. The modular design facilitates ease of maintenance and extension.
"""

import sys
import os
import shutil
import warnings
import json
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMenuBar, QAction, QFileDialog, QLabel, QMessageBox, QInputDialog
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon

from gui.ProjectTab.project_tab import ProjectTab
from gui.VisualizationTab.visualization_tab import VisualizationTab
from gui.LOD2Tab.lod2_tab import LOD2Tab
from gui.BuildingTab.building_tab import BuildingTab
from gui.RenovationTab.RenovationTab import RenovationTab
from gui.CalculationTab.calculation_tab import CalculationTab
from gui.MixDesignTab.mix_design_tab import MixDesignTab
from gui.ComparisonTab.comparison_tab import ComparisonTab
from gui.IndividualTab.individual_tab import IndividualTab
from gui.PVTab.pv_tab import PVTab

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

class DataManager:
    """
    Manages central data for the application.
    """

    def __init__(self):
        self.map_data = []
        self.try_filename = None  # New attribute for storing TRY filename
        self.cop_filename = None  # New attribute for storing COP filename

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
    
    def set_try_filename(self, filename):
        """
        Set the TRY filename.
        
        Args:
            filename (str): The filename of the TRY data.
        """
        self.try_filename = filename

    def get_try_filename(self):
        """
        Get the TRY filename.
        
        Returns:
            str: The filename of the TRY data.
        """
        return self.try_filename

    def set_cop_filename(self, filename):
        """
        Set the COP filename.
        
        Args:
            filename (str): The filename of the COP data.
        """
        self.cop_filename = filename

    def get_cop_filename(self):
        """
        Get the COP filename.
        
        Returns:
            str: The filename of the COP data.
        """
        return self.cop_filename

class ProjectFolderManager(QObject):
    """
    Manages the project folder and emits signals related to changes.
    
    Attributes:
        project_folder_changed (pyqtSignal): Signal emitted when the project folder changes.
    """
    project_folder_changed = pyqtSignal(str)

    def __init__(self, config_manager=None):
        super(ProjectFolderManager, self).__init__()
        self.config_manager = config_manager or ProjectConfigManager()
        self.project_folder = self.config_manager.get_resource_path("project_data\\Beispiel")

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
            self.project_folder_changed.emit("")
        
class HeatSystemPresenter:
    """
    Acts as a middleman between the Model (CentralDataManager) and the View (HeatSystemDesignGUI).
    """

    def __init__(self, view, folder_manager, data_manager):
        """
        Initialize the HeatSystemPresenter.
        
        Args:
            view: The view instance (HeatSystemDesignGUI).
            model: The model instance (CentralDataManager).
        """
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager

        # Connect the model signals directly to the view updates
        self.folder_manager.project_folder_changed.connect(self.view.update_project_folder_label)

        # Initialize the folder label on startup
        QTimer.singleShot(0, lambda: self.view.update_project_folder_label(self.folder_manager.project_folder))

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
                self.folder_manager.set_project_folder(full_path)
                return True
            except Exception as e:
                self.view.show_error_message(f"Ein Fehler ist aufgetreten: {e}")
                return False
        return False

    def open_existing_project(self, folder_path):
        """
        Open an existing project by selecting a project folder.
        """
        if folder_path:
            self.folder_manager.set_project_folder(folder_path)

    def create_project_variant(self):
        """
        Create a variant of the current project by copying its folder.
        """
        base_dir = os.path.dirname(self.folder_manager.project_folder)
        base_name = os.path.basename(self.folder_manager.project_folder)
        variant_num = 1

        while True:
            new_project_path = os.path.join(base_dir, f"{base_name} Variante {variant_num}")
            if not os.path.exists(new_project_path):
                break
            variant_num += 1

        try:
            shutil.copytree(self.folder_manager.project_folder, new_project_path)
            self.folder_manager.set_project_folder(new_project_path)
            return True
        except Exception as e:
            self.view.show_error_message(f"Ein Fehler ist aufgetreten: {str(e)}")
            return False

class HeatSystemDesignGUI(QMainWindow):
    """
    Main window class for the GUI, initializes all components and handles user interactions.
    
    Attributes:
        presenter (HeatSystemPresenter): The Presenter instance managing logic.
    """

    def __init__(self, folder_manager, data_manager):
        """
        Initialize the HeatSystemDesignGUI.
        """
        super().__init__()
        self.presenter = None  # Initially, no presenter is set
        self.folder_manager = folder_manager
        self.data_manager = data_manager

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

        # Set the window icon, if available
        icon = QIcon("styles\\logo.JPG")
        if icon.isNull():
            print("Icon could not be loaded.")
        self.setWindowIcon(icon)

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
        self.projectTab = ProjectTab(self.presenter.folder_manager)
        self.buildingTab = BuildingTab(self.presenter.folder_manager, self.presenter.data_manager)
        self.visTab = VisualizationTab(self.presenter.folder_manager)
        self.lod2Tab = LOD2Tab(self.presenter.folder_manager, self.presenter.data_manager)
        self.renovationTab = RenovationTab(self.presenter.folder_manager, self.presenter.data_manager)
        self.calcTab = CalculationTab(self.presenter.folder_manager, self.presenter.data_manager, self)
        self.mixDesignTab = MixDesignTab(self.presenter.folder_manager, self.presenter.data_manager, self)
        self.comparisonTab = ComparisonTab(self.presenter.folder_manager, self.presenter.data_manager)
        self.individualTab = IndividualTab(self.presenter.folder_manager, self.presenter.data_manager)
        self.pvTab = PVTab(self.presenter.folder_manager, self.presenter.data_manager)

        tabWidget.addTab(self.projectTab, "Projektdefinition")
        tabWidget.addTab(self.buildingTab, "Wärmebedarf Gebäude")
        tabWidget.addTab(self.visTab, "Wärmenetz generieren")
        tabWidget.addTab(self.lod2Tab, "Verarbeitung LOD2-Daten")
        tabWidget.addTab(self.renovationTab, "Gebäudesanierung")
        tabWidget.addTab(self.calcTab, "Wärmenetzberechnung")
        tabWidget.addTab(self.mixDesignTab, "Erzeugerauslegung und Wirtschaftlichkeitsrechnung")
        tabWidget.addTab(self.comparisonTab, "Variantenvergleich")
        tabWidget.addTab(self.individualTab, "Einzelversorgungslösung")
        tabWidget.addTab(self.pvTab, "Photovoltaik")

        self.temperatureDataDialog = TemperatureDataDialog(self)
        self.heatPumpDataDialog = HeatPumpDataDialog(self)

        # Connect the model signals to the view updates
        self.folder_manager.project_folder_changed.connect(self.update_project_folder_label)
        self.presenter.folder_manager.project_folder_changed.connect(self.updateTemperatureData)
        self.presenter.folder_manager.project_folder_changed.connect(self.updateHeatPumpData)

    def initMenuBar(self):
        """
        Initialize the menu bar and its actions.
        """
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        fileMenu = self.menubar.addMenu('Datei')

        createNewProjectAction = QAction('Neues Projekt erstellen', self)
        chooseProjectAction = QAction('Projekt öffnen', self)
        fileMenu.addAction(createNewProjectAction)
        fileMenu.addAction(chooseProjectAction)

         # Always add the recent projects menu
        recentMenu = fileMenu.addMenu('Zuletzt geöffnet')
        recent_projects = self.presenter.folder_manager.config_manager.get_recent_projects()
        if recent_projects:
            for project in recent_projects:
                action = QAction(project, self)
                action.triggered.connect(lambda checked, p=project: self.presenter.folder_manager.set_project_folder(p))
                recentMenu.addAction(action)
        else:
            no_recent_action = QAction('Keine kürzlich geöffneten Projekte', self)
            no_recent_action.setEnabled(False)
            recentMenu.addAction(no_recent_action)

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

    def on_create_project_variant(self):
        """
        Handle creating a project variant.
        """
        success = self.presenter.create_project_variant()
        if success:
            QMessageBox.information(self, "Info", "Projektvariante wurde erfolgreich erstellt.")

    def applyTheme(self, theme_path):
        qss_path = self.presenter.folder_manager.config_manager.get_resource_path(theme_path)
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
        self.data_manager.set_try_filename(TRY['TRY-filename'])  # Save to DataManager

    def updateHeatPumpData(self):
        """
        Update the heat pump data based on the selection dialog.
        """
        COP = self.heatPumpDataDialog.getValues()
        self.data_manager.set_cop_filename(COP['COP-filename'])  # Save to DataManager


    def show_info_message(self, message):
        """
        Display an informational message to the user.
        
        Args:
            message (str): The informational message to display.
        """
        QMessageBox.information(self, "Info", message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setWindowIcon(QIcon("styles\\logo.JPG"))

    # Initialize the managers
    config_manager = ProjectConfigManager()
    folder_manager = ProjectFolderManager(config_manager)
    data_manager = DataManager()

    # Initialize the GUI
    view = HeatSystemDesignGUI(folder_manager, data_manager)

    # Initialize the presenter and link it to the view
    presenter = HeatSystemPresenter(view, folder_manager, data_manager)
    view.set_presenter(presenter)
    view.applyTheme("styles\\win11_light.qss")

    presenter.view.updateTemperatureData()
    presenter.view.updateHeatPumpData()

    # Setup and show the UI
    view.initUI()
    QTimer.singleShot(0, view.showMaximized)

    view.show()
    sys.exit(app.exec_())
