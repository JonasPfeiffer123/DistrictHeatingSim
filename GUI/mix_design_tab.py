import numpy as np
import itertools
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QComboBox, 
    QLineEdit, QListWidget, QDialog, QProgressBar, QMessageBox, QFileDialog, QScrollArea, QAbstractItemView
)
from PyQt5.QtCore import Qt
from gui.dialogs import TechInputDialog
from heat_generators.heat_generator_classes_v2 import *
from gui.checkable_combobox import CheckableComboBox

from gui.threads import CalculateMixThread

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import matplotlib.pyplot as plt

from io import BytesIO


class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.parent().updateTechObjectsOrder()

class MixDesignTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tech_objects = []
        self.initFileInputs()
        self.initUI()

    def initFileInputs(self):
        self.FilenameInput = QLineEdit('results/results_time_series_net.csv')
        self.tryFilenameInput = QLineEdit('heat_requirement/TRY_511676144222/TRY2015_511676144222_Jahr.dat')
        self.copFilenameInput = QLineEdit('heat_generators/Kennlinien WP.csv')

        self.selectFileButton = QPushButton('Ergebnis-CSV auswählen')
        self.selectTRYFileButton = QPushButton('TRY-Datei auswählen')
        self.selectCOPFileButton = QPushButton('COP-Datei auswählen')

        self.selectFileButton.clicked.connect(lambda: self.selectFilename(self.FilenameInput))
        self.selectTRYFileButton.clicked.connect(lambda: self.selectFilename(self.tryFilenameInput))
        self.selectCOPFileButton.clicked.connect(lambda: self.selectFilename(self.copFilenameInput))

    def initUI(self):
        mainScrollArea, mainWidget, mainLayout = self.setupMainScrollArea()

        self.mainLayout = mainLayout
        self.setupFileInputs(mainLayout)
        self.setupEconomicParameters(mainLayout)
        self.setupTechnologySelection(mainLayout)
        self.setupScaleFactor(mainLayout)
        self.setupCalculationOptimization(mainLayout)
        self.setupDiagrams(mainLayout)

        self.progressBar = QProgressBar(self)
        mainLayout.addWidget(self.progressBar)

        mainScrollArea.setWidget(mainWidget)
        self.setLayoutWithScrollArea(mainScrollArea)

    def setupMainScrollArea(self):
        mainScrollArea = QScrollArea(self)
        mainScrollArea.setWidgetResizable(True)

        mainWidget = QWidget()
        mainLayout = QVBoxLayout(mainWidget)

        return mainScrollArea, mainWidget, mainLayout

    def setupFileInputs(self, mainLayout):
        self.addLabel(mainLayout, 'Dateneingaben')
        self.addFileInputLayout(mainLayout, self.FilenameInput, self.selectFileButton)
        self.addFileInputLayout(mainLayout, self.tryFilenameInput, self.selectTRYFileButton)
        self.addFileInputLayout(mainLayout, self.copFilenameInput, self.selectCOPFileButton)

    def setupEconomicParameters(self, mainLayout):
        self.addLabel(mainLayout, 'Wirtschaftliche Vorgaben')
        self.setupParameterInputs(mainLayout)

    def setupParameterInputs(self, mainLayout):
        self.gaspreisInput = QLineEdit("70")
        self.strompreisInput = QLineEdit("150")
        self.holzpreisInput = QLineEdit("50")
        self.BEWComboBox = QComboBox()
        self.BEWComboBox.addItems(["Nein", "Ja"])

        inputLayout = QHBoxLayout()
        self.addParameterToLayout(inputLayout, 'Gaspreis (€/MWh):', self.gaspreisInput)
        self.addParameterToLayout(inputLayout, 'Strompreis (€/MWh):', self.strompreisInput)
        self.addParameterToLayout(inputLayout, 'Holzpreis (€/MWh):', self.holzpreisInput)
        self.addParameterToLayout(inputLayout, 'Berücksichtigung BEW-Förderung?:', self.BEWComboBox)

        mainLayout.addLayout(inputLayout)

    def setupTechnologySelection(self, mainLayout):
        self.addLabel(mainLayout, 'Auswahl Erzeugungstechnologien')
        self.setupTechnologyComboBox(mainLayout)
        self.setupTechnologyList(mainLayout)

    def setupTechnologyComboBox(self, mainLayout):
        self.techComboBox = QComboBox()
        self.techComboBox.addItems(["Solarthermie", "BHKW", "Holzgas-BHKW", "Geothermie", "Abwärme", "Flusswasser", "Biomassekessel", "Gaskessel"])
        mainLayout.addWidget(self.techComboBox)

        buttonLayout = QHBoxLayout()
        self.btnAddTech = QPushButton("Technologie hinzufügen")
        self.btnRemoveTech = QPushButton("Alle Technologien entfernen")
        buttonLayout.addWidget(self.btnAddTech)
        buttonLayout.addWidget(self.btnRemoveTech)
        mainLayout.addLayout(buttonLayout)

        self.btnAddTech.clicked.connect(self.addTech)
        self.btnRemoveTech.clicked.connect(self.removeTech)

    def setupTechnologyList(self, mainLayout):
        self.techList = QListWidget()
        self.techList.setDragDropMode(QAbstractItemView.InternalMove)
        self.techList.itemDoubleClicked.connect(self.editTech)
        mainLayout.addWidget(self.techList)

    def setupScaleFactor(self, mainLayout):
        # Hinzufügen der Eingabe für den Lastgang-Skalierungsfaktor
        self.load_scale_factorLabel = QLabel('Lastgang skalieren?:')
        self.load_scale_factorInput = QLineEdit("1")  # Standardwert ist "1"

        # Hinzufügen zum Layout
        loadScaleFactorLayout = QHBoxLayout()
        loadScaleFactorLayout.addWidget(self.load_scale_factorLabel)
        loadScaleFactorLayout.addWidget(self.load_scale_factorInput)
        mainLayout.addLayout(loadScaleFactorLayout)

    def setupCalculationOptimization(self, mainLayout):
        self.addLabel(mainLayout, 'Berechnung und Optimierung')
        self.setupCalculationButtons(mainLayout)
        self.resultLabel = QLabel('Ergebnisse werden hier angezeigt')
        mainLayout.addWidget(self.resultLabel)

    def setupCalculationButtons(self, mainLayout):
        self.calculateButton = QPushButton('Berechnen')
        self.optimizeButton = QPushButton('Optimieren')

        self.calculateButton.clicked.connect(self.start_calculation)
        self.optimizeButton.clicked.connect(self.optimize)

        mainLayout.addWidget(self.calculateButton)
        mainLayout.addWidget(self.optimizeButton)

    def createPlotControlDropdown(self):
        self.dropdownLayout = QHBoxLayout()
        self.dataSelectionDropdown = CheckableComboBox(self)

        # Hier wird angenommen, dass die erste Reihe von Daten standardmäßig geplottet wird.
        initial_checked = True

        # Füllen des Dropdown-Menüs mit Optionen und Setzen des Checkbox-Zustands
        for label in self.results.keys():
            if label.endswith('_L'):
                self.dataSelectionDropdown.addItem(label)
                item = self.dataSelectionDropdown.model().item(self.dataSelectionDropdown.count() - 1, 0)
                item.setCheckState(Qt.Checked if initial_checked else Qt.Unchecked)
                initial_checked = False  # Nur das erste Element wird standardmäßig ausgewählt

        self.dropdownLayout.addWidget(self.dataSelectionDropdown)
        self.mainLayout.addLayout(self.dropdownLayout)

        # Verbindung des Dropdown-Menüs mit der Aktualisierungsfunktion
        self.dataSelectionDropdown.checkedStateChanged.connect(self.updatePlot)

    def setupDiagrams(self, mainLayout):
        diagramScrollArea, diagramWidget, diagramLayout = self.setupDiagramScrollArea()
        self.setupFigures(diagramLayout)
        diagramScrollArea.setWidget(diagramWidget)
        mainLayout.addWidget(diagramScrollArea)

    def setupDiagramScrollArea(self):
        diagramScrollArea = QScrollArea()
        diagramScrollArea.setWidgetResizable(True)
        diagramScrollArea.setMinimumSize(800, 1200)

        diagramWidget = QWidget()
        diagramLayout = QVBoxLayout(diagramWidget)

        return diagramScrollArea, diagramWidget, diagramLayout

    def setupFigures(self, diagramLayout):
        self.figure1, self.canvas1 = self.addFigure(diagramLayout)
        self.figure2, self.canvas2 = self.addFigure(diagramLayout)

    def addFigure(self, layout):
        figure = Figure()
        canvas = FigureCanvas(figure)
        canvas.setMinimumSize(800, 600)
        layout.addWidget(canvas)
        return figure, canvas

    def setLayoutWithScrollArea(self, mainScrollArea):
        tabLayout = QVBoxLayout(self)
        tabLayout.addWidget(mainScrollArea)
        self.setLayout(tabLayout)

    def addLabel(self, layout, text):
        label = QLabel(text)
        layout.addWidget(label)

    def addFileInputLayout(self, mainLayout, lineEdit, button):
        layout = QHBoxLayout()
        layout.addWidget(lineEdit)
        layout.addWidget(button)
        mainLayout.addLayout(layout)

    def addParameterToLayout(self, layout, labelText, inputWidget):
        label = QLabel(labelText)
        layout.addWidget(label)
        layout.addWidget(inputWidget)

    def selectFilename(self, lineEdit):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei auswählen")
        if filename:
            lineEdit.setText(filename)

    def optimize(self):
        self.start_calculation(True)

    def start_calculation(self, optimize=False):
        self.updateTechObjectsOrder()

        filename = self.FilenameInput.text()
        load_scale_factor = float(self.load_scale_factorInput.text())
        try_filename = self.tryFilenameInput.text()
        cop_filename = self.copFilenameInput.text()
        gaspreis = float(self.gaspreisInput.text())
        strompreis = float(self.strompreisInput.text())
        holzpreis = float(self.holzpreisInput.text())
        BEW = self.BEWComboBox.itemText(self.BEWComboBox.currentIndex())
        tech_objects = self.tech_objects

        self.calculationThread = CalculateMixThread(
            filename, load_scale_factor, try_filename, cop_filename,
            gaspreis, strompreis, holzpreis, BEW, tech_objects, optimize
        )
        self.calculationThread.calculation_done.connect(self.on_calculation_done)
        self.calculationThread.calculation_error.connect(self.on_calculation_error)
        self.calculationThread.start()
        self.progressBar.setRange(0, 0)

    def on_calculation_done(self, result):
        self.progressBar.setRange(0, 1)
        self.showResults(result)
        self.plotResults(result)

    def on_calculation_error(self, error_message):
        self.progressBar.setRange(0, 1)
        QMessageBox.critical(self, "Berechnungsfehler", error_message)

    def showResults(self, results):
        resultText = f"Jahreswärmebedarf: {results['Jahreswärmebedarf']:.2f} MWh\n"
        resultText += f"Wärmegestehungskosten Gesamt: {results['WGK_Gesamt']:.2f} €/MWh\n\n"
        for tech, wärmemenge, anteil, wgk in zip(results['techs'], results['Wärmemengen'], results['Anteile'], results['WGK']):
            resultText += f"{tech}: {wärmemenge:.2f} MWh, {wgk:.2f} €/MWh, Anteil: {anteil*100:.2f}%\n"
        self.resultLabel.setText(resultText)

    def addTech(self):
        tech_type = self.techComboBox.currentText()
        dialog = TechInputDialog(tech_type)
        if dialog.exec_() == QDialog.Accepted:
            new_tech = self.createTechnology(tech_type, dialog.getInputs())
            self.tech_objects.append(new_tech)
            self.updateTechList()

    def updateTechList(self):
        self.techList.clear()
        for tech in self.tech_objects:
            self.techList.addItem(self.formatTechForDisplay(tech))

    def formatTechForDisplay(self, tech):
        # Formatieren Sie die Ausgabe basierend auf den Eigenschaften der Technologie
        display_text = f"{tech.name}"
        for key, value in tech.__dict__.items():
            if key != 'name':
                display_text += f", {key}: {value}"
        return display_text

    def editTech(self, item):
        selected_tech_index = self.techList.row(item)
        selected_tech = self.tech_objects[selected_tech_index]
        tech_data = {k: v for k, v in selected_tech.__dict__.items() if not k.startswith('_')}
        
        dialog = TechInputDialog(selected_tech.name, tech_data)

        if dialog.exec_() == QDialog.Accepted:
            updated_inputs = dialog.getInputs()
            self.tech_objects[selected_tech_index] = self.createTechnology(selected_tech.name, updated_inputs)
            self.updateTechList()

    def updateTechObjectsOrder(self):
        new_order = []
        for index in range(self.techList.count()):
            item_text = self.techList.item(index).text()
            # Finden Sie das entsprechende Tech-Objekt basierend auf dem Text
            for tech in self.tech_objects:
                if self.formatTechForDisplay(tech) == item_text:
                    new_order.append(tech)
                    break
        self.tech_objects = new_order

    def createTechnology(self, tech_type, inputs):
        if tech_type == "Solarthermie":
            return SolarThermal(name=tech_type, bruttofläche_STA=inputs["bruttofläche_STA"], vs=inputs["vs"], Typ=inputs["Typ"])
        elif tech_type == "Biomassekessel":
            return BiomassBoiler(name=tech_type, P_BMK=inputs["P_BMK"])
        elif tech_type == "Gaskessel":
            return GasBoiler(name=tech_type)  # Angenommen, GasBoiler benötigt keine zusätzlichen Eingaben
        elif tech_type == "BHKW":
            return CHP(name=tech_type, th_Leistung_BHKW=inputs["th_Leistung_BHKW"])
        elif tech_type == "Holzgas-BHKW":
            return CHP(name=tech_type, th_Leistung_BHKW=inputs["th_Leistung_BHKW"])  # Angenommen, Holzgas-BHKW verwendet dieselbe Klasse wie BHKW
        elif tech_type == "Geothermie":
            return Geothermal(name=tech_type, Fläche=inputs["Fläche"], Bohrtiefe=inputs["Bohrtiefe"], Temperatur_Geothermie=inputs["Temperatur_Geothermie"])
        elif tech_type == "Abwärme":
            return WasteHeatPump(name=tech_type, Kühlleistung_Abwärme=inputs["Kühlleistung_Abwärme"], Temperatur_Abwärme=inputs["Temperatur_Abwärme"])
        elif tech_type == "Flusswasser":
            return RiverHeatPump(name=tech_type, Wärmeleistung_FW_WP=inputs["Wärmeleistung_FW_WP"], Temperatur_FW_WP=inputs["Temperatur_FW_WP"], dT=inputs["dT"])
        else:
            raise ValueError(f"Unbekannter Technologietyp: {tech_type}")


    def removeTech(self):
        self.techList.clear()
        self.tech_objects = []

    def plotResults(self, results):
        self.results = results
        if not hasattr(self, 'dataSelectionDropdown'):
            self.createPlotControlDropdown()

        self.exportPDFButton = QPushButton('Export to PDF')
        self.exportPDFButton.clicked.connect(self.on_export_pdf_clicked)
        self.mainLayout.addWidget(self.exportPDFButton)

        self.figure1.clear()
        self.figure2.clear()

        self.plotStackPlot(self.figure1, results['time_steps'], results['Wärmeleistung_L'], results['techs'], results['Last_L'])
        self.plotPieChart(self.figure2, results['Anteile'], results['techs'])
        self.canvas1.draw()
        self.canvas2.draw()

    def plotStackPlot(self, figure, t, data, labels, Last):
        ax = figure.add_subplot(111)
        ax.stackplot(t, data, labels=labels)
        ax.set_title("Jahresdauerlinie")
        ax.set_xlabel("Jahresstunden")
        ax.set_ylabel("thermische Leistung in kW")
        ax.legend(loc='upper center')
        ax.grid()

    def plotPieChart(self, figure, Anteile, labels):
        ax = figure.add_subplot(111)
        ax.pie(Anteile, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title("Anteile Wärmeerzeugung")
        ax.legend(loc='lower left')
        ax.axis("equal")

    def updatePlot(self):
        self.figure1.clear()
        ax = self.figure1.add_subplot(111)
        color_cycle = itertools.cycle(['b', 'g', 'r', 'c', 'm', 'y', 'k'])

        # Gehen Sie alle Optionen im Dropdown-Menü durch und zeichnen Sie nur die ausgewählten
        for i in range(self.dataSelectionDropdown.count()):
            if self.dataSelectionDropdown.itemChecked(i):
                key = self.dataSelectionDropdown.itemText(i)
                data = self.results[key]
                color = next(color_cycle)
                ax.plot(self.results['time_steps'], data, label=key, color=color)

        ax.set_xlabel("Zeit")
        ax.set_ylabel("Werte")
        ax.legend(loc='upper left')
        ax.grid()
        self.canvas1.draw()

    def create_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Eingaben als Text hinzufügen
        for tech in self.tech_objects:
            story.append(Paragraph(self.formatTechForDisplay(tech), styles['Normal']))
            story.append(Spacer(1, 12))

        # Textausgaben hinzufügen
        story.append(Paragraph(self.resultLabel.text(), styles['Normal']))
        story.append(Spacer(1, 12))

        # Diagramme als Bilder hinzufügen
        for figure in [self.figure1, self.figure2]:
            img_buffer = BytesIO()  # Verwenden eines BytesIO-Objekts anstatt einer temporären Datei
            figure.savefig(img_buffer, format='png')
            img_buffer.seek(0)  # Zurück zum Anfang des Streams
            img = Image(img_buffer)
            img.drawHeight = 6 * inch  # oder eine andere Größe
            img.drawWidth = 8 * inch
            story.append(img)
            story.append(Spacer(1, 12))
        
        # PDF-Dokument erstellen
        doc.build(story)

    def on_export_pdf_clicked(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'PDF speichern als...', filter='PDF Files (*.pdf)')
        if filename:
            self.create_pdf(filename)