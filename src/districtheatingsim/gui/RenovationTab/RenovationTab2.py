"""
Renovation Tab 2 Module
=======================

Individual building renovation analysis tab with parameter-based cost calculation.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
"""

import sys

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QComboBox, QFormLayout, QSplitter, QTabWidget
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt

from districtheatingsim.utilities.renovation_analysis import calculate_all_results

class PlotCanvas(FigureCanvas):
    """
    Custom matplotlib canvas for bar chart visualization.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """
        Initialize plot canvas.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        width : int, optional
            Canvas width.
        height : int, optional
            Canvas height.
        dpi : int, optional
            Canvas resolution.
        """
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

    def plot(self, data, title, xlabel, ylabel):
        """
        Plot bar chart with given data.

        Parameters
        ----------
        data : dict
            Data to plot.
        title : str
            Plot title.
        xlabel : str
            X-axis label.
        ylabel : str
            Y-axis label.
        """
        self.axes.clear()
        self.axes.bar(data.keys(), data.values())
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.draw()

class RenovationTab2(QWidget):
    """
    Individual building renovation analysis tab.
    
    Provides functionality for analyzing renovation costs and savings
    for individual buildings using parameter-based input.
    """
    data_added = pyqtSignal(object)

    def __init__(self, folder_manager, data_manager, parent=None):
        """
        Initialize renovation tab for individual buildings.

        Parameters
        ----------
        folder_manager : object
            Project folder manager.
        data_manager : object
            Application data manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.parent = parent

        # Connect to folder manager signals
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.project_folder)

        self.initUI()
    
    def initUI(self):
        """Initialize user interface components."""
        self.setWindowTitle("Sanierungsanalyse")

        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Input section
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        self.input_fields = {}

        tab_widget = QTabWidget()
        self.create_input_tabs(tab_widget)
        input_layout.addWidget(tab_widget)
        splitter.addWidget(input_widget)

        # Results section
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        self.create_result_section(result_layout)
        splitter.addWidget(result_widget)

        splitter.setSizes([800, 800])
        self.setLayout(main_layout)
        self.results = {}

    def create_input_tabs(self, tab_widget):
        """Create input parameter tabs with organized field groups."""
        groups = {
            "Gebäudedaten": [("Länge (m)", "10"), ("Breite (m)", "15"), ("Anzahl Stockwerke", "2"), ("Stockwerkshöhe (m)", "3")],
            "U-Werte": [("U-Wert Boden (W/m²K)", "0.77"), ("U-Wert Fassade (W/m²K)", "1.0"), 
                        ("U-Wert Dach (W/m²K)", "0.51"), ("U-Wert Fenster (W/m²K)", "3.0"), 
                        ("U-Wert Tür (W/m²K)", "4")],
            "Ziel-U-Werte": [("Ziel-U-Wert Boden (W/m²K)", "0.15"), ("Ziel-U-Wert Fassade (W/m²K)", "0.15"), 
                            ("Ziel-U-Wert Dach (W/m²K)", "0.15"), ("Ziel-U-Wert Fenster (W/m²K)", "0.8"), 
                            ("Ziel-U-Wert Tür (W/m²K)", "0.8")],
            "Kosten": [("Kosten Boden (€/m²)", "100"), ("Kosten Fassade (€/m²)", "100"), 
                    ("Kosten Dach (€/m²)", "150"), ("Kosten Fenster (€/m²)", "200"), 
                    ("Kosten Tür (€/m²)", "250")],
            "Sonstiges": [("Energiepreis IST (€/kWh)", "0.10"), ("Energiepreis Saniert (€/kWh)", "0.08"), ("Diskontierungsrate (%)", "3"), 
                        ("Jahre", "20"), ("Kaltmiete (€/m²)", "5"), 
                        ("Anteil Türflächen an Fensterfläche", "0.10"), ("Anteil Türflächen an Fassadenfläche", "0.01"), 
                        ("Luftwechselrate", "0.5"), ("Normaußentemperatur (°C)", "-12"), 
                        ("Normrauminnentemperatur (°C)", "20"), ("Heizgrenztemperatur (°C)", "15"), 
                        ("Warmwasserbedarf Wh/(m²*a)", "12.8")],
            "Betriebskosten": [("Betriebskosten Boden (€/Jahr)", "50"),
                            ("Betriebskosten Fassade (€/Jahr)", "100"), 
                            ("Betriebskosten Dach (€/Jahr)", "125"), 
                            ("Betriebskosten Fenster (€/Jahr)", "120"), 
                            ("Betriebskosten Tür (€/Jahr)", "40")],
            "Instandhaltungskosten": [("Instandhaltungskosten Boden (€/Jahr)", "25"), 
                                    ("Instandhaltungskosten Fassade (€/Jahr)", "50"), 
                                    ("Instandhaltungskosten Dach (€/Jahr)", "75"), 
                                    ("Instandhaltungskosten Fenster (€/Jahr)", "60"),
                                    ("Instandhaltungskosten Tür (€/Jahr)", "25")],                                        
            "Restwertanteil": [("Restwert-Anteil Boden", "0.30"), ("Restwert-Anteil Fassade", "0.30"),
                            ("Restwert-Anteil Dach", "0.50"), ("Restwert-Anteil Fenster", "0.20"),
                            ("Restwert-Anteil Tür", "0.10")],
            "Förderung": [("Förderquote", "0.5")]
        }

        for group_name, fields in groups.items():
            group_widget = QWidget()
            form_layout = QFormLayout()
            for label, default in fields:
                self.input_fields[label] = QLineEdit()
                self.input_fields[label].setText(default)
                form_layout.addRow(QLabel(label), self.input_fields[label])
            group_widget.setLayout(form_layout)
            tab_widget.addTab(group_widget, group_name)

    def create_result_section(self, layout):
        """Create results display section with plot and controls."""
        self.run_button = QPushButton("Analyse durchführen")
        self.run_button.clicked.connect(self.run_analysis)
        layout.addWidget(self.run_button)

        self.combo_box = QComboBox()
        self.combo_box.addItems(["Investitionskosten in €", "Gesamtenergiebedarf in kWh/a", "Energieeinsparung in kWh/a", "Kosteneinsparung in €/a",
                                 "Kaltmieten in €/m²", "Warmmieten in €/m²", "Amortisationszeit in a", "NPV in €", "LCCA in €", "ROI"])
        self.combo_box.currentIndexChanged.connect(self.update_plot)
        layout.addWidget(self.combo_box)

        self.canvas = PlotCanvas(self, width=12, height=6)
        layout.addWidget(self.canvas)

        self.result_label = QLabel("Ergebnisse werden hier angezeigt")
        layout.addWidget(self.result_label)

    def updateDefaultPath(self, new_base_path):
        """
        Update project default path.

        Parameters
        ----------
        new_base_path : str
            New base path for file operations.
        """
        self.base_path = new_base_path

    @pyqtSlot()
    def run_analysis(self):
        """Run renovation analysis based on input parameters."""
        try:
            # Extract values from input fields
            length = float(self.input_fields["Länge (m)"].text())
            width = float(self.input_fields["Breite (m)"].text())
            floors = int(self.input_fields["Anzahl Stockwerke"].text())
            floor_height = float(self.input_fields["Stockwerkshöhe (m)"].text())
            u_ground = float(self.input_fields["U-Wert Boden (W/m²K)"].text())
            u_wall = float(self.input_fields["U-Wert Fassade (W/m²K)"].text())
            u_roof = float(self.input_fields["U-Wert Dach (W/m²K)"].text())
            u_window = float(self.input_fields["U-Wert Fenster (W/m²K)"].text())
            u_door = float(self.input_fields["U-Wert Tür (W/m²K)"].text())
            energy_price_ist = float(self.input_fields["Energiepreis IST (€/kWh)"].text())
            energy_price_saniert = float(self.input_fields["Energiepreis Saniert (€/kWh)"].text())
            discount_rate = float(self.input_fields["Diskontierungsrate (%)"].text()) / 100
            years = int(self.input_fields["Jahre"].text())
            cold_rent = float(self.input_fields["Kaltmiete (€/m²)"].text())
            target_u_ground = float(self.input_fields["Ziel-U-Wert Boden (W/m²K)"].text())
            target_u_wall = float(self.input_fields["Ziel-U-Wert Fassade (W/m²K)"].text())
            target_u_roof = float(self.input_fields["Ziel-U-Wert Dach (W/m²K)"].text())
            target_u_window = float(self.input_fields["Ziel-U-Wert Fenster (W/m²K)"].text())
            target_u_door = float(self.input_fields["Ziel-U-Wert Tür (W/m²K)"].text())
            cost_ground = float(self.input_fields["Kosten Boden (€/m²)"].text())
            cost_wall = float(self.input_fields["Kosten Fassade (€/m²)"].text())
            cost_roof = float(self.input_fields["Kosten Dach (€/m²)"].text())
            cost_window = float(self.input_fields["Kosten Fenster (€/m²)"].text())
            cost_door = float(self.input_fields["Kosten Tür (€/m²)"].text())
            fracture_windows = float(self.input_fields["Anteil Türflächen an Fensterfläche"].text())
            fracture_doors = float(self.input_fields["Anteil Türflächen an Fassadenfläche"].text())
            air_change_rate = float(self.input_fields["Luftwechselrate"].text())
            min_air_temp = float(self.input_fields["Normaußentemperatur (°C)"].text())
            room_temp = float(self.input_fields["Normrauminnentemperatur (°C)"].text())
            max_air_temp_heating = float(self.input_fields["Heizgrenztemperatur (°C)"].text())
            warmwasserbedarf = float(self.input_fields["Warmwasserbedarf Wh/(m²*a)"].text())

            betriebskosten = {
                'ground_u': float(self.input_fields["Betriebskosten Boden (€/Jahr)"].text()),
                'wall_u': float(self.input_fields["Betriebskosten Fassade (€/Jahr)"].text()),
                'roof_u': float(self.input_fields["Betriebskosten Dach (€/Jahr)"].text()),
                'window_u': float(self.input_fields["Betriebskosten Fenster (€/Jahr)"].text()),
                'door_u': float(self.input_fields["Betriebskosten Tür (€/Jahr)"].text())
            }

            instandhaltungskosten = {
                'ground_u': float(self.input_fields["Instandhaltungskosten Boden (€/Jahr)"].text()),
                'wall_u': float(self.input_fields["Instandhaltungskosten Fassade (€/Jahr)"].text()),
                'roof_u': float(self.input_fields["Instandhaltungskosten Dach (€/Jahr)"].text()),
                'window_u': float(self.input_fields["Instandhaltungskosten Fenster (€/Jahr)"].text()),
                'door_u': float(self.input_fields["Instandhaltungskosten Tür (€/Jahr)"].text())
            }

            restwert_anteile = {
                'ground_u': float(self.input_fields["Restwert-Anteil Boden"].text()),
                'wall_u': float(self.input_fields["Restwert-Anteil Fassade"].text()),
                'roof_u': float(self.input_fields["Restwert-Anteil Dach"].text()),
                'window_u': float(self.input_fields["Restwert-Anteil Fenster"].text()),
                'door_u': float(self.input_fields["Restwert-Anteil Tür"].text())
            }

            foerderquote = float(self.input_fields["Förderquote"].text())

            self.results = calculate_all_results(
                length, width, floors, floor_height, u_ground, u_wall, u_roof, u_window, u_door,
                energy_price_ist, energy_price_saniert, discount_rate, years, cold_rent, target_u_ground,
                target_u_wall, target_u_roof, target_u_window, target_u_door,
                cost_ground, cost_wall, cost_roof, cost_window, cost_door,
                fracture_windows, fracture_doors, air_change_rate, min_air_temp, room_temp, max_air_temp_heating,
                warmwasserbedarf, betriebskosten, instandhaltungskosten, restwert_anteile, foerderquote, self.data_manager.get_try_filename()
            )

            self.result_label.setText("Analyse abgeschlossen. Wählen Sie ein Diagramm aus der Liste.")
            self.update_plot()

        except Exception as e:
            self.result_label.setText(f"Fehler: {str(e)}")

    @pyqtSlot()
    def update_plot(self):
        """Update plot display based on selected analysis parameter."""
        if not self.results:
            return

        selected_plot = self.combo_box.currentText()
        data = self.results[selected_plot]
        title = selected_plot
        xlabel = "Komponente"
        ylabel = "Wert"

        self.canvas.plot(data, title, xlabel, ylabel)

        # Display calculated results in result label
        result_text = f"{title}:\n"
        for k, v in data.items():
            result_text += f"{k}: {v:.2f}\n"
        self.result_label.setText(result_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QWidget()
    renovation_tab = RenovationTab2()
    main_window.setCentralWidget(renovation_tab)
    main_window.show()
    sys.exit(app.exec_())