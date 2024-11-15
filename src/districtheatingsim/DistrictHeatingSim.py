"""
Filename: DistrictHeatingSim.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-28
Description: Main GUI file of the DistrictHeatingSim-Tool utilizing the Model-View-Presenter (MVP) architecture.

This script initializes and runs the main graphical user interface (GUI) for the DistrictHeatingSim tool,
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
import time
import shutil
import warnings
import json
import traceback
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMenuBar, QAction, 
                             QFileDialog, QLabel, QMessageBox, QInputDialog)
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QPixmap

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
from gui.results_pdf import create_pdf
from gui.dialogs import TemperatureDataDialog, HeatPumpDataDialog

from gui.PyQt5_leaflet.leaflet_tab import VisualizationTabLeaflet

class ProjectConfigManager:
    """
    Handles loading and saving of project configuration and file paths.
    """

    def __init__(self, config_path=None, file_paths_path=None):
        self.config_path = config_path or self.get_default_config_path()
        self.file_paths_path = file_paths_path or self.get_default_file_paths_path()
        self.config_data = self.load_config()  # Load the config data upon initialization
        self.file_paths_data = self.load_file_paths()  # Load file paths data upon initialization
        
    def get_default_config_path(self):
        """
        Get the path to the default configuration file.
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

    def get_default_file_paths_path(self):
        """
        Get the path to the default file paths file.
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'file_paths.json')

    def load_config(self):
        """
        Load the configuration from the config file using UTF-8 encoding.
        
        Returns:
            dict: Configuration data.
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        return {}

    def load_file_paths(self):
        """
        Load the file paths from the file paths file using UTF-8 encoding.
        
        Returns:
            dict: File paths data.
        """
        if os.path.exists(self.file_paths_path):
            with open(self.file_paths_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        return {}

    def save_config(self, config):
        """
        Save the configuration to the config file using UTF-8 encoding.
        
        Args:
            config (dict): Configuration data to be saved.
        """
        with open(self.config_path, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=4, ensure_ascii=False)

    def save_file_paths(self, file_paths):
        """
        Save the file paths to the file paths file using UTF-8 encoding.
        
        Args:
            file_paths (dict): File paths data to be saved.
        """
        with open(self.file_paths_path, 'w', encoding='utf-8') as file:
            json.dump(file_paths, file, indent=4, ensure_ascii=False)

    def get_last_project(self):
        """
        Retrieve the last opened project path from the config.
        
        Returns:
            str: Last opened project path.
        """
        return self.config_data.get('last_project', '')

    def set_last_project(self, path):
        """
        Set the last opened project path in the config.
        
        Args:
            path (str): Path to the last opened project.
        """
        self.config_data['last_project'] = path
        if 'recent_projects' not in self.config_data:
            self.config_data['recent_projects'] = []
        if path not in self.config_data['recent_projects']:
            self.config_data['recent_projects'].insert(0, path)
            self.config_data['recent_projects'] = self.config_data['recent_projects'][:5]  # Save only the last 5 projects
        self.save_config(self.config_data)

    def get_recent_projects(self):
        """
        Retrieve a list of recent projects from the config.
        
        Returns:
            list: List of recent project paths.
        """
        return self.config_data.get('recent_projects', [])

    def get_relative_path(self, key):
        """
        Get the relative path from the file_paths.json.
        
        Args:
            key (str): The key for the resource path in the JSON file.
        
        Returns:
            str: The relative path for the resource.
        """
        relative_path = self.file_paths_data.get(key, "")
        if not relative_path:
            raise KeyError(f"Key '{key}' not found in file paths configuration.")
        
        return relative_path

    def get_resource_path(self, key):
        """
        Get the absolute path to a resource, considering if the script is packaged with PyInstaller.
        
        Args:
            key (str): The key for the resource path in the JSON file.
        
        Returns:
            str: The absolute path for the resource.
        """
        relative_path = self.get_relative_path(key)
        
        # If running in a PyInstaller environment, use the _MEIPASS path
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            # Normal path when not bundled
            base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'districtheatingsim')
        
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

        # Setze den Projektordner und den Standard-Variantenordner
        self.project_folder = self.config_manager.get_resource_path("standard_folder_path")
        self.variant_folder = self.config_manager.get_resource_path("standard_variant_path")

        # Emit signal for the initial project and variant folder
        self.emit_project_and_variant_folder()

    def emit_project_and_variant_folder(self):
        """
        Emit signal for both project and variant folder.
        """
        if self.project_folder and self.variant_folder and os.path.exists(self.variant_folder):
            print(f"Initial variant folder set to: {self.variant_folder}")
            self.project_folder_changed.emit(self.variant_folder)
        elif self.project_folder:
            # If variant folder does not exist, set a default variant
            print("No variant folder found, setting default variant")
            self.variant_folder = os.path.join(self.project_folder, "Variante 1")
            self.project_folder_changed.emit(self.variant_folder)

    def set_project_folder(self, path):
        """
        Set the project folder path and emit the project_folder_changed signal.
        """
        self.project_folder = path
        self.config_manager.set_last_project(self.project_folder)

        # Check if the variant folder exists, otherwise set a default variant
        if not self.variant_folder or not os.path.exists(self.variant_folder):
            self.variant_folder = os.path.join(self.project_folder, "Variante 1")
        
        self.emit_project_and_variant_folder()

    def set_variant_folder(self, variant_name):
        """
        Set the current variant folder based on the project folder and variant name.
        """
        if self.project_folder:
            self.variant_folder = os.path.join(self.project_folder, variant_name)
            self.project_folder_changed.emit(self.variant_folder)
            self.config_manager.set_last_project(self.project_folder)

    def get_variant_folder(self):
        """
        Return the current variant folder.
        """
        return self.variant_folder if self.variant_folder else self.project_folder

    def load_last_project(self):
        """
        Load the last opened project folder.
        """
        last_project = self.config_manager.get_last_project()
        if last_project and os.path.exists(last_project):
            self.set_project_folder(last_project)
        else:
            self.emit_project_and_variant_folder()
        
