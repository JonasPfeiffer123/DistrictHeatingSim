"""
Filename: generator_schematic_test_window.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-27
Description: Test window for the schematic scene with buttons to add components.
"""

import sys

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QHBoxLayout, QApplication
from generator_schematic import SchematicScene, CustomGraphicsView

class SchematicWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up main window
        self.setWindowTitle('Complex Heat Generator Schematic')
        self.setGeometry(100, 100, 1000, 1000)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        layout = QHBoxLayout(self.centralWidget)

        # Instantiate SchematicScene (now decoupled from the window)
        self.scene = SchematicScene(1000, 1000)
        self.view = CustomGraphicsView(self.scene)  # Use custom view with zoom and pan functionality
        layout.addWidget(self.view)

        # Button panel for UI
        button_layout = QVBoxLayout()
        self.add_solar_button = QPushButton("Add Solar")
        self.add_solar_storage_button = QPushButton("Add Solar + Storage")
        self.add_chp_button = QPushButton("Add CHP")
        self.add_chp_storage_button = QPushButton("Add CHP + Storage")
        self.add_wood_chp_button = QPushButton("Add Wood-CHP")
        self.add_wood_chp_storage_button = QPushButton("Add Wood-CHP + Storage")
        self.add_biomass_boiler_button = QPushButton("Add Biomass Boiler")
        self.add_biomass_boiler_storage_button = QPushButton("Add Biomass Boiler + Storage")
        self.add_gas_boiler_button = QPushButton("Add Gas Boiler")
        self.add_geothermal_hp_button = QPushButton("Add Geothermal Heat Pump")
        self.add_river_hp_button = QPushButton("Add River Heat Pump")
        self.add_waste_hp_button = QPushButton("Add Waste Heat Pump")
        self.add_aqva_hp_button = QPushButton("Add Aqva Heat Pump")
        self.delete_button = QPushButton("Delete Selected")
        self.delete_all_button = QPushButton("Delete All")

        # Add the buttons to the layout
        button_layout.addWidget(self.add_solar_button)
        button_layout.addWidget(self.add_solar_storage_button)
        button_layout.addWidget(self.add_chp_button)
        button_layout.addWidget(self.add_chp_storage_button)
        button_layout.addWidget(self.add_wood_chp_button)
        button_layout.addWidget(self.add_wood_chp_storage_button)
        button_layout.addWidget(self.add_biomass_boiler_button)
        button_layout.addWidget(self.add_biomass_boiler_storage_button)
        button_layout.addWidget(self.add_gas_boiler_button)
        button_layout.addWidget(self.add_geothermal_hp_button)
        button_layout.addWidget(self.add_river_hp_button)
        button_layout.addWidget(self.add_waste_hp_button)
        button_layout.addWidget(self.add_aqva_hp_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.delete_all_button)

        layout.addLayout(button_layout)

        # Button signals with new add_component logic
        self.add_solar_button.clicked.connect(lambda: self.scene.add_component(item_name="Solar", storage=False))
        self.add_solar_storage_button.clicked.connect(lambda: self.scene.add_component(item_name="Solar", storage=True))
        self.add_chp_button.clicked.connect(lambda: self.scene.add_component(item_name="CHP", storage=False))
        self.add_chp_storage_button.clicked.connect(lambda: self.scene.add_component(item_name="CHP", storage=True))
        self.add_wood_chp_button.clicked.connect(lambda: self.scene.add_component(item_name="Wood-CHP", storage=False))
        self.add_wood_chp_storage_button.clicked.connect(lambda: self.scene.add_component(item_name="Wood-CHP", storage=True))
        self.add_biomass_boiler_button.clicked.connect(lambda: self.scene.add_component(item_name="Biomass Boiler", storage=False))
        self.add_biomass_boiler_storage_button.clicked.connect(lambda: self.scene.add_component(item_name="Biomass Boiler", storage=True))
        self.add_gas_boiler_button.clicked.connect(lambda: self.scene.add_component(item_name="Gas Boiler", storage=False))
        self.add_geothermal_hp_button.clicked.connect(lambda: self.scene.add_component(item_name="Geothermal Heat Pump", storage=False))
        self.add_river_hp_button.clicked.connect(lambda: self.scene.add_component(item_name="River Heat Pump", storage=False))
        self.add_waste_hp_button.clicked.connect(lambda: self.scene.add_component(item_name="Waste Heat Pump", storage=False))
        self.add_aqva_hp_button.clicked.connect(lambda: self.scene.add_component(item_name="Aqva Heat Pump", storage=False))
        self.delete_button.clicked.connect(self.scene.delete_selected)
        self.delete_all_button.clicked.connect(self.scene.delete_all)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SchematicWindow()
    window.show()
    sys.exit(app.exec_())
