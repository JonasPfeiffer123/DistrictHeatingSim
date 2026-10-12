"""
Welcome screen at high display scaling.

At 125-150 % Windows scaling a maximised window has only ~650-800 logical pixels of height; the
welcome screen needed ~920, and Qt squeezed its sections below their minimum size - the buttons
were cut off inside their frames and overlapped (it looked fine at 100 %). The page now scrolls
instead and is compact enough to fit at 125 % on a 1080p screen.
"""

import pytest
from PyQt6.QtWidgets import QApplication, QFrame, QPushButton, QWidget

from districtheatingsim.utilities.utilities import get_resource_path

#: Logical client size of a maximised window on a 1920x1080 screen
MAXIMISED = {"100 %": (1920, 1010), "125 %": (1536, 805), "150 %": (1280, 660)}


@pytest.fixture
def show_welcome(qapp, tmp_path):
    from districtheatingsim.gui.MainTab.main_data_manager import ProjectConfigManager
    from districtheatingsim.gui.welcome_screen import WelcomeScreen

    windows = []

    def show(width, height):
        # The maximised main window cannot grow past the screen: a fixed-size parent stands in for it
        window = QWidget()
        window.setStyleSheet(open(get_resource_path("styles/win11_light.qss"), encoding="utf-8").read())
        window.setFixedSize(width, height)
        screen = WelcomeScreen(ProjectConfigManager(config_path=str(tmp_path / "recent.json")))
        screen.setParent(window)
        screen.setGeometry(0, 0, width, height)
        window.show()
        for _ in range(5):
            QApplication.processEvents()
        windows.append(window)
        return screen

    yield show
    for window in windows:
        window.close()


def _squeezed(screen):
    """Framed boxes and buttons that got less height than they need."""
    widgets = [w for w in screen.findChildren(QFrame) if w.objectName() == "actionButtonContainer"]
    widgets += screen.findChildren(QPushButton)
    return [
        (w.objectName() or w.text(), w.height(), w.minimumSizeHint().height())
        for w in widgets
        if w.isVisible() and w.height() < w.minimumSizeHint().height()
    ]


@pytest.mark.parametrize("scaling", list(MAXIMISED))
def test_nothing_is_squeezed(show_welcome, scaling):
    screen = show_welcome(*MAXIMISED[scaling])
    assert _squeezed(screen) == []


def test_fits_without_scrolling_at_125_percent(show_welcome):
    from PyQt6.QtWidgets import QScrollArea

    screen = show_welcome(*MAXIMISED["125 %"])
    page_scroll = screen.findChild(QScrollArea, "welcomePageScroll")
    assert not page_scroll.verticalScrollBar().isVisible()
    assert screen.findChild(QScrollArea, "welcomePageScroll").widget().minimumSizeHint().height() <= 805


def test_long_project_path_is_shortened_not_cut(qapp):
    from districtheatingsim.gui.welcome_screen import ElidedLabel

    path = r"C:\Users\jemand\Documents\GitHub\DistrictHeatingSim\src\districtheatingsim\project_data\Görlitz"
    label = ElidedLabel(path)
    label.resize(250, 20)
    label.show()
    QApplication.processEvents()
    assert "…" in label.text() and label.text().endswith("Görlitz") and label.full_text() == path
    label.resize(2000, 20)
    QApplication.processEvents()
    assert label.text() == path
    label.close()
