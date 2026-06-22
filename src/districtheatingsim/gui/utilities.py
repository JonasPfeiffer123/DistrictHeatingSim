"""GUI Utilities Module
====================

Custom GUI widgets and utility functions for DistrictHeatingSim application.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from datetime import datetime

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QComboBox, QListView


class NoScrollComboBox(QComboBox):
    """
    A QComboBox that ignores mouse-wheel events.

    Inside a scroll area or table, hovering over a normal combo box and scrolling
    accidentally cycles its selection. This variant lets the wheel event pass through
    to the container (so the table/page scrolls instead); the value still changes via
    clicking and the popup list.
    """

    def wheelEvent(self, event):
        event.ignore()


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
        super().__init__(parent)
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


def stop_qthreads(*threads):
    """
    Stop each given ``QThread`` (via its ``stop()``) if it exists and is running.

    Called from the main window's ``closeEvent`` so worker threads are not destroyed
    while still running (which Qt aborts on). ``None`` entries (uninitialised thread
    attributes) are skipped.
    """
    for thread in threads:
        if thread is not None and thread.isRunning():
            thread.stop()


def any_thread_running(*threads) -> bool:
    """
    Return ``True`` if any given worker thread exists and is currently running.

    Used to refuse launching a second worker that would mutate the same shared
    object while one is already in flight (BACKLOG C1). ``None`` entries
    (uninitialised thread attributes) are skipped. Duck-typed on ``isRunning()`` so
    it is unit-testable without a real ``QThread``.
    """
    return any(t is not None and t.isRunning() for t in threads)
