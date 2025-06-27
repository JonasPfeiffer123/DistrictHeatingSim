"""
Renovation Tab 1 Module
=======================

District renovation analysis tab for LOD2 data based renovation cost analysis.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-08-01
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
    Custom matplotlib canvas for rendering renovation analysis plots.
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

    def plot(self, data_ist, data_saniert, title, xlabel, ylabel):
        """
        Plot bar charts for renovation analysis data.

        Parameters
        ----------
        data_ist : dict
            Current state data.
        data_saniert : dict
            Renovated state data.
        title : str
            Plot title.
        xlabel : str
            X-axis label.
        ylabel : str
            Y-axis label.
        """
        self.axes.clear()
        width = 0.35

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
    District renovation analysis tab for LOD2 building data.
    
    Provides functionality for analyzing renovation costs and savings
    for building districts using GeoJSON data input.
    """
    data_added = pyqtSignal(object)

    def __init__(self, folder_manager, parent=None):
        """
        Initialize renovation tab.

        Parameters
        ----------
        folder_manager : object
            Project folder manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        
        # Connect to folder manager signals
        self.folder_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.folder_manager.project_folder)

        self.initUI()
    
    def initUI(self):
        """Initialize user interface components."""
        self.setWindowTitle("Sanierungsanalyse")
        
        main_layout = QVBoxLayout()
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
        
        # Initialize data containers
        self.results = {}
        self.ist_geojson = None
        self.saniert_geojson = None
        
        # Define relevant GeoJSON fields
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
        """Create input parameter tabs with organized field groups."""
        # File loading tab
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

        # Parameter groups
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
        
    def load_ist_geojson(self):
        """Load current state GeoJSON file and populate table."""
        path, _ = QFileDialog.getOpenFileName(self, "IST-Stand GeoJSON laden", self.base_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                self.ist_geojson = gpd.read_file(path)
                if self.ist_geojson is None:
                    raise ValueError("Die GeoJSON-Datei konnte nicht geladen werden.")
                
                # Filter parent objects and remove duplicates
                self.ist_geojson = self.ist_geojson[self.ist_geojson['Obj_Parent'].isnull()]
                self.ist_geojson = self.ist_geojson.drop_duplicates(subset='ID')
                self.populate_table(self.ist_geojson, self.ist_table)
                QMessageBox.information(self, "Erfolg", f"IST-Stand GeoJSON erfolgreich geladen: {path}")
            except Exception as e:
                tb_str = traceback.format_exception(type(e), e, e.__traceback__)
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der IST-Stand GeoJSON:\n{''.join(tb_str)}")

    def load_saniert_geojson(self):
        """Load renovated state GeoJSON file and populate table."""
        path, _ = QFileDialog.getOpenFileName(self, "Sanierten Stand GeoJSON laden", self.base_path, "GeoJSON-Dateien (*.geojson)")
        if path:
            try:
                self.saniert_geojson = gpd.read_file(path)
                if self.saniert_geojson is None:
                    raise ValueError("Die GeoJSON-Datei konnte nicht geladen werden.")
                
                # Filter parent objects and remove duplicates
                self.saniert_geojson = self.saniert_geojson[self.saniert_geojson['Obj_Parent'].isnull()]
                self.saniert_geojson = self.saniert_geojson.drop_duplicates(subset='ID')
                self.populate_table(self.saniert_geojson, self.saniert_table)
                QMessageBox.information(self, "Erfolg", f"Sanierten Stand GeoJSON erfolgreich geladen: {path}")
            except Exception as e:
                tb_str = traceback.format_exception(type(e), e, e.__traceback__)
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der sanierten Stand GeoJSON:\n{''.join(tb_str)}")

    def populate_table(self, gdf, table_widget):
        """
        Populate table widget with GeoDataFrame data.

        Parameters
        ----------
        gdf : GeoDataFrame
            Source data.
        table_widget : QTableWidget
            Target table widget.
        """
        try:
            properties_list = gdf.drop(columns='geometry').to_dict(orient='records')
            if not properties_list:
                raise ValueError("Die GeoJSON-Datei enthält keine gültigen 'properties'.")
            
            # Filter to relevant fields only
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
        Extract building information from GeoDataFrame.

        Parameters
        ----------
        gdf : GeoDataFrame
            Source GeoDataFrame.

        Returns
        -------
        list
            List of building information dictionaries.
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
        """Run renovation analysis with loaded data and input parameters."""
        try:
            if self.ist_geojson is None or self.saniert_geojson is None:
                QMessageBox.critical(self, "Fehler", "Beide GeoJSON-Dateien müssen geladen werden.")
                return

            ist_buildings = self.extract_building_info(self.ist_geojson)
            saniert_buildings = self.extract_building_info(self.saniert_geojson)

            # Extract input parameters
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

            # Operating and maintenance costs
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

            # Perform analysis for each building pair
            for ist_building, saniert_building in zip(ist_buildings, saniert_buildings):
                ist_heat_demand = ist_building['Wärmebedarf']
                saniert_heat_demand = saniert_building['Wärmebedarf']

                analyse = SanierungsAnalyse(ist_heat_demand, saniert_heat_demand, energy_price_ist, energy_price_saniert, discount_rate, years)
                kosteneinsparung = analyse.berechne_kosteneinsparungen()
                
                # Calculate investment costs
                investitionskosten = {
                    'ground_u': cost_ground * ist_building["ground_area"],
                    'wall_u': cost_wall * ist_building["wall_area"],
                    'roof_u': cost_roof * ist_building["roof_area"],
                    'window_u': cost_window * ist_building["wall_area"] * ist_building["fracture_windows"],
                    'door_u': cost_door * ist_building["wall_area"] * ist_building["fracture_doors"]
                }

                gesamt_investitionskosten = sum(investitionskosten.values())
                effektive_investitionskosten = gesamt_investitionskosten * (1 - foerderquote)

                # Calculate financial metrics
                amortisationszeit = analyse.berechne_amortisationszeit(gesamt_investitionskosten, foerderquote)
                npv = analyse.berechne_npv(gesamt_investitionskosten, foerderquote)
                lcca = analyse.lcca(gesamt_investitionskosten, sum(betriebskosten.values()), sum(instandhaltungskosten.values()), sum(restwert_anteile.values()), foerderquote)
                roi = analyse.berechne_roi(gesamt_investitionskosten, foerderquote)

                # Calculate rent impacts
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
        """Update plot display based on selected analysis parameter."""
        if not self.results:
            return

        selected_plot = self.combo_box.currentText()
        
        if selected_plot in ["Gesamtenergiebedarf in kWh/a", "Kaltmieten in €/m²", "Warmmieten in €/m²"]:
            data_ist = {adresse: values[f"{selected_plot} (IST)"] for adresse, values in self.results.items()}
            data_saniert = {adresse: values[f"{selected_plot} (Saniert)"] for adresse, values in self.results.items()}
            self.canvas.plot(data_ist, data_saniert, f"{selected_plot}", "Adresse", "Wert")
        else:
            data = {adresse: values[selected_plot] for adresse, values in self.results.items()}
            self.canvas.plot(data, {}, selected_plot, "Adresse", "Wert")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QWidget()
    renovation_tab = RenovationTab1()
    main_layout = QVBoxLayout(main_window)
    main_layout.addWidget(renovation_tab)
    main_window.setLayout(main_layout)
    main_window.show()
    sys.exit(app.exec_())