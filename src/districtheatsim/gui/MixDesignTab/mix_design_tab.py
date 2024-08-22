"""
Filename: mix_design_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the MixdesignTab.
"""

import json
import pandas as pd
import traceback
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QProgressBar, QTabWidget, QMessageBox, QFileDialog, QMenuBar, QScrollArea, QAction, QDialog)
from PyQt5.QtCore import pyqtSignal, QEventLoop
from heat_generators.heat_generator_classes import *
from gui.MixDesignTab.mix_design_dialogs import EconomicParametersDialog, NetInfrastructureDialog, WeightDialog
from gui.threads import CalculateMixThread
from gui.results_pdf import create_pdf
from gui.MixDesignTab.technology_tab import TechnologyTab
from gui.MixDesignTab.cost_tab import CostTab
from gui.MixDesignTab.results_tab import ResultsTab
from gui.MixDesignTab.sensitivity_tab import SensitivityTab
from utilities.test_reference_year import import_TRY

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
            if isinstance(obj, (CHP, RiverHeatPump, WasteHeatPump, Geothermal, BiomassBoiler, GasBoiler, SolarThermal)):
                return obj.to_dict()
            return super().default(obj)
        except TypeError as e:
            print(f"Failed to encode {obj} of type {type(obj)}")
            raise e

