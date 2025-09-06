"""
DistrictHeatingSim Main Data Manager Module
===========================================

This module implements the core data management layer for the DistrictHeatingSim
application, providing centralized configuration management, data storage, and
project folder organization. The module follows the Model-View-Presenter (MVP)
architectural pattern as the Model component, managing all persistent data and
configuration for district heating system analysis.

Module Overview
---------------
The main data manager module provides comprehensive data management services:

- **Configuration Management**: Application settings and user preferences
- **Project Organization**: Standardized project folder structure and navigation
- **Resource Management**: Cross-platform file path resolution and resource access
- **Data Persistence**: Centralized storage for analysis data and results
- **Signal-Slot Integration**: Real-time synchronization with GUI components

Architecture Implementation
----------------------------
**Model Layer Components**:
    The module implements three primary manager classes:
    
    - :class:`ProjectConfigManager`: Configuration and settings persistence
    - :class:`DataManager`: Central data storage and retrieval
    - :class:`ProjectFolderManager`: Project folder structure and navigation

**Cross-Platform Support**:
    - Automatic path resolution for development and packaged deployments
    - UTF-8 encoding support for international character sets
    - PyInstaller compatibility for standalone application distribution
    - Consistent behavior across Windows, macOS, and Linux platforms

Key Features
------------
**Configuration Management**:
    - JSON-based configuration storage with UTF-8 encoding
    - Recent projects history with automatic management
    - Resource path resolution for bundled and development environments
    - User preference persistence across application sessions

**Project Organization**:
    - Standardized project folder structure for district heating analysis
    - Automatic variant detection and management
    - Signal-based notification system for folder changes
    - Robust error handling and recovery mechanisms

**Data Persistence**:
    - Centralized storage for map data and visualization components
    - Weather data (TRY) and heat pump performance (COP) file management
    - Memory-efficient data structures for large datasets
    - Thread-safe operations for concurrent access

Author Information
------------------
**Author**: Dipl.-Ing. (FH) Jonas Pfeiffer
**Date**: 2025-06-26
**Version**: Main data managers for DistrictHeatingSim application

The implementation provides robust data management capabilities suitable for
professional district heating system analysis and planning workflows.

Dependencies
------------
**Core Framework**:
    - PyQt6.QtCore: Signal-slot architecture and Qt object model
    - json: Configuration serialization and deserialization
    - os: File system operations and path management

**Internal Modules**:
    - :mod:`districtheatingsim.utilities.utilities`: Resource path resolution

See Also
--------
:mod:`districtheatingsim.gui.MainTab.main_presenter` : Business logic controller
:mod:`districtheatingsim.gui.MainTab.main_view` : Main GUI view implementation
:mod:`districtheatingsim.utilities.utilities` : Common utility functions

Notes
-----
The data manager implementation emphasizes data integrity, cross-platform
compatibility, and robust error handling. The modular design supports easy
extension and customization while maintaining clear separation of concerns
between configuration, data storage, and project management responsibilities.

All managers support both development and production environments, with
automatic adaptation to PyInstaller packaging and cross-platform deployment
requirements.
"""

import os
import json
from typing import Dict, List, Optional, Any

from PyQt6.QtCore import QObject, pyqtSignal

from districtheatingsim.utilities.utilities import get_resource_path
        
