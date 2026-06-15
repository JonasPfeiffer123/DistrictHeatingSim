"""
Declarative field schema + base dialog for technology-input widgets.

The simple and combustion technology dialogs differ only in *which* fields they
show and how those map to the ``tech_data`` dict. ``SchemaDialog`` builds the
QFormLayout and implements ``getInputs()`` from a declarative list of ``Field`` /
``ComboField`` / ``CheckField`` entries, removing the per-dialog QLineEdit→dict
boilerplate.

Dialogs needing custom widgets (3D plots, CSV import) subclass ``SchemaDialog``,
let it build the fields via ``_build_fields()``, and arrange/extend them by
overriding ``_build()`` and ``getInputs()`` (see ``_solar.py`` / ``_heat_pump.py``).
The 1D thermal-storage dialog (dynamic loss-model sections + conditional output)
stays fully hand-written — it is unique, not duplicated, so the schema buys nothing.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

from collections.abc import Callable
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass
class Field:
    """A single text-input row mapping a ``tech_data`` key to a QLineEdit.

    :param key: Output key written by ``getInputs()``.
    :param label: German label shown next to the field.
    :param default: Default text when the value is absent from ``tech_data``.
    :param cast: Callable applied to the text on output (``float`` by default;
        e.g. ``int`` for node counts).
    :param in_key: Key read for the *initial* value, when it differs from ``key``.
        Reproduces the legacy read/write asymmetry of some dialogs (e.g. GasBoiler
        reads ``th_Leistung_kW`` but writes ``thermal_capacity_kW``). Defaults to
        ``key``.
    """

    key: str
    label: str
    default: str
    cast: Callable = float
    in_key: str | None = None

    @property
    def read_key(self) -> str:
        return self.in_key if self.in_key is not None else self.key


@dataclass
class ComboField:
    """A dropdown row producing the selected option string in ``getInputs()``."""

    key: str
    label: str
    options: list[str]
    default: str


@dataclass
class CheckField:
    """A checkbox row producing a bool in ``getInputs()``."""

    key: str
    label: str
    default: bool = False


SchemaItem = Field | ComboField | CheckField


@dataclass
class Section:
    """A titled QGroupBox grouping a set of fields (purely a layout container)."""

    title: str
    fields: list[SchemaItem]


class SchemaDialog(QWidget):
    """Base widget that builds itself from a declarative field schema.

    Subclasses set class attributes:

    - ``main_schema``: flat list of :class:`Field` / :class:`ComboField` /
      :class:`CheckField` (rendered in a single form).
    - ``sections``: alternatively, a list of :class:`Section` rendered as titled
      group boxes. When set it takes precedence over ``main_schema``.
    - ``storage_schema``: optional list of :class:`Field` rendered in a side panel
      whose visibility is toggled by the ``storage_toggle_key`` checkbox; its keys
      are only included in ``getInputs()`` when that checkbox is checked.
    - ``storage_toggle_key``: key of the controlling checkbox (default
      ``"speicher_aktiv"``).
    - ``title``: optional window title.

    Dialogs with custom widgets override :meth:`_build` (calling
    :meth:`_build_fields` for the schema part) and, if needed, :meth:`getInputs`.
    """

    main_schema: list[SchemaItem] = []
    sections: list[Section] | None = None
    storage_schema: list[Field] | None = None
    storage_toggle_key: str = "speicher_aktiv"
    title: str = ""

    def __init__(self, tech_data: dict | None = None):
        super().__init__()
        self.tech_data = tech_data if tech_data is not None else {}
        self._widgets: dict = {}
        self._storage_widget: QWidget | None = None
        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        """Default layout: the schema fields fill the dialog. Override to add
        custom widgets (e.g. a visualization canvas alongside the fields)."""
        outer = QVBoxLayout(self)
        outer.addWidget(self._build_fields())
        if self.title:
            self.setWindowTitle(self.title)

    def _build_fields(self) -> QWidget:
        """Build all schema widgets into a container and return it.

        Handles three layouts: titled sections, a main form with a toggled storage
        side panel, or a plain single form. Populates ``self._widgets``.
        """
        container = QWidget()
        if self.sections is not None:
            layout = QVBoxLayout(container)
            for section in self.sections:
                box = QGroupBox(section.title)
                form = QFormLayout(box)
                self._populate(form, section.fields)
                layout.addWidget(box)
        elif self.storage_schema is not None:
            layout = QHBoxLayout(container)
            left = QFormLayout()
            self._populate(left, self.main_schema)
            layout.addLayout(left)

            self._storage_widget = QWidget()
            storage_form = QFormLayout(self._storage_widget)
            self._populate(storage_form, self.storage_schema)
            layout.addWidget(self._storage_widget)

            toggle = self._widgets[self.storage_toggle_key]
            toggle.stateChanged.connect(self._toggle_storage)
            self._toggle_storage()
        else:
            form = QFormLayout(container)
            self._populate(form, self.main_schema)
        return container

    def _populate(self, form: QFormLayout, schema: list[SchemaItem]) -> None:
        for item in schema:
            if isinstance(item, CheckField):
                widget = QCheckBox(item.label)
                widget.setChecked(bool(self.tech_data.get(item.key, item.default)))
                form.addRow(widget)
            elif isinstance(item, ComboField):
                widget = QComboBox()
                widget.addItems(item.options)
                current = self.tech_data.get(item.key, item.default)
                if current in item.options:
                    widget.setCurrentText(current)
                form.addRow(QLabel(item.label), widget)
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

    def _main_items(self) -> list[SchemaItem]:
        if self.sections is not None:
            return [field for section in self.sections for field in section.fields]
        return self.main_schema

    def _read(self, item: SchemaItem):
        widget = self._widgets[item.key]
        if isinstance(item, CheckField):
            return widget.isChecked()
        if isinstance(item, ComboField):
            return widget.currentText()
        return item.cast(widget.text())

    def getInputs(self) -> dict:
        """Collect the field values into a ``tech_data`` dict."""
        inputs = {item.key: self._read(item) for item in self._main_items()}

        if self.storage_schema is not None and self._widgets[self.storage_toggle_key].isChecked():
            for item in self.storage_schema:
                inputs[item.key] = self._read(item)

        return inputs
