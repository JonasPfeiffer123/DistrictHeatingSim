from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QLineEdit, QListWidget, QDialog, QFileDialog, QMenuBar, QScrollArea, QAction, QAbstractItemView, QMessageBox)
from PyQt5.QtCore import pyqtSignal
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from heat_generators.heat_generator_classes import *
from gui.MixDesignTab.mix_design_dialogs import TechInputDialog

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.parent().updateTechObjectsOrder()

class TechnologyTab(QWidget):
    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.results = {}
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()
        
        # Connect to the data manager signal
        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.project_folder)
        self.loadFileAndPlot()

    def initFileInputs(self):
        self.FilenameInput = QLineEdit('')
        self.selectFileButton = QPushButton('Ergebnis-CSV auswählen')
        self.selectFileButton.clicked.connect(self.on_selectFileButton_clicked)

    def updateDefaultPath(self, new_base_path):
        self.base_path = new_base_path
        new_output_path = f"{self.base_path}/Lastgang/Lastgang.csv"
        self.FilenameInput.setText(new_output_path)
        self.loadFileAndPlot()

    def initUI(self):
        self.createMainScrollArea()
        self.setupFileInputs()
        self.setupScaleFactor()
        self.setupTechnologySelection()
        self.setupPlotArea()
        self.setLayout(self.createMainLayout())

    def createMainScrollArea(self):
        self.mainScrollArea = QScrollArea(self)
        self.mainScrollArea.setWidgetResizable(True)
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.mainScrollArea.setWidget(self.mainWidget)

    def setupFileInputs(self):
        self.addLabel('Eingabe csv-Datei berechneter Lastgang Wärmenetz')
        self.addFileInputLayout(self.FilenameInput, self.selectFileButton)
        self.FilenameInput.textChanged.connect(self.loadFileAndPlot)

    def addLabel(self, text):
        label = QLabel(text)
        self.mainLayout.addWidget(label)

    def addFileInputLayout(self, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        self.mainLayout.addLayout(layout)

    def on_selectFileButton_clicked(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            self.FilenameInput.setText(filename)

    def setupScaleFactor(self):
        self.load_scale_factorLabel = QLabel('Lastgang skalieren?:')
        self.load_scale_factorInput = QLineEdit("1")
        self.addHorizontalLayout(self.load_scale_factorLabel, self.load_scale_factorInput)
        self.load_scale_factorInput.textChanged.connect(self.loadFileAndPlot)

    def addHorizontalLayout(self, *widgets):
        layout = QHBoxLayout()
        for widget in widgets:
            layout.addWidget(widget)
        self.mainLayout.addLayout(layout)

    def setupTechnologySelection(self):
        self.addLabel('Definierte Wärmeerzeuger')
        self.techList = CustomListWidget(self)
        self.techList.setDragDropMode(QAbstractItemView.InternalMove)
        self.techList.itemDoubleClicked.connect(self.editTech)
        self.mainLayout.addWidget(self.techList)
        self.addButtonLayout()

    def addButtonLayout(self):
        buttonLayout = QHBoxLayout()
        self.btnDeleteSelectedTech = QPushButton("Ausgewählte Technologie entfernen")
        self.btnRemoveTech = QPushButton("Alle Technologien entfernen")
        buttonLayout.addWidget(self.btnDeleteSelectedTech)
        buttonLayout.addWidget(self.btnRemoveTech)
        self.mainLayout.addLayout(buttonLayout)
        self.btnDeleteSelectedTech.clicked.connect(self.removeSelectedTech)
        self.btnRemoveTech.clicked.connect(self.removeTech)

    def createTechnology(self, tech_type, inputs):
        tech_classes = {
            "Solarthermie": SolarThermal,
            "BHKW": CHP,
            "Holzgas-BHKW": CHP,
            "Geothermie": Geothermal,
            "Abwärme": WasteHeatPump,
            "Flusswasser": RiverHeatPump,
            "Biomassekessel": BiomassBoiler,
            "Gaskessel": GasBoiler
        }
        tech_class = tech_classes.get(tech_type)
        if not tech_class:
            raise ValueError(f"Unbekannter Technologietyp: {tech_type}")
        return tech_class(name=tech_type, **inputs)
        
    def addTech(self, tech_type, tech_data):
        dialog = TechInputDialog(tech_type, tech_data)
        if dialog.exec_() == QDialog.Accepted:
            new_tech = self.createTechnology(tech_type, dialog.getInputs())
            self.tech_objects.append(new_tech)
            self.updateTechList()

    def editTech(self, item):
        selected_tech_index = self.techList.row(item)
        selected_tech = self.tech_objects[selected_tech_index]
        tech_data = {k: v for k, v in selected_tech.__dict__.items() if not k.startswith('_')}
        
        dialog = TechInputDialog(selected_tech.name, tech_data)
        if dialog.exec_() == QDialog.Accepted:
            updated_inputs = dialog.getInputs()
            self.tech_objects[selected_tech_index] = self.createTechnology(selected_tech.name, updated_inputs)
            self.updateTechList()

    def removeSelectedTech(self):
        selected_row = self.techList.currentRow()
        if selected_row != -1:
            self.techList.takeItem(selected_row)
            del self.tech_objects[selected_row]
            self.updateTechList()

    def removeTech(self):
        self.techList.clear()
        self.tech_objects = []

    def updateTechList(self):
        self.techList.clear()
        for tech in self.tech_objects:
            self.techList.addItem(self.formatTechForDisplay(tech))

    def updateTechObjectsOrder(self):
        new_order = []
        for index in range(self.techList.count()):
            item_text = self.techList.item(index).text()
            for tech in self.tech_objects:
                if self.formatTechForDisplay(tech) == item_text:
                    new_order.append(tech)
                    break
        self.tech_objects = new_order

    def formatTechForDisplay(self, tech):
        display_text = f"{tech.name}: "
        if isinstance(tech, RiverHeatPump):
            display_text += f"Wärmeleistung FW WP: {tech.Wärmeleistung_FW_WP} kW, Temperatur FW WP: {tech.Temperatur_FW_WP} °C, dT: {tech.dT} K, spez. Investitionskosten Flusswärme: {tech.spez_Investitionskosten_Flusswasser} €/kW, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, WasteHeatPump):
            display_text += f"Kühlleistung Abwärme: {tech.Kühlleistung_Abwärme} kW, Temperatur Abwärme: {tech.Temperatur_Abwärme} °C, spez. Investitionskosten Abwärme: {tech.spez_Investitionskosten_Abwärme} €/kW, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, Geothermal):
            display_text += f"Fläche Sondenfeld: {tech.Fläche} m², Bohrtiefe: {tech.Bohrtiefe} m, Quelltemperatur Erdreich: {tech.Temperatur_Geothermie} °C, spez. Bohrkosten: {tech.spez_Bohrkosten} €/m, spez. Entzugsleistung: {tech.spez_Entzugsleistung} W/m, Vollbenutzungsstunden: {tech.Vollbenutzungsstunden} h, Abstand Sonden: {tech.Abstand_Sonden} m, spez. Investitionskosten Wärmepumpe: {tech.spezifische_Investitionskosten_WP} €/kW"
        elif isinstance(tech, CHP):
            display_text += f"th. Leistung: {tech.th_Leistung_BHKW} kW, spez. Investitionskosten Erdgas-BHKW: {tech.spez_Investitionskosten_GBHKW} €/BHKW, spez. Investitionskosten Holzgas-BHKW: {tech.spez_Investitionskosten_HBHKW} €/kW"
        elif isinstance(tech, BiomassBoiler):
            display_text += f"th. Leistung: {tech.P_BMK}, Größe Holzlager: {tech.Größe_Holzlager} t, spez. Investitionskosten Kessel: {tech.spez_Investitionskosten} €/kW, spez. Investitionskosten Holzlager: {tech.spez_Investitionskosten_Holzlager} €/t"
        elif isinstance(tech, GasBoiler):
            display_text += f"spez. Investitionskosten: {tech.spez_Investitionskosten} €/kW"
        elif isinstance(tech, SolarThermal):
            display_text += f"Bruttokollektorfläche: {tech.bruttofläche_STA} m², Volumen Solarspeicher: {tech.vs} m³, Kollektortyp: {tech.Typ}, spez. Kosten Speicher: {tech.kosten_speicher_spez} €/m³, spez. Kosten Flachkollektor: {tech.kosten_fk_spez} €/m², spez. Kosten Röhrenkollektor: {tech.kosten_vrk_spez} €/m²"
        else:
            display_text = f"Unbekannte Technologieklasse: {type(tech).__name__}"
        
        return display_text

    def createMainLayout(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.mainScrollArea)
        return layout

    def setupPlotArea(self):
        self.plotLayout = QVBoxLayout()
        self.plotCanvas = None
        self.createPlotCanvas()
        self.mainLayout.addLayout(self.plotLayout)

    def createPlotCanvas(self):
        if self.plotCanvas:
            self.plotLayout.removeWidget(self.plotCanvas)
            self.plotCanvas.deleteLater()
        self.plotFigure = plt.figure()
        self.plotCanvas = FigureCanvas(self.plotFigure)
        self.plotLayout.addWidget(self.plotCanvas)

    def loadFileAndPlot(self):
        filename = self.FilenameInput.text()
        if filename:
            try:
                data = pd.read_csv(filename, sep=";")
                self.plotData(data)
            except Exception as e:
                self.showErrorMessage(f"Fehler beim Laden der Datei: {e}")

    def plotData(self, data):
        try:
            scale_factor = float(self.load_scale_factorInput.text())
        except ValueError:
            self.showErrorMessage("Ungültiger Skalierungsfaktor.")
            return

        self.createPlotCanvas()
        ax = self.plotFigure.add_subplot(111)
        if 'Zeit' in data.columns and 'Wärmeerzeugung_Heizentrale Haupteinspeisung_1_kW' in data.columns:
            ax.plot(pd.to_datetime(data['Zeit']), data['Wärmeerzeugung_Heizentrale Haupteinspeisung_1_kW'] * scale_factor, label='Gesamtwärmebedarf')
            ax.set_title("Jahresgang Wärmebedarf")
            ax.set_xlabel("Zeit")
            ax.set_ylabel("Wärmebedarf (kW)")
            ax.legend()
            self.plotCanvas.draw()
        else:
            self.showErrorMessage("Die Datei enthält nicht die erforderlichen Spalten 'Zeit' und 'Wärmeerzeugung_Heizentrale Haupteinspeisung_1_kW'.")

    def showErrorMessage(self, message):
        QMessageBox.critical(self, "Fehler", message)
