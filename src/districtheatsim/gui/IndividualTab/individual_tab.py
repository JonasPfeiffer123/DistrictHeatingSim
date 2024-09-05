"""
Filename: individual_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-04
Description: Contains the IndividualTab for managing building data and calculating heat generation technologies.
"""

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton, QComboBox, QLineEdit, QMessageBox,
                             QFormLayout, QScrollArea, QHBoxLayout, QTabWidget, QMenuBar, QMenu, QListWidget,
                             QAbstractItemView, QDialog)
from PyQt5.QtCore import pyqtSignal, Qt
import json
from gui.utilities import CheckableComboBox  # Assuming you have this implemented
from gui.MixDesignTab.heat_generator_dialogs import TechInputDialog  # Import your dialogs
from heat_generators.heat_generator_classes import *

class IndividualTab(QWidget):
    """
    Main tab that manages the menu bar and three sub-tabs: DiagramTab, TechnologyTab, and ResultsTab.
    """

    def __init__(self, folder_manager, data_manager, parent=None):
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.base_path = None

        self.folder_manager.project_folder_changed.connect(self.update_default_path)
        self.update_default_path(self.folder_manager.project_folder)

        self.initUI()

    def update_default_path(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # Create a menu bar
        menubar = QMenuBar(self)
        menubar.setFixedHeight(30)  # Set a fixed height for the menu bar
        file_menu = QMenu('File', self)
        menubar.addMenu(file_menu)

        load_action = file_menu.addAction('Load JSON Data')
        load_action.triggered.connect(self.load_json_file)

        # Create tab widget to hold the individual tabs
        self.tab_widget = QTabWidget(self)

        # Create the sub-tabs
        self.diagram_tab = DiagramTab(self)
        self.technology_tab = TechnologyTab(self)
        self.results_tab = ResultsTab(self)

        # Add the tabs to the tab widget
        self.tab_widget.addTab(self.diagram_tab, "Diagram + Data")
        self.tab_widget.addTab(self.technology_tab, "Technology Selection")
        self.tab_widget.addTab(self.results_tab, "Results")

        # Add the menu bar and tab widget to the layout
        main_layout.setMenuBar(menubar)
        main_layout.addWidget(self.tab_widget)

        self.setLayout(main_layout)

    def load_json_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', f"{self.base_path}/Lastgang", 'JSON Files (*.json);;All Files (*)')
        if file_path:
            self.diagram_tab.load_json(file_path)  # Load JSON data into the diagram tab


class DiagramTab(QWidget):
    """
    Handles the data selection and diagram plotting functionality.
    """

    data_loaded = pyqtSignal(dict)  # Signal to notify when data is loaded

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.results = {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Initialize the plot area
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)

        # Initialize the comboboxes for data selection
        self.data_type_combobox = CheckableComboBox(self)
        self.data_type_combobox.addItem("Heat Demand")
        self.data_type_combobox.addItem("Heating Demand")
        self.data_type_combobox.addItem("Warmwater Demand")
        self.data_type_combobox.addItem("Supply Temperature")
        self.data_type_combobox.addItem("Return Temperature")

        self.building_combobox = CheckableComboBox(self)

        layout.addWidget(QLabel("Select Data Types"))
        layout.addWidget(self.data_type_combobox)
        layout.addWidget(QLabel("Select Buildings"))
        layout.addWidget(self.building_combobox)

        # Connect combobox changes to replotting
        self.data_type_combobox.view().pressed.connect(self.on_combobox_selection_changed)
        self.building_combobox.view().pressed.connect(self.on_combobox_selection_changed)

        self.setLayout(layout)

    def load_json(self, file_path):
        """
        Loads the data from a JSON file and populates the view.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.results = json.load(f)
            self.populate_building_combobox(self.results)
            self.plot(self.results)  # Initial plot with first selection
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading JSON file: {e}")

    def populate_building_combobox(self, results):
        """
        Populates the building combobox with the results data and selects the first building.

        Args:
            results (dict): The results data to populate the combobox with.
        """
        self.building_combobox.clear()
        for key in results.keys():
            self.building_combobox.addItem(f'Building {key}')
            item = self.building_combobox.model().item(self.building_combobox.count() - 1, 0)
            item.setCheckState(Qt.Checked)

        # Automatically select the first building and replot
        if self.building_combobox.count() > 0:
            first_item = self.building_combobox.model().item(0)
            first_item.setCheckState(Qt.Checked)

        # Automatically select the first data type
        if self.data_type_combobox.count() > 0:
            first_data_item = self.data_type_combobox.model().item(0)
            first_data_item.setCheckState(Qt.Checked)

        # Generate configuration UI for each building
        self.parent.technology_tab.populate_generator_configuration(self.results)

    def on_combobox_selection_changed(self):
        """
        Replots the data when the combobox selection changes.
        """
        self.plot(self.results)

    def plot(self, results=None):
        """
        Plots the selected data types for the selected buildings, adjusting the figure size for the legend outside.
        
        Args:
            results (dict, optional): The results data to plot. Defaults to None.
        """
        if results is None:
            return

        self.figure.clear()
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        selected_data_types = self.data_type_combobox.checkedItems()
        selected_buildings = self.building_combobox.checkedItems()

        for building in selected_buildings:
            key = building.split()[-1]
            value = results[key]

            if "Heat Demand" in selected_data_types:
                ax1.plot(value["wärme"], label=f'Building {key} Heat Demand')
            if "Heating Demand" in selected_data_types:
                ax1.plot(value["heizwärme"], label=f'Building {key} Heating Demand', linestyle='--')
            if "Warmwater Demand" in selected_data_types:
                ax1.plot(value["warmwasserwärme"], label=f'Building {key} Warmwater Demand', linestyle=':')
            if "Supply Temperature" in selected_data_types:
                ax2.plot(value["vorlauftemperatur"], label=f'Building {key} Supply Temp', linestyle='-.')
            if "Return Temperature" in selected_data_types:
                ax2.plot(value["rücklauftemperatur"], label=f'Building {key} Return Temp', linestyle='-.')

        ax1.set_xlabel('Time (hours)')
        ax1.set_ylabel('Heat Demand (W)')
        ax2.set_ylabel('Temperature (°C)')

        # Legend for ax1 on the left
        ax1.legend(loc='center right', bbox_to_anchor=(-0.2, 0.5))  # Left of the plot
        # Legend for ax2 on the right
        ax2.legend(loc='center left', bbox_to_anchor=(1.2, 0.5))  # Right of the plot

        # Adjust layout to ensure the legends do not overlap the plot
        self.figure.subplots_adjust(left=0.25, right=0.75, top=0.9, bottom=0.1)

        ax1.grid()

        self.canvas.draw()


class TechnologyTab(QWidget):
    """
    A QWidget subclass for configuring heat generation technologies for individual buildings.
    This version includes a CustomListWidget for each building to manage the selected technologies.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.generator_configs = {}  # Store configurations for each building
        self.tech_objects = {}  # Store technology objects per building
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Scroll area for generator configuration per building
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        container_widget = QWidget()
        scroll_area.setWidget(container_widget)

        self.form_layout = QFormLayout(container_widget)
        layout.addWidget(QLabel("Configure Heat Generators for Selected Buildings"))
        layout.addWidget(scroll_area)

        self.setLayout(layout)

    def populate_generator_configuration(self, buildings):
        """
        Populates the form layout with generator configurations for each selected building.
        Adds a configuration button and a CustomListWidget for managing technologies per building.
        """
        # Clear the previous layout
        for i in reversed(range(self.form_layout.count())):
            widget = self.form_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        for building_id in buildings:
            row_layout = QHBoxLayout()

            # Dropdown for selecting technologies
            generator_combobox = QComboBox(self)
            generator_combobox.addItem("Gaskessel")
            generator_combobox.addItem("Biomassekessel")
            generator_combobox.addItem("BHKW")
            generator_combobox.addItem("Holzgas-BHKW")
            generator_combobox.addItem("Geothermie")
            generator_combobox.addItem("Abwärme")
            generator_combobox.addItem("Flusswasser")
            generator_combobox.addItem("AqvaHeat")
            generator_combobox.addItem("Solarthermie")
            generator_combobox.setFixedWidth(150)

            # Button to open configuration dialog
            configure_button = QPushButton(f"Configure {building_id}", self)
            configure_button.setFixedWidth(120)
            configure_button.clicked.connect(lambda _, b_id=building_id, g_cbox=generator_combobox: self.open_generator_dialog(b_id, g_cbox))

            # Create a CustomListWidget for each building to manage the technologies
            tech_list_widget = CustomListWidget(self)

            # Store configurations in dictionary for each building
            self.generator_configs[building_id] = {
                "generator_combobox": generator_combobox,
                "tech_list_widget": tech_list_widget  # Store the list widget for later updates
            }

            row_layout.addWidget(QLabel(f"Building {building_id} Generator:"))
            row_layout.addWidget(generator_combobox)
            row_layout.addWidget(configure_button)
            row_layout.addWidget(tech_list_widget)  # Add the technology list widget to the row

            self.form_layout.addRow(row_layout)

    def open_generator_dialog(self, building_id, generator_combobox):
        """
        Opens a dialog to configure the selected generator for a specific building.
        The configured technology will be added to the respective CustomListWidget.
        """
        generator_type = generator_combobox.currentText()
        tech_data = self.generator_configs.get(building_id, {})

        # Open the appropriate dialog based on the generator type
        dialog = TechInputDialog(generator_type, tech_data)
        if dialog.exec_():
            # Retrieve the inputs after the dialog is accepted
            tech_inputs = dialog.getInputs()

            # Create a display string for the tech configuration
            tech_display = f"{generator_type}: {tech_inputs}"

            # Add the configuration to the CustomListWidget for the building
            tech_list_widget = self.generator_configs[building_id]["tech_list_widget"]
            tech_list_widget.addItem(tech_display)

            QMessageBox.information(self, "Generator Configured", f"Configuration for {generator_type} saved for Building {building_id}.")


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
            "Gaskessel": GasBoiler,
            "AqvaHeat": AqvaHeat
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
        elif isinstance(tech, AqvaHeat):
            display_text += "technische Daten"
        else:
            display_text = f"Unbekannte Technologieklasse: {type(tech).__name__}"

        return display_text


class ResultsTab(QWidget):
    """
    Handles the presentation of the calculation results.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Button to trigger the calculation
        self.calc_button = QPushButton("Start Generator Calculation", self)
        self.calc_button.setStyleSheet("margin-top: 10px;")
        self.calc_button.clicked.connect(self.start_generator_calculation)
        layout.addWidget(self.calc_button)

        self.setLayout(layout)

    def start_generator_calculation(self):
        """
        Starts the generator calculation based on the configuration.
        """
        results = []
        for building_id, config in self.parent.technology_tab.generator_configs.items():
            selected_generator = config["generator_combobox"].currentText()
            generator_details = config.get("generator_details", "No details provided")  # Placeholder for dialog results

            # Dummy calculation logic
            results.append(
                f"Building {building_id} - Generator: {selected_generator}, Details: {generator_details}"
            )

        QMessageBox.information(self, "Generator Calculation", "\n".join(results))

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
