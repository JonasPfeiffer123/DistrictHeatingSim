"""
Energy System Tab Utilities Module
===================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Utility classes for Energy System Tab, including collapsible sections, checkable combo boxes, and custom JSON encoding.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QSizePolicy, QComboBox)
from PyQt6.QtCore import QSize, Qt

import json
import numpy as np
import pandas as pd

from districtheatingsim.heat_generators import *

class CheckableComboBox(QComboBox):
    """
    Combo box that allows multiple items to be checked.
    """

    def __init__(self, parent=None):
        """
        Initialize the CheckableComboBox.

        :param parent: Parent widget.
        :type parent: QWidget
        """
        super(CheckableComboBox, self).__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModelColumn(0)
        self.checked_items = []

    def handleItemPressed(self, index):
        """
        Handle item pressed event to toggle check state.

        :param index: Index of the pressed item.
        :type index: QModelIndex
        """
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
            self.checked_items.remove(item.text())
        else:
            item.setCheckState(Qt.CheckState.Checked)
            self.checked_items.append(item.text())
        self.updateText()

    def updateText(self):
        """
        Update displayed text to show checked items.
        """
        if self.checked_items:
            self.setEditText(', '.join(self.checked_items))
        else:
            self.setEditText('')

    def addItem(self, text, data=None):
        """
        Add item to combo box.

        :param text: Item text.
        :type text: str
        :param data: Associated data.
        :type data: Any
        """
        super(CheckableComboBox, self).addItem(text, data)
        item = self.model().item(self.count() - 1)
        item.setCheckState(Qt.CheckState.Unchecked)

    def addItems(self, texts):
        """
        Add multiple items to combo box.

        :param texts: List of item texts to add.
        :type texts: list
        """
        for text in texts:
            self.addItem(text)

    def setItemChecked(self, text, checked=True):
        """
        Set check state of an item.

        :param text: Item text.
        :type text: str
        :param checked: Check state.
        :type checked: bool
        """
        index = self.findText(text)
        if index != -1:
            item = self.model().item(index)
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            if checked:
                if text not in self.checked_items:
                    self.checked_items.append(text)
            else:
                if text in self.checked_items:
                    self.checked_items.remove(text)
            self.updateText()

    def clear(self):
        """
        Clear all items from combo box.
        """
        super(CheckableComboBox, self).clear()
        self.checked_items = []

    def checkedItems(self):
        """
        Get list of checked items.

        :return: List of checked items.
        :rtype: list
        """
        return self.checked_items

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
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)
        self.content_widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)

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
        
class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder for handling numpy arrays, pandas DataFrames, and custom objects.
    """
    def default(self, obj):
        try:
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, pd.DataFrame):
                # Use 'split' format for DataFrame serialization
                return obj.to_dict(orient='split')
            if isinstance(obj, (BaseHeatGenerator, BaseStrategy, STES)):
                return obj.to_dict()
            return super().default(obj)
        except TypeError as e:
            print(f"Failed to encode {obj} of type {type(obj)}")
            raise e