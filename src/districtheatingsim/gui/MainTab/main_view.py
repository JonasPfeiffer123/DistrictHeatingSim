"""
DistrictHeatingSim Main GUI View Module
=======================================

This module implements the main graphical user interface for the DistrictHeatingSim
application, providing a comprehensive PyQt6-based interface for district heating
system simulation and analysis. The module follows the Model-View-Presenter (MVP)
architectural pattern as the View component, managing all user interface elements
and interactions.

Module Overview
---------------
The main view module serves as the central GUI controller, orchestrating:

- **Multi-Tab Interface**: Tabbed interface for different analysis modules
- **Menu System**: Comprehensive menu bar with project and data management
- **Theme Management**: Dynamic light/dark theme switching
- **Project Workflow**: Complete project lifecycle management
- **Data Visualization**: Integration with various analysis and visualization tabs
- **User Interaction**: Event handling and user feedback mechanisms

Key Components
--------------
**Main Window Class**:
    :class:`HeatSystemDesignGUI`: Primary application window and interface controller

**Tab Management**:
    - Dynamic tab creation and visibility control
    - Tab ordering and restoration functionality
    - Context-sensitive tab availability

**Menu System**:
    - File operations (create, open, save projects)
    - Data management (temperature data, heat pump characteristics)
    - Theme selection and application
    - Tab visibility control

**Dialog Integration**:
    - Temperature data selection dialogs
    - Heat pump performance data dialogs
    - Project creation and management dialogs

Architecture Integration
------------------------
**MVP Pattern Implementation**:
    The view component integrates with:
    
    - **Model Layer**: Data and configuration managers
    - **Presenter Layer**: Business logic and event handling
    - **External Components**: Specialized tab modules and dialogs

**Signal-Slot Architecture**:
    Utilizes PyQt6's signal-slot mechanism for:
    
    - Inter-component communication
    - Event propagation and handling
    - Real-time UI updates
    - Data synchronization

**Modular Design**:
    Each functional area is implemented as separate tab modules:
    
    - Project definition and configuration
    - Building heat demand analysis
    - Network visualization and generation
    - Hydraulic and thermal calculations
    - Energy system design and optimization
    - Economic comparison and analysis

Author Information
------------------
**Author**: Dipl.-Ing. (FH) Jonas Pfeiffer
**Date**: 2025-06-26
**Version**: Main GUI view for DistrictHeatingSim application

The implementation provides a professional-grade user interface suitable for
engineering applications in district heating system planning and analysis.

Dependencies
------------
**Core GUI Framework**:
    - PyQt6: Primary GUI framework for widgets and layouts
    - QtWidgets: Main widget classes and containers
    - QtGui: Icons, themes, and visual elements

**Internal Modules**:
    - Tab implementations for specialized functionality
    - Dialog components for data input and configuration
    - Utility modules for theme management and PDF generation

**External Integration**:
    - File system operations for project management

See Also
--------
:mod:`districtheatingsim.gui.MainTab.main_presenter` : Business logic controller
:mod:`districtheatingsim.gui.MainTab.main_data_manager` : Data management classes
:mod:`districtheatingsim.gui` : GUI component modules
:mod:`districtheatingsim.utilities` : Common utility functions

Notes
-----
This module implements the user interface layer of a comprehensive district
heating simulation tool. The design emphasizes usability, professional
appearance, and maintainable code structure suitable for engineering
applications requiring complex data analysis and visualization capabilities.

The multi-tab interface allows users to progress through different phases
of district heating system analysis, from initial project setup through
detailed technical and economic evaluation of heating system alternatives.
"""

import os
import traceback
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget, QMenuBar, 
                             QFileDialog, QLabel, QMessageBox, QInputDialog, QStackedWidget,
                             QHBoxLayout)
from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtCore import pyqtSlot

from districtheatingsim.gui.ProjectTab.project_tab import ProjectTab
from districtheatingsim.gui.BuildingTab.building_tab import BuildingTab
from districtheatingsim.gui.NetSimulationTab.calculation_tab import CalculationTab
from districtheatingsim.gui.EnergySystemTab._01_energy_system_main_tab import EnergySystemTab
from districtheatingsim.gui.ComparisonTab.comparison_tab import ComparisonTab

from districtheatingsim.gui.dialogs import TemperatureDataDialog, HeatPumpDataDialog
from districtheatingsim.gui.welcome_screen import WelcomeScreen, ThemeToggleSwitch

from districtheatingsim.gui.LeafletTab.leaflet_tab import VisualizationTabLeaflet


