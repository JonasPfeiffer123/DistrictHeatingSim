"""
Filename: checkable_comboboxes.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
Description: Contains a custom class for checkable comboboxes.
"""

import pandas as pd
import numpy as np
from datetime import datetime

from PyQt5.QtWidgets import QComboBox, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, pyqtSignal

class CheckableComboBox(QComboBox):
    """
    A custom QComboBox widget that allows multiple selections through checkboxes.

    Attributes:
        checkedStateChanged (pyqtSignal): Signal emitted when the checked state of an item changes.
    """

    checkedStateChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initializes the CheckableComboBox.

        Args:
            parent: The parent widget.
        """
        super(CheckableComboBox, self).__init__(parent)
        self.setView(QListView(self))
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def handleItemPressed(self, index):
        """
        Handles the item pressed event. Toggles the check state of the item.

        Args:
            index (QModelIndex): The index of the pressed item.
        """
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        
        self.checkedStateChanged.emit()

    def itemChecked(self, index):
        """
        Checks if the item at the given index is checked.

        Args:
            index (int): The index of the item to check.

        Returns:
            bool: True if the item is checked, False otherwise.
        """
        item = self.model().item(index)
        return item.checkState() == Qt.Checked

    def addItem(self, text, data=None):
        """
        Adds an item to the combo box with a checkbox.

        Args:
            text (str): The text of the item.
            data: Optional user data for the item.
        """
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def checkedItems(self):
        """
        Returns a list of checked items.

        Returns:
            list: List of checked items.
        """
        checked_items = []
        for index in range(self.count()):
            item = self.model().item(index)
            if item.checkState() == Qt.Checked:
                checked_items.append(item.text())
        return checked_items

def convert_to_serializable(obj):
    """
    Converts an object to a serializable format.
    
    Args:
        obj: The object to convert.
    
    Returns:
        The serializable format of the object.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict()
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, np.datetime64):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj
