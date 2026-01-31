"""
Main entry point for the DistrictHeatingSim application.

This module provides a PyQt6-based GUI application for planning and optimizing
district heating networks. It implements the Model-View-Presenter (MVP) pattern
with clear separation between data management, business logic, and user interface.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

The application provides:

    - Project management with variant support
    - Building heat demand calculation using BDEW profiles
    - Network generation from GIS data (OpenStreetMap)
    - Thermohydraulic simulation with pandapipes
    - Heat generator sizing and economic analysis
    - Multi-variant comparison

Architecture:

    - **Model**: ProjectConfigManager, DataManager, ProjectFolderManager
    - **View**: HeatSystemDesignGUI (main window with tab-based interface)
    - **Presenter**: HeatSystemPresenter (coordinates business logic)

.. note::
    The application uses time-based theme selection (light/dark mode) and
    supports Windows taskbar integration when available.
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
    Initialize and launch the DistrictHeatingSim application.
    
    This function sets up the Qt application, initializes all managers (config,
    data, folder), creates the main GUI window, connects the MVP components,
    applies the theme, and starts the event loop.
    
    :raises SystemExit: Normal application termination
    :raises Exception: Caught by global exception handler for user-friendly error reporting
    
    .. note::
        Windows-specific taskbar integration is applied if available but
        fails gracefully on other platforms.
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
    import traceback
    
    # Check if stdin is available (console window exists)
    has_console = sys.stdin is not None and hasattr(sys.stdin, 'fileno')
    
    try:
        if has_console:
            print("DistrictHeatingSim wird gestartet...")
            print("-" * 80)
        main()
    except Exception as e:
        if has_console:
            print("\n" + "="*80)
            print("FEHLER BEIM START DER ANWENDUNG")
            print("="*80)
            print(f"\nFehlermeldung: {e}\n")
            print("Vollständiger Traceback:")
            print("-"*80)
            traceback.print_exc()
            print("-"*80)
            print("\nDrücken Sie ENTER zum Beenden...")
            try:
                input()
            except:
                pass
        sys.exit(1)
    finally:
        # Keep console open when console window exists (debug builds, development)
        if has_console:
            print("\n" + "="*80)
            print("Drücken Sie ENTER zum Beenden der Konsole...")
            try:
                input()
            except:
                pass