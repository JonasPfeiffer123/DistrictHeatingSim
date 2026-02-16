"""
Main GUI view module for DistrictHeatingSim application.

This module implements the main window with a multi-tab interface for district
heating system simulation. Follows the View component of the MVP pattern,
managing UI elements, menu system, theme management, and tab coordination.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
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
    Main application window with multi-tab interface for district heating analysis.

    Implements the View component of the MVP pattern, managing UI elements,
    menu system, theme switching, and tab coordination for the complete
    district heating workflow.

    :param folder_manager: Project folder management system
    :type folder_manager: ProjectFolderManager
    :param data_manager: Central data storage system
    :type data_manager: DataManager
    
    .. note::
        Tabs can be dynamically shown/hidden via the menu system to
        customize the workflow.
    """

    def __init__(self, folder_manager, data_manager):
        """
        Initialize main application window with manager dependencies.

        Sets up basic window structure, defers UI creation until presenter is set.

        :param folder_manager: Project folder management system
        :type folder_manager: ProjectFolderManager
        :param data_manager: Central data management system
        :type data_manager: DataManager
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
        Set presenter and initialize complete user interface.

        Completes MVP pattern setup by connecting presenter and triggering
        full UI initialization including menus, tabs, dialogs, and theme.

        :param presenter: Business logic controller
        :type presenter: HeatSystemPresenter
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
        Show standardized save dialog for project operations.
        
        :param title: Dialog window title
        :type title: str
        :param info_text: Informative text explaining the operation
        :type info_text: str
        :param accept_text: Text for accept button
        :type accept_text: str
        :return: User choice: 'save', 'discard', 'cancel', or 'continue'
        :rtype: str
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
        Initialize menu bar with File, Data, Theme, and Tabs menus.

        Creates professional menu system with project management, recent projects,
        variant handling, data configuration, and tab visibility control.
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
        Initialize multi-tab interface for district heating analysis workflow.

        Creates tabs for project definition, building data, network visualization,
        network calculation, energy system design, and variant comparison.
        Supports dynamic tab visibility control.
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
        Initialize application logo and window icon.

        Loads logo via ConfigManager with fallback paths for both development
        and packaged application scenarios.
        """
        try:
            # Primary logo loading through configuration manager
            logo_path = self.presenter.config_manager.get_resource_path(self.presenter.config_manager.get_relative_path('logo_path'))
            
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
                'images/logo.png',
                'images\\logo.png',
                os.path.join('images', 'logo.png'),
                os.path.join(os.path.dirname(__file__), 'images', 'logo.png'),
                os.path.join(os.path.dirname(__file__), '..', 'images', 'logo.png'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'images', 'logo.png')
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
        Update project folder status label with current project path.

        :param base_path: Current project/variant folder path
        :type base_path: str
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
        Display standardized error message dialog.

        :param message: Error message text to display
        :type message: str
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

        Prompts for save if project loaded, collects project name, and creates
        standardized project structure via presenter.
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
        # If no project is loaded, use a sensible default or ask user
        if self.base_path:
            folder_path = os.path.dirname(os.path.dirname(self.base_path))
        else:
            # No project loaded - ask user to select parent folder
            # Try to use the most recent project's parent directory
            start_dir = None
            if hasattr(self, 'presenter') and self.presenter and self.presenter.folder_manager:
                try:
                    config_manager = self.presenter.folder_manager.config_manager
                    recent_projects = config_manager.get_recent_projects()
                    if recent_projects:
                        # Use the parent directory of the most recent project
                        start_dir = os.path.dirname(recent_projects[0])
                except:
                    pass
            
            # Fallback to Documents folder if no recent projects
            if not start_dir:
                default_dir = os.path.expanduser("~/Documents")
                if os.path.exists(default_dir):
                    start_dir = default_dir
                else:
                    start_dir = os.path.expanduser("~")
            
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Übergeordneten Ordner für neues Projekt auswählen",
                start_dir
            )
        
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

        Prompts for save, discovers variants, and loads selected project.

        :param folder_path: Direct path to project folder (optional)
        :type folder_path: str or None
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
        Discover available project variants in specified project directory.

        Scans project directory for folders starting with "Variante".

        :param project_path: Path to main project directory
        :type project_path: str
        :return: List of valid variant folder names
        :rtype: list of str
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
        Handle project copy creation with user feedback.

        Prompts for save, creates complete project duplicate via presenter,
        and displays success message.
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
        Handle variant selection within current project.

        Prompts for save, discovers variants, and switches to selected variant.
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
        Handle creation of new project variant.

        Prompts for save, creates new variant via presenter, and displays
        success message.
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
        Handle creation of variant copy with data preservation.

        Prompts for save, creates variant copy via presenter, and displays
        success message.
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
        Display auto-dismissing success message.
        
        :param message: Success message to display
        :type message: str
        :param duration_ms: Display duration in milliseconds (default: 2000)
        :type duration_ms: int
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
        Load all available project data and results.

        Silently loads building data, network data, and energy system results
        without individual confirmation dialogs. Shows single success message.
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
        Apply visual theme to application.

        Loads and applies Qt stylesheet with fallback for missing resources.

        :param theme_path: Configuration key for theme stylesheet path
        :type theme_path: str
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

        Displays dialog for TRY (Test Reference Year) selection and triggers
        system-wide temperature data update.
        """
        if self.temperatureDataDialog.exec():
            self.updateTemperatureData()

    def openCOPDataSelection(self) -> None:
        """
        Open heat pump COP data configuration dialog and update settings.

        Displays dialog for heat pump performance data selection and triggers
        system-wide COP data update.
        """
        if self.heatPumpDataDialog.exec():
            self.updateHeatPumpData()

    def updateTemperatureData(self) -> None:
        """
        Update system temperature data based on user selection.

        Retrieves TRY filename from dialog and updates data manager.
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

        Retrieves COP filename from dialog and updates data manager.
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
        Display informational message dialog.

        :param message: Informational text to display
        :type message: str
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
