"""
Filename: producer_order_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-11
Description: Contains the ProducerOrderTab class.
"""

import os

import geopandas as gpd

from PyQt5.QtWidgets import QVBoxLayout, QWidget, QGroupBox, QListWidget, QPushButton, \
    QMessageBox, QAbstractItemView, QListWidgetItem, QHBoxLayout, QLabel, QLineEdit

from PyQt5.QtCore import Qt

class ProducerOrderTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        producerGroup = QGroupBox("Erzeugerauswahl")
        producerGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        producerLayout = QVBoxLayout()
        producerLayout.addLayout(self.create_producer_selection())
        producerGroup.setLayout(producerLayout)
        layout.addWidget(producerGroup)

        self.load_producers()
    
    def create_producer_selection(self):
        layout = QVBoxLayout()

        self.producer_list_widget = QListWidget()
        self.producer_list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.producer_list_widget)

        self.add_producer_button = QPushButton("Erzeuger hinzufügen")
        self.add_producer_button.clicked.connect(self.add_producer_to_order)
        layout.addWidget(self.add_producer_button)

        self.remove_producer_button = QPushButton("Erzeuger entfernen")
        self.remove_producer_button.clicked.connect(self.remove_producer_from_order)
        layout.addWidget(self.remove_producer_button)

        self.producer_order_list_widget = QListWidget()
        self.producer_order_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.producer_order_list_widget)

        self.producer_percentage_inputs = QVBoxLayout()
        layout.addLayout(self.producer_percentage_inputs)

        return layout

    def load_producers(self):
        """
        Loads the producers from the GeoJSON file and populates the producer list widget.
        """
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
        Reads the producers from the GeoJSON file.

        Args:
            filepath (str): Path to the GeoJSON file.

        Returns:
            list: List of producers with their properties.
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
        """
        Adds the selected producer to the order list.
        """
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
        """
        Removes the selected producer from the order list.
        """
        selected_items = self.producer_order_list_widget.selectedItems()
        for item in selected_items:
            self.producer_order_list_widget.takeItem(self.producer_order_list_widget.row(item))

        self.update_producer_percentage_inputs()

    def update_producer_percentage_inputs(self):
        """
        Updates the percentage input fields for secondary producers.
        """
        # Clear existing percentage inputs
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
                percentage_input_layout.addWidget(label)
                percentage_input_layout.addWidget(line_edit)
                self.producer_percentage_inputs.addLayout(percentage_input_layout)
