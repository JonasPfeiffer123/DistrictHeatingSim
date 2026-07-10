"""
Network Info Panel
==================

Scrollable KPI card panel for displaying district heating
network simulation results.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget


class NetworkInfoPanel(QWidget):
    """
    Scrollable panel of compact KPI cards built from NetworkGenerationData results.

    Call :meth:`update` whenever the simulation data changes.
    """

    _PRIORITY_KEYS = [
        "Anzahl angeschlossene Gebäude",
        "Anzahl Heizzentralen",
        "Jahresgesamtwärmebedarf Gebäude [MWh/a]",
        "max. Heizlast Gebäude [kW]",
        "Trassenlänge Wärmenetz [m]",
        "Trassenlänge ohne Hausanschlüsse [m]",
        "Wärmebedarfsdichte [MWh/(a*m)]",
        "Wärmebedarfsdichte ohne Hausanschlüsse [MWh/(a*m)]",
        "Anschlussdichte [kW/m]",
        "Anschlussdichte ohne Hausanschlüsse [kW/m]",
        "Jahreswärmeerzeugung [MWh]",
        "Pumpenstrom [MWh]",
        "Verteilverluste [MWh]",
        "rel. Verteilverluste [%]",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("📊 Netzwerk-Informationen")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setFixedHeight(35)
        title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 6px;
                background-color: #ecf0f1;
                border-radius: 3px;
                border-left: 3px solid #3498db;
            }
        """)
        layout.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setSpacing(2)
        self._cards_layout.setContentsMargins(2, 2, 2, 2)

        self._scroll.setWidget(self._cards_widget)
        layout.addWidget(self._scroll, 1)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def update(self, network_data):
        """
        Rebuild the card list from *network_data*.

        :param network_data: Simulation result data object.
        :type network_data: NetworkGenerationData
        """
        self._clear_cards()

        if not hasattr(network_data, "net"):
            lbl = QLabel("⚠️ Keine Netzdaten verfügbar")
            lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            lbl.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    background-color: #ffebee;
                    border: 1px solid #ef5350;
                    border-radius: 4px;
                    padding: 8px;
                }
            """)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cards_layout.addWidget(lbl)
            return

        # Render the KPIs computed by the producer (worker thread) or restored from a
        # saved project; only fall back to computing here for an older loaded project
        # whose JSON predates kpi_results (BACKLOG B2 — keep the panel a pure renderer).
        results = network_data.kpi_results
        if results is None:
            results = network_data.calculate_results()
        elif "Trassenlänge ohne Hausanschlüsse [m]" not in results and hasattr(network_data, "net"):
            # Older saved project (kpi_results predates the C34 without-house-connection
            # KPIs): augment from the net + persisted demand instead of recomputing
            # everything (a loaded project does not restore the demand time series).
            results = self._with_house_connection_kpis(dict(results), network_data.net)

        for key in self._PRIORITY_KEYS:
            if key in results and results[key] is not None:
                self._cards_layout.addWidget(self._make_card(key, results[key]))

        for key, value in results.items():
            if key not in self._PRIORITY_KEYS and value is not None:
                self._cards_layout.addWidget(self._make_card(key, value))

        self._cards_layout.addStretch()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _with_house_connection_kpis(results, net):
        """Add the C34 without-house-connection KPIs to a restored (older) results dict.

        Recomputes the trace length without house connections from the net and derives the
        matching densities from the persisted demand/peak, so a loaded project shows them
        without discarding the saved values.
        """
        from districtheatingsim.net_simulation_pandapipes.NetworkDataClass import NetworkGenerationData

        _, without = NetworkGenerationData.house_connection_route_lengths(net)
        results["Trassenlänge ohne Hausanschlüsse [m]"] = without
        demand = results.get("Jahresgesamtwärmebedarf Gebäude [MWh/a]")
        peak = results.get("max. Heizlast Gebäude [kW]")
        results["Wärmebedarfsdichte ohne Hausanschlüsse [MWh/(a*m)]"] = (
            (demand / without) if (demand and without) else None
        )
        results["Anschlussdichte ohne Hausanschlüsse [kW/m]"] = (peak / without) if (peak and without) else None
        return results

    def _clear_cards(self):
        while self._cards_layout.count():
            child = self._cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _make_card(self, title: str, value) -> QFrame:
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin: 1px;
            }
            QFrame:hover {
                border-color: #3498db;
                background-color: #f8f9fa;
            }
        """)

        row = QHBoxLayout(card)
        row.setSpacing(8)
        row.setContentsMargins(8, 4, 8, 4)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #2c3e50;")
        title_lbl.setWordWrap(True)
        row.addWidget(title_lbl, 2)

        if isinstance(value, float):
            value_text = f"{value:.1f}{'%' if '%' in title else ''}"
        else:
            value_text = str(value)

        val_lbl = QLabel(value_text)
        val_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        val_lbl.setStyleSheet("color: #27ae60;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(val_lbl, 1)

        return card
