"""
Producer Order Tab Module
=========================

Tab for selecting and ordering heat producers in district heating networks.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-11
"""

import os

import geopandas as gpd

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QGroupBox, QListWidget, QPushButton, \
    QMessageBox, QAbstractItemView, QListWidgetItem, QHBoxLayout, QLabel, QLineEdit

from PyQt6.QtCore import Qt

class ProducerOrderTab(QWidget):
    """
    Widget for configuring heat producer selection and priority order.
    """
    
    def __init__(self, dialog_config, parent=None):
        """
        Initialize producer order tab.

        Parameters
        ----------
        dialog_config : dict
            Configuration data.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.parent = parent
        self.dialog_config = dialog_config
        self.initUI()
        self.percentage_inputs = []

    def initUI(self):
        """Initialize user interface components."""
        layout = QVBoxLayout(self)

        producerGroup = QGroupBox("Erzeugerauswahl")
        producerGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        producerLayout = QVBoxLayout()
        producerLayout.addLayout(self.create_producer_selection())
        producerGroup.setLayout(producerLayout)
        layout.addWidget(producerGroup)

        self.load_producers()
    
    def create_producer_selection(self):
        """
        Create producer selection interface components.

        Returns
        -------
        QVBoxLayout
            Layout containing producer selection widgets.
        """
        layout = QVBoxLayout()

        self.producer_list_widget = QListWidget()
        self.producer_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        layout.addWidget(self.producer_list_widget)

        self.add_producer_button = QPushButton("Erzeuger hinzufügen")
        self.add_producer_button.clicked.connect(self.add_producer_to_order)
        layout.addWidget(self.add_producer_button)

        self.remove_producer_button = QPushButton("Erzeuger entfernen")
        self.remove_producer_button.clicked.connect(self.remove_producer_from_order)
        layout.addWidget(self.remove_producer_button)

        self.producer_order_list_widget = QListWidget()
        self.producer_order_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.producer_order_list_widget)

        self.producer_percentage_inputs = QVBoxLayout()
        layout.addLayout(self.producer_percentage_inputs)

        return layout

    def load_producers(self):
        """Load producers from GeoJSON file and populate list widget."""
        filepath = self.parent.network_data_tab.erzeugeranlagenInput.itemAt(1).widget().text()
        try:
            producers = self.read_producers_from_geojson(filepath)
            self.producer_list_widget.clear()
            for producer in producers:
                item = QListWidgetItem(producer['name'])
                item.setData(Qt.UserRole, producer)
                self.producer_list_widget.addItem(item)
        except FileNotFoundError as e:
            QMessageBox.warning(self, "Datei nicht gefunden", str(e))

    def read_producers_from_geojson(self, filepath):
        """
        Read producer data from GeoJSON file.

        Parameters
        ----------
        filepath : str
            Path to GeoJSON file.

        Returns
        -------
        list
            List of producer dictionaries.

        Raises
        ------
        FileNotFoundError
            If GeoJSON file not found.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"GeoJSON file not found: {filepath}")

        geojson_data = gpd.read_file(filepath)
        producers = []
        for idx, row in geojson_data.iterrows():
            producers.append({
                'name': f'Erzeugerstandort {idx + 1}',
                'location': row['geometry']
            })
        return producers

    def add_producer_to_order(self):
        """Add selected producer to the order list."""
        selected_items = self.producer_list_widget.selectedItems()
        for item in selected_items:
            producer = item.data(Qt.UserRole)
            # Check if the producer is already in the order list
            if not any(self.producer_order_list_widget.item(i).data(Qt.UserRole)['index'] == self.producer_list_widget.row(item) for i in range(self.producer_order_list_widget.count())):
                order_item = QListWidgetItem(producer['name'])
                order_item.setData(Qt.UserRole, {'name': producer['name'], 'index': self.producer_list_widget.row(item)})
                self.producer_order_list_widget.addItem(order_item)

        self.update_producer_percentage_inputs()

    def remove_producer_from_order(self):
        """Remove selected producer from the order list."""
        selected_items = self.producer_order_list_widget.selectedItems()
        for item in selected_items:
            self.producer_order_list_widget.takeItem(self.producer_order_list_widget.row(item))

        self.update_producer_percentage_inputs()

    def update_producer_percentage_inputs(self):
        """Update percentage input fields for secondary producers."""
        # Clear existing percentage inputs
        self.percentage_inputs.clear()
        while self.producer_percentage_inputs.count():
            item = self.producer_percentage_inputs.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Add new percentage inputs for secondary producers
        count = self.producer_order_list_widget.count()
        if count > 1:
            for i in range(1, count):
                percentage_input_layout = QHBoxLayout()
                label = QLabel(f"Erzeuger {i+1} Prozentuale Erzeugung (%):")
                line_edit = QLineEdit()
                self.percentage_inputs.append(line_edit)
                percentage_input_layout.addWidget(label)
                percentage_input_layout.addWidget(line_edit)
                self.producer_percentage_inputs.addLayout(percentage_input_layout)