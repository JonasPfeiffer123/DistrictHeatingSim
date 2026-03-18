"""
Energy System Main Tab Module
==============================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Main tab for managing energy system design, including technology definitions, cost calculations, and results display.
"""

import traceback
import numpy as np
import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QTabWidget,
                             QMessageBox, QMenuBar, QScrollArea, QDialog, QLabel,
                             QComboBox, QPushButton, QInputDialog)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal, QEventLoop

from districtheatingsim.net_simulation_pandapipes.pp_net_time_series_simulation import import_results_csv
from districtheatingsim.utilities.test_reference_year import import_TRY

from districtheatingsim.gui.EnergySystemTab._02_energy_system_dialogs import EconomicParametersDialog, WeightDialog
from districtheatingsim.gui.EnergySystemTab._06_calculate_energy_system_thread import CalculateEnergySystemThread
from districtheatingsim.gui.EnergySystemTab._03_technology_tab import TechnologyTab
from districtheatingsim.gui.EnergySystemTab._05_cost_tab import CostTab
from districtheatingsim.gui.EnergySystemTab._07_results_tab import ResultsTab
from districtheatingsim.gui.EnergySystemTab._08_sensitivity_tab import SensitivityTab
from districtheatingsim.gui.EnergySystemTab._09_sankey_dialog import SankeyDialog
from districtheatingsim.heat_generators.energy_system import EnergySystem


def _config_name_to_filename(config_name: str) -> str:
    """Convert a display config name to the corresponding JSON filename."""
    if config_name == "Standard":
        return "Ergebnisse.json"
    safe = config_name.replace("/", "-").replace("\\", "-").replace(":", "-")
    return f"Ergebnisse_{safe}.json"


def _filename_to_config_name(filename: str) -> str:
    """Convert a JSON filename back to a display config name."""
    if filename == "Ergebnisse.json":
        return "Standard"
    # Strip "Ergebnisse_" prefix and ".json" suffix
    return filename[len("Ergebnisse_"):-len(".json")]


