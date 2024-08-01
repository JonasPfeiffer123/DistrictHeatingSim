"""
Filename: technology_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the TechnologyTab.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QLineEdit, 
    QListWidget, QDialog, QFileDialog, QScrollArea, QCheckBox, QFormLayout, 
    QDialogButtonBox, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from heat_generators.heat_generator_classes import *
from gui.MixDesignTab.heat_generator_dialogs import TechInputDialog

class CustomListWidget(QListWidget):
    """
    A custom QListWidget with additional functionality for handling drop events
    and updating the order of technology objects in the parent TechnologyTab.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_tab = parent

    def dropEvent(self, event):
        """
        Handles the drop event to update the order of technology objects
        in the parent TechnologyTab.
        """
        super().dropEvent(event)
        if self.parent_tab:
            self.parent_tab.updateTechObjectsOrder()

class TechnologyTab(QWidget):
    """
    A QWidget subclass representing the TechnologyTab.

    Attributes:
        data_added (pyqtSignal): A signal that emits data as an object.
        data_manager (DataManager): An instance of the DataManager class for managing data.
        results (dict): A dictionary to store results.
        tech_objects (list): A list of technology objects.
    """
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        """
        Initializes the TechnologyTab.

        Args:
            data_manager (DataManager): The data manager.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.results = {}
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        self.loadFileAndPlot()

    def initFileInputs(self):
        """
        Initializes the file input widgets.
        """
        self.FilenameInput = QLineEdit('')
        self.selectFileButton = QPushButton('Ergebnis-CSV auswählen')
        self.selectFileButton.clicked.connect(self.on_selectFileButton_clicked)

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for file inputs.

        Args:
            new_base_path (str): The new base path.
        """
        self.base_path = new_base_path
        new_output_path = f"{self.base_path}/Lastgang/Lastgang.csv"
        self.FilenameInput.setText(new_output_path)
        self.loadFileAndPlot()

    def initUI(self):
        """
        Initializes the UI components of the TechnologyTab.
        """
        self.createMainScrollArea()
        self.setupFileInputs()
        self.setupScaleFactor()
        self.setupTechnologySelection()
        self.setupPlotArea()
        self.setLayout(self.createMainLayout())

    def createMainScrollArea(self):
        """
        Creates the main scroll area for the TechnologyTab.
        """
        self.mainScrollArea = QScrollArea(self)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.mainScrollArea.setWidget(self.mainWidget)

    def setupFileInputs(self):
        """
        Sets up the file input widgets and layout.
        """
        layout = QHBoxLayout()
        layout.addWidget(QLabel('Eingabe csv-Datei berechneter Lastgang Wärmenetz'))
        layout.addWidget(self.FilenameInput)
        layout.addWidget(self.selectFileButton)
        self.mainLayout.addLayout(layout)
        self.FilenameInput.textChanged.connect(self.loadFileAndPlot)

    def addLabel(self, text):
        """
        Adds a label to the main layout.

        Args:
            text (str): The text for the label.
        """
        label = QLabel(text)
        self.mainLayout.addWidget(label)

    def on_selectFileButton_clicked(self):
        """
        Handles the event when the select file button is clicked.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            self.FilenameInput.setText(filename)

    def setupScaleFactor(self):
        """
        Sets up the scale factor input widgets and layout.
        """
        self.load_scale_factorLabel = QLabel('Lastgang skalieren?:')
        self.load_scale_factorInput = QLineEdit("1")
        self.addHorizontalLayout(self.load_scale_factorLabel, self.load_scale_factorInput)
        self.load_scale_factorInput.textChanged.connect(self.loadFileAndPlot)

    def addHorizontalLayout(self, *widgets):
        """
        Adds a horizontal layout with the given widgets to the main layout.

        Args:
            *widgets: The widgets to add to the horizontal layout.
        """
        layout = QHBoxLayout()
        for widget in widgets:
            layout.addWidget(widget)
        self.mainLayout.addLayout(layout)

    def setupTechnologySelection(self):
        """
        Sets up the technology selection widgets and layout.
        """
        self.addLabel('Definierte Wärmeerzeuger')
        self.techList = CustomListWidget(self)
        self.techList.setDragDropMode(QAbstractItemView.InternalMove)
        self.techList.itemDoubleClicked.connect(self.editTech)
        self.mainLayout.addWidget(self.techList)
        self.addButtonLayout()

    def addButtonLayout(self):
        """
        Adds the button layout for managing technologies.
        """
        buttonLayout = QHBoxLayout()
        self.btnDeleteSelectedTech = QPushButton("Ausgewählte Technologie entfernen")
        self.btnRemoveTech = QPushButton("Alle Technologien entfernen")
        buttonLayout.addWidget(self.btnDeleteSelectedTech)
        buttonLayout.addWidget(self.btnRemoveTech)
        self.mainLayout.addLayout(buttonLayout)
        self.btnDeleteSelectedTech.clicked.connect(self.removeSelectedTech)
        self.btnRemoveTech.clicked.connect(self.removeTech)

    def createTechnology(self, tech_type, inputs):
        """
        Creates a technology object based on the type and inputs.

        Args:
            tech_type (str): The type of technology.
            inputs (dict): The inputs for the technology.

        Returns:
            Technology: The created technology object.
        """
        tech_classes = {
            "Solarthermie": SolarThermal,
            "BHKW": CHP,
            "Holzgas-BHKW": CHP,
            "Geothermie": Geothermal,
            "Abwärme": WasteHeatPump,
            "Flusswasser": RiverHeatPump,
            "Biomassekessel": BiomassBoiler,
            "Gaskessel": GasBoiler
        }

        base_tech_type = tech_type.split('_')[0]
        tech_class = tech_classes.get(base_tech_type)
        if not tech_class:
            raise ValueError(f"Unbekannter Technologietyp: {tech_type}")

        tech_count = sum(1 for tech in self.tech_objects if tech.name.startswith(base_tech_type))
        unique_name = f"{base_tech_type}_{tech_count + 1}"

        return tech_class(name=unique_name, **inputs)

    def addTech(self, tech_type, tech_data):
        """
        Adds a new technology to the list.

        Args:
            tech_type (str): The type of technology.
            tech_data (dict): The data for the technology.
        """
        dialog = TechInputDialog(tech_type, tech_data)
        if dialog.exec_() == QDialog.Accepted:
            new_tech = self.createTechnology(tech_type, dialog.getInputs())
            self.tech_objects.append(new_tech)
            self.updateTechList()

    def editTech(self, item):
        """
        Edits the selected technology.

        Args:
            item (QListWidgetItem): The selected item to edit.
        """
        selected_tech_index = self.techList.row(item)
        selected_tech = self.tech_objects[selected_tech_index]
        tech_data = {k: v for k, v in selected_tech.__dict__.items() if not k.startswith('_')}

        dialog = TechInputDialog(selected_tech.name, tech_data)
        if dialog.exec_() == QDialog.Accepted:
            updated_inputs = dialog.getInputs()
            updated_tech = self.createTechnology(selected_tech.name.split('_')[0], updated_inputs)
            updated_tech.name = selected_tech.name
            self.tech_objects[selected_tech_index] = updated_tech
            self.updateTechList()

    def removeSelectedTech(self):
        """
        Removes the selected technology from the list.
        """
        selected_row = self.techList.currentRow()
        if selected_row != -1:
            self.techList.takeItem(selected_row)
            del self.tech_objects[selected_row]
            self.updateTechList()

    def removeTech(self):
        """
        Removes all technologies from the list.
        """
        self.techList.clear()
        self.tech_objects = []

    def updateTechList(self):
        """
        Updates the technology list display.
        """
        self.techList.clear()
        for tech in self.tech_objects:
            self.techList.addItem(self.formatTechForDisplay(tech))

    def updateTechObjectsOrder(self):
        """
        Updates the order of technology objects based on the list display.
        """
        new_order = []
        for index in range(self.techList.count()):
            item_text = self.techList.item(index).text()
            for tech in self.tech_objects:
                if self.formatTechForDisplay(tech) == item_text:
                    new_order.append(tech)
                    break
        self.tech_objects = new_order

    def formatTechForDisplay(self, tech):
        """
        Formats a technology object for display in the list.

        Args:
            tech (Technology): The technology object.

        Returns:
            str: The formatted string for display.
        """
        display_text = f"{tech.name}: "
        if isinstance(tech, RiverHeatPump):
            display_text += f"Wärmeleistung FW WP: {tech.Wärmeleistung_FW_WP} kW, Temperatur FW WP: {tech.Temperatur_FW_WP} °C, dT: {tech.dT} K, spez. Investitionskosten Flusswärme: {tech.spez_Investitionskosten_Flusswasser} €/kW, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, WasteHeatPump):
            display_text += f"Kühlleistung Abwärme: {tech.Kühlleistung_Abwärme} kW, Temperatur Abwärme: {tech.Temperatur_Abwärme} °C, spez. Investitionskosten Abwärme: {tech.spez_Investitionskosten_Abwärme} €/kW, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, Geothermal):
            display_text += f"Fläche Sondenfeld: {tech.Fläche} m², Bohrtiefe: {tech.Bohrtiefe} m, Quelltemperatur Erdreich: {tech.Temperatur_Geothermie} °C, spez. Bohrkosten: {tech.spez_Bohrkosten} €/m, spez. Entzugsleistung: {tech.spez_Entzugsleistung} W/m, Vollbenutzungsstunden: {tech.Vollbenutzungsstunden} h, Abstand Sonden: {tech.Abstand_Sonden} m, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, CHP):
            display_text += f"th. Leistung: {tech.th_Leistung_BHKW} kW, spez. Investitionskosten Erdgas-BHKW: {tech.spez_Investitionskosten_GBHKW} €/kW, spez. Investitionskosten Holzgas-BHKW: {tech.spez_Investitionskosten_HBHKW} €/kW"
        elif isinstance(tech, BiomassBoiler):
            display_text += f"th. Leistung: {tech.P_BMK}, Größe Holzlager: {tech.Größe_Holzlager} t, spez. Investitionskosten Kessel: {tech.spez_Investitionskosten} €/kW, spez. Investitionskosten Holzlager: {tech.spez_Investitionskosten_Holzlager} €/t"
        elif isinstance(tech, GasBoiler):
            display_text += f"spez. Investitionskosten: {tech.spez_Investitionskosten} €/kW"
        elif isinstance(tech, SolarThermal):
            display_text += f"Bruttokollektorfläche: {tech.bruttofläche_STA} m², Volumen Solarspeicher: {tech.vs} m³, Kollektortyp: {tech.Typ}, spez. Kosten Speicher: {tech.kosten_speicher_spez} €/m³, spez. Kosten Flachkollektor: {tech.kosten_fk_spez} €/m², spez. Kosten Röhrenkollektor: {tech.kosten_vrk_spez} €/m²"
        else:
            display_text = f"Unbekannte Technologieklasse: {type(tech).__name__}"

        return display_text

    def createMainLayout(self):
        """
        Creates the main layout for the TechnologyTab.

        Returns:
            QVBoxLayout: The main layout.
        """
        layout = QVBoxLayout(self)
        layout.addWidget(self.mainScrollArea)
        return layout

    def setupPlotArea(self):
        """
        Sets up the plot area for displaying graphs.
        """
        self.plotLayout = QVBoxLayout()
        self.plotCanvas = None
        self.createPlotCanvas()
        self.mainLayout.addLayout(self.plotLayout)

    def createPlotCanvas(self):
        """
        Creates the plot canvas for displaying graphs.
        """
        if self.plotCanvas:
            self.plotLayout.removeWidget(self.plotCanvas)
            self.plotCanvas.deleteLater()
        self.plotFigure = Figure(figsize=(6, 6))
        self.plotCanvas = FigureCanvas(self.plotFigure)
        self.plotCanvas.setMinimumSize(500, 500)
        self.plotLayout.addWidget(self.plotCanvas)

    def loadFileAndPlot(self):
        """
        Loads the file and plots the data.
        """
        filename = self.FilenameInput.text()
        if filename:
            try:
                data = pd.read_csv(filename, sep=";")
                self.plotData(data)
            except Exception as e:
                self.showErrorMessage(f"Fehler beim Laden der Datei: {e}")

    def plotData(self, data):
        """
        Plots the data on the plot canvas.

        Args:
            data (DataFrame): The data to plot.
        """
        try:
            scale_factor = float(self.load_scale_factorInput.text())
        except ValueError:
            self.showErrorMessage("Ungültiger Skalierungsfaktor.")
            return

        self.createPlotCanvas()
        ax = self.plotFigure.add_subplot(111)
        if 'Zeit' in data.columns and 'Wärmeerzeugung_Heizentrale Haupteinspeisung_1_kW' in data.columns:
            ax.plot(pd.to_datetime(data['Zeit']), data['Wärmeerzeugung_Heizentrale Haupteinspeisung_1_kW'] * scale_factor, label='Gesamtwärmebedarf')
            ax.set_title("Jahresgang Wärmebedarf")
            ax.set_xlabel("Zeit")
            ax.set_ylabel("Wärmebedarf (kW)")
            ax.legend()
            self.plotCanvas.draw()
        else:
            self.showErrorMessage("Die Datei enthält nicht die erforderlichen Spalten 'Zeit' und 'Wärmeerzeugung_Heizentrale Haupteinspeisung_1_kW'.")

    def showErrorMessage(self, message):
        """
        Shows an error message.

        Args:
            message (str): The error message to display.
        """
        QMessageBox.critical(self, "Fehler", message)