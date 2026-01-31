"""GUI Utilities Module
====================

Custom GUI widgets and utility functions for DistrictHeatingSim application.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import pandas as pd
import numpy as np
from datetime import datetime

from PyQt6.QtWidgets import QComboBox, QListView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal

class CheckableComboBox(QComboBox):
    """
    Custom combo box widget with checkable items for multiple selection.

    :signal checkedStateChanged: Emitted when any item's checked state changes

    .. note::
       Extends QComboBox to provide checkbox functionality for each item.
    """

    checkedStateChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialize the checkable combo box.

        :param parent: Parent widget, defaults to None
        :type parent: QWidget, optional
        """
        super(CheckableComboBox, self).__init__(parent)
        self.setView(QListView(self))
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

    def handleItemPressed(self, index):
        """
        Toggle item's check state when pressed.

        :param index: Index of the pressed item
        :type index: QModelIndex
        """
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
        else:
            item.setCheckState(Qt.CheckState.Checked)
        
        self.checkedStateChanged.emit()

    def itemChecked(self, index):
        """
        Check if item at given index is checked.

        :param index: Item index to check
        :type index: int
        :return: True if item is checked
        :rtype: bool
        """
        item = self.model().item(index)
        return item.checkState() == Qt.CheckState.Checked

    def addItem(self, text, data=None):
        """
        Add a checkable item to the combo box.

        :param text: Item text to display
        :type text: str
        :param data: Optional user data for the item, defaults to None
        :type data: any, optional
        """
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setCheckState(Qt.CheckState.Unchecked)
        self.model().appendRow(item)

    def checkedItems(self):
        """
        Get list of checked item texts.

        :return: Text of all checked items
        :rtype: list of str
        """
        checked_items = []
        for index in range(self.count()):
            item = self.model().item(index)
            if item.checkState() == Qt.CheckState.Checked:
                checked_items.append(item.text())
        return checked_items

def convert_to_serializable(obj):
    """
    Convert various data types to JSON-serializable format.

    :param obj: Object to convert
    :type obj: any
    :return: JSON-serializable representation of the object
    :rtype: any

    .. note::
       Handles pandas objects, numpy arrays, and datetime objects for JSON serialization.
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