class HeatSystemPresenter:
    """
    Acts as a middleman between the Model (CentralDataManager) and the View (HeatSystemDesignGUI).
    """

    def __init__(self, view, folder_manager, data_manager, config_manager):
        """
        Initialize the HeatSystemPresenter.
        
        Args:
            view: The view instance (HeatSystemDesignGUI).
            model: The model instance (CentralDataManager).
        """
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Connect the model signals directly to the view updates
        self.folder_manager.project_folder_changed.connect(self.view.update_project_folder_label)

    def create_new_project(self, folder_path, project_name):
        """
        Create a new project with the updated folder structure.
        
        Args:
            folder_path (str): The folder path to create the project in.
            project_name (str): The name of the new project.
        """
        if folder_path and project_name:
            try:
                full_path = os.path.join(folder_path, project_name)
                os.makedirs(full_path)
                
                # Create subfolders based on the new structure
                subdirs = {
                    "Eingangsdaten allgemein": [],
                    "Definition Quartier IST": [],
                    "Variante 1": [
                        "Ergebnisse",
                        "Gebäudedaten",
                        "Lastgang",
                        "Wärmenetz"
                    ]
                }
                
                # Create the main folders and their respective subfolders
                for main_folder, subfolders in subdirs.items():
                    main_folder_path = os.path.join(full_path, main_folder)
                    os.makedirs(main_folder_path)
                    for subfolder in subfolders:
                        os.makedirs(os.path.join(main_folder_path, subfolder))

                # Set the project folder to the newly created project
                self.folder_manager.set_project_folder(full_path)

                # Now open the newly created "Variante 1"
                variant_folder = os.path.join(full_path, "Variante 1")
                if os.path.exists(variant_folder):
                    self.folder_manager.set_variant_folder("Variante 1")
                else:
                    self.view.show_error_message("Fehler: Variante 1 konnte nicht gefunden werden.")
                
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

    def create_project_copy(self):
        """
        Create a copy of the current project and allow the user to input a new project name.
        """
        base_dir = os.path.dirname(self.folder_manager.project_folder)
        current_project_name = os.path.basename(self.folder_manager.project_folder)

        # Zeige ein Eingabefenster, um den neuen Projektnamen zu erhalten
        new_project_name, ok = QInputDialog.getText(self.view, 'Projektkopie erstellen', 'Geben Sie einen neuen Namen für das Projekt ein:')

        if ok and new_project_name:
            new_project_path = os.path.join(base_dir, new_project_name)
            
            if not os.path.exists(new_project_path):
                try:
                    # Kopiere das gesamte Projektverzeichnis
                    shutil.copytree(self.folder_manager.project_folder, new_project_path)

                    # Setze das kopierte Projekt als neues Projektverzeichnis
                    self.folder_manager.set_project_folder(new_project_path)
                    
                    # Suche nach der ersten Variante im kopierten Projekt
                    variants = [folder for folder in os.listdir(new_project_path) if "Variante" in folder]
                    
                    if variants:
                        # Setze die erste Variante als aktive Variante
                        self.folder_manager.set_variant_folder(variants[0])
                    else:
                        # Falls keine Variante existiert, setze den Standard-Variantenordner
                        default_variant_path = os.path.join(new_project_path, "Variante 1")
                        if os.path.exists(default_variant_path):
                            self.folder_manager.set_variant_folder("Variante 1")
                        else:
                            # Setze den Projektordner ohne Variante
                            self.folder_manager.set_project_folder(new_project_path)

                    return True
                except Exception as e:
                    self.view.show_error_message(f"Ein Fehler ist aufgetreten: {str(e)}")
                    return False
            else:
                self.view.show_error_message(f"Ein Projekt mit dem Namen '{new_project_name}' existiert bereits.")
                return False
        else:
            self.view.show_error_message("Projektkopie wurde abgebrochen.")
            return False
        
    def create_project_variant(self):
        """
        Creates a new variant automatically if no name is provided, based on the existing variants.
        """
        base_dir = self.folder_manager.project_folder
        variant_num = 1

        while True:
            new_variant_name = f"Variante {variant_num}"
            new_variant_path = os.path.join(base_dir, new_variant_name)
            if not os.path.exists(new_variant_path):
                break
            variant_num += 1

        try:
            os.makedirs(os.path.join(new_variant_path, "Ergebnisse"))
            os.makedirs(os.path.join(new_variant_path, "Gebäudedaten"))
            os.makedirs(os.path.join(new_variant_path, "Lastgang"))
            os.makedirs(os.path.join(new_variant_path, "Wärmenetz"))
            self.folder_manager.set_variant_folder(new_variant_name)
            return True
        except Exception as e:
            self.view.show_error_message(f"Fehler beim Erstellen der Variante: {e}")
            return False
        
    def create_project_variant_copy(self):
        """
        Create a copy of the current variant.
        """
        current_variant = os.path.basename(self.folder_manager.get_variant_folder())
        base_dir = os.path.dirname(self.folder_manager.get_variant_folder())
        variant_num = 1

        while True:
            new_variant_name = f"{current_variant}_Kopie{variant_num}"
            new_variant_path = os.path.join(base_dir, new_variant_name)
            if not os.path.exists(new_variant_path):
                break
            variant_num += 1

        try:
            shutil.copytree(self.folder_manager.get_variant_folder(), new_variant_path)
            self.folder_manager.set_variant_folder(new_variant_name)
            return True
        except Exception as e:
            self.view.show_error_message(f"Fehler beim Kopieren der Variante: {e}")
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
        self.folderLabel = None  # Initialize the folderLabel to None
        self.hidden_tabs = {}  # Speichert versteckte Tabs
        self.tab_order = []  # Speichert die Reihenfolge der Tabs

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

        self.initTabs()

        # Initialize the folderLabel
        self.folderLabel = QLabel("Kein Projektordner ausgewählt")
        self.layout1.addWidget(self.folderLabel)

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

         # Always add the recent projects menu
        recentMenu = fileMenu.addMenu('Zuletzt geöffnet')
        recent_projects = self.presenter.folder_manager.config_manager.get_recent_projects()
        if recent_projects:
            for project in recent_projects:
                action = QAction(project, self)
                action.triggered.connect(lambda checked, p=project: self.on_open_existing_project(p))
                recentMenu.addAction(action)
        else:
            no_recent_action = QAction('Keine kürzlich geöffneten Projekte', self)
            no_recent_action.setEnabled(False)
            recentMenu.addAction(no_recent_action)

        createNewProjectAction = QAction('Neues Projekt erstellen', self)
        fileMenu.addAction(createNewProjectAction)

        chooseProjectAction = QAction('Projekt öffnen', self)
        fileMenu.addAction(chooseProjectAction)

        createCopyAction = QAction('Projektkopie erstellen', self)
        fileMenu.addAction(createCopyAction)

        # Neue Aktion "Variante öffnen" hinzufügen
        openVariantAction = QAction('Variante öffnen', self)
        fileMenu.addAction(openVariantAction)

        createVariantAction = QAction('Variante erstellen', self)
        fileMenu.addAction(createVariantAction)

        createVariantCopyAction = QAction('Variantenkopie erstellen', self)
        fileMenu.addAction(createVariantCopyAction)

        importResultsAction = QAction('Projektstand / -ergebnisse Laden', self)
        fileMenu.addAction(importResultsAction)

        pdfExportAction = QAction('Ergebnis-PDF exportieren', self)
        fileMenu.addAction(pdfExportAction)

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

        # Neuer Menüpunkt für Tabs
        self.tabsMenu = self.menubar.addMenu('Tabs')
        self.menu_actions = {}  # Speichert die Aktionen für die Tabs

        self.layout1.addWidget(self.menubar)

        createNewProjectAction.triggered.connect(self.on_create_new_project)
        chooseProjectAction.triggered.connect(self.on_open_existing_project)
        createCopyAction.triggered.connect(self.on_create_project_copy)
        openVariantAction.triggered.connect(self.on_open_variant)
        createVariantAction.triggered.connect(self.on_create_project_variant)
        createVariantCopyAction.triggered.connect(self.on_create_project_variant_copy)
        importResultsAction.triggered.connect(self.on_importResultsAction)
        pdfExportAction.triggered.connect(self.on_pdf_export)
        chooseTemperatureDataAction.triggered.connect(self.openTemperatureDataSelection)
        createCOPDataAction.triggered.connect(self.openCOPDataSelection)
        lightThemeAction.triggered.connect(lambda: self.applyTheme('light_theme_style_path'))
        darkThemeAction.triggered.connect(lambda: self.applyTheme('dark_theme_style_path'))

    def initTabs(self):
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self.hide_tab)

        self.layout1.addWidget(self.tabWidget)

        # Initialize tabs
        self.projectTab = ProjectTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager)
        self.buildingTab = BuildingTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager)
        self.visTab2 = VisualizationTabLeaflet(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager)
        self.calcTab = CalculationTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager, self)
        self.mixDesignTab = MixDesignTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager, self)
        self.comparisonTab = ComparisonTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager)
        self.lod2Tab = LOD2Tab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager)
        self.renovationTab = RenovationTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager)
        self.individualTab = IndividualTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager, self)
        self.pvTab = PVTab(self.presenter.folder_manager, self.presenter.data_manager, self.presenter.config_manager)

         # Hinzufügen der Tabs zum Widget und Menü
        self.add_tab_to_menu(self.projectTab, "Projektdefinition")
        self.add_tab_to_menu(self.buildingTab, "Wärmebedarf Gebäude")
        self.add_tab_to_menu(self.visTab2, "Kartenansicht Wärmenetzgenerierung")
        self.add_tab_to_menu(self.calcTab, "Wärmenetzberechnung")
        self.add_tab_to_menu(self.mixDesignTab, "Erzeugerauslegung und Wirtschaftlichkeitsrechnung")
        self.add_tab_to_menu(self.comparisonTab, "Variantenvergleich")
        self.add_tab_to_menu(self.lod2Tab, "Verarbeitung LOD2-Daten")
        self.add_tab_to_menu(self.renovationTab, "Gebäudesanierung")
        self.add_tab_to_menu(self.individualTab, "Einzelversorgungslösung")
        self.add_tab_to_menu(self.pvTab, "Photovoltaik")

        self.default_visible_tabs = ["Projektdefinition", "Wärmebedarf Gebäude", "Kartenansicht Wärmenetzgenerierung", "Wärmenetzberechnung", "Erzeugerauslegung und Wirtschaftlichkeitsrechnung", "Variantenvergleich"]

        # Tabs ausblenden, die nicht standardmäßig sichtbar sind
        for tab_name in self.tab_order:
            if tab_name not in self.default_visible_tabs:
                self.toggle_tab_visibility(tab_name)

    def initLogo(self):
        """
        Initialize the logo in the GUI. Doesn't work with currently.
        """
        
        """logoLabel = QLabel(self)
        pixmap = QPixmap('styles\\logo.JPG')
        logoLabel.setPixmap(pixmap)
        logoLabel.setGeometry(10, 10, 100, 100)
        logoLabel.show()"""	

        """# Set the window icon, if available
        icon = QIcon("styles\\logo.JPG")
        if icon.isNull():
            print("Icon could not be loaded.")
        self.setWindowIcon(icon)"""

        self.setWindowIcon(QIcon('styles\\logo.png'))

    def update_project_folder_label(self, base_path):
        """
        Update the project folder label in the UI.
        
        Args:
            path (str): The current project folder path.
        """
        self.base_path = base_path

        if base_path:
            self.folderLabel.setText(f"Ausgewählter Projektordner: {base_path}")
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

        folder_path = QFileDialog.getExistingDirectory(self, "Speicherort für neues Projekt wählen", os.path.dirname(os.path.dirname(self.base_path)))
        
        if folder_path:
            projectName, ok = QInputDialog.getText(self, 'Neues Projekt', 'Projektnamen eingeben:')
            if ok and projectName:
                success = self.presenter.create_new_project(folder_path, projectName)
                if success:
                    QMessageBox.information(self, "Projekt erstellt", f"Projekt '{projectName}' wurde erfolgreich erstellt.")

    def on_open_existing_project(self, folder_path=None):
        """
        Handle opening an existing project and let the user choose from the available variants.
        """
        # folder_path is None if the user clicks on the menu item open existing project, if recent project is clicked, folder_path is the path of the recent project
        if not folder_path:
            folder_path = QFileDialog.getExistingDirectory(self, "Projektordner auswählen", os.path.dirname(os.path.dirname(self.base_path)))

        try:
            if folder_path and os.path.exists(folder_path):
                self.presenter.open_existing_project(folder_path)
                
                # Suche nach allen Varianten, falls es eine gibt
                available_variants = self.get_available_variants(folder_path)
                if available_variants:
                    variant_name, ok = QInputDialog.getItem(self, 'Variante auswählen', 'Wähle eine Variante aus:', available_variants, 0, False)
                    if ok and variant_name:
                        self.presenter.folder_manager.set_variant_folder(variant_name)
                else:
                    self.show_error_message("Keine verfügbaren Varianten gefunden.")
            else:
                raise FileNotFoundError(f"Projektpfad '{folder_path}' nicht gefunden.")
        except FileNotFoundError as e:
            self.show_error_message(str(e))

    def get_available_variants(self, project_path):
        """
        Get a list of available variant folders in the project path.
        
        Args:
            project_path (str): The path to the project.
            
        Returns:
            list: A list of available variant names or an empty list if the path is invalid.
        """
        variants = []
        try:
            for folder_name in os.listdir(project_path):
                full_path = os.path.join(project_path, folder_name)
                # Überprüfen, ob es sich um ein Verzeichnis handelt und ob es "Variante" enthält
                if os.path.isdir(full_path) and folder_name.startswith("Variante"):
                    variants.append(folder_name)
        except FileNotFoundError:
            self.show_error_message(f"Der Projektpfad '{project_path}' konnte nicht gefunden werden.")
        return variants

    def on_create_project_copy(self):
        """
        Handle creating a project variant.
        """
        success = self.presenter.create_project_copy()
        if success:
            QMessageBox.information(self, "Info", "Projektkopie wurde erfolgreich erstellt.")
    
    def on_open_variant(self):
        """
        Handle opening a specific variant from the current project.
        """
        project_folder = self.folder_manager.project_folder  # Aktueller Projektordner
        if not project_folder:
            self.show_error_message("Kein Projektordner ausgewählt.")
            return

        # Suche nach allen Varianten im Projektordner
        available_variants = self.get_available_variants(project_folder)

        if available_variants:
            # Zeige die verfügbaren Varianten zur Auswahl an
            variant_name, ok = QInputDialog.getItem(self, 'Variante öffnen', 'Wähle eine Variante aus:', available_variants, 0, False)
            if ok and variant_name:
                self.presenter.folder_manager.set_variant_folder(variant_name)
        else:
            self.show_error_message("Keine Varianten im Projekt gefunden.")

    def on_create_project_variant(self):
        """
        Handle creating a project variant.
        """
        success = self.presenter.create_project_variant()
        if success:
            QMessageBox.information(self, "Info", "Projektvariante wurde erfolgreich erstellt.")

    def on_create_project_variant_copy(self):
        """
        Handle creating a project variant copy.
        """
        success = self.presenter.create_project_variant()
        if success:
            QMessageBox.information(self, "Info", "Projektvariantenkopie wurde erfolgreich erstellt.")

    def on_importResultsAction(self):
        """
        Handle the import of project results.
        """

        """
        building tab: load building csv and building load profiles json
        calculation tab: load net json, pickle and csv and load profile csv
        mix design tab: load mix design results json
        
        """
        self.buildingTab.presenter.load_csv(os.path.join(self.base_path, self.presenter.config_manager.get_relative_path("current_building_data_path")))
        self.buildingTab.presenter.load_json(os.path.join(self.base_path, self.presenter.config_manager.get_relative_path("building_load_profile_path")))
        self.calcTab.loadNet()
        self.calcTab.load_net_results()
        self.mixDesignTab.load_results_JSON()

    def on_pdf_export(self):
        """
        Handle the PDF export action.
        """
        filepath = os.path.join(self.base_path, self.presenter.config_manager.get_relative_path("results_PDF_path"))
        filename, _ = QFileDialog.getSaveFileName(self, 'PDF speichern als...', filepath, filter='PDF Files (*.pdf)')
        if filename:
            try:
                create_pdf(self, filename)
                QMessageBox.information(self, "PDF erfolgreich erstellt.", f"Die Ergebnisse wurden erfolgreich in {filename} gespeichert.")
            except Exception as e:
                error_message = traceback.format_exc()
                QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern als PDF:\n{error_message}\n\n{str(e)}")

    def applyTheme(self, theme_path):
        qss_path = self.presenter.config_manager.get_resource_path(theme_path)
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

    def add_tab_to_menu(self, tab_widget, tab_name):
        """
        Fügt einen Tab zum Tab-Widget und die entsprechende Aktion zum Menü hinzu.
        """
        # Tab zur Reihenfolge hinzufügen
        if tab_name not in self.tab_order:
            self.tab_order.append(tab_name)

        # Tab zum Tab-Widget hinzufügen
        self.tabWidget.addTab(tab_widget, tab_name)

        # Menüeintrag erstellen
        action = QAction(tab_name, self)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(lambda checked: self.toggle_tab_visibility(tab_name))
        self.tabsMenu.addAction(action)

        # Aktion im Dictionary speichern
        self.menu_actions[tab_name] = action

    def toggle_tab_visibility(self, tab_name):
        """
        Entfernt oder fügt einen Tab hinzu, abhängig von seiner aktuellen Sichtbarkeit.
        """
        if tab_name in self.hidden_tabs:
            # Tab wiederherstellen
            restored_tab, _ = self.hidden_tabs.pop(tab_name)

            # Stelle die ursprüngliche Reihenfolge sicher
            for i, name in enumerate(self.tab_order):
                if name == tab_name:
                    self.tabWidget.insertTab(i, restored_tab, tab_name)
                    self.tabWidget.setCurrentIndex(i)
                    break

            self.menu_actions[tab_name].setChecked(True)
        else:
            # Tab entfernen und speichern
            for index in range(self.tabWidget.count()):
                if self.tabWidget.tabText(index) == tab_name:
                    tab = self.tabWidget.widget(index)
                    self.hidden_tabs[tab_name] = (tab, index)
                    self.tabWidget.removeTab(index)
                    break
            self.menu_actions[tab_name].setChecked(False)

    def hide_tab(self, tab_index):
        """
        Versteckt einen Tab, indem die Sichtbarkeitslogik getriggert wird.
        """
        tab_name = self.tabWidget.tabText(tab_index)
        self.toggle_tab_visibility(tab_name)

