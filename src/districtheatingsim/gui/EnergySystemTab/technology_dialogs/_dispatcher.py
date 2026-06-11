"""
TechInputDialog — the public entry point that routes a technology type to its
sub-dialog and wraps it with OK/Cancel buttons.

Dispatch logic (prefix matching, order) is preserved verbatim from the original
``_04_technology_dialogs.py``.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from districtheatingsim.gui.EnergySystemTab.technology_dialogs._combustion import (
    BiomassBoilerDialog,
    CHPDialog,
    HolzgasCHPDialog,
)
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._geothermal import GeothermalDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._heat_pump import (
    AqvaHeatDialog,
    RiverHeatPumpDialog,
)
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._simple import (
    GasBoilerDialog,
    PowerToHeatDialog,
    WasteHeatPumpDialog,
)
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._solar import SolarThermalDialog
from districtheatingsim.gui.EnergySystemTab.technology_dialogs._storage import ThermalStorage1DDialog


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
        elif self.tech_type.startswith("Thermischer Netzspeicher"):
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