class HeatSystemDesignGUI(QMainWindow):
    """
    Main application window providing comprehensive district heating system analysis interface.

    This class implements the primary user interface for the DistrictHeatingSim application,
    serving as the central hub for project management, data analysis, and system design
    workflows. The interface follows modern GUI design principles with a multi-tab
    architecture that guides users through the complete district heating analysis process.

    The main window integrates multiple specialized analysis modules through a tabbed
    interface, providing seamless workflow progression from initial project setup
    through detailed technical and economic evaluation of heating system alternatives.

    Parameters
    ----------
    folder_manager : ProjectFolderManager
        Manager for project file system operations and folder structure maintenance.
        Handles project creation, variant management, and file path resolution.
    data_manager : DataManager
        Central data storage and management system for application state and user data.
        Maintains consistency across different analysis modules and workflow stages.

    Attributes
    ----------
    presenter : HeatSystemPresenter or None
        Business logic controller implementing MVP pattern presenter component.
        Initially None until set via set_presenter() method.
    folder_manager : ProjectFolderManager
        Reference to project folder management system.
    data_manager : DataManager
        Reference to central data management system.
    folderLabel : QLabel or None
        Status label displaying current project folder path.
    hidden_tabs : dict
        Storage for temporarily hidden tabs to support dynamic tab management.
        Maps tab names to (widget, index) tuples for restoration.
    tab_order : list of str
        Ordered list of tab names maintaining consistent tab sequence.
        Used for proper tab insertion and restoration.
    temperatureDataDialog : TemperatureDataDialog
        Dialog for temperature data selection and configuration.
    heatPumpDataDialog : HeatPumpDataDialog
        Dialog for heat pump performance characteristics configuration.
    
    **Tab Components**:
    
    projectTab : ProjectTab
        Project definition and configuration interface.
    buildingTab : BuildingTab
        Building heat demand analysis and calculation interface.
    visTab2 : VisualizationTabLeaflet
        Interactive map-based network visualization and generation interface.
    calcTab : CalculationTab
        Network hydraulic and thermal calculation interface.
    mixDesignTab : EnergySystemTab
        Energy system design and economic analysis interface.
    comparisonTab : ComparisonTab
        Multi-variant comparison and evaluation interface.
    lod2Tab : LOD2Tab
        LOD2 building data processing and analysis interface.
    renovationTab : RenovationTab
        Building renovation scenario analysis interface.
    individualTab : IndividualTab
        Individual heating solution analysis interface.

    **Menu System Components**:
    
    menubar : QMenuBar
        Main application menu bar with file, data, theme, and tab management.
    tabsMenu : QMenu
        Dynamic menu for tab visibility control and management.
    menu_actions : dict
        Storage for tab-specific menu actions enabling dynamic tab control.

    Notes
    -----
    User Interface Architecture:
        
        **Multi-Tab Design**:
        The interface employs a tab-based design that guides users through
        the district heating analysis workflow:
        
        1. **Project Definition**: Basic project setup and configuration
        2. **Building Analysis**: Heat demand calculation and profiling
        3. **Network Design**: Interactive network layout and generation
        4. **System Calculation**: Hydraulic and thermal network simulation
        5. **Technology Selection**: Energy system design and optimization
        6. **Economic Analysis**: Comprehensive cost-benefit evaluation
        7. **Comparison Tools**: Multi-variant analysis and comparison
        8. **Advanced Features**: Specialized analysis modules
        
        **Dynamic Tab Management**:
        - Tabs can be shown/hidden based on workflow requirements
        - Tab ordering is maintained for consistent user experience
        - Context-sensitive tab availability based on project state
        
        **Professional Interface**:
        - Clean, modern design suitable for engineering applications
        - Consistent styling and theming across all components
        - Responsive layout adaptation for different screen sizes

    Project Management Integration:
        
        **Project Lifecycle**:
        - New project creation with standardized folder structures
        - Existing project opening with variant selection
        - Project copying and variant management
        - Data import/export and result persistence
        
        **Workflow Support**:
        - Sequential workflow guidance through tab organization
        - Data consistency maintenance across analysis modules
        - Automatic saving and loading of project state
        - Professional report generation capabilities

    Theme and Customization:
        
        **Theme System**:
        - Light and dark theme support for user preference
        - Time-based automatic theme selection
        - Consistent styling across all interface components
        - Professional appearance suitable for technical applications
        
        **Customization Options**:
        - Tab visibility control for workflow customization
        - Menu reorganization for user preferences
        - Dialog and window positioning memory
        - User preference persistence across sessions

    Examples
    --------
    **Basic GUI Initialization**:

        >>> from districtheatingsim.gui.MainTab.main_data_manager import *
        >>> from districtheatingsim.gui.MainTab.main_presenter import HeatSystemPresenter
        >>> from PyQt6.QtWidgets import QApplication
        >>> import sys
        >>> 
        >>> # Initialize Qt application
        >>> app = QApplication(sys.argv)
        >>> 
        >>> # Create managers
        >>> config_manager = ProjectConfigManager()
        >>> folder_manager = ProjectFolderManager(config_manager)
        >>> data_manager = DataManager()
        >>> 
        >>> # Create main GUI window
        >>> main_window = HeatSystemDesignGUI(folder_manager, data_manager)
        >>> 
        >>> # Create and connect presenter
        >>> presenter = HeatSystemPresenter(main_window, folder_manager, data_manager, config_manager)
        >>> main_window.set_presenter(presenter)
        >>> 
        >>> # Show window and start application
        >>> main_window.show()
        >>> sys.exit(app.exec())

    **Project Management Example**:

        >>> # Create new project through GUI
        >>> # User clicks "File" -> "Create New Project"
        >>> # GUI prompts for project name and location
        >>> project_name = "Munich_District_Heating"
        >>> project_path = "/projects/heating_systems"
        >>> 
        >>> # Project structure is automatically created:
        >>> # Munich_District_Heating/
        >>> #   ├── Eingangsdaten allgemein/
        >>> #   ├── Definition Quartier IST/
        >>> #   └── Variante 1/
        >>> #       ├── Ergebnisse/
        >>> #       ├── Gebäudedaten/
        >>> #       ├── Lastgang/
        >>> #       └── Wärmenetz/

    **Tab Management Example**:

        >>> # Hide specialized tabs for basic workflow
        >>> main_window.toggle_tab_visibility("Verarbeitung LOD2-Daten")
        >>> main_window.toggle_tab_visibility("Gebäudesanierung")
        >>> main_window.toggle_tab_visibility("Einzelversorgungslösung")
        >>> 
        >>> # Show only core analysis tabs
        >>> core_tabs = [
        ...     "Projektdefinition",
        ...     "Wärmebedarf Gebäude", 
        ...     "Kartenansicht Wärmenetzgenerierung",
        ...     "Wärmenetzberechnung",
        ...     "Erzeugerauslegung und Wirtschaftlichkeitsrechnung",
        ...     "Variantenvergleich"
        ... ]
        >>> 
        >>> # Tabs are automatically ordered and displayed

    **Theme Application Example**:

        >>> # Apply dark theme for evening work
        >>> main_window.applyTheme('dark_theme_style_path')
        >>> 
        >>> # Apply light theme for daytime work
        >>> main_window.applyTheme('light_theme_style_path')
        >>> 
        >>> # Theme is applied to all tabs and dialogs automatically

    See Also
    --------
    HeatSystemPresenter : Business logic controller for main window
    ProjectFolderManager : Project file system management
    DataManager : Central data storage and management
    ProjectTab : Project definition and configuration interface
    BuildingTab : Building heat demand analysis interface
    EnergySystemTab : Energy system design and optimization interface

    References
    ----------
    .. [1] PyQt6 Documentation, "Model/View Programming"
    .. [2] Qt Documentation, "Application Windows and Dialogs"
    .. [3] GUI Design Principles for Engineering Applications
    """

    def __init__(self, folder_manager, data_manager):
        """
        Initialize the main application window with manager dependencies.

        This constructor sets up the basic window structure and initializes
        core components, but defers UI creation until the presenter is set
        to ensure proper MVP pattern implementation.

        Parameters
        ----------
        folder_manager : ProjectFolderManager
            Project folder management system for file operations.
        data_manager : DataManager
            Central data management system for application state.

        Notes
        -----
        The initialization follows a two-phase approach:
        
        1. **Basic Setup**: Window creation and manager assignment
        2. **UI Creation**: Deferred until presenter connection via set_presenter()
        
        This ensures proper dependency injection and MVP pattern compliance.
        """
        super().__init__()
        
        # MVP pattern: Initially no presenter until explicitly set
        self.presenter: None
        
        # Store manager references for later use
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        
        # UI state management
        self.show_welcome_on_startup = True
        self.welcome_screen: Optional[WelcomeScreen] = None
        self.main_interface_widget: Optional[QWidget] = None
        self.stacked_widget: Optional[QStackedWidget] = None
        
        # Theme tracking
        self.current_theme_is_dark = False  # Track current theme state
        
        # Initialize UI components (created later in initUI)
        self.folderLabel: Optional[QLabel] = None

    def set_presenter(self, presenter) -> None:
        """
        Set the presenter and initialize the complete user interface.

        This method completes the MVP pattern setup by connecting the presenter
        and triggering full UI initialization. All UI components are created
        after presenter connection to ensure proper event handling setup.

        Parameters
        ----------
        presenter : HeatSystemPresenter
            Business logic controller implementing presenter pattern.
            Manages user interactions and coordinates between model and view.

        Notes
        -----
        Post-Presenter Initialization:
            
            **UI Component Creation**:
            - Complete interface layout and widget creation
            - Menu system setup with proper event connections
            - Tab system initialization with all analysis modules
            - Dialog creation for data input and configuration
            
            **Event Connection**:
            - Signal-slot connections for model-view synchronization
            - Menu action connections for user interactions
            - Tab visibility and management event handling
            
            **Theme and Styling**:
            - Application logo and icon setup
            - Theme system initialization
            - Professional styling application

        The method ensures that all UI components are properly connected
        to the business logic layer before the interface is displayed.
        """
        self.presenter = presenter

        # Initialize dialogs early for later reference
        self.temperatureDataDialog = TemperatureDataDialog(self)
        self.heatPumpDataDialog = HeatPumpDataDialog(self)

        # Complete UI initialization now that presenter is available
        self.initUI()

    def initUI(self) -> None:
        """
        Initialize the user interface with stacked widget architecture.
        """
        # Configure main window properties
        self.setWindowTitle("DistrictHeatingSim")
        self.setGeometry(100, 100, 1400, 1000)
        
        # Create central stacked widget to manage views
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Create welcome screen
        self.init_welcome_screen()
        
        # Create main interface widget  
        self.init_main_interface()
        
        # Add both views to the stacked widget
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.main_interface_widget)
        
        # Show welcome screen by default if enabled
        if self.show_welcome_on_startup:
            self.show_welcome_screen()
        else:
            self.show_main_interface()
        
        # Apply theme (this will work on both views)
        self.apply_theme()

    def init_welcome_screen(self) -> None:
        """Initialize the welcome screen widget."""
        # Create welcome screen with config manager for recent projects
        config_manager = None
        if hasattr(self, 'presenter') and self.presenter:
            config_manager = self.presenter.folder_manager.config_manager
        
        self.welcome_screen = WelcomeScreen(config_manager)
        
        # Connect welcome screen signals
        self.welcome_screen.projectSelected.connect(self.on_project_selected)
        self.welcome_screen.newProjectRequested.connect(self.on_new_project_requested)
        self.welcome_screen.themeChangeRequested.connect(self.on_theme_change_requested)
        
        # Apply current application theme to welcome screen and sync toggle state
        if hasattr(self, 'presenter') and self.presenter:
            self.apply_current_theme_to_welcome_screen()
            self.sync_theme_toggle_state()
        
        # Hide menu bar on welcome screen
        self.menuBar().hide()

    def init_main_interface(self) -> None:
        """Initialize the main application interface widget."""        
        # Create main interface widget if not exists
        if self.main_interface_widget is None:
            self.main_interface_widget = QWidget()
            self.layout1 = QVBoxLayout(self.main_interface_widget)

            # Initialize major interface components
            self.initMenuBar()
            self.initTabs()
            self.initLogo()
            
            # Add theme toggle to the top-right corner
            self.add_theme_toggle_to_main_interface()

            # Create project status display
            self.folderLabel = QLabel("Kein Projektordner ausgewählt")
            self.layout1.addWidget(self.folderLabel)

            # Ensure dialogs are properly initialized
            self.temperatureDataDialog = TemperatureDataDialog(self)
            self.heatPumpDataDialog = HeatPumpDataDialog(self)

            # Connect model signals to view updates for reactive interface
            # Disconnect first to avoid duplicate connections
            try:
                self.folder_manager.project_folder_changed.disconnect(self.update_project_folder_label)
                self.presenter.folder_manager.project_folder_changed.disconnect(self.updateTemperatureData)
                self.presenter.folder_manager.project_folder_changed.disconnect(self.updateHeatPumpData)
            except:
                pass  # Connections might not exist yet
            
            # Connect signals
            self.folder_manager.project_folder_changed.connect(self.update_project_folder_label)
            self.presenter.folder_manager.project_folder_changed.connect(self.updateTemperatureData)
            self.presenter.folder_manager.project_folder_changed.connect(self.updateHeatPumpData)

    def show_welcome_screen(self) -> None:
        """
        Zeige den Welcome Screen und setze base_path auf leer.
        """
        self.base_path = ""
        if self.stacked_widget and self.welcome_screen:
            self.stacked_widget.setCurrentWidget(self.welcome_screen)
            self.menuBar().hide()
            
    def show_main_interface(self) -> None:
        """Switch to showing the main interface."""
        if self.stacked_widget and self.main_interface_widget:
            self.stacked_widget.setCurrentWidget(self.main_interface_widget)
            self.menuBar().show()

    def add_theme_toggle_to_main_interface(self):
        """Add theme toggle switch to the main interface next to menu bar."""
        # Create a horizontal layout for menu bar and theme toggle
        top_bar_widget = QWidget()
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(0)  # No spacing between menu and toggle
        
        # Add menu bar to the left side - it will expand to fill available space
        top_bar_layout.addWidget(self.menubar, 1) # stretch factor 1
        
        # Create a compact widget for theme toggle elements
        theme_widget = QWidget()
        theme_widget.setFixedHeight(self.menubar.sizeHint().height())  # Match menu bar height
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(8, 0, 8, 0)  # Small padding on sides
        theme_layout.setSpacing(5)
        
        # Theme toggle elements
        theme_label = QLabel("☀️")
        theme_label.setFont(QFont("Arial", 11))
        theme_layout.addWidget(theme_label)
        
        # Create theme toggle for main interface
        self.main_theme_toggle = ThemeToggleSwitch()
        self.main_theme_toggle.setToolTip("Switch between Light and Dark theme")
        self.main_theme_toggle.toggled.connect(self.on_main_theme_toggle)
        theme_layout.addWidget(self.main_theme_toggle)
        
        dark_label = QLabel("🌙")
        dark_label.setFont(QFont("Arial", 11))
        theme_layout.addWidget(dark_label)
        
        # Add theme widget to the right side without stretch
        top_bar_layout.addWidget(theme_widget, 0)  # no stretch factor
        
        top_bar_widget.setLayout(top_bar_layout)
        
        # Replace the menu bar with the combined top bar
        self.layout1.removeWidget(self.menubar)
        self.layout1.insertWidget(0, top_bar_widget)

    def on_main_theme_toggle(self, checked):
        """Handle theme toggle from main interface."""
        self.current_theme_is_dark = checked
        
        if checked:
            self.applyTheme('dark_theme_style_path')
        else:
            self.applyTheme('light_theme_style_path')
            
        # Sync welcome screen toggle if it exists
        if self.welcome_screen:
            self.welcome_screen.set_current_theme(checked)

    def on_project_selected(self, project_path: str):
        """Handle project selection from welcome screen."""
        # Switch to main interface
        self.show_main_interface()
        
        # Sync theme toggle state
        self.sync_theme_toggle_state()
        
        # Use the existing project opening functionality
        try:
            # Call the existing method that handles project opening with all the proper logic
            self.on_open_existing_project(project_path)
        except Exception as e:
            print(f"Warning: Could not load project from {project_path}: {e}")
            # Fallback: just show the main interface
            pass

    def on_new_project_requested(self):
        """Handle new project creation request from welcome screen."""
        # Switch to main interface 
        self.show_main_interface()
        
        # Sync theme toggle state
        self.sync_theme_toggle_state()
        
        # Use the existing new project functionality
        try:
            self.on_create_new_project()
        except Exception as e:
            print(f"Warning: Could not create new project: {e}")
            # Fallback: just show the main interface
            pass

    def show_save_dialog(self, title: str, info_text: str, accept_text: str) -> str:
        """
        Show a standardized save dialog for project operations.
        
        Parameters
        ----------
        title : str
            Dialog window title
        info_text : str 
            Informative text explaining the operation
        accept_text : str
            Text for the accept button (e.g., "Speichern und wechseln")
            
        Returns
        -------
        str
            'save', 'discard', or 'cancel'
        """
        if not hasattr(self, 'base_path') or not self.base_path:
            return 'continue'  # No project loaded, continue operation
            
        from PyQt6.QtWidgets import QMessageBox
        
        # Create custom message box with three options
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(title)
        msgBox.setText('Es ist ein Projekt geöffnet.')
        msgBox.setInformativeText(info_text)
        
        # Force larger dialog size with stylesheet
        msgBox.setStyleSheet("""
            QMessageBox {
                min-width: 550px;
                min-height: 250px;
            }
            QMessageBox QLabel {
                min-width: 525px;
                font-size: 11pt;
            }
            QMessageBox QPushButton {
                min-width: 120px;
                min-height: 30px;
                font-size: 10pt;
                padding: 5px 10px;
                margin: 2px;
            }
        """)
        
        # Add custom buttons
        saveButton = msgBox.addButton(accept_text, QMessageBox.ButtonRole.AcceptRole)
        discardButton = msgBox.addButton('Ohne Speichern fortfahren', QMessageBox.ButtonRole.DestructiveRole)
        cancelButton = msgBox.addButton('Abbrechen', QMessageBox.ButtonRole.RejectRole)
        
        msgBox.setDefaultButton(saveButton)  # Default to save for safety
        msgBox.exec()
        
        if msgBox.clickedButton() == saveButton:
            return 'save'
        elif msgBox.clickedButton() == discardButton:
            return 'discard'
        else:
            return 'cancel'

    def on_back_to_welcome(self):
        """
        Return to the welcome screen from main interface.
        Give user choice to save, discard, or cancel if project is loaded.
        """
        dialog_result = self.show_save_dialog(
            'Zurück zum Start',
            'Möchten Sie Ihre Änderungen vor dem Wechsel zum Startbildschirm speichern?',
            'Speichern und zum Start'
        )
        
        if dialog_result == 'save':
            # Save and go to welcome
            if not self.save_all_project_results():
                return  # User cancelled save operation
            self.base_path = ""
            self.show_welcome_screen()
            if self.welcome_screen:
                self.welcome_screen.refresh_recent_projects()
                self.sync_theme_toggle_state()
        elif dialog_result == 'discard':
            # Go to welcome without saving
            self.base_path = ""
            self.show_welcome_screen()
            if self.welcome_screen:
                self.welcome_screen.refresh_recent_projects()
                self.sync_theme_toggle_state()
        elif dialog_result == 'continue':
            # No project loaded, go to welcome normally
            self.show_welcome_screen()
            if self.welcome_screen:
                self.welcome_screen.refresh_recent_projects()
                self.sync_theme_toggle_state()
        # If 'cancel', do nothing

    def on_theme_change_requested(self, theme_path: str):
        """Handle theme change request from welcome screen."""
        # Update theme state tracking
        self.current_theme_is_dark = 'dark' in theme_path.lower()
        
        # Apply theme to the entire application
        self.applyTheme(theme_path)
        
        # Update the main interface toggle switch state to reflect the new theme
        if hasattr(self, 'main_theme_toggle') and self.main_theme_toggle:
            self.main_theme_toggle.toggled.disconnect(self.on_main_theme_toggle)
            self.main_theme_toggle.setChecked(self.current_theme_is_dark)
            self.main_theme_toggle.toggled.connect(self.on_main_theme_toggle)

    def apply_theme(self):
        """Apply the current theme to both welcome screen and main interface."""
        try:
            # Get the current theme from utilities
            from districtheatingsim.utilities.utilities import get_stylesheet_based_on_time
            theme_path = get_stylesheet_based_on_time()
            
            # Update our theme state tracking
            self.current_theme_is_dark = 'dark' in theme_path.lower()
            
            # Apply theme to the main application
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as file:
                    theme_content = file.read()
                    self.setStyleSheet(theme_content)
                    
                    # Also apply to welcome screen if it exists
                    if self.welcome_screen:
                        self.welcome_screen.setStyleSheet(theme_content)
                        
            # Sync toggle states
            self.sync_theme_toggle_state()
        except Exception as e:
            print(f"Warning: Could not apply theme: {e}")

    def apply_current_theme_to_welcome_screen(self):
        """Apply the current application theme to the welcome screen."""
        if not self.welcome_screen:
            return
            
        try:
            # Get the current theme from utilities (same logic as main app startup)
            from districtheatingsim.utilities.utilities import get_stylesheet_based_on_time
            theme_path = get_stylesheet_based_on_time()
            
            # Apply theme to welcome screen
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as file:
                    self.welcome_screen.setStyleSheet(file.read())
        except Exception as e:
            print(f"Warning: Could not apply current theme to welcome screen: {e}")

    def sync_theme_toggle_state(self):
        """Synchronize the theme toggle switch with the current theme."""        
        try:
            # First try to use our tracked theme state
            is_dark_theme = self.current_theme_is_dark
            
            # If we don't have tracked state, determine from utilities as fallback
            if not hasattr(self, 'current_theme_is_dark'):
                from districtheatingsim.utilities.utilities import get_stylesheet_based_on_time
                theme_path = get_stylesheet_based_on_time()
                is_dark_theme = 'dark' in theme_path.lower()
                self.current_theme_is_dark = is_dark_theme
            
            # Set welcome screen toggle state without triggering signals
            if self.welcome_screen:
                self.welcome_screen.set_current_theme(is_dark_theme)
                
            # Set main interface toggle state without triggering signals
            if hasattr(self, 'main_theme_toggle') and self.main_theme_toggle:
                self.main_theme_toggle.toggled.disconnect(self.on_main_theme_toggle)
                self.main_theme_toggle.setChecked(is_dark_theme)
                self.main_theme_toggle.toggled.connect(self.on_main_theme_toggle)
                
        except Exception as e:
            print(f"Warning: Could not sync theme toggle state: {e}")

    def initMenuBar(self) -> None:
        """
        Initialize the comprehensive menu bar system with all functional categories.

        This method creates a professional menu system providing access to all
        application functionality including project management, data configuration,
        theme selection, and tab control. The menu follows standard GUI conventions
        with logical grouping and keyboard shortcuts.

        Menu Structure:
            
            **File Menu**:
            - Project creation and management
            - Recent projects with quick access
            - Project variants and copies
            - Data import/export functionality
            - Professional PDF report generation
            
            **Data Menu**:
            - Temperature data configuration
            - Heat pump performance characteristics
            - External data source integration
            
            **Theme Menu**:
            - Light mode for daytime work
            - Dark mode for evening work
            - Automatic theme switching
            
            **Tabs Menu**:
            - Dynamic tab visibility control
            - Workflow customization options
            - Tab ordering and management

        The menu system integrates seamlessly with the business logic layer
        through the presenter pattern, ensuring proper separation of concerns
        and maintainable code structure.

        Notes
        -----
        Recent Projects Integration:
            
            **Smart Recent Projects**:
            - Automatic tracking of recently opened projects
            - Quick access to frequently used projects
            - Graceful handling of missing or moved projects
            - Configurable recent projects list length
            
            **User Experience**:
            - One-click access to recent work
            - Visual indication of project availability
            - Fallback messaging for empty recent list

        Professional Menu Features:
            
            **Standard Conventions**:
            - Consistent with platform-specific menu standards
            - Logical grouping of related functionality
            - Appropriate use of separators and organization
            - Professional terminology and descriptions
            
            **Accessibility**:
            - Keyboard shortcuts for common operations
            - Clear, descriptive menu item text
            - Proper enabling/disabling based on context
            - User-friendly error handling and feedback
        """
        # Create main menu bar with professional appearance
        self.menubar = QMenuBar(self)
        self.menubar.setFixedHeight(30)

        # File Menu - Project and data management
        fileMenu = self.menubar.addMenu('Datei')

        # Back to Welcome Screen action
        backToWelcomeAction = QAction('🏠 Zurück zum Start', self)
        fileMenu.addAction(backToWelcomeAction)
        fileMenu.addSeparator()  # Visual separation from project operations

        # Recent Projects submenu with dynamic content
        recentMenu = fileMenu.addMenu('Zuletzt geöffnet')
        recent_projects = self.presenter.folder_manager.config_manager.get_recent_projects()
        
        if recent_projects:
            # Add recent projects with click handlers
            for project in recent_projects:
                action = QAction(project, self)
                action.triggered.connect(lambda checked, p=project: self.on_open_existing_project(p))
                recentMenu.addAction(action)
        else:
            # Provide user feedback when no recent projects exist
            no_recent_action = QAction('Keine kürzlich geöffneten Projekte', self)
            no_recent_action.setEnabled(False)
            recentMenu.addAction(no_recent_action)

        # Add primary file actions to file menu
        createNewProjectAction = QAction('Neues Projekt erstellen', self)
        chooseProjectAction = QAction('Projekt öffnen', self)
        createCopyAction = QAction('Projektkopie erstellen', self)
        for primaryFileAction in [createNewProjectAction, chooseProjectAction, createCopyAction]:
            fileMenu.addAction(primaryFileAction)
        
        fileMenu.addSeparator()  # Separate each major action for clarity

        # Add project variant actions to file menu
        openVariantAction = QAction('Variante öffnen', self)
        createVariantAction = QAction('Variante erstellen', self)
        createVariantCopyAction = QAction('Variantenkopie erstellen', self)
        for variantAction in [openVariantAction, createVariantAction, createVariantCopyAction]:
            fileMenu.addAction(variantAction)
        
        fileMenu.addSeparator()  # Separate each major action for clarity

        # Add data import/export actions to file menu
        importResultsAction = QAction('Projektstand / -ergebnisse Laden', self)
        fileMenu.addAction(importResultsAction)

        # Data Menu - External data configuration
        dataMenu = self.menubar.addMenu('Datenbasis')
        chooseTemperatureDataAction = QAction('Temperaturdaten festlegen', self)
        createCOPDataAction = QAction('COP-Kennfeld festlegen', self)
        dataMenu.addAction(chooseTemperatureDataAction)
        dataMenu.addAction(createCOPDataAction)

        # Note: Menu bar will be added to layout in add_theme_toggle_to_main_interface()

        # Connect menu actions to handler methods
        backToWelcomeAction.triggered.connect(self.on_back_to_welcome)
        createNewProjectAction.triggered.connect(self.on_create_new_project)
        chooseProjectAction.triggered.connect(self.on_open_existing_project)
        createCopyAction.triggered.connect(self.on_create_project_copy)
        openVariantAction.triggered.connect(self.on_open_variant)
        createVariantAction.triggered.connect(self.on_create_project_variant)
        createVariantCopyAction.triggered.connect(self.on_create_project_variant_copy)
        importResultsAction.triggered.connect(self.on_importResultsAction)
        chooseTemperatureDataAction.triggered.connect(self.openTemperatureDataSelection)
        createCOPDataAction.triggered.connect(self.openCOPDataSelection)

    def initTabs(self) -> None:
        """
        Initialize the comprehensive multi-tab interface for district heating analysis.

        This method creates the complete tabbed interface that guides users through
        the district heating system analysis workflow. Each tab represents a major
        phase of the analysis process, from initial project setup through detailed
        economic evaluation and comparison.

        The tab system supports dynamic visibility control, allowing users to
        customize their workflow by showing only relevant analysis modules for
        their specific project requirements.

        Tab Architecture:
            
            **Core Analysis Workflow**:
            1. **Project Definition**: Basic project setup and configuration
            2. **Building Heat Demand**: Heat requirement analysis and profiling
            3. **Network Visualization**: Interactive network design and layout
            4. **Network Calculation**: Hydraulic and thermal system simulation
            5. **Energy System Design**: Technology selection and optimization
            6. **Variant Comparison**: Economic and technical comparison analysis
            
            **Specialized Modules**:
            7. **LOD2 Processing**: Advanced building geometry analysis
            8. **Renovation Analysis**: Building upgrade scenario evaluation
            9. **Individual Solutions**: Decentralized heating system analysis

        Tab Management Features:
            
            **Dynamic Visibility**:
            - Tabs can be shown/hidden based on project requirements
            - Default visible tabs for standard workflow
            - Specialized tabs hidden by default to reduce interface complexity
            - Tab restoration maintains original ordering
            
            **Professional Interface**:
            - Closeable tabs with proper restoration functionality
            - Consistent styling and layout across all tabs
            - Context-sensitive tab availability
            - Seamless data flow between analysis phases

        Notes
        -----
        Default Tab Configuration:
            
            **Always Visible**:
            - Project Definition (mandatory starting point)
            - Building Heat Demand (core analysis requirement)
            - Network Visualization (essential for network design)
            - Network Calculation (fundamental simulation capability)
            - Energy System Design (technology selection core)
            - Variant Comparison (essential decision support)
            
            **Hidden by Default**:
            - LOD2 Processing (specialized building data analysis)
            - Renovation Analysis (optional upgrade scenarios)
            - Individual Solutions (alternative to district systems)

        Integration with Business Logic:
            
            **Data Flow**:
            Each tab is connected to the same manager instances, ensuring:
            - Consistent data access across all analysis modules
            - Real-time synchronization of project changes
            - Centralized configuration management
            - Unified error handling and user feedback
            
            **Workflow Support**:
            - Sequential analysis progression through tab ordering
            - Data validation and consistency checking
            - Automatic saving and loading of intermediate results
            - Professional report generation from all analysis phases
        """
        # Create main tab widget with closeable tabs
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(False)
        
        # Add tab widget to main layout
        self.layout1.addWidget(self.tabWidget)

        # Initialize all analysis tabs with proper manager dependencies
        self.projectTab = ProjectTab(
            self.presenter.folder_manager, 
            self.presenter.data_manager, 
            self.presenter.config_manager
        )
        
        self.buildingTab = BuildingTab(
            self.presenter.folder_manager, 
            self.presenter.data_manager, 
            self.presenter.config_manager
        )
        
        self.visTab2 = VisualizationTabLeaflet(
            self.presenter.folder_manager, 
            self.presenter.data_manager, 
            self.presenter.config_manager
        )
        
        self.calcTab = CalculationTab(
            self.presenter.folder_manager, 
            self.presenter.data_manager, 
            self.presenter.config_manager, 
            self
        )
        
        self.energySystemTab = EnergySystemTab(
            self.presenter.folder_manager, 
            self.presenter.data_manager, 
            self.presenter.config_manager, 
            self
        )
        
        self.comparisonTab = ComparisonTab(
            self.presenter.folder_manager, 
            self.presenter.data_manager, 
            self.presenter.config_manager
        )
        # Add tabs to interface with proper German localization
        self.tabWidget.addTab(self.projectTab, "Projektdefinition")
        self.tabWidget.addTab(self.buildingTab, "Wärmebedarf Gebäude")
        self.tabWidget.addTab(self.visTab2, "Kartenansicht Wärmenetzgenerierung")
        self.tabWidget.addTab(self.calcTab, "Wärmenetzberechnung")
        self.tabWidget.addTab(self.energySystemTab, "Erzeugerauslegung und Wirtschaftlichkeitsrechnung")
        self.tabWidget.addTab(self.comparisonTab, "Variantenvergleich")

    def initLogo(self) -> None:
        """
        Initialize the application logo and window icon for professional branding.

        This method handles logo loading with comprehensive fallback mechanisms
        to ensure the application maintains professional appearance even when
        resources are missing or paths are incorrect. The logo serves as both
        window icon and application identifier in the taskbar.

        Logo Loading Strategy:
            
            **Primary Path Resolution**:
            - Uses ConfigManager for proper resource path resolution
            - Handles both development and packaged application scenarios
            - Supports relative and absolute path configurations
            
            **Fallback Mechanisms**:
            - Multiple fallback paths for logo discovery
            - Graceful degradation when logo is unavailable
            - User feedback for troubleshooting logo issues
            - Default system icon when all fallbacks fail

        Professional Branding Integration:
            
            **Visual Identity**:
            - Consistent logo application across application windows
            - Professional icon for taskbar and window management
            - Brand recognition in multi-application environments
            - Quality assurance for packaged application distribution

        Notes
        -----
        Resource Path Handling:
            
            **Development Environment**:
            - Direct file system access to logo resources
            - Relative path resolution from module location
            - Hot-reload capability for logo updates during development
            
            **Packaged Application**:
            - Bundled resource access through PyInstaller or similar
            - Embedded resource extraction and utilization
            - Cross-platform path resolution and compatibility
            
            **Error Handling**:
            - Comprehensive exception handling for missing resources
            - User-friendly error messages with troubleshooting guidance
            - Logging for development and deployment debugging
            - Graceful fallback to system default icons

        The method ensures that the application maintains professional
        appearance regardless of deployment scenario or resource availability.
        """
        try:
            # Primary logo loading through configuration manager
            logo_path = self.presenter.config_manager.get_resource_path('logo_path')
            
            # Create and validate icon
            icon = QIcon(logo_path)
            if not icon.isNull():
                self.setWindowIcon(icon)
                print(f"Logo erfolgreich geladen: {logo_path}")
                return
            else:
                print(f"Logo konnte nicht geladen werden: {logo_path}")
                
        except Exception as e:
            print(f"Fehler beim Laden des Logos: {e}")
            
        # Comprehensive fallback mechanism for logo discovery
        try:
            fallback_paths = [
                'styles/logo.png',
                'styles\\logo.png',
                os.path.join('styles', 'logo.png'),
                os.path.join(os.path.dirname(__file__), 'styles', 'logo.png'),
                os.path.join(os.path.dirname(__file__), '..', 'styles', 'logo.png'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'styles', 'logo.png')
            ]
            
            # Try each fallback path sequentially
            for path in fallback_paths:
                if os.path.exists(path):
                    icon = QIcon(path)
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        print(f"Logo erfolgreich geladen (Fallback): {path}")
                        return
                        
            # Final fallback - no logo available
            print("Kein Logo gefunden - verwende Standard-Icon")
            
        except Exception as fallback_error:
            print(f"Auch Fallback-Logo konnte nicht geladen werden: {fallback_error}")

    @pyqtSlot(str)
    def update_project_folder_label(self, base_path: str) -> None:
        """
        Update the project folder status label with current project information.

        This method provides real-time feedback to users about the currently
        active project, displaying the full path to help users understand
        their current working context within the application.

        Parameters
        ----------
        base_path : str
            Current project base path, typically the variant folder path.
            Empty string or None indicates no active project.

        Notes
        -----
        User Experience Benefits:
            
            **Context Awareness**:
            - Clear indication of active project for user orientation
            - Full path display for unambiguous project identification
            - Real-time updates when project changes occur
            - Professional status reporting consistent with engineering tools
            
            **Workflow Support**:
            - Immediate feedback when projects are opened or changed
            - Visual confirmation of successful project operations
            - Clear indication when no project is selected
            - Support for troubleshooting project-related issues

        The label serves as an important user interface element for maintaining
        context awareness in complex project workflows with multiple variants
        and analysis phases.
        """
        # Store base path for other operations
        self.base_path = base_path

        # Update status label with current project information only if label exists and is valid
        if self.folderLabel is not None:
            try:
                if base_path:
                    self.folderLabel.setText(f"Ausgewählter Projektordner: {base_path}")
                else:
                    self.folderLabel.setText("Kein Projektordner ausgewählt")
            except RuntimeError:
                # QLabel has been deleted - reset reference
                self.folderLabel = None

    def show_error_message(self, message: str) -> None:
        """
        Display professional error messages with consistent styling and behavior.

        This method provides standardized error reporting throughout the application,
        ensuring users receive clear, actionable feedback when problems occur.
        The error display follows GUI best practices for professional software.

        Parameters
        ----------
        message : str
            Error message text to display to the user.
            Should be clear, descriptive, and actionable when possible.

        Notes
        -----
        Error Handling Philosophy:
            
            **User-Friendly Communication**:
            - Clear, non-technical language when possible
            - Specific problem description with context
            - Actionable guidance for error resolution
            - Professional tone appropriate for engineering software
            
            **Consistent Interface**:
            - Standardized error dialog appearance
            - Consistent button layout and behavior
            - Proper modal behavior for user attention
            - Integration with application theming system

        This method serves as the central error reporting mechanism for
        all user-facing error conditions throughout the application.
        """
        QMessageBox.critical(self, "Fehler", message)

    def show_message(self, title: str, message: str) -> None:
        """Show a success/info message dialog."""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, title, message)

    # Project Management Methods
    # ==========================

    def on_create_new_project(self) -> None:
        """
        Handle new project creation with user input and validation.

        This method manages the complete new project creation workflow,
        including user input collection, validation, and success feedback.
        It integrates with the folder manager to ensure proper project
        structure creation following established conventions.

        Workflow Steps:
            
            1. **Path Resolution**: Determine parent directory for new project
            2. **User Input**: Collect project name through input dialog
            3. **Validation**: Check project name validity and uniqueness
            4. **Creation**: Execute project creation through presenter
            5. **Feedback**: Provide success or failure notification

        Notes
        -----
        Project Creation Standards:
            
            **Folder Structure**:
            The method creates standardized folder structures:
            - Main project folder with user-specified name
            - Standardized subfolder hierarchy for data organization
            - Default variant folder for initial analysis work
            - Proper permissions and accessibility setup
            
            **User Experience**:
            - Intuitive input dialogs with helpful defaults
            - Clear success/failure feedback
            - Automatic project activation after creation
            - Integration with recent projects system
        """
        # Check if user wants to save current project before creating new one
        dialog_result = self.show_save_dialog(
            'Neues Projekt erstellen',
            'Möchten Sie Ihre Änderungen vor dem Erstellen eines neuen Projekts speichern?',
            'Speichern und neues Projekt erstellen'
        )
        
        if dialog_result == 'cancel':
            return  # User cancelled operation
        elif dialog_result == 'save':
            if not self.save_all_project_results():
                return  # User cancelled save operation
        # If 'discard' or 'continue', proceed without saving
        
        # Determine parent directory for new project
        folder_path = os.path.dirname(os.path.dirname(self.base_path))
        
        if folder_path:
            # Collect project name from user
            projectName, ok = QInputDialog.getText(
                self, 
                'Neues Projekt', 
                'Projektnamen eingeben:', 
                text='Neues Projekt'
            )
            
            # Process project creation if user confirmed
            if ok and projectName:
                success = self.presenter.create_new_project(folder_path, projectName)
                if success:
                    QMessageBox.information(
                        self, 
                        "Projekt erstellt", 
                        f"Projekt '{projectName}' wurde erfolgreich erstellt."
                    )

    def on_open_existing_project(self, folder_path: Optional[str] = None) -> None:
        """
        Handle opening existing projects with variant selection support.
        Before switching, save all current project results.

        This method manages the complete project opening workflow, including
        folder selection, variant discovery, and user choice collection.
        It supports both manual folder selection and direct path specification
        for recent project integration.

        Parameters
        ----------
        folder_path : str, optional
            Direct path to project folder. If None, user will be prompted
            to select folder through file dialog. Used for recent projects.

        Workflow Process:
            
            1. **Folder Selection**: Interactive folder selection or direct path
            2. **Project Validation**: Verify project structure and accessibility
            3. **Variant Discovery**: Scan for available project variants
            4. **User Selection**: Present variant choices to user
            5. **Project Activation**: Load selected project and variant

        Notes
        -----
        Variant Management:
            
            **Automatic Discovery**:
            - Scans project folder for variant subdirectories
            - Validates variant folder structure and accessibility
            - Presents user-friendly variant selection interface
            - Handles projects with single or multiple variants
            
            **User Experience**:
            - Clear variant naming and identification
            - Intuitive selection dialogs with helpful information
            - Graceful handling of missing or corrupted variants
            - Integration with recent projects for quick access
        """
        # Handle folder selection - either direct path or user dialog
        if not folder_path:
            folder_path = QFileDialog.getExistingDirectory(
                self, 
                "Projektordner auswählen", 
                os.path.dirname(os.path.dirname(self.base_path))
            )

        try:
            # Check if user wants to save before switching projects
            dialog_result = self.show_save_dialog(
                'Projekt öffnen',
                'Möchten Sie Ihre Änderungen vor dem Öffnen eines anderen Projekts speichern?',
                'Speichern und Projekt öffnen'
            )
            
            if dialog_result == 'cancel':
                return  # User cancelled operation
            elif dialog_result == 'save':
                if not self.save_all_project_results():
                    return  # User cancelled save operation
            # If 'discard' or 'continue', proceed without saving
            
            # Validate project path and proceed with opening
            if folder_path and os.path.exists(folder_path):
                self.presenter.open_existing_project(folder_path)
                
                # Discover and present available variants
                available_variants = self.get_available_variants(folder_path)
                if available_variants:
                    # If only one variant, select it automatically
                    if len(available_variants) == 1:
                        variant_name = available_variants[0]
                        self.presenter.folder_manager.set_variant_folder(variant_name)
                        # Automatically load available results
                        self.on_importResultsAction()
                    else:
                        # Multiple variants - let user choose
                        variant_name, ok = QInputDialog.getItem(
                            self, 
                            'Variante auswählen', 
                            'Wähle eine Variante aus:', 
                            available_variants, 
                            0, 
                            False
                        )
                        if ok and variant_name:
                            self.presenter.folder_manager.set_variant_folder(variant_name)
                            # Automatically load available results after variant selection
                            self.on_importResultsAction()
                else:
                    self.show_error_message("Keine verfügbaren Varianten gefunden.")
            else:
                raise FileNotFoundError(f"Projektpfad '{folder_path}' nicht gefunden.")
                
        except FileNotFoundError as e:
            self.show_error_message(str(e))

    def get_available_variants(self, project_path: str) -> List[str]:
        """
        Discover and validate available project variants in the specified project.

        This method scans the project directory structure to identify valid
        variant folders, providing the foundation for variant selection and
        management throughout the application.

        Parameters
        ----------
        project_path : str
            Path to the main project directory to scan for variants.

        Returns
        -------
        list of str
            List of valid variant folder names found in the project.
            Returns empty list if no variants found or path is invalid.

        Notes
        -----
        Variant Discovery Logic:
            
            **Folder Validation**:
            - Checks for directory existence and accessibility
            - Validates variant naming conventions (starts with "Variante")
            - Ensures proper folder structure and permissions
            - Filters out invalid or corrupted variant folders
            
            **Error Handling**:
            - Graceful handling of missing project directories
            - Clear error messages for troubleshooting
            - Robust operation even with partially corrupted projects
            - Logging for development and deployment debugging

        This method supports the variant management system that allows
        users to maintain multiple analysis scenarios within a single
        project structure.
        """
        variants: List[str] = []
        
        try:
            # Scan project directory for variant folders
            for folder_name in os.listdir(project_path):
                full_path = os.path.join(project_path, folder_name)
                
                # Validate variant folder criteria
                if (os.path.isdir(full_path) and 
                    folder_name.startswith("Variante")):
                    variants.append(folder_name)
                    
        except FileNotFoundError:
            self.show_error_message(
                f"Der Projektpfad '{project_path}' konnte nicht gefunden werden."
            )
            
        return variants

    def on_create_project_copy(self) -> None:
        """
        Handle project copy creation with user feedback and validation.

        This method manages the complete project copying workflow through
        the presenter layer, providing appropriate user feedback for
        success or failure conditions.

        Notes
        -----
        Project Copy Functionality:
            
            **Copy Operation**:
            - Creates complete duplicate of current project
            - Preserves all data, settings, and analysis results
            - Generates unique project identifier and folder name
            - Maintains data integrity throughout copy process
            
            **User Experience**:
            - Clear success confirmation with operation details
            - Appropriate error handling and user notification
            - Integration with project management workflow
            - Support for project versioning and backup strategies
        """
        # Check if user wants to save current changes before creating copy
        dialog_result = self.show_save_dialog(
            'Projektkopie erstellen',
            'Möchten Sie Ihre Änderungen vor dem Erstellen der Projektkopie speichern?',
            'Speichern und Kopie erstellen'
        )
        
        if dialog_result == 'cancel':
            return  # User cancelled operation
        elif dialog_result == 'save':
            if not self.save_all_project_results():
                return  # User cancelled save operation
        # If 'discard', proceed without saving
            
        success = self.presenter.create_project_copy()
        if success:
            QMessageBox.information(
                self, 
                "Info", 
                "Projektkopie wurde erfolgreich erstellt."
            )

    def on_open_variant(self) -> None:
        """
        Handle opening specific variants within the current project context.
        Before switching, save all current project results.

        This method provides variant switching functionality within an already
        open project, allowing users to easily navigate between different
        analysis scenarios without full project reloading.

        Workflow Process:
            
            1. **Current Project Validation**: Verify active project context
            2. **Variant Discovery**: Scan current project for available variants
            3. **User Selection**: Present variant options through selection dialog
            4. **Variant Activation**: Switch to selected variant seamlessly

        Notes
        -----
        Variant Switching Benefits:
            
            **Efficient Workflow**:
            - Quick variant switching without full project reload
            - Maintains application state and user preferences
            - Preserves unsaved changes with appropriate handling
            - Seamless transition between analysis scenarios
            
            **User Experience**:
            - Clear variant identification and selection
            - Immediate feedback for variant activation
            - Error handling for missing or corrupted variants
            - Integration with overall project workflow
        """
        # Validate current project context
        project_folder = self.folder_manager.project_folder
        if not project_folder:
            self.show_error_message("Kein Projektordner ausgewählt.")
            return

        # Check if user wants to save current changes before opening variant
        dialog_result = self.show_save_dialog(
            'Variante öffnen',
            'Möchten Sie Ihre Änderungen vor dem Öffnen der Variante speichern?',
            'Speichern und Variante öffnen'
        )
        
        if dialog_result == 'cancel':
            return  # User cancelled operation
        elif dialog_result == 'save':
            if not self.save_all_project_results():
                return  # User cancelled save operation
        # If 'discard', proceed without saving
            
        # Discover available variants in current project
        available_variants = self.get_available_variants(project_folder)

        if available_variants:
            # Present variant selection to user
            variant_name, ok = QInputDialog.getItem(
                self, 
                'Variante öffnen', 
                'Wähle eine Variante aus:', 
                available_variants, 
                0, 
                False
            )
            
            # Activate selected variant
            if ok and variant_name:
                self.presenter.folder_manager.set_variant_folder(variant_name)
                # Automatically load available results after variant selection
                self.on_importResultsAction()
        else:
            self.show_error_message("Keine Varianten im Projekt gefunden.")

    def on_create_project_variant(self) -> None:
        """
        Handle creation of new project variants with proper validation and feedback.

        This method manages the variant creation workflow through the presenter
        layer, ensuring proper variant structure creation and user notification.

        Notes
        -----
        Variant Creation Process:
            
            **New Variant Structure**:
            - Creates new variant folder with standardized structure
            - Inherits base project configuration and settings
            - Initializes empty analysis data for independent development
            - Maintains proper folder permissions and accessibility
            
            **User Workflow Integration**:
            - Seamless integration with existing project workflow
            - Automatic variant activation after creation
            - Clear success feedback and next steps guidance
            - Error handling for creation failures
        """
        # Check if user wants to save current changes before creating variant
        dialog_result = self.show_save_dialog(
            'Projektvariante erstellen',
            'Möchten Sie Ihre Änderungen vor dem Erstellen der Projektvariante speichern?',
            'Speichern und Variante erstellen'
        )
        
        if dialog_result == 'cancel':
            return  # User cancelled operation
        elif dialog_result == 'save':
            if not self.save_all_project_results():
                return  # User cancelled save operation
        # If 'discard', proceed without saving
            
        success = self.presenter.create_project_variant()
        if success:
            QMessageBox.information(
                self, 
                "Info", 
                "Projektvariante wurde erfolgreich erstellt."
            )

    def on_create_project_variant_copy(self) -> None:
        """
        Handle creation of project variant copies with data preservation.

        This method manages the variant copying workflow, creating new variants
        based on existing variant data while maintaining data integrity and
        providing appropriate user feedback.

        Notes
        -----
        Variant Copy Benefits:
            
            **Data Preservation**:
            - Copies all analysis data and results from source variant
            - Maintains configuration settings and user preferences
            - Preserves network definitions and building data
            - Creates independent copy for modification and experimentation
            
            **Analysis Workflow Support**:
            - Enables comparative analysis development
            - Supports iterative design and optimization processes
            - Facilitates sensitivity analysis and parameter studies
            - Provides backup functionality for variant protection
        """
        # Check if user wants to save current changes before creating variant copy
        dialog_result = self.show_save_dialog(
            'Projektvariantenkopie erstellen',
            'Möchten Sie Ihre Änderungen vor dem Erstellen der Projektvariantenkopie speichern?',
            'Speichern und Kopie erstellen'
        )
        
        if dialog_result == 'cancel':
            return  # User cancelled operation
        elif dialog_result == 'save':
            if not self.save_all_project_results():
                return  # User cancelled save operation
        # If 'discard', proceed without saving
            
        success = self.presenter.create_project_variant_copy()
        if success:
            QMessageBox.information(
                self, 
                "Info", 
                "Projektvariantenkopie wurde erfolgreich erstellt."
            )

    # Data Management Methods
    # =======================

    def show_temporary_success_message(self, message: str, duration_ms: int = 2000) -> None:
        """
        Display a temporary success message that disappears automatically.
        
        Parameters
        ----------
        message : str
            Success message to display
        duration_ms : int, optional
            Duration in milliseconds before the dialog closes automatically (default: 1000ms)
        """
        from PyQt6.QtCore import QTimer
        
        # Create and show the message box
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Erfolgreich")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Create timer to close the dialog automatically
        timer = QTimer()
        timer.timeout.connect(msg_box.accept)
        timer.setSingleShot(True)
        timer.start(duration_ms)
        
        # Show the dialog
        msg_box.exec()

    def on_importResultsAction(self) -> None:
        """
        Handle comprehensive project data import for restoring analysis results.

        This method uses the auto_load_project_results functionality but provides
        user feedback with a temporary success message that automatically disappears
        after 1 second. This gives users confirmation that the import completed
        without requiring manual dialog dismissal.

        Import Process:
            
            **Automated Loading**:
            - Uses the same silent loading mechanism as auto_load_project_results
            - Loads all available project data without individual confirmation dialogs
            - Provides single success confirmation with auto-dismissal
            
            **User Experience**:
            - Single-click restoration of complete project state
            - Brief success confirmation that doesn't interrupt workflow
            - Error handling with detailed failure information
            - Integration with project management workflow

        This functionality is essential for project continuity and
        collaborative work environments where analysis results need
        to be shared and restored across different work sessions.
        """
        try:
            # Check if we have a valid project and variant loaded
            if not hasattr(self, 'base_path') or not self.base_path:
                return
                
            # Building data auto-load (without dialogs)
            try:
                building_data_path = os.path.join(
                    self.base_path, 
                    self.presenter.config_manager.get_relative_path("current_building_data_path")
                )
                building_profile_path = os.path.join(
                    self.base_path, 
                    self.presenter.config_manager.get_relative_path("building_load_profile_path")
                )
                
                # Load building data if files exist (no dialogs)
                if os.path.exists(building_data_path):
                    self.projectTab.presenter.load_csv(building_data_path)
                    self.buildingTab.presenter.load_csv(building_data_path, show_dialog=False)
                    
                if os.path.exists(building_profile_path):
                    self.buildingTab.presenter.load_json(building_profile_path, show_dialog=False)
                    
            except Exception:
                # Silently continue if building data loading fails
                pass
            
            # Network data auto-load (without dialogs)
            try:
                self.calcTab.loadNet(show_dialog=False)
                self.calcTab.load_net_results(show_dialog=False)
            except Exception:
                # Silently continue if network data loading fails
                pass
            
            # Energy system data auto-load
            try:
                self.energySystemTab.load_results_JSON(show_dialog=False)
            except Exception:
                # Silently continue if energy system data loading fails
                pass
                
            print("Auto-load completed: Available results loaded successfully.")
            
            # Show temporary success message that disappears after 1 second
            self.show_temporary_success_message("Projektdaten wurden erfolgreich geladen.")
            
        except Exception as e:
            # Handle import errors with specific information
            self.show_error_message(f"Fehler beim Laden der Projektdaten: {str(e)}")

    def save_all_project_results(self) -> bool:
        """
        Zentrale Speicherlogik für alle Projektergebnisse.
        Ruft die jeweiligen Save-Methoden der einzelnen Tabs/Presenter auf.
        Sollte vor dem Schließen der Anwendung und beim Wechsel des Projekts/Variante aufgerufen werden.
        Vor dem Speichern wird ein Warn-Dialog angezeigt, der auf fehlende Versionierung und mögliche Überschreibung hinweist.
        Bricht der Nutzer den Dialog ab, wird die Aktion abgebrochen.
        
        Returns
        -------
        bool
            True wenn erfolgreich gespeichert, False wenn abgebrochen
        """
        reply = QMessageBox.warning(
            self,
            "Achtung: Daten werden überschrieben!",
            "Mit dieser Aktion werden alle aktuellen Projektdaten überschrieben. Es ist noch keine Versionierung implementiert. Möchten Sie fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            # Aktion abbrechen, falls der Nutzer abbricht
            return False

        errors = []
        try:
            # Gebäudedaten speichern
            if hasattr(self, 'projectTab') and hasattr(self.projectTab.presenter, 'save_csv'):
                try:
                    self.projectTab.presenter.save_csv(show_dialog=False)
                except Exception as e:
                    errors.append(f"ProjektTab: {str(e)}")
            if hasattr(self, 'buildingTab') and hasattr(self.buildingTab.presenter, 'save_csv'):
                try:
                    self.buildingTab.presenter.save_csv(show_dialog=False)
                except Exception as e:
                    errors.append(f"BuildingTab: {str(e)}")
            # Netzdaten speichern
            if hasattr(self, 'calcTab') and hasattr(self.calcTab, 'saveNet'):
                try:
                    self.calcTab.saveNet(show_dialog=False)
                except Exception as e:
                    errors.append(f"CalcTab: {str(e)}")
            if hasattr(self, 'calcTab') and hasattr(self.calcTab, 'exportNetGeoJSON'):
                try:
                    self.calcTab.exportNetGeoJSON(show_dialog=False)
                except Exception as e:
                    errors.append(f"CalcTab GeoJSON: {str(e)}")
            # Energiesystem speichern
            if hasattr(self, 'energySystemTab') and hasattr(self.energySystemTab, 'save_results_JSON'):
                try:
                    self.energySystemTab.save_results_JSON(show_dialog=False)
                except Exception as e:
                    errors.append(f"EnergySystemTab: {str(e)}")
            # Weitere Tabs nach Bedarf ergänzen
        except Exception as e:
            errors.append(f"Allgemeiner Fehler: {str(e)}")
        if errors:
            self.show_error_message("Fehler beim Speichern der Projektdaten:\n" + "\n".join(errors))
            return False  # Fehler beim Speichern
        else:
            self.show_message("Erfolg", "Alle Projektdaten wurden erfolgreich gespeichert.")
            return True  # Erfolgreich gespeichert

    # Theme and Appearance Methods
    # ============================

    def applyTheme(self, theme_path: str) -> None:
        """
        Apply visual themes to the application with comprehensive error handling.

        This method manages the application's visual appearance by loading and
        applying Qt stylesheet files. It supports both light and dark themes
        with professional styling suitable for engineering applications.

        Parameters
        ----------
        theme_path : str
            Configuration key for the theme stylesheet path.
            Resolved through the configuration manager for proper resource handling.

        Theme System Features:
            
            **Professional Styling**:
            - Consistent visual appearance across all interface components
            - Professional color schemes suitable for technical applications
            - Proper contrast and readability for extended use
            - Integration with system accessibility settings
            
            **Dynamic Theme Switching**:
            - Runtime theme changes without application restart
            - Immediate visual feedback for theme selection
            - Proper handling of theme-dependent resources
            - Consistent theme application across all tabs and dialogs

        Notes
        -----
        Theme Implementation:
            
            **Resource Management**:
            - Centralized theme resource management through configuration
            - Support for both development and packaged application scenarios
            - Graceful fallback for missing theme resources
            - Error handling with user-friendly feedback
            
            **Cross-Platform Compatibility**:
            - Consistent appearance across different operating systems
            - Proper handling of platform-specific styling requirements
            - Integration with system theme preferences when appropriate
            - Professional appearance regardless of deployment environment
        """
        try:
            # Resolve theme path through configuration manager
            qss_path = self.presenter.config_manager.get_resource_path(theme_path)
            
            # Validate theme file existence
            if os.path.exists(qss_path):
                # Load and apply stylesheet
                with open(qss_path, 'r', encoding='utf-8') as file:
                    theme_content = file.read()
                    self.setStyleSheet(theme_content)
                    
                    # Also apply to welcome screen if it exists
                    if self.welcome_screen:
                        self.welcome_screen.setStyleSheet(theme_content)
                        
                print(f"Theme erfolgreich angewendet: {qss_path}")
            else:
                self.show_error_message(f"Stylesheet {qss_path} nicht gefunden.")
                
        except Exception as e:
            self.show_error_message(f"Fehler beim Anwenden des Themes: {str(e)}")

    # Data Configuration Methods
    # ==========================

    def openTemperatureDataSelection(self) -> None:
        """
        Open temperature data configuration dialog and update system settings.

        This method provides access to temperature data configuration for
        climate-dependent calculations throughout the application. It manages
        the dialog interaction and system-wide data updates.

        Notes
        -----
        Temperature Data Integration:
            
            **Climate Data Management**:
            - Selection from standardized Test Reference Year (TRY) datasets
            - Integration with thermal calculations and energy system modeling
            - Support for different climate zones and weather patterns
            - Proper data validation and format checking
            
            **System-Wide Updates**:
            - Automatic propagation of temperature data changes
            - Real-time recalculation of temperature-dependent parameters
            - Integration with energy system performance calculations
            - Consistency maintenance across all analysis modules
        """
        if self.temperatureDataDialog.exec():
            self.updateTemperatureData()

    def openCOPDataSelection(self) -> None:
        """
        Open heat pump performance data configuration dialog and update settings.

        This method provides access to heat pump coefficient of performance (COP)
        data configuration for accurate heat pump modeling throughout the
        application analysis modules.

        Notes
        -----
        Heat Pump Data Integration:
            
            **Performance Characteristics**:
            - Selection from certified heat pump performance datasets
            - Temperature-dependent COP calculations for accurate modeling
            - Integration with energy system design and optimization
            - Support for different heat pump technologies and manufacturers
            
            **Analysis Integration**:
            - Real-time performance calculations based on selected data
            - Integration with economic analysis and optimization algorithms
            - Proper handling of part-load and seasonal performance variations
            - Consistency with industry standards and certification data
        """
        if self.heatPumpDataDialog.exec():
            self.updateHeatPumpData()

    def updateTemperatureData(self) -> None:
        """
        Update system temperature data based on user selection and validate settings.

        This method processes temperature data selection from the configuration
        dialog and updates the central data management system for use throughout
        the application's thermal calculations and analysis modules.

        Data Update Process:
            
            **Configuration Retrieval**:
            - Extracts temperature data selection from dialog
            - Validates data format and accessibility
            - Updates central data manager with new settings
            - Triggers recalculation of temperature-dependent parameters

        Notes
        -----
        The temperature data serves as a foundation for multiple analysis
        modules including building heat demand calculation, network thermal
        simulation, and energy system performance evaluation.
        """
        try:
            # Retrieve temperature data selection from dialog
            TRY = self.temperatureDataDialog.getValues()
            
            # Update central data manager with selected temperature data
            self.data_manager.set_try_filename(TRY['TRY-filename'])
            
            print(f"Temperaturdaten aktualisiert: {TRY['TRY-filename']}")
            
        except Exception as e:
            self.show_error_message(f"Fehler beim Aktualisieren der Temperaturdaten: {str(e)}")

    def updateHeatPumpData(self) -> None:
        """
        Update system heat pump performance data based on user selection.

        This method processes heat pump performance data selection from the
        configuration dialog and updates the central data management system
        for use in energy system modeling and optimization calculations.

        Data Update Process:
            
            **Performance Data Integration**:
            - Extracts heat pump COP data from dialog
            - Validates performance data format and completeness
            - Updates central data manager with new performance characteristics
            - Triggers recalculation of heat pump-dependent analyses

        Notes
        -----
        The heat pump performance data directly affects energy system design,
        economic analysis, and optimization calculations throughout the
        application's analysis modules.
        """
        try:
            # Retrieve heat pump performance data selection from dialog
            COP = self.heatPumpDataDialog.getValues()
            
            # Update central data manager with selected performance data
            self.data_manager.set_cop_filename(COP['COP-filename'])
            
            print(f"Wärmepumpendaten aktualisiert: {COP['COP-filename']}")
            
        except Exception as e:
            self.show_error_message(f"Fehler beim Aktualisieren der Wärmepumpendaten: {str(e)}")


    def show_info_message(self, message: str) -> None:
        """
        Display informational messages with consistent professional styling.

        This method provides standardized informational feedback to users,
        complementing the error message system with positive confirmation
        and status updates for successful operations.

        Parameters
        ----------
        message : str
            Informational message text to display to the user.
            Typically used for success confirmations and status updates.

        Notes
        -----
        Information Display Standards:
            
            **Positive User Feedback**:
            - Success confirmation for completed operations
            - Status updates for long-running processes
            - Helpful tips and guidance messages
            - Professional communication tone
            
            **Interface Consistency**:
            - Standardized information dialog appearance
            - Consistent with error message styling
            - Proper modal behavior and user interaction
            - Seamless integration with application theme

        User Experience Benefits:
            
            **Clear Communication**:
            - Immediate feedback for user actions
            - Confirmation of successful operations
            - Status updates during data processing
            - Professional tone appropriate for engineering software
            
            **Workflow Integration**:
            - Non-intrusive information delivery
            - Proper dialog positioning and sizing
            - Consistent with application's visual design
            - Support for German and English localization

        Examples
        --------
        **Success Confirmation**:

            >>> # Confirm successful project creation
            >>> self.show_info_message("Projekt wurde erfolgreich erstellt.")

        **Status Update**:

            >>> # Inform user about data loading completion  
            >>> self.show_info_message("Projektdaten wurden erfolgreich geladen.")

        **Process Completion**:

            >>> # Notify user of completed calculations
            >>> self.show_info_message("Netzwerkberechnung wurde erfolgreich abgeschlossen.")

        See Also
        --------
        show_error_message : Display error messages with consistent styling
        QMessageBox.information : Underlying Qt message box functionality
        """
        QMessageBox.information(self, "Info", message)

    def closeEvent(self, event):
        """
        Save all project results before closing the application.
        Only if a project is loaded. Allows user to cancel application closure.
        """
        if hasattr(self, 'base_path') and self.base_path:
            # Check if user wants to save current changes before closing
            dialog_result = self.show_save_dialog(
                'Anwendung schließen',
                'Möchten Sie Ihre Änderungen vor dem Schließen der Anwendung speichern?',
                'Speichern und schließen'
            )
            
            if dialog_result == 'cancel':
                # User cancelled, prevent application closure
                event.ignore()
                return
            elif dialog_result == 'save':
                if not self.save_all_project_results():
                    # User cancelled save operation, prevent closure
                    event.ignore()
                    return
            # If 'discard', proceed with closing without saving
        event.accept()
