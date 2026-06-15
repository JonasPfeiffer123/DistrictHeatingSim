"""
Results Tab Module
==================

:author: Dipl.-Ing. (FH) Jonas Pfeiffer

Displaying results of energy system calculations with diagrams and tables, including stack plots, pie charts, and result tables.
"""

import sys

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from districtheatingsim.gui.EnergySystemTab._10_utilities import CheckableComboBox, CollapsibleHeader

# Month labels and starts for a full year (8760 h)
_MONTH_NAMES = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
_MONTH_STARTS = [0, 744, 1416, 2160, 2880, 3624, 4344, 5088, 5832, 6552, 7296, 8016]


def _apply_month_xticks(ax, n_steps: int):
    """Replace integer hour labels with abbreviated month names when n_steps ≥ 8000."""
    if n_steps >= 8000:
        valid = [(s, m) for s, m in zip(_MONTH_STARTS, _MONTH_NAMES, strict=False) if s < n_steps]
        ax.set_xticks([s for s, _ in valid])
        ax.set_xticklabels([m for _, m in valid], fontsize=9)
    else:
        step = max(1, n_steps // 10)
        ax.set_xticks(np.arange(0, n_steps + step, step))


def _plot_storage_panels(
    fig,
    hours,
    net_flow,
    soc,
    T_top,
    T_middle,
    T_bottom,
    Q_loss,
    title: str,
    n_steps: int,
    min_fill: float | None = None,
    max_fill: float | None = None,
    gen_profile: np.ndarray | None = None,
    load_profile: np.ndarray | None = None,
):
    """
    Draw the 4-panel storage overview into *fig*.

    Panel 1 – load vs generator output + net buffer flow (optional, when gen/load given)
    Panel 2 – SOC [%] with optional min/max fill lines
    Panel 3 – T_top / T_middle / T_bottom
    Panel 4 – Heat loss [kW]
    """
    fig.clear()
    ax1, ax2, ax3, ax4 = fig.subplots(4, 1, sharex=True)

    # Panel 1 – net storage flow (+ optional load/generator overlay)
    if gen_profile is not None and load_profile is not None:
        ax1.fill_between(hours, load_profile, alpha=0.2, color="gray", label="Wärmebedarf (kW)")
        ax1.plot(hours, gen_profile, color="orange", linewidth=0.7, label="Erzeuger (kW)")
    ax1.fill_between(hours, net_flow, where=(net_flow > 0), color="steelblue", alpha=0.7, label="Beladung (kW)")
    ax1.fill_between(hours, net_flow, where=(net_flow < 0), color="tomato", alpha=0.7, label="Entladung (kW)")
    ax1.axhline(0, color="black", linewidth=0.5)
    ax1.set_ylabel("Speicherfluss (kW)")
    ax1.legend(fontsize=7, loc="upper right")
    ax1.grid(True, alpha=0.3)

    # Panel 2 – SOC
    ax2.fill_between(hours, soc, alpha=0.35, color="steelblue")
    ax2.plot(hours, soc, color="steelblue", linewidth=0.8, label="SOC (%)")
    if min_fill is not None:
        ax2.axhline(
            min_fill * 100, color="red", linewidth=0.9, linestyle="--", label=f"min_fill {min_fill * 100:.0f} %"
        )
    if max_fill is not None:
        ax2.axhline(
            max_fill * 100, color="green", linewidth=0.9, linestyle="--", label=f"max_fill {max_fill * 100:.0f} %"
        )
    ax2.set_ylabel("SOC (%)")
    ax2.set_ylim(0, 100)
    ax2.legend(fontsize=7, loc="upper right")
    ax2.grid(True, alpha=0.3)

    # Panel 3 – temperatures
    ax3.plot(hours, T_top, color="red", linewidth=0.8, label="T oben (°C)")
    ax3.plot(hours, T_middle, color="orange", linewidth=0.8, label="T mitte (°C)")
    ax3.plot(hours, T_bottom, color="royalblue", linewidth=0.8, label="T unten (°C)")
    ax3.set_ylabel("Temperatur (°C)")
    ax3.legend(fontsize=7, loc="upper right")
    ax3.grid(True, alpha=0.3)

    # Panel 4 – heat loss
    ax4.fill_between(hours, Q_loss, alpha=0.5, color="orange")
    ax4.plot(hours, Q_loss, color="darkorange", linewidth=0.7, label="Wärmeverluste (kW)")
    ax4.set_ylabel("Verluste (kW)")
    ax4.legend(fontsize=7, loc="upper right")
    ax4.grid(True, alpha=0.3)

    _apply_month_xticks(ax4, n_steps)

    fig.suptitle(title, fontsize=10)
    fig.tight_layout()


class ResultsTab(QWidget):
    """
    A QWidget subclass representing the ResultsTab.

    Attributes:
        data_added (pyqtSignal): A signal that emits data as an object.
        data_manager (DataManager): An instance of the DataManager class for managing data.
        parent (QWidget): The parent widget.
        results (dict): A dictionary to store results.
        selected_variables (list): A list of selected variables for plotting.
    """

    data_added = pyqtSignal(object)  # Signal, das Daten als Objekt überträgt

    def __init__(self, data_manager, parent=None):
        """
        Initializes the ResultsTab.

        :param data_manager: The data manager
        :type data_manager: DataManager
        :param parent: The parent widget
        :type parent: QWidget or None
        """
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent = parent
        self.results = {}
        self.selected_variables = []
        self.energy_system = None

        # Dynamic buffer storage section widgets (rebuilt on each updateResults call)
        self._buffer_section_widgets: list[QWidget] = []

        self.data_manager.project_folder_changed.connect(self.updateDefaultPath)
        self.updateDefaultPath(self.data_manager.variant_folder)

        self.initUI()

    def updateDefaultPath(self, new_base_path):
        """
        Updates the default base path.

        :param new_base_path: The new base path
        :type new_base_path: str
        """
        self.base_path = new_base_path

    def initUI(self):
        """
        Initializes the UI components of the ResultsTab.
        """
        self.mainLayout = QVBoxLayout(self)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)

        self.setupDiagrams()
        self.setupCollapsibleResultsSections()

        self.scrollArea.setWidget(self.scrollWidget)
        self.mainLayout.addWidget(self.scrollArea)
        self.setLayout(self.mainLayout)

    def setupDiagrams(self):
        """
        Sets up the collapsible diagrams for the ResultsTab.
        """

        # Layout for variable selection (ComboBox and Checkbox)
        self.variableSelectionLayout = QHBoxLayout()
        self.variableComboBox = CheckableComboBox()
        self.variableComboBox.view().pressed.connect(self.updateSelectedVariables)

        self.secondYAxisCheckBox = QCheckBox("Second y-Axis")
        self.secondYAxisCheckBox.stateChanged.connect(self.updateSelectedVariables)

        self.variableSelectionLayout.addWidget(self.variableComboBox)
        self.variableSelectionLayout.addWidget(self.secondYAxisCheckBox)

        # First Diagram (Stackplot and Line Plot)
        self.stackPlotFigure = Figure(figsize=(8, 6))
        self.stackPlotCanvas = FigureCanvas(self.stackPlotFigure)
        self.stackPlotCanvas.setMinimumSize(500, 500)
        self.toolbar1 = NavigationToolbar(self.stackPlotCanvas, self)
        self.diagram1_widget = QWidget()
        diagram1_layout = QVBoxLayout(self.diagram1_widget)
        diagram1_layout.addLayout(self.variableSelectionLayout)
        diagram1_layout.addWidget(self.stackPlotCanvas)
        diagram1_layout.addWidget(self.toolbar1)
        self.diagram1_section = CollapsibleHeader("Jahresganglinie Diagramm", self.diagram1_widget)
        self.scrollLayout.addWidget(self.diagram1_section)

        # Second Diagram (Pie Chart)
        self.pieChartFigure = Figure(figsize=(6, 6))
        self.pieChartCanvas = FigureCanvas(self.pieChartFigure)
        self.pieChartCanvas.setMinimumSize(500, 500)
        self.pieCharttoolbar = NavigationToolbar(self.pieChartCanvas, self)
        self.diagram2_widget = QWidget()
        diagram2_layout = QVBoxLayout(self.diagram2_widget)
        diagram2_layout.addWidget(self.pieChartCanvas)
        diagram2_layout.addWidget(self.pieCharttoolbar)
        self.diagram2_section = CollapsibleHeader("Anteile Wärmeerzeugung Diagramm", self.diagram2_widget)
        self.scrollLayout.addWidget(self.diagram2_section)

        # Third Diagram – network storage (shown only when a ThermalStorageAdapter is present)
        self.storageFigure = Figure(figsize=(10, 8))
        self.storageCanvas = FigureCanvas(self.storageFigure)
        self.storageCanvas.setMinimumSize(500, 600)
        self.storageToolbar = NavigationToolbar(self.storageCanvas, self)
        self.diagram3_widget = QWidget()
        diagram3_layout = QVBoxLayout(self.diagram3_widget)
        diagram3_layout.addWidget(self.storageCanvas)
        diagram3_layout.addWidget(self.storageToolbar)
        self.diagram3_section = CollapsibleHeader("Thermischer Netzspeicher – Betrieb", self.diagram3_widget)
        self.diagram3_section.setVisible(False)
        self.scrollLayout.addWidget(self.diagram3_section)

        # Placeholder widget that holds all dynamic buffer-storage sections.
        # It sits between the network storage section and the results tables so
        # that newly discovered buffer storages are always inserted in the right place.
        self._buffer_container = QWidget()
        self._buffer_container_layout = QVBoxLayout(self._buffer_container)
        self._buffer_container_layout.setContentsMargins(0, 0, 0, 0)
        self._buffer_container_layout.setSpacing(4)
        self.scrollLayout.addWidget(self._buffer_container)

    def setupCollapsibleResultsSections(self):
        """
        Sets up the collapsible sections for displaying results tables.
        """

        # First Table (Results Table)
        self.setupResultsTable()

        self.table1_widget = QWidget()
        table1_layout = QVBoxLayout(self.table1_widget)
        table1_layout.addWidget(self.resultsTable)
        self.table1_section = CollapsibleHeader("Ergebnisse Erzeugung", self.table1_widget)
        self.scrollLayout.addWidget(self.table1_section)

        # Second Table (Additional Results Table)
        self.setupAdditionalResultsTable()

        self.table2_widget = QWidget()
        table2_layout = QVBoxLayout(self.table2_widget)
        table2_layout.addWidget(self.additionalResultsTable)
        self.table2_section = CollapsibleHeader("Ergebnisse Wirtschaftlichkeit", self.table2_widget)
        self.scrollLayout.addWidget(self.table2_section)

    def addLabel(self, text):
        """
        Adds a label to the layout.

        :param text: The text for the label
        :type text: str
        """
        label = QLabel(text)
        self.scrollLayout.addWidget(label)

    def setupResultsTable(self):
        """
        Sets up the results table with additional columns for operational hours and starts.
        """
        self.resultsTable = QTableWidget()
        self.resultsTable.setColumnCount(9)
        self.resultsTable.setHorizontalHeaderLabels(
            [
                "Technologie",
                "Wärmemenge (MWh)",
                "Anzahl Betriebsstunden",
                "Anzahl Starts",
                "Betriebsstunden/Start",
                "Kosten (€/MWh)",
                "Anteil (%)",
                "CO2-eq (t_CO2/MWh_th)",
                "Primärenergiefaktor",
            ]
        )
        self.resultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def setupAdditionalResultsTable(self):
        """
        Sets up the additional results table.
        """
        self.additionalResultsTable = QTableWidget()
        self.additionalResultsTable.setColumnCount(3)
        self.additionalResultsTable.setHorizontalHeaderLabels(["Ergebnis", "Wert", "Einheit"])
        self.additionalResultsTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def adjustTableSize(self, table):
        """
        Adjusts the size of the table to fit its contents.

        :param table: The table to adjust
        :type table: QTableWidget
        """
        header_height = table.horizontalHeader().height()
        rows_height = sum([table.rowHeight(i) for i in range(table.rowCount())])
        table.setFixedHeight(header_height + rows_height)

    def updateResults(self, energy_system):
        """
        Updates the results in the ResultsTab.

        :param energy_system: The energy system instance containing results
        :type energy_system: EnergySystem
        """
        self.energy_system = energy_system

        self.showResultsInTable()
        self.showAdditionalResultsTable()
        self.plotResults()
        self.updatePieChart()
        self.plotStorage()
        self.plotBufferStorages()

    def showResultsInTable(self):
        """
        Displays the results in the results table, including calculated operational metrics.
        Resets the table rows before populating to avoid leftover rows from previous calculations.
        """

        results = self.energy_system.results

        self.resultsTable.setRowCount(0)
        self.resultsTable.setRowCount(len(results["techs"]))

        for i, (tech, wärmemenge, wgk, anteil, spec_emission, primary_energy, wärmeleistung) in enumerate(
            zip(
                results["techs"],
                results["Wärmemengen"],
                results["WGK"],
                results["Anteile"],
                results["specific_emissions_L"],
                results["primärenergie_L"],
                results["Wärmeleistung_L"],
                strict=False,
            )
        ):
            if not isinstance(wärmeleistung, (list, np.ndarray)):
                wärmeleistung = [wärmeleistung]
            wärmeleistung = np.array(wärmeleistung)

            betriebsstunden = np.count_nonzero(wärmeleistung)
            starts = np.sum((wärmeleistung[:-1] == 0) & (wärmeleistung[1:] > 0))
            betriebsstunden_pro_start = betriebsstunden / starts if starts > 0 else 0

            self.resultsTable.setItem(i, 0, QTableWidgetItem(tech))
            self.resultsTable.setItem(i, 1, QTableWidgetItem(f"{np.sum(wärmemenge):.2f}"))
            self.resultsTable.setItem(i, 2, QTableWidgetItem(f"{betriebsstunden}"))
            self.resultsTable.setItem(i, 3, QTableWidgetItem(f"{starts}"))
            self.resultsTable.setItem(i, 4, QTableWidgetItem(f"{betriebsstunden_pro_start:.2f}"))
            self.resultsTable.setItem(i, 5, QTableWidgetItem(f"{wgk:.2f}"))
            self.resultsTable.setItem(i, 6, QTableWidgetItem(f"{anteil * 100:.2f}"))
            self.resultsTable.setItem(i, 7, QTableWidgetItem(f"{spec_emission:.4f}"))
            self.resultsTable.setItem(i, 8, QTableWidgetItem(f"{primary_energy / np.sum(wärmemenge):.4f}"))

        self.resultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.resultsTable)

    def showAdditionalResultsTable(self):
        """
        Displays the additional results in the additional results table.
        """
        self.waerme_ges_kW, self.strom_wp_kW = (
            np.sum(self.energy_system.results["waerme_ges_kW"]),
            np.sum(self.energy_system.results["strom_wp_kW"]),
        )
        if "Summe Infrastruktur" in self.parent.costTab.data.index:
            self.WGK_Infra = (
                self.parent.costTab.data.at["Summe Infrastruktur", "Annuität"]
                / self.energy_system.results["Jahreswärmebedarf"]
            )
            if self.energy_system.economic_parameters["subsidy_eligibility"] == "Ja":
                self.WGK_Infra = (
                    self.parent.costTab.data.at["Summe Infrastruktur", "Annuität"] * 0.6
                ) / self.energy_system.results["Jahreswärmebedarf"]
        else:
            self.WGK_Infra = 0
        self.wgk_heat_pump_electricity = (
            (self.strom_wp_kW / 1000) * self.parent.economic_parameters["electricity_price"]
        ) / ((self.strom_wp_kW + self.waerme_ges_kW) / 1000)
        self.WGK_Gesamt = self.energy_system.results["WGK_Gesamt"] + self.WGK_Infra + self.wgk_heat_pump_electricity

        data = [
            ("Jahreswärmebedarf", round(self.energy_system.results["Jahreswärmebedarf"], 1), "MWh"),
            ("Stromerzeugung", round(self.energy_system.results["Strommenge"], 2), "MWh"),
            ("Strombedarf", round(self.energy_system.results["Strombedarf"], 2), "MWh"),
            ("Wärmegestehungskosten Erzeugeranlagen", round(self.energy_system.results["WGK_Gesamt"], 2), "€/MWh"),
            ("Wärmegestehungskosten Netzinfrastruktur", round(self.WGK_Infra, 2), "€/MWh"),
            ("Wärmegestehungskosten dezentrale Wärmepumpen", round(self.wgk_heat_pump_electricity, 2), "€/MWh"),
            ("Wärmegestehungskosten Gesamt", round(self.WGK_Gesamt, 2), "€/MWh"),
            (
                "spez. CO2-Emissionen Wärme",
                round(self.energy_system.results["specific_emissions_Gesamt"], 4),
                "t_CO2/MWh_th",
            ),
            (
                "CO2-Emissionen Wärme",
                round(
                    self.energy_system.results["specific_emissions_Gesamt"]
                    * self.energy_system.results["Jahreswärmebedarf"],
                    2,
                ),
                "t_CO2",
            ),
            ("Primärenergiefaktor", round(self.energy_system.results["primärenergiefaktor_Gesamt"], 4), "-"),
        ]

        self.additionalResultsTable.setRowCount(len(data))

        for i, (description, value, unit) in enumerate(data):
            self.additionalResultsTable.setItem(i, 0, QTableWidgetItem(description))
            self.additionalResultsTable.setItem(i, 1, QTableWidgetItem(str(value)))
            self.additionalResultsTable.setItem(i, 2, QTableWidgetItem(unit))

        self.additionalResultsTable.resizeColumnsToContents()
        self.adjustTableSize(self.additionalResultsTable)

    def plotResults(self):
        """
        Plots the results in the diagrams.
        """
        extracted_data, initial_vars = self.energy_system.getInitialPlotData()

        model = self.variableComboBox.model()
        combo_items = [model.item(i).text() for i in range(model.rowCount())]
        if set(extracted_data.keys()) != set(combo_items):
            self.variableComboBox.clear()
            self.variableComboBox.addItems(extracted_data.keys())
            self.variableComboBox.addItem("Last_L")

        for var in initial_vars:
            self.variableComboBox.setItemChecked(var, True)

        self.selected_variables = self.variableComboBox.checkedItems()
        self.stackPlotFigure.clear()
        self.energy_system.plot_stack_plot(
            figure=self.stackPlotFigure,
            selected_vars=self.selected_variables,
            second_y_axis=self.secondYAxisCheckBox.isChecked(),
        )
        self.stackPlotCanvas.draw()

    def updateSelectedVariables(self):
        """
        Updates the selected variables and re-plots the diagram.
        """
        self.selected_variables = self.variableComboBox.checkedItems()
        self.stackPlotFigure.clear()
        self.energy_system.plot_stack_plot(
            figure=self.stackPlotFigure,
            selected_vars=self.selected_variables,
            second_y_axis=self.secondYAxisCheckBox.isChecked(),
        )
        self.stackPlotCanvas.draw()

    def plotStorage(self):
        """
        Draws the 4-panel network storage overview plot.
        Hidden when no ThermalStorageAdapter is attached to the energy system.
        """
        storage = getattr(self.energy_system, "storage", None)
        if storage is None:
            self.diagram3_section.setVisible(False)
            return

        self.diagram3_section.setVisible(True)
        n_steps = len(storage._soc)
        hours = np.arange(n_steps)
        net = storage._Q_net_storage_flow

        _plot_storage_panels(
            fig=self.storageFigure,
            hours=hours,
            net_flow=net,
            soc=storage._soc * 100,
            T_top=storage._T_supply,
            T_middle=storage._T_middle,
            T_bottom=storage._T_return,
            Q_loss=storage.Q_loss,
            title=f"Thermischer Netzspeicher – {storage.name}",
            n_steps=n_steps,
        )
        self.storageCanvas.draw()

    def plotBufferStorages(self):
        """
        Dynamically create/update one 4-panel collapsible section per generator
        that has an active buffer storage (CHP, BiomassBoiler with speicher_aktiv=True).
        Old sections are destroyed and rebuilt on each call.
        """
        # Remove all previously created buffer sections from the container
        for w in self._buffer_section_widgets:
            self._buffer_container_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
        self._buffer_section_widgets.clear()

        techs_with_buffer = [
            tech for tech in self.energy_system.technologies if getattr(tech, "buffer", None) is not None
        ]

        for tech in techs_with_buffer:
            buf = tech.buffer

            # Guard: history must cover the full simulation (may be empty on first run)
            if not buf.soc_history:
                continue

            n_steps = len(buf.soc_history)
            hours = np.arange(n_steps)
            soc = np.array(buf.soc_history) * 100.0
            T_top = np.array(buf.T_top_history)
            T_mid = np.array(buf.T_middle_history)
            T_bot = np.array(buf.T_bottom_history)
            Q_loss = np.array(buf.Q_loss_history)
            Q_net = np.array(buf.Q_net_history)  # + = charge, − = discharge

            # Generator output profile (from results) + load profile
            gen_profile = None
            load_profile = None
            results = self.energy_system.results
            if tech.name in results.get("techs", []):
                idx = list(results["techs"]).index(tech.name)
                gen_arr = results["Wärmeleistung_L"][idx]
                if len(gen_arr) == n_steps:
                    gen_profile = gen_arr
            load_arr = self.energy_system.load_profile
            if len(load_arr) == n_steps:
                load_profile = load_arr

            # Build the figure
            fig = Figure(figsize=(10, 8))
            canvas = FigureCanvas(fig)
            canvas.setMinimumSize(500, 600)
            toolbar = NavigationToolbar(canvas, self)

            _plot_storage_panels(
                fig=fig,
                hours=hours,
                net_flow=Q_net,
                soc=soc,
                T_top=T_top,
                T_middle=T_mid,
                T_bottom=T_bot,
                Q_loss=Q_loss,
                title=f"Anlagenspezifischer Pufferspeicher – {tech.name}  "
                f"(V = {buf.volume:.0f} m³, Kapazität ≈ {buf.get_capacity_kwh():.0f} kWh)",
                n_steps=n_steps,
                min_fill=getattr(tech, "min_fill", None),
                max_fill=getattr(tech, "max_fill", None),
                gen_profile=gen_profile,
                load_profile=load_profile,
            )
            canvas.draw()

            # Wrap in a collapsible section
            inner = QWidget()
            inner_layout = QVBoxLayout(inner)
            inner_layout.addWidget(canvas)
            inner_layout.addWidget(toolbar)

            section = CollapsibleHeader(f"Anlagenspezifischer Pufferspeicher – {tech.name}", inner)
            self._buffer_container_layout.addWidget(section)
            self._buffer_section_widgets.append(section)

    def updatePieChart(self):
        """
        Updates the pie chart with results from the EnergySystem.
        """
        self.pieChartFigure.clear()
        self.energy_system.plot_pie_chart(self.pieChartFigure)
        self.pieChartCanvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    data_manager = None
    main = ResultsTab(data_manager)
    main.show()
    sys.exit(app.exec())
