"""
CSV Import Dialog
=================

Column-mapping dialog that lets users load a CSV in any format and map its
columns to the internal building-data schema.  Missing columns can be filled
with a per-column default value.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import csv
import io
from typing import Dict, List, Optional, Tuple

import pandas as pd

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QHeaderView, QMessageBox, QAbstractItemView, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


# ---------------------------------------------------------------------------
# Target schema
# ---------------------------------------------------------------------------

# (column_name, label_in_ui, required, default_value, tooltip)
TARGET_COLUMNS: List[Tuple[str, str, bool, str, str]] = [
    ("Land",                "Land",                  True,  "Deutschland", "Pflichtfeld – z. B. 'Deutschland'"),
    ("Bundesland",          "Bundesland",             True,  "",            "Pflichtfeld – z. B. 'Sachsen'"),
    ("Stadt",               "Stadt",                  True,  "",            "Pflichtfeld – z. B. 'Leipzig'"),
    ("Adresse",             "Adresse",                True,  "",            "Pflichtfeld – Straße + Hausnummer"),
    ("Wärmebedarf",         "Wärmebedarf [kWh/a]",   True,  "",            "Pflichtfeld – jährlicher Wärmebedarf in kWh"),
    ("Gebäudetyp",          "Gebäudetyp",             True,  "HMF",         "Pflichtfeld – BDEW/VDI 4655 Typkürzel (EFH, MFH, GKO, …)"),
    ("Subtyp",              "Subtyp",                 False, "",            "Optional – z. B. BDEW-Subtyp"),
    ("WW_Anteil",           "WW-Anteil [0–1]",        True,  "",        "Pflichtfeld – Anteil Warmwasser am Gesamtwärmebedarf"),
    ("Typ_Heizflächen",     "Typ Heizflächen",        False, "",          "Optional – HK = Heizkörper, FBH = Fußbodenheizung"),
    ("VLT_max",             "VLT_max [°C]",           True,  "70",          "Pflichtfeld – maximale Vorlauftemperatur"),
    ("Steigung_Heizkurve",  "Steigung Heizkurve",     True,  "1.5",         "Pflichtfeld – Steigung der witterungsgeführten Heizkurve"),
    ("RLT_max",             "RLT_max [°C]",           True,  "50",          "Pflichtfeld – maximale Rücklauftemperatur"),
    ("Normaußentemperatur", "Normaußentemp. [°C]",    True,  "-15",         "Pflichtfeld – Normaußentemperatur nach DIN EN 12831"),
    ("Heizgrenztemperatur", "Heizgrenztemp. [°C]",    False, "15",            "Optional BDEW – Temperatur, ab der nicht mehr geheizt wird (~15 °C)"),
    ("Heizexponent",        "Heizexponent",            False, "",            "Optional BDEW – Formparameter der Lastkurve (Standard 1.0)"),
    ("P_max",               "P_max [kW]",             False, "",            "Optional BDEW – maximale Wärmeleistung in kW"),
]

# Known alternative names for auto-mapping (lower-case keys)
_ALIASES: Dict[str, List[str]] = {
    "land":                ["country", "nation", "staat"],
    "bundesland":          ["state", "province", "region"],
    "stadt":               ["city", "ort", "gemeinde", "place", "location"],
    "adresse":             ["address", "street", "straße", "strasse", "anschrift", "adress"],
    "wärmebedarf":         ["heat_demand", "heizenergie", "jahresenergiebedarf", "energiebedarf",
                            "jahreswärmebedarf", "jwb", "waermebedarf", "annual_heat", "wärmemengen"],
    "gebäudetyp":          ["building_type", "typ", "type", "nutzungstyp", "gebaeudetyp", "gebäudetyp"],
    "subtyp":              ["subtype", "sub_type", "untertyp"],
    "ww_anteil":           ["dhw_share", "warmwasser", "ww", "dhw", "warmwasseranteil"],
    "typ_heizflächen":     ["heating_surface", "heizflaeche", "heizfläche"],
    "vlt_max":             ["vl_max", "vorlauf_max", "vorlauftemperatur_max", "supply_temp", "tvl_max"],
    "steigung_heizkurve":  ["slope", "heizkurve_steigung", "neigung_heizkurve"],
    "rlt_max":             ["rl_max", "rücklauf_max", "rücklauftemperatur_max", "return_temp", "trl_max"],
    "normaußentemperatur": ["design_temp", "auslegungstemperatur", "normaußen", "t_design",
                            "normaussentemperatur", "t_norm"],
    "heizgrenztemperatur": ["heating_limit_temp", "heizgrenze", "t_heizgrenze"],
    "heizexponent":        ["heating_exponent", "exponent"],
    "p_max":               ["peak_design_kw", "maxleistung", "max_leistung", "p_nenn", "p_max_kw"],
}

_NO_MAPPING = "(nicht zugeordnet – Standardwert)"


def _detect_delimiter(path: str) -> str:
    """Auto-detect CSV delimiter using csv.Sniffer."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        sample = f.read(4096)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ";"


