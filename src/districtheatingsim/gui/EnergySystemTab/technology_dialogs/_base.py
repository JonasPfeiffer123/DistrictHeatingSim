"""
Declarative field schema + base dialog for technology-input widgets.

The simple and combustion technology dialogs differ only in *which* fields they
show and how those map to the ``tech_data`` dict. ``SchemaDialog`` builds the
QFormLayout and implements ``getInputs()`` from a declarative list of ``Field`` /
``CheckField`` entries, removing the per-dialog QLineEdit→dict boilerplate.

Dialogs needing custom widgets (3D plots, CSV import, dynamic sections) stay
hand-written in their own modules; they are not forced through this base.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Union

from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QLabel, QCheckBox, QFormLayout, QVBoxLayout, QHBoxLayout,
)


@dataclass
class Field:
    """A single text-input row mapping a ``tech_data`` key to a QLineEdit.

    :param key: Output key written by ``getInputs()``.
    :param label: German label shown next to the field.
    :param default: Default text when the value is absent from ``tech_data``.
    :param cast: Callable applied to the text on output (``float`` by default).
    :param in_key: Key read for the *initial* value, when it differs from ``key``.
        Reproduces the legacy read/write asymmetry of some dialogs (e.g. GasBoiler
        reads ``th_Leistung_kW`` but writes ``thermal_capacity_kW``). Defaults to
        ``key``.
    """

    key: str
    label: str
    default: str
    cast: Callable = float
    in_key: Optional[str] = None

    @property
    def read_key(self) -> str:
        return self.in_key if self.in_key is not None else self.key


@dataclass
class CheckField:
    """A checkbox row producing a bool in ``getInputs()``."""

    key: str
    label: str
    default: bool = False


SchemaItem = Union[Field, CheckField]


class SchemaDialog(QWidget):
    """Base widget that builds itself from a declarative field schema.

    Subclasses set class attributes:

    - ``main_schema``: list of :class:`Field` / :class:`CheckField` (always shown).
    - ``storage_schema``: optional list of :class:`Field` rendered in a side panel
      whose visibility is toggled by the ``storage_toggle_key`` checkbox; its keys
      are only included in ``getInputs()`` when that checkbox is checked.
    - ``storage_toggle_key``: key of the controlling checkbox (default
      ``"speicher_aktiv"``).
    - ``title``: optional window title.
    """

    main_schema: List[SchemaItem] = []
    storage_schema: Optional[List[Field]] = None
    storage_toggle_key: str = "speicher_aktiv"
    title: str = ""

    def __init__(self, tech_data: Optional[dict] = None):
        super().__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self._widgets: dict = {}
        self._storage_widget: Optional[QWidget] = None
        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        if self.storage_schema is None:
            outer = QVBoxLayout(self)
            form = QFormLayout()
            self._populate(form, self.main_schema)
            outer.addLayout(form)
        else:
            outer = QHBoxLayout(self)
            left = QFormLayout()
            self._populate(left, self.main_schema)
            outer.addLayout(left)

            self._storage_widget = QWidget()
            storage_form = QFormLayout(self._storage_widget)
            self._populate(storage_form, self.storage_schema)
            outer.addWidget(self._storage_widget)

            toggle = self._widgets[self.storage_toggle_key]
            toggle.stateChanged.connect(self._toggle_storage)
            self._toggle_storage()

        if self.title:
            self.setWindowTitle(self.title)

    def _populate(self, form: QFormLayout, schema: List[SchemaItem]) -> None:
        for item in schema:
            if isinstance(item, CheckField):
                widget = QCheckBox(item.label)
                widget.setChecked(bool(self.tech_data.get(item.key, item.default)))
                form.addRow(widget)
            else:  # Field
                widget = QLineEdit()
                widget.setText(str(self.tech_data.get(item.read_key, item.default)))
                form.addRow(QLabel(item.label), widget)
            self._widgets[item.key] = widget

    def _toggle_storage(self) -> None:
        if self._storage_widget is not None:
            checked = self._widgets[self.storage_toggle_key].isChecked()
            self._storage_widget.setVisible(checked)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _read(self, item: SchemaItem):
        widget = self._widgets[item.key]
        if isinstance(item, CheckField):
            return widget.isChecked()
        return item.cast(widget.text())

    def getInputs(self) -> dict:
        """Collect the field values into a ``tech_data`` dict."""
        inputs = {item.key: self._read(item) for item in self.main_schema}

        if self.storage_schema is not None and \
                self._widgets[self.storage_toggle_key].isChecked():
            for item in self.storage_schema:
                inputs[item.key] = self._read(item)

        return inputs
