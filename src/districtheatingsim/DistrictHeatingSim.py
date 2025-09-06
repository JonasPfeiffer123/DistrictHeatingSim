"""
DistrictHeatingSim - Main Application Module
================================================

This module serves as the main entry point for the DistrictHeatingSim application,
a comprehensive district heating system simulation and analysis tool. The application
implements the Model-View-Presenter (MVP) architectural pattern to provide a
maintainable and extensible GUI framework for district heating project management.

Module Overview
---------------
The DistrictHeatingSim application provides a complete environment for:

- **Project Management**: Create, open, and manage district heating projects
- **Data Visualization**: Interactive mapping and visualization of heating networks
- **Building Analysis**: Calculate and analyze building heating requirements
- **Network Simulation**: Perform hydraulic and thermal network calculations
- **Energy System Design**: Design and optimize heating system configurations
- **Economic Analysis**: Comprehensive economic evaluation and comparison
- **Results Documentation**: Generate professional reports and documentation

Architecture
------------
The application follows the MVP pattern with clear separation of concerns:

**Model Layer**:
    - :class:`ProjectConfigManager`: Configuration and settings management
    - :class:`DataManager`: Central data storage and management
    - :class:`ProjectFolderManager`: Project file system operations

**View Layer**:
    - :class:`HeatSystemDesignGUI`: Main application window and user interface
    - Tab-based interface for different analysis modules
    - Interactive dialogs and visualization components

**Presenter Layer**:
    - :class:`HeatSystemPresenter`: Business logic and user interaction handling
    - Coordinates between model and view components
    - Manages application state and data flow

Key Features
------------
**Project Management**:
    - Create new district heating projects with standardized folder structure
    - Open existing projects with variant support
    - Manage project versions and create copies
    - Recent projects history and quick access

**Multi-Tab Interface**:
    - **Project Definition**: Basic project setup and configuration
    - **Building Heat Demand**: Building-by-building heat requirement analysis
    - **Network Visualization**: Interactive map-based network design
    - **Network Calculation**: Hydraulic and thermal network simulation
    - **Energy System Design**: Heating technology selection and sizing
    - **Variant Comparison**: Economic and technical comparison of alternatives
    - **LOD2 Processing**: Advanced building geometry processing
    - **Renovation Analysis**: Building renovation scenario evaluation
    - **Individual Solutions**: Decentralized heating system analysis

**Data Management**:
    - Standardized data formats for interoperability
    - Import/export capabilities for external tools

**User Experience**:
    - Intuitive workflow-based interface design
    - Customizable themes (light/dark mode)

Technical Implementation
------------------------
**GUI Framework**:
    The application uses PyQt6 for the graphical user interface, providing:
    
    - Native look and feel across platforms
    - Rich widget set for complex data visualization
    - Signal-slot architecture for event handling
    - Threading support for long-running calculations

**Data Persistence**:
    Project data is stored using multiple formats:
    
    - JSON for configuration and structured data
    - CSV for tabular building and network data
    - Pickle for complex Python objects and results
    - PDF for professional report generation

**Error Handling**:
    Comprehensive error handling includes:
    
    - Global exception handling with error messages

**Cross-Platform Support**:
    The application is designed for cross-platform deployment:
    
    - Windows-specific features (taskbar integration)
    - PyInstaller packaging support
    - Resource path resolution for bundled applications
    - Theme adaptation based on system time

Application Lifecycle
---------------------
**Initialization Sequence**:
    1. **System Setup**: Exception handling, Qt application initialization
    2. **Manager Creation**: Instantiate data and configuration managers
    3. **GUI Construction**: Build main window and tab interfaces
    4. **Presenter Linking**: Connect business logic to view components
    5. **Theme Application**: Apply time-based or user-selected theme
    6. **Project Loading**: Load last project or show default state

Examples
--------
**Basic Application Launch**:

    >>> # Launch the DistrictHeatingSim application
    >>> python DistrictHeatingSim.py
    
    # The application will:
    # 1. Initialize all managers and GUI components
    # 2. Load the last opened project (if available)
    # 3. Apply theme based on current time
    # 4. Display the main window maximized

**Programmatic Usage** (for testing or automation):

    >>> import sys
    >>> from PyQt6.QtWidgets import QApplication
    >>> from districtheatingsim.gui.MainTab.main_data_manager import *
    >>> from districtheatingsim.gui.MainTab.main_presenter import HeatSystemPresenter
    >>> from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI
    >>> 
    >>> # Initialize application
    >>> app = QApplication(sys.argv)
    >>> 
    >>> # Create managers
    >>> config_manager = ProjectConfigManager()
    >>> folder_manager = ProjectFolderManager(config_manager)
    >>> data_manager = DataManager()
    >>> 
    >>> # Create GUI and presenter
    >>> view = HeatSystemDesignGUI(folder_manager, data_manager)
    >>> presenter = HeatSystemPresenter(view, folder_manager, data_manager, config_manager)
    >>> view.set_presenter(presenter)
    >>> 
    >>> # Show application
    >>> view.show()
    >>> sys.exit(app.exec())

**Project Creation Example**:

    >>> # Create a new district heating project
    >>> project_path = "/path/to/projects"
    >>> project_name = "District_Heating_Munich"
    >>> 
    >>> # This creates the complete folder structure:
    >>> # District_Heating_Munich/
    >>> #   ├── Eingangsdaten allgemein/
    >>> #   ├── Definition Quartier IST/
    >>> #   └── Variante 1/
    >>> #       ├── Ergebnisse/
    >>> #       ├── Gebäudedaten/
    >>> #       ├── Lastgang/
    >>> #       └── Wärmenetz/

Configuration and Customization
-------------------------------
**Configuration Files**:
    - `config.json`: User preferences and application settings
    - `file_paths.json`: Resource paths and file locations
    - Theme files: Light and dark mode stylesheets

**Resource Management**:
    The application uses a centralized resource management system:
    
    - Automatic path resolution for development and packaged versions
    - Support for relative and absolute path configurations
    - Fallback mechanisms for missing resources

**Extensibility**:
    The modular architecture supports easy extension:
    
    - New tabs can be added by implementing the base tab interface

**Calculation Performance**:
    - Progress feedback for long-running operations

Dependencies
------------
**Core Dependencies**:
    - PyQt6: GUI framework and widgets
    - NumPy: Numerical computations and array operations
    - Pandas: Data manipulation and analysis
    - Matplotlib: Plotting and visualization
    - JSON: Configuration and data serialization

**Optional Dependencies**:
    - ctypes: Windows-specific system integration
    - PyInstaller: Application packaging and distribution
    - Additional scientific libraries for specialized calculations

**Internal Modules**:
    - :mod:`districtheatingsim.utilities`: Common utilities and helpers
    - :mod:`districtheatingsim.gui`: GUI components and interfaces
    - :mod:`districtheatingsim.heat_generators`: Heating system models
    - :mod:`districtheatingsim.network`: Network simulation and analysis

Deployment and Distribution
---------------------------
**Development Environment**:
    - Direct execution from source code
    - Debug mode with detailed logging

**Production Deployment**:
    - PyInstaller packaging for standalone executables
    - Resource bundling and path resolution

**System Requirements**:
    - Tested on Windows with Python 3.11

See Also
--------
:mod:`districtheatingsim.gui.MainTab.main_view` : Main GUI implementation
:mod:`districtheatingsim.gui.MainTab.main_presenter` : Business logic controller
:mod:`districtheatingsim.gui.MainTab.main_data_manager` : Data management classes
:mod:`districtheatingsim.utilities.utilities` : Common utility functions

Notes
-----
The application is designed for professional use in district heating system
planning and analysis. It provides comprehensive tools for engineers and
planners to evaluate different heating system configurations, perform
economic analysis, and generate professional documentation.

The MVP architecture ensures maintainability and testability, while the
modular design allows for easy extension and customization based on
specific project requirements.

For detailed usage instructions, see the user manual and tutorial
documentation provided with the application.
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from districtheatingsim.utilities.utilities import handle_global_exception, get_stylesheet_based_on_time

from districtheatingsim.gui.MainTab.main_presenter import HeatSystemPresenter
from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI
from districtheatingsim.gui.MainTab.main_data_manager import ProjectConfigManager
from districtheatingsim.gui.MainTab.main_data_manager import DataManager
from districtheatingsim.gui.MainTab.main_data_manager import ProjectFolderManager


def main():
    """
    Main application entry point and initialization function.
    
    This function handles the complete application startup sequence including
    system configuration, manager initialization, GUI construction, and
    application launch with proper error handling and cross-platform support.
    
    The initialization process follows a carefully orchestrated sequence:
    
    1. **System Configuration**: Set up global exception handling and Qt application
    2. **Platform Integration**: Configure Windows-specific features if available
    3. **Manager Initialization**: Create data, configuration, and folder managers
    4. **GUI Construction**: Initialize main window and connect presenter
    5. **Theme Application**: Apply time-based theme selection
    6. **Data Loading**: Load initial temperature and heat pump data
    7. **Window Display**: Show maximized window with project folder information
    
    Platform-Specific Features
    ---------------------------
    **Windows Integration**:
        - Sets explicit app user model ID for proper taskbar grouping
        - Enables custom application icon in taskbar
        - Handles Windows-specific path separators and conventions
    
    **Cross-Platform Support**:
        - Graceful fallback for platform-specific features
        - Universal resource path resolution
        - Consistent behavior across operating systems
    
    Error Handling
    --------------
    The application implements comprehensive error handling:
    
    - Global exception handler for unhandled exceptions
    - Logging and debugging information for troubleshooting
    
    Theme Management
    ----------------
    Automatic theme selection based on system time:
    
    - Light theme during daytime hours (6 AM - 6 PM)
    - Dark theme during evening and night hours
    - User can override with manual theme selection
    - Smooth theme transitions and consistent styling
    
    Resource Loading
    ----------------
    Initial data loading includes:
    
    - Temperature data for thermal calculations
    - Heat pump performance characteristics
    - Project configuration and recent project history
    - User interface preferences and settings
    
    Raises
    ------
    SystemExit
        Application exits normally after user closes the window
    Exception
        Any unhandled exceptions are caught by the global exception handler
        
    Examples
    --------
    **Standard Application Launch**:
    
        >>> # From command line or script
        >>> if __name__ == '__main__':
        ...     main()
        
        # This will:
        # 1. Create all necessary managers and GUI components
        # 2. Load the last opened project automatically
        # 3. Display the main window in maximized state
        # 4. Apply appropriate theme based on current time
    
    **Debug Mode Launch**:
    
        >>> import os
        >>> os.environ['DEBUG'] = '1'  # Enable debug logging
        >>> main()  # Launch with additional debugging information
    
    See Also
    --------
    handle_global_exception : Global exception handling function
    get_stylesheet_based_on_time : Time-based theme selection
    HeatSystemPresenter : Main application business logic controller
    HeatSystemDesignGUI : Main application window and user interface
    """
    # Configure global exception handling for user-friendly error reporting
    sys.excepthook = handle_global_exception
    
    # Initialize Qt application with Fusion style for consistent appearance
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Configure Windows-specific taskbar integration for professional appearance
    try:
        import ctypes
        # Set unique application ID for proper Windows taskbar grouping
        myappid = 'districtheatingsim.main.1.0'  # Unique app identifier
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        # Graceful fallback for non-Windows systems
        print("Windows-specific taskbar integration not available on this platform.")
        pass
    except Exception as e:
        # Handle any other Windows integration errors
        print(f"Warning: Could not configure Windows taskbar integration: {e}")
        pass

    # Initialize the core application managers with proper dependency injection
    config_manager = ProjectConfigManager()
    folder_manager = ProjectFolderManager(config_manager)
    data_manager = DataManager()

    # Create the main GUI window with manager dependencies
    view = HeatSystemDesignGUI(folder_manager, data_manager)

    # Initialize the presenter and establish MVP connections
    presenter = HeatSystemPresenter(view, folder_manager, data_manager, config_manager)
    view.set_presenter(presenter)
    
    # Apply time-based theme for optimal user experience
    theme_path = get_stylesheet_based_on_time()
    view.applyTheme(theme_path)

    # Load initial application data for immediate availability
    presenter.view.updateTemperatureData()
    presenter.view.updateHeatPumpData()

    # Configure window display with proper timing to ensure complete initialization
    QTimer.singleShot(0, lambda: view.showMaximized())
    QTimer.singleShot(0, lambda: view.update_project_folder_label(folder_manager.variant_folder))

    # Display the main window and enter the Qt event loop
    view.show()
    
    # Start the application event loop and handle clean shutdown
    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()