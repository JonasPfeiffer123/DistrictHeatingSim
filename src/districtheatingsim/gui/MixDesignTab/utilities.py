"""
Filename: utilities.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-06
Description: Contains the CollapsibleHeader class for creating collapsible sections in the GUI.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QSizePolicy)
from PyQt5.QtCore import QSize

class CollapsibleHeader(QWidget):
    def __init__(self, title, content_widget):
        super().__init__()
        self.content_widget = content_widget
        self.is_expanded = True

        # Create header layout with a toggle button
        self.layout = QVBoxLayout(self)
        self.toggle_button = QPushButton(f"▼ {title}")  # ▼ for expanded, ▶ for collapsed
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.clicked.connect(self.toggle_content)

        # Style the toggle button
        self.toggle_button.setStyleSheet("QPushButton { font-weight: bold; border: none; text-align: left; }")

        # Add button and content to layout
        self.layout.addWidget(self.toggle_button)
        self.layout.addWidget(self.content_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)  # Reduce margins for a compact look

        # Adjust size policies for proper behavior when collapsed
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        self.content_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)

    def toggle_content(self):
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self.toggle_button.setText(f"{'▼' if self.is_expanded else '▶'} {self.toggle_button.text()[2:]}")  # Update arrow

        # Adjust size based on expanded/collapsed state
        self.updateGeometry()

    def sizeHint(self):
        if self.is_expanded:
            return super().sizeHint()
        else:
            # Only the height of the button when collapsed
            return QSize(self.toggle_button.width(), self.toggle_button.sizeHint().height())