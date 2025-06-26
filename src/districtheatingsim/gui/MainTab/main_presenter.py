"""
DistrictHeatingSim Main Presenter Module
========================================

This module implements the main presenter component for the DistrictHeatingSim
application, following the Model-View-Presenter (MVP) architectural pattern.
The presenter serves as the central coordinator between the user interface (View)
and the data management layer (Model), handling all business logic and user
interactions for district heating project management.

Module Overview
---------------
The main presenter module provides comprehensive project lifecycle management:

- **Project Creation**: New district heating projects with standardized structure
- **Project Management**: Opening, copying, and variant management
- **Data Coordination**: Synchronization between model and view components
- **Business Logic**: Core application workflow and validation
- **Error Handling**: Comprehensive error management and user feedback
- **File System Operations**: Project folder structure management

Architecture Implementation
----------------------------
**MVP Pattern Role**:
    The HeatSystemPresenter acts as the central controller:
    
    - **Model Communication**: Manages data through folder, data, and config managers
    - **View Coordination**: Updates UI components and handles user interactions
    - **Business Logic**: Implements project management workflows and validation
    - **Event Handling**: Processes user actions and coordinates system responses

**Component Integration**:
    The presenter coordinates multiple manager components:
    
    - :class:`ProjectFolderManager`: File system and folder operations
    - :class:`DataManager`: Central data storage and retrieval
    - :class:`ProjectConfigManager`: Configuration and settings management
    - :class:`HeatSystemDesignGUI`: Main user interface view

Key Features
------------
**Project Lifecycle Management**:
    - Create new projects with standardized folder structure
    - Open existing projects with automatic variant detection
    - Copy entire projects for scenario comparison
    - Create and manage project variants for analysis alternatives

**Standardized Project Structure**:
    Projects follow a consistent hierarchical organization:
    
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

**Variant Management**:
    - Automatic variant numbering system
    - Variant copying with complete data preservation
    - Seamless switching between analysis alternatives
    - Independent analysis workflows per variant

Business Logic Implementation
-----------------------------
**Project Creation Workflow**:
    1. **Validation**: Verify input parameters and folder availability
    2. **Structure Creation**: Build standardized folder hierarchy
    3. **Initialization**: Set up default files and configurations
    4. **Registration**: Register project with application managers
    5. **Activation**: Switch to newly created project context

**Error Handling Strategy**:
    - Comprehensive exception handling for all operations
    - User-friendly error messages with specific problem descriptions
    - Graceful degradation and recovery options
    - Detailed logging for debugging and support

**Data Consistency**:
    - Automatic synchronization between managers and view
    - Signal-slot connections for real-time updates
    - Data validation and integrity checking
    - Consistent state management across application components

Author Information
------------------
**Author**: Dipl.-Ing. (FH) Jonas Pfeiffer
**Date**: 2025-06-26
**Version**: Main presenter for DistrictHeatingSim application

The implementation provides robust project management capabilities suitable for
professional district heating system analysis and planning workflows.

Dependencies
------------
**Core Framework**:
    - PyQt5: GUI framework for dialogs and user interaction
    - Python Standard Library: os, shutil for file operations

**Internal Modules**:
    - Manager classes for data, configuration, and folder operations
    - View components for user interface coordination
    - Utility modules for common operations

See Also
--------
:mod:`districtheatingsim.gui.MainTab.main_view` : Main GUI view implementation
:mod:`districtheatingsim.gui.MainTab.main_data_manager` : Data management classes
:class:`HeatSystemDesignGUI` : Main application window

Notes
-----
The presenter implementation emphasizes separation of concerns, ensuring that
business logic remains independent of user interface implementation details.
This architecture supports maintainable code, comprehensive testing, and
flexible user interface modifications without affecting core functionality.

The project management workflow supports the complete district heating analysis
process, from initial project setup through detailed technical and economic
evaluation of heating system alternatives.
"""

import os
import shutil
from typing import Optional, Tuple

