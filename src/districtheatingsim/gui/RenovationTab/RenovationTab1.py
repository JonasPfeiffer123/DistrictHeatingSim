"""
Filename: RenovationTab1.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
Description: Contains the RenovationTab1, the Tab for LOD2 data based renovation cost analysis.
"""

import sys
import traceback

import geopandas as gpd

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QComboBox, 
                             QFormLayout, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QSplitter, QTabWidget)
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt

from districtheatingsim.utilities.renovation_analysis import SanierungsAnalyse

class PlotCanvas(FigureCanvas):
    """
    Custom QWidget for rendering Matplotlib plots in a PyQt5 application.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """
        Initializes the PlotCanvas.

        Args:
            parent (QWidget, optional): The parent widget. Defaults to None.
            width (int, optional): The width of the canvas. Defaults to 5.
            height (int, optional): The height of the canvas. Defaults to 4.
            dpi (int, optional): The resolution of the canvas. Defaults to 100.
        """
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

    def plot(self, data_ist, data_saniert, title, xlabel, ylabel):
        """
        Plots bar charts for the given data.

        Args:
            data_ist (dict): Data for the IST state.
            data_saniert (dict): Data for the saniert state.
            title (str): The title of the plot.
            xlabel (str): The label for the x-axis.
            ylabel (str): The label for the y-axis.
        """
        self.axes.clear()
        width = 0.35  # the width of the bars

        y = list(range(len(data_ist)))
        y_labels = list(data_ist.keys())

        self.axes.barh(y, data_ist.values(), width, label='IST')
        if data_saniert:
            self.axes.barh([p + width for p in y], data_saniert.values(), width, label='Saniert')

        self.axes.set_title(title)
        self.axes.set_ylabel(xlabel)
        self.axes.set_xlabel(ylabel)
        self.axes.set_yticks([p + width / 2 for p in y])
        self.axes.set_yticklabels(y_labels)
        self.axes.legend()
        self.draw()


class RenovationTab1(QWidget):
    """
    The RenovationTab1 class, responsible for the LOD2 data based renovation cost analysis.

    Attributes:
        data_added (pyqtSignal): Signal that emits data as an object.
        data_manager (object): The data manager object.
        base_path (str): The base path for the project.
        ist_geojson (GeoDataFrame): GeoDataFrame containing IST state data.
        saniert_geojson (GeoDataFrame): GeoDataFrame containing saniert state data.
        results (dict): Dictionary to store analysis results.
        input_fields (dict): Dictionary to store input fields.
        RELEVANT_FIELDS (list): List of relevant fields to extract from GeoJSON.
    """
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, folder_manager, parent=None):
        """
        Initializes the RenovationTab1.

        Args:
            data_manager (object): The data manager.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        
        # Connect to the data manager signal
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        # Update the base path immediately with the current project folder
        self.updateDefaultPath(self.folder_manager.project_folder)

        self.initUI()
    
    def initUI(self):
        """
        Initializes the UI components of the RenovationTab1.
        """
        self.setWindowTitle("Sanierungsanalyse")
        #self.setGeometry(100, 100, 1200, 800)

        main_layout = QVBoxLayout()

        # Main splitter to divide the UI into input and result sections
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Creating input sections
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        self.input_fields = {}

        tab_widget = QTabWidget()
        self.create_input_tabs(tab_widget)
        input_layout.addWidget(tab_widget)

        #scroll = QScrollArea()
        #scroll.setWidgetResizable(True)
        #scroll.setWidget(input_widget)
        splitter.addWidget(input_widget)

        # Creating results and plotting sections
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        self.create_result_section(result_layout)
        splitter.addWidget(result_widget)

        splitter.setSizes([800, 800])  # Balance the splitter sections

        self.setLayout(main_layout)
        self.results = {}
        self.ist_geojson = None
        self.saniert_geojson = None

        # Liste der relevanten Felder
        self.RELEVANT_FIELDS = [
            'ID', 'Land', 'Bundesland', 'Stadt', 'Adresse', 'Wärmebedarf',
            'Gebäudetyp', 'Subtyp', 'Warmwasseranteil', 'Typ_Heizflächen', 'VLT_max', 
            'Steigung_Heizkurve', 'RLT_max', 'UTM_X', 'UTM_Y', 'Ground_Area', 
            'Wall_Area', 'Roof_Area', 'Volume', 'Nutzungstyp', 'Typ', 
            'Gebäudezustand', 'ww_demand_kWh_per_m2', 'air_change_rate', 
            'fracture_windows', 'fracture_doors', 'Normaußentemperatur', 'room_temp', 
            'max_air_temp_heating', 'wall_u', 'roof_u', 'window_u', 'door_u', 
            'ground_u'
        ]

    def create_input_tabs(self, tab_widget):
        # Adding a new tab for file loading
        file_tab = QWidget()
        file_layout = QVBoxLayout()

        self.load_button_ist = QPushButton("IST-Stand GeoJSON laden")
        self.load_button_ist.clicked.connect(self.load_ist_geojson)
        file_layout.addWidget(self.load_button_ist)

        self.ist_table = QTableWidget()
        file_layout.addWidget(self.ist_table)

        self.load_button_saniert = QPushButton("Sanierten Stand GeoJSON laden")
        self.load_button_saniert.clicked.connect(self.load_saniert_geojson)
        file_layout.addWidget(self.load_button_saniert)

        self.saniert_table = QTableWidget()
        file_layout.addWidget(self.saniert_table)

        file_tab.setLayout(file_layout)
        tab_widget.addTab(file_tab, "Dateien laden")

        # Grouping input fields into additional tabs for better organization
        groups = {
            "Kosten": [("Kosten Boden (€/m²)", "100"), ("Kosten Fassade (€/m²)", "100"),
                        ("Kosten Dach (€/m²)", "150"), ("Kosten Fenster (€/m²)", "200"),
                        ("Kosten Tür (€/m²)", "250")],
            "Sonstiges": [("Energiepreis vor Sanierung (€/kWh)", "0.10"),
                        ("Energiepreis nach Sanierung (€/kWh)", "0.08"),
                        ("Diskontierungsrate (%)", "3"),
                        ("Jahre", "20"), ("Kaltmiete (€/m²)", "5")],
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
        self.run_button = QPushButton("Analyse durchführen")
        self.run_button.clicked.connect(self.run_analysis)
        layout.addWidget(self.run_button)

        self.combo_box = QComboBox()
        self.combo_box.addItems(["Investitionskosten in €", "Gesamtenergiebedarf in kWh/a", "Energieeinsparung in kWh/a", "Kosteneinsparung in €/a",
                                 "Kaltmieten in €/m²", "Warmmieten in €/m²", "Amortisationszeit in a", "NPV in €", "LCCA in €", "ROI"])
        self.combo_box.currentIndexChanged.connect(self.update_plot)
        layout.addWidget(self.combo_box)

        self.canvas = PlotCanvas(self, width=12, height=6)  # Increased the canvas size
        layout.addWidget(self.canvas)

        self.result_label = QLabel("Ergebnisse werden hier angezeigt")
        layout.addWidget(self.result_label)

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default path for the project.

        Args:
            new_base_path (str): The new base path for the project.
        """
        self.base_path = new_base_path
        
    def load_ist_geojson(self):
        """
        Loads the IST state GeoJSON file and populates the IST table with its data.
        """
        path, _ = QFileDialog.getOpenFileName(self, "IST-Stand GeoJSON laden", self.base_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                self.ist_geojson = gpd.read_file(path)
                if self.ist_geojson is None:
                    raise ValueError("Die GeoJSON-Datei konnte nicht geladen werden.")
                # Filtern der Parent-Objekte und Duplikate nach ID entfernen
                self.ist_geojson = self.ist_geojson[self.ist_geojson['Obj_Parent'].isnull()]
                self.ist_geojson = self.ist_geojson.drop_duplicates(subset='ID')
                self.populate_table(self.ist_geojson, self.ist_table)
                QMessageBox.information(self, "Erfolg", f"IST-Stand GeoJSON erfolgreich geladen: {path}")
            except Exception as e:
                tb_str = traceback.format_exception(type(e), e, e.__traceback__)
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der IST-Stand GeoJSON:\n{''.join(tb_str)}")

    def load_saniert_geojson(self):
        """
        Loads the saniert state GeoJSON file and populates the saniert table with its data.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Sanierten Stand GeoJSON laden", self.base_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                self.saniert_geojson = gpd.read_file(path)
                if self.saniert_geojson is None:
                    raise ValueError("Die GeoJSON-Datei konnte nicht geladen werden.")
                # Filtern der Parent-Objekte und Duplikate nach ID entfernen
                self.saniert_geojson = self.saniert_geojson[self.saniert_geojson['Obj_Parent'].isnull()]
                self.saniert_geojson = self.saniert_geojson.drop_duplicates(subset='ID')
                self.populate_table(self.saniert_geojson, self.saniert_table)
                QMessageBox.information(self, "Erfolg", f"Sanierten Stand GeoJSON erfolgreich geladen: {path}")
            except Exception as e:
                tb_str = traceback.format_exception(type(e), e, e.__traceback__)
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der sanierten Stand GeoJSON:\n{''.join(tb_str)}")

    def populate_table(self, gdf, table_widget):
        """
        Populates the given table widget with data from the GeoDataFrame.

        Args:
            gdf (GeoDataFrame): The GeoDataFrame containing the data.
            table_widget (QTableWidget): The table widget to populate.
        """
        try:
            properties_list = gdf.drop(columns='geometry').to_dict(orient='records')
            if not properties_list:
                raise ValueError("Die GeoJSON-Datei enthält keine gültigen 'properties'.")
            
            # Filter properties to only include relevant fields
            filtered_properties_list = [
                {key: value for key, value in properties.items() if key in self.RELEVANT_FIELDS}
            for properties in properties_list]
            
            columns = self.RELEVANT_FIELDS
            
            table_widget.setRowCount(len(filtered_properties_list))
            table_widget.setColumnCount(len(columns))
            table_widget.setHorizontalHeaderLabels(columns)
            
            for row, properties in enumerate(filtered_properties_list):
                for col, key in enumerate(columns):
                    value = properties.get(key, "")
                    table_widget.setItem(row, col, QTableWidgetItem(str(value)))
        except Exception as e:
            tb_str = traceback.format_exception(type(e), e, e.__traceback__)
            QMessageBox.critical(self, "Fehler", f"Ein Fehler ist beim Befüllen der Tabelle aufgetreten:\n{''.join(tb_str)}")

    def extract_building_info(self, gdf):
        """
        Extracts building information from the given GeoDataFrame.

        Args:
            gdf (GeoDataFrame): The GeoDataFrame containing the data.

        Returns:
            list: A list of dictionaries containing building information.
        """
        buildings = []
        for _, properties in gdf.drop(columns='geometry').iterrows():
            building = {
                'ID': properties.get('ID'),
                'ground_area': properties.get('Ground_Area', 0),
                'wall_area': properties.get('Wall_Area', 0),
                'roof_area': properties.get('Roof_Area', 0),
                'building_volume': properties.get('Volume', 0),
                'Wärmebedarf': properties.get('Wärmebedarf', 0),
                'Warmwasseranteil': properties.get('Warmwasseranteil', 0),
                'fracture_windows': properties.get('fracture_windows', 0),
                'fracture_doors': properties.get('fracture_doors', 0),
                'Adresse': properties.get('Adresse', "")
            }
            buildings.append(building)
        return buildings

    @pyqtSlot()
    def run_analysis(self):
        """
        Runs the renovation analysis using the loaded GeoJSON data and input parameters.
        """
        try:
            if self.ist_geojson is None or self.saniert_geojson is None:
                QMessageBox.critical(self, "Fehler", "Beide GeoJSON-Dateien müssen geladen werden.")
                return

            ist_buildings = self.extract_building_info(self.ist_geojson)
            saniert_buildings = self.extract_building_info(self.saniert_geojson)

            energy_price_ist = float(self.input_fields["Energiepreis vor Sanierung (€/kWh)"].text())
            energy_price_saniert = float(self.input_fields["Energiepreis nach Sanierung (€/kWh)"].text())
            discount_rate = float(self.input_fields["Diskontierungsrate (%)"].text()) / 100
            years = int(self.input_fields["Jahre"].text())
            cold_rent = float(self.input_fields["Kaltmiete (€/m²)"].text())
            cost_ground = float(self.input_fields["Kosten Boden (€/m²)"].text())
            cost_wall = float(self.input_fields["Kosten Fassade (€/m²)"].text())
            cost_roof = float(self.input_fields["Kosten Dach (€/m²)"].text())
            cost_window = float(self.input_fields["Kosten Fenster (€/m²)"].text())
            cost_door = float(self.input_fields["Kosten Tür (€/m²)"].text())
            foerderquote = float(self.input_fields["Förderquote"].text())

            # Betriebskosten und Instandhaltungskosten
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

            results = {}

            for ist_building, saniert_building in zip(ist_buildings, saniert_buildings):
                ist_heat_demand = ist_building['Wärmebedarf']
                saniert_heat_demand = saniert_building['Wärmebedarf']

                analyse = SanierungsAnalyse(ist_heat_demand, saniert_heat_demand, energy_price_ist, energy_price_saniert, discount_rate, years)
                kosteneinsparung = analyse.berechne_kosteneinsparungen()
                investitionskosten = {
                    'ground_u': cost_ground * ist_building["ground_area"],
                    'wall_u': cost_wall * ist_building["wall_area"],
                    'roof_u': cost_roof * ist_building["roof_area"],
                    'window_u': cost_window * ist_building["wall_area"] * ist_building["fracture_windows"],
                    'door_u': cost_door * ist_building["wall_area"] * ist_building["fracture_doors"]
                }

                # Gesamtinvestitionskosten und Förderquote berücksichtigen
                gesamt_investitionskosten = sum(investitionskosten.values())
                effektive_investitionskosten = gesamt_investitionskosten * (1 - foerderquote)

                amortisationszeit = analyse.berechne_amortisationszeit(gesamt_investitionskosten, foerderquote)
                npv = analyse.berechne_npv(gesamt_investitionskosten, foerderquote)
                lcca = analyse.lcca(gesamt_investitionskosten, sum(betriebskosten.values()), sum(instandhaltungskosten.values()), sum(restwert_anteile.values()), foerderquote)
                roi = analyse.berechne_roi(gesamt_investitionskosten, foerderquote)

                neue_kaltmiete_pro_m2 = cold_rent + effektive_investitionskosten / (amortisationszeit * 12 * ist_building['ground_area']) if amortisationszeit != 0 else 0
                neue_warmmiete_pro_m2 = neue_kaltmiete_pro_m2 + ((saniert_heat_demand / 12) / ist_building['ground_area']) * energy_price_saniert

                adresse = f"{ist_building['Adresse']}"

                results[adresse] = {
                    'Investitionskosten in €': sum(investitionskosten.values()),
                    'Gesamtenergiebedarf in kWh/a (IST)': ist_heat_demand,
                    'Gesamtenergiebedarf in kWh/a (Saniert)': saniert_heat_demand,
                    'Energieeinsparung in kWh/a': ist_heat_demand - saniert_heat_demand,
                    'Kosteneinsparung in €/a': kosteneinsparung,
                    'Kaltmieten in €/m² (IST)': cold_rent,
                    'Kaltmieten in €/m² (Saniert)': neue_kaltmiete_pro_m2,
                    'Warmmieten in €/m² (IST)': cold_rent + ((ist_heat_demand / 12) / ist_building['ground_area']) * energy_price_ist,
                    'Warmmieten in €/m² (Saniert)': neue_warmmiete_pro_m2,
                    'Amortisationszeit in a': amortisationszeit,
                    'NPV in €': npv,
                    'LCCA in €': lcca,
                    'ROI': roi
                }

            self.results = results
            self.result_label.setText("Analyse abgeschlossen. Wählen Sie ein Diagramm aus der Liste.")
            self.update_plot()

        except Exception as e:
            tb_str = traceback.format_exception(type(e), e, e.__traceback__)
            self.result_label.setText(f"Fehler: {''.join(tb_str)}")

    @pyqtSlot()
    def update_plot(self):
        """
        Updates the plot based on the selected item in the combo box.
        """
        if not self.results:
            return

        selected_plot = self.combo_box.currentText()
        result_text = f"{selected_plot}:\n"
        
        if selected_plot in ["Gesamtenergiebedarf in kWh/a", "Kaltmieten in €/m²", "Warmmieten in €/m²"]:
            data_ist = {adresse: values[f"{selected_plot} (IST)"] for adresse, values in self.results.items()}
            data_saniert = {adresse: values[f"{selected_plot} (Saniert)"] for adresse, values in self.results.items()}
            
            # Plot IST und Saniert Zustand
            self.canvas.plot(data_ist, data_saniert, f"{selected_plot}", "Adresse", "Wert")
            
            for k in data_ist.keys():
                result_text += f"{k} (IST): {data_ist[k]:.2f}\n"
                result_text += f"{k} (Saniert): {data_saniert[k]:.2f}\n"
        else:
            data = {adresse: values[selected_plot] for adresse, values in self.results.items()}
            title = selected_plot
            xlabel = "Adresse"
            ylabel = "Wert"
            
            self.canvas.plot(data, {}, title, xlabel, ylabel)  # Empty dictionary for saniert to avoid plotting errors
            
            for k, v in data.items():
                result_text += f"{k}: {v:.2f}\n"
        
        #self.result_label.setText(result_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QWidget()
    renovation_tab = RenovationTab1()
    main_layout = QVBoxLayout(main_window)
    main_layout.addWidget(renovation_tab)
    main_window.setLayout(main_layout)
    main_window.show()
    sys.exit(app.exec_())
