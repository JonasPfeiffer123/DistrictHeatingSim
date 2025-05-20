"""
Filename: net_generation_dialog.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-05-20
Description: Contains the NetGenerationDialog class.
"""

import json
import os
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QPushButton, QTabWidget
from PyQt5.QtCore import Qt

from districtheatingsim.gui.NetSimulationTab.network_data_tab import NetworkDataTab
from districtheatingsim.gui.NetSimulationTab.producer_order_tab import ProducerOrderTab
from districtheatingsim.gui.NetSimulationTab.network_config_tab import NetworkConfigTab
from districtheatingsim.gui.NetSimulationTab.diameter_optimization_tab import DiameterOptimizationTab
from districtheatingsim.gui.NetSimulationTab.NetworkDataClass import NetworkGenerationData, SecondaryProducer

def load_dialog_config(config_path="dialog_config.json"):
    # Join the config_path with the directory of this file if it's a relative path
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def save_dialog_config(config, config_path="dialog_config.json"):
    # Join the config_path with the directory of this file if it's a relative path
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    
class NetGenerationDialog(QDialog):
    def __init__(self, generate_callback, base_path, parent=None, config_path="dialog_config.json"):
        super().__init__(parent)
        self.generate_callback = generate_callback
        self.base_path = base_path
        self.parent = parent
        self.dialog_config = load_dialog_config(config_path)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Netz generieren")
        self.resize(1000, 800)

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.network_data_tab = NetworkDataTab(self.base_path, self.dialog_config, self)
        self.producer_order_tab = ProducerOrderTab(self.dialog_config, self)
        self.network_config_tab = NetworkConfigTab(self.dialog_config, self)
        self.diameter_optimization_tab = DiameterOptimizationTab(self.dialog_config, self)

        self.tabs.addTab(self.network_data_tab, "Netzdaten")
        self.tabs.addTab(self.producer_order_tab, "Erzeugerstandorte")
        self.tabs.addTab(self.network_config_tab, "Netzkonfiguration")
        self.tabs.addTab(self.diameter_optimization_tab, "Durchmesseroptimierung")

        main_layout.addWidget(self.tabs)

        self.generateButton = QPushButton("Netz generieren")
        self.generateButton.clicked.connect(self.generateNetwork)
        main_layout.addWidget(self.generateButton)

    def generateNetwork(self):
        """
        Generates the network based on the user inputs and calls the generate_callback function.
        """
        if self.network_data_tab.importTypeComboBox.currentText() == "GeoJSON":
            # Extrahiere GeoJSON-spezifische Daten
            vorlauf_path = self.network_data_tab.vorlaufInput.itemAt(1).widget().text()
            ruecklauf_path = self.network_data_tab.ruecklaufInput.itemAt(1).widget().text()
            hast_path = self.network_data_tab.hastInput.itemAt(1).widget().text()
            erzeugeranlagen_path = self.network_data_tab.erzeugeranlagenInput.itemAt(1).widget().text()

            json_path = self.network_data_tab.jsonLineEdit.text()

            pipetype = self.network_config_tab.initialpipetypeInput.currentText()

            v_max_pipe = float(self.diameter_optimization_tab.v_max_pipeInput.text())
            material_filter = self.diameter_optimization_tab.material_filterInput.currentText()
            k_mm = float(self.diameter_optimization_tab.k_mm_Input.text())

        self.network_config_tab.getSupplyTemperatureHeatGenerator()
        
        flow_pressure_pump = float(self.network_config_tab.parameter_rows_net[4].itemAt(1).widget().text())
        lift_pressure_pump = float(self.network_config_tab.parameter_rows_net[5].itemAt(1).widget().text())

        min_supply_temperature_building = (
            float(self.network_config_tab.parameter_rows_heat_consumer[0].itemAt(1).widget().text())
            if self.network_config_tab.min_supply_temperature_building_checked else None
        )
        fixed_return_temperature_heat_consumer = (
            float(self.network_config_tab.parameter_rows_heat_consumer[1].itemAt(1).widget().text())
            if self.network_config_tab.return_temp_checked else None
        )

        dT_RL = float(self.network_config_tab.parameter_rows_heat_consumer[2].itemAt(1).widget().text())

        # Ermitteln des Index des Haupterzeugers und der Reihenfolge der sekundären Erzeuger
        if self.producer_order_tab.producer_order_list_widget.count() > 0:
            main_producer_location_index = self.producer_order_tab.producer_order_list_widget.item(0).data(Qt.UserRole)['index']
            secondary_producers = [
                {
                    'index': self.producer_order_tab.producer_order_list_widget.item(i).data(Qt.UserRole)['index'],
                    'percentage': float(self.producer_order_tab.percentage_inputs[i-1].text())  # Zugriff auf die Liste
                }
                for i in range(1, self.producer_order_tab.producer_order_list_widget.count())
            ]
        else:
            main_producer_location_index = 0
            secondary_producers = []

        data = NetworkGenerationData(
            import_type=self.network_data_tab.importTypeComboBox.currentText(), # Type: str
            flow_line_path=vorlauf_path, # Type: str
            return_line_path=ruecklauf_path, # Type: str
            heat_consumer_path=hast_path, # Type: str
            heat_generator_path=erzeugeranlagen_path, # Type: str
            heat_demand_json_path=json_path, # Type: str

            netconfiguration=self.network_config_tab.netconfiguration, # Type: str
            supply_temperature_control=self.network_config_tab.supplyTemperatureControlInput.currentText(), # Type: str
            max_supply_temperature_heat_generator=self.network_config_tab.max_supply_temperature, # Type: float
            min_supply_temperature_heat_generator=self.network_config_tab.min_supply_temperature, # Type: float
            max_air_temperature_heat_generator=self.network_config_tab.max_air_temperature, # Type: float
            min_air_temperature_heat_generator=self.network_config_tab.min_air_temperature, # Type: float
            flow_pressure_pump=flow_pressure_pump, # Type: float
            lift_pressure_pump=lift_pressure_pump, # Type: float
            min_supply_temperature_building_checked=self.network_config_tab.min_supply_temperature_building_checked, # Type: bool
            min_supply_temperature_building=min_supply_temperature_building, # Type: float or None
            fixed_return_temperature_heat_consumer_checked=self.network_config_tab.return_temp_checked, # Type: bool
            fixed_return_temperature_heat_consumer=fixed_return_temperature_heat_consumer, # Type: float or None
            dT_RL=dT_RL, # Type: float
            building_temperature_checked=self.network_config_tab.building_temp_checked, # Type: bool
            pipetype=pipetype, # Type: str

            diameter_optimization_pipe_checked=self.diameter_optimization_tab.DiameterOpt_ckecked, # Type: bool
            max_velocity_pipe=v_max_pipe, # Type: float
            material_filter_pipe=material_filter, # Type: str
            k_mm_pipe=k_mm, # Type: float

            main_producer_location_index=main_producer_location_index, # Type: int
            secondary_producers=[SecondaryProducer(**sp) for sp in secondary_producers], # Type: list of SecondaryProducer
        )
        if self.generate_callback:
            print("Calling generate_callback with data:", vars(data))
            # Call the callback function with the generated data
            self.generate_callback(data)

        self.accept()