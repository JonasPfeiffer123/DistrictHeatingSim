"""
CSV Import Dialog
=================

Column-mapping dialog that lets users load a CSV in any format and map its
columns to the internal building-data schema.  Missing columns can be filled
with a per-column default value; a second source column can be appended (street +
house number).

Tables come as Excel writes them on a German Windows: Windows-1252, decimal commas, empty
cells. The module functions read and normalise them and check the values before anything is
saved (BACKLOG UT-H5).

:author: M.Eng. Jonas Pfeiffer
"""

import csv
import html
import io
import re

import pandas as pd
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

# ---------------------------------------------------------------------------
# Target schema
# ---------------------------------------------------------------------------

# (column_name, label_in_ui, required, default_value, tooltip)
TARGET_COLUMNS: list[tuple[str, str, bool, str, str]] = [
    ("Land", "Land", True, "Deutschland", "Pflichtfeld – z. B. 'Deutschland'"),
    ("Bundesland", "Bundesland", True, "", "Pflichtfeld – z. B. 'Sachsen'"),
    ("Stadt", "Stadt", True, "", "Pflichtfeld – z. B. 'Leipzig'"),
    ("Adresse", "Adresse", True, "", "Pflichtfeld – Straße + Hausnummer"),
    ("Wärmebedarf", "Wärmebedarf [kWh/a]", True, "", "Pflichtfeld – jährlicher Wärmebedarf in kWh"),
    ("Gebäudetyp", "Gebäudetyp", True, "HMF", "Pflichtfeld – BDEW/VDI 4655 Typkürzel (EFH, MFH, GKO, …)"),
    ("Subtyp", "Subtyp", False, "", "Optional – z. B. BDEW-Subtyp"),
    ("WW_Anteil", "WW-Anteil [0–1]", True, "0.2", "Pflichtfeld – Anteil Warmwasser am Gesamtwärmebedarf"),
    ("Typ_Heizflächen", "Typ Heizflächen", False, "", "Optional – HK = Heizkörper, FBH = Fußbodenheizung"),
    ("VLT_max", "VLT_max [°C]", True, "70", "Pflichtfeld – maximale Vorlauftemperatur"),
    (
        "Steigung_Heizkurve",
        "Steigung Heizkurve",
        True,
        "1.5",
        "Pflichtfeld – Steigung der witterungsgeführten Heizkurve",
    ),
    ("RLT_max", "RLT_max [°C]", True, "50", "Pflichtfeld – maximale Rücklauftemperatur"),
    ("Normaußentemperatur", "Normaußentemp. [°C]", True, "-15", "Pflichtfeld – Normaußentemperatur nach DIN EN 12831"),
    (
        "Heizgrenztemperatur",
        "Heizgrenztemp. [°C]",
        False,
        "15",
        "Optional BDEW – Temperatur, ab der nicht mehr geheizt wird (~15 °C)",
    ),
    ("Heizexponent", "Heizexponent", False, "", "Optional BDEW – Formparameter der Lastkurve (Standard 1.0)"),
    ("P_max", "P_max [kW]", False, "", "Optional BDEW – maximale Wärmeleistung in kW"),
]

# Known alternative names for auto-mapping (lower-case keys)
_ALIASES: dict[str, list[str]] = {
    "land": ["country", "nation", "staat"],
    "bundesland": ["state", "province", "region"],
    "stadt": ["city", "ort", "gemeinde", "place", "location"],
    "adresse": ["address", "street", "straße", "strasse", "anschrift", "adress"],
    "wärmebedarf": [
        "heat_demand",
        "heizenergie",
        "jahresenergiebedarf",
        "energiebedarf",
        "jahreswärmebedarf",
        "jwb",
        "waermebedarf",
        "annual_heat",
        "wärmemengen",
    ],
    "gebäudetyp": [
        "building_type",
        "typ",
        "type",
        "nutzung",
        "nutzungsart",
        "nutzungstyp",
        "gebäudeart",
        "gebaeudetyp",
        "gebäudetyp",
    ],
    "subtyp": ["subtype", "sub_type", "untertyp"],
    "ww_anteil": [
        "dhw_share",
        "warmwasser",
        "ww",
        "dhw",
        "warmwasseranteil",
        "anteil ww",
        "anteil_ww",
        "ww-anteil",
        "ww anteil",
    ],
    "typ_heizflächen": ["heating_surface", "heizflaeche", "heizfläche"],
    "vlt_max": ["vl_max", "vorlauf_max", "vorlauftemperatur_max", "supply_temp", "tvl_max"],
    "steigung_heizkurve": ["slope", "heizkurve_steigung", "neigung_heizkurve"],
    "rlt_max": ["rl_max", "rücklauf_max", "rücklauftemperatur_max", "return_temp", "trl_max"],
    "normaußentemperatur": [
        "design_temp",
        "auslegungstemperatur",
        "normaußen",
        "t_design",
        "normaussentemperatur",
        "t_norm",
    ],
    "heizgrenztemperatur": ["heating_limit_temp", "heizgrenze", "t_heizgrenze"],
    "heizexponent": ["heating_exponent", "exponent"],
    "p_max": ["peak_design_kw", "maxleistung", "max_leistung", "p_nenn", "p_max_kw"],
}

