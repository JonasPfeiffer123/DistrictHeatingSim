"""
Filename: technology_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-12-11
Description: Contains the TechnologyTab.
"""

import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QLineEdit, 
    QListWidget, QDialog, QFileDialog, QScrollArea, QAbstractItemView,
    QSplitter
)
from PyQt5.QtCore import pyqtSignal
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from districtheatingsim.heat_generators import TECH_CLASS_REGISTRY
from districtheatingsim.gui.MixDesignTab.heat_generator_dialogs import TechInputDialog
from districtheatingsim.gui.MixDesignTab.generator_schematic import SchematicScene, CustomGraphicsView

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

    # Globale Zähler für jede Technologieklasse
    global_counters = {
        "Solarthermie": 0,
        "BHKW": 0,
        "Holzgas-BHKW": 0,
        "Geothermie": 0,
        "Abwärme": 0,
        "Flusswasser": 0,
        "Biomassekessel": 0,
        "Gaskessel": 0,
        "AqvaHeat": 0,
        "Power-to-Heat": 0
    }

    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, config_manager, parent=None):
        """
        Initializes the TechnologyTab.

        Args:
            data_manager (DataManager): The data manager.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.results = {}
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.variant_folder)
        self.loadFileAndPlot()

    def initFileInputs(self):
        """
        Initializes the file input widgets.
        """
        self.FilenameInput = QLineEdit('')
        self.selectFileButton = QPushButton('Lastgang-CSV auswählen')
        self.selectFileButton.clicked.connect(self.on_selectFileButton_clicked)

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for file inputs.

        Args:
            new_base_path (str): The new base path.
        """
        self.base_path = new_base_path
        new_output_path = os.path.join(self.base_path, self.config_manager.get_relative_path('load_profile_path'))
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
        self.setupPlotAndSchematic()
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
        layout.addWidget(self.selectFileButton)
        layout.addWidget(self.FilenameInput)
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

    def createTechnology(self, tech_type, inputs):
        """
        Creates a technology object based on the type and inputs.

        Args:
            tech_type (str): The type of technology.
            inputs (dict): The inputs for the technology.

        Returns:
            Technology: The created technology object.
        """
        tech_classes = TECH_CLASS_REGISTRY

        base_tech_type = tech_type.split('_')[0]
        tech_class = tech_classes.get(base_tech_type)
        if not tech_class:
            raise ValueError(f"Unbekannter Technologietyp: {tech_type}")

        # Erhöhe den globalen Zähler für diese Technologieklasse
        self.global_counters[base_tech_type] += 1
        unique_name = f"{base_tech_type}_{self.global_counters[base_tech_type]}"

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
            # Speicheraktivität direkt vom Dialog abrufen und im tech-Objekt speichern
            new_tech.has_storage = dialog.getInputs().get('speicher_aktiv', False)
            self.tech_objects.append(new_tech)
            self.updateTechList()
            self.addTechToScene(new_tech)  # Füge das neue Objekt zur Szene hinzu

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
            updated_tech.has_storage = updated_inputs.get('speicher_aktiv', False)  # Aktualisiere die Speicheroption
            self.tech_objects[selected_tech_index] = updated_tech

            # Lösche die gesamte Szene und erstelle neu
            self.rebuildScene()
            self.updateTechList()

    def removeSelectedTech(self):
        """
        Entfernt das ausgewählte Technologie-Objekt und aktualisiert die Zähler und Objektnamen.
        """
        selected_row = self.techList.currentRow()

        if selected_row != -1:
            # Finde das zu löschende Objekt
            removed_tech = self.tech_objects[selected_row]
            tech_type = removed_tech.name.split('_')[0]

            # Entferne das Objekt aus der Liste
            self.techList.takeItem(selected_row)
            del self.tech_objects[selected_row]

            # Aktualisiere die globalen Zähler und füge alle verbleibenden Objekte wieder hinzu
            self.updateTechNames(tech_type)
            self.rebuildScene()

            # Aktualisiere die Anzeige der Technologien
            self.updateTechList()

    def rebuildScene(self):
        """
        Baut die gesamte Szene neu auf, indem alle verbleibenden Technologien hinzugefügt werden.
        """
        self.schematic_scene.delete_all()  # Lösche alle Objekte aus der Szene

        for tech in self.tech_objects:
            # Füge jede Technologie wieder zur Szene hinzu
            self.addTechToScene(tech)

            # Aktualisiere die Namen und Zähler basierend auf der Reihenfolge in der Liste
            tech_type = tech.name.split('_')[0]
            # every other global counter should be 0
            for key in self.global_counters:
                self.global_counters[key] = 0
            self.global_counters[tech_type] = sum(1 for t in self.tech_objects if t.name.startswith(tech_type))


        # Aktualisiere die Liste der Technologien in der UI
        self.updateTechList()

    def updateTechNames(self, tech_type):
        """
        Aktualisiert die Namen und Labels der verbleibenden Objekte einer Technologieklasse.
        """
        count = 1  # Starte den Zähler für die Technologieklasse bei 1

        for tech in self.tech_objects:
            if tech.name.startswith(tech_type):
                # Aktualisiere den Namen des Technologie-Objekts basierend auf dem neuen Zähler
                tech.name = f"{tech_type}_{count}"

                # Aktualisiere den Namen und das Label in der Szene
                tech.scene_item.item_name = tech.name
                
                count += 1

        # Aktualisiere den globalen Zähler basierend auf der Anzahl verbleibender Objekte dieser Klasse
        self.global_counters[tech_type] = count - 1

    def removeTech(self):
        """
        Removes all technologies from the list.
        """
        self.techList.clear()
        self.tech_objects = []
        self.schematic_scene.delete_all()  # Entferne alle Objekte aus der Szene

        self.global_counters = {tech_type: 0 for tech_type in self.global_counters}

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

        self.rebuildScene()
    
    def formatTechForDisplay(self, tech):
        """
        Delegates the formatting of the display text to the technology object itself.
        
        Args:
            tech (Technology): The technology object.
        
        Returns:
            str: The formatted string for display.
        """
        try:
            return tech.get_display_text()
        
        except Exception as e:
            return f"Error: {e}"

    def createMainLayout(self):
        """
        Creates the main layout for the TechnologyTab.

        Returns:
            QVBoxLayout: The main layout.
        """
        layout = QVBoxLayout(self)
        layout.addWidget(self.mainScrollArea)
        return layout

    def setupPlotAndSchematic(self):
        """
        Sets up both the plot area and the schematic scene area.
        """
        # Create a QSplitter to split the plot area and the schematic scene
        splitter = QSplitter(self)

        # Create the plot canvas on the left side
        self.plotLayout = QVBoxLayout()  # Füge das Plot-Layout hinzu
        self.plotWidget = QWidget()
        self.plotWidget.setLayout(self.plotLayout)
        self.plotFigure = Figure(figsize=(4, 3))
        self.plotCanvas = FigureCanvas(self.plotFigure)
        self.plotLayout.addWidget(self.plotCanvas)
        splitter.addWidget(self.plotWidget)

        # Create the schematic scene on the right side
        self.schematic_scene = SchematicScene(500, 500)
        self.schematic_view = CustomGraphicsView(self.schematic_scene)
        splitter.addWidget(self.schematic_view)

        # Add the splitter to the main layout
        self.mainLayout.addWidget(splitter)

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
        Loads the file and plots the data. If the file is not available or has issues,
        it displays a message on the plot canvas instead of throwing an error.
        """
        filename = self.FilenameInput.text()
        if filename:
            try:
                data = pd.read_csv(filename, sep=";")
                self.plotData(data)
            except FileNotFoundError:
                self.showInfoMessageOnPlot("Datei nicht gefunden. Bitte wählen Sie eine gültige CSV-Datei aus.")
            except pd.errors.EmptyDataError:
                self.showInfoMessageOnPlot("Die Datei ist leer.")
            except Exception as e:
                self.showInfoMessageOnPlot(f"Fehler beim Laden der Datei: {e}")
        else:
            self.showInfoMessageOnPlot("Keine Datei ausgewählt.")

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

        # Identifiziere alle Spalten, die Wärmeerzeugung enthalten
        heat_generation_columns = [col for col in data.columns if 'Wärmeerzeugung' in col]

        if 'Zeit' in data.columns and heat_generation_columns:
            # Summiere alle Wärmeerzeugungsspalten
            data['Summenlastgang'] = data[heat_generation_columns].sum(axis=1) * scale_factor

            # Plotten des Summenlastgangs
            ax.plot(pd.to_datetime(data['Zeit']), data['Summenlastgang'], label='Gesamtwärmebedarf')
            ax.set_title("Jahresganglinie Wärmeerzeugung (Summe)")
            ax.set_xlabel("Zeit")
            ax.set_ylabel("Wärmebedarf (kW)")
            ax.legend()
            self.plotCanvas.draw()
        else:
            self.showErrorMessage("Die Datei enthält nicht die erforderlichen Spalten 'Zeit' und 'Wärmeerzeugung'.")
    
    def showInfoMessageOnPlot(self, message):
        """
        Displays an information message on the plot canvas.

        Args:
            message (str): The message to display.
        """
        self.createPlotCanvas()
        ax = self.plotFigure.add_subplot(111)
        ax.text(0.5, 0.5, message, ha='center', va='center', transform=ax.transAxes)
        ax.set_axis_off()
        self.plotCanvas.draw()

    def addTechToScene(self, tech):
        """
        Fügt die Technologie zur SchematicScene hinzu und speichert die Referenz im tech-Objekt.
        """
        has_storage = getattr(tech, 'has_storage', False)  # Prüfe, ob der Speicher ausgewählt wurde
        name = tech.name  # Nutze den eindeutigen Namen für die Szene

        if tech.name.startswith('Solarthermie'):
            tech.scene_item = self.schematic_scene.add_component('Solar', name, storage=True)
        elif tech.name.startswith('BHKW'):
            tech.scene_item = self.schematic_scene.add_component('CHP', name, storage=has_storage)
        elif tech.name.startswith('Holzgas-BHKW'):
            tech.scene_item = self.schematic_scene.add_component('Wood-CHP', name, storage=has_storage)
        elif tech.name.startswith('Geothermie'):
            tech.scene_item = self.schematic_scene.add_component('Geothermal Heat Pump', name, storage=False)
        elif tech.name.startswith('Abwärme'):
            tech.scene_item = self.schematic_scene.add_component('Waste Heat Pump', name, storage=False)
        elif tech.name.startswith('Flusswasser'):
            tech.scene_item = self.schematic_scene.add_component('River Heat Pump', name, storage=False)
        elif tech.name.startswith('AqvaHeat'):
            tech.scene_item = self.schematic_scene.add_component('Aqva Heat Pump', name, storage=False)
        elif tech.name.startswith('Biomassekessel'):
            tech.scene_item = self.schematic_scene.add_component('Biomass Boiler', name, storage=has_storage)
        elif tech.name.startswith('Gaskessel'):
            tech.scene_item = self.schematic_scene.add_component('Gas Boiler', name, storage=False)
        elif tech.name.startswith('PowerToHeat'):
            tech.scene_item = self.schematic_scene.add_component('Power-to-Heat', name, storage=False)
