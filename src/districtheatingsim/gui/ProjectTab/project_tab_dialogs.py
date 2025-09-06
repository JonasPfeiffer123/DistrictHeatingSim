"""
Project Tab Dialogs Module
==========================

Dialog windows for project tab functionality including data input and progress display.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-20
"""

from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QDialog, QLineEdit, QDialogButtonBox, 
                             QGridLayout, QFrame, QScrollArea, QPushButton, QProgressBar)

class RowInputDialog(QDialog):
    """
    Dialog for adding new table rows with input fields.
    """
    def __init__(self, headers, parent=None):
        """
        Initialize row input dialog.

        Parameters
        ----------
        headers : list
            Column headers for input fields.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Neue Zeile hinzufügen")
        self.layout = QGridLayout(self)
        self.fields = {}

        # Create input fields with labels
        for i, header in enumerate(headers):
            label = QLabel(header)
            lineEdit = QLineEdit()
            lineEdit.setPlaceholderText(f"Geben Sie {header} ein")
            self.layout.addWidget(label, i, 0)
            self.layout.addWidget(lineEdit, i, 1)
            self.fields[header] = lineEdit

        # Dialog buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(headers), 0, 1, 2)

    def get_input_data(self):
        """
        Get input data from dialog fields.

        Returns
        -------
        dict
            Mapping of headers to input values.
        """
        return {header: field.text() for header, field in self.fields.items()}
    
class OSMImportDialog(QDialog):
    """
    Dialog for OSM data import with default building parameters.
    """
    def __init__(self, parent=None):
        """
        Initialize OSM import dialog.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("OSM-Daten importieren")
        self.layout = QGridLayout(self)
        self.fields = {}

        # Define the default values for the fields
        self.default_values = {
            "Land": "Deutschland",
            "Bundesland": "",
            "Stadt": "",
            "Adresse": "",
            "Wärmebedarf": "30000",
            "Gebäudetyp": "HMF",
            "Subtyp": "05",
            "WW_Anteil": "0.2",
            "Typ_Heizflächen": "HK",
            "VLT_max": "70",
            "Steigung_Heizkurve": "1.5",
            "RLT_max": "55",
            "Normaußentemperatur": "-15"
        }

        # Create input fields with labels and default values
        for i, (header, value) in enumerate(self.default_values.items()):
            label = QLabel(header)
            lineEdit = QLineEdit(value)
            lineEdit.setPlaceholderText(f"Geben Sie {header} ein")
            self.layout.addWidget(label, i, 0)
            self.layout.addWidget(lineEdit, i, 1)
            self.fields[header] = lineEdit

        # Dialog buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(buttonBox, len(self.default_values), 0, 1, 2)

    def get_input_data(self):
        """
        Get OSM import parameters.

        Returns
        -------
        dict
            Mapping of parameters to input values.
        """
        return {header: field.text() for header, field in self.fields.items()}
    
class ProcessDetailsDialog(QDialog):
    """
    Dialog displaying detailed project progress information.
    """
    def __init__(self, process_steps, parent=None):
        """
        Initialize process details dialog.

        Parameters
        ----------
        process_steps : list
            List of process step dictionaries with progress info.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Projektfortschritt - Details")
        self.setMinimumSize(800, 800)
        
        self.process_steps = process_steps

        # Main layout for the dialog
        main_layout = QVBoxLayout(self)
        
        # Scrollable area for process steps
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        
        # Container widget and layout for process steps
        process_widget = QFrame()
        process_layout = QVBoxLayout(process_widget)
        
        for step in self.process_steps:
            # Each process step will have its own section
            step_layout = QVBoxLayout()
            step_label = QLabel(f"{step['name']}")
            step_layout.addWidget(step_label)

            # Status and required files
            progress = self.get_step_progress(step)
            progress_bar = QProgressBar()
            progress_bar.setValue(int(progress))
            progress_bar.setTextVisible(True)
            step_layout.addWidget(progress_bar)

            # Description of the step
            description_label = QLabel(f"Beschreibung: {step['description']}")
            step_layout.addWidget(description_label)

            # Show missing files if any
            if len(step.get("missing_files", [])) > 0:
                for missing_file in step["missing_files"]:
                    missing_label = QLabel(f"Fehlende Datei: {missing_file}")
                    missing_label.setStyleSheet("color: red;")
                    step_layout.addWidget(missing_label)
            else:
                completed_label = QLabel("Alle Dateien vorhanden")
                completed_label.setStyleSheet("color: green;")
                step_layout.addWidget(completed_label)

            # Optionally, add file sizes and modification times if available
            if "file_sizes" in step:
                for i, size in enumerate(step["file_sizes"]):
                    size_label = QLabel(f"Dateigröße: {size}")
                    step_layout.addWidget(size_label)

            if "file_modification_times" in step:
                for i, mod_time in enumerate(step["file_modification_times"]):
                    mod_time_label = QLabel(f"Zuletzt geändert: {mod_time}")
                    step_layout.addWidget(mod_time_label)
            
            # Add the step layout to the process layout
            step_frame = QFrame()
            step_frame.setLayout(step_layout)
            process_layout.addWidget(step_frame)

        # Set the widget for the scroll area
        scroll_area.setWidget(process_widget)
        main_layout.addWidget(scroll_area)

        # Close button
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.accept)
        main_layout.addWidget(close_button)

    def get_step_progress(self, step):
        """
        Calculate step completion percentage based on required files.

        Parameters
        ----------
        step : dict
            Process step information.

        Returns
        -------
        float
            Completion percentage (0-100).
        """
        total_files = len(step["required_files"])
        missing_files = len(step.get("missing_files", []))
        return ((total_files - missing_files) / total_files) * 100