# House-number columns, appended to the street for "Adresse" (lower-case)
_HOUSE_NUMBER_NAMES = ("hausnummer", "hausnr", "hausnr.", "hnr", "hnr.", "nr", "nr.", "housenumber", "house_number")

_NO_MAPPING = "(nicht zugeordnet – Standardwert)"
_NO_ADDITION = "–"

#: Columns the heat-demand calculation reads as numbers
NUMERIC_COLUMNS = (
    "Wärmebedarf",
    "WW_Anteil",
    "VLT_max",
    "Steigung_Heizkurve",
    "RLT_max",
    "Normaußentemperatur",
    "Heizgrenztemperatur",
    "Heizexponent",
    "P_max",
)
# kWh/a and kW are never fractions of a thousandth: '185.000' is 185 000 (German thousands dot)
_THOUSANDS_COLUMNS = ("Wärmebedarf", "P_max")
_THOUSANDS_DOTS = re.compile(r"^-?\d{1,3}(\.\d{3})+$")

_MAX_LISTED_PROBLEMS = 15


def detect_encoding(path: str) -> str:
    """
    Encoding of a text file: UTF-8 (with or without BOM) if it decodes, else Windows-1252.

    Excel's "CSV (Trennzeichen-getrennt)" on a German Windows writes Windows-1252; reading it as
    UTF-8 failed with a UnicodeDecodeError (BACKLOG UT-H5).
    """
    with open(path, "rb") as f:
        data = f.read()
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "cp1252"
    return "utf-8-sig"


def _detect_delimiter(path: str, encoding: str = "utf-8-sig") -> str:
    """Auto-detect CSV delimiter using csv.Sniffer."""
    with open(path, encoding=encoding, errors="replace") as f:
        sample = f.read(4096)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ";"


def read_source_table(path: str) -> tuple[pd.DataFrame, str, str]:
    """
    Read a user's building table as text: encoding and delimiter detected, empty cells as ``""``.

    Empty cells used to come through as the text ``"nan"`` (BACKLOG UT-H5).

    :return: ``(table, delimiter, encoding)``
    """
    encoding = detect_encoding(path)
    delimiter = _detect_delimiter(path, encoding)
    table = pd.read_csv(
        path, delimiter=delimiter, encoding=encoding, encoding_errors="replace", dtype=str, keep_default_na=False
    )
    table.columns = [str(column).strip() for column in table.columns]
    return table, delimiter, encoding


def normalise_number(text: str, thousands_dots: bool = False) -> str:
    """
    A number as the calculation reads it: ``'0,25'`` → ``'0.25'``, ``'1.234,5'`` → ``'1234.5'``.

    :param thousands_dots: Also read ``'185.000'`` as 185 000 (for kWh/a and kW).
    :return: The normalised text; anything that is no number comes back stripped.
    """
    value = str(text).strip().replace("\u00a0", "").replace(" ", "")
    if "," in value:
        return value.replace(".", "").replace(",", ".")
    if thousands_dots and _THOUSANDS_DOTS.match(value):
        return value.replace(".", "")
    return value


