"""
Pipe Config Table
=================

QWidget wrapping a QTableWidget for editing district heating pipe parameters.
Emits :attr:`pipe_highlight_requested` when the user selects a row, so the
network plot widget can highlight the corresponding pipe.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging

import pandapipes as pp
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from districtheatingsim.gui.utilities import NoScrollComboBox
from districtheatingsim.net_simulation_pandapipes.pipe_std_types import (
    isoplus_std_type_names,
    resolve_pipe_u_w_per_m2k,
)

# Background tint for a pipe row whose values were edited since the last calculation.
_CHANGED_ROW_COLOR = "#fff3cd"


class PipeConfigTable(QWidget):
    """
    Pipe configuration table with editable std_type, diameter, and roughness.

    Call :meth:`populate` with a ``NetworkGenerationData`` instance to fill
    the table; call :meth:`select_pipe` to programmatically select a row.

    Emits :attr:`pipe_highlight_requested` with the pipe index whenever the
    user selects a row.
    """

    pipe_highlight_requested = pyqtSignal(int)  # pipe index

    _COLUMNS = ["Index", "Name", "Von", "Nach", "Länge [m]", "Std-Typ", "DN [mm]", "k [mm]"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._net_data = None
        self._original_pipe_df = None
        # Per-pipe snapshot of the editable values as of the last calculation; rows whose
        # current values differ from this are highlighted. Reset on every _fill_table().
        self._baseline = {}
        self._init_ui()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def populate(self, net_data):
        """
        Populate the table from *net_data.net.pipe*.

        :param net_data: Simulation result data with ``net`` attribute.
        :type net_data: NetworkGenerationData
        """
        if net_data is None or not hasattr(net_data, "net"):
            return

        self._net_data = net_data
        if self._original_pipe_df is None:
            self._original_pipe_df = net_data.net.pipe.copy()

        self._fill_table()
        self.show()

    def select_pipe(self, pipe_idx: int):
        """
        Programmatically select the row for *pipe_idx*.

        :param pipe_idx: Pipe index to select.
        :type pipe_idx: int
        """
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and int(item.text()) == pipe_idx:
                self._table.blockSignals(True)
                self._table.selectRow(row)
                self._table.scrollToItem(item)
                self._table.blockSignals(False)
                break

    def apply_changes_to_net(self):
        """
        Write all editable table values back to *net_data.net.pipe*.
        """
        if self._net_data is None or not hasattr(self._net_data, "net"):
            return

        net = self._net_data.net
        try:
            pipe_std_types = pp.std_types.available_std_types(net, "pipe")
        except Exception:
            pipe_std_types = None

        for row in range(self._table.rowCount()):
            pipe_idx = int(self._table.item(row, 0).text())

            combo = self._table.cellWidget(row, 5)
            if combo:
                std_type = combo.currentText()
                if std_type:
                    net.pipe.at[pipe_idx, "std_type"] = std_type
                    if pipe_std_types is not None and std_type in pipe_std_types.index:
                        try:
                            net.pipe.at[pipe_idx, "u_w_per_m2k"] = resolve_pipe_u_w_per_m2k(
                                pipe_std_types.loc[std_type]
                            )
                        except ValueError:
                            # std-type carries no heat-loss value (e.g. an uninsulated
                            # type); keep the pipe's existing u_w_per_m2k.
                            logging.warning(
                                "No heat-loss value for std-type '%s'; keeping existing u for pipe %d",
                                std_type,
                                pipe_idx,
                            )

            diameter_item = self._table.item(row, 6)
            if diameter_item:
                try:
                    net.pipe.at[pipe_idx, "inner_diameter_mm"] = float(diameter_item.text())
                except ValueError:
                    pass

            k_item = self._table.item(row, 7)
            if k_item:
                try:
                    net.pipe.at[pipe_idx, "k_mm"] = float(k_item.text())
                except ValueError:
                    pass

        logging.info("Applied all pipe table changes to network")

    def restore_defaults(self):
        """
        Restore pipe parameters to the snapshot taken at first :meth:`populate`.
        """
        if self._net_data is None or self._original_pipe_df is None:
            QMessageBox.warning(
                self,
                "Keine Originaldaten",
                "Es sind keine Originaldaten zum Wiederherstellen vorhanden.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Standardwerte wiederherstellen",
            "Möchten Sie alle Änderungen an den Rohrleitungsparametern verwerfen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._net_data.net.pipe = self._original_pipe_df.copy()
            self._fill_table()
            logging.info("Restored original pipe parameters")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)

        title = QLabel("🔧 Rohrleitungs-Konfiguration")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 6px;
                background-color: #ecf0f1;
                border-radius: 3px;
                border-left: 3px solid #e74c3c;
            }
        """)
        layout.addWidget(title)

        self._table = QTableWidget()
        self._table.setMinimumHeight(400)
        self._table.setMaximumHeight(600)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                alternate-background-color: #f9f9f9;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: 1px solid #2c3e50;
            }
        """)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        restore_btn = QPushButton("Standardwerte wiederherstellen")
        restore_btn.clicked.connect(self.restore_defaults)
        btn_row.addWidget(restore_btn)
        btn_row.addStretch()

        self._recalc_btn = QPushButton("Netz neu berechnen")
        self._recalc_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        btn_row.addWidget(self._recalc_btn)
        layout.addLayout(btn_row)

        self.hide()

    def _fill_table(self):
        net = self._net_data.net

        self._table.blockSignals(True)
        self._table.setColumnCount(len(self._COLUMNS))
        self._table.setHorizontalHeaderLabels(self._COLUMNS)
        self._table.setRowCount(len(net.pipe))
        self._table.verticalHeader().setDefaultSectionSize(50)

        try:
            pipe_std_types = pp.std_types.available_std_types(net, "pipe")
        except Exception:
            pipe_std_types = None

        for row, (idx, pipe_data) in enumerate(net.pipe.iterrows()):

            def ro(text):
                item = QTableWidgetItem(str(text))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return item

            self._table.setItem(row, 0, ro(idx))
            self._table.setItem(row, 1, ro(pipe_data.get("name", f"Pipe {idx}")))
            self._table.setItem(row, 2, ro(f"J{pipe_data['from_junction']}"))
            self._table.setItem(row, 3, ro(f"J{pipe_data['to_junction']}"))
            self._table.setItem(row, 4, ro(f"{pipe_data['length_km'] * 1000:.1f}"))

            combo = NoScrollComboBox()
            combo.setMinimumHeight(25)
            combo.setStyleSheet("""
                QComboBox {
                    padding: 4px 8px;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                    background-color: white;
                    color: black;
                    font-size: 11pt;
                }
                QComboBox:focus { border: 2px solid #3498db; }
                QComboBox::drop-down { border: none; width: 20px; }
                QComboBox QAbstractItemView {
                    background-color: white;
                    color: black;
                    selection-background-color: #3498db;
                    selection-color: white;
                }
            """)
            # Only ISOPLUS bonded-steel pipes are relevant for district heating.
            isoplus_names = isoplus_std_type_names(pipe_std_types)
            if isoplus_names:
                combo.addItems(isoplus_names)
                current = pipe_data.get("std_type", "")
                if current and current in isoplus_names:
                    combo.setCurrentText(current)
                else:
                    combo.setCurrentIndex(0)
            combo.currentTextChanged.connect(lambda text, r=row: self._on_std_type_changed(r, text))
            self._table.setCellWidget(row, 5, combo)

            self._table.setItem(row, 6, QTableWidgetItem(f"{pipe_data.get('inner_diameter_mm', 0):.1f}"))
            self._table.setItem(row, 7, QTableWidgetItem(f"{pipe_data.get('k_mm', 0.1):.2f}"))

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(0, 60)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(2, 60)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(3, 60)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(4, 90)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(5, 200)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(6, 80)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(7, 80)

        # This freshly-filled state is the "last calculation" baseline; no row is highlighted.
        self._capture_baseline()

        self._table.blockSignals(False)

    # ------------------------------------------------------------------
    # Change highlighting (rows edited since the last calculation)
    # ------------------------------------------------------------------

    def _row_values(self, row):
        """Return the editable values of *row* as displayed strings: (std_type, DN, k)."""
        combo = self._table.cellWidget(row, 5)
        dn_item = self._table.item(row, 6)
        k_item = self._table.item(row, 7)
        return (
            combo.currentText() if combo else "",
            dn_item.text() if dn_item else "",
            k_item.text() if k_item else "",
        )

    def _capture_baseline(self):
        """Snapshot every row's current values as the baseline (clears all highlights)."""
        self._baseline = {}
        for row in range(self._table.rowCount()):
            idx_item = self._table.item(row, 0)
            if idx_item is not None:
                self._baseline[int(idx_item.text())] = self._row_values(row)

    def _update_row_highlight(self, row):
        """Tint *row* if its current values differ from the baseline, else clear the tint."""
        idx_item = self._table.item(row, 0)
        if idx_item is None:
            return
        pipe_idx = int(idx_item.text())
        changed = self._baseline.get(pipe_idx) != self._row_values(row)
        brush = QBrush(QColor(_CHANGED_ROW_COLOR)) if changed else QBrush()

        # setBackground emits itemChanged; block signals to avoid re-entering the handlers.
        self._table.blockSignals(True)
        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item is not None:
                item.setBackground(brush)
        self._table.blockSignals(False)

    def _on_row_selected(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        pipe_idx = int(self._table.item(rows[0].row(), 0).text())
        self.pipe_highlight_requested.emit(pipe_idx)

    def _on_std_type_changed(self, row: int, new_std_type: str):
        if not new_std_type or self._net_data is None:
            return

        net = self._net_data.net
        pipe_idx = int(self._table.item(row, 0).text())

        try:
            pipe_std_types = pp.std_types.available_std_types(net, "pipe")
            props = pipe_std_types.loc[new_std_type]
            net.pipe.at[pipe_idx, "std_type"] = new_std_type
            net.pipe.at[pipe_idx, "inner_diameter_mm"] = props["inner_diameter_mm"]
            net.pipe.at[pipe_idx, "u_w_per_m2k"] = resolve_pipe_u_w_per_m2k(props)

            self._table.blockSignals(True)
            item = self._table.item(row, 6)
            if item:
                item.setText(f"{props['inner_diameter_mm']:.1f}")
            self._table.blockSignals(False)

            self._update_row_highlight(row)
            logging.info(f"Pipe {pipe_idx}: std_type changed to {new_std_type}")
        except Exception as e:
            logging.error(f"Failed to update pipe {pipe_idx} std_type: {e}")

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._net_data is None:
            return

        row, col = item.row(), item.column()
        pipe_idx = int(self._table.item(row, 0).text())
        net = self._net_data.net

        try:
            if col == 6:
                net.pipe.at[pipe_idx, "inner_diameter_mm"] = float(item.text())
            elif col == 7:
                net.pipe.at[pipe_idx, "k_mm"] = float(item.text())
        except ValueError:
            # Revert to stored value
            self._table.blockSignals(True)
            if col == 6:
                item.setText(f"{net.pipe.at[pipe_idx, 'inner_diameter_mm']:.1f}")
            elif col == 7:
                item.setText(f"{net.pipe.at[pipe_idx, 'k_mm']:.2f}")
            self._table.blockSignals(False)

        self._update_row_highlight(row)
