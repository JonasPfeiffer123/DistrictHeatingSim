"""
Technology Input Dialogs Module
================================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Dialogs for inputting technology-specific data in Energy System Tab.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QDialog, QComboBox, QCheckBox, QGroupBox, \
    QDialogButtonBox, QHBoxLayout, QFormLayout, QPushButton, QFileDialog, QMessageBox, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import art3d
from matplotlib.figure import Figure

class TechInputDialog(QDialog):
    """
    Dialog for inputting technology-specific data based on technology type.
    """

    def __init__(self, tech_type, tech_data=None):
        """
        Initialize TechInputDialog with technology type and data.

        :param tech_type: Technology type.
        :type tech_type: str
        :param tech_data: Technology data.
        :type tech_data: dict
        """
        super().__init__()

        self.tech_type = tech_type
        self.tech_data = tech_data if tech_data is not None else {}
        self.dialog = None

        self.initUI()

    def initUI(self):
        """
        Initializes the user interface for the dialog.
        """
        layout = QVBoxLayout()
        self.setLayout(layout)

        if self.tech_type.startswith("Solarthermie"):
            self.dialog = SolarThermalDialog(self.tech_data)
        elif self.tech_type.startswith("Biomassekessel"):
            self.dialog = BiomassBoilerDialog(self.tech_data)
        elif self.tech_type.startswith("Gaskessel"):
            self.dialog = GasBoilerDialog(self.tech_data)
        elif self.tech_type.startswith("BHKW"):
            self.dialog = CHPDialog(self.tech_data)
        elif self.tech_type.startswith("Holzgas-BHKW"):
            self.dialog = HolzgasCHPDialog(self.tech_data)
        elif self.tech_type.startswith("Geothermie"):
            self.dialog = GeothermalDialog(self.tech_data)
        elif self.tech_type.startswith("Abwärmepumpe"):
            self.dialog = WasteHeatPumpDialog(self.tech_data)
        elif self.tech_type.startswith("Flusswärmepumpe"):
            self.dialog = RiverHeatPumpDialog(self.tech_data)
        elif self.tech_type.startswith("AqvaHeat"):
            self.dialog = AqvaHeatDialog(self.tech_data)
        elif self.tech_type.startswith("Power-to-Heat"):
            self.dialog = PowerToHeatDialog(self.tech_data)
        elif self.tech_type.startswith("Saisonaler Wärmespeicher"):
            self.dialog = ThermalStorage1DDialog(self.tech_data)
        else:
            raise ValueError(f"Unbekannter Technologietyp: {self.tech_type}")

        if self.dialog:
            layout.addWidget(self.dialog)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setWindowTitle(f"Eingabe für {self.tech_type}")

    def accept(self):
        """
        Accept dialog and retrieve input data from specific technology dialog.
        """
        if self.dialog:
            self.tech_data = self.dialog.getInputs()
        super().accept()

    def getInputs(self):
        """
        Retrieves the input data from the dialog.

        :return: The input data
        :rtype: dict
        """
        return self.tech_data

class SolarThermalDialog(QWidget):
    """
    A dialog for inputting data specific to solar thermal technology.

    Attributes:
        tech_data (dict): The data for the solar thermal technology.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the SolarThermalDialog with the given data.

        :param tech_data: The data for the solar thermal technology
        :type tech_data: dict or None
        """
        super(SolarThermalDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface for the dialog.
        """
        main_layout = QHBoxLayout()  # Main layout as QHBoxLayout
        input_layout = QVBoxLayout()  # Layout for inputs

        # Technical Data GroupBox
        tech_groupbox = QGroupBox("Technische Daten")
        tech_layout = QFormLayout()

        self.areaSInput = QLineEdit(self)
        self.areaSInput.setText(str(self.tech_data.get('bruttofläche_STA', "200")))
        tech_layout.addRow(QLabel("Kollektorbruttofläche in m²"), self.areaSInput)

        self.vsInput = QLineEdit(self)
        self.vsInput.setText(str(self.tech_data.get('vs', "20")))
        tech_layout.addRow(QLabel("Solarspeichervolumen in m³"), self.vsInput)

        self.typeInput = QComboBox(self)
        self.techOptions = ["Vakuumröhrenkollektor", "Flachkollektor"]
        self.typeInput.addItems(self.techOptions)
        if 'Typ' in self.tech_data:
            current_type_index = self.techOptions.index(self.tech_data['Typ'])
            self.typeInput.setCurrentIndex(current_type_index)
        tech_layout.addRow(QLabel("Kollektortyp"), self.typeInput)

        self.TsmaxInput = QLineEdit(self)
        self.TsmaxInput.setText(str(self.tech_data.get('Tsmax', "90")))
        tech_layout.addRow(QLabel("Maximale Speichertemperatur in °C"), self.TsmaxInput)

        self.LongitudeInput = QLineEdit(self)
        self.LongitudeInput.setText(str(self.tech_data.get('Longitude', "-14.4222")))
        tech_layout.addRow(QLabel("Longitude des Erzeugerstandortes"), self.LongitudeInput)

        self.STD_LongitudeInput = QLineEdit(self)
        self.STD_LongitudeInput.setText(str(self.tech_data.get('STD_Longitude', "15")))
        tech_layout.addRow(QLabel("STD_Longitude des Erzeugerstandortes"), self.STD_LongitudeInput)

        self.LatitudeInput = QLineEdit(self)
        self.LatitudeInput.setText(str(self.tech_data.get('Latitude', "51.1676")))
        tech_layout.addRow(QLabel("Latitude des Erzeugerstandortes"), self.LatitudeInput)

        self.East_West_collector_azimuth_angleInput = QLineEdit(self)
        self.East_West_collector_azimuth_angleInput.setText(str(self.tech_data.get('East_West_collector_azimuth_angle', "0")))
        tech_layout.addRow(QLabel("Azimuth-Ausrichtung des Kollektors in °"), self.East_West_collector_azimuth_angleInput)

        self.Collector_tilt_angleInput = QLineEdit(self)
        self.Collector_tilt_angleInput.setText(str(self.tech_data.get('Collector_tilt_angle', "36")))
        tech_layout.addRow(QLabel("Neigungswinkel des Kollektors in ° (0-90)"), self.Collector_tilt_angleInput)

        self.Tm_rlInput = QLineEdit(self)
        self.Tm_rlInput.setText(str(self.tech_data.get('Tm_rl', "60")))
        tech_layout.addRow(QLabel("Startwert Rücklauftemperatur in Speicher in °C"), self.Tm_rlInput)

        self.QsaInput = QLineEdit(self)
        self.QsaInput.setText(str(self.tech_data.get('Qsa', "0")))
        tech_layout.addRow(QLabel("Startwert Speicherfüllstand"), self.QsaInput)

        self.Vorwärmung_KInput = QLineEdit(self)
        self.Vorwärmung_KInput.setText(str(self.tech_data.get('Vorwärmung_K', "8")))
        tech_layout.addRow(QLabel("Mögliche Abweichung von Solltemperatur bei Vorwärmung"), self.Vorwärmung_KInput)

        self.DT_WT_Solar_KInput = QLineEdit(self)
        self.DT_WT_Solar_KInput.setText(str(self.tech_data.get('DT_WT_Solar_K', "5")))
        tech_layout.addRow(QLabel("Grädigkeit Wärmeübertrager Kollektor/Speicher"), self.DT_WT_Solar_KInput)

        self.DT_WT_Netz_KInput = QLineEdit(self)
        self.DT_WT_Netz_KInput.setText(str(self.tech_data.get('DT_WT_Netz_K', "5")))
        tech_layout.addRow(QLabel("Grädigkeit Wärmeübertrager Speicher/Netz"), self.DT_WT_Netz_KInput)

        tech_groupbox.setLayout(tech_layout)
        input_layout.addWidget(tech_groupbox)

        # Cost GroupBox
        cost_groupbox = QGroupBox("Kosten")
        cost_layout = QFormLayout()

        self.vscostInput = QLineEdit(self)
        self.vscostInput.setText(str(self.tech_data.get('kosten_speicher_spez', "750")))
        cost_layout.addRow(QLabel("spez. Kosten Solarspeicher in €/m³"), self.vscostInput)

        self.areaScostfkInput = QLineEdit(self)
        self.areaScostfkInput.setText(str(self.tech_data.get('kosten_fk_spez', "430")))
        cost_layout.addRow(QLabel("spez. Kosten Flachkollektor in €/m²"), self.areaScostfkInput)

        self.areaScostvrkInput = QLineEdit(self)
        self.areaScostvrkInput.setText(str(self.tech_data.get('kosten_vrk_spez', "590")))
        cost_layout.addRow(QLabel("spez. Kosten Vakuumröhrenkollektor in €/m²"), self.areaScostvrkInput)

        cost_groupbox.setLayout(cost_layout)
        input_layout.addWidget(cost_groupbox)

        # Optimization Parameters GroupBox
        opt_groupbox = QGroupBox("Optimierungsparameter")
        opt_layout = QFormLayout()

        self.minVolumeInput = QLineEdit(self)
        self.minVolumeInput.setText(str(self.tech_data.get('opt_volume_min', "1")))
        opt_layout.addRow(QLabel("Untere Grenze Speichervolumen Optimierung"), self.minVolumeInput)

        self.maxVolumeInput = QLineEdit(self)
        self.maxVolumeInput.setText(str(self.tech_data.get('opt_volume_max', "200")))
        opt_layout.addRow(QLabel("Obere Grenze Speichervolumen Optimierung"), self.maxVolumeInput)

        self.minAreaInput = QLineEdit(self)
        self.minAreaInput.setText(str(self.tech_data.get('opt_area_min', "1")))
        opt_layout.addRow(QLabel("Untere Grenze Kollektorfläche Optimierung"), self.minAreaInput)

        self.maxAreaInput = QLineEdit(self)
        self.maxAreaInput.setText(str(self.tech_data.get('opt_area_max', "2000")))
        opt_layout.addRow(QLabel("Obere Grenze Kollektorfläche Optimierung"), self.maxAreaInput)

        opt_groupbox.setLayout(opt_layout)
        input_layout.addWidget(opt_groupbox)

        main_layout.addLayout(input_layout)  # Add input layout to main layout

        # Visualization
        vis_layout = QVBoxLayout()
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.canvas = FigureCanvas(self.figure)
        vis_layout.addWidget(self.canvas)

        main_layout.addLayout(vis_layout)  # Add visualization layout to main layout

        self.setLayout(main_layout)
        self.updateVisualization()

        # Connect input changes to the visualization update
        self.East_West_collector_azimuth_angleInput.textChanged.connect(self.updateVisualization)
        self.Collector_tilt_angleInput.textChanged.connect(self.updateVisualization)

    def updateVisualization(self):
        """
        Updates the visualization of the collector orientation.
        """
        try:
            azimuth = float(self.East_West_collector_azimuth_angleInput.text())
            tilt = float(self.Collector_tilt_angleInput.text())
        except ValueError:
            azimuth = 0
            tilt = 0

        self.ax.clear()

        # Draw the ground plane
        xx, yy = np.meshgrid(range(-180, 181, 45), range(-180, 181, 45))
        zz = np.zeros_like(xx)
        self.ax.plot_surface(xx, yy, zz, color='green', alpha=0.5)

        # Define the corners of the collector plane
        length = 50  # Length of the collector for better visibility
        width = 30   # Width of the collector for better visibility

        # Calculate coordinates of the collector plane
        x1 = length * np.cos(np.radians(azimuth)) * np.cos(np.radians(tilt))
        y1 = length * np.sin(np.radians(azimuth)) * np.cos(np.radians(tilt))
        z1 = length * np.sin(np.radians(tilt))

        collector_corners = np.array([
            [0, 0, 0],
            [x1, y1, z1],
            [x1 - width * np.sin(np.radians(azimuth)), y1 + width * np.cos(np.radians(azimuth)), z1],
            [-width * np.sin(np.radians(azimuth)), width * np.cos(np.radians(azimuth)), 0]
        ])

        # Create the collector plane
        collector_plane = art3d.Poly3DCollection([collector_corners], facecolors='blue', linewidths=1, edgecolors='r', alpha=0.75)
        self.ax.add_collection3d(collector_plane)

        # Draw a vector representing the normal to the collector plane
        normal_x = np.cos(np.radians(tilt)) * np.cos(np.radians(azimuth))
        normal_y = np.cos(np.radians(tilt)) * np.sin(np.radians(azimuth))
        normal_z = np.sin(np.radians(tilt))
        self.ax.quiver(0, 0, 0, normal_x, normal_y, normal_z, length=10, color='red')

        # Set plot limits
        self.ax.set_xlim([-180, 180])
        self.ax.set_ylim([-180, 180])
        self.ax.set_zlim([0, 100])

        # Label axes with angles
        self.ax.set_xticks(np.arange(-180, 181, 45))
        self.ax.set_yticks(np.arange(-180, 181, 45))
        self.ax.set_zticks(np.arange(0, 101, 10))

        self.ax.set_xlabel('X (Azimut in °)')
        self.ax.set_ylabel('Y (Azimut in °)')
        self.ax.set_zlabel('Z (Höhe in m)')

        # Add compass directions
        self.ax.text(180, 0, 0, 'Nord', color='black', fontsize=12)
        self.ax.text(-180, 0, 0, 'Süd', color='black', fontsize=12)
        self.ax.text(0, 180, 0, 'Ost', color='black', fontsize=12)
        self.ax.text(0, -180, 0, 'West', color='black', fontsize=12)

        self.ax.set_title(f"Kollektorausrichtung\nAzimut: {azimuth}°, Neigung: {tilt}°")
        self.canvas.draw()

    def getInputs(self):
        """
        Retrieves the input data from the dialog.

        :return: The input data
        :rtype: dict
        """
        inputs = {
            'bruttofläche_STA': float(self.areaSInput.text()),
            'vs': float(self.vsInput.text()),
            'Typ': self.typeInput.itemText(self.typeInput.currentIndex()),
            'Tsmax': float(self.TsmaxInput.text()),
            'Longitude': float(self.LongitudeInput.text()),
            'STD_Longitude': int(self.STD_LongitudeInput.text()),
            'Latitude': float(self.LatitudeInput.text()),
            'East_West_collector_azimuth_angle': float(self.East_West_collector_azimuth_angleInput.text()),
            'Collector_tilt_angle': float(self.Collector_tilt_angleInput.text()),
            'Tm_rl': float(self.Tm_rlInput.text()),
            'Qsa': float(self.QsaInput.text()),
            'Vorwärmung_K': float(self.Vorwärmung_KInput.text()),
            'DT_WT_Solar_K': float(self.DT_WT_Solar_KInput.text()),
            'DT_WT_Netz_K': float(self.DT_WT_Netz_KInput.text()),
            'kosten_speicher_spez': float(self.vscostInput.text()),
            'kosten_fk_spez': float(self.areaScostfkInput.text()),
            'kosten_vrk_spez': float(self.areaScostvrkInput.text()),
            'opt_volume_min': float(self.minVolumeInput.text()),
            'opt_volume_max': float(self.maxVolumeInput.text()),
            'opt_area_min': float(self.minAreaInput.text()),
            'opt_area_max': float(self.maxAreaInput.text())
        }
        return inputs

