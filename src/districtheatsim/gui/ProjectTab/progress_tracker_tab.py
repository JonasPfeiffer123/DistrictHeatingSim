from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
import os

class ProgressTrackerDialog(QDialog):
    """
    Dialog for showing project progress based on generated files.

    Args:
        parent (QWidget, optional): The parent widget. Defaults to None.
        required_files (list): List of required files for progress tracking.
        base_path (str): The base path to check for file existence.
    """
    def __init__(self, required_files, base_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Projektfortschritt")
        self.layout = QVBoxLayout(self)

        self.required_files = required_files
        self.base_path = base_path

        # Create label and progress bar
        self.label = QLabel("Fortschritt der Dateigenerierung")
        self.layout.addWidget(self.label)

        self.progressBar = QProgressBar(self)
        self.layout.addWidget(self.progressBar)

        # Create close button
        self.closeButton = QPushButton("Schließen", self)
        self.closeButton.clicked.connect(self.close)
        self.layout.addWidget(self.closeButton)

        # Calculate initial progress
        self.update_progress()

    def update_progress(self):
        """
        Update the progress bar based on the number of detected files.
        """
        generated_files = [file for file in self.required_files if os.path.exists(file)]
        progress = len(generated_files) / len(self.required_files) * 100
        self.progressBar.setValue(int(progress))  # Convert progress to int

