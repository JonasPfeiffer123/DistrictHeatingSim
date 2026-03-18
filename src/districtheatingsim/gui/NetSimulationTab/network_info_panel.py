"""
Network Info Panel
==================

Scrollable KPI card panel for displaying district heating
network simulation results.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea,
                              QLabel, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


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
        "Wärmebedarfsdichte [MWh/(a*m)]",
        "Anschlussdichte [kW/m]",
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
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background-color: transparent; }"
        )

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

        if not hasattr(network_data, 'net'):
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

        results = network_data.calculate_results()

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
