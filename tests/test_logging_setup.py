"""
Logging setup + print guard (BACKLOG G10).

The library logs through module loggers; only the GUI entry point configures logging
(console + rotating log file). The guard keeps ``print``, ``logging.basicConfig`` and
root-logger calls out of the package, so diagnostics reach the log file in the no-console exe.
"""

import ast
import logging
import os
from pathlib import Path

import pytest

from districtheatingsim.utilities import logging_setup
from districtheatingsim.utilities.logging_setup import LOG_FILE_NAME, PACKAGE_LOGGER, configure_logging

SRC = Path(__file__).resolve().parents[1] / "src" / "districtheatingsim"
ENTRY_POINT = SRC / "DistrictHeatingSim.py"


@pytest.fixture
def restore_logging():
    root = logging.getLogger()
    package = logging.getLogger(PACKAGE_LOGGER)
    saved = (list(root.handlers), root.level, package.level)
    yield
    for handler in root.handlers[:]:
        if handler not in saved[0]:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(saved[1])
    package.setLevel(saved[2])
    logging.captureWarnings(False)


def _flush():
    for handler in logging.getLogger().handlers:
        handler.flush()


def test_writes_package_info_and_third_party_warnings_to_the_log_file(tmp_path, restore_logging):
    log_path = configure_logging(log_dir=str(tmp_path), console=False)

    assert log_path == os.path.join(str(tmp_path), LOG_FILE_NAME)
    logging.getLogger("districtheatingsim.some_module").info("package info Δh °C")
    logging.getLogger("districtheatingsim.some_module").debug("package debug")
    logging.getLogger("thirdparty").info("third-party info")
    logging.getLogger("thirdparty").warning("third-party warning")
    _flush()

    text = Path(log_path).read_text(encoding="utf-8")
    assert "package info Δh °C" in text
    assert "package debug" not in text
    assert "third-party info" not in text
    assert "third-party warning" in text


def test_level_from_environment(tmp_path, monkeypatch, restore_logging):
    monkeypatch.setenv(logging_setup.LOG_LEVEL_ENV, "debug")
    configure_logging(log_dir=str(tmp_path), console=False)
    assert logging.getLogger(PACKAGE_LOGGER).level == logging.DEBUG

    monkeypatch.setenv(logging_setup.LOG_LEVEL_ENV, "nonsense")
    configure_logging(log_dir=str(tmp_path), console=False)
    assert logging.getLogger(PACKAGE_LOGGER).level == logging.INFO


def test_reconfiguring_replaces_its_own_handlers_only(tmp_path, restore_logging):
    foreign = logging.NullHandler()
    logging.getLogger().addHandler(foreign)
    try:
        configure_logging(log_dir=str(tmp_path))
        configure_logging(log_dir=str(tmp_path))
        own = [h for h in logging.getLogger().handlers if getattr(h, logging_setup._OWN_HANDLER, False)]
        assert len(own) == 2  # console + file, not doubled
        assert foreign in logging.getLogger().handlers
    finally:
        logging.getLogger().removeHandler(foreign)


def test_unwritable_log_dir_falls_back_to_console(tmp_path, restore_logging):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")

    assert configure_logging(log_dir=str(blocker / "logs")) is None
    own = [h for h in logging.getLogger().handlers if getattr(h, logging_setup._OWN_HANDLER, False)]
    assert [type(h) for h in own] == [logging.StreamHandler]


def test_default_log_dir_is_per_user(monkeypatch):
    monkeypatch.delenv(logging_setup.LOG_DIR_ENV, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", os.path.join("C:", "Users", "x", "AppData", "Local"))
    assert logging_setup.default_log_dir() == os.path.join(
        "C:", "Users", "x", "AppData", "Local", "DistrictHeatingSim", "logs"
    )
    monkeypatch.setenv(logging_setup.LOG_DIR_ENV, "custom")
    assert logging_setup.default_log_dir() == "custom"


_ROOT_LOGGER_CALLS = {"debug", "info", "warning", "error", "exception", "critical", "basicConfig"}


def _offending_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    allowed = set()
    if path == ENTRY_POINT:
        # The console prompts of the entry point's __main__ block are interactive output, not logs.
        for node in tree.body:
            if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
                allowed.update(id(n) for n in ast.walk(node))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in allowed:
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "print":
            found.append(f"{path.name}:{node.lineno} print")
        elif (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "logging"
            and func.attr in _ROOT_LOGGER_CALLS
        ):
            found.append(f"{path.name}:{node.lineno} logging.{func.attr}")
    return found


def test_package_uses_module_loggers_not_print():
    offenders = [hit for path in sorted(SRC.rglob("*.py")) for hit in _offending_calls(path)]
    assert offenders == []