class EnergySystemTab(QWidget):
    """
    Main tab for defining and managing energy mix design for heat generation projects.

    :signal data_added: Signal emitted when new data is added.
    """
    data_added = pyqtSignal(object)  # Signal that transfers data as an object
    
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize the EnergySystemTab.

        :param folder_manager: Folder manager instance.
        :type folder_manager: object
        :param data_manager: Data manager instance.
        :type data_manager: object
        :param config_manager: Configuration manager instance.
        :type config_manager: object
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.parent_object = parent
        self.results = {}
        self._active_config_name = "Standard"

        self.initDialogs()
        self.setupParameters()
        self.initUI()

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

    def initDialogs(self):
        """
        Initialize dialogs for economic parameters.
        """
        self.economicParametersDialog = EconomicParametersDialog(self)

    def updateDefaultPath(self, new_base_path):
        """
        Update project default path and refresh the config selector.

        :param new_base_path: New base path for the project (variant folder).
        :type new_base_path: str
        """
        self.base_path = new_base_path
        self._refresh_config_combo()

    def initUI(self):
        """
        Initialize user interface components.
        """
        self.createMainScrollArea()
        self.createMenu()
        self.createConfigBar()
        self.createTabs()
        self.createProgressBar()
        self.setLayout(self.createMainLayout())

    def createMainScrollArea(self):
        """
        Create main scroll area for the tab.
        """
        self.mainScrollArea = QScrollArea(self)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.mainScrollArea.setWidget(self.mainWidget)

    def createMenu(self):
        """
        Create menu bar for the tab.
        """
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)

        # 'Datei'-Menü
        fileMenu = self.menuBar.addMenu('Datei')
        saveJSONAction = QAction('Ergebnisse als JSON speichern', self)
        saveJSONAction.triggered.connect(self.save_results_JSON)
        fileMenu.addAction(saveJSONAction)

        loadJSONAction = QAction('Ergebnisse aus JSON laden', self)
        loadJSONAction.triggered.connect(self.load_results_JSON)
        fileMenu.addAction(loadJSONAction)

        fileMenu.addSeparator()
        exportCSVAction = QAction('Ergebnisse als CSV exportieren...', self)
        exportCSVAction.triggered.connect(self.save_heat_generation_results_to_csv)
        fileMenu.addAction(exportCSVAction)

        # 'Einstellungen'-Menü
        settingsMenu = self.menuBar.addMenu('Einstellungen')
        settingsMenu.addAction(self.createAction('Wirtschaftliche Parameter...', self.openEconomicParametersDialog))

        addHeatGeneratorMenu = self.menuBar.addMenu('Wärmeerzeuger hinzufügen')

        heatGenerators = ["Solarthermie", "BHKW", "Holzgas-BHKW", "Geothermie", "Abwärmepumpe", "Flusswärmepumpe", "Biomassekessel", "Gaskessel", "Power-to-Heat"] # AqvaHeat could be added here
        for generator in heatGenerators:
            action = QAction(generator, self)
            action.triggered.connect(lambda checked, gen=generator: self.techTab.addTech(gen, None))
            addHeatGeneratorMenu.addAction(action)

        addstorageMenu = self.menuBar.addMenu('Speicher hinzufügen')
        storageTypes = ["Saisonaler Wärmespeicher"]
        for storage in storageTypes:
            action = QAction(storage, self)
            action.triggered.connect(lambda checked, stor=storage: self.techTab.addTech(stor, None))
            addstorageMenu.addAction(action)

        # 'Berechnungen'-Menü
        calculationsMenu = self.menuBar.addMenu('Berechnungen')
        calculationsMenu.addAction(self.createAction('Berechnen', self.calculate_energy_system))
        calculationsMenu.addAction(self.createAction('Optimieren', self.start_optimization))

        # 'weitere Ergebnisse Anzeigen'-Menü
        showAdditionalResultsMenu = self.menuBar.addMenu('weitere Ergebnisse Anzeigen')
        showAdditionalResultsMenu.addAction(self.createAction('Sankey-Diagramm Energieflüsse im Quartier', self.show_sankey))

        self.mainLayout.addWidget(self.menuBar)

    def createAction(self, title, method):
        """
        Create a menu action.

        :param title: Action title.
        :type title: str
        :param method: Method to be called when triggered.
        :type method: function
        :return: Created action.
        :rtype: QAction
        """
        action = QAction(title, self)
        action.triggered.connect(method)
        return action

    def createTabs(self):
        """
        Create tab widget and its sub-tabs.
        """
        self.tabWidget = QTabWidget()
        self.techTab = TechnologyTab(self.folder_manager, self.config_manager, self)
        self.costTab = CostTab(self.folder_manager, self.config_manager, self)
        self.resultTab = ResultsTab(self.folder_manager, self)
        self.sensitivityTab = SensitivityTab(self.folder_manager, self)
        self.tabWidget.addTab(self.techTab, "Erzeugerdefinition")
        self.tabWidget.addTab(self.costTab, "Kostenübersicht")
        self.tabWidget.addTab(self.resultTab, "Ergebnisse")
        self.tabWidget.addTab(self.sensitivityTab, "Sensivitätsuntersuchung")
        self.mainLayout.addWidget(self.tabWidget)

    def createProgressBar(self):
        """
        Create progress bar for calculation progress.
        """
        self.progressBar = QProgressBar(self)
        self.mainLayout.addWidget(self.progressBar)

    def createConfigBar(self):
        """Create the energy config selector bar (ComboBox + action buttons)."""
        self.configBar = QWidget()
        bar_layout = QHBoxLayout(self.configBar)
        bar_layout.setContentsMargins(4, 2, 4, 2)

        bar_layout.addWidget(QLabel("Erzeugerkonfiguration:"))

        self.configCombo = QComboBox()
        self.configCombo.setMinimumWidth(200)
        self.configCombo.setToolTip("Aktive Erzeugerkonfiguration auswählen")
        self.configCombo.currentIndexChanged.connect(self._on_config_selected)
        bar_layout.addWidget(self.configCombo)

        btn_new = QPushButton("Neu")
        btn_new.setToolTip("Neue leere Konfiguration anlegen")
        btn_new.clicked.connect(self._new_config_action)
        bar_layout.addWidget(btn_new)

        btn_save_as = QPushButton("Speichern als...")
        btn_save_as.setToolTip("Aktuelle Konfiguration unter neuem Namen speichern")
        btn_save_as.clicked.connect(self._save_as_config_action)
        bar_layout.addWidget(btn_save_as)

        btn_delete = QPushButton("Löschen")
        btn_delete.setToolTip("Aktuelle Konfiguration löschen")
        btn_delete.clicked.connect(self._delete_config_action)
        bar_layout.addWidget(btn_delete)

        bar_layout.addStretch()

    def createMainLayout(self):
        """
        Create main layout for the tab.

        :return: Main layout.
        :rtype: QVBoxLayout
        """
        layout = QVBoxLayout(self)
        layout.addWidget(self.menuBar)
        layout.addWidget(self.configBar)
        layout.addWidget(self.mainScrollArea)
        return layout

    # ── Config management ────────────────────────────────────────────────────

    def _ergebnisse_dir(self) -> str:
        """Return the Ergebnisse subfolder for the current variant."""
        return os.path.join(self.base_path, "Ergebnisse") if self.base_path else ""

    def _discover_configs(self) -> list:
        """
        Scan the Ergebnisse folder and return (display_name, filename) pairs.

        ``Ergebnisse.json`` always appears first as ``"Standard"``.
        """
        ergebnisse_dir = self._ergebnisse_dir()
        configs = []
        if os.path.isdir(ergebnisse_dir):
            files = sorted(os.listdir(ergebnisse_dir))
            if "Ergebnisse.json" in files:
                configs.append(("Standard", "Ergebnisse.json"))
            for f in files:
                if f.startswith("Ergebnisse_") and f.endswith(".json"):
                    configs.append((_filename_to_config_name(f), f))
        if not configs:
            configs = [("Standard", "Ergebnisse.json")]
        return configs

    def _refresh_config_combo(self):
        """Repopulate the config ComboBox; restore saved active selection."""
        self.configCombo.blockSignals(True)
        self.configCombo.clear()
        configs = self._discover_configs()
        for name, _ in configs:
            self.configCombo.addItem(name)

        # Restore the saved active config for this variant
        saved = self.folder_manager.get_active_energy_config(self.base_path) if self.base_path else "Standard"
        idx = self.configCombo.findText(saved)
        if idx >= 0:
            self.configCombo.setCurrentIndex(idx)
            self._active_config_name = saved
        else:
            self._active_config_name = configs[0][0] if configs else "Standard"

        # Show selection dialog only when multiple configs exist and no saved preference
        configs_on_disk = [c for c in configs if c[0] != "Standard" or
                           os.path.exists(os.path.join(self._ergebnisse_dir(), "Ergebnisse.json"))]
        if len(configs_on_disk) > 1 and idx < 0:
            self.configCombo.blockSignals(False)
            self._ask_which_config(configs)
            return

        self.configCombo.blockSignals(False)

    def _ask_which_config(self, configs: list):
        """Show a selection dialog when multiple configs exist and no preference is saved."""
        names = [name for name, _ in configs]
        chosen, ok = QInputDialog.getItem(
            self, "Erzeugerkonfiguration wählen",
            "Mehrere Konfigurationen vorhanden.\nWelche soll geladen werden?",
            names, 0, False
        )
        if ok and chosen:
            idx = self.configCombo.findText(chosen)
            if idx >= 0:
                self.configCombo.setCurrentIndex(idx)
            self._active_config_name = chosen
            self.folder_manager.set_active_energy_config(self.base_path, chosen)

    def _on_config_selected(self, index: int):
        """Handle combo-box selection change — persist and load the selected config."""
        if index < 0:
            return
        name = self.configCombo.itemText(index)
        if name == self._active_config_name:
            return
        self._active_config_name = name
        if self.base_path:
            self.folder_manager.set_active_energy_config(self.base_path, name)
        # Load the config if a file already exists for it
        filepath = os.path.join(self._ergebnisse_dir(), _config_name_to_filename(name))
        if os.path.exists(filepath):
            self.load_results_JSON(show_dialog=False)

    def _new_config_action(self):
        """Create a new (unsaved) configuration by clearing the current state."""
        name, ok = QInputDialog.getText(self, "Neue Konfiguration", "Name der neuen Konfiguration:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name == "Standard":
            QMessageBox.warning(self, "Ungültiger Name", "'Standard' ist reserviert.")
            return
        # Check for duplicate
        existing = [n for n, _ in self._discover_configs()]
        if name in existing:
            QMessageBox.warning(self, "Bereits vorhanden",
                                f"Eine Konfiguration mit dem Namen '{name}' existiert bereits.")
            return
        # Set as active (no file written yet) and clear tech list
        self._active_config_name = name
        self.configCombo.blockSignals(True)
        self.configCombo.addItem(name)
        self.configCombo.setCurrentText(name)
        self.configCombo.blockSignals(False)
        if self.base_path:
            self.folder_manager.set_active_energy_config(self.base_path, name)
        # Clear the technology scene
        self.techTab.tech_objects.clear()
        self.techTab.rebuildScene()
        self.techTab.updateTechList()

    def _save_as_config_action(self):
        """Save the current energy system under a new config name."""
        name, ok = QInputDialog.getText(
            self, "Konfiguration speichern als", "Name der Konfiguration:",
            text=self._active_config_name if self._active_config_name != "Standard" else ""
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        self._active_config_name = name
        self.configCombo.blockSignals(True)
        if self.configCombo.findText(name) < 0:
            self.configCombo.addItem(name)
        self.configCombo.setCurrentText(name)
        self.configCombo.blockSignals(False)
        if self.base_path:
            self.folder_manager.set_active_energy_config(self.base_path, name)
        self.save_results_JSON(show_dialog=True)

    def _delete_config_action(self):
        """Delete the active configuration file (Standard cannot be deleted)."""
        name = self._active_config_name
        if name == "Standard":
            QMessageBox.warning(self, "Nicht möglich",
                                "Die Standardkonfiguration kann nicht gelöscht werden.")
            return
        reply = QMessageBox.question(
            self, "Konfiguration löschen",
            f"Konfiguration '{name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        filepath = os.path.join(self._ergebnisse_dir(), _config_name_to_filename(name))
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError as e:
            QMessageBox.critical(self, "Fehler", f"Datei konnte nicht gelöscht werden:\n{e}")
            return
        self._active_config_name = "Standard"
        if self.base_path:
            self.folder_manager.set_active_energy_config(self.base_path, "Standard")
        self._refresh_config_combo()

    # ── Input Economic Parameters ────────────────────────────────────────────
    def setupParameters(self):
        """
        Set up economic parameters.
        """
        self.updateEconomicParameters()

    def updateEconomicParameters(self):
        """
        Update economic parameters from dialog.
        """

        self.economic_parameters = self.economicParametersDialog.getValues()

    ### Dialogs ###
    def openEconomicParametersDialog(self):
        """
        Open economic parameters dialog.
        """
        if self.economicParametersDialog.exec():
            self.updateEconomicParameters()

    ### Calculation Functions ###
    def validateInputs(self):
        """
        Validate inputs for calculation.

        :return: True if inputs are valid, False otherwise.
        :rtype: bool
        """
        try:
            load_scale_factor = float(self.techTab.load_scale_factorInput.text())
            if load_scale_factor <= 0:
                raise ValueError("Der Skalierungsfaktor muss größer als 0 sein.")
        except ValueError as e:
            QMessageBox.warning(self, "Ungültige Eingabe", str(e))
            return False
        return True
    
    def preprocessData(self):
        """
        Preprocess data before calculation.
        """
        self.csv_filename = self.techTab.FilenameInput.text()
        self.TRY_filename = self.data_manager.try_filename
        self.COP_filename = self.data_manager.cop_filename
        self.load_scale_factor = float(self.techTab.load_scale_factorInput.text())

        # Import data from the CSV file
        time_steps, waerme_ges_kW, strom_wp_kW, pump_results = import_results_csv(self.csv_filename)
        self.TRY_data = import_TRY(self.TRY_filename)
        self.COP_data = np.genfromtxt(self.COP_filename, delimiter=';')

        # Collect qext_kW values from pump results
        qext_values = []
        for pump_type, pumps in pump_results.items():
            for idx, pump_data in pumps.items():
                if 'qext_kW' in pump_data:
                    qext_values.append(pump_data['qext_kW'])

                if pump_type == "Heizentrale Haupteinspeisung":
                    flow_temp_circ_pump = pump_data['flow_temp']
                    return_temp_circ_pump = pump_data['return_temp']

        if qext_values:
            qext_kW = np.sum(np.array(qext_values), axis=0)
        else:
            qext_kW = np.array([])

        qext_kW *= self.load_scale_factor

        # Create the energy system object
        self.energy_system = EnergySystem(
            time_steps=time_steps,
            load_profile=qext_kW,
            VLT_L=flow_temp_circ_pump,
            RLT_L=return_temp_circ_pump,
            TRY_data=self.TRY_data,
            COP_data=self.COP_data,
            economic_parameters=self.economic_parameters,
        )

        # Add technologies to the system
        for tech in self.techTab.tech_objects:
            self.energy_system.add_technology(tech)

        self.energy_system.results["waerme_ges_kW"] = waerme_ges_kW
        self.energy_system.results["strom_wp_kW"] = strom_wp_kW

        self.costTab.updateInfrastructureTable()
        self.energy_system.results["infrastructure_cost"]  = self.costTab.data

    def calculate_energy_system(self, optimize=False, weights=None):
        """
        Start calculation process.

        :param optimize: Whether to optimize the calculation.
        :type optimize: bool
        :param weights: Weights for optimization.
        :type weights: dict
        """
        
        self.optimize = optimize

        if not self.validateInputs():
            return

        if self.techTab.tech_objects:
            self.preprocessData()

            self.calculationThread = CalculateEnergySystemThread(self.energy_system, self.optimize, weights)
            
            self.calculationThread.calculation_done.connect(self.on_calculation_done)
            self.calculationThread.calculation_error.connect(self.on_calculation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)
        else:
            QMessageBox.information(self, "Keine Erzeugeranlagen", "Es wurden keine Erzeugeranlagen definiert. Keine Berechnung möglich.")

    def start_optimization(self):
        """
        Open optimization dialog and start optimization process.
        """
        dialog = WeightDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            weights = dialog.get_weights()
            self.calculate_energy_system(True, weights)

    def on_calculation_done(self, result):
        """
        Handle calculation completion.

        :param result: Calculation results.
        :type result: dict
        """
        self.progressBar.setRange(0, 1)
        self.energy_system = result[0]

        if self.optimize:
            self.optimized_energy_system = result[1]
            self.energy_system = self.optimized_energy_system
            
        self.process_data()

    def on_calculation_error(self, error_message):
        """
        Handle calculation errors.

        :param error_message: Error message.
        :type error_message: str
        """
        self.progressBar.setRange(0, 1)
        QMessageBox.critical(self, "Berechnungsfehler", str(error_message))

    def process_data(self):
        # Update economic parameters with saved parameters from energy system class
        self.economicParametersDialog.updateValues(self.energy_system.economic_parameters)
        self.updateEconomicParameters()

        # Update the tech objects from the loaded EnergySystem
        self.techTab.tech_objects = self.energy_system.technologies + [self.energy_system.storage] if self.energy_system.storage else self.energy_system.technologies
        self.techTab.rebuildScene()
        self.techTab.updateTechList()

        # Lade den gespeicherten Infrastrukturkosten-DataFrame
        if "infrastructure_cost" in self.energy_system.results:
            self.costTab.data = self.energy_system.results["infrastructure_cost"]
            self.costTab.updateInfrastructureTable()  # Aktualisiere die Tabelle mit den neuen Daten


        self.costTab.updateTechDataTable(self.energy_system.technologies)
        self.costTab.updateSumLabel()
        self.costTab.plotCostComposition()
        self.resultTab.updateResults(self.energy_system)

    def sensitivity(self, gas_range, electricity_range, wood_range, weights=None):
        """
        Perform sensitivity analysis over a range of prices.

        :param gas_range: Range of gas prices (lower, upper, num_points).
        :type gas_range: tuple
        :param electricity_range: Range of electricity prices (lower, upper, num_points).
        :type electricity_range: tuple
        :param wood_range: Range of wood prices (lower, upper, num_points).
        :type wood_range: tuple
        :param weights: Weights for optimization.
        :type weights: dict
        """
        if not self.validateInputs():
            return

        if not self.techTab.tech_objects:
            QMessageBox.information(self, "Keine Erzeugeranlagen", "Es wurden keine Erzeugeranlagen definiert. Keine Berechnung möglich.")
            return
        
        if not self.energy_system.technologies:
            QMessageBox.information(self, "Keine Erzeugeranlagen im EnergySystem", "Im EnergySystem sind keine Erzeugeranlagen definiert. Keine Berechnung möglich.")
            return
                
        results = []
        for gas_price in self.generate_values(gas_range):
            for electricity_price in self.generate_values(electricity_range):
                for wood_price in self.generate_values(wood_range):
                    result = self.calculate_sensitivity(gas_price, electricity_price, wood_price, weights)
                    waerme_ges_kW, strom_wp_kW = np.sum(result["waerme_ges_kW"]), np.sum(result["strom_wp_kW"])
                    wgk_heat_pump_electricity = ((strom_wp_kW/1000) * electricity_price) / ((strom_wp_kW+waerme_ges_kW)/1000)
                    if result is not None:
                        results.append({
                            'gas_price': gas_price,
                            'electricity_price': electricity_price,
                            'wood_price': wood_price,
                            'WGK_Gesamt': result['WGK_Gesamt'],
                            'waerme_ges_kW': waerme_ges_kW,
                            'strom_wp_kW': strom_wp_kW,
                            'wgk_heat_pump_electricity': wgk_heat_pump_electricity
                        })

        self.sensitivityTab.plotSensitivity(results)
        self.sensitivityTab.plotSensitivitySurface(results)

    def generate_values(self, price_range):
        """
        Generate values within a specified range.

        :param price_range: Price range (lower, upper, num_points).
        :type price_range: tuple
        :return: Generated values within the range.
        :rtype: list
        """
        lower, upper, num_points = price_range
        step = (upper - lower) / (num_points - 1)
        return [lower + i * step for i in range(num_points)]

    def calculate_sensitivity(self, gas_price, electricity_price, wood_price, weights):
        """
        Calculate energy mix for given prices and weights.

        :param gas_price: Gas price.
        :type gas_price: float
        :param electricity_price: Electricity price.
        :type electricity_price: float
        :param wood_price: Wood price.
        :type wood_price: float
        :param weights: Weights for optimization.
        :type weights: dict
        :return: Calculation results.
        :rtype: dict
        """
        result = None
        calculation_done_event = QEventLoop()
        
        def calculation_done(energy_system):
            self.progressBar.setRange(0, 1)
            nonlocal result
            result = energy_system[0].results
            calculation_done_event.quit()

        def calculation_error(error_message):
            self.progressBar.setRange(0, 1)
            QMessageBox.critical(self, "Berechnungsfehler", str(error_message))
            calculation_done_event.quit()

        economic_parameters = self.economic_parameters.copy()
        economic_parameters["gas_price"] = gas_price
        economic_parameters["electricity_price"] = electricity_price
        economic_parameters["wood_price"] = wood_price

        self.energy_system.economic_parameters = economic_parameters

        self.calculationThread = CalculateEnergySystemThread(self.energy_system, False,  weights)
        
        self.calculationThread.calculation_done.connect(calculation_done)
        self.calculationThread.calculation_error.connect(calculation_error)
        self.calculationThread.start()
        self.progressBar.setRange(0, 0)
        calculation_done_event.exec()  # Wait for the thread to finish

        # Ensure the thread has finished before returning
        self.calculationThread.wait()

        return result

    # Show Sankey Diagram
    def show_sankey(self):
        """
        Show Sankey diagram of energy flows.
        """
        if self.techTab.tech_objects and self.energy_system.results:
            dialog = SankeyDialog(results=self.energy_system.results, parent=self)
            dialog.exec()
        else:
            if not self.techTab.tech_objects:
                QMessageBox.information(self, "Keine Erzeugeranlagen", "Es wurden keine Erzeugeranlagen definiert. Keine Berechnung möglich.")
            elif not self.results:
                QMessageBox.information(self, "Keine Berechnungsergebnisse", "Es sind keine Berechnungsergebnisse verfügbar. Führen Sie zunächst eine Berechnung durch.")
            
    ### Save Calculation Results ###
    def save_heat_generation_results_to_csv(self, show_dialog=True):
        """
        Save heat generation results to CSV file.

        :param show_dialog: Whether to show dialogs.
        :type show_dialog: bool
        """
        if not self.energy_system or not self.energy_system.results:
            if show_dialog:
                QMessageBox.warning(self, "Keine Daten vorhanden", "Es sind keine Berechnungsergebnisse vorhanden, die gespeichert werden könnten.")
            return

        try:
            csv_filename = os.path.join(self.base_path, self.config_manager.get_relative_path('calculated_heat_generation_path'))
            self.energy_system.save_to_csv(csv_filename)
            if show_dialog:
                QMessageBox.information(self, "Erfolgreich gespeichert", f"Die Ergebnisse wurden erfolgreich unter {csv_filename} gespeichert.")
        except Exception as e:
            if show_dialog:
                QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der CSV-Datei: {e}")

    def _active_json_path(self) -> str:
        """Return the full path to the active config's JSON file."""
        ergebnisse_dir = self._ergebnisse_dir()
        os.makedirs(ergebnisse_dir, exist_ok=True)
        return os.path.join(ergebnisse_dir, _config_name_to_filename(self._active_config_name))

    def save_results_JSON(self, show_dialog=True):
        """
        Save results and technology objects to the active config JSON file.

        :param show_dialog: Whether to show dialogs.
        :type show_dialog: bool
        """
        if not hasattr(self, 'energy_system') or not self.energy_system or not self.energy_system.results:
            if show_dialog:
                QMessageBox.warning(self, "Keine Daten vorhanden",
                                    "Es sind keine Berechnungsergebnisse vorhanden, die gespeichert werden könnten.")
            return

        try:
            json_filename = self._active_json_path()
            self.energy_system.save_to_json(json_filename)
            # Refresh combo in case a new file was created
            self._refresh_config_combo()
            if show_dialog:
                QMessageBox.information(self, "Erfolgreich gespeichert",
                                        f"Konfiguration '{self._active_config_name}' gespeichert unter:\n{json_filename}")
        except Exception as e:
            error_details = traceback.format_exc()
            if show_dialog:
                QMessageBox.critical(self, "Speicherfehler",
                                     f"Fehler beim Speichern der JSON-Datei: {e}\n\nDetails:\n{error_details}")

    def load_results_JSON(self, show_dialog=True):
        """
        Load EnergySystem from the active config JSON file.

        :param show_dialog: Whether to show success/error dialogs.
        :type show_dialog: bool
        """
        json_filename = self._active_json_path()
        if not os.path.exists(json_filename):
            if show_dialog:
                QMessageBox.warning(self, "Datei nicht gefunden",
                                    f"Keine gespeicherte Konfiguration gefunden:\n{json_filename}")
            return

        try:
            self.energy_system = EnergySystem.load_from_json(json_filename)
            self.process_data()
            if show_dialog:
                QMessageBox.information(self, "Erfolgreich geladen",
                                        f"Konfiguration '{self._active_config_name}' geladen.")
        except ValueError as e:
            if show_dialog:
                QMessageBox.critical(self, "Ladefehler", str(e))