class BiomassBoilerDialog(QDialog):
    """
    A dialog for inputting data specific to biomass boiler technology.

    Attributes:
        tech_data (dict): The data for the biomass boiler technology.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the BiomassBoilerDialog with the given data.

        :param tech_data: The data for the biomass boiler technology
        :type tech_data: dict or None
        """
        super(BiomassBoilerDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface for the dialog.
        """
        self.setWindowTitle("Eingabe für Biomassekessel")
        main_layout = QHBoxLayout()

        # Left side: Biomass boiler settings
        bm_layout = QFormLayout()

        self.PBMKInput = QLineEdit(self)
        self.PBMKInput.setText(str(self.tech_data.get('P_BMK', "240")))
        bm_layout.addRow(QLabel("th. Leistung in kW"), self.PBMKInput)

        self.HLsizeInput = QLineEdit(self)
        self.HLsizeInput.setText(str(self.tech_data.get('Größe_Holzlager', "40")))
        bm_layout.addRow(QLabel("Größe Holzlager in t"), self.HLsizeInput)

        self.BMKcostInput = QLineEdit(self)
        self.BMKcostInput.setText(str(self.tech_data.get('spez_Investitionskosten', "200")))
        bm_layout.addRow(QLabel("spez. Investitionskosten Kessel in €/kW"), self.BMKcostInput)

        self.HLcostInput = QLineEdit(self)
        self.HLcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_Holzlager', "400")))
        bm_layout.addRow(QLabel("spez. Investitionskosten Holzlager in €/t"), self.HLcostInput)

        # Input for biomass boiler efficiency
        self.BMKeffInput = QLineEdit(self)
        self.BMKeffInput.setText(str(self.tech_data.get('Nutzungsgrad_BMK', "0.8")))
        bm_layout.addRow(QLabel("Nutzungsgrad Biomassekessel"), self.BMKeffInput)

        # Input for minimum part load
        self.minLoadInput = QLineEdit(self)
        self.minLoadInput.setText(str(self.tech_data.get('min_Teillast', "0.3")))
        bm_layout.addRow(QLabel("minimale Teillast"), self.minLoadInput)

        # Optimization of biomass boiler
        self.minPoptInput = QLineEdit(self)
        self.minPoptInput.setText(str(self.tech_data.get('opt_BMK_min', "0")))
        bm_layout.addRow(QLabel("Untere Grenze th. Leistung Optimierung"), self.minPoptInput)

        self.maxPoptInput = QLineEdit(self)
        self.maxPoptInput.setText(str(self.tech_data.get('opt_BMK_max', "5000")))
        bm_layout.addRow(QLabel("Obere Grenze th. Leistung Optimierung"), self.maxPoptInput)

        # Checkbox for storage active
        self.speicherAktivCheckbox = QCheckBox("Speicher aktiv", self)
        self.speicherAktivCheckbox.setChecked(self.tech_data.get('speicher_aktiv', False))
        self.speicherAktivCheckbox.stateChanged.connect(self.toggleSpeicherInputs)
        bm_layout.addRow(self.speicherAktivCheckbox)

        main_layout.addLayout(bm_layout)

        # Right side: Storage settings
        self.speicherInputs = QWidget()
        speicher_layout = QFormLayout(self.speicherInputs)

        # Input for storage volume
        self.speicherVolInput = QLineEdit(self.speicherInputs)
        self.speicherVolInput.setText(str(self.tech_data.get('Speicher_Volumen', "20")))
        speicher_layout.addRow(QLabel("Speicher Volumen"), self.speicherVolInput)

        # Input for flow temperature
        self.vorlaufTempInput = QLineEdit(self.speicherInputs)
        self.vorlaufTempInput.setText(str(self.tech_data.get('T_vorlauf', "90")))
        speicher_layout.addRow(QLabel("Vorlauftemperatur"), self.vorlaufTempInput)

        # Input for return temperature
        self.ruecklaufTempInput = QLineEdit(self.speicherInputs)
        self.ruecklaufTempInput.setText(str(self.tech_data.get('T_ruecklauf', "60")))
        speicher_layout.addRow(QLabel("Rücklauftemperatur"), self.ruecklaufTempInput)

        # Input for initial fill
        self.initialFillInput = QLineEdit(self.speicherInputs)
        self.initialFillInput.setText(str(self.tech_data.get('initial_fill', "0.0")))
        speicher_layout.addRow(QLabel("initiale Füllung"), self.initialFillInput)

        # Input for minimum fill
        self.minFillInput = QLineEdit(self.speicherInputs)
        self.minFillInput.setText(str(self.tech_data.get('min_fill', "0.2")))
        speicher_layout.addRow(QLabel("minimale Füllung"), self.minFillInput)

        # Input for maximum fill
        self.maxFillInput = QLineEdit(self.speicherInputs)
        self.maxFillInput.setText(str(self.tech_data.get('max_fill', "0.8")))
        speicher_layout.addRow(QLabel("maximale Füllung"), self.maxFillInput)

        # Input for storage costs
        self.spezCostStorageInput = QLineEdit(self.speicherInputs)
        self.spezCostStorageInput.setText(str(self.tech_data.get('spez_Investitionskosten_Speicher', "750")))
        speicher_layout.addRow(QLabel("spez. Investitionskosten Speicher in €/m³"), self.spezCostStorageInput)

        # Optimization of storage
        self.minVolumeoptInput = QLineEdit(self.speicherInputs)
        self.minVolumeoptInput.setText(str(self.tech_data.get('opt_Speicher_min', "0")))
        speicher_layout.addRow(QLabel("Untere Grenze Speichervolumen Optimierung"), self.minVolumeoptInput)

        self.maxVolumeoptInput = QLineEdit(self.speicherInputs)
        self.maxVolumeoptInput.setText(str(self.tech_data.get('opt_Speicher_max', "100")))
        speicher_layout.addRow(QLabel("Obere Grenze Speichervolumen Optimierung"), self.maxVolumeoptInput)

        main_layout.addWidget(self.speicherInputs)

        self.setLayout(main_layout)

        # Set initial visibility of storage inputs
        self.toggleSpeicherInputs()

    def toggleSpeicherInputs(self):
        """
        Toggles the visibility of the storage input fields based on the state of the storage active checkbox.
        """
        self.speicherInputs.setVisible(self.speicherAktivCheckbox.isChecked())

    def getInputs(self):
        """
        Retrieves the input data from the dialog.

        :return: The input data
        :rtype: dict
        """
        inputs = {
            'thermal_capacity_kW': float(self.PBMKInput.text()),
            'Größe_Holzlager': float(self.HLsizeInput.text()),
            'spez_Investitionskosten': float(self.BMKcostInput.text()),
            'spez_Investitionskosten_Holzlager': float(self.HLcostInput.text()),
            'Nutzungsgrad_BMK': float(self.BMKeffInput.text()),
            'min_Teillast': float(self.minLoadInput.text()),
            'speicher_aktiv': self.speicherAktivCheckbox.isChecked(),
            'opt_BMK_min': float(self.minPoptInput.text()),
            'opt_BMK_max': float(self.maxPoptInput.text()),
        }

        if self.speicherAktivCheckbox.isChecked():
            inputs.update({
                'Speicher_Volumen': float(self.speicherVolInput.text()),
                'T_vorlauf': float(self.vorlaufTempInput.text()),
                'T_ruecklauf': float(self.ruecklaufTempInput.text()),
                'initial_fill': float(self.initialFillInput.text()),
                'min_fill': float(self.minFillInput.text()),
                'max_fill': float(self.maxFillInput.text()),
                'spez_Investitionskosten_Speicher': float(self.spezCostStorageInput.text()),
                'opt_Speicher_min': float(self.minVolumeoptInput.text()),
                'opt_Speicher_max': float(self.maxVolumeoptInput.text())
            })

        return inputs
    
class GasBoilerDialog(QDialog):
    """
    A QDialog subclass for configuring gas boiler parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the gas boiler parameters.
        PowerFactorGKInput (QLineEdit): Input field for the dimensioning factor of the gas boiler.
        effGKInput (QLineEdit): Input field for the efficiency of the gas boiler.
        spezcostGKInput (QLineEdit): Input field for the specific investment costs.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the GasBoilerDialog.

        :param tech_data: Dictionary containing initial values for the gas boiler parameters
        :type tech_data: dict or None
        """
        super(GasBoilerDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        self.setWindowTitle("Eingabe für Gaskessel")
        main_layout = QVBoxLayout()
        g_layout = QFormLayout()

        self.thermalCapacityGasBoilerInput = QLineEdit(self)
        self.thermalCapacityGasBoilerInput.setText(str(self.tech_data.get('th_Leistung_kW', "1000")))
        g_layout.addRow(QLabel("Thermische Leistung Gaskessel in kW"), self.thermalCapacityGasBoilerInput)

        self.effGKInput = QLineEdit(self)
        self.effGKInput.setText(str(self.tech_data.get('Nutzungsgrad', "0.9")))
        g_layout.addRow(QLabel("Nutzungsgrad Gaskessel"), self.effGKInput)

        self.spezcostGKInput = QLineEdit(self)
        self.spezcostGKInput.setText(str(self.tech_data.get('spez_Investitionskosten', "30")))
        g_layout.addRow(QLabel("spez. Investitionskosten in €/kW"), self.spezcostGKInput)
        
        main_layout.addLayout(g_layout)
        self.setLayout(main_layout)

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'thermal_capacity_kW': float(self.thermalCapacityGasBoilerInput.text()),
            'spez_Investitionskosten': float(self.spezcostGKInput.text()),
            'Nutzungsgrad': float(self.effGKInput.text())
        }
        return inputs
    
class PowerToHeatDialog(QDialog):
    """
    A QDialog subclass for configuring Power-to-Heat parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the Power-to-Heat parameters.
        PowerFactorGKInput (QLineEdit): Input field for the dimensioning factor of the Power-to-Heat.
        effGKInput (QLineEdit): Input field for the efficiency of the Power-to-Heat.
        spezcostGKInput (QLineEdit): Input field for the specific investment costs.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the PowerToHeatDialog.

        :param tech_data: Dictionary containing initial values for the Power-to-Heat parameters
        :type tech_data: dict or None
        """
        super(PowerToHeatDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        self.setWindowTitle("Eingabe für Power-to-Heat")
        main_layout = QVBoxLayout()
        g_layout = QFormLayout()

        self.thermalCapacityPTHInput = QLineEdit(self)
        self.thermalCapacityPTHInput.setText(str(self.tech_data.get('th_Leistung_kW', "1000")))
        g_layout.addRow(QLabel("Thermische Leistung Power-To-Heat in kW"), self.thermalCapacityPTHInput)

        self.effPTHInput = QLineEdit(self)
        self.effPTHInput.setText(str(self.tech_data.get('Nutzungsgrad', "0.9")))
        g_layout.addRow(QLabel("Nutzungsgrad Power-to-Heat"), self.effPTHInput)

        self.spezcostPTHInput = QLineEdit(self)
        self.spezcostPTHInput.setText(str(self.tech_data.get('spez_Investitionskosten', "30")))
        g_layout.addRow(QLabel("spez. Investitionskosten in €/kW"), self.spezcostPTHInput)
        
        main_layout.addLayout(g_layout)
        self.setLayout(main_layout)

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'thermal_capacity_kW': float(self.thermalCapacityPTHInput.text()),
            'spez_Investitionskosten': float(self.spezcostPTHInput.text()),
            'Nutzungsgrad': float(self.effPTHInput.text())
        }
        return inputs

class CHPDialog(QDialog):
    """
    A QDialog subclass for configuring combined heat and power (CHP) parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the CHP parameters.
        Various QLineEdit and QCheckBox widgets for different CHP parameters.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the CHPDialog.

        :param tech_data: Dictionary containing initial values for the CHP parameters
        :type tech_data: dict or None
        """
        super(CHPDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QHBoxLayout()
        # Linke Seite: BHKW-Einstellungen
        bhkw_layout = QFormLayout()

        # Eingabe für thermische Leistung
        self.PBHKWInput = QLineEdit(self)
        self.PBHKWInput.setText(str(self.tech_data.get('th_Leistung_kW', "100")))
        bhkw_layout.addRow(QLabel("thermische Leistung"), self.PBHKWInput)

        # Eingabe für elektrischen Wirkungsgrad BHKW
        self.BHKWeleffInput = QLineEdit(self)
        self.BHKWeleffInput.setText(str(self.tech_data.get('el_Wirkungsgrad', "0.33")))
        bhkw_layout.addRow(QLabel("elektrischer Wirkungsgrad BHKW"), self.BHKWeleffInput)

        # Eingabe für KWK Wirkungsgrad
        self.KWKeffInput = QLineEdit(self)
        self.KWKeffInput.setText(str(self.tech_data.get('KWK_Wirkungsgrad', "0.9")))
        bhkw_layout.addRow(QLabel("KWK Wirkungsgrad"), self.KWKeffInput)

        # Eingabe für minimale Teillast
        self.minLoadInput = QLineEdit(self)
        self.minLoadInput.setText(str(self.tech_data.get('min_Teillast', "0.7")))
        bhkw_layout.addRow(QLabel("minimale Teillast"), self.minLoadInput)

        # Eingabe für spez. Investitionskosten BHKW
        self.BHKWcostInput = QLineEdit(self)
        self.BHKWcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_GBHKW', "1500")))
        bhkw_layout.addRow(QLabel("spez. Investitionskosten BHKW"), self.BHKWcostInput)

        # Optimierung BHKW
        self.minPoptInput = QLineEdit(self)
        self.minPoptInput.setText(str(self.tech_data.get('opt_BHKW_min', "0")))
        bhkw_layout.addRow(QLabel("Untere Grenze th. Leistung Optimierung"), self.minPoptInput)

        self.maxPoptInput = QLineEdit(self)
        self.maxPoptInput.setText(str(self.tech_data.get('opt_BHKW_max', "1000")))
        bhkw_layout.addRow(QLabel("Obere Grenze th. Leistung Optimierung"), self.maxPoptInput)

        # Checkbox für Speicher aktiv
        self.speicherAktivCheckbox = QCheckBox("Speicher aktiv", self)
        self.speicherAktivCheckbox.setChecked(self.tech_data.get('speicher_aktiv', False))
        self.speicherAktivCheckbox.stateChanged.connect(self.toggleSpeicherInputs)
        bhkw_layout.addRow(self.speicherAktivCheckbox)

        main_layout.addLayout(bhkw_layout)

        # Rechte Seite: Speicher-Einstellungen
        self.speicherInputs = QWidget()
        speicher_layout = QFormLayout(self.speicherInputs)

        # Eingabe für Speicher Volumen
        self.speicherVolInput = QLineEdit(self.speicherInputs)
        self.speicherVolInput.setText(str(self.tech_data.get('Speicher_Volumen_BHKW', "20")))
        speicher_layout.addRow(QLabel("Speicher Volumen"), self.speicherVolInput)

        # Eingabe für Vorlauftemperatur
        self.vorlaufTempInput = QLineEdit(self.speicherInputs)
        self.vorlaufTempInput.setText(str(self.tech_data.get('T_vorlauf', "90")))
        speicher_layout.addRow(QLabel("Vorlauftemperatur"), self.vorlaufTempInput)

        # Eingabe für Rücklauftemperatur
        self.ruecklaufTempInput = QLineEdit(self.speicherInputs)
        self.ruecklaufTempInput.setText(str(self.tech_data.get('T_ruecklauf', "60")))
        speicher_layout.addRow(QLabel("Rücklauftemperatur"), self.ruecklaufTempInput)

        # Eingabe für initiale Füllung
        self.initialFillInput = QLineEdit(self.speicherInputs)
        self.initialFillInput.setText(str(self.tech_data.get('initial_fill', "0.0")))
        speicher_layout.addRow(QLabel("initiale Füllung"), self.initialFillInput)

        # Eingabe für minimale Füllung
        self.minFillInput = QLineEdit(self.speicherInputs)
        self.minFillInput.setText(str(self.tech_data.get('min_fill', "0.2")))
        speicher_layout.addRow(QLabel("minimale Füllung"), self.minFillInput)

        # Eingabe für maximale Füllung
        self.maxFillInput = QLineEdit(self.speicherInputs)
        self.maxFillInput.setText(str(self.tech_data.get('max_fill', "0.8")))
        speicher_layout.addRow(QLabel("maximale Füllung"), self.maxFillInput)

        # Eingabe für Speicherkosten
        self.spezCostStorageInput = QLineEdit(self.speicherInputs)
        self.spezCostStorageInput.setText(str(self.tech_data.get('spez_Investitionskosten_Speicher', "0.8")))
        speicher_layout.addRow(QLabel("spez. Investitionskosten Speicher in €/m³"), self.spezCostStorageInput)

        # Optimierung Speicher
        self.minVolumeoptInput = QLineEdit(self.speicherInputs)
        self.minVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_min', "0")))
        speicher_layout.addRow(QLabel("Untere Grenze Speichervolumen Optimierung"), self.minVolumeoptInput)

        self.maxVolumeoptInput = QLineEdit(self.speicherInputs)
        self.maxVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_max', "100")))
        speicher_layout.addRow(QLabel("Obere Grenze Speichervolumen Optimierung"), self.maxVolumeoptInput)

        main_layout.addWidget(self.speicherInputs)
        self.setLayout(main_layout)

        # Initiale Sichtbarkeit der Speicher-Eingaben einstellen
        self.toggleSpeicherInputs()

    def toggleSpeicherInputs(self):
        """
        Toggles the visibility of the storage inputs based on the state of the storage active checkbox.
        """
        self.speicherInputs.setVisible(self.speicherAktivCheckbox.isChecked())

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'th_Leistung_kW': float(self.PBHKWInput.text()),
            'el_Wirkungsgrad': float(self.BHKWeleffInput.text()),
            'spez_Investitionskosten_GBHKW': float(self.BHKWcostInput.text()),
            'KWK_Wirkungsgrad': float(self.KWKeffInput.text()),
            'min_Teillast': float(self.minLoadInput.text()),
            'speicher_aktiv': self.speicherAktivCheckbox.isChecked(),
            'opt_BHKW_min': float(self.minPoptInput.text()),
            'opt_BHKW_max': float(self.maxPoptInput.text()),
        }

        if self.speicherAktivCheckbox.isChecked():
            inputs.update({
                'Speicher_Volumen_BHKW': float(self.speicherVolInput.text()),
                'T_vorlauf': float(self.vorlaufTempInput.text()),
                'T_ruecklauf': float(self.ruecklaufTempInput.text()),
                'initial_fill': float(self.initialFillInput.text()),
                'min_fill': float(self.minFillInput.text()),
                'max_fill': float(self.maxFillInput.text()),
                'spez_Investitionskosten_Speicher': float(self.spezCostStorageInput.text()),
                'opt_BHKW_Speicher_min': float(self.minVolumeoptInput.text()),
                'opt_BHKW_Speicher_max': float(self.maxVolumeoptInput.text())
            })

        return inputs
    
class HolzgasCHPDialog(QDialog):
    """
    A QDialog subclass for configuring Holzgas-CHP (combined heat and power) parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the Holzgas-CHP parameters.
        Various QLineEdit and QCheckBox widgets for different Holzgas-CHP parameters.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the HolzgasCHPDialog.

        :param tech_data: Dictionary containing initial values for the Holzgas-CHP parameters
        :type tech_data: dict or None
        """
        super(HolzgasCHPDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QHBoxLayout()

        # Linke Seite: Holzgas-BHKW-Einstellungen
        chp_layout = QFormLayout()

        self.PBHKWInput = QLineEdit(self)
        self.PBHKWInput.setText(str(self.tech_data.get('th_Leistung_kW', "100")))
        chp_layout.addRow(QLabel("thermische Leistung"), self.PBHKWInput)

        # Eingabe für elektrischen Wirkungsgrad BHKW
        self.BHKWeleffInput = QLineEdit(self)
        self.BHKWeleffInput.setText(str(self.tech_data.get('el_Wirkungsgrad', "0.33")))
        chp_layout.addRow(QLabel("elektrischer Wirkungsgrad BHKW"), self.BHKWeleffInput)

        # Eingabe für KWK Wirkungsgrad
        self.KWKeffInput = QLineEdit(self)
        self.KWKeffInput.setText(str(self.tech_data.get('KWK_Wirkungsgrad', "0.9")))
        chp_layout.addRow(QLabel("KWK Wirkungsgrad"), self.KWKeffInput)

        # Eingabe für minimale Teillast
        self.minLoadInput = QLineEdit(self)
        self.minLoadInput.setText(str(self.tech_data.get('min_Teillast', "0.7")))
        chp_layout.addRow(QLabel("minimale Teillast"), self.minLoadInput)

        self.BHKWcostInput = QLineEdit(self)
        self.BHKWcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_HBHKW', "1850")))
        chp_layout.addRow(QLabel("spez. Investitionskosten BHKW"), self.BHKWcostInput)

        # Optimierung BHKW
        self.minPoptInput = QLineEdit(self)
        self.minPoptInput.setText(str(self.tech_data.get('opt_BHKW_min', "0")))
        chp_layout.addRow(QLabel("Untere Grenze th. Leistung Optimierung"), self.minPoptInput)

        self.maxPoptInput = QLineEdit(self)
        self.maxPoptInput.setText(str(self.tech_data.get('opt_BHKW_max', "1000")))
        chp_layout.addRow(QLabel("Obere Grenze th. Leistung Optimierung"), self.maxPoptInput)

        # Checkbox für Speicher aktiv
        self.speicherAktivCheckbox = QCheckBox("Speicher aktiv", self)
        self.speicherAktivCheckbox.setChecked(self.tech_data.get('speicher_aktiv', False))
        self.speicherAktivCheckbox.stateChanged.connect(self.toggleSpeicherInputs)
        chp_layout.addRow(self.speicherAktivCheckbox)

        main_layout.addLayout(chp_layout)

        # Rechte Seite: Speicher-Einstellungen
        self.speicherInputs = QWidget()
        speicher_layout = QFormLayout(self.speicherInputs)

        # Eingabe für Speicher Volumen
        self.speicherVolInput = QLineEdit(self.speicherInputs)
        self.speicherVolInput.setText(str(self.tech_data.get('Speicher_Volumen_BHKW', "20")))
        speicher_layout.addRow(QLabel("Speicher Volumen"), self.speicherVolInput)

        # Eingabe für Vorlauftemperatur
        self.vorlaufTempInput = QLineEdit(self.speicherInputs)
        self.vorlaufTempInput.setText(str(self.tech_data.get('T_vorlauf', "90")))
        speicher_layout.addRow(QLabel("Vorlauftemperatur"), self.vorlaufTempInput)

        # Eingabe für Rücklauftemperatur
        self.ruecklaufTempInput = QLineEdit(self.speicherInputs)
        self.ruecklaufTempInput.setText(str(self.tech_data.get('T_ruecklauf', "60")))
        speicher_layout.addRow(QLabel("Rücklauftemperatur"), self.ruecklaufTempInput)

        # Eingabe für initiale Füllung
        self.initialFillInput = QLineEdit(self.speicherInputs)
        self.initialFillInput.setText(str(self.tech_data.get('initial_fill', "0.0")))
        speicher_layout.addRow(QLabel("initiale Füllung"), self.initialFillInput)

        # Eingabe für minimale Füllung
        self.minFillInput = QLineEdit(self.speicherInputs)
        self.minFillInput.setText(str(self.tech_data.get('min_fill', "0.2")))
        speicher_layout.addRow(QLabel("minimale Füllung"), self.minFillInput)

        # Eingabe für maximale Füllung
        self.maxFillInput = QLineEdit(self.speicherInputs)
        self.maxFillInput.setText(str(self.tech_data.get('max_fill', "0.8")))
        speicher_layout.addRow(QLabel("maximale Füllung"), self.maxFillInput)

        # Eingabe für Speicherkosten
        self.spezCostStorageInput = QLineEdit(self.speicherInputs)
        self.spezCostStorageInput.setText(str(self.tech_data.get('spez_Investitionskosten_Speicher', "0.8")))
        speicher_layout.addRow(QLabel("spez. Investitionskosten Speicher in €/m³"), self.spezCostStorageInput)

        # Optimierung Speicher
        self.minVolumeoptInput = QLineEdit(self.speicherInputs)
        self.minVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_min', "0")))
        speicher_layout.addRow(QLabel("Untere Grenze Speichervolumen Optimierung"), self.minVolumeoptInput)

        self.maxVolumeoptInput = QLineEdit(self.speicherInputs)
        self.maxVolumeoptInput.setText(str(self.tech_data.get('opt_BHKW_Speicher_max', "100")))
        speicher_layout.addRow(QLabel("Obere Grenze Speichervolumen Optimierung"), self.maxVolumeoptInput)

        main_layout.addWidget(self.speicherInputs)
        self.setLayout(main_layout)

        # Initiale Sichtbarkeit der Speicher-Eingaben einstellen
        self.toggleSpeicherInputs()

    def toggleSpeicherInputs(self):
        """
        Toggles the visibility of the storage inputs based on the state of the storage active checkbox.
        """
        self.speicherInputs.setVisible(self.speicherAktivCheckbox.isChecked())

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'th_Leistung_kW': float(self.PBHKWInput.text()),
            'el_Wirkungsgrad': float(self.BHKWeleffInput.text()),
            'spez_Investitionskosten_HBHKW': float(self.BHKWcostInput.text()),
            'KWK_Wirkungsgrad': float(self.KWKeffInput.text()),
            'min_Teillast': float(self.minLoadInput.text()),
            'speicher_aktiv': self.speicherAktivCheckbox.isChecked(),
            'opt_BHKW_min': float(self.minPoptInput.text()),
            'opt_BHKW_max': float(self.maxPoptInput.text()),
        }

        if self.speicherAktivCheckbox.isChecked():
            inputs.update({
                'Speicher_Volumen_BHKW': float(self.speicherVolInput.text()),
                'T_vorlauf': float(self.vorlaufTempInput.text()),
                'T_ruecklauf': float(self.ruecklaufTempInput.text()),
                'initial_fill': float(self.initialFillInput.text()),
                'min_fill': float(self.minFillInput.text()),
                'max_fill': float(self.maxFillInput.text()),
                'spez_Investitionskosten_Speicher': float(self.spezCostStorageInput.text()),
                'opt_BHKW_Speicher_min': float(self.minVolumeoptInput.text()),
                'opt_BHKW_Speicher_max': float(self.maxVolumeoptInput.text())
            })

        return inputs
    
class GeothermalDialog(QWidget):
    """
    A QWidget subclass for configuring geothermal parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the geothermal parameters.
        areaGInput (QLineEdit): Input field for the area of the borehole field.
        depthInput (QLineEdit): Input field for the depth of the boreholes.
        tempGInput (QLineEdit): Input field for the source temperature.
        distholeInput (QLineEdit): Input field for the distance between boreholes.
        costdethInput (QLineEdit): Input field for the specific drilling costs.
        spezPInput (QLineEdit): Input field for the specific extraction performance.
        VBHInput (QLineEdit): Input field for the full load hours of the borehole field.
        WPGcostInput (QLineEdit): Input field for the specific investment costs of the heat pump.
        figure (Figure): Matplotlib figure for plotting the borehole configuration.
        ax (Axes): Matplotlib axes for plotting.
        canvas (FigureCanvas): Canvas to display the Matplotlib figure.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the GeothermalDialog.

        :param tech_data: Dictionary containing initial values for the geothermal parameters
        :type tech_data: dict or None
        """
        super(GeothermalDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        form_layout = QFormLayout()

        self.areaGInput = QLineEdit(self)
        self.areaGInput.setText(str(self.tech_data.get('Fläche', "100")))
        form_layout.addRow(QLabel("Fläche Erdsondenfeld in m²"), self.areaGInput)

        self.depthInput = QLineEdit(self)
        self.depthInput.setText(str(self.tech_data.get('Bohrtiefe', "100")))
        form_layout.addRow(QLabel("Bohrtiefe Sonden in m"), self.depthInput)

        self.tempGInput = QLineEdit(self)
        self.tempGInput.setText(str(self.tech_data.get('Temperatur_Geothermie', "10")))
        form_layout.addRow(QLabel("Quelltemperatur in °C"), self.tempGInput)

        self.distholeInput = QLineEdit(self)
        self.distholeInput.setText(str(self.tech_data.get('Abstand_Sonden', "10")))
        form_layout.addRow(QLabel("Abstand Erdsonden in m"), self.distholeInput)

        self.costdethInput = QLineEdit(self)
        self.costdethInput.setText(str(self.tech_data.get('spez_Bohrkosten', "120")))
        form_layout.addRow(QLabel("spez. Bohrkosten pro Bohrmeter in €/m"), self.costdethInput)

        self.spezPInput = QLineEdit(self)
        self.spezPInput.setText(str(self.tech_data.get('spez_Entzugsleistung', "50")))
        form_layout.addRow(QLabel("spez. Entzugsleistung Untergrund in W/m"), self.spezPInput)

        self.VBHInput = QLineEdit(self)
        self.VBHInput.setText(str(self.tech_data.get('Vollbenutzungsstunden', "2400")))
        form_layout.addRow(QLabel("Vollbenutzungsstunden Sondenfeld in h"), self.VBHInput)

        self.WPGcostInput = QLineEdit(self)
        self.WPGcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        form_layout.addRow(QLabel("spez. Investitionskosten Wärmepumpe in €/kW"), self.WPGcostInput)

        top_layout.addLayout(form_layout)

        # Visualization
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111, projection='3d')
        self.canvas = FigureCanvas(self.figure)
        top_layout.addWidget(self.canvas)

        main_layout.addLayout(top_layout)

        # Connect input changes to the visualization update
        self.areaGInput.textChanged.connect(self.updateVisualization)
        self.depthInput.textChanged.connect(self.updateVisualization)
        self.distholeInput.textChanged.connect(self.updateVisualization)

        self.setLayout(main_layout)
        self.updateVisualization()

    def updateVisualization(self):
        """
        Updates the 3D visualization of the borehole configuration.
        """
        try:
            area = float(self.areaGInput.text())
            depth = float(self.depthInput.text())
            distance = float(self.distholeInput.text())
        except ValueError:
            area = 100
            depth = 100
            distance = 10

        self.ax.clear()

        # Calculate the number of boreholes in a grid
        side_length = np.sqrt(area)
        num_holes_per_side = int(side_length / distance) + 1
        x_positions = np.linspace(0, side_length, num_holes_per_side)
        y_positions = np.linspace(0, side_length, num_holes_per_side)
        x_positions, y_positions = np.meshgrid(x_positions, y_positions)

        # Draw the boreholes
        for x, y in zip(x_positions.flatten(), y_positions.flatten()):
            self.ax.plot([x, x], [y, y], [0, -depth], color='blue')

        # Set plot limits
        self.ax.set_xlim([0, side_length])
        self.ax.set_ylim([0, side_length])
        self.ax.set_zlim([-depth, 0])

        # Label axes
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (Tiefe in m)')

        self.ax.set_title(f"Sondenkonfiguration\nFläche: {area} m², Tiefe: {depth} m, Abstand: {distance} m")
        self.canvas.draw()

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'Fläche': float(self.areaGInput.text()),
            'Bohrtiefe': float(self.depthInput.text()),
            'Temperatur_Geothermie': float(self.tempGInput.text()),
            'Abstand_Sonden': float(self.distholeInput.text()),
            'spez_Bohrkosten': float(self.costdethInput.text()),
            'spez_Entzugsleistung': float(self.spezPInput.text()),
            'Vollbenutzungsstunden': float(self.VBHInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPGcostInput.text())
        }
        return inputs

class WasteHeatPumpDialog(QDialog):
    """
    A QDialog subclass for configuring waste heat pump parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the waste heat pump parameters.
        PWHInput (QLineEdit): Input field for the cooling capacity of waste heat.
        TWHInput (QLineEdit): Input field for the temperature of waste heat.
        WHcostInput (QLineEdit): Input field for the specific investment costs of waste heat utilization.
        WPWHcostInput (QLineEdit): Input field for the specific investment costs of the heat pump.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the WasteHeatPumpDialog.

        :param tech_data: Dictionary containing initial values for the waste heat pump parameters
        :type tech_data: dict or None
        """
        super(WasteHeatPumpDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QVBoxLayout()
        whp_layout = QFormLayout()

        self.PWHInput = QLineEdit(self)
        self.PWHInput.setText(str(self.tech_data.get('Kühlleistung_Abwärme', "30")))
        whp_layout.addRow(QLabel("Kühlleistung Abwärme in kW"), self.PWHInput)

        self.TWHInput = QLineEdit(self)
        self.TWHInput.setText(str(self.tech_data.get('Temperatur_Abwärme', "30")))
        whp_layout.addRow(QLabel("Temperatur Abwärme in °C"), self.TWHInput)

        self.WHcostInput = QLineEdit(self)
        self.WHcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_Abwärme', "500")))
        whp_layout.addRow(QLabel("spez. Investitionskosten Abwärmenutzung in €/kW"), self.WHcostInput)

        self.WPWHcostInput = QLineEdit(self)
        self.WPWHcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        whp_layout.addRow(QLabel("spez. Investitionskosten Wärmepumpe"), self.WPWHcostInput)

        main_layout.addLayout(whp_layout)
        self.setLayout(main_layout)

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'Kühlleistung_Abwärme': float(self.PWHInput.text()),
            'Temperatur_Abwärme': float(self.TWHInput.text()),
            'spez_Investitionskosten_Abwärme': float(self.WHcostInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPWHcostInput.text())
        }
        return inputs

class RiverHeatPumpDialog(QDialog):
    """
    A QDialog subclass for configuring river heat pump parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the river heat pump parameters.
        PFWInput (QLineEdit): Input field for the thermal capacity of the heat pump.
        TFWInput (QLineEdit): Input field for the river temperature.
        DTFWInput (QLineEdit): Input field for the permissible deviation of the heat pump's supply temperature from the network supply temperature.
        RHcostInput (QLineEdit): Input field for the specific investment costs of river heat utilization.
        WPRHcostInput (QLineEdit): Input field for the specific investment costs of the heat pump.
        csvButton (QPushButton): Button to open and load a CSV file containing river temperatures.
        canvas (FigureCanvas): Canvas to display the Matplotlib figure.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the RiverHeatPumpDialog.

        :param tech_data: Dictionary containing initial values for the river heat pump parameters
        :type tech_data: dict or None
        """
        super(RiverHeatPumpDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QVBoxLayout()
        rhp_layout = QFormLayout()

        self.PFWInput = QLineEdit(self)
        self.PFWInput.setText(str(self.tech_data.get('Wärmeleistung_FW_WP', "200")))
        rhp_layout.addRow(QLabel("th. Leistung Wärmepumpe in kW"), self.PFWInput)

        self.TFWInput = QLineEdit(self)
        if isinstance(self.tech_data.get('Temperatur_FW_WP'), (float, int)) or self.tech_data == {}:
            self.TFWInput.setText(str(self.tech_data.get('Temperatur_FW_WP', "10")))
        rhp_layout.addRow(QLabel("Flusstemperatur in °C"), self.TFWInput)

        self.csvButton = QPushButton("CSV für Flusstemperatur wählen", self)
        self.csvButton.clicked.connect(self.openCSV)
        rhp_layout.addRow(self.csvButton)

        self.DTFWInput = QLineEdit(self)
        self.DTFWInput.setText(str(self.tech_data.get('dT', "0")))
        rhp_layout.addRow(QLabel("Zulässige Abweichung Vorlauftemperatur Wärmepumpe von Netzvorlauftemperatur"), self.DTFWInput)

        self.RHcostInput = QLineEdit(self)
        self.RHcostInput.setText(str(self.tech_data.get('spez_Investitionskosten_Flusswasser', "1000")))
        rhp_layout.addRow(QLabel("spez. Investitionskosten Flusswärmenutzung"), self.RHcostInput)

        self.WPRHcostInput = QLineEdit(self)
        self.WPRHcostInput.setText(str(self.tech_data.get('spezifische_Investitionskosten_WP', "1000")))
        rhp_layout.addRow(QLabel("spez. Investitionskosten Wärmepumpe"), self.WPRHcostInput)

        main_layout.addLayout(rhp_layout)
        self.setLayout(main_layout)

    def openCSV(self):
        """
        Opens a file dialog to select a CSV file and loads its content.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)") # this needs a path
        if filename:
            self.loadCSV(filename)

    def loadCSV(self, filename):
        """
        Loads temperature data from a CSV file.

        :param filename: The path to the CSV file
        :type filename: str
        """
        data = np.loadtxt(filename, delimiter=';', skiprows=1, usecols=1).astype(float)
        self.csvData = data
        QMessageBox.information(self, "CSV geladen", f"CSV-Datei {filename} erfolgreich geladen.")

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
            'Wärmeleistung_FW_WP': float(self.PFWInput.text()),
            'dT': float(self.DTFWInput.text()),
            'spez_Investitionskosten_Flusswasser': float(self.RHcostInput.text()),
            'spezifische_Investitionskosten_WP': float(self.WPRHcostInput.text())
        }
        try:
            if hasattr(self, 'csvData'):
                inputs['Temperatur_FW_WP'] = self.csvData
            elif isinstance(self.tech_data.get('Temperatur_FW_WP'), (float, int)):
                inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
            elif isinstance(self.tech_data.get('Temperatur_FW_WP'), np.ndarray):
                inputs['Temperatur_FW_WP'] = self.tech_data.get('Temperatur_FW_WP')
            else:
                inputs['Temperatur_FW_WP'] = float(self.TFWInput.text())
        except ValueError:
            pass
        return inputs


