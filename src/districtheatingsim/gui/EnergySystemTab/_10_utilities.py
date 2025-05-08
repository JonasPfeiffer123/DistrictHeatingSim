"""
Filename: _10_utilities.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-06
Description: Contains the CollapsibleHeader class for creating collapsible sections in the GUI.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QSizePolicy, QComboBox)
from PyQt5.QtCore import QSize, Qt

import json
import numpy as np
import pandas as pd

from districtheatingsim.heat_generators.heat_pumps import RiverHeatPump, WasteHeatPump, Geothermal, AqvaHeat
from districtheatingsim.heat_generators.gas_boiler import GasBoiler
from districtheatingsim.heat_generators.biomass_boiler import BiomassBoiler
from districtheatingsim.heat_generators.solar_thermal import SolarThermal
from districtheatingsim.heat_generators.chp import CHP
from districtheatingsim.heat_generators.power_to_heat import PowerToHeat

from districtheatingsim.heat_generators.base_heat_generator import BaseHeatGenerator, BaseStrategy
from districtheatingsim.heat_generators.STES import TemperatureStratifiedThermalStorage

class CheckableComboBox(QComboBox):
    """
    A QComboBox subclass that allows multiple items to be checked.
    """

    def __init__(self, parent=None):
        """
        Initializes the CheckableComboBox.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super(CheckableComboBox, self).__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModelColumn(0)
        self.checked_items = []

    def handleItemPressed(self, index):
        """
        Handles the item pressed event to toggle the check state.

        Args:
            index (QModelIndex): The index of the pressed item.
        """
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
            self.checked_items.remove(item.text())
        else:
            item.setCheckState(Qt.Checked)
            self.checked_items.append(item.text())
        self.updateText()

    def updateText(self):
        """
        Updates the displayed text to show the checked items.
        """
        if self.checked_items:
            self.setEditText(', '.join(self.checked_items))
        else:
            self.setEditText('')

    def addItem(self, text, data=None):
        """
        Adds an item to the combo box.

        Args:
            text (str): The text of the item.
            data (Any, optional): The data associated with the item. Defaults to None.
        """
        super(CheckableComboBox, self).addItem(text, data)
        item = self.model().item(self.count() - 1)
        item.setCheckState(Qt.Unchecked)

    def addItems(self, texts):
        """
        Adds multiple items to the combo box.

        Args:
            texts (list): The list of item texts to add.
        """
        for text in texts:
            self.addItem(text)

    def setItemChecked(self, text, checked=True):
        """
        Sets the check state of an item.

        Args:
            text (str): The text of the item.
            checked (bool, optional): The check state. Defaults to True.
        """
        index = self.findText(text)
        if index != -1:
            item = self.model().item(index)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            if checked:
                if text not in self.checked_items:
                    self.checked_items.append(text)
            else:
                if text in self.checked_items:
                    self.checked_items.remove(text)
            self.updateText()

    def clear(self):
        """
        Clears all items from the combo box.
        """
        super(CheckableComboBox, self).clear()
        self.checked_items = []

    def checkedItems(self):
        """
        Gets the list of checked items.

        Returns:
            list: The list of checked items.
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
        
class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder to handle encoding of specific objects and data types.
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
            if isinstance(obj, (BaseHeatGenerator, BaseStrategy, TemperatureStratifiedThermalStorage)):
                return obj.to_dict()
            return super().default(obj)
        except TypeError as e:
            print(f"Failed to encode {obj} of type {type(obj)}")
            raise e