def get_stylesheet_based_on_time():
    """
    Return the stylesheet path based on the current system time.
    """
    current_hour = time.localtime().tm_hour
    if 6 <= current_hour < 18:  # Wenn es zwischen 6:00 und 18:00 Uhr ist
        return "light_theme_style_path"  # Pfad zum hellen Stylesheet
    else:
        return "dark_theme_style_path"   # Pfad zum dunklen Stylesheet

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Initialize the managers
    config_manager = ProjectConfigManager()
    folder_manager = ProjectFolderManager(config_manager)
    data_manager = DataManager()

    # Initialize the GUI
    view = HeatSystemDesignGUI(folder_manager, data_manager)

    # Initialize the presenter and link it to the view
    presenter = HeatSystemPresenter(view, folder_manager, data_manager, config_manager)
    view.set_presenter(presenter)
    theme_path = get_stylesheet_based_on_time()
    view.applyTheme(theme_path)

    presenter.view.updateTemperatureData()
    presenter.view.updateHeatPumpData()

    # Setup and show the UI
    QTimer.singleShot(0, lambda: view.showMaximized())
    QTimer.singleShot(0, lambda: view.update_project_folder_label(folder_manager.variant_folder))  # Verschiebe diesen Aufruf hierhin

    view.show()
    sys.exit(app.exec_())

