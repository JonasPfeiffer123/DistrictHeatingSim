import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QProgressBar, QTabWidget, QMessageBox, QFileDialog, QMenuBar, QScrollArea, QAction)
from PyQt5.QtCore import pyqtSignal

from heat_generators.heat_generator_classes import *
from gui.mix_design_dialogs import EconomicParametersDialog, NetInfrastructureDialog, TemperatureDataDialog, HeatPumpDataDialog
from gui.threads import CalculateMixThread
from gui.results_pdf import create_pdf

from gui.technology_tab import TechnologyTab
from gui.cost_tab import CostTab
from gui.results_tab import ResultsTab

class MixDesignTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.results = {}
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.economicParametersDialog = EconomicParametersDialog(self)
        self.netInfrastructureDialog = NetInfrastructureDialog(self)
        self.temperatureDataDialog = TemperatureDataDialog(self)
        self.heatPumpDataDialog = HeatPumpDataDialog(self)
        self.updateDefaultPath(self.data_manager.project_folder)
        self.setupParameters()
        self.tech_objects = []
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path
        self.netInfrastructureDialog.base_path = self.base_path

    def initUI(self):
        mainScrollArea = QScrollArea(self)
        mainScrollArea.setWidgetResizable(True)

        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)

        self.mainLayout = mainLayout
        self.setupMenu()

        tabWidget = QTabWidget()
        self.mainLayout.addWidget(tabWidget)

        self.techTab = TechnologyTab(self.data_manager, self)
        self.costTab = CostTab(self.data_manager, self)
        self.resultTab = ResultsTab(self.data_manager, self)

        # Adding tabs to the tab widget
        tabWidget.addTab(self.techTab, "Erzeugerdefinition")
        tabWidget.addTab(self.costTab, "Kostenübersicht")
        tabWidget.addTab(self.resultTab, "Ergebnisse")

        self.progressBar = QProgressBar(self)
        mainLayout.addWidget(self.progressBar)

        mainScrollArea.setWidget(mainWidget)

        tabLayout = QVBoxLayout(self)
        tabLayout.addWidget(self.menuBar)  # Menüleiste zuerst hinzufügen
        tabLayout.addWidget(mainScrollArea)  # Scrollbereich darunter hinzufügen
        self.setLayout(tabLayout)

    def setupMenu(self):
        # Erstellen der Menüleiste
        self.menuBar = QMenuBar(self)
        self.menuBar.setFixedHeight(30)

        # Erstellen des 'Datei'-Menüs
        fileMenu = self.menuBar.addMenu('Datei')
        pdfAction = QAction('Ergebnisse als PDF speichern', self)
        pdfAction.triggered.connect(self.on_export_pdf_clicked)
        fileMenu.addAction(pdfAction)

        # Neues Menü für Einstellungen
        settingsMenu = self.menuBar.addMenu('Einstellungen')
        # Aktion für wirtschaftliche Parameter
        economicParametersAction = QAction('Wirtschaftliche Parameter...', self)
        economicParametersAction.triggered.connect(self.openEconomicParametersDialog)
        settingsMenu.addAction(economicParametersAction)
        # Aktion für Infrastrukturkosten
        infrastructureCostsAction = QAction('Infrastrukturkosten...', self)
        infrastructureCostsAction.triggered.connect(self.openInfrastructureCostsDialog)
        settingsMenu.addAction(infrastructureCostsAction)
        # Aktion für Temperaturdaten
        temperatureDataAction = QAction('Temperaturdaten...', self)
        temperatureDataAction.triggered.connect(self.opentemperatureDataDialog)
        settingsMenu.addAction(temperatureDataAction)
        # Aktion für Temperaturdaten
        heatPumpDataAction = QAction('COP-Kennfeld Wärmepumpe...', self)
        heatPumpDataAction.triggered.connect(self.openheatPumpDataDialog)
        settingsMenu.addAction(heatPumpDataAction)

        calculationsMenu = self.menuBar.addMenu('Berechnungen')
        # Aktion für die Berechnung starten
        calculateAction = QAction('Berechnen', self)
        calculateAction.triggered.connect(self.start_calculation)
        calculationsMenu.addAction(calculateAction)
        # Aktion für die Optimierung starten
        optimizeAction = QAction('Optimieren', self)
        optimizeAction.triggered.connect(self.optimize)
        calculationsMenu.addAction(optimizeAction)

        showAdditionalResultsMenu = self.menuBar.addMenu('weitere Ergebnisse Anzeigen')
        # Aktion für die Berechnung starten
        showAdditionalResultsAction = QAction('Kostenzusammensetzung über Betrachtungszeitraum', self)
        showAdditionalResultsAction.triggered.connect(self.show_additional_results)
        showAdditionalResultsMenu.addAction(showAdditionalResultsAction)

        self.mainLayout.addWidget(self.menuBar)

    ### Eingabe wirtschaftliche Randbedingungen ###
    def setupParameters(self):
        values = self.economicParametersDialog.getValues()
        self.gaspreis = values['Gaspreis in €/MWh']
        self.strompreis = values['Strompreis in €/MWh']
        self.holzpreis = values['Holzpreis in €/MWh']
        self.BEW = values['BEW-Förderung']
        self.kapitalzins = values['Kapitalzins in %']
        self.preissteigerungsrate = values['Preissteigerungsrate in %']
        self.betrachtungszeitraum = values['Betrachtungszeitraum in a']

        TRY = self.temperatureDataDialog.getValues()
        self.try_filename = TRY['TRY-filename']

        COP = self.heatPumpDataDialog.getValues()
        self.cop_filename = COP['COP-filename']

    ### Dialoge ###
    def openEconomicParametersDialog(self):
        if self.economicParametersDialog.exec_():
            values = self.economicParametersDialog.getValues()
            self.gaspreis = values['Gaspreis in €/MWh']
            self.strompreis = values['Strompreis in €/MWh']
            self.holzpreis = values['Holzpreis in €/MWh']
            self.BEW = values['BEW-Förderung']
            self.kapitalzins = values['Kapitalzins in %']
            self.preissteigerungsrate = values['Preissteigerungsrate in %']
            self.betrachtungszeitraum = values['Betrachtungszeitraum in a']

    def openInfrastructureCostsDialog(self):
        dialog = self.netInfrastructureDialog
        if dialog.exec_():
            updated_values = dialog.getValues()
            self.costTab.updateInfrastructureTable(updated_values)

    def opentemperatureDataDialog(self):
        if self.temperatureDataDialog.exec_():
            TRY = self.temperatureDataDialog.getValues()
            self.try_filename = TRY['TRY-filename']

    def openheatPumpDataDialog(self):
        if self.heatPumpDataDialog.exec_():
            COP = self.heatPumpDataDialog.getValues()
            self.cop_filename = COP['COP-filename']
    
    ### Berechnungsfunktionen ###
    def optimize(self):
        self.start_calculation(True)

    def start_calculation(self, optimize=False):
        if self.techTab.tech_objects != []:
            #self.updateTechObjectsOrder()

            filename = self.techTab.FilenameInput.text()
            load_scale_factor = float(self.techTab.load_scale_factorInput.text())

            self.calculationThread = CalculateMixThread(filename, load_scale_factor, self.try_filename, self.cop_filename, self.gaspreis, 
                                                        self.strompreis, self.holzpreis, self.BEW, self.techTab.tech_objects, optimize, self.kapitalzins, 
                                                        self.preissteigerungsrate, self.betrachtungszeitraum)
            self.calculationThread.calculation_done.connect(self.on_calculation_done)
            self.calculationThread.calculation_error.connect(self.on_calculation_error)
            self.calculationThread.start()
            self.progressBar.setRange(0, 0)

        else:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(f"Es wurden keine Erzeugeranlagen definiert. Keine Berechnung möglich.")
            msgBox.setWindowTitle("Keine Erzeugeranlagen für die Berechnung vorhanden.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

    def on_calculation_done(self, result):
        self.progressBar.setRange(0, 1)
        self.results = result
        self.techTab.updateTechList()
        self.costTab.updateTechDataTable(self.techTab.tech_objects)
        self.resultTab.showResultsInTable(result)
        self.resultTab.showAdditionalResultsTable(result)
        self.resultTab.plotResults(result)
        self.save_results_to_csv(result)
        self.showConfirmationDialog()

    def on_calculation_error(self, error_message):
        self.progressBar.setRange(0, 1)
        QMessageBox.critical(self, "Berechnungsfehler", str(error_message))

    def showConfirmationDialog(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(f"Die Berechnung des Erzeugermixes war erfolgreich. Die Ergebnisse wurden unter {self.base_path}\Lastgang\\results.csv gespeichert.")
        msgBox.setWindowTitle("Berechnung Erfolgreich")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def show_additional_results(self):
        if self.tech_objects != [] and self.results != {}:
            print(self.results)
            print(self.tech_objects)

            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(f"Hier gibts noch nichts zu sehen. Nur Konsolenausgabe.")
            msgBox.setWindowTitle("Hier könnten Ergebnisse Visualisiert werden.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

        else:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText(f"Es sind keine Berechnungsergebnisse verfügbar. Führen Sie zunächst eine Berechnung durch.")
            msgBox.setWindowTitle("Keine Berechnungsergebnisse vorhanden.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

    ### Speicherung der Berechnungsergebnisse der Erzeugerauslegung als csv ###
    def save_results_to_csv(self, results):
        # Initialisiere den DataFrame mit den Zeitstempeln
        df = pd.DataFrame({'time_steps': results['time_steps']})
        
        # Füge die Last hinzu
        df['Last_L'] = results['Last_L']
        
        # Hier müssen eindeutige Namen noch eingeführt werden
        # Füge die Daten für Wärmeleistung hinzu. Jede Technologie wird eine Spalte haben.
        #for i, tech in enumerate(results['techs']):
        #    df[tech] = results['Wärmeleistung_L'][i]

        for i, (tech_results, techs) in enumerate(zip(results['Wärmeleistung_L'], results['techs'])):
            df[techs] = tech_results
        
        # Füge die elektrischen Leistungsdaten hinzu
        df['el_Leistungsbedarf_L'] = results['el_Leistungsbedarf_L']
        df['el_Leistung_L'] = results['el_Leistung_L']
        df['el_Leistung_ges_L'] = results['el_Leistung_ges_L']
        
        # Speichere den DataFrame als CSV-Datei
        csv_filename = f"{self.base_path}\Lastgang\\results.csv"
        df.to_csv(csv_filename, index=False, sep=";")
        print(f"Ergebnisse wurden in '{csv_filename}' gespeichert.")

    def on_export_pdf_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'PDF speichern als...', filter='PDF Files (*.pdf)')
        if filename:
            create_pdf(self, filename)