"""
Filename: RenovationTab2.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the RenovationTab2, the Tab for individual renovation cost analysis.
"""

import sys

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QFormLayout, QHBoxLayout, QScrollArea
from PyQt5.QtCore import pyqtSlot, pyqtSignal

from utilities.SanierungsanalysefuerGUI import calculate_all_results


class PlotCanvas(FigureCanvas):
    """
    A canvas for plotting bar charts using matplotlib.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

    def plot(self, data, title, xlabel, ylabel):
        """
        Plots a bar chart with the given data.

        Args:
            data (dict): The data to plot.
            title (str): The title of the plot.
            xlabel (str): The label for the x-axis.
            ylabel (str): The label for the y-axis.
        """
        self.axes.clear()
        self.axes.bar(data.keys(), data.values())
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.draw()


class RenovationTab2(QWidget):
    """
    The RenovationTab2 class provides a tab for performing individual renovation cost analysis.
    """
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent

        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.updateDefaultPath(self.data_manager.project_folder)

        self.initUI()
    
    def initUI(self):
        """
        Initializes the user interface.
        """
        self.setWindowTitle("Sanierungsanalyse")
        self.setGeometry(100, 100, 1200, 800)
        
        main_layout = QVBoxLayout()

        self.input_fields = {}
        self.create_input_groups(main_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setLayout(main_layout)
        scroll.setWidget(scroll_content)

        layout = QHBoxLayout()
        layout.addWidget(scroll)

        result_layout = QVBoxLayout()

        self.run_button = QPushButton("Analyse durchführen")
        self.run_button.clicked.connect(self.run_analysis)
        result_layout.addWidget(self.run_button)

        self.combo_box = QComboBox()
        self.combo_box.addItems(["Investitionskosten in €", "Gesamtenergiebedarf in kWh/a", "Energieeinsparung in kWh/a", "Kosteneinsparung in €/a", 
                                "Kaltmieten in €/m²", "Warmmieten in €/m²", "Amortisationszeit in a", "NPV in €", "LCCA in €", "ROI"])
        self.combo_box.currentIndexChanged.connect(self.update_plot)
        result_layout.addWidget(self.combo_box)

        self.canvas = PlotCanvas(self, width=12, height=5)
        result_layout.addWidget(self.canvas)

        self.result_label = QLabel("Ergebnisse werden hier angezeigt")
        result_layout.addWidget(self.result_label)

        layout.addLayout(result_layout)

        self.setLayout(layout)

        self.results = {}

    def create_input_groups(self, layout):
        """
        Creates input groups for various parameters.

        Args:
            layout (QVBoxLayout): The main layout to add input groups to.
        """
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        main_layout = QHBoxLayout()

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

        for i, (group_name, fields) in enumerate(groups.items()):
            group_box = QGroupBox(group_name)
            form_layout = QFormLayout()
            for label, default in fields:
                self.input_fields[label] = QLineEdit()
                self.input_fields[label].setText(default)
                form_layout.addRow(QLabel(label), self.input_fields[label])
            group_box.setLayout(form_layout)
            if i % 2 == 0:
                left_layout.addWidget(group_box)
            else:
                right_layout.addWidget(group_box)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        layout.addLayout(main_layout)

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path
        
    @pyqtSlot()
    def run_analysis(self):
        """
        Runs the renovation analysis based on the input parameters.
        """
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
                warmwasserbedarf, betriebskosten, instandhaltungskosten, restwert_anteile, foerderquote, self.parent.try_filename
            )

            self.result_label.setText("Analyse abgeschlossen. Wählen Sie ein Diagramm aus der Liste.")
            self.update_plot()

        except Exception as e:
            self.result_label.setText(f"Fehler: {str(e)}")

    @pyqtSlot()
    def update_plot(self):
        """
        Updates the plot based on the selected item in the combo box.
        """
        if not self.results:
            return

        selected_plot = self.combo_box.currentText()
        data = self.results[selected_plot]
        title = selected_plot
        xlabel = "Komponente"
        ylabel = "Wert"

        self.canvas.plot(data, title, xlabel, ylabel)

        # Anzeige der berechneten Ergebnisse im result_label
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
