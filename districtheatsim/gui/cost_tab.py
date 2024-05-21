from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

from heat_generators.heat_generator_classes import *

class CostTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        self.tech_objects = []
        self.initUI()

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path

    def initUI(self):
        mainScrollArea = QScrollArea(self)
        mainScrollArea.setWidgetResizable(True)

        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)

        self.mainLayout = mainLayout
        self.setupInfrastructureCostsTable(mainLayout)
        self.setupCalculationOptimization()

        mainScrollArea.setWidget(mainWidget)

        tabLayout = QVBoxLayout(self)
        tabLayout.addWidget(mainScrollArea)  # Scrollbereich darunter hinzufügen
        self.setLayout(tabLayout)

    def addLabel(self, layout, text):
        label = QLabel(text)
        layout.addWidget(label)
    
    ### Infrastrukturtabellen ###
    def setupInfrastructureCostsTable(self, mainLayout):
        self.addLabel(mainLayout, 'Wärmenetzinfrastruktur')
        self.infrastructure_costs = self.parent.netInfrastructureDialog.getValues()
        self.infrastructureCostsTable = QTableWidget()
        self.infrastructureCostsTable.setColumnCount(7)  # Eine zusätzliche Spalte für Annuität
        self.infrastructureCostsTable.setHorizontalHeaderLabels(['Beschreibung', 'Kosten', 'Technische Nutzungsdauer', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Annuität'])
        mainLayout.addWidget(self.infrastructureCostsTable)
        self.updateInfrastructureTable(self.infrastructure_costs)  # Tabelle mit Standardwerten füllen

    def updateInfrastructureTable(self, values):
        # Hole die aktuellen Infrastruktur-Objekte aus dem Dialog
        infraObjects = self.parent.netInfrastructureDialog.getCurrentInfraObjects()
        columns = ['Beschreibung', 'Kosten', 'Technische Nutzungsdauer', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Gesamtannuität']

        self.infrastructureCostsTable.setRowCount(len(infraObjects))
        self.infrastructureCostsTable.setColumnCount(len(columns))  # Hier 7 Spalten setzen
        self.infrastructureCostsTable.setHorizontalHeaderLabels(columns)

        # Summen initialisieren
        self.summe_investitionskosten = 0
        self.summe_annuität = 0

        for i, obj in enumerate(infraObjects):
            self.infrastructureCostsTable.setItem(i, 0, QTableWidgetItem(obj.capitalize()))
            for j, col in enumerate(columns[1:], 1):
                key = f"{obj}_{col.lower()}"
                value = values.get(key, "")
                self.infrastructureCostsTable.setItem(i, j, QTableWidgetItem(str(value)))

            # Annuität berechnen und hinzufügen
            A0 = float(values.get(f"{obj}_kosten", 0))
            TN = int(values.get(f"{obj}_technische nutzungsdauer", 0))
            f_Inst = float(values.get(f"{obj}_f_inst", 0))
            f_W_Insp = float(values.get(f"{obj}_f_w_insp", 0))
            Bedienaufwand = float(values.get(f"{obj}_bedienaufwand", 0))
            annuität = self.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)
            self.infrastructureCostsTable.setItem(i, 6, QTableWidgetItem("{:.1f}".format(annuität)))
            # Summen berechnen
            self.summe_investitionskosten += float(values.get(f"{obj}_kosten", 0))
            self.summe_annuität += annuität

        # Neue Zeile für Summen hinzufügen
        summen_row_index = self.infrastructureCostsTable.rowCount()
        self.infrastructureCostsTable.insertRow(summen_row_index)

        # Fettgedruckten Font erstellen
        boldFont = QFont()
        boldFont.setBold(True)

        # Summenzellen hinzufügen und formatieren
        summen_beschreibung_item = QTableWidgetItem("Summe Infrastruktur")
        summen_beschreibung_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 0, summen_beschreibung_item)

        # Formatieren der Zahlen auf eine Dezimalstelle
        summen_kosten_item = QTableWidgetItem("{:.0f}".format(self.summe_investitionskosten))
        summen_kosten_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 1, summen_kosten_item)

        summen_annuität_item = QTableWidgetItem("{:.0f}".format(self.summe_annuität))
        summen_annuität_item.setFont(boldFont)
        self.infrastructureCostsTable.setItem(summen_row_index, 6, summen_annuität_item)

        self.infrastructureCostsTable.resizeColumnsToContents()
        self.adjustTableSize(self.infrastructureCostsTable)

    def calc_annuität(self, A0, TN, f_Inst, f_W_Insp, Bedienaufwand):
        q = 1 + (self.parent.kapitalzins / 100)
        r = 1 + (self.parent.preissteigerungsrate / 100)
        t = int(self.parent.betrachtungszeitraum)

        a = annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand, q=q, r=r, T=t)
        return a
    
    ### Setup der Berechnungsergebnistabellen ###
    def setupCalculationOptimization(self):
        self.resultLabel = QLabel('Kosten Erzeuger')
        self.mainLayout.addWidget(self.resultLabel)
        self.setupTechDataTable()

    ### Tech Data Table ###
    def setupTechDataTable(self):
        self.techDataTable = QTableWidget()
        self.techDataTable.setColumnCount(4)  # Anpassen an die Anzahl der benötigten Spalten
        self.techDataTable.setHorizontalHeaderLabels(['Name', 'Dimensionen', 'Kosten', 'Gesamtkosten'])
        self.mainLayout.addWidget(self.techDataTable)

    def updateTechDataTable(self, tech_objects):
        self.techDataTable.setRowCount(len(tech_objects))

        for i, tech in enumerate(tech_objects):
            name, dimensions, costs, full_costs = self.extractTechData(tech)
            self.techDataTable.setItem(i, 0, QTableWidgetItem(name))
            self.techDataTable.setItem(i, 1, QTableWidgetItem(dimensions))
            self.techDataTable.setItem(i, 2, QTableWidgetItem(costs))
            self.techDataTable.setItem(i, 3, QTableWidgetItem(full_costs))

        self.techDataTable.resizeColumnsToContents()
        self.adjustTableSize(self.techDataTable)

    ### Extraktion Ergebnisse Berechnung ###
    def extractTechData(self, tech):
        if isinstance(tech, RiverHeatPump):
            dimensions = f"th. Leistung: {tech.Wärmeleistung_FW_WP} kW"
            costs = f"Investitionskosten Flusswärmenutzung: {tech.spez_Investitionskosten_Flusswasser*tech.Wärmeleistung_FW_WP:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP*tech.Wärmeleistung_FW_WP:.1f}"
            full_costs = f"{tech.spez_Investitionskosten_Flusswasser*tech.Wärmeleistung_FW_WP + tech.spezifische_Investitionskosten_WP*tech.Wärmeleistung_FW_WP:.1f}"

        elif isinstance(tech, WasteHeatPump):
            dimensions = f"Kühlleistung Abwärme: {tech.Kühlleistung_Abwärme} kW, Temperatur Abwärme: {tech.Temperatur_Abwärme} °C, th. Leistung: {tech.max_Wärmeleistung} kW"
            costs = f"Investitionskosten Abwärmenutzung: {tech.spez_Investitionskosten_Abwärme*tech.max_Wärmeleistung:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"
            full_costs = f"{tech.spez_Investitionskosten_Abwärme*tech.max_Wärmeleistung + tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"

        elif isinstance(tech, Geothermal):
            dimensions = f"Fläche: {tech.Fläche} m², Bohrtiefe: {tech.Bohrtiefe} m, Temperatur Geothermie: {tech.Temperatur_Geothermie} °C, Entzugsleistung: {tech.spez_Entzugsleistung} W/m, th. Leistung: {tech.max_Wärmeleistung} kW"
            costs = f"Investitionskosten Sondenfeld: {tech.Investitionskosten_Sonden:.1f}, Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"
            full_costs = f"{tech.Investitionskosten_Sonden + tech.spezifische_Investitionskosten_WP*tech.max_Wärmeleistung:.1f}"

        elif isinstance(tech, CHP):
            dimensions = f"th. Leistung: {tech.th_Leistung_BHKW} kW, el. Leistung: {tech.el_Leistung_Soll} kW"
            costs = f"Investitionskosten: {tech.Investitionskosten:.1f}"
            full_costs = f"{tech.Investitionskosten:.1f}"

        elif isinstance(tech, BiomassBoiler):
            dimensions = f"th. Leistung: {tech.P_BMK} kW, Größe Holzlager: {tech.Größe_Holzlager} t"
            costs = f"Investitionskosten Kessel: {tech.Investitionskosten_Kessel:.1f} €, Investitionskosten Holzlager: {tech.Investitionskosten_Holzlager:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"

        elif isinstance(tech, GasBoiler):
            dimensions = f"th. Leistung: {tech.P_max:.1f} kW"
            costs = f"Investitionskosten: {tech.Investitionskosten:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"
            
        elif isinstance(tech, SolarThermal):
            dimensions = f"Bruttokollekttorfläche: {tech.bruttofläche_STA} m², Speichervolumen: {tech.vs} m³; Kollektortyp: {tech.Typ}"
            costs = f"Investitionskosten Speicher: {tech.Investitionskosten_Speicher:.1f} €, Investitionskosten STA: {tech.Investitionskosten_STA:.1f} €"
            full_costs = f"{tech.Investitionskosten:.1f}"

        else:
            dimensions = "N/A"
            costs = "N/A"
            full_costs = "N/A"

        return tech.name, dimensions, costs, full_costs
    
    ### Table size adjustment function ###
    def adjustTableSize(self, table):
        # header row height
        header_height = table.horizontalHeader().height()
        # hight of all rows
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        # configuring table height
        table.setFixedHeight(header_height + rows_height)