def _suggest_mapping(target_col: str, source_cols: List[str]) -> str:
    """
    Return the best source column name for *target_col*, or empty string if
    no confident match is found.
    """
    target_lower = target_col.lower()
    source_lower = {c.lower(): c for c in source_cols}

    # 1. Exact match (case-insensitive)
    if target_lower in source_lower:
        return source_lower[target_lower]

    # 2. Known aliases
    for alias in _ALIASES.get(target_lower, []):
        if alias in source_lower:
            return source_lower[alias]

    # 3. Partial substring match (target contained in source or vice versa)
    for src_lower, src_orig in source_lower.items():
        if target_lower in src_lower or src_lower in target_lower:
            return src_orig

    return ""


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class CsvImportDialog(QDialog):
    """
    Column-mapping dialog for importing CSVs with arbitrary column names.

    Shows one row per target field.  Each row has a source-column dropdown
    (including a "not mapped – use default" option) and a default-value
    text field.  When a source column is selected the default field is
    disabled; when "not mapped" is selected it becomes the actual value
    written for every row.

    :param source_path: Path to the source CSV file.
    :type source_path: str
    :param parent: Parent widget.
    :type parent: QWidget or None
    """

    # Columns in the mapping table
    _COL_TARGET  = 0
    _COL_SOURCE  = 1
    _COL_DEFAULT = 2

    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.result_df: Optional[pd.DataFrame] = None

        self._delimiter = _detect_delimiter(source_path)
        self._source_df = pd.read_csv(source_path, delimiter=self._delimiter,
                                      encoding="utf-8-sig", dtype=str)
        self._source_cols: List[str] = list(self._source_df.columns)

        self.setWindowTitle("CSV importieren – Spaltenzuordnung")
        self.resize(820, 620)
        self._build_ui()
        self._populate_table()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Info header
        info_text = (
            f"<b>Quelldatei:</b> {self.source_path}<br>"
            f"<b>Trennzeichen erkannt:</b> '{self._delimiter}'  |  "
            f"<b>Zeilen:</b> {len(self._source_df)}  |  "
            f"<b>Quellspalten:</b> {', '.join(self._source_cols)}"
        )
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setFrameShape(QFrame.Shape.StyledPanel)
        info_label.setContentsMargins(6, 4, 6, 4)
        layout.addWidget(info_label)

        hint = QLabel(
            "Ordnen Sie jeder Zielspalte eine Quellspalte zu oder geben Sie einen Standardwert ein.\n"
            "Fette Zielfelder sind Pflichtfelder (müssen Quellspalte ODER Standardwert haben)."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Mapping table
        self.table = QTableWidget(len(TARGET_COLUMNS), 3)
        self.table.setHorizontalHeaderLabels(["Zielfeld", "Quellspalte", "Standardwert"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._preview_btn = QPushButton("Vorschau")
        self._preview_btn.clicked.connect(self._on_preview)
        btn_row.addWidget(self._preview_btn)
        self._import_btn = QPushButton("Importieren")
        self._import_btn.setDefault(True)
        self._import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self._import_btn)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _populate_table(self):
        """Fill the mapping table with one row per target column."""
        bold = QFont()
        bold.setBold(True)

        combo_items = [_NO_MAPPING] + self._source_cols

        for row, (col_name, label, required, default, tooltip) in enumerate(TARGET_COLUMNS):
            # Col 0 – target field label
            item = QTableWidgetItem(label)
            item.setToolTip(tooltip)
            if required:
                item.setFont(bold)
            self.table.setItem(row, self._COL_TARGET, item)

            # Col 1 – source column dropdown
            combo = QComboBox()
            combo.addItems(combo_items)
            combo.setToolTip(tooltip)
            suggestion = _suggest_mapping(col_name, self._source_cols)
            if suggestion:
                idx = combo.findText(suggestion)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.currentIndexChanged.connect(lambda _, r=row: self._on_combo_changed(r))
            self.table.setCellWidget(row, self._COL_SOURCE, combo)

            # Col 2 – default value input
            default_edit = QLineEdit(default)
            default_edit.setPlaceholderText("Standardwert")
            self.table.setCellWidget(row, self._COL_DEFAULT, default_edit)

            # Sync enabled state
            self._on_combo_changed(row)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_combo_changed(self, row: int):
        """Enable/disable the default value field based on combo selection."""
        combo: QComboBox = self.table.cellWidget(row, self._COL_SOURCE)
        default_edit: QLineEdit = self.table.cellWidget(row, self._COL_DEFAULT)
        if combo and default_edit:
            not_mapped = combo.currentText() == _NO_MAPPING
            default_edit.setEnabled(not_mapped)
            default_edit.setStyleSheet("" if not_mapped else "color: gray;")

    def _build_result_df(self) -> Tuple[Optional[pd.DataFrame], List[str]]:
        """
        Apply the current mapping to produce the target DataFrame.

        :return: (DataFrame or None, list of validation error messages)
        """
        errors: List[str] = []
        out_rows = []

        target_col_names = [tc[0] for tc in TARGET_COLUMNS]

        for src_idx in range(len(self._source_df)):
            row_out: Dict[str, str] = {}
            for col_idx, (col_name, label, required, _, _) in enumerate(TARGET_COLUMNS):
                combo: QComboBox = self.table.cellWidget(col_idx, self._COL_SOURCE)
                default_edit: QLineEdit = self.table.cellWidget(col_idx, self._COL_DEFAULT)
                src_col = combo.currentText() if combo else _NO_MAPPING
                default_val = default_edit.text().strip() if default_edit else ""

                if src_col == _NO_MAPPING:
                    if required and not default_val and src_idx == 0:
                        errors.append(f"Pflichtfeld '{label}' hat weder Quellspalte noch Standardwert.")
                    row_out[col_name] = default_val
                else:
                    row_out[col_name] = str(self._source_df.at[src_idx, src_col])

            out_rows.append(row_out)

        if errors:
            return None, errors

        df = pd.DataFrame(out_rows, columns=target_col_names)
        # Append UTM_X / UTM_Y if not already present
        if "UTM_X" not in df.columns:
            df["UTM_X"] = ""
        if "UTM_Y" not in df.columns:
            df["UTM_Y"] = ""
        return df, []

    def _on_preview(self):
        """Show a short preview of the first 5 mapped rows."""
        df, errors = self._build_result_df()
        if errors:
            QMessageBox.warning(self, "Validierungsfehler", "\n".join(errors))
            return

        # Show first 5 rows as plain text
        buf = io.StringIO()
        df.head(5).to_csv(buf, sep=";", index=False)
        QMessageBox.information(
            self, "Vorschau (erste 5 Zeilen)",
            f"<pre>{buf.getvalue()}</pre>"
        )

    def _on_import(self):
        """Validate mapping, build result DataFrame and accept the dialog."""
        df, errors = self._build_result_df()
        if errors:
            QMessageBox.warning(self, "Validierungsfehler",
                                "Bitte beheben Sie folgende Fehler:\n\n" + "\n".join(errors))
            return
        self.result_df = df
        self.accept()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_result(self) -> Optional[pd.DataFrame]:
        """Return the mapped DataFrame after the dialog was accepted, else None."""
        return self.result_df
