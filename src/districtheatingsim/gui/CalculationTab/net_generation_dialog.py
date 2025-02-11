"""
Filename: net_generation_dialog.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-11
Description: Contains the NetGenerationDialog class.
"""

from PyQt5.QtWidgets import QVBoxLayout, QDialog, QPushButton, QTabWidget
from PyQt5.QtCore import Qt

from districtheatingsim.gui.CalculationTab.network_data_tab import NetworkDataTab
from districtheatingsim.gui.CalculationTab.producer_order_tab import ProducerOrderTab
from districtheatingsim.gui.CalculationTab.network_config_tab import NetworkConfigTab
from districtheatingsim.gui.CalculationTab.diameter_optimization_tab import DiameterOptimizationTab
        
class NetGenerationDialog(QDialog):
    def __init__(self, generate_callback, base_path, parent=None):
        super().__init__(parent)
        self.generate_callback = generate_callback
        self.base_path = base_path
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Netz generieren")
        self.resize(1000, 800)

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.network_data_tab = NetworkDataTab(self.base_path, self)
        self.producer_order_tab = ProducerOrderTab(self)
        self.network_config_tab = NetworkConfigTab(self)
        self.diameter_optimization_tab = DiameterOptimizationTab(self)

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
        import_type = self.network_data_tab.importTypeComboBox.currentText()
        if import_type == "GeoJSON":
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

        supply_temperature_net = self.network_config_tab.calculateTemperatureCurve()
        flow_pressure_pump = float(self.network_config_tab.parameter_rows_net[5].itemAt(1).widget().text())
        lift_pressure_pump = float(self.network_config_tab.parameter_rows_net[6].itemAt(1).widget().text())

        if self.network_config_tab.supply_temperature_heat_consumer_checked == True:
            supply_temperature_heat_consumer = float(self.network_config_tab.parameter_rows_heat_consumer[0].itemAt(1).widget().text())
        else:
            supply_temperature_heat_consumer = None  
              
        if self.network_config_tab.return_temp_checked == True:
            rl_temp_heat_consumer = float(self.network_config_tab.parameter_rows_heat_consumer[1].itemAt(1).widget().text())
        else:
            rl_temp_heat_consumer = None

        dT_RL = float(self.network_config_tab.parameter_rows_heat_consumer[2].itemAt(1).widget().text())

        # Ermitteln des Index des Haupterzeugers, wenn keiner dann 0
        if self.network_config_tab.producer_order_list_widget.count() > 0:
            main_producer_location_index = self.network_config_tab.producer_order_list_widget.item(0).data(Qt.UserRole)['index']
        else:
            main_producer_location_index = 0

        ### hier muss der path für die JSON mit den Lastgängen ergänzt werden ###
        # Führen Sie die Netzgenerierung für GeoJSON durch
        if self.generate_callback:
            self.generate_callback(vorlauf_path, ruecklauf_path, hast_path, erzeugeranlagen_path, json_path, supply_temperature_heat_consumer, 
                                   rl_temp_heat_consumer, supply_temperature_net, flow_pressure_pump, lift_pressure_pump, self.network_config_tab.netconfiguration, 
                                   dT_RL, self.network_config_tab.building_temp_checked, pipetype, v_max_pipe, material_filter, self.diameter_optimization_tab.DiameterOpt_ckecked, 
                                   k_mm, main_producer_location_index, import_type)

        self.accept()