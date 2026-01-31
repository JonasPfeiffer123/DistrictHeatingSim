"""Network Generation Dialog Module
================================

Dialog for configuring network generation parameters with tabbed interface.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import json
import os
import sys
from PyQt6.QtWidgets import QVBoxLayout, QDialog, QPushButton, QTabWidget
from PyQt6.QtCore import Qt

from districtheatingsim.utilities.utilities import get_resource_path
from districtheatingsim.gui.NetSimulationTab.network_data_tab import NetworkDataTab
from districtheatingsim.gui.NetSimulationTab.producer_order_tab import ProducerOrderTab
from districtheatingsim.gui.NetSimulationTab.network_config_tab import NetworkConfigTab
from districtheatingsim.gui.NetSimulationTab.diameter_optimization_tab import DiameterOptimizationTab
from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import NetworkGenerationData, SecondaryProducer

def load_dialog_config(config_path="dialog_config.json"):
    """
    Load dialog configuration from JSON file.

    :param config_path: Path to configuration file.
    :type config_path: str
    :return: Configuration data.
    :rtype: dict
    """
    if not os.path.isabs(config_path):
        # Use get_resource_path for PyInstaller compatibility
        config_path = get_resource_path(os.path.join('gui', 'NetSimulationTab', config_path))
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def save_dialog_config(config, config_path="dialog_config.json"):
    """
    Save dialog configuration to JSON file.

    :param config: Configuration data to save.
    :type config: dict
    :param config_path: Path to configuration file.
    :type config_path: str
    """
    if not os.path.isabs(config_path):
        # Use get_resource_path for PyInstaller compatibility
        config_path = get_resource_path(os.path.join('gui', 'NetSimulationTab', config_path))
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    
class NetGenerationDialog(QDialog):
    """
    Dialog for network generation configuration with multiple tabs.
    """
    
    def __init__(self, generate_callback, base_path, parent=None, config_path="dialog_config.json"):
        """
        Initialize network generation dialog.

        :param generate_callback: Callback function for network generation.
        :type generate_callback: callable
        :param base_path: Base path for file operations.
        :type base_path: str
        :param parent: Parent widget.
        :type parent: QWidget
        :param config_path: Path to configuration file.
        :type config_path: str
        """
        super().__init__(parent)
        self.generate_callback = generate_callback
        self.base_path = base_path
        self.parent = parent
        self.dialog_config = load_dialog_config(config_path)
        self.initUI()

    def initUI(self):
        """
        Initialize dialog user interface with tabs.
        """
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
        Generate network based on user inputs and execute callback.
        """
        if self.network_data_tab.importTypeComboBox.currentText() == "GeoJSON":
            # Extract unified GeoJSON path
            network_path = self.network_data_tab.networkInput.itemAt(1).widget().text()
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

        # Determine main producer index and secondary producer order
        if self.producer_order_tab.producer_order_list_widget.count() > 0:
            main_producer_location_index = self.producer_order_tab.producer_order_list_widget.item(0).data(Qt.ItemDataRole.UserRole)['index']
            
            secondary_producers = [
            {
                'index': self.producer_order_tab.producer_order_list_widget.item(i).data(Qt.ItemDataRole.UserRole)['index'],
                'load_percentage': float(self.producer_order_tab.percentage_inputs[i-1].text())
            }
            for i in range(1, self.producer_order_tab.producer_order_list_widget.count())
            ]
        else:
            main_producer_location_index = 0
            secondary_producers = []

        data = NetworkGenerationData(
            import_type=self.network_data_tab.importTypeComboBox.currentText(),
            network_geojson_path=network_path,
            heat_demand_json_path=json_path,

            netconfiguration=self.network_config_tab.netconfiguration,
            supply_temperature_control=self.network_config_tab.supplyTemperatureControlInput.currentText(),
            max_supply_temperature_heat_generator=self.network_config_tab.max_supply_temperature,
            min_supply_temperature_heat_generator=self.network_config_tab.min_supply_temperature,
            max_air_temperature_heat_generator=self.network_config_tab.max_air_temperature,
            min_air_temperature_heat_generator=self.network_config_tab.min_air_temperature,
            flow_pressure_pump=flow_pressure_pump,
            lift_pressure_pump=lift_pressure_pump,
            min_supply_temperature_building_checked=self.network_config_tab.min_supply_temperature_building_checked,
            min_supply_temperature_building=min_supply_temperature_building,
            fixed_return_temperature_heat_consumer_checked=self.network_config_tab.return_temp_checked,
            fixed_return_temperature_heat_consumer=fixed_return_temperature_heat_consumer,
            dT_RL=dT_RL,
            building_temperature_checked=self.network_config_tab.building_temp_checked,
            pipetype=pipetype,

            diameter_optimization_pipe_checked=self.diameter_optimization_tab.DiameterOpt_ckecked,
            max_velocity_pipe=v_max_pipe,
            material_filter_pipe=material_filter,
            k_mm_pipe=k_mm,

            main_producer_location_index=main_producer_location_index,
            secondary_producers=[SecondaryProducer(**sp) for sp in secondary_producers],
        )
        
        if self.generate_callback:
            print("Calling generate_callback with data:", vars(data))
            self.generate_callback(data)

        self.accept()