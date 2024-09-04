"""
Filename: individual_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-04
Description: Contains the IndividualTab for managing building data and calculating heat generation technologies.
"""

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton, QComboBox, QLineEdit, QMessageBox, QFormLayout, QScrollArea, QHBoxLayout)
from PyQt5.QtCore import pyqtSignal, Qt

from gui.utilities import CheckableComboBox  # Assuming you have this implemented like in BuildingTab
import json

from gui.MixDesignTab.heat_generator_dialogs import TechInputDialog  # Import your dialogs

class IndividualTab(QWidget):
    """
    The IndividualTab class manages the UI and logic for calculating heat generation technologies for buildings.

    Signals:
        data_added = pyqtSignal(object): Emitted when new data is added.
    """

    data_added = pyqtSignal(object)

    def __init__(self, folder_manager, data_manager, parent=None):
        """
        Initializes the IndividualTab instance.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.results = {}
        self.generator_configs = {}  # Store configurations for each building
        self.base_path = None

        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.update_default_path)
        self.update_default_path(self.folder_manager.project_folder)

        self.initUI()

    def update_default_path(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path

    def initUI(self):
        """
        Initializes the UI components for the IndividualTab.
        """
        main_layout = QVBoxLayout(self)

        # Add buttons
        self.load_button = QPushButton("Load JSON Data", self)
        self.load_button.clicked.connect(self.load_json_file)
        main_layout.addWidget(self.load_button)

        # Initialize the plot area
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(self.toolbar)

        # Initialize the comboboxes for data selection
        self.data_type_combobox = CheckableComboBox(self)
        self.data_type_combobox.addItem("Heat Demand")
        self.data_type_combobox.addItem("Heating Demand")
        self.data_type_combobox.addItem("Warmwater Demand")
        self.data_type_combobox.addItem("Supply Temperature")
        self.data_type_combobox.addItem("Return Temperature")

        self.building_combobox = CheckableComboBox(self)

        main_layout.addWidget(QLabel("Select Data Types"))
        main_layout.addWidget(self.data_type_combobox)
        main_layout.addWidget(QLabel("Select Buildings"))
        main_layout.addWidget(self.building_combobox)

        # Connect combobox changes to replotting
        self.data_type_combobox.view().pressed.connect(self.on_combobox_selection_changed)
        self.building_combobox.view().pressed.connect(self.on_combobox_selection_changed)

        # Scroll area for generator configuration per building
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        container_widget = QWidget()
        scroll_area.setWidget(container_widget)

        self.form_layout = QFormLayout(container_widget)
        main_layout.addWidget(QLabel("Configure Heat Generators for Selected Buildings"))
        main_layout.addWidget(scroll_area)

        # Button to trigger calculation
        self.calc_button = QPushButton("Start Generator Calculation", self)
        self.calc_button.setStyleSheet("margin-top: 10px;")
        self.calc_button.clicked.connect(self.start_generator_calculation)
        main_layout.addWidget(self.calc_button)

        self.setLayout(main_layout)

    def load_json_file(self):
        """
        Opens a file dialog to load a JSON file and loads the data.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select JSON File', f"{self.base_path}/Lastgang", 'JSON Files (*.json);;All Files (*)')
        if file_path:
            self.load_json(file_path)

    def load_json(self, file_path):
        """
        Loads data from a JSON file and populates the view.

        Args:
            file_path (str): Path to the JSON file.
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
        self.populate_generator_configuration()

    def populate_generator_configuration(self):
        """
        Dynamically creates generator configuration UI for each selected building.
        """
        # Clear the previous generator configurations
        for i in reversed(range(self.form_layout.count())):
            widget = self.form_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Add new configurations
        selected_buildings = [self.building_combobox.itemText(i) for i in range(self.building_combobox.count())]
        for building in selected_buildings:
            building_id = building.split()[-1]

            # Layout for each building's configuration (horizontal layout)
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
            configure_button.setFixedWidth(120)  # Smaller button
            configure_button.clicked.connect(lambda _, b_id=building_id, g_cbox=generator_combobox: self.open_generator_dialog(b_id, g_cbox))

            # Store configurations in dictionary for each building
            self.generator_configs[building_id] = {
                "generator_combobox": generator_combobox
            }

            # Add components to the horizontal layout
            row_layout.addWidget(QLabel(f"Building {building_id} Generator:"))
            row_layout.addWidget(generator_combobox)
            row_layout.addWidget(configure_button)

            # Add the horizontal layout as a row in the form
            self.form_layout.addRow(row_layout)

    def open_generator_dialog(self, building_id, generator_combobox):
        """
        Opens a dialog to configure the selected generator for a specific building.
        """
        generator_type = generator_combobox.currentText()
        tech_data = self.generator_configs.get(building_id, {})

        # Open the appropriate dialog based on the generator type
        dialog = TechInputDialog(generator_type, tech_data)
        if dialog.exec_():
            # Retrieve the inputs after the dialog is accepted
            self.generator_configs[building_id].update(dialog.getInputs())
            QMessageBox.information(self, "Generator Configured", f"Configuration for {generator_type} saved for Building {building_id}.")

    def on_combobox_selection_changed(self):
        """
        Replots the data when the combobox selection changes.
        """
        self.plot(self.results)

    def plot(self, results=None):
        """
        Plots the selected data types for the selected buildings.

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
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        ax1.grid()

        self.canvas.draw()

    def start_generator_calculation(self):
        """
        Starts the calculation for the selected heat generator technology for each building.

        This is currently a dummy implementation that prints the selected generators and their parameters.
        """
        results = []
        for building_id, config in self.generator_configs.items():
            selected_generator = config["generator_combobox"].currentText()
            generator_details = config.get("generator_details", "No details provided")  # Placeholder for dialog results

            # Dummy calculation logic
            results.append(
                f"Building {building_id} - Generator: {selected_generator}, Details: {generator_details}"
            )

        QMessageBox.information(self, "Generator Calculation", "\n".join(results))