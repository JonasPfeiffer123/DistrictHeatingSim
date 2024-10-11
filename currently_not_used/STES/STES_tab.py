import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QHBoxLayout, QFormLayout)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd

class ThermalStorageUI(QWidget):
    def __init__(self):
        super().__init__()

        # Layout setup
        self.initUI()

    def initUI(self):
        # Main layout
        layout = QVBoxLayout()

        # Form layout for input parameters
        form_layout = QFormLayout()

        # Dropdown for storage type
        self.storage_type_combo = QComboBox(self)
        self.storage_type_combo.addItems(["cylindrical", "rectangular", "pit"])
        self.storage_type_combo.setCurrentText("cylindrical")
        form_layout.addRow("Storage Type:", self.storage_type_combo)

        # Input fields for storage dimensions
        self.dimensions_input = QLineEdit(self)
        self.dimensions_input.setText("10,12")  # Default values: radius=10m, height=12m for cylindrical
        form_layout.addRow("Dimensions (comma separated):", self.dimensions_input)

        # Other inputs with default values
        self.rho_input = QLineEdit(self)
        self.rho_input.setText("1000")  # Default: Density of water (kg/m³)
        form_layout.addRow("Density (kg/m³):", self.rho_input)

        self.cp_input = QLineEdit(self)
        self.cp_input.setText("4180")  # Default: Specific heat capacity of water (J/kg*K)
        form_layout.addRow("Specific Heat Capacity (J/kg*K):", self.cp_input)

        self.T_ref_input = QLineEdit(self)
        self.T_ref_input.setText("10")  # Default: Reference temperature (°C)
        form_layout.addRow("Reference Temperature (°C):", self.T_ref_input)

        self.U_top_input = QLineEdit(self)
        self.U_top_input.setText("0.3")  # Default: U-value top (W/m²K)
        form_layout.addRow("U-value Top (W/m²K):", self.U_top_input)

        self.U_side_input = QLineEdit(self)
        self.U_side_input.setText("0.06")  # Default: U-value side (W/m²K)
        form_layout.addRow("U-value Side (W/m²K):", self.U_side_input)

        self.U_bottom_input = QLineEdit(self)
        self.U_bottom_input.setText("0.4")  # Default: U-value bottom (W/m²K)
        form_layout.addRow("U-value Bottom (W/m²K):", self.U_bottom_input)

        self.T_amb_input = QLineEdit(self)
        self.T_amb_input.setText("10")  # Default: Ambient temperature (°C)
        form_layout.addRow("Ambient Temperature (°C):", self.T_amb_input)

        self.T_soil_input = QLineEdit(self)
        self.T_soil_input.setText("10")  # Default: Soil temperature (°C)
        form_layout.addRow("Soil Temperature (°C):", self.T_soil_input)

        self.T_max_input = QLineEdit(self)
        self.T_max_input.setText("95")  # Default: Max storage temperature (°C)
        form_layout.addRow("Max Storage Temperature (°C):", self.T_max_input)

        self.T_min_input = QLineEdit(self)
        self.T_min_input.setText("40")  # Default: Min storage temperature (°C)
        form_layout.addRow("Min Storage Temperature (°C):", self.T_min_input)

        self.initial_temp_input = QLineEdit(self)
        self.initial_temp_input.setText("60")  # Default: Initial storage temperature (°C)
        form_layout.addRow("Initial Temperature (°C):", self.initial_temp_input)

        # Submit button
        submit_button = QPushButton("Run Simulation", self)
        submit_button.clicked.connect(self.run_simulation)
        form_layout.addWidget(submit_button)

        # Add the form layout to the main layout
        layout.addLayout(form_layout)

        # Matplotlib Figure
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        # Set the layout for the window
        self.setLayout(layout)

        # Window properties
        self.setWindowTitle("STES Simulation")
        self.setGeometry(100, 100, 800, 600)

    def run_simulation(self):
        # Get input values
        storage_type = self.storage_type_combo.currentText()
        dimensions = tuple(map(float, self.dimensions_input.text().split(',')))
        rho = float(self.rho_input.text())
        cp = float(self.cp_input.text())
        T_ref = float(self.T_ref_input.text())
        U_top = float(self.U_top_input.text())
        U_side = float(self.U_side_input.text())
        U_bottom = float(self.U_bottom_input.text())
        T_amb = float(self.T_amb_input.text())
        T_soil = float(self.T_soil_input.text())
        T_max = float(self.T_max_input.text())
        T_min = float(self.T_min_input.text())
        initial_temp = float(self.initial_temp_input.text())

        # Simulated heat input and output (example random values)
        hours = 8760
        Q_in = np.random.uniform(10000, 40000, hours)  # Heat input in W
        #Q_out = np.random.uniform(10000, 20000, hours)  # Heat output in W
        
        # Load Q_out from Lastgang.csv
        file_path = os.path.abspath('currently_not_used\STES\Lastgang.csv')
        df = pd.read_csv(file_path, delimiter=';', encoding='utf-8')
        Q_out = df['Gesamtwärmebedarf_Gebäude_kW'].values*1000 # from kW to W

        # Example: run a simple simulation using the provided values
        T_sto = self.simulate_example(storage_type, dimensions, rho, cp, T_ref, U_top, U_side, U_bottom, T_amb, T_soil, T_max, T_min, initial_temp, hours, Q_in, Q_out)

        # Plot results
        self.plot_results(T_sto)

    def simulate_example(self, storage_type, dimensions, rho, cp, T_ref, U_top, U_side, U_bottom, T_amb, T_soil, T_max, T_min, initial_temp, hours, Q_in, Q_out):
        # Placeholder for a simple simulation
        T_sto = np.zeros(hours)
        T_sto[0] = initial_temp
        for t in range(1, hours):
            T_sto[t] = T_sto[t-1] + (Q_in[t] - Q_out[t]) / (rho * cp * dimensions[0] * dimensions[1])
            T_sto[t] = np.clip(T_sto[t], T_min, T_max)
        return T_sto

    def plot_results(self, T_sto):
        # Clear previous figure
        self.fig.clear()

        # Add new subplot
        ax = self.fig.add_subplot(111)
        ax.plot(T_sto, label="Storage Temperature")
        ax.set_xlabel("Time (hours)")
        ax.set_ylabel("Temperature (°C)")
        ax.set_title("Storage Temperature over Time")
        ax.legend()

        # Draw the canvas
        self.canvas.draw()

# Run the PyQt5 application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ThermalStorageUI()
    window.show()
    sys.exit(app.exec_())
