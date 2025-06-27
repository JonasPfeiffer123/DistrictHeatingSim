"""
GUI Utilities Module
====================

This module provides custom GUI widgets and utility functions for the DistrictHeatingSim application.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-07-23
"""

import pandas as pd
import numpy as np
from datetime import datetime

from PyQt5.QtWidgets import QComboBox, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, pyqtSignal

class CheckableComboBox(QComboBox):
    """
    A custom combo box widget with checkable items for multiple selection.

    Extends QComboBox to provide checkbox functionality for each item,
    enabling users to select multiple options from a dropdown list.

    Signals
    -------
    checkedStateChanged : pyqtSignal
        Emitted when any item's checked state changes.

    Examples
    --------
    >>> combo = CheckableComboBox()
    >>> combo.addItem("Option 1")
    >>> combo.addItem("Option 2")
    >>> selected = combo.checkedItems()
    """

    checkedStateChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialize the checkable combo box.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super(CheckableComboBox, self).__init__(parent)
        self.setView(QListView(self))
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def handleItemPressed(self, index):
        """
        Toggle item's check state when pressed.

        Parameters
        ----------
        index : QModelIndex
            Index of the pressed item.
        """
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        
        self.checkedStateChanged.emit()

    def itemChecked(self, index):
        """
        Check if item at given index is checked.

        Parameters
        ----------
        index : int
            Item index to check.

        Returns
        -------
        bool
            True if item is checked.
        """
        item = self.model().item(index)
        return item.checkState() == Qt.Checked

    def addItem(self, text, data=None):
        """
        Add a checkable item to the combo box.

        Parameters
        ----------
        text : str
            Item text to display.
        data : any, optional
            Optional user data for the item.
        """
        item = QStandardItem(text)
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def checkedItems(self):
        """
        Get list of checked item texts.

        Returns
        -------
        list of str
            Text of all checked items.
        """
        checked_items = []
        for index in range(self.count()):
            item = self.model().item(index)
            if item.checkState() == Qt.Checked:
                checked_items.append(item.text())
        return checked_items

def convert_to_serializable(obj):
    """
    Convert various data types to JSON-serializable format.
    
    Handles pandas objects, numpy arrays, and datetime objects
    for JSON serialization compatibility.
    
    Parameters
    ----------
    obj : any
        Object to convert.
    
    Returns
    -------
    any
        JSON-serializable representation of the object.
        
    Examples
    --------
    >>> import numpy as np
    >>> convert_to_serializable(np.int64(42))
    42
    >>> convert_to_serializable(np.array([1, 2, 3]))
    [1, 2, 3]
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