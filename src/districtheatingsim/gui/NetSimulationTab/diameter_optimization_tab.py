"""Diameter Optimization Tab Module
================================

UI tab for pipe diameter optimization settings in district heating networks.

:author: M.Eng. Jonas Pfeiffer
"""

from PyQt6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from districtheatingsim.constants import MAX_PRESSURE_LOSS_PA_PER_M


class DiameterOptimizationTab(QWidget):
    """
    Widget for configuring pipe diameter optimization parameters.
    """

    def __init__(self, dialog_config, parent=None):
        """
        Initialize diameter optimization tab.

        :param dialog_config: Configuration data for dialog settings.
        :type dialog_config: dict
        :param parent: Parent widget.
        :type parent: QWidget
        """
        super().__init__(parent)
        self.dialog_config = dialog_config
        self.initUI()

    def initUI(self):
        """
        Initialize user interface components.
        """
        layout = QVBoxLayout(self)

        OptDiameterGroup = QGroupBox("Durchmesseroptimierung im Netz")
        OptDiameterGroup.setStyleSheet("QGroupBox { font-size: 11pt; font-weight: bold; }")
        OptDiameterLayout = QVBoxLayout()
        OptDiameterLayout.addLayout(self.createDiameterOptCheckbox())
        OptDiameterLayout.addLayout(self.createDiameterOptInput())
        OptDiameterGroup.setLayout(OptDiameterLayout)
        layout.addWidget(OptDiameterGroup)

        # Update der Sichtbarkeit
        self.updateInputFieldsVisibility()

    def createDiameterOptCheckbox(self):
        """
        Create checkbox for enabling diameter optimization.

        :return: Layout containing checkbox.
        :rtype: QVBoxLayout
        """
        layout = QVBoxLayout()
        self.DiameterOptCheckbox = QCheckBox("Durchmesser optimieren.")
        layout.addWidget(self.DiameterOptCheckbox)
        self.DiameterOptCheckbox.setChecked(True)
        self.DiameterOptCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createDiameterOptInput(self):
        """
        Create input fields for diameter optimization parameters.

        :return: Layout containing input fields.
        :rtype: QVBoxLayout
        """
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Eingaben zur Durchmesseroptimierung der Rohrleitungen:"))

        config = self.dialog_config["diameter_optimization"]
        hint = (
            "Jede Leitung bekommt die kleinste Nennweite, die beide Grenzen einhält.\n"
            "In kleinen Leitungen (Hausanschlüsse, DN 20 …) entscheidet meist der Druckverlust:\n"
            "DN 20 verliert bei 1 m/s rund 690 Pa/m, DN 100 rund 90 Pa/m.\n"
            "Die Pumpe wird danach so ausgelegt, dass am ungünstigsten Hausanschluss\n"
            "mindestens 1 bar Differenzdruck anliegen."
        )

        row_layout = QHBoxLayout()
        self.v_max_pipelabel = QLabel("Maximale Strömungsgeschwindigkeit Leitungen in m/s:")
        self.v_max_pipeInput = QLineEdit(str(config["v_max_pipe"]))
        self.v_max_pipelabel.setToolTip(hint)
        self.v_max_pipeInput.setToolTip(hint)
        row_layout.addWidget(self.v_max_pipelabel)
        row_layout.addWidget(self.v_max_pipeInput)
        layout.addLayout(row_layout)

        loss_layout = QHBoxLayout()
        self.max_loss_label = QLabel("Maximaler Druckverlust durch Reibung in Pa/m (leer = ohne Grenze):")
        self.max_loss_input = QLineEdit(str(config.get("max_pressure_loss_pa_per_m", MAX_PRESSURE_LOSS_PA_PER_M)))
        self.max_loss_label.setToolTip(hint)
        self.max_loss_input.setToolTip(hint)
        loss_layout.addWidget(self.max_loss_label)
        loss_layout.addWidget(self.max_loss_input)
        layout.addLayout(loss_layout)

        self.material_filterInput = QComboBox(self)
        self.material_filterInput.addItems(self.dialog_config["diameter_optimization"]["material_filter"])
        layout.addWidget(self.material_filterInput)
        self.material_filterInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        row_layout2 = QHBoxLayout()
        self.k_mm_Label = QLabel("Rauigkeit der Rohrleitungen in mm:")
        self.k_mm_Input = QLineEdit(str(config["k_mm"]))
        row_layout2.addWidget(self.k_mm_Label)
        row_layout2.addWidget(self.k_mm_Input)
        layout.addLayout(row_layout2)

        return layout

    def updateInputFieldsVisibility(self):
        """
        Update visibility of input fields based on checkbox state.
        """
        self.DiameterOpt_ckecked = self.DiameterOptCheckbox.isChecked()

        # Anzeige Optimierungsoptionen
        self.v_max_pipelabel.setVisible(self.DiameterOpt_ckecked)
        self.v_max_pipeInput.setVisible(self.DiameterOpt_ckecked)
        self.max_loss_label.setVisible(self.DiameterOpt_ckecked)
        self.max_loss_input.setVisible(self.DiameterOpt_ckecked)
        self.material_filterInput.setVisible(self.DiameterOpt_ckecked)
        self.k_mm_Label.setVisible(self.DiameterOpt_ckecked)
        self.k_mm_Input.setVisible(self.DiameterOpt_ckecked)

    def max_pressure_loss(self) -> float | None:
        """
        The pressure loss limit [Pa/m], ``None`` if the field is empty.

        :raises ValueError: If the field holds no number.
        """
        text = self.max_loss_input.text().strip().replace(",", ".")
        return float(text) if text else None

    def getValues(self):
        """
        Get current parameter values from input fields.

        :return: Dictionary containing diameter optimization parameters.
        :rtype: dict
        """
        return {
            "diameter_optimization_enabled": self.DiameterOptCheckbox.isChecked(),
            "v_max_pipe": float(self.v_max_pipeInput.text()),
            "max_pressure_loss_pa_per_m": self.max_pressure_loss(),
            "material_filter": self.material_filterInput.currentText(),
            "k_mm": float(self.k_mm_Input.text()),
        }