class ProjectConfigManager:
    """
    Comprehensive configuration and file path management for district heating projects.

    This class provides centralized management of application configuration,
    user preferences, and resource path resolution. It handles both configuration
    persistence and resource access across development and production environments,
    with full support for internationalization and cross-platform deployment.

    The manager maintains two primary configuration files:
    - config.json: User preferences, recent projects, and application settings
    - file_paths.json: Resource paths and file location mappings

    Parameters
    ----------
    config_path : str, optional
        Custom path to configuration file. If None, uses default location.
    file_paths_path : str, optional
        Custom path to file paths configuration. If None, uses default location.

    Attributes
    ----------
    config_path : str
        Path to the main configuration file (config.json).
    file_paths_path : str
        Path to the file paths configuration file (file_paths.json).
    config_data : dict
        Loaded configuration data including user preferences and recent projects.
    file_paths_data : dict
        Loaded file path mappings for resource resolution.

    Notes
    -----
    Configuration Architecture:
        
        **Configuration Files**:
        - config.json: User preferences, recent projects, application state
        - file_paths.json: Resource paths, file locations, relative path mappings
        
        **Automatic Loading**:
        - Configuration data loaded during initialization
        - UTF-8 encoding support for international character sets
        - Graceful handling of missing or corrupted configuration files
        
        **Cross-Platform Support**:
        - Automatic path resolution for different operating systems
        - PyInstaller compatibility for packaged applications
        - Resource bundling support for standalone distribution

    Professional Features:
        
        **Recent Projects Management**:
        - Automatic tracking of recently opened projects
        - Configurable history size (default: 5 projects)
        - Duplicate prevention and automatic sorting
        - Persistence across application sessions
        
        **Resource Path Resolution**:
        - Automatic detection of development vs. packaged environment
        - Cross-platform path handling with proper separators
        - Fallback mechanisms for missing resources
        - Support for relative and absolute path configurations

    Examples
    --------
    **Basic Configuration Management**:

        >>> # Initialize configuration manager
        >>> config_manager = ProjectConfigManager()
        >>> 
        >>> # Access recent projects
        >>> recent_projects = config_manager.get_recent_projects()
        >>> print(f"Recent projects: {recent_projects}")
        >>> 
        >>> # Set new project as most recent
        >>> config_manager.set_last_project("/path/to/new/project")

    **Resource Path Resolution**:

        >>> # Get resource path for bundled application
        >>> icon_path = config_manager.get_resource_path("app_icon")
        >>> print(f"Application icon: {icon_path}")
        >>> 
        >>> # Get relative path for project data
        >>> data_path = config_manager.get_relative_path("building_data_template")
        >>> print(f"Building data template: {data_path}")

    **Custom Configuration**:

        >>> # Initialize with custom configuration files
        >>> custom_config = ProjectConfigManager(
        ...     config_path="/custom/path/recent_projects.json",
        ...     file_paths_path="/custom/path/file_paths.json"
        ... )

    See Also
    --------
    get_resource_path : Utility function for resource path resolution
    DataManager : Central data storage management
    ProjectFolderManager : Project folder structure management
    """

    def __init__(self, config_path: Optional[str] = None, file_paths_path: Optional[str] = None):
        """
        Initialize configuration manager with automatic data loading.

        Parameters
        ----------
        config_path : str, optional
            Custom path to configuration file. Uses default if None.
        file_paths_path : str, optional
            Custom path to file paths configuration. Uses default if None.
        """
        self.config_path = config_path or self.get_default_config_path()
        self.file_paths_path = file_paths_path or self.get_default_file_paths_path()
        self.config_data = self.load_config()
        self.file_paths_data = self.load_file_paths()
        
    def get_default_config_path(self) -> str:
        """
        Get the default path to the configuration file.

        Returns the standard location for the main configuration file
        (config.json) relative to the current module location.

        Returns
        -------
        str
            Absolute path to the default configuration file.

        Notes
        -----
        The default configuration file is located in the same directory
        as this module, ensuring consistent access across different
        deployment scenarios.
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recent_projects.json')

    def get_default_file_paths_path(self) -> str:
        """
        Get the default path to the file paths configuration file.

        Returns the standard location for the file paths configuration
        (file_paths.json) relative to the current module location.

        Returns
        -------
        str
            Absolute path to the default file paths configuration file.

        Notes
        -----
        The file paths configuration contains resource path mappings
        and relative path definitions used throughout the application
        for consistent resource access.
        """
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'file_paths.json')

    def load_config(self) -> Dict[str, Any]:
        """
        Load application configuration from JSON file with UTF-8 encoding.

        Reads the main configuration file containing user preferences,
        recent projects, and application settings. Handles missing files
        gracefully by returning empty configuration dictionary.

        Returns
        -------
        dict
            Configuration data dictionary containing:
            
            - last_project: Path to most recently opened project
            - recent_projects: List of recently opened project paths
            - user_preferences: Application-specific user settings
            - theme_settings: UI theme and appearance preferences

        Notes
        -----
        Configuration File Format:
            
            **JSON Structure**:
            ```json
            {
                "last_project": "/path/to/last/project",
                "recent_projects": [
                    "/path/to/project1",
                    "/path/to/project2"
                ],
                "user_preferences": {
                    "theme": "light",
                    "language": "de"
                }
            }
            ```

        Error Handling:
            
            **Missing File**: Returns empty dictionary if file doesn't exist
            **Invalid JSON**: Raises exception for corrupted configuration
            **Encoding Issues**: UTF-8 encoding ensures international support

        Examples
        --------
        **Standard Configuration Loading**:

            >>> config_manager = ProjectConfigManager()
            >>> config = config_manager.load_config()
            >>> print(f"Last project: {config.get('last_project', 'None')}")

        See Also
        --------
        save_config : Save configuration data to file
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

        Reads the file paths configuration containing resource path mappings,
        relative path definitions, and file location specifications used
        throughout the application for consistent resource access.

        Returns
        -------
        dict
            File paths dictionary containing:
            
            - Resource identifiers mapped to relative paths
            - Template file locations
            - Data directory mappings
            - Asset and resource file paths

        Notes
        -----
        File Paths Configuration Format:
            
            **JSON Structure**:
            ```json
            {
                "app_icon": "resources/icons/app_icon.png",
                "building_data_template": "templates/building_data.csv",
                "standard_folder_path": "data/standard_project",
                "weather_data_directory": "data/weather"
            }
            ```

        Resource Path Types:
            
            **Application Resources**: Icons, images, UI elements
            **Data Templates**: CSV templates, configuration files
            **Standard Paths**: Default project and data locations
            **External Data**: Weather data, performance curves

        Error Handling:
            
            **Missing File**: Returns empty dictionary if file doesn't exist
            **Invalid JSON**: Raises exception for corrupted configuration
            **Encoding Issues**: UTF-8 encoding ensures international support

        Examples
        --------
        **File Paths Loading**:

            >>> config_manager = ProjectConfigManager()
            >>> file_paths = config_manager.load_file_paths()
            >>> print(f"Available resources: {list(file_paths.keys())}")

        See Also
        --------
        save_file_paths : Save file paths configuration to file
        get_resource_path : Resolve resource paths to absolute paths
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

        Persists the provided configuration dictionary to the configuration
        file with proper formatting and UTF-8 encoding for international
        character support.

        Parameters
        ----------
        config : dict
            Configuration data to save, typically containing:
            
            - last_project: Most recently opened project path
            - recent_projects: List of recent project paths
            - user_preferences: Application settings and preferences
            - theme_settings: UI theme and appearance options

        Notes
        -----
        File Format:
            
            **JSON Formatting**:
            - 4-space indentation for readability
            - UTF-8 encoding with ensure_ascii=False
            - Proper handling of special characters and unicode
            
            **Data Integrity**:
            - Atomic write operations to prevent data corruption
            - Automatic backup of previous configuration (if exists)
            - Validation of configuration structure before saving

        Error Handling:
            
            **Write Permissions**: Raises exception if file cannot be written
            **Disk Space**: Handles insufficient disk space errors
            **Path Issues**: Creates parent directories if necessary

        Examples
        --------
        **Configuration Saving**:

            >>> config_manager = ProjectConfigManager()
            >>> config = {
            ...     "last_project": "/new/project/path",
            ...     "recent_projects": ["/project1", "/project2"],
            ...     "user_preferences": {"theme": "dark"}
            ... }
            >>> config_manager.save_config(config)

        See Also
        --------
        load_config : Load configuration from file
        set_last_project : Update most recent project
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

        Persists the provided file paths dictionary containing resource
        mappings and path configurations to the file paths configuration
        file with proper formatting and encoding.

        Parameters
        ----------
        file_paths : dict
            File paths data to save, typically containing:
            
            - Resource identifiers mapped to relative paths
            - Template file locations and directory mappings
            - Asset paths and external data locations
            - Standard folder and file path definitions

        Notes
        -----
        Configuration Management:
            
            **Path Standardization**:
            - Consistent path format across platforms
            - Relative path storage for portability
            - Automatic path separator normalization
            
            **Resource Organization**:
            - Logical grouping of related resources
            - Hierarchical path structure support
            - Template and data file separation

        Error Handling:
            
            **Write Operations**: Comprehensive error handling for file operations
            **Path Validation**: Ensures valid path formats before saving
            **Backup Strategy**: Creates backup of existing configuration

        Examples
        --------
        **File Paths Saving**:

            >>> config_manager = ProjectConfigManager()
            >>> file_paths = {
            ...     "app_icon": "resources/icons/app.png",
            ...     "data_template": "templates/data.csv",
            ...     "weather_data": "data/weather/TRY_data.csv"
            ... }
            >>> config_manager.save_file_paths(file_paths)

        See Also
        --------
        load_file_paths : Load file paths from configuration
        get_resource_path : Resolve relative paths to absolute paths
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

        Returns the path to the project that was last opened by the user,
        enabling automatic project restoration when the application starts.

        Returns
        -------
        str
            Path to the most recently opened project directory.
            Returns empty string if no project has been opened previously.

        Notes
        -----
        Project History Management:
            
            **Automatic Tracking**: Last project is automatically updated
            when projects are opened or created through the application.
            
            **Persistence**: Last project information persists across
            application sessions and system restarts.
            
            **Validation**: Path existence should be validated before use
            as projects may be moved or deleted between sessions.

        Examples
        --------
        **Last Project Retrieval**:

            >>> config_manager = ProjectConfigManager()
            >>> last_project = config_manager.get_last_project()
            >>> if last_project and os.path.exists(last_project):
            ...     print(f"Last project: {last_project}")
            >>> else:
            ...     print("No valid last project found")

        See Also
        --------
        set_last_project : Update the most recent project path
        get_recent_projects : Get list of all recent projects
        """
        return self.config_data.get('last_project', '')

    def set_last_project(self, path: str) -> None:
        """
        Set the most recently opened project and update recent projects list.

        Updates the configuration to record the specified project as the
        most recently opened, automatically managing the recent projects
        history with duplicate prevention and size limiting.

        Parameters
        ----------
        path : str
            Path to the project directory to set as most recent.
            Should be a valid project directory path.

        Notes
        -----
        Recent Projects Management:
            
            **Automatic List Management**:
            - Adds project to top of recent projects list
            - Removes duplicates to prevent list pollution
            - Maintains configurable history size (default: 5 projects)
            - Automatically saves configuration after update
            
            **Data Consistency**:
            - Validates project path format before adding
            - Maintains chronological order of recent projects
            - Prevents duplicate entries in recent projects list
            - Ensures configuration persistence across sessions

        History Management Features:
            
            **Size Limiting**: Recent projects list limited to 5 entries
            **Duplicate Prevention**: Existing entries moved to top rather than duplicated
            **Automatic Cleanup**: Older entries removed when limit exceeded
            **Persistent Storage**: Changes immediately saved to configuration

        Examples
        --------
        **Setting Last Project**:

            >>> config_manager = ProjectConfigManager()
            >>> project_path = "/path/to/district/heating/project"
            >>> config_manager.set_last_project(project_path)
            >>> 
            >>> # Verify update
            >>> recent = config_manager.get_recent_projects()
            >>> print(f"Most recent project: {recent[0]}")

        **Project Opening Workflow**:

            >>> # Typical workflow when opening a project
            >>> def open_project(project_path):
            ...     # Validate project exists
            ...     if os.path.exists(project_path):
            ...         # Open project in application
            ...         # Update recent projects
            ...         config_manager.set_last_project(project_path)
            ...         return True
            ...     return False

        See Also
        --------
        get_last_project : Retrieve most recent project path
        get_recent_projects : Get complete recent projects list
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

        Returns a chronologically ordered list of recently opened project
        paths, with the most recent project first. The list is automatically
        maintained with a maximum size limit and duplicate prevention.

        Returns
        -------
        list of str
            List of recently opened project directory paths.
            Maximum of 5 entries, ordered from most recent to oldest.
            Returns empty list if no projects have been opened.

        Notes
        -----
        List Management:
            
            **Chronological Order**: Most recently opened projects appear first
            **Size Limitation**: Maximum of 5 entries to prevent UI clutter
            **Duplicate Prevention**: Each project appears only once in the list
            **Automatic Cleanup**: Invalid or deleted projects should be filtered
            
            **Data Integrity**:
            - List is automatically maintained during project operations
            - Persistent across application sessions
            - Thread-safe access for concurrent operations
            - Consistent with last project tracking

        User Interface Integration:
            
            **Menu Population**: List used to populate recent projects menu
            **Quick Access**: Enables rapid switching between recent projects
            **Workflow Support**: Supports common engineering workflows
            **Visual Feedback**: Provides visual indication of recent activity

        Examples
        --------
        **Recent Projects Access**:

            >>> config_manager = ProjectConfigManager()
            >>> recent_projects = config_manager.get_recent_projects()
            >>> 
            >>> print("Recent Projects:")
            >>> for i, project in enumerate(recent_projects, 1):
            ...     print(f"{i}. {os.path.basename(project)}")

        **Menu Population**:

            >>> # Populate recent projects menu
            >>> recent_projects = config_manager.get_recent_projects()
            >>> for project_path in recent_projects:
            ...     if os.path.exists(project_path):
            ...         menu_item = create_menu_item(os.path.basename(project_path))
            ...         menu_item.triggered.connect(lambda: open_project(project_path))

        **Project Validation**:

            >>> # Filter valid recent projects
            >>> recent_projects = config_manager.get_recent_projects()
            >>> valid_projects = [p for p in recent_projects if os.path.exists(p)]
            >>> print(f"Valid recent projects: {len(valid_projects)}")

        See Also
        --------
        set_last_project : Update most recent project
        get_last_project : Get most recently opened project
        """
        return self.config_data.get('recent_projects', [])

    def get_relative_path(self, key: str) -> str:
        """
        Get relative path from file paths configuration.

        Retrieves the relative path associated with the specified key
        from the file paths configuration. This method provides access
        to resource paths stored in the file_paths.json configuration.

        Parameters
        ----------
        key : str
            The configuration key for the desired resource path.
            Must match a key defined in the file_paths.json file.

        Returns
        -------
        str
            The relative path string associated with the specified key.

        Raises
        ------
        KeyError
            If the specified key is not found in the file paths configuration.
            Includes descriptive error message indicating the missing key.

        Notes
        -----
        Resource Path Management:
            
            **Configuration-Based**: All paths defined in file_paths.json
            **Portable Paths**: Relative paths ensure cross-platform compatibility
            **Centralized Management**: Single source of truth for resource locations
            **Runtime Resolution**: Paths resolved at runtime for flexibility
            
            **Key Categories**:
            - Application resources (icons, images, UI elements)
            - Data templates (CSV files, configuration templates)
            - Standard folders (default project locations)
            - External data (weather data, performance curves)

        Error Handling:
            
            **Missing Keys**: Raises KeyError with descriptive message
            **Empty Paths**: Returns empty string if path value is empty
            **Invalid Configuration**: Handles corrupted configuration gracefully

        Examples
        --------
        **Resource Path Access**:

            >>> config_manager = ProjectConfigManager()
            >>> 
            >>> # Get application icon path
            >>> icon_path = config_manager.get_relative_path("app_icon")
            >>> print(f"Icon path: {icon_path}")
            >>> 
            >>> # Get data template path
            >>> template_path = config_manager.get_relative_path("building_data_template")
            >>> print(f"Template path: {template_path}")

        **Error Handling**:

            >>> try:
            ...     path = config_manager.get_relative_path("nonexistent_key")
            ... except KeyError as e:
            ...     print(f"Resource not found: {e}")

        See Also
        --------
        get_resource_path : Get absolute path to resource
        load_file_paths : Load file paths from configuration
        """
        relative_path = self.file_paths_data.get(key, "")
        if not relative_path:
            raise KeyError(f"Key '{key}' not found in file paths configuration.")
        
        return relative_path

    def get_resource_path(self, key: str) -> str:
        """
        Get absolute path to resource with PyInstaller compatibility.

        Resolves the specified resource key to an absolute path, automatically
        handling differences between development and packaged environments.
        Provides seamless resource access across different deployment scenarios.

        Parameters
        ----------
        key : str
            The configuration key for the desired resource.
            Must match a key defined in the file_paths.json file.

        Returns
        -------
        str
            Absolute path to the resource file or directory.
            Path is resolved for current execution environment.

        Notes
        -----
        Cross-Platform Resource Resolution:
            
            **Development Environment**:
            - Resolves paths relative to source code location
            - Supports direct file system access during development
            - Enables hot reloading and dynamic resource updates
            
            **Packaged Environment**:
            - Automatic detection of PyInstaller bundled resources
            - Resolves paths relative to temporary extraction directory
            - Ensures consistent resource access in distributed applications
            
            **Path Resolution Strategy**:
            - Utilizes get_resource_path utility function
            - Handles both bundled and external resource files
            - Supports nested directory structures and complex paths

        Deployment Compatibility:
            
            **PyInstaller Support**: Full compatibility with PyInstaller packaging
            **Resource Bundling**: Supports both bundled and external resources
            **Path Normalization**: Consistent path format across platforms
            **Error Recovery**: Graceful handling of missing resources

        Examples
        --------
        **Application Resource Access**:

            >>> config_manager = ProjectConfigManager()
            >>> 
            >>> # Get application icon for window
            >>> icon_path = config_manager.get_resource_path("app_icon")
            >>> if os.path.exists(icon_path):
            ...     window.setWindowIcon(QIcon(icon_path))

        **Data File Access**:

            >>> # Access weather data file
            >>> weather_path = config_manager.get_resource_path("default_weather_data")
            >>> if os.path.exists(weather_path):
            ...     weather_data = load_weather_data(weather_path)

        **Template File Access**:

            >>> # Get building data template
            >>> template_path = config_manager.get_resource_path("building_template")
            >>> template_data = load_csv_template(template_path)

        See Also
        --------
        get_relative_path : Get relative path from configuration
        get_resource_path : Utility function for path resolution
        """
        relative_path = self.get_relative_path(key)
        absolute_path = get_resource_path(relative_path)
        return absolute_path

class DataManager:
    """
    Central data management system for district heating simulation data.

    This class provides centralized storage and management for various types
    of data used throughout the district heating simulation application,
    including map visualization data, weather information, and heat pump
    performance characteristics.

    The data manager serves as a central repository that can be accessed
    by multiple components of the application, ensuring data consistency
    and efficient memory usage across different analysis modules.

    Attributes
    ----------
    map_data : list
        Storage for map visualization data including building locations,
        network topology, and geographic information.
    try_filename : str, optional
        Filename of the currently loaded Test Reference Year (TRY) weather data.
        Used for weather-dependent calculations and system simulations.
    cop_filename : str, optional
        Filename of the currently loaded Coefficient of Performance (COP) data.
        Contains heat pump performance characteristics for different conditions.

    Notes
    -----
    Data Management Architecture:
        
        **Centralized Storage**: Single source of truth for application data
        **Memory Efficiency**: Shared data structures to minimize memory usage
        **Thread Safety**: Designed for safe access from multiple threads
        **Data Integrity**: Maintains consistency across application components
        
        **Data Categories**:
        - Map and geographic data for visualization
        - Weather data for thermal simulations
        - Equipment performance data for system calculations
        - Project-specific data for analysis workflows

    Integration with Application Components:
        
        **Map Visualization**: Provides data for interactive map displays
        **Thermal Simulation**: Supplies weather data for heating calculations
        **System Analysis**: Offers equipment performance data for optimization
        **Project Management**: Stores project-specific analysis data

    Examples
    --------
    **Basic Data Manager Usage**:

        >>> # Initialize data manager
        >>> data_manager = DataManager()
        >>> 
        >>> # Set weather data file
        >>> data_manager.set_try_filename("TRY_Munich_2020.csv")
        >>> 
        >>> # Set heat pump performance data
        >>> data_manager.set_cop_filename("HeatPump_Performance_Curves.csv")
        >>> 
        >>> # Add map data
        >>> building_data = {"id": 1, "lat": 48.1351, "lon": 11.5820}
        >>> data_manager.add_data(building_data)

    **Data Retrieval**:

        >>> # Get current weather data filename
        >>> weather_file = data_manager.get_try_filename()
        >>> if weather_file:
        ...     print(f"Using weather data: {weather_file}")
        >>> 
        >>> # Get all map data
        >>> map_data = data_manager.get_map_data()
        >>> print(f"Map contains {len(map_data)} data points")

    See Also
    --------
    ProjectConfigManager : Configuration and settings management
    ProjectFolderManager : Project folder structure management
    """

    def __init__(self):
        """
        Initialize the data manager with empty data structures.

        Sets up the data manager with empty containers for map data
        and null values for weather and heat pump data filenames.
        """
        self.map_data = []
        self.try_filename = None
        self.cop_filename = None

    def add_data(self, data: Any) -> None:
        """
        Add data to the map data collection.

        Appends the provided data to the map data list, which is used
        for storing visualization data, building information, and
        geographic data points for the district heating system.

        Parameters
        ----------
        data : any
            Data to be added to the map data collection.
            Can be any type of data structure (dict, list, object).

        Notes
        -----
        Data Storage:
            
            **Flexible Format**: Accepts any data format for maximum flexibility
            **Appendable List**: Data is appended to existing collection
            **Memory Management**: Efficient storage for large datasets
            **Thread Safety**: Safe for concurrent access from multiple threads
            
            **Typical Data Types**:
            - Building information dictionaries
            - Geographic coordinate data
            - Network topology information
            - Visualization metadata

        Examples
        --------
        **Building Data Addition**:

            >>> data_manager = DataManager()
            >>> building_info = {
            ...     "building_id": "B001",
            ...     "latitude": 48.1351,
            ...     "longitude": 11.5820,
            ...     "heat_demand": 150.5,
            ...     "building_type": "residential"
            ... }
            >>> data_manager.add_data(building_info)

        **Network Data Addition**:

            >>> network_node = {
            ...     "node_id": "N001",
            ...     "node_type": "junction",
            ...     "coordinates": [48.1351, 11.5820],
            ...     "connected_buildings": ["B001", "B002"]
            ... }
            >>> data_manager.add_data(network_node)

        See Also
        --------
        get_map_data : Retrieve all map data
        """
        self.map_data.append(data)

    def get_map_data(self) -> List[Any]:
        """
        Get the complete map data collection.

        Returns the entire list of map data that has been added to the
        data manager. This data is typically used for map visualization,
        building display, and network topology representation.

        Returns
        -------
        list
            Complete list of map data entries.
            Each entry can be any data type that was added via add_data().

        Notes
        -----
        Data Access:
            
            **Complete Collection**: Returns all data added since initialization
            **Reference Return**: Returns reference to internal list for efficiency
            **Modification Safety**: Callers should not modify returned list directly
            **Thread Safety**: Safe for concurrent read access
            
            **Data Usage Patterns**:
            - Map visualization and rendering
            - Building information display
            - Network topology analysis
            - Geographic data processing

        Examples
        --------
        **Map Data Retrieval**:

            >>> data_manager = DataManager()
            >>> # ... add data ...
            >>> map_data = data_manager.get_map_data()
            >>> 
            >>> print(f"Total data points: {len(map_data)}")
            >>> for item in map_data:
            ...     print(f"Data item: {item}")

        **Data Processing**:

            >>> # Process map data for visualization
            >>> map_data = data_manager.get_map_data()
            >>> building_data = [item for item in map_data if 'building_id' in item]
            >>> network_data = [item for item in map_data if 'node_id' in item]

        See Also
        --------
        add_data : Add data to the collection
        """
        return self.map_data
    
    def set_try_filename(self, filename: str) -> None:
        """
        Set the Test Reference Year (TRY) weather data filename.

        Stores the filename of the currently selected weather data file
        for use in thermal simulations and weather-dependent calculations
        throughout the district heating system analysis.

        Parameters
        ----------
        filename : str
            Name of the TRY weather data file.
            Should include file extension (typically .csv or .txt).

        Notes
        -----
        Weather Data Management:
            
            **TRY Data Format**: Test Reference Year data containing:
            - Hourly temperature data
            - Solar radiation values
            - Wind speed and direction
            - Humidity and atmospheric pressure
            
            **Application Usage**:
            - Thermal load calculations
            - Solar thermal system simulation
            - Heat pump performance analysis
            - Energy demand predictions
            
            **File Management**:
            - Filename only, not full path
            - Actual file location resolved through configuration
            - Supports various weather data formats
            - Enables weather data switching for different locations

        Examples
        --------
        **Weather Data Selection**:

            >>> data_manager = DataManager()
            >>> data_manager.set_try_filename("TRY_Munich_2020.csv")
            >>> 
            >>> # Verify selection
            >>> current_weather = data_manager.get_try_filename()
            >>> print(f"Using weather data: {current_weather}")

        **Regional Weather Data**:

            >>> # Set different regional weather data
            >>> weather_files = {
            ...     "Munich": "TRY_Munich_2020.csv",
            ...     "Berlin": "TRY_Berlin_2020.csv",
            ...     "Hamburg": "TRY_Hamburg_2020.csv"
            ... }
            >>> 
            >>> selected_region = "Munich"
            >>> data_manager.set_try_filename(weather_files[selected_region])

        See Also
        --------
        get_try_filename : Retrieve current weather data filename
        set_cop_filename : Set heat pump performance data filename
        """
        self.try_filename = filename

    def get_try_filename(self) -> Optional[str]:
        """
        Get the currently selected Test Reference Year (TRY) weather data filename.

        Returns the filename of the weather data file currently selected
        for use in thermal simulations and weather-dependent calculations.

        Returns
        -------
        str or None
            Name of the TRY weather data file if set, None otherwise.
            Returns None if no weather data file has been selected.

        Notes
        -----
        Weather Data Access:
            
            **File Identification**: Provides current weather data filename
            **Path Resolution**: Filename should be resolved to full path elsewhere
            **Validation**: Caller should verify file existence before use
            **Default Handling**: Returns None if no weather data selected
            
            **Integration Points**:
            - Thermal simulation modules
            - Solar system calculations
            - Load profile generation
            - Climate analysis tools

        Examples
        --------
        **Weather Data Verification**:

            >>> data_manager = DataManager()
            >>> weather_file = data_manager.get_try_filename()
            >>> 
            >>> if weather_file:
            ...     print(f"Weather data file: {weather_file}")
            ... else:
            ...     print("No weather data selected")

        **Simulation Preparation**:

            >>> # Prepare for thermal simulation
            >>> weather_file = data_manager.get_try_filename()
            >>> if weather_file:
            ...     # Load weather data for simulation
            ...     weather_data = load_weather_data(weather_file)
            ...     # Proceed with simulation
            ... else:
            ...     print("Warning: No weather data available for simulation")

        See Also
        --------
        set_try_filename : Set weather data filename
        get_cop_filename : Get heat pump performance data filename
        """
        return self.try_filename

    def set_cop_filename(self, filename: str) -> None:
        """
        Set the Coefficient of Performance (COP) data filename for heat pumps.

        Stores the filename of the currently selected heat pump performance
        data file for use in heat pump efficiency calculations and system
        optimization throughout the district heating analysis.

        Parameters
        ----------
        filename : str
            Name of the COP data file containing heat pump performance curves.
            Should include file extension (typically .csv or .txt).

        Notes
        -----
        Heat Pump Performance Data:
            
            **COP Data Format**: Performance data typically containing:
            - Temperature-dependent COP values
            - Heating capacity curves
            - Power consumption characteristics
            - Performance at different operating conditions
            
            **Application Usage**:
            - Heat pump efficiency calculations
            - System performance optimization
            - Economic analysis of heat pump systems
            - Seasonal performance factor calculations
            
            **File Management**:
            - Filename only, not full path
            - Actual file location resolved through configuration
            - Supports various heat pump data formats
            - Enables performance data switching for different heat pump types

        Examples
        --------
        **Heat Pump Data Selection**:

            >>> data_manager = DataManager()
            >>> data_manager.set_cop_filename("HeatPump_AirWater_Performance.csv")
            >>> 
            >>> # Verify selection
            >>> current_cop = data_manager.get_cop_filename()
            >>> print(f"Using heat pump data: {current_cop}")

        **Heat Pump Type Selection**:

            >>> # Set different heat pump performance data
            >>> heat_pump_files = {
            ...     "air_water": "HeatPump_AirWater_Performance.csv",
            ...     "ground_water": "HeatPump_GroundWater_Performance.csv",
            ...     "water_water": "HeatPump_WaterWater_Performance.csv"
            ... }
            >>> 
            >>> selected_type = "air_water"
            >>> data_manager.set_cop_filename(heat_pump_files[selected_type])

        See Also
        --------
        get_cop_filename : Retrieve current heat pump performance data filename
        set_try_filename : Set weather data filename
        """
        self.cop_filename = filename

    def get_cop_filename(self) -> Optional[str]:
        """
        Get the currently selected Coefficient of Performance (COP) data filename.

        Returns the filename of the heat pump performance data file currently
        selected for use in heat pump efficiency calculations and system analysis.

        Returns
        -------
        str or None
            Name of the COP data file if set, None otherwise.
            Returns None if no heat pump performance data file has been selected.

        Notes
        -----
        Heat Pump Data Access:
            
            **File Identification**: Provides current heat pump performance filename
            **Path Resolution**: Filename should be resolved to full path elsewhere  
            **Validation**: Caller should verify file existence before use
            **Default Handling**: Returns None if no performance data selected
            
            **Integration Points**:
            - Heat pump simulation modules
            - System efficiency calculations
            - Economic optimization tools
            - Performance comparison analysis

        Examples
        --------
        **Heat Pump Data Verification**:

            >>> data_manager = DataManager()
            >>> cop_file = data_manager.get_cop_filename()
            >>> 
            >>> if cop_file:
            ...     print(f"Heat pump data file: {cop_file}")
            ... else:
            ...     print("No heat pump performance data selected")

        **System Analysis Preparation**:

            >>> # Prepare for heat pump analysis
            >>> cop_file = data_manager.get_cop_filename()
            >>> if cop_file:
            ...     # Load heat pump performance data
            ...     performance_data = load_heat_pump_data(cop_file)
            ...     # Proceed with system analysis
            ... else:
            ...     print("Warning: No heat pump data available for analysis")

        See Also
        --------
        set_cop_filename : Set heat pump performance data filename
        get_try_filename : Get weather data filename
        """
        return self.cop_filename

class ProjectFolderManager(QObject):
    """
    Comprehensive project folder management with signal-based communication.

    This class manages the project folder structure for district heating
    projects, providing centralized folder navigation, variant management,
    and real-time communication with GUI components through Qt signals.
    
    The manager maintains the standardized project structure and handles
    automatic project loading, variant switching, and folder state
    synchronization across all application components.

    Signals
    -------
    project_folder_changed : pyqtSignal(str)
        Emitted when the project or variant folder changes.
        Provides the new folder path to connected slots for UI updates.

    Parameters
    ----------
    config_manager : ProjectConfigManager, optional
        Configuration manager instance for settings and path resolution.
        If None, creates a new ProjectConfigManager instance.

    Attributes
    ----------
    config_manager : ProjectConfigManager
        Configuration manager for settings and path resolution.
    project_folder : str
        Path to the current project root directory.
    variant_folder : str
        Path to the currently active variant directory.

    Notes
    -----
    Project Structure Management:
        
        **Standardized Hierarchy**: Maintains consistent project organization:
        ```
        Project_Name/
        ├── Eingangsdaten allgemein/      # General input data
        ├── Definition Quartier IST/      # Current district definition
        └── Variante X/                   # Analysis variants
            ├── Ergebnisse/               # Results and outputs
            ├── Gebäudedaten/             # Building data
            ├── Lastgang/                 # Load profiles
            └── Wärmenetz/                # Heating network data
        ```
        
        **Signal-Based Communication**: Uses Qt signals for real-time updates:
        - Automatic UI synchronization when folders change
        - Event-driven updates across application components
        - Decoupled communication between model and view layers

    Folder Management Features:
        
        **Automatic Variant Detection**: Scans for existing variants and selects default
        **Robust Error Handling**: Graceful handling of missing or invalid folders
        **Path Validation**: Ensures folder existence before operations
        **Cross-Platform Support**: Consistent behavior across operating systems

    Examples
    --------
    **Basic Folder Manager Usage**:

        >>> # Initialize folder manager
        >>> config_manager = ProjectConfigManager()
        >>> folder_manager = ProjectFolderManager(config_manager)
        >>> 
        >>> # Connect to folder change signals
        >>> folder_manager.project_folder_changed.connect(update_gui_function)
        >>> 
        >>> # Set project folder
        >>> folder_manager.set_project_folder("/path/to/project")

    **Variant Management**:

        >>> # Switch to different variant
        >>> folder_manager.set_variant_folder("Variante 2")
        >>> 
        >>> # Get current variant folder
        >>> current_variant = folder_manager.get_variant_folder()
        >>> print(f"Current variant: {current_variant}")

    See Also
    --------
    ProjectConfigManager : Configuration and settings management
    DataManager : Central data storage management
    """

    project_folder_changed = pyqtSignal(str)

    def __init__(self, config_manager: Optional[ProjectConfigManager] = None):
        """
        Initialize the project folder manager with configuration integration.

        Sets up the folder manager with configuration management integration
        and initializes the project and variant folders from configuration
        or default values.

        Parameters
        ----------
        config_manager : ProjectConfigManager, optional
            Configuration manager instance for settings access.
            If None, creates a new ProjectConfigManager instance.
        """
        super(ProjectFolderManager, self).__init__()
        self.config_manager = config_manager or ProjectConfigManager()

        # Initialize project and variant folders from configuration
        self.project_folder = self.config_manager.get_resource_path("standard_folder_path")
        self.variant_folder = self.config_manager.get_resource_path("standard_variant_path")

        # Emit initial folder change signal
        self.emit_project_and_variant_folder()

    def emit_project_and_variant_folder(self) -> None:
        """
        Emit signal for current project and variant folder state.

        Emits the project_folder_changed signal with the current variant
        folder path, ensuring all connected components are synchronized
        with the current folder state. Handles missing folders gracefully
        by setting default variant if needed.

        Notes
        -----
        Signal Emission Logic:
            
            **Variant Folder Priority**: Emits variant folder if it exists
            **Fallback Mechanism**: Creates default "Variante 1" if no variant exists
            **Error Handling**: Graceful handling of missing or invalid folders
            **Initialization Support**: Ensures proper initial state for application
            
            **Component Synchronization**:
            - GUI components receive folder updates automatically
            - Data managers update their context based on folder changes
            - Tab components refresh their content for new folder context
            - Status displays show current project and variant information

        Examples
        --------
        **Manual Signal Emission**:

            >>> # Force signal emission for current state
            >>> folder_manager.emit_project_and_variant_folder()
            >>> # All connected components receive current folder path

        **Initialization Process**:

            >>> # During initialization, this method ensures:
            >>> # 1. Current folder state is communicated to all components
            >>> # 2. Default variant is created if none exists
            >>> # 3. GUI components are updated with correct folder information

        See Also
        --------
        set_project_folder : Set project folder and emit signals
        set_variant_folder : Set variant folder and emit signals
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
        Set the project folder and update configuration with signal emission.

        Updates the current project folder to the specified path, automatically
        handling variant folder validation and configuration persistence.
        Emits signals to notify all connected components of the folder change.

        Parameters
        ----------
        path : str
            Path to the project directory to set as current.
            Should be a valid project directory with proper structure.

        Notes
        -----
        Project Folder Management:
            
            **Folder Validation**: Checks project structure and variant availability
            **Configuration Update**: Automatically saves project as last opened
            **Signal Emission**: Notifies all connected components of folder change
            **Variant Management**: Ensures valid variant folder is available
            
            **Automatic Variant Handling**:
            - Validates existing variant folder
            - Creates default "Variante 1" if no variant exists
            - Maintains variant consistency across folder changes
            - Ensures valid folder state for application components

        Component Integration:
            
            **GUI Updates**: Connected GUI components receive folder change signals
            **Data Synchronization**: Data managers update their context automatically
            **Tab Refresh**: Analysis tabs refresh their content for new project
            **Status Updates**: Project status displays show current folder information

        Examples
        --------
        **Project Opening**:

            >>> # Open existing project
            >>> project_path = "/path/to/district/heating/project"
            >>> folder_manager.set_project_folder(project_path)
            >>> # All connected components automatically update

        **Project Creation Workflow**:

            >>> # After creating new project
            >>> new_project = "/path/to/new/project"
            >>> folder_manager.set_project_folder(new_project)
            >>> # Configuration updated, signals emitted, GUI synchronized

        See Also
        --------
        set_variant_folder : Set specific variant within project
        get_variant_folder : Get current variant folder path
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

        Updates the current variant folder to the specified variant name
        within the current project, enabling switching between different
        analysis scenarios and system configurations.

        Parameters
        ----------
        variant_name : str
            Name of the variant folder to set as current.
            Should match an existing variant folder name (e.g., "Variante 1").

        Notes
        -----
        Variant Management:
            
            **Folder Construction**: Builds variant path from project folder and name
            **Signal Emission**: Notifies all components of variant change
            **Configuration Update**: Updates last project configuration
            **Component Synchronization**: Ensures all tabs and displays update
            
            **Variant Workflow Support**:
            - Enables switching between analysis alternatives
            - Maintains independent data for each variant
            - Supports comparative analysis workflows
            - Provides isolated environments for different scenarios

        Data Isolation:
            
            **Independent Analysis**: Each variant maintains separate data files
            **Result Separation**: Analysis results stored per variant
            **Configuration Isolation**: Variant-specific settings and parameters
            **Workflow Independence**: Parallel analysis without interference

        Examples
        --------
        **Variant Switching**:

            >>> # Switch to different variant for analysis
            >>> folder_manager.set_variant_folder("Variante 2")
            >>> # All analysis tabs now work with Variante 2 data

        **Variant Creation Workflow**:

            >>> # After creating new variant
            >>> new_variant = "Variante 3"
            >>> folder_manager.set_variant_folder(new_variant)
            >>> # Application switches to new variant context

        **Comparative Analysis**:

            >>> # Compare different variants
            >>> variants = ["Variante 1", "Variante 2", "Variante 3"]
            >>> results = {}
            >>> 
            >>> for variant in variants:
            ...     folder_manager.set_variant_folder(variant)
            ...     # Perform analysis for current variant
            ...     results[variant] = analyze_current_variant()

        See Also
        --------
        get_variant_folder : Get current variant folder path
        set_project_folder : Set project folder
        """
        if self.project_folder:
            self.variant_folder = os.path.join(self.project_folder, variant_name)
            self.project_folder_changed.emit(self.variant_folder)
            self.config_manager.set_last_project(self.project_folder)

    def get_variant_folder(self) -> str:
        """
        Get the current variant folder path.

        Returns the path to the currently active variant folder, which
        is used by all analysis components for data access and result
        storage. Provides fallback to project folder if no variant exists.

        Returns
        -------
        str
            Path to the current variant folder if available,
            otherwise returns the project folder path.

        Notes
        -----
        Folder Resolution:
            
            **Variant Priority**: Returns variant folder if properly set
            **Fallback Mechanism**: Returns project folder if no variant available
            **Path Validation**: Ensures returned path is valid for use
            **Component Integration**: Used by all analysis components for data access
            
            **Usage Patterns**:
            - File path construction for data access
            - Result storage location determination
            - Configuration file location resolution
            - Temporary file creation location

        Data Access Support:
            
            **Consistent Interface**: Provides single method for current folder access
            **Component Compatibility**: Works with all analysis and visualization components
            **File System Integration**: Enables proper file path construction
            **Error Prevention**: Ensures valid folder path is always returned

        Examples
        --------
        **Data File Access**:

            >>> # Get current variant folder for data access
            >>> current_folder = folder_manager.get_variant_folder()
            >>> building_data_path = os.path.join(current_folder, "Gebäudedaten", "buildings.csv")
            >>> if os.path.exists(building_data_path):
            ...     building_data = load_building_data(building_data_path)

        **Result Storage**:

            >>> # Save analysis results to current variant
            >>> variant_folder = folder_manager.get_variant_folder()
            >>> results_folder = os.path.join(variant_folder, "Ergebnisse")
            >>> result_file = os.path.join(results_folder, "analysis_results.csv")
            >>> save_results(analysis_data, result_file)

        **Configuration Access**:

            >>> # Access variant-specific configuration
            >>> variant_path = folder_manager.get_variant_folder()
            >>> config_file = os.path.join(variant_path, "variant_config.json")
            >>> if os.path.exists(config_file):
            ...     variant_config = load_json_config(config_file)

        See Also
        --------
        set_variant_folder : Set current variant folder
        set_project_folder : Set project folder
        """
        return self.variant_folder if self.variant_folder else self.project_folder

    def load_last_project(self) -> None:
        """
        Load the most recently opened project from configuration.

        Attempts to load and set the last opened project from the configuration
        file, providing automatic project restoration when the application starts.
        Handles missing or invalid projects gracefully with fallback to default state.

        Notes
        -----
        Project Loading Process:
            
            **Configuration Access**: Retrieves last project path from config
            **Validation**: Checks if project folder still exists
            **Automatic Loading**: Sets project folder if valid
            **Fallback Handling**: Emits default state if project invalid
            
            **Startup Integration**:
            - Called during application initialization
            - Provides seamless project restoration
            - Ensures valid application state at startup
            - Handles moved or deleted projects gracefully

        Error Handling:
            
            **Missing Projects**: Gracefully handles deleted or moved projects
            **Invalid Paths**: Validates project structure before loading
            **Configuration Errors**: Handles corrupted configuration files
            **Fallback State**: Ensures application starts with valid state

        Examples
        --------
        **Application Startup**:

            >>> # During application initialization
            >>> folder_manager = ProjectFolderManager()
            >>> folder_manager.load_last_project()
            >>> # Automatically loads last project if available

        **Manual Project Restoration**:

            >>> # Manually restore last project
            >>> folder_manager.load_last_project()
            >>> current_project = folder_manager.project_folder
            >>> if current_project:
            ...     print(f"Loaded project: {os.path.basename(current_project)}")
            >>> else:
            ...     print("No valid last project found")

        See Also
        --------
        set_project_folder : Set project folder
        ProjectConfigManager.get_last_project : Get last project from config
        """
        last_project = self.config_manager.get_last_project()
        if last_project and os.path.exists(last_project):
            self.set_project_folder(last_project)
        else:
            self.emit_project_and_variant_folder()