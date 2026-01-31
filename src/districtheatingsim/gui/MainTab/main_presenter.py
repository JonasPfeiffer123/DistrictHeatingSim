"""
Main presenter module for DistrictHeatingSim application.

Implements the Presenter component of the MVP pattern, handling business logic
for project management, variant creation, and coordination between view and
data management layers.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import shutil
from typing import Optional, Tuple

from PyQt6.QtWidgets import QInputDialog

class HeatSystemPresenter:
    """
    Presenter for district heating project management (MVP pattern).

    Coordinates between view and data management layers, handling business logic
    for project creation, variant management, and folder structure operations.

    :param view: Main application view component
    :type view: HeatSystemDesignGUI
    :param folder_manager: Project folder management
    :type folder_manager: ProjectFolderManager
    :param data_manager: Central data storage
    :type data_manager: DataManager
    :param config_manager: Configuration management
    :type config_manager: ProjectConfigManager
    """

    def __init__(self, view, folder_manager, data_manager, config_manager):
        """
        Initialize presenter with manager dependencies.

        :param view: Main application view
        :type view: HeatSystemDesignGUI
        :param folder_manager: Project folder manager
        :type folder_manager: ProjectFolderManager
        :param data_manager: Data manager
        :type data_manager: DataManager
        :param config_manager: Configuration manager
        :type config_manager: ProjectConfigManager
        """
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Connect the model signals directly to the view updates
        self.folder_manager.project_folder_changed.connect(self.view.update_project_folder_label)

    def create_new_project(self, folder_path: str, project_name: str) -> bool:
        """
        Create new district heating project with standardized folder structure.

        Creates project with "Eingangsdaten allgemein", "Definition Quartier IST",
        and "Variante 1" folders. Initializes building data CSV and registers
        project with folder manager.

        :param folder_path: Base directory for new project
        :type folder_path: str
        :param project_name: Name of project folder
        :type project_name: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        # Validate input parameters
        if not folder_path or not project_name:
            return False
            
        try:
            # Create main project folder
            full_path = os.path.join(folder_path, project_name)
            os.makedirs(full_path)
            
            # Define standardized folder structure for district heating projects
            subdirs = {
                "Eingangsdaten allgemein": [],  # General input data
                "Definition Quartier IST": [],  # Current district definition
                "Variante 1": [                # First analysis variant
                    "Ergebnisse",               # Results and outputs
                    "Gebäudedaten",             # Building data
                    "Lastgang",                 # Load profiles
                    "Wärmenetz"                 # Heating network data
                ]
            }
            
            # Create main folders and their respective subfolders
            for main_folder, subfolders in subdirs.items():
                main_folder_path = os.path.join(full_path, main_folder)
                os.makedirs(main_folder_path)
                
                # Create subfolders for variant organization
                for subfolder in subfolders:
                    os.makedirs(os.path.join(main_folder_path, subfolder))

            # Register project with folder manager
            self.folder_manager.set_project_folder(full_path)

            # Activate the newly created "Variante 1" for immediate use
            variant_folder = os.path.join(full_path, "Variante 1")
            if os.path.exists(variant_folder):
                self.folder_manager.set_variant_folder("Variante 1")
            else:
                self.view.show_error_message("Fehler: Variante 1 konnte nicht gefunden werden.")
                return False

            # Create initial CSV file for building data in project tab
            csv_path = os.path.join(
                self.folder_manager.get_variant_folder(), 
                self.config_manager.get_relative_path("current_building_data_path")
            )
            self.view.projectTab.presenter.create_csv(csv_path)
            
            return True
            
        except Exception as e:
            # Provide user-friendly error feedback
            self.view.show_error_message(f"Ein Fehler ist aufgetreten: {e}")
            return False

    def open_existing_project(self, folder_path: str) -> None:
        """
        Open existing district heating project.

        Registers project folder with folder manager, triggering automatic
        synchronization of all application components.

        :param folder_path: Path to existing project folder
        :type folder_path: str
        """
        if folder_path:
            self.folder_manager.set_project_folder(folder_path)

    def create_project_copy(self) -> bool:
        """
        Create complete copy of current project with user-specified name.

        Prompts user for new project name via dialog, then creates exact
        duplicate including all data files, analysis results, and structure.
        Automatically activates the copied project.

        :return: True if successful, False if cancelled or failed
        :rtype: bool
        """
        # Get base directory for project creation
        base_dir = os.path.dirname(self.folder_manager.project_folder)

        # Show interactive dialog for new project name input
        current_project_name = os.path.basename(self.folder_manager.project_folder)
        default_name = f"{current_project_name} - Kopie"
        
        new_project_name, ok = QInputDialog.getText(
            self.view, 
            'Projektkopie erstellen', 
            'Geben Sie einen neuen Namen für das Projekt ein:', 
            text=default_name
        )

        # Process user input and create project copy
        if ok and new_project_name:
            new_project_path = os.path.join(base_dir, new_project_name)
            
            # Check for naming conflicts
            if not os.path.exists(new_project_path):
                try:
                    # Create complete copy of project directory
                    shutil.copytree(self.folder_manager.project_folder, new_project_path)

                    # Register copied project as active project
                    self.folder_manager.set_project_folder(new_project_path)
                    
                    # Search for variants in copied project
                    variants = [
                        folder for folder in os.listdir(new_project_path) 
                        if "Variante" in folder
                    ]
                    
                    if variants:
                        # Activate first available variant
                        self.folder_manager.set_variant_folder(variants[0])
                    else:
                        # Handle projects without variants
                        default_variant_path = os.path.join(new_project_path, "Variante 1")
                        if os.path.exists(default_variant_path):
                            self.folder_manager.set_variant_folder("Variante 1")
                        else:
                            # Set project folder without specific variant
                            self.folder_manager.set_project_folder(new_project_path)

                    return True
                    
                except Exception as e:
                    # Provide detailed error feedback
                    self.view.show_error_message(f"Ein Fehler ist aufgetreten: {str(e)}")
                    return False
            else:
                # Handle naming conflicts
                self.view.show_error_message(
                    f"Ein Projekt mit dem Namen '{new_project_name}' existiert bereits."
                )
                return False
        else:
            # Handle user cancellation
            self.view.show_error_message("Projektkopie wurde abgebrochen.")
            return False

    def create_project_variant(self) -> bool:
        """
        Create new analysis variant within current project.

        Creates sequentially numbered variant (Variante X) with standardized
        subfolder structure (Ergebnisse, Gebäudedaten, Lastgang, Wärmenetz).
        Automatically activates new variant.

        :return: True if successful, False if failed
        :rtype: bool
        """
        
        # Get base project directory for variant creation
        base_dir = self.folder_manager.project_folder
        variant_num = 1

        # Find next available variant number
        while True:
            new_variant_name = f"Variante {variant_num}"
            new_variant_path = os.path.join(base_dir, new_variant_name)
            if not os.path.exists(new_variant_path):
                break
            variant_num += 1

        try:
            # Create standardized variant folder structure
            variant_subdirs = [
                "Ergebnisse",    # Analysis results and outputs
                "Gebäudedaten",  # Building data and characteristics
                "Lastgang",      # Load profiles and demand data
                "Wärmenetz"      # Heating network design and data
            ]
            
            # Create main variant folder and all subdirectories
            for subdir in variant_subdirs:
                os.makedirs(os.path.join(new_variant_path, subdir))
            
            # Activate newly created variant
            self.folder_manager.set_variant_folder(new_variant_name)
            return True
            
        except Exception as e:
            # Provide detailed error feedback
            self.view.show_error_message(f"Fehler beim Erstellen der Variante: {e}")
            return False

    def create_project_variant_copy(self) -> bool:
        """
        Create exact copy of current variant with sequential numbering.

        Duplicates all data, analysis results, and configuration settings.
        Automatically activates new variant copy.

        :return: True if successful, False if failed
        :rtype: bool
        """
        # Get base directory for variant creation
        base_dir = os.path.dirname(self.folder_manager.get_variant_folder())
        variant_num = 1

        # Find next available variant number
        while True:
            new_variant_name = f"Variante {variant_num}"
            new_variant_path = os.path.join(base_dir, new_variant_name)
            if not os.path.exists(new_variant_path):
                break
            variant_num += 1

        try:
            # Create complete copy of current variant directory
            shutil.copytree(self.folder_manager.get_variant_folder(), new_variant_path)
            
            # Activate newly created variant copy
            self.folder_manager.set_variant_folder(new_variant_name)
            return True
            
        except Exception as e:
            # Provide detailed error feedback
            self.view.show_error_message(f"Fehler beim Kopieren der Variante: {e}")
            return False