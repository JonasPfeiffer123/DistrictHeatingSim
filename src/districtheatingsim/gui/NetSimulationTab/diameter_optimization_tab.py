"""
Filename: diameter_optimization_tab.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-02-11
Description: Contains the DiameterOptimizationTab class.
"""

from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QComboBox, QWidget,  QHBoxLayout, QCheckBox, QGroupBox

class DiameterOptimizationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
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
        layout = QVBoxLayout()
        self.DiameterOptCheckbox = QCheckBox("Durchmesser optimieren.")
        layout.addWidget(self.DiameterOptCheckbox)
        self.DiameterOptCheckbox.setChecked(True)
        self.DiameterOptCheckbox.stateChanged.connect(self.updateInputFieldsVisibility)
        return layout

    def createDiameterOptInput(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Eingaben zur Durchmesseroptimierung der Rohrleitungen:"))

        row_layout = QHBoxLayout()
        self.v_max_pipelabel = QLabel("Maximale Strömungsgeschwindigkeit Leitungen:")
        self.v_max_pipeInput = QLineEdit("1.0")
        row_layout.addWidget(self.v_max_pipelabel)
        row_layout.addWidget(self.v_max_pipeInput)
        layout.addLayout(row_layout)

        self.material_filterInput = QComboBox(self)
        self.material_filterInput.addItems(["KMR", "FL", "HK"])
        layout.addWidget(self.material_filterInput)
        self.material_filterInput.currentIndexChanged.connect(self.updateInputFieldsVisibility)

        self.k_mm_Label = QLabel("Rauigkeit der Rohrleitungen:")
        self.k_mm_Input = QLineEdit("0.1")
        row_layout.addWidget(self.k_mm_Label)
        row_layout.addWidget(self.k_mm_Input)
        layout.addLayout(row_layout)
    
        return layout

    def updateInputFieldsVisibility(self):
        """
        Updates the visibility of input fields based on the selected options.
        """
        
        self.DiameterOpt_ckecked = self.DiameterOptCheckbox.isChecked()

        # Anzeige Optimierungsoptionen
        self.v_max_pipelabel.setVisible(self.DiameterOpt_ckecked)
        self.v_max_pipeInput.setVisible(self.DiameterOpt_ckecked)
        self.material_filterInput.setVisible(self.DiameterOpt_ckecked)
