"""
Data management layer for DistrictHeatingSim application.

This module implements the Model layer of the MVP pattern, providing three core managers:
- ProjectConfigManager: Configuration and user preferences
- DataManager: Central data storage for analysis results
- ProjectFolderManager: Project folder structure and navigation

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import json
from typing import Dict, List, Optional, Any

from PyQt6.QtCore import QObject, pyqtSignal

from districtheatingsim.utilities.utilities import get_resource_path
        
class ProjectConfigManager:
    """
    Manages application configuration and resource paths.

    Handles JSON-based configuration storage including user preferences,
    recent projects, and resource path resolution for both development
    and PyInstaller builds.

    :param config_path: Path to config.json (optional, uses default if None)
    :type config_path: str
    :param file_paths_path: Path to file_paths.json (optional, uses default if None)
    :type file_paths_path: str
    
    .. note::
        Configuration files are stored with UTF-8 encoding for international
        character support.
    """

    def __init__(self, config_path: Optional[str] = None, file_paths_path: Optional[str] = None):
        """
        Initialize configuration manager with automatic data loading.

        :param config_path: Custom path to configuration file
        :type config_path: str
        :param file_paths_path: Custom path to file paths configuration
        :type file_paths_path: str
        """
        self.config_path = config_path or self.get_default_config_path()
        self.file_paths_path = file_paths_path or self.get_default_file_paths_path()
        self.config_data = self.load_config()
        self.file_paths_data = self.load_file_paths()
        
    def get_default_config_path(self) -> str:
        """
        Get the default path to recent_projects.json.

        :return: Absolute path to the default configuration file
        :rtype: str
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recent_projects.json')

    def get_default_file_paths_path(self) -> str:
        """
        Get the default path to file_paths.json.

        :return: Absolute path to the default file paths configuration file
        :rtype: str
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'file_paths.json')

    def load_config(self) -> Dict[str, Any]:
        """
        Load application configuration from JSON file with UTF-8 encoding.

        :return: Configuration dictionary (empty if file doesn't exist)
        :rtype: dict
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error loading configuration: {e}")
                return {}
        return {}

    def load_file_paths(self) -> Dict[str, str]:
        """
        Load file path mappings from JSON configuration with UTF-8 encoding.

        :return: File paths dictionary mapping resource IDs to relative paths (empty if file doesn't exist)
        :rtype: dict
        """
        if os.path.exists(self.file_paths_path):
            try:
                with open(self.file_paths_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"Error loading file paths: {e}")
                return {}
        return {}

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration data to JSON file with UTF-8 encoding.

        :param config: Configuration data to save
        :type config: dict
        :raises Exception: If file cannot be written
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving configuration: {e}")
            raise

    def save_file_paths(self, file_paths: Dict[str, str]) -> None:
        """
        Save file paths configuration to JSON file with UTF-8 encoding.

        :param file_paths: File paths data to save
        :type file_paths: dict
        :raises Exception: If file cannot be written
        """
        try:
            with open(self.file_paths_path, 'w', encoding='utf-8') as file:
                json.dump(file_paths, file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving file paths: {e}")
            raise

    def get_last_project(self) -> str:
        """
        Retrieve the path of the most recently opened project.

        :return: Path to last opened project (empty string if none)
        :rtype: str
        """
        return self.config_data.get('last_project', '')

    def set_last_project(self, path: str) -> None:
        """
        Set the most recently opened project and update recent projects list.

        Automatically manages recent projects history (max 5 entries) with
        duplicate prevention and configuration persistence.

        :param path: Path to the project directory
        :type path: str
        """
        self.config_data['last_project'] = path
        
        # Initialize recent projects list if not exists
        if 'recent_projects' not in self.config_data:
            self.config_data['recent_projects'] = []
        
        # Add to recent projects with duplicate prevention
        if path not in self.config_data['recent_projects']:
            self.config_data['recent_projects'].insert(0, path)
            # Maintain maximum of 5 recent projects
            self.config_data['recent_projects'] = self.config_data['recent_projects'][:5]
        else:
            # Move existing entry to top
            self.config_data['recent_projects'].remove(path)
            self.config_data['recent_projects'].insert(0, path)
        
        # Persist changes immediately
        self.save_config(self.config_data)

    def get_recent_projects(self) -> List[str]:
        """
        Retrieve the list of recently opened projects.

        :return: List of project paths (max 5 entries, most recent first)
        :rtype: list of str
        """
        return self.config_data.get('recent_projects', [])

    def get_relative_path(self, key: str) -> str:
        """
        Get relative path from file paths configuration.

        :param key: Configuration key for desired resource path
        :type key: str
        :return: Relative path string
        :rtype: str
        :raises KeyError: If key not found in file paths configuration
        """
        relative_path = self.file_paths_data.get(key, "")
        if not relative_path:
            raise KeyError(f"Key '{key}' not found in file paths configuration.")
        
        return relative_path

    def get_resource_path(self, key: str) -> str:
        """
        Get absolute path to resource with PyInstaller compatibility.

        :param key: Configuration key for desired resource
        :type key: str
        :return: Absolute path to resource
        :rtype: str
        """
        relative_path = self.get_relative_path(key)
        absolute_path = get_resource_path(relative_path)
        return absolute_path

class DataManager:
    """
    Central data storage for district heating simulation.

    Manages map visualization data, weather data (TRY) filenames,
    and heat pump performance (COP) filenames for use across
    application components.
    """

    def __init__(self):
        """
        Initialize the data manager with empty data structures.
        """
        self.map_data = []
        self.try_filename = None
        self.cop_filename = None

    def add_data(self, data: Any) -> None:
        """
        Add data to the map data collection.

        :param data: Data to be added to the map data collection
        :type data: any
        """
        self.map_data.append(data)

    def get_map_data(self) -> List[Any]:
        """
        Get the complete map data collection.

        :return: List of all map data entries
        :rtype: list
        """
        return self.map_data
    
    def set_try_filename(self, filename: str) -> None:
        """
        Set the Test Reference Year (TRY) weather data filename.

        :param filename: Name of the TRY weather data file
        :type filename: str
        """
        self.try_filename = filename

    def get_try_filename(self) -> Optional[str]:
        """
        Get the currently selected TRY weather data filename.

        :return: TRY weather data filename or None if not set
        :rtype: str or None
        """
        return self.try_filename

    def set_cop_filename(self, filename: str) -> None:
        """
        Set the Coefficient of Performance (COP) data filename for heat pumps.

        :param filename: Name of the COP data file
        :type filename: str
        """
        self.cop_filename = filename

    def get_cop_filename(self) -> Optional[str]:
        """
        Get the currently selected COP data filename.

        :return: COP data filename or None if not set
        :rtype: str or None
        """
        return self.cop_filename

class ProjectFolderManager(QObject):
    """
    Manages project folder structure and variant navigation.

    Handles project folder hierarchy, variant switching, and emits
    signals when project/variant folders change for UI synchronization.

    :param config_manager: Configuration manager instance (creates new if None)
    :type config_manager: ProjectConfigManager
    
    :signal project_folder_changed: Emitted when project/variant folder changes (str)
    """

    project_folder_changed = pyqtSignal(str)

    def __init__(self, config_manager: Optional[ProjectConfigManager] = None):
        """
        Initialize the project folder manager.

        :param config_manager: Configuration manager instance (creates new if None)
        :type config_manager: ProjectConfigManager
        """
    def __init__(self, config_manager: Optional[ProjectConfigManager] = None):
        super(ProjectFolderManager, self).__init__()
        self.config_manager = config_manager or ProjectConfigManager()

        # Do not set project_folder or variant_folder until a project is selected or loaded
        self.project_folder = None
        self.variant_folder = None

        # Do not emit initial folder change signal; will be emitted after project selection

    def emit_project_and_variant_folder(self) -> None:
        """
        Emit signal for current project and variant folder state.

        Creates default "Variante 1" if no variant folder exists.
        """
        if self.project_folder and self.variant_folder and os.path.exists(self.variant_folder):
            print(f"Initial variant folder set to: {self.variant_folder}")
            self.project_folder_changed.emit(self.variant_folder)
        elif self.project_folder:
            # Create default variant if none exists
            print("No variant folder found, setting default variant")
            self.variant_folder = os.path.join(self.project_folder, "Variante 1")
            self.project_folder_changed.emit(self.variant_folder)

    def set_project_folder(self, path: str) -> None:
        """
        Set the project folder and update configuration.

        Validates variant folder and emits signals to notify connected components.
        Creates default "Variante 1" if no valid variant exists.

        :param path: Path to the project directory
        :type path: str
        """
        self.project_folder = path
        self.config_manager.set_last_project(self.project_folder)

        # Validate and set variant folder
        if not self.variant_folder or not os.path.exists(self.variant_folder):
            self.variant_folder = os.path.join(self.project_folder, "Variante 1")
        
        self.emit_project_and_variant_folder()

    def set_variant_folder(self, variant_name: str) -> None:
        """
        Set the current variant folder and emit change signal.

        :param variant_name: Name of the variant folder (e.g., "Variante 1")
        :type variant_name: str
        """
        if self.project_folder:
            self.variant_folder = os.path.join(self.project_folder, variant_name)
            self.project_folder_changed.emit(self.variant_folder)
            self.config_manager.set_last_project(self.project_folder)

    def get_variant_folder(self) -> str:
        """
        Get the current variant folder path.

        :return: Current variant folder path (or project folder if no variant)
        :rtype: str
        """
        return self.variant_folder if self.variant_folder else self.project_folder

    def load_last_project(self) -> None:
        """
        Load the most recently opened project from configuration.

        Validates project existence before loading. Emits default state if
        project invalid or missing.
        """
        last_project = self.config_manager.get_last_project()
        if last_project and os.path.exists(last_project):
            self.set_project_folder(last_project)
        else:
            self.emit_project_and_variant_folder()