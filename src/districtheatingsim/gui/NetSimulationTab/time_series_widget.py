"""
Time Series Widget
==================

Full-width matplotlib canvas with a checkable dropdown for
displaying network simulation time series results.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer

from districtheatingsim.gui.utilities import CheckableComboBox


class TimeSeriesWidget(QWidget):
    """
    Full-width time series plot with a checkable data-selection dropdown.

    Call :meth:`update` with a ``NetworkGenerationData`` instance after
    ``prepare_plot_data()`` has been called on it.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._network_data = None
        self._dropdown = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self._dropdown_layout = QHBoxLayout()
        layout.addLayout(self._dropdown_layout)

        self._figure = Figure()
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setMinimumSize(800, 500)
        self._toolbar = NavigationToolbar(self._canvas, self)

        layout.addWidget(self._canvas)
        layout.addWidget(self._toolbar)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def update(self, network_data):
        """
        Rebuild the dropdown from *network_data.plot_data* and redraw.

        :param network_data: Simulation result data with plot_data populated.
        :type network_data: NetworkGenerationData
        """
        self._network_data = network_data
        self._rebuild_dropdown()
        # Small delay so the dropdown is fully laid out before first draw
        QTimer.singleShot(100, self._plot)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rebuild_dropdown(self):
        # Remove old dropdown widget if present
        while self._dropdown_layout.count():
            item = self._dropdown_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._dropdown = None

        if not self._network_data or not hasattr(self._network_data, 'plot_data'):
            return

        self._dropdown = CheckableComboBox(self)
        first = True
        for label in self._network_data.plot_data.keys():
            self._dropdown.addItem(label)
            model_item = self._dropdown.model().item(self._dropdown.count() - 1, 0)
            model_item.setCheckState(
                Qt.CheckState.Checked if first else Qt.CheckState.Unchecked
            )
            first = False

        self._dropdown_layout.addWidget(self._dropdown)
        self._dropdown.checkedStateChanged.connect(self._plot)

    def _plot(self):
        if not self._network_data or self._dropdown is None:
            return

        self._figure.clear()

        gs = gridspec.GridSpec(
            1, 3, width_ratios=[0.25, 0.50, 0.25], figure=self._figure
        )
        ax_leg_l = self._figure.add_subplot(gs[0, 0])
        ax_main  = self._figure.add_subplot(gs[0, 1])
        ax_leg_r = self._figure.add_subplot(gs[0, 2])
        ax_right = ax_main.twinx()

        label_fs   = 16
        legend_fs  = 12
        line_width = 2
        left_cmap  = plt.get_cmap('tab10')
        right_cmap = plt.get_cmap('Set2')

        li = ri = 0
        lines_l, labels_l = [], []
        lines_r, labels_r = [], []
        y_labels_l, y_labels_r = set(), set()
        min_t = max_t = None

        for i in range(self._dropdown.model().rowCount()):
            if not self._dropdown.itemChecked(i):
                continue

            key  = self._dropdown.itemText(i)
            info = self._network_data.plot_data[key]
            time_steps = info.get("time")

            if time_steps is None or len(time_steps) != len(info["data"]):
                continue

            try:
                hours = self._to_hours(time_steps, info["data"])
            except Exception:
                hours = list(range(len(info["data"])))

            if info["axis"] == "left":
                color = left_cmap(li % 10)
                line, = ax_main.plot(
                    hours, info["data"], label=key, color=color, linewidth=line_width
                )
                lines_l.append(line)
                labels_l.append(key)
                y_labels_l.add(info["label"])
                li += 1
            elif info["axis"] == "right":
                color = right_cmap(ri % 8)
                line, = ax_right.plot(
                    hours, info["data"], label=key, color=color,
                    linewidth=line_width, linestyle='--'
                )
                lines_r.append(line)
                labels_r.append(key)
                y_labels_r.add(info["label"])
                ri += 1

            try:
                tmin, tmax = float(hours[0]), float(hours[-1])
                min_t = tmin if min_t is None else min(min_t, tmin)
                max_t = tmax if max_t is None else max(max_t, tmax)
            except (ValueError, TypeError):
                pass

        # Axis labels
        ax_main.set_xlabel("Jahresstunden [h]", fontsize=label_fs)
        ax_main.set_ylabel(
            self._wrap_label(", ".join(y_labels_l)), fontsize=label_fs - 1
        )
        ax_right.set_ylabel(
            self._wrap_label(", ".join(y_labels_r)), fontsize=label_fs - 1
        )
        ax_main.tick_params(axis='both', labelsize=14)
        ax_right.tick_params(axis='y', labelsize=14)

        if min_t is not None:
            ax_main.set_xlim(min_t, max_t)
            ax_right.set_xlim(min_t, max_t)
            self._set_xticks(ax_main, max_t)

        # Side-panel legends
        ax_leg_l.axis('off')
        ax_leg_r.axis('off')

        if lines_l:
            ncol = 1 if len(lines_l) <= 10 else 2
            ax_leg_l.legend(
                lines_l, labels_l, loc='upper left',
                fontsize=legend_fs - 2, frameon=False, ncol=ncol,
                columnspacing=0.2, handletextpad=0.3, handlelength=1.0,
            )
        if lines_r:
            ncol = 1 if len(lines_r) <= 10 else 2
            ax_leg_r.legend(
                lines_r, labels_r, loc='upper right',
                fontsize=legend_fs - 2, frameon=False, ncol=ncol,
                columnspacing=0.2, handletextpad=0.3, handlelength=1.0,
            )

        self._figure.suptitle('Zeitreihen-Simulation Wärmenetz', fontsize=18)
        ax_main.grid(True, alpha=0.3)
        self._figure.subplots_adjust(
            left=0.02, right=0.98, top=0.92, bottom=0.1, wspace=0.1
        )
        self._canvas.draw()

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_hours(time_steps, data):
        """Convert time_steps to hours-of-year list."""
        if not hasattr(time_steps, '__iter__') or len(time_steps) == 0:
            return list(range(len(data)))
        first = (
            time_steps[0]
            if hasattr(time_steps, '__getitem__')
            else next(iter(time_steps))
        )
        if hasattr(first, 'timetuple') or 'datetime' in str(type(first)):
            if hasattr(first, 'year'):
                start = pd.Timestamp(first.year, 1, 1)
                return [
                    (pd.Timestamp(t) - start).total_seconds() / 3600
                    for t in time_steps
                ]
            return list(range(len(time_steps)))
        return list(time_steps)

    @staticmethod
    def _wrap_label(text: str, width: int = 40) -> str:
        """Insert newlines into long comma-separated axis labels."""
        if len(text) <= width:
            return text
        words, lines, current = text.split(", "), [], ""
        for word in words:
            if current and len(current) + 2 + len(word) > width:
                lines.append(current)
                current = word
            else:
                current = (current + ", " + word) if current else word
        if current:
            lines.append(current)
        return "\n".join(lines)

    @staticmethod
    def _set_xticks(ax, max_time):
        try:
            n = int(max_time)
            step = 2000 if n > 8760 else 1000 if n > 4000 else 500
            ax.set_xticks(range(0, n, step))
        except (ValueError, TypeError):
            pass
