"""
1D stratified thermal-storage dialog (hand-written: dynamic loss-model / fluid
sections and a collapsible advanced solver block). Moved verbatim from
``_04_technology_dialogs.py``; not yet schema-driven.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QLineEdit, QComboBox, QCheckBox, QGroupBox, QFormLayout, QWidget,
)


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

        self.name_input = QLineEdit(self._field("name", "Thermischer Netzspeicher"))
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

        self.T_charge_input = QLineEdit(self._field("T_charge", "90"))
        temp_layout.addRow("Generator charge temp (°C):", self.T_charge_input)

        self.T_discharge_return_input = QLineEdit(self._field("T_discharge_return", "50"))
        temp_layout.addRow("Network return temp (°C):", self.T_discharge_return_input)

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

        self.lambda_eff_factor_input = QLineEdit(self._field("lambda_eff_factor", "5.0"))
        solver_layout.addRow("Effective conductivity factor (λ_eff):", self.lambda_eff_factor_input)

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
            "lambda_eff_factor": float(self.lambda_eff_factor_input.text()),
            "spez_Investitionskosten": float(self.spez_cost_input.text()),
            "hours": 8760,
            "T_charge": float(self.T_charge_input.text()),
            "T_discharge_return": float(self.T_discharge_return_input.text()),
        }