class AqvaHeatDialog(QDialog):
    """
    A QDialog subclass for configuring AqvaHeat parameters.

    Attributes:
        tech_data (dict): Dictionary containing initial values for the river heat pump parameters.
        PFWInput (QLineEdit): Input field for the thermal capacity of the heat pump.
        TFWInput (QLineEdit): Input field for the river temperature.
        DTFWInput (QLineEdit): Input field for the permissible deviation of the heat pump's supply temperature from the network supply temperature.
        RHcostInput (QLineEdit): Input field for the specific investment costs of river heat utilization.
        WPRHcostInput (QLineEdit): Input field for the specific investment costs of the heat pump.
        csvButton (QPushButton): Button to open and load a CSV file containing river temperatures.
        canvas (FigureCanvas): Canvas to display the Matplotlib figure.
    """

    def __init__(self, tech_data=None):
        """
        Initializes the RiverHeatPumpDialog.

        :param tech_data: Dictionary containing initial values for the river heat pump parameters
        :type tech_data: dict or None
        """
        super(AqvaHeatDialog, self).__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface components.
        """
        main_layout = QVBoxLayout()
        rhp_layout = QFormLayout()

        main_layout.addLayout(rhp_layout)
        self.setLayout(main_layout)

    def openCSV(self):
        """
        Opens a file dialog to select a CSV file and loads its content.
        """
        filename, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)") # this needs a path
        if filename:
            self.loadCSV(filename)

    def loadCSV(self, filename):
        """
        Loads temperature data from a CSV file.

        :param filename: The path to the CSV file
        :type filename: str
        """
        data = np.loadtxt(filename, delimiter=';', skiprows=1, usecols=1).astype(float)
        self.csvData = data
        QMessageBox.information(self, "CSV geladen", f"CSV-Datei {filename} erfolgreich geladen.")

    def getInputs(self):
        """
        Retrieves the input values from the user interface.

        :return: A dictionary containing the input values
        :rtype: dict
        """
        inputs = {
        }
        return inputs
    
class ThermalStorage1DDialog(QWidget):
    """
    Dialog for configuring a 1D stratified thermal storage (ThermalStorageAdapter).

    Sections:
    - Basic: name, volume, height, geometry, n_nodes
    - Temperature limits: T_min, T_max, initial_temp
    - Loss model: constant / split / ground (dynamic fields)
    - Fluid properties: water / constant (dynamic fields)
    - Solver (collapsible advanced section)
    - Costs: specific investment cost
    """

    def __init__(self, tech_data=None):
        super().__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self._init_ui()

    def _field(self, key, default):
        """Return tech_data value as string or default."""
        return str(self.tech_data.get(key, default))

    def _init_ui(self):
        from districtheatingsim.gui.EnergySystemTab._10_utilities import CollapsibleHeader

        main_layout = QVBoxLayout(self)

        # ── Basic ────────────────────────────────────────────────────────────
        basic_box = QGroupBox("Basic")
        basic_layout = QFormLayout()

        self.name_input = QLineEdit(self._field("name", "Saisonaler Wärmespeicher"))
        basic_layout.addRow("Name:", self.name_input)

        self.volume_input = QLineEdit(self._field("volume", "1000"))
        basic_layout.addRow("Volume (m³):", self.volume_input)

        self.height_input = QLineEdit(self._field("height", "10"))
        basic_layout.addRow("Height (m):", self.height_input)

        self.geometry_combo = QComboBox()
        self.geometry_combo.addItems(["cylinder", "truncated_cone", "truncated_pyramid"])
        self.geometry_combo.setCurrentText(self._field("geometry_type", "cylinder"))
        basic_layout.addRow("Geometry:", self.geometry_combo)

        self.n_nodes_input = QLineEdit(self._field("n_nodes", "50"))
        basic_layout.addRow("Number of nodes:", self.n_nodes_input)

        basic_box.setLayout(basic_layout)
        main_layout.addWidget(basic_box)

        # ── Temperature limits ───────────────────────────────────────────────
        temp_box = QGroupBox("Temperature Limits")
        temp_layout = QFormLayout()

        self.T_min_input = QLineEdit(self._field("T_min", "40"))
        temp_layout.addRow("T_min (°C):", self.T_min_input)

        self.T_max_input = QLineEdit(self._field("T_max", "95"))
        temp_layout.addRow("T_max (°C):", self.T_max_input)

        self.initial_temp_input = QLineEdit(self._field("initial_temp", "60"))
        temp_layout.addRow("Initial temperature (°C):", self.initial_temp_input)

        temp_box.setLayout(temp_layout)
        main_layout.addWidget(temp_box)

        # ── Loss model ───────────────────────────────────────────────────────
        loss_box = QGroupBox("Loss Model")
        loss_outer = QVBoxLayout()

        loss_type_row = QFormLayout()
        self.loss_type_combo = QComboBox()
        self.loss_type_combo.addItems(["constant", "split", "ground"])
        self.loss_type_combo.setCurrentText(self._field("loss_model_type", "constant"))
        loss_type_row.addRow("Type:", self.loss_type_combo)
        loss_outer.addLayout(loss_type_row)

        # Constant loss fields
        self._loss_constant_widget = QWidget()
        lc = QFormLayout(self._loss_constant_widget)
        self.U_loss_input = QLineEdit(self._field("U_loss", "0.3"))
        lc.addRow("U_loss (W/m²K):", self.U_loss_input)
        self.T_ambient_input = QLineEdit(self._field("T_ambient", "10"))
        lc.addRow("T_ambient (°C):", self.T_ambient_input)
        loss_outer.addWidget(self._loss_constant_widget)

        # Split loss fields
        self._loss_split_widget = QWidget()
        ls = QFormLayout(self._loss_split_widget)
        self.U_top_input = QLineEdit(self._field("U_top", "0.3"))
        ls.addRow("U_top (W/m²K):", self.U_top_input)
        self.U_side_input = QLineEdit(self._field("U_side", "0.06"))
        ls.addRow("U_side (W/m²K):", self.U_side_input)
        self.U_bottom_input = QLineEdit(self._field("U_bottom", "0.4"))
        ls.addRow("U_bottom (W/m²K):", self.U_bottom_input)
        self.T_ambient_split_input = QLineEdit(self._field("T_ambient", "10"))
        ls.addRow("T_ambient (°C):", self.T_ambient_split_input)
        loss_outer.addWidget(self._loss_split_widget)

        # Ground loss fields
        self._loss_ground_widget = QWidget()
        lg = QFormLayout(self._loss_ground_widget)
        self.U_top_ground_input = QLineEdit(self._field("U_top", "0.3"))
        lg.addRow("U_top (W/m²K):", self.U_top_ground_input)
        self.T_ground_surface_input = QLineEdit(self._field("T_ambient", "10"))
        lg.addRow("T_ground_surface (°C):", self.T_ground_surface_input)
        self.z_ground_input = QLineEdit(self._field("z_ground", "2.0"))
        lg.addRow("Burial depth z_ground (m):", self.z_ground_input)
        loss_outer.addWidget(self._loss_ground_widget)

        loss_box.setLayout(loss_outer)
        main_layout.addWidget(loss_box)

        self.loss_type_combo.currentTextChanged.connect(self._update_loss_visibility)
        self._update_loss_visibility(self.loss_type_combo.currentText())

        # ── Fluid properties ─────────────────────────────────────────────────
        fluid_box = QGroupBox("Fluid Properties")
        fluid_outer = QVBoxLayout()

        fluid_type_row = QFormLayout()
        self.fluid_type_combo = QComboBox()
        self.fluid_type_combo.addItems(["water", "constant"])
        self.fluid_type_combo.setCurrentText(self._field("fluid_type", "water"))
        fluid_type_row.addRow("Type:", self.fluid_type_combo)
        fluid_outer.addLayout(fluid_type_row)

        self._fluid_constant_widget = QWidget()
        fc = QFormLayout(self._fluid_constant_widget)
        self.rho_input = QLineEdit(self._field("rho", "977.8"))
        fc.addRow("Density ρ (kg/m³):", self.rho_input)
        self.cp_input = QLineEdit(self._field("cp", "4187"))
        fc.addRow("Heat capacity cp (J/kgK):", self.cp_input)
        self.lambda_fluid_input = QLineEdit(self._field("lambda_fluid", "0.663"))
        fc.addRow("Thermal conductivity λ (W/mK):", self.lambda_fluid_input)
        fluid_outer.addWidget(self._fluid_constant_widget)

        fluid_box.setLayout(fluid_outer)
        main_layout.addWidget(fluid_box)

        self.fluid_type_combo.currentTextChanged.connect(self._update_fluid_visibility)
        self._update_fluid_visibility(self.fluid_type_combo.currentText())

        # ── Solver (collapsible) ─────────────────────────────────────────────
        solver_inner = QWidget()
        solver_layout = QFormLayout(solver_inner)

        self.solver_combo = QComboBox()
        self.solver_combo.addItems(["implicit", "explicit"])
        self.solver_combo.setCurrentText(self._field("solver", "implicit"))
        solver_layout.addRow("Solver:", self.solver_combo)

        self.advection_combo = QComboBox()
        self.advection_combo.addItems(["tvd", "upwind"])
        self.advection_combo.setCurrentText(self._field("advection_scheme", "tvd"))
        solver_layout.addRow("Advection scheme:", self.advection_combo)

        self.buoyancy_check = QCheckBox("Buoyancy correction")
        self.buoyancy_check.setChecked(self.tech_data.get("buoyancy", True))
        solver_layout.addRow("", self.buoyancy_check)

        solver_header = CollapsibleHeader("Solver (Advanced)", solver_inner)
        solver_header.toggle_content()  # start collapsed
        main_layout.addWidget(solver_header)

        # ── Costs ────────────────────────────────────────────────────────────
        cost_box = QGroupBox("Costs")
        cost_layout = QFormLayout()

        self.spez_cost_input = QLineEdit(self._field("spez_Investitionskosten", "50"))
        cost_layout.addRow("Specific investment costs (€/m³):", self.spez_cost_input)

        cost_box.setLayout(cost_layout)
        main_layout.addWidget(cost_box)

        self.setLayout(main_layout)

    def _update_loss_visibility(self, loss_type: str):
        self._loss_constant_widget.setVisible(loss_type == "constant")
        self._loss_split_widget.setVisible(loss_type == "split")
        self._loss_ground_widget.setVisible(loss_type == "ground")

    def _update_fluid_visibility(self, fluid_type: str):
        self._fluid_constant_widget.setVisible(fluid_type == "constant")

    def getInputs(self) -> dict:
        loss_type = self.loss_type_combo.currentText()

        # Resolve T_ambient from whichever section is active
        if loss_type == "constant":
            T_ambient = float(self.T_ambient_input.text())
        elif loss_type == "split":
            T_ambient = float(self.T_ambient_split_input.text())
        else:
            T_ambient = float(self.T_ground_surface_input.text())

        return {
            "name": self.name_input.text(),
            "volume": float(self.volume_input.text()),
            "height": float(self.height_input.text()),
            "geometry_type": self.geometry_combo.currentText(),
            "n_nodes": int(self.n_nodes_input.text()),
            "T_min": float(self.T_min_input.text()),
            "T_max": float(self.T_max_input.text()),
            "initial_temp": float(self.initial_temp_input.text()),
            "loss_model_type": loss_type,
            "U_loss": float(self.U_loss_input.text()),
            "U_top": float(self.U_top_input.text()) if loss_type == "split"
                     else float(self.U_top_ground_input.text()) if loss_type == "ground"
                     else float(self.U_loss_input.text()),
            "U_side": float(self.U_side_input.text()),
            "U_bottom": float(self.U_bottom_input.text()),
            "T_ambient": T_ambient,
            "z_ground": float(self.z_ground_input.text()),
            "fluid_type": self.fluid_type_combo.currentText(),
            "rho": float(self.rho_input.text()),
            "cp": float(self.cp_input.text()),
            "lambda_fluid": float(self.lambda_fluid_input.text()),
            "solver": self.solver_combo.currentText(),
            "advection_scheme": self.advection_combo.currentText(),
            "buoyancy": self.buoyancy_check.isChecked(),
            "spez_Investitionskosten": float(self.spez_cost_input.text()),
            "hours": 8760,
        }
