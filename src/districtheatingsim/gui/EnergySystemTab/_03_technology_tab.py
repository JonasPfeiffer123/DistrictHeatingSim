"""
Technology Tab Module
=====================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Managing and displaying technologies in district heating simulation, including add, edit, remove, and schematic visualization.
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QLineEdit, 
    QListWidget, QDialog, QFileDialog, QScrollArea, QAbstractItemView,
    QSplitter
)
from PyQt6.QtCore import pyqtSignal
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from districtheatingsim.heat_generators import TECH_CLASS_REGISTRY
from districtheatingsim.gui.EnergySystemTab._04_technology_dialogs import TechInputDialog
from districtheatingsim.gui.EnergySystemTab._11_generator_schematic import SchematicScene, CustomGraphicsView

class CustomListWidget(QListWidget):
    """
    Custom list widget with drag-drop functionality for technology ordering.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_tab = parent

    def dropEvent(self, event):
        """
        Handle drop event to update technology object order.

        :param event: Drop event.
        :type event: QDropEvent
        """
        super().dropEvent(event)
        if self.parent_tab:
            self.parent_tab.updateTechObjectsOrder()

class TechnologyTab(QWidget):
    """
    Tab for managing and displaying heat generation technologies.

    :signal data_added: Signal that emits data as an object.
    """

    # Globale Zähler für jede Technologieklasse
    global_counters = {
        "Solarthermie": 0,
        "BHKW": 0,
        "Holzgas-BHKW": 0,
        "Geothermie": 0,
        "Abwärmepumpe": 0,
        "Flusswärmepumpe": 0,
        "Biomassekessel": 0,
        "Gaskessel": 0,
        "AqvaHeat": 0,
        "Power-to-Heat": 0,
        "Saisonaler Wärmespeicher": 0
    }

    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, config_manager, parent=None):
        """
        Initialize the TechnologyTab.

        :param data_manager: Data manager instance.
        :type data_manager: object
        :param config_manager: Configuration manager instance.
        :type config_manager: object
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        if self.data_manager.variant_folder:
            self.updateDefaultPath(self.data_manager.variant_folder)
        self.loadFileAndPlot()

    def initFileInputs(self):
        """
        Initialize file input widgets.
        """
        self.FilenameInput = QLineEdit('')
        self.selectFileButton = QPushButton('Lastgang-CSV auswählen')
        self.selectFileButton.clicked.connect(self.on_selectFileButton_clicked)

    def updateDefaultPath(self, new_base_path):
        """
        Update default path for file inputs.

        :param new_base_path: New base path.
        :type new_base_path: str
        """
        if new_base_path:
            self.base_path = new_base_path
            new_output_path = os.path.join(self.base_path, self.config_manager.get_relative_path('load_profile_path'))
            self.FilenameInput.setText(new_output_path)
            self.loadFileAndPlot()

    def initUI(self):
        """
        Initialize UI components.
        """
        self.createMainScrollArea()
        self.setupFileInputs()
        self.setupScaleFactor()
        self.setupTechnologySelection()
        self.setupPlotAndSchematic()
        self.setLayout(self.createMainLayout())

    def createMainScrollArea(self):
        """
        Create main scroll area.
        """
        self.mainScrollArea = QScrollArea(self)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.mainScrollArea.setWidget(self.mainWidget)

    def setupFileInputs(self):
        """
        Set up file input widgets and layout.
        """
        layout = QHBoxLayout()
        layout.addWidget(self.selectFileButton)
        layout.addWidget(self.FilenameInput)
        self.mainLayout.addLayout(layout)
        self.FilenameInput.textChanged.connect(self.loadFileAndPlot)

    def addLabel(self, text):
        """
        Add label to main layout.

        :param text: Label text.
        :type text: str
        """
        label = QLabel(text)
        self.mainLayout.addWidget(label)

    def on_selectFileButton_clicked(self):
        """
        Handle select file button click event.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            self.FilenameInput.setText(filename)

    def setupScaleFactor(self):
        """
        Set up scale factor input widgets and layout.
        """
        self.load_scale_factorLabel = QLabel('Lastgang skalieren?:')
        self.load_scale_factorInput = QLineEdit("1")
        self.addHorizontalLayout(self.load_scale_factorLabel, self.load_scale_factorInput)
        self.load_scale_factorInput.textChanged.connect(self.loadFileAndPlot)

    def addHorizontalLayout(self, *widgets):
        """
        Add horizontal layout with given widgets to main layout.

        :param widgets: Widgets to add to horizontal layout.
        :type widgets: tuple
        """
        layout = QHBoxLayout()
        for widget in widgets:
            layout.addWidget(widget)
        self.mainLayout.addLayout(layout)

    def addButtonLayout(self):
        """
        Add button layout for managing technologies.
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
        Set up technology selection widgets and layout.
        """
        self.addLabel('Definierte Wärmeerzeuger')
        self.techList = CustomListWidget(self)
        self.techList.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.techList.itemDoubleClicked.connect(self.editTech)
        self.mainLayout.addWidget(self.techList)
        self.addButtonLayout()

    def createTechnology(self, tech_type, inputs):
        """
        Create technology object based on type and inputs.

        :param tech_type: Technology type.
        :type tech_type: str
        :param inputs: Technology inputs.
        :type inputs: dict
        :return: Created technology object.
        :rtype: Technology
        """
        tech_classes = TECH_CLASS_REGISTRY

        base_tech_type = tech_type.split('_')[0]
        tech_class = tech_classes.get(base_tech_type)
        if not tech_class:
            raise ValueError(f"Unbekannter Technologietyp: {tech_type}")

        # Erhöhe den globalen Zähler für diese Technologieklasse
        self.global_counters[base_tech_type] += 1
        unique_name = f"{base_tech_type}_{self.global_counters[base_tech_type]}"
        
        try:
            # Erstelle die Technologieinstanz
            return tech_class(name=unique_name, **inputs)

        except TypeError as e:
            raise TypeError(
                f"Fehler beim Erstellen der Technologie '{tech_type}': {e}\n"
                f"Übergebene Eingaben: {inputs}"
            )

    def addTech(self, tech_type, tech_data):
        """
        Add new technology to list.

        :param tech_type: Technology type.
        :type tech_type: str
        :param tech_data: Technology data.
        :type tech_data: dict
        """
        dialog = TechInputDialog(tech_type, tech_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_tech = self.createTechnology(tech_type, dialog.getInputs())
            # Speicheraktivität direkt vom Dialog abrufen und im tech-Objekt speichern
            new_tech.has_storage = dialog.getInputs().get('speicher_aktiv', False) # thats stupid af
            self.tech_objects.append(new_tech)
            self.updateTechList()
            self.addTechToScene(new_tech)  # Füge das neue Objekt zur Szene hinzu

    def editTech(self, item):
        """
        Edit selected technology.

        :param item: Selected item to edit.
        :type item: QListWidgetItem
        """
        selected_tech_index = self.techList.row(item)
        selected_tech = self.tech_objects[selected_tech_index]
        tech_data = {k: v for k, v in selected_tech.__dict__.items() if not k.startswith('_')}

        dialog = TechInputDialog(selected_tech.name, tech_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
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
        Remove selected technology object and update counters and object names.
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
        Rebuild entire scene by adding all remaining technologies.
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
        Update names and labels of remaining objects of a technology class.

        :param tech_type: Technology type.
        :type tech_type: str
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
        Remove all technologies from list.
        """
        self.techList.clear()
        self.tech_objects = []
        self.schematic_scene.delete_all()  # Entferne alle Objekte aus der Szene

        self.global_counters = {tech_type: 0 for tech_type in self.global_counters}

    def updateTechList(self):
        """
        Update technology list display.
        """
        self.techList.clear()
        for tech in self.tech_objects:
            self.techList.addItem(self.formatTechForDisplay(tech))

    def updateTechObjectsOrder(self):
        """
        Update order of technology objects based on list display.
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
        Delegate formatting of display text to technology object.

        :param tech: Technology object.
        :type tech: Technology
        :return: Formatted string for display.
        :rtype: str
        """
        try:
            return tech.get_display_text()
        
        except Exception as e:
            return f"Error: {e}"

    def createMainLayout(self):
        """
        Create main layout for TechnologyTab.

        :return: Main layout.
        :rtype: QVBoxLayout
        """
        layout = QVBoxLayout(self)
        layout.addWidget(self.mainScrollArea)
        return layout

    def setupPlotAndSchematic(self):
        """
        Set up plot area and schematic scene area.
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
        Create plot canvas for displaying graphs.
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
        Load file and plot data, display message if file unavailable or has issues.
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
        Plot data on canvas with modern styling and hour-based x-axis.

        :param data: Data to plot.
        :type data: DataFrame
        """
        try:
            scale_factor = float(self.load_scale_factorInput.text())
        except ValueError:
            self.showErrorMessage("Ungültiger Skalierungsfaktor.")
            return

        self.createPlotCanvas()
        
        # Apply modern matplotlib styling
        plt.style.use('seaborn-v0_8-darkgrid')
        
        ax = self.plotFigure.add_subplot(111)

        # Identifiziere alle Spalten, die Wärmeerzeugung enthalten
        heat_generation_columns = [col for col in data.columns if 'Wärmeerzeugung' in col]

        if 'Zeit' in data.columns and heat_generation_columns:
            # Summiere alle Wärmeerzeugungsspalten
            data['Summenlastgang'] = data[heat_generation_columns].sum(axis=1) * scale_factor

            # Convert datetime to hours of year (0-8760)
            time_data = pd.to_datetime(data['Zeit'])
            if len(time_data) > 0:
                start_of_year = pd.Timestamp(time_data.iloc[0].year, 1, 1)
                hours_of_year = [(t - start_of_year).total_seconds() / 3600 for t in time_data]
            else:
                hours_of_year = list(range(len(data)))

            # Modern plot styling
            ax.plot(hours_of_year, data['Summenlastgang'], 
                   label='Gesamtwärmebedarf', color='#3498db', linewidth=1.5)
            
            # Modern styling
            ax.set_title("Jahresganglinie Wärmeerzeugung (Summe)", fontsize=16, fontweight='bold', color='#2c3e50')
            ax.set_xlabel("Jahresstunden [h]", fontsize=14, color='#2c3e50')
            ax.set_ylabel("Wärmebedarf [kW]", fontsize=14, color='#2c3e50')
            
            # Grid and styling
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='both', labelsize=12, colors='#2c3e50')
            
            # Legend styling
            legend = ax.legend(fontsize=12, frameon=True, fancybox=True, shadow=True)
            legend.get_frame().set_facecolor('#ffffff')
            legend.get_frame().set_alpha(0.9)
            
            # X-axis ticks for better readability
            max_hours = max(hours_of_year) if hours_of_year else 8760
            if max_hours > 8760:  # More than one year
                ax.set_xticks(range(0, int(max_hours), 2000))
            elif max_hours > 4000:  # More than half year
                ax.set_xticks(range(0, int(max_hours), 1000))
            elif max_hours > 2000:  # More than ~3 months
                ax.set_xticks(range(0, int(max_hours), 500))
            else:
                ax.set_xticks(range(0, int(max_hours), 500))
            
            # Tight layout for better appearance
            self.plotFigure.tight_layout()
            self.plotCanvas.draw()
        else:
            self.showErrorMessage("Die Datei enthält nicht die erforderlichen Spalten 'Zeit' und 'Wärmeerzeugung'.")
    
    def showInfoMessageOnPlot(self, message):
        """
        Display information message on plot canvas with modern styling.

        :param message: Message to display.
        :type message: str
        """
        self.createPlotCanvas()
        
        # Apply modern matplotlib styling
        plt.style.use('seaborn-v0_8-darkgrid')
        
        ax = self.plotFigure.add_subplot(111)
        ax.text(0.5, 0.5, message, ha='center', va='center', transform=ax.transAxes,
                fontsize=14, color='#7f8c8d', bbox=dict(boxstyle="round,pad=0.5", 
                facecolor='#ecf0f1', edgecolor='#bdc3c7', alpha=0.8))
        ax.set_axis_off()
        self.plotFigure.tight_layout()
        self.plotCanvas.draw()

    def addTechToScene(self, tech):
        """
        Add technology to SchematicScene and store reference in tech object.

        :param tech: Technology object.
        :type tech: object
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
        elif tech.name.startswith('Abwärmepumpe'):
            tech.scene_item = self.schematic_scene.add_component('Waste Heat Pump', name, storage=False)
        elif tech.name.startswith('Flusswärmepumpe'):
            tech.scene_item = self.schematic_scene.add_component('River Heat Pump', name, storage=False)
        elif tech.name.startswith('AqvaHeat'):
            tech.scene_item = self.schematic_scene.add_component('Aqva Heat Pump', name, storage=False)
        elif tech.name.startswith('Biomassekessel'):
            tech.scene_item = self.schematic_scene.add_component('Biomass Boiler', name, storage=has_storage)
        elif tech.name.startswith('Gaskessel'):
            tech.scene_item = self.schematic_scene.add_component('Gas Boiler', name, storage=False)
        elif tech.name.startswith('PowerToHeat'):
            tech.scene_item = self.schematic_scene.add_component('Power-to-Heat', name, storage=False)
        elif tech.name.startswith('Saisonaler Wärmespeicher'):
            tech.scene_item = self.schematic_scene.add_component('Seasonal Thermal Storage', name, storage=False)
