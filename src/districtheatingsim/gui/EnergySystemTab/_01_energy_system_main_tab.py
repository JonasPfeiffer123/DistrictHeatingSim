"""
Energy System Main Tab Module
=============================

This module contains the main tab for managing the energy system design, including technology definitions, cost calculations, and results display.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-04-19
"""

import traceback
import numpy as np
import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QProgressBar, QTabWidget, QMessageBox, QMenuBar, QScrollArea, QDialog)
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

class EnergySystemTab(QWidget):
    """
    The MixDesignTab class represents the tab responsible for defining and managing the design of energy mix 
    for a heat generation project.

    Attributes:
        data_added (pyqtSignal): Signal emitted when new data is added.
        data_manager (object): Reference to the data manager instance.
        parent (QWidget): Reference to the parent widget.
        results (dict): Stores results data.
        tech_objects (list): List of technology objects.
        economicParametersDialog (EconomicParametersDialog): Dialog for economic parameters.
        base_path (str): Base path for the project.
        gaspreis (float): Gas price in €/MWh.
        strompreis (float): Electricity price in €/MWh.
        holzpreis (float): Wood price in €/MWh.
        BEW (str): BEW funding consideration.
        kapitalzins (float): Capital interest rate in %.
        preissteigerungsrate (float): Price increase rate in %.
        betrachtungszeitraum (int): Consideration period in years.
        stundensatz (float): Hourly rate in €/h.
        filename (str): Filename for data import.
        load_scale_factor (float): Load scale factor.
        TRY_data (array): Test reference year data.
        COP_data (array): Coefficient of performance data.
        calculationThread (CalculateMixThread): Thread for mix calculation.
        menuBar (QMenuBar): Menu bar for the tab.
        tabWidget (QTabWidget): Tab widget to hold different sub-tabs.
        techTab (TechnologyTab): Tab for technology definitions.
        costTab (CostTab): Tab for cost overview.
        resultTab (ResultsTab): Tab for results display.
        sensitivityTab (SensitivityTab): Tab for sensitivity analysis.
        progressBar (QProgressBar): Progress bar for showing calculation progress.
    """
    data_added = pyqtSignal(object)  # Signal that transfers data as an object
    
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initializes the MixDesignTab instance.

        Args:
            data_manager (object): Reference to the data manager instance.
            parent (QWidget, optional): Reference to the parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.parent_object = parent
        self.results = {}
        
        self.initDialogs()
        self.setupParameters()
        self.initUI()

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.variant_folder)

    def initDialogs(self):
        """
        Initializes the dialogs for economic and infrastructure parameters.
        """
        self.economicParametersDialog = EconomicParametersDialog(self)

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path

    def initUI(self):
        """
        Initializes the user interface components for the MixDesignTab.
        """
        self.createMainScrollArea()
        self.createMenu()
        self.createTabs()
        self.createProgressBar()
        self.setLayout(self.createMainLayout())

    def createMainScrollArea(self):
        """
        Creates the main scroll area for the tab.
        """
        self.mainScrollArea = QScrollArea(self)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.mainScrollArea.setWidget(self.mainWidget)

    def createMenu(self):
        """
        Creates the menu bar for the tab.
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
        Creates a menu action.

        Args:
            title (str): The title of the action.
            method (function): The method to be called when the action is triggered.

        Returns:
            QAction: The created action.
        """
        action = QAction(title, self)
        action.triggered.connect(method)
        return action

    def createTabs(self):
        """
        Creates the tab widget and its sub-tabs.
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
        Creates the progress bar for showing calculation progress.
        """
        self.progressBar = QProgressBar(self)
        self.mainLayout.addWidget(self.progressBar)

    def createMainLayout(self):
        """
        Creates the main layout for the tab.

        Returns:
            QVBoxLayout: The main layout for the tab.
        """
        layout = QVBoxLayout(self)
        layout.addWidget(self.menuBar)
        layout.addWidget(self.mainScrollArea)
        return layout

    ### Input Economic Parameters ###
    def setupParameters(self):
        """
        Sets up the economic parameters.
        """
        self.updateEconomicParameters()

    def updateEconomicParameters(self):
        """
        Updates the economic parameters from the dialog.
        """

        self.economic_parameters = self.economicParametersDialog.getValues()

    ### Dialogs ###
    def openEconomicParametersDialog(self):
        """
        Opens the economic parameters dialog.
        """
        if self.economicParametersDialog.exec():
            self.updateEconomicParameters()

    ### Calculation Functions ###
    def validateInputs(self):
        """
        Validates the inputs for the calculation.

        Returns:
            bool: True if inputs are valid, False otherwise.
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
        Preprocesses the data before calculation.
        """
        self.csv_filename = self.techTab.FilenameInput.text()
        self.TRY_filename = self.data_manager.get_try_filename()
        self.COP_filename = self.data_manager.get_cop_filename()
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
                else:
                    print(f"Keine qext_kW Daten für {pump_type} Pumpe {idx}")

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
        Starts the calculation process.

        Args:
            optimize (bool, optional): Whether to optimize the calculation. Defaults to False.
            weights (dict, optional): Weights for optimization. Defaults to None.
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
        Opens the optimization dialog and starts the optimization process.
        """
        dialog = WeightDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            weights = dialog.get_weights()
            self.calculate_energy_system(True, weights)

    def on_calculation_done(self, result):
        """
        Handles the completion of the calculation.

        Args:
            result (dict): The results of the calculation.
        """
        self.progressBar.setRange(0, 1)
        self.energy_system = result[0]

        if self.optimize:
            self.optimized_energy_system = result[1]
            self.energy_system = self.optimized_energy_system
            
        self.process_data()

        self.save_heat_generation_results_to_csv()

    def on_calculation_error(self, error_message):
        """
        Handles calculation errors.

        Args:
            error_message (str): The error message.
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
        Performs a sensitivity analysis over a range of prices.

        Args:
            gas_range (tuple): Range of gas prices (lower, upper, num_points).
            electricity_range (tuple): Range of electricity prices (lower, upper, num_points).
            wood_range (tuple): Range of wood prices (lower, upper, num_points).
            weights (dict, optional): Weights for optimization. Defaults to None.
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
        Generates values within a specified range.

        Args:
            price_range (tuple): The price range (lower, upper, num_points).

        Returns:
            list: Generated values within the specified range.
        """
        lower, upper, num_points = price_range
        step = (upper - lower) / (num_points - 1)
        return [lower + i * step for i in range(num_points)]

    def calculate_sensitivity(self, gas_price, electricity_price, wood_price, weights):
        """
        Calculates the energy mix for given prices and weights.

        Args:
            gas_price (float): Gas price.
            electricity_price (float): Electricity price.
            wood_price (float): Wood price.
            weights (dict): Weights for optimization.

        Returns:
            dict: The calculation results.
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
        Shows additional results.
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
        Saves the heat generation results to a CSV file.
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

    def save_results_JSON(self, show_dialog=True):
        """
        Saves the results and technology objects to a JSON file.
        """
        # Check if energy_system attribute exists and has results
        if not hasattr(self, 'energy_system') or not self.energy_system or not self.energy_system.results:
            if show_dialog:
                QMessageBox.warning(self, "Keine Daten vorhanden", "Es sind keine Berechnungsergebnisse vorhanden, die gespeichert werden könnten.")
            return

        try:
            json_filename = os.path.join(self.base_path, self.config_manager.get_relative_path("results_path"))
            self.energy_system.save_to_json(json_filename)
            if show_dialog:
                QMessageBox.information(self, "Erfolgreich gespeichert", f"Die Ergebnisse wurden erfolgreich unter {json_filename} gespeichert.")
        except Exception as e:
            error_details = traceback.format_exc()
            if show_dialog:
                QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der JSON-Datei: {e}\n\nDetails:\n{error_details}")

    def load_results_JSON(self, show_dialog=True):
        """
        Loads the EnergySystem object and its results from a JSON file.
        
        Parameters
        ----------
        show_dialog : bool, optional
            Whether to show success/error dialogs. Default is True.
        """
        json_filename = os.path.join(self.base_path, self.config_manager.get_relative_path("results_path"))
        if not json_filename:
            if show_dialog:
                QMessageBox.warning(self, "Fehler", "Pfad für Ergebnisse konnte nicht ermittelt werden.")
            return

        try:
            # Load the EnergySystem object
            self.energy_system = EnergySystem.load_from_json(json_filename)

            self.process_data()

            if show_dialog:
                QMessageBox.information(self, "Erfolgreich geladen", f"Die Ergebnisse wurden erfolgreich aus {json_filename} geladen.")
        except ValueError as e:
            if show_dialog:
                QMessageBox.critical(self, "Ladefehler", str(e))