class MixDesignTab(QWidget):
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
        netInfrastructureDialog (NetInfrastructureDialog): Dialog for infrastructure parameters.
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
    
    def __init__(self, data_manager, parent=None):
        """
        Initializes the MixDesignTab instance.

        Args:
            data_manager (object): Reference to the data manager instance.
            parent (QWidget, optional): Reference to the parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        self.tech_objects = []
        
        self.initDialogs()
        self.setupParameters()
        self.initUI()

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)

    def initDialogs(self):
        """
        Initializes the dialogs for economic and infrastructure parameters.
        """
        self.economicParametersDialog = EconomicParametersDialog(self)
        self.netInfrastructureDialog = NetInfrastructureDialog(self)

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path
        self.netInfrastructureDialog.base_path = self.base_path

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

        pdfAction = QAction('Ergebnisse als PDF speichern', self)
        pdfAction.triggered.connect(self.on_export_pdf_clicked)
        fileMenu.addAction(pdfAction)

        # 'Einstellungen'-Menü
        settingsMenu = self.menuBar.addMenu('Einstellungen')
        settingsMenu.addAction(self.createAction('Wirtschaftliche Parameter...', self.openEconomicParametersDialog))
        settingsMenu.addAction(self.createAction('Infrastrukturkosten...', self.openInfrastructureCostsDialog))

        addHeatGeneratorMenu = self.menuBar.addMenu('Wärmeerzeuger hinzufügen')

        heatGenerators = ["Solarthermie", "BHKW", "Holzgas-BHKW", "Geothermie", "Abwärme", "Flusswasser", "Biomassekessel", "Gaskessel", "AqvaHeat"]
        for generator in heatGenerators:
            action = QAction(generator, self)
            action.triggered.connect(lambda checked, gen=generator: self.techTab.addTech(gen, None))
            addHeatGeneratorMenu.addAction(action)

        # 'Berechnungen'-Menü
        calculationsMenu = self.menuBar.addMenu('Berechnungen')
        calculationsMenu.addAction(self.createAction('Berechnen', self.start_calculation))
        calculationsMenu.addAction(self.createAction('Optimieren', self.optimize))
        #calculationsMenu.addAction(self.createAction('Sensivitätsuntersuchung', self.sensitivity))

        # 'weitere Ergebnisse Anzeigen'-Menü
        showAdditionalResultsMenu = self.menuBar.addMenu('weitere Ergebnisse Anzeigen')
        showAdditionalResultsMenu.addAction(self.createAction('Kostenzusammensetzung über Betrachtungszeitraum', self.show_additional_results))

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
        self.techTab = TechnologyTab(self.data_manager, self)
        self.costTab = CostTab(self.data_manager, self)
        self.resultTab = ResultsTab(self.data_manager, self)
        self.sensitivityTab = SensitivityTab(self.data_manager, self)
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
        values = self.economicParametersDialog.getValues()
        self.gaspreis = values['Gaspreis in €/MWh']
        self.strompreis = values['Strompreis in €/MWh']
        self.holzpreis = values['Holzpreis in €/MWh']
        self.BEW = values['BEW-Förderung']
        self.kapitalzins = values['Kapitalzins in %']
        self.preissteigerungsrate = values['Preissteigerungsrate in %']
        self.betrachtungszeitraum = values['Betrachtungszeitraum in a']
        self.stundensatz = values['Stundensatz in €/h']

    ### Dialogs ###
    def openEconomicParametersDialog(self):
        """
        Opens the economic parameters dialog.
        """
        if self.economicParametersDialog.exec_():
            self.updateEconomicParameters()
            #self.costTab.updateInfrastructureTable()
            #self.costTab.plotCostComposition()
            #self.costTab.updateSumLabel()

    def openInfrastructureCostsDialog(self):
        """
        Opens the infrastructure costs dialog.
        """
        if self.netInfrastructureDialog.exec_():
            self.costTab.updateInfrastructureTable()
            self.costTab.plotCostComposition()
            self.costTab.updateSumLabel()

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

    def start_calculation(self, optimize=False, weights=None):
        """
        Starts the calculation process.

        Args:
            optimize (bool, optional): Whether to optimize the calculation. Defaults to False.
            weights (dict, optional): Weights for optimization. Defaults to None.
        """
        if not self.validateInputs():
            return

        if self.techTab.tech_objects:
            self.filename = self.techTab.FilenameInput.text()
            self.load_scale_factor = float(self.techTab.load_scale_factorInput.text())
            self.TRY_data = import_TRY(self.parent.try_filename)
            self.COP_data = np.genfromtxt(self.parent.cop_filename, delimiter=';')

            self.calculationThread = CalculateMixThread(
                self.filename, self.load_scale_factor, self.TRY_data, self.COP_data, self.gaspreis, 
                self.strompreis, self.holzpreis, self.BEW, self.techTab.tech_objects, optimize, 
                self.kapitalzins, self.preissteigerungsrate, self.betrachtungszeitraum, self.stundensatz, weights)
            
            self.calculationThread.calculation_done.connect(self.on_calculation_done)
            self.calculationThread.calculation_error.connect(self.on_calculation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)
        else:
            QMessageBox.information(self, "Keine Erzeugeranlagen", "Es wurden keine Erzeugeranlagen definiert. Keine Berechnung möglich.")

    def on_calculation_done(self, result):
        """
        Handles the completion of the calculation.

        Args:
            result (dict): The results of the calculation.
        """
        self.progressBar.setRange(0, 1)
        self.results = result
        self.techTab.updateTechList()
        self.costTab.updateInfrastructureTable()  # Ensure the infrastructure table is updated first
        self.costTab.updateTechDataTable(self.techTab.tech_objects)  # Then update the tech table
        self.costTab.updateSumLabel()  # Then update the sum label
        self.costTab.plotCostComposition()
        self.resultTab.showResultsInTable(self.results)
        self.resultTab.showAdditionalResultsTable(self.results)
        self.resultTab.plotResults(self.results)
        self.save_heat_generation_results_to_csv(self.results)
        self.showConfirmationDialog()

    def on_calculation_error(self, error_message):
        """
        Handles calculation errors.

        Args:
            error_message (str): The error message.
        """
        self.progressBar.setRange(0, 1)
        QMessageBox.critical(self, "Berechnungsfehler", str(error_message))

    def showConfirmationDialog(self):
        """
        Shows a confirmation dialog after a successful calculation.
        """
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(f"Die Berechnung des Erzeugermixes war erfolgreich. Die Ergebnisse wurden unter {self.base_path}\Lastgang\\results.csv gespeichert.")
        msgBox.setWindowTitle("Berechnung Erfolgreich")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def show_additional_results(self):
        """
        Shows additional results.
        """
        if self.tech_objects and self.results:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(f"Hier gibts noch nichts zu sehen. Nur Konsolenausgabe.")
            msgBox.setWindowTitle("Hier könnten Ergebnisse Visualisiert werden.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()
            print(self.results)
            print(self.tech_objects)
        else:
            QMessageBox.information(self, "Keine Berechnungsergebnisse", "Es sind keine Berechnungsergebnisse verfügbar. Führen Sie zunächst eine Berechnung durch.")

    def optimize(self):
        """
        Opens the optimization dialog and starts the optimization process.
        """
        dialog = WeightDialog()
        if dialog.exec_() == QDialog.Accepted:
            weights = dialog.get_weights()
            self.start_calculation(True, weights)

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

        self.filename = self.techTab.FilenameInput.text()
        self.load_scale_factor = float(self.techTab.load_scale_factorInput.text())

        self.TRY_data = import_TRY(self.parent.try_filename)
        self.COP_data = np.genfromtxt(self.parent.cop_filename, delimiter=';')

        results = []
        for gas_price in self.generate_values(gas_range):
            for electricity_price in self.generate_values(electricity_range):
                for wood_price in self.generate_values(wood_range):
                    result = self.calculate_mix(gas_price, electricity_price, wood_price, weights)
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

    def calculate_mix(self, gas_price, electricity_price, wood_price, weights):
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
        
        def calculation_done(result_data):
            self.progressBar.setRange(0, 1)
            nonlocal result
            result = result_data
            calculation_done_event.quit()

        def calculation_error(error_message):
            self.progressBar.setRange(0, 1)
            QMessageBox.critical(self, "Berechnungsfehler", str(error_message))
            calculation_done_event.quit()

        self.calculationThread = CalculateMixThread(
            self.filename, self.load_scale_factor, self.TRY_data, self.COP_data, gas_price, 
            electricity_price, wood_price, self.BEW, self.techTab.tech_objects, False, 
            self.kapitalzins, self.preissteigerungsrate, self.betrachtungszeitraum, self.stundensatz, weights)
        
        self.calculationThread.calculation_done.connect(calculation_done)
        self.calculationThread.calculation_error.connect(calculation_error)
        self.calculationThread.start()
        self.progressBar.setRange(0, 0)
        calculation_done_event.exec_()  # Wait for the thread to finish

        # Ensure the thread has finished before returning
        self.calculationThread.wait()

        return result

    ### Save Calculation Results ###
    def save_heat_generation_results_to_csv(self, results):
        """
        Saves the heat generation results to a CSV file.

        Args:
            results (dict): The calculation results.
        """
        # Initialize the DataFrame with the timestamps
        df = pd.DataFrame({'time_steps': results['time_steps']})
        
        # Add the load data
        df['Last_L'] = results['Last_L']
        
        # Add the heat generation data for each technology
        for i, (tech_results, techs) in enumerate(zip(results['Wärmeleistung_L'], results['techs'])):
            df[techs] = tech_results
        
        # Add the electrical power data
        df['el_Leistungsbedarf_L'] = results['el_Leistungsbedarf_L']
        df['el_Leistung_L'] = results['el_Leistung_L']
        df['el_Leistung_ges_L'] = results['el_Leistung_ges_L']
        
        # Save the DataFrame as a CSV file
        csv_filename = f"{self.base_path}\Lastgang\\calculated_heat_generation.csv"
        df.to_csv(csv_filename, index=False, sep=";")
        print(f"Ergebnisse wurden in '{csv_filename}' gespeichert.")

    def save_results_JSON(self):
        """
        Saves the results and technology objects to a JSON file.
        """
        if not self.results and not self.techTab.tech_objects:
            QMessageBox.warning(self, "Keine Daten vorhanden", "Es sind keine Berechnungsergebnisse oder technischen Objekte vorhanden, die gespeichert werden könnten.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(self, 'JSON speichern als...', self.base_path, filter='JSON Files (*.json)')
        if filename:
            # Create a copy of the results and tech_objects
            data_to_save = {
                'results': self.results.copy() if self.results else {},
                'tech_objects': [obj.to_dict() for obj in self.techTab.tech_objects]
            }

            try:
                # Save to a JSON file using the custom encoder
                with open(filename, 'w') as json_file:
                    json.dump(data_to_save, json_file, indent=4, cls=CustomJSONEncoder)
                
                QMessageBox.information(self, "Erfolgreich gespeichert", f"Die Ergebnisse wurden erfolgreich unter {filename} gespeichert.")
            except TypeError as e:
                QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der JSON-Datei: {e}")
                raise e

    def load_results_JSON(self):
        """
        Loads the results and technology objects from a JSON file.
        """
        filename, _ = QFileDialog.getOpenFileName(self, 'JSON Datei laden...', self.base_path, filter='JSON Files (*.json)')
        if filename:
            try:
                # Load the JSON file
                with open(filename, 'r') as json_file:
                    data_loaded = json.load(json_file)
                
                results_loaded = data_loaded.get('results', {})
                tech_objects_loaded = data_loaded.get('tech_objects', [])
                tech_classes = []

                # Convert lists back to numpy arrays and dictionaries back to objects
                for key, value in results_loaded.items():
                    if isinstance(value, list):
                        if key == "tech_classes":  # Convert dictionaries back to objects
                            for v in value:
                                if v['name'] == 'BHKW' or v['name'] == 'Holzgas-BHKW':
                                    tech_classes.append(CHP.from_dict(v))
                                    results_loaded[key] = tech_classes
                                elif v['name'] == 'Flusswasser':
                                    tech_classes.append(RiverHeatPump.from_dict(v))
                                    results_loaded[key] = tech_classes
                                elif v['name'] == 'Abwärme':
                                    tech_classes.append(WasteHeatPump.from_dict(v))
                                    results_loaded[key] = tech_classes
                                elif v['name'] == 'Geothermie':
                                    tech_classes.append(Geothermal.from_dict(v))
                                    results_loaded[key] = tech_classes
                                elif v['name'] == 'Biomassekessel':
                                    tech_classes.append(BiomassBoiler.from_dict(v))
                                    results_loaded[key] = tech_classes
                                elif v['name'] == 'Gaskessel':
                                    tech_classes.append(GasBoiler.from_dict(v))
                                    results_loaded[key] = tech_classes
                                elif v['name'] == 'Solarthermie':
                                    tech_classes.append(SolarThermal.from_dict(v))
                        elif all(isinstance(i, list) for i in value):  # Check if the list is a list of lists
                            results_loaded[key] = [np.array(v) for v in value]
                        else:
                            results_loaded[key] = np.array(value)
                
                # Load the tech_objects
                tech_objects = []
                for obj in tech_objects_loaded:
                    if obj['name'] == 'BHKW' or obj['name'] == 'Holzgas-BHKW':
                        tech_objects.append(CHP.from_dict(obj))
                    elif obj['name'] == 'Flusswasser':
                        tech_objects.append(RiverHeatPump.from_dict(obj))
                    elif obj['name'] == 'Abwärme':
                        tech_objects.append(WasteHeatPump.from_dict(obj))
                    elif obj['name'] == 'Geothermie':
                        tech_objects.append(Geothermal.from_dict(obj))
                    elif obj['name'] == 'Biomassekessel':
                        tech_objects.append(BiomassBoiler.from_dict(obj))
                    elif obj['name'] == 'Gaskessel':
                        tech_objects.append(GasBoiler.from_dict(obj))
                    elif obj['name'] == 'Solarthermie':
                        tech_objects.append(SolarThermal.from_dict(obj))

                self.results = results_loaded
                self.techTab.tech_objects = tech_objects

                # Update the tabs with the loaded data
                if self.techTab.tech_objects != []:
                    self.techTab.updateTechList()

                if self.results != {}:
                    self.costTab.updateInfrastructureTable()  # Ensure the infrastructure table is updated first
                    self.costTab.updateTechDataTable(self.techTab.tech_objects)  # Then update the tech table
                    self.costTab.updateSumLabel()  # Then update the sum label
                    self.costTab.plotCostComposition()
                    self.resultTab.showResultsInTable(self.results)
                    self.resultTab.showAdditionalResultsTable(self.results)
                    self.resultTab.plotResults(self.results)
                
                QMessageBox.information(self, "Erfolgreich geladen", f"Die Ergebnisse wurden erfolgreich aus {filename} geladen.")
            except Exception as e:
                QMessageBox.critical(self, "Ladefehler", f"Fehler beim Laden der JSON-Datei: {e}")
                raise e

    def on_export_pdf_clicked(self):
        """
        Exports the results to a PDF file.
        """
        filename, _ = QFileDialog.getSaveFileName(self, 'PDF speichern als...', self.base_path, filter='PDF Files (*.pdf)')
        if filename:
            try:
                create_pdf(self, filename)
                
                QMessageBox.information(self, "PDF erfolgreich erstellt.", f"Die Ergebnisse wurden erfolgreich in {filename} gespeichert.")
            
            except Exception as e:
                error_message = traceback.format_exc()
                QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern als PDF:\n{error_message}")
                raise e