def prepare_buildings(table: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise an imported building table: stripped text, dot decimals, upper-case type codes.

    :param table: Buildings in the internal column schema, all values text.
    :return: A normalised copy.
    """
    table = table.copy()
    for column in table.columns:
        table[column] = table[column].map(lambda value: str(value).strip())
    for column in NUMERIC_COLUMNS:
        if column in table.columns:
            thousands = column in _THOUSANDS_COLUMNS
            table[column] = table[column].map(lambda value, t=thousands: normalise_number(value, t))
    if "Gebäudetyp" in table.columns:
        table["Gebäudetyp"] = table["Gebäudetyp"].str.upper()
    return table


def validate_buildings(table: pd.DataFrame) -> list[str]:
    """
    Values of a prepared building table that the heat-demand calculation would reject.

    Checked: required numbers present and numeric, WW share between 0 and 1, known building
    types, VDI 4655 and BDEW types not mixed. Line numbers count the header as line 1.

    :return: One German message per problem (empty if the table is fine).
    """
    from districtheatingsim.heat_requirement.heat_requirement_calculation_csv import (
        BDEW_BUILDING_TYPES,
        VDI4655_BUILDING_TYPES,
    )

    labels = {name: label for name, label, *_ in TARGET_COLUMNS}
    required = {name for name, _label, is_required, *_ in TARGET_COLUMNS if is_required}
    known_types = VDI4655_BUILDING_TYPES | BDEW_BUILDING_TYPES
    problems: list[str] = []
    unknown_type = False
    for position, (_, row) in enumerate(table.iterrows()):
        line = position + 2
        for column in NUMERIC_COLUMNS:
            if column not in table.columns:
                continue
            value = str(row[column]).strip()
            if not value:
                if column in required:
                    problems.append(f"Zeile {line}: {labels[column]} fehlt.")
                continue
            try:
                number = float(value)
            except ValueError:
                problems.append(f"Zeile {line}: {labels[column]} „{value}“ ist keine Zahl.")
                continue
            if column == "WW_Anteil" and not 0 <= number <= 1:
                problems.append(f"Zeile {line}: {labels[column]} {value} liegt nicht zwischen 0 und 1.")
        if "Gebäudetyp" in table.columns:
            building_type = str(row["Gebäudetyp"]).strip()
            if building_type not in known_types:
                unknown_type = True
                problems.append(f"Zeile {line}: Gebäudetyp „{building_type}“ ist unbekannt.")
    if "Gebäudetyp" in table.columns:
        types = set(table["Gebäudetyp"].astype(str).str.strip())
        vdi, bdew = sorted(types & VDI4655_BUILDING_TYPES), sorted(types & BDEW_BUILDING_TYPES)
        if vdi and bdew:
            problems.append(
                f"VDI-4655-Typen ({', '.join(vdi)}) und BDEW-Typen ({', '.join(bdew)}) sind gemischt; "
                "ein Projekt rechnet nur mit einem Verfahren (Wohngebäude im BDEW: HEF/HMF)."
            )
        if unknown_type:
            problems.append(
                f"Bekannte Gebäudetypen: VDI 4655 {', '.join(sorted(VDI4655_BUILDING_TYPES))}; "
                f"BDEW {', '.join(sorted(BDEW_BUILDING_TYPES))}."
            )
    return problems


def confirm_import_with_problems(parent, problems: list[str]) -> bool:
    """
    Show the problems of an import and ask whether to import anyway.

    :return: True if there are no problems or the user imports anyway.
    """
    if not problems:
        return True
    rows = [p for p in problems if p.startswith("Zeile")]
    listed = rows[:_MAX_LISTED_PROBLEMS] + [p for p in problems if not p.startswith("Zeile")]
    more = len(rows) - _MAX_LISTED_PROBLEMS
    text = "\n".join(listed) + (f"\n… und {more} weitere." if more > 0 else "")
    reply = QMessageBox.question(
        parent,
        "Werte prüfen",
        f"Einige Werte kann die Wärmebedarfsrechnung so nicht verwenden:\n\n{text}\n\n"
        "Trotzdem importieren? Die Werte lassen sich danach in der Gebäudetabelle korrigieren.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def _suggest_mapping(target_col: str, source_cols: list[str]) -> str:
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

    # 3. Partial substring match (target contained in source or vice versa); a short source name
    # like "Typ" or "Nr" would match half the targets
    for src_lower, src_orig in source_lower.items():
        if len(src_lower) >= 4 and (target_lower in src_lower or src_lower in target_lower):
            return src_orig

    return ""


def _suggest_addition(target_col: str, source_cols: list[str], primary: str) -> str:
    """Source column appended to *primary*: the house number for the address, else nothing."""
    if target_col != "Adresse" or not primary:
        return ""
    return next((c for c in source_cols if c != primary and c.strip().lower() in _HOUSE_NUMBER_NAMES), "")


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class CsvImportDialog(QDialog):
    """
    Column-mapping dialog for importing CSVs with arbitrary column names.

    Shows one row per target field.  Each row has a source-column dropdown
    (including a "not mapped – use default" option), a second dropdown whose
    column is appended with a space (street + house number) and a default-value
    text field.  When a source column is selected the default field is
    disabled; when "not mapped" is selected it becomes the actual value
    written for every row.

    :param source_path: Path to the source CSV file.
    :type source_path: str
    :param parent: Parent widget.
    :type parent: QWidget or None
    """

    # Columns in the mapping table
    _COL_TARGET = 0
    _COL_SOURCE = 1
    _COL_ADDITION = 2
    _COL_DEFAULT = 3

    def __init__(self, source_path: str, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.result_df: pd.DataFrame | None = None

        self._source_df, self._delimiter, self._encoding = read_source_table(source_path)
        self._source_cols: list[str] = list(self._source_df.columns)

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
            f"<b>Zeichensatz:</b> {'Windows-1252' if self._encoding == 'cp1252' else 'UTF-8'}  |  "
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
            "Fette Zielfelder sind Pflichtfelder (müssen Quellspalte ODER Standardwert haben).\n"
            "„+ Spalte“ hängt eine zweite Quellspalte an, z. B. die Hausnummer an die Straße. "
            "Dezimalkommas werden in Punkte umgewandelt."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Mapping table
        self.table = QTableWidget(len(TARGET_COLUMNS), 4)
        self.table.setHorizontalHeaderLabels(["Zielfeld", "Quellspalte", "+ Spalte", "Standardwert"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
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

            # Col 2 – optional second source column, appended with a space
            addition = QComboBox()
            addition.addItems([_NO_ADDITION] + self._source_cols)
            addition.setToolTip("Optional – wird mit Leerzeichen angehängt (z. B. Hausnummer an Straße)")
            addition_suggestion = _suggest_addition(col_name, self._source_cols, suggestion)
            if addition_suggestion:
                addition.setCurrentIndex(addition.findText(addition_suggestion))
            self.table.setCellWidget(row, self._COL_ADDITION, addition)

            # Col 3 – default value input
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

    def _build_result_df(self) -> tuple[pd.DataFrame | None, list[str]]:
        """
        Apply the current mapping to produce the target DataFrame.

        :return: (DataFrame or None, list of validation error messages)
        """
        errors: list[str] = []
        out_rows = []

        target_col_names = [tc[0] for tc in TARGET_COLUMNS]

        for src_idx in range(len(self._source_df)):
            row_out: dict[str, str] = {}
            for col_idx, (col_name, label, required, _, _) in enumerate(TARGET_COLUMNS):
                combo: QComboBox = self.table.cellWidget(col_idx, self._COL_SOURCE)
                addition: QComboBox = self.table.cellWidget(col_idx, self._COL_ADDITION)
                default_edit: QLineEdit = self.table.cellWidget(col_idx, self._COL_DEFAULT)
                src_col = combo.currentText() if combo else _NO_MAPPING
                add_col = addition.currentText() if addition else _NO_ADDITION
                default_val = default_edit.text().strip() if default_edit else ""

                if src_col == _NO_MAPPING:
                    if required and not default_val and src_idx == 0:
                        errors.append(f"Pflichtfeld '{label}' hat weder Quellspalte noch Standardwert.")
                    row_out[col_name] = default_val
                else:
                    parts = [self._source_df.at[src_idx, src_col]]
                    if add_col != _NO_ADDITION:
                        parts.append(self._source_df.at[src_idx, add_col])
                    row_out[col_name] = " ".join(str(p).strip() for p in parts if str(p).strip())

            out_rows.append(row_out)

        if errors:
            return None, errors

        df = prepare_buildings(pd.DataFrame(out_rows, columns=target_col_names))
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

        # Show first 5 rows as plain text, followed by the values that would not compute
        buf = io.StringIO()
        df.head(5).to_csv(buf, sep=";", index=False)
        problems = validate_buildings(df)
        notes = "<br>".join(html.escape(p) for p in problems[:_MAX_LISTED_PROBLEMS])
        text = f"<pre>{html.escape(buf.getvalue())}</pre>" + (f"<p><b>Zu prüfen:</b><br>{notes}</p>" if notes else "")
        QMessageBox.information(self, "Vorschau (erste 5 Zeilen)", text)

    def _on_import(self):
        """Validate mapping, build result DataFrame and accept the dialog."""
        df, errors = self._build_result_df()
        if errors:
            QMessageBox.warning(
                self, "Validierungsfehler", "Bitte beheben Sie folgende Fehler:\n\n" + "\n".join(errors)
            )
            return
        if not confirm_import_with_problems(self, validate_buildings(df)):
            return
        self.result_df = df
        self.accept()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_result(self) -> pd.DataFrame | None:
        """Return the mapped DataFrame after the dialog was accepted, else None."""
        return self.result_df
