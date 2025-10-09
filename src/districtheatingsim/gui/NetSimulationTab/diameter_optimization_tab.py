"""
Diameter Optimization Tab Module
================================

UI tab for pipe diameter optimization settings in district heating networks.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-11
"""

from PyQt6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QComboBox, QWidget,  QHBoxLayout, QCheckBox, QGroupBox

class DiameterOptimizationTab(QWidget):
    """
    Widget for configuring pipe diameter optimization parameters.
    """
    
    def __init__(self, dialog_config, parent=None):
        """
        Initialize diameter optimization tab.

        Parameters
        ----------
        dialog_config : dict
            Configuration data for dialog settings.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.dialog_config = dialog_config
        self.initUI()

    def initUI(self):
        """Initialize user interface components."""
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

        Returns
        -------
        QVBoxLayout
            Layout containing checkbox.
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

        Returns
        -------
        QVBoxLayout
            Layout containing input fields.
        """
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Eingaben zur Durchmesseroptimierung der Rohrleitungen:"))

        row_layout = QHBoxLayout()
        self.v_max_pipelabel = QLabel("Maximale Strömungsgeschwindigkeit Leitungen:")
        self.v_max_pipeInput = QLineEdit(str(self.dialog_config["diameter_optimization"]["v_max_pipe"]))
        row_layout.addWidget(self.v_max_pipelabel)
        row_layout.addWidget(self.v_max_pipeInput)
        layout.addLayout(row_layout)

        self.material_filterInput = QComboBox(self)
        self.material_filterInput.addItems(self.dialog_config["diameter_optimization"]["material_filter"])
        layout.addWidget(self.material_filterInput)
        self.material_filterInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        row_layout2 = QHBoxLayout()
        self.k_mm_Label = QLabel("Rauigkeit der Rohrleitungen:")
        self.k_mm_Input = QLineEdit(str(self.dialog_config["diameter_optimization"]["k_mm"]))
        row_layout2.addWidget(self.k_mm_Label)
        row_layout2.addWidget(self.k_mm_Input)
        layout.addLayout(row_layout2)
    
        return layout

    def updateInputFieldsVisibility(self):
        """Update visibility of input fields based on checkbox state."""
        self.DiameterOpt_ckecked = self.DiameterOptCheckbox.isChecked()

        # Anzeige Optimierungsoptionen
        self.v_max_pipelabel.setVisible(self.DiameterOpt_ckecked)
        self.v_max_pipeInput.setVisible(self.DiameterOpt_ckecked)
        self.material_filterInput.setVisible(self.DiameterOpt_ckecked)
        self.k_mm_Label.setVisible(self.DiameterOpt_ckecked)
        self.k_mm_Input.setVisible(self.DiameterOpt_ckecked)

    def getValues(self):
        """
        Get current parameter values from input fields.

        Returns
        -------
        dict
            Dictionary containing diameter optimization parameters.
        """
        return {
            "diameter_optimization_enabled": self.DiameterOptCheckbox.isChecked(),
            "v_max_pipe": float(self.v_max_pipeInput.text()),
            "material_filter": self.material_filterInput.currentText(),
            "k_mm": float(self.k_mm_Input.text())
        }