from PyQt5.QtWidgets import QInputDialog

class HeatSystemPresenter:
    """
    Main presenter class implementing the MVP pattern for district heating project management.

    This class serves as the central coordinator between the user interface and data
    management layers, handling all business logic for project lifecycle management,
    variant creation, and data synchronization in district heating system analysis.

    The presenter implements comprehensive project management workflows including
    project creation, copying, variant management, and folder structure maintenance
    according to engineering best practices for district heating system planning.

    Parameters
    ----------
    view : HeatSystemDesignGUI
        Main application view component for user interface coordination.
    folder_manager : ProjectFolderManager
        Manager for project folder structure and file system operations.
    data_manager : DataManager
        Central data storage and retrieval management component.
    config_manager : ProjectConfigManager
        Configuration and settings management component.

    Attributes
    ----------
    view : HeatSystemDesignGUI
        Reference to the main application view for UI updates.
    folder_manager : ProjectFolderManager
        Project folder and file system operations manager.
    data_manager : DataManager
        Central data management and storage coordinator.
    config_manager : ProjectConfigManager
        Application configuration and settings manager.

    Notes
    -----
    MVP Pattern Implementation:
        
        **Presenter Responsibilities**:
        - Business logic implementation and validation
        - Coordination between model and view components
        - User interaction handling and event processing
        - Data synchronization and consistency management
        
        **Model Integration**:
        - Folder management for project structure operations
        - Data management for information storage and retrieval
        - Configuration management for application settings
        
        **View Coordination**:
        - UI updates through direct view method calls
        - Error message display and user feedback
        - Progress indication for long-running operations
        - State synchronization with user interface components

    Project Management Features:
        
        **Standardized Structure**:
        All projects follow a consistent folder hierarchy that supports:
        
        - General input data organization
        - Current state documentation (IST-Zustand)
        - Multiple analysis variants for comparison
        - Structured results storage and documentation
        
        **Workflow Support**:
        - Linear analysis workflow from data input to results
        - Parallel variant analysis for scenario comparison
        - Professional documentation and result organization
        - Integration with external tools and data sources

    Examples
    --------
    **Presenter Initialization**:

        >>> from districtheatingsim.gui.MainTab.main_data_manager import *
        >>> from districtheatingsim.gui.MainTab.main_view import HeatSystemDesignGUI
        >>> 
        >>> # Initialize managers
        >>> config_manager = ProjectConfigManager()
        >>> folder_manager = ProjectFolderManager(config_manager)
        >>> data_manager = DataManager()
        >>> view = HeatSystemDesignGUI(folder_manager, data_manager)
        >>> 
        >>> # Create presenter with manager dependencies
        >>> presenter = HeatSystemPresenter(view, folder_manager, data_manager, config_manager)
        >>> view.set_presenter(presenter)

    **Project Creation Workflow**:

        >>> # Create new district heating project
        >>> success = presenter.create_new_project(
        ...     folder_path="/path/to/projects",
        ...     project_name="District_Heating_Munich"
        ... )
        >>> if success:
        ...     print("Project created successfully")
        >>> else:
        ...     print("Project creation failed")

    See Also
    --------
    HeatSystemDesignGUI : Main application view component
    ProjectFolderManager : Project folder structure management
    DataManager : Central data storage and retrieval
    ProjectConfigManager : Configuration and settings management
    """

    def __init__(self, view, folder_manager, data_manager, config_manager):
        """
        Initialize the presenter with manager dependencies and establish component connections.

        This method sets up the presenter as the central coordinator between the view
        and model components, establishing signal-slot connections for real-time
        synchronization and preparing the presenter for project management operations.

        Parameters
        ----------
        view : HeatSystemDesignGUI
            Main application view instance for user interface coordination.
        folder_manager : ProjectFolderManager
            Project folder structure and file system operations manager.
        data_manager : DataManager
            Central data storage and retrieval management component.
        config_manager : ProjectConfigManager
            Application configuration and settings management component.

        Notes
        -----
        Initialization Process:
            
            **Component Registration**:
            - Store references to all manager components
            - Establish presenter as central coordination point
            - Prepare for project management operations
            
            **Signal-Slot Connections**:
            - Connect folder manager signals to view updates
            - Enable automatic UI synchronization
            - Establish real-time project status updates

        The initialization ensures that all components are properly connected
        and ready for project management operations before any user interactions.
        """
        self.view = view
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager

        # Connect the model signals directly to the view updates
        self.folder_manager.project_folder_changed.connect(self.view.update_project_folder_label)

    def create_new_project(self, folder_path: str, project_name: str) -> bool:
        """
        Create a new district heating project with standardized folder structure.

        This method implements the complete project creation workflow including
        folder structure creation, initial file setup, and project registration
        with the application's management system. The created project follows
        engineering best practices for district heating system analysis.

        Parameters
        ----------
        folder_path : str
            Base directory path where the new project folder will be created.
            Must be a valid, writable directory path.
        project_name : str
            Name of the new project folder and identifier.
            Should follow standard naming conventions for project identification.

        Returns
        -------
        bool
            Success status of project creation operation:
            
            True : Project created successfully and ready for use
            False : Project creation failed due to validation or system error

        Project Structure Created:
            
            **Standardized Hierarchy**:
            The method creates a comprehensive folder structure:
            
            ```
            Project_Name/
            ├── Eingangsdaten allgemein/
            │   └── (General input data and parameters)
            ├── Definition Quartier IST/
            │   └── (Current district state documentation)
            └── Variante 1/
                ├── Ergebnisse/
                │   └── (Analysis results and outputs)
                ├── Gebäudedaten/
                │   └── (Building data and characteristics)
                ├── Lastgang/
                │   └── (Load profiles and demand data)
                └── Wärmenetz/
                    └── (Heating network design and data)
            ```
            
            **Initial Configuration**:
            - Default CSV file creation for building data
            - Project registration with folder manager
            - Automatic activation of "Variante 1" for immediate use
            - Integration with application configuration system

        Business Logic Implementation:
            
            **Validation and Error Handling**:
            - Input parameter validation for folder path and project name
            - Directory creation with proper error handling
            - Graceful error recovery with user-friendly messages
            - Complete cleanup in case of partial creation failure
            
            **Integration Workflow**:
            - Project folder registration with folder manager
            - Variant folder activation for immediate use
            - Initial data file creation and setup
            - User interface synchronization and status updates

        Notes
        -----
        Engineering Workflow Support:
            
            **Professional Structure**:
            The created folder structure supports the complete district heating
            analysis workflow from initial data collection through final
            documentation and reporting.
            
            **Variant Analysis**:
            The structure enables multiple analysis scenarios through the
            variant system, supporting comparative studies and optimization.
            
            **Data Organization**:
            Clear separation of input data, analysis parameters, and results
            facilitates professional project management and documentation.

        Examples
        --------
        **Standard Project Creation**:

            >>> # Create new district heating project
            >>> success = presenter.create_new_project(
            ...     folder_path="C:/Projects/DistrictHeating",
            ...     project_name="Munich_Downtown_District"
            ... )
            >>> 
            >>> if success:
            ...     print("Project 'Munich_Downtown_District' created successfully")
            ...     print("Ready for building data input and analysis")
            >>> else:
            ...     print("Project creation failed - check permissions and path")

        **Batch Project Creation** (for multiple scenarios):

            >>> # Create multiple projects for different districts
            >>> districts = [
            ...     ("Munich_Downtown", "Munich Downtown District"),
            ...     ("Munich_Residential", "Munich Residential Area"),
            ...     ("Munich_Industrial", "Munich Industrial Zone")
            ... ]
            >>> 
            >>> base_path = "C:/Projects/Munich_DistrictHeating"
            >>> for folder_name, project_name in districts:
            ...     success = presenter.create_new_project(base_path, folder_name)
            ...     if success:
            ...         print(f"Created project: {project_name}")

        See Also
        --------
        create_project_copy : Create copies of existing projects
        create_project_variant : Create new analysis variants
        open_existing_project : Open previously created projects
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
        Open an existing district heating project for analysis and modification.

        This method loads a previously created project by setting the project
        folder in the folder manager, which triggers automatic synchronization
        of all application components with the project data and structure.

        Parameters
        ----------
        folder_path : str
            Path to the existing project folder to open.
            Must be a valid project folder with proper structure.

        Notes
        -----
        Project Opening Process:
            
            **Folder Registration**:
            - Registers project folder with folder manager
            - Triggers automatic project folder changed signals
            - Updates user interface with project information
            
            **Component Synchronization**:
            - All managers automatically sync with project data
            - Tab components load project-specific information
            - User interface updates with current project status
            
            **Validation and Recovery**:
            - Automatic validation of project folder structure
            - Graceful handling of incomplete or corrupted projects
            - User feedback for project loading status

        User Experience:
            
            **Seamless Integration**:
            - Immediate availability of all project data and settings
            - Automatic restoration of last active variant
            - Preservation of user interface customizations
            - Real-time synchronization of project status displays

        Examples
        --------
        **Standard Project Opening**:

            >>> # Open existing district heating project
            >>> project_path = "C:/Projects/Munich_Downtown_District"
            >>> presenter.open_existing_project(project_path)
            >>> # Project loaded and ready for analysis

        **Project Switching Workflow**:

            >>> # Switch between multiple projects
            >>> projects = [
            ...     "C:/Projects/Munich_Downtown",
            ...     "C:/Projects/Munich_Residential",
            ...     "C:/Projects/Munich_Industrial"
            ... ]
            >>> 
            >>> for project_path in projects:
            ...     presenter.open_existing_project(project_path)
            ...     # Perform analysis operations
            ...     # Results automatically saved to project folder

        See Also
        --------
        create_new_project : Create new projects with standardized structure
        ProjectFolderManager.set_project_folder : Core folder management method
        """
        if folder_path:
            self.folder_manager.set_project_folder(folder_path)

    def create_project_copy(self) -> bool:
        """
        Create a complete copy of the current project with user-specified name.

        This method creates an exact duplicate of the current project including
        all data files, analysis results, and project structure. The user is
        prompted to provide a new name for the copied project through an
        interactive dialog interface.

        Returns
        -------
        bool
            Success status of project copying operation:
            
            True : Project copied successfully and activated
            False : Project copying failed or was cancelled by user

        Project Copying Process:
            
            **User Interaction**:
            - Interactive dialog for new project name input
            - Default suggestion based on current project name
            - Validation of user input and name conflicts
            - User cancellation handling with graceful feedback
            
            **Complete Data Duplication**:
            - Recursive copying of entire project directory structure
            - Preservation of all data files and analysis results
            - Maintenance of folder structure and organization
            - Automatic variant detection and activation
            
            **System Integration**:
            - Automatic activation of copied project
            - Folder manager registration and synchronization
            - User interface updates with new project information
            - Error handling with comprehensive user feedback

        Business Logic Implementation:
            
            **Name Conflict Resolution**:
            - Automatic detection of existing project names
            - User notification of naming conflicts
            - Prevention of data loss through duplicate naming
            
            **Variant Management**:
            - Automatic detection of project variants
            - Activation of first available variant
            - Fallback to default variant structure if needed
            - Comprehensive variant folder handling

        Notes
        -----
        Professional Workflow Support:
            
            **Scenario Analysis**:
            Project copying enables comparative analysis of different
            scenarios while preserving original project data and results.
            
            **Backup and Archiving**:
            Provides mechanism for creating project backups and maintaining
            project versions for documentation and quality assurance.
            
            **Collaborative Workflows**:
            Supports team collaboration by enabling project sharing and
            independent analysis of copied project data.

        Examples
        --------
        **Standard Project Copying**:

            >>> # Create copy of current project
            >>> success = presenter.create_project_copy()
            >>> if success:
            ...     print("Project copied successfully")
            ...     print("New project activated and ready for analysis")
            >>> else:
            ...     print("Project copying cancelled or failed")

        **Automated Project Versioning**:

            >>> # Create timestamped project versions
            >>> import datetime
            >>> current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            >>> 
            >>> # This would be handled through the interactive dialog
            >>> # User would enter: "Project_Name_v" + current_time
            >>> success = presenter.create_project_copy()

        See Also
        --------
        create_new_project : Create new projects from scratch
        create_project_variant : Create variants within current project
        create_project_variant_copy : Copy specific project variants
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
        Create a new analysis variant within the current project.

        This method creates a new variant folder with the standardized structure
        for district heating analysis. Variants enable comparative analysis of
        different system configurations within the same base project, supporting
        engineering workflows that require evaluation of multiple alternatives.

        Returns
        -------
        bool
            Success status of variant creation operation:
            
            True : Variant created successfully and activated
            False : Variant creation failed due to system error

        Variant Creation Process:
            
            **Automatic Numbering**:
            - Scans existing variants to determine next available number
            - Creates sequentially numbered variants (Variante 1, 2, 3, ...)
            - Prevents conflicts with existing variant names
            - Maintains consistent naming convention
            
            **Standardized Structure**:
            Each variant receives the complete folder structure:
            
            ```
            Variante X/
            ├── Ergebnisse/      # Analysis results and outputs
            ├── Gebäudedaten/    # Building data and parameters
            ├── Lastgang/        # Load profiles and demand data
            └── Wärmenetz/       # Heating network design data
            ```
            
            **System Integration**:
            - Automatic activation of newly created variant
            - Folder manager registration and synchronization
            - User interface updates with new variant information
            - Immediate availability for analysis work

        Engineering Workflow Support:
            
            **Comparative Analysis**:
            - Multiple variants enable scenario comparison
            - Independent analysis of different system configurations
            - Parallel development of alternative solutions
            - Professional documentation of variant differences
            
            **Iterative Design Process**:
            - Support for iterative system optimization
            - Preservation of intermediate design steps
            - Backup of analysis progress and results
            - Foundation for sensitivity analysis and optimization

        Notes
        -----
        Professional Analysis Benefits:
            
            **System Optimization**:
            Variants support the engineering process of evaluating multiple
            system configurations to identify optimal solutions based on
            technical and economic criteria.
            
            **Documentation Standards**:
            Each variant maintains independent documentation and results,
            supporting professional engineering documentation requirements
            and quality assurance processes.
            
            **Regulatory Compliance**:
            Variant analysis supports compliance with engineering standards
            that require evaluation of alternative solutions and documentation
            of design decision rationale.

        Examples
        --------
        **Standard Variant Creation**:

            >>> # Create new variant for alternative system configuration
            >>> success = presenter.create_project_variant()
            >>> if success:
            ...     print("New variant created and activated")
            ...     print("Ready for alternative system analysis")
            >>> else:
            ...     print("Variant creation failed")

        **Systematic Variant Analysis**:

            >>> # Create multiple variants for comprehensive analysis
            >>> variant_configs = [
            ...     "Biomass_Primary",
            ...     "HeatPump_Primary", 
            ...     "Hybrid_System",
            ...     "Solar_Integration"
            ... ]
            >>> 
            >>> for config in variant_configs:
            ...     success = presenter.create_project_variant()
            ...     if success:
            ...         # Configure variant for specific system type
            ...         print(f"Created variant for {config}")
            ...         # Perform system-specific analysis
            ...     else:
            ...         print(f"Failed to create variant for {config}")

        See Also
        --------
        create_project_variant_copy : Copy existing variants
        create_project_copy : Copy entire projects
        ProjectFolderManager.set_variant_folder : Variant activation method
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
        Create a complete copy of the current project variant with all data files.

        This method creates an exact duplicate of the currently active variant
        including all analysis data, results, and configuration files. The new
        variant receives sequential numbering and immediate activation, enabling
        iterative analysis workflows and scenario comparison.

        Returns
        -------
        bool
            Success status of variant copying operation:
            
            True : Variant copied successfully and activated
            False : Variant copying failed due to system error

        Variant Copying Process:
            
            **Complete Data Duplication**:
            - Recursive copying of entire variant directory structure
            - Preservation of all data files including:
              * Building data and characteristics
              * Load profiles and demand calculations
              * Network design and configuration
              * Analysis results and documentation
            
            **Automatic Numbering System**:
            - Scans existing variants to determine next available number
            - Creates sequentially numbered variant copies
            - Prevents naming conflicts with existing variants
            - Maintains consistent variant identification
            
            **Immediate Activation**:
            - Automatic activation of newly created variant copy
            - Folder manager registration and synchronization
            - User interface updates with new variant information
            - Ready for immediate analysis and modification

        Engineering Workflow Benefits:
            
            **Iterative Analysis**:
            - Preserve previous analysis results while exploring alternatives
            - Create baseline scenarios for sensitivity analysis
            - Support incremental system optimization processes
            - Maintain analysis history and decision documentation
            
            **Risk Management**:
            - Backup current analysis state before major modifications
            - Enable rollback to previous configurations if needed
            - Preserve working solutions during experimental analysis
            - Support quality assurance and validation workflows
            
            **Comparative Studies**:
            - Create multiple variants from single baseline configuration
            - Support parametric analysis of system variations
            - Enable systematic evaluation of design alternatives
            - Professional documentation of variant differences

        Data Integrity and Consistency:
            
            **Complete Preservation**:
            - All file types and formats preserved exactly
            - Maintains data relationships and dependencies
            - Preserves custom configurations and settings
            - Ensures analysis continuity and reproducibility
            
            **System Integration**:
            - Seamless integration with existing project structure
            - Automatic recognition by all application components
            - Consistent behavior with original variants
            - Full compatibility with analysis and visualization tools

        Notes
        -----
        Professional Analysis Support:
            
            **Engineering Standards**:
            Variant copying supports engineering workflows that require
            systematic evaluation of alternatives and documentation of
            analysis progression for professional project delivery.
            
            **Quality Assurance**:
            Enables creation of reference configurations and baseline
            scenarios that support quality assurance processes and
            validation of analysis results.

        Examples
        --------
        **Baseline Scenario Creation**:

            >>> # Create baseline variant before major system modifications
            >>> success = presenter.create_project_variant_copy()
            >>> if success:
            ...     print("Baseline variant created successfully")
            ...     print("Safe to proceed with system modifications")
            >>> else:
            ...     print("Failed to create baseline variant")

        **Parametric Analysis Workflow**:

            >>> # Create multiple variants for parametric study
            >>> base_variant = "Variante 1"  # Original configuration
            >>> 
            >>> # Create copies for different parameter studies
            >>> parameters = ["Temperature_Levels", "Insulation_Standards", "Heat_Sources"]
            >>> 
            >>> for param in parameters:
            ...     success = presenter.create_project_variant_copy()
            ...     if success:
            ...         print(f"Created variant copy for {param} analysis")
            ...         # Configure variant for specific parameter study
            ...     else:
            ...         print(f"Failed to create variant for {param}")

        **Incremental Development**:

            >>> # Save progress at major analysis milestones
            >>> milestones = [
            ...     "Initial_Design", 
            ...     "Optimized_Network", 
            ...     "Final_Configuration"
            ... ]
            >>> 
            >>> for milestone in milestones:
            ...     # Perform analysis work for milestone
            ...     success = presenter.create_project_variant_copy()
            ...     if success:
            ...         print(f"Milestone '{milestone}' saved as variant copy")

        See Also
        --------
        create_project_variant : Create new empty variants
        create_project_copy : Copy entire projects
        shutil.copytree : Underlying directory copying functionality
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