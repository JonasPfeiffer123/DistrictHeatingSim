"""
Application logging setup.

Library modules log through ``logging.getLogger(__name__)`` and never configure logging
themselves; the GUI entry point calls :func:`configure_logging` once. Records of this package
(INFO and above by default) and warnings/errors of third-party packages go to the console, if
there is one, and to a rotating log file — the only place diagnostics survive in the
no-console exe (BACKLOG G10).

Environment overrides: ``DISTRICTHEATINGSIM_LOG_LEVEL`` (e.g. ``DEBUG``) and
``DISTRICTHEATINGSIM_LOG_DIR``.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import logging
import logging.handlers
import os
import sys

PACKAGE_LOGGER = "districtheatingsim"
LOG_FILE_NAME = "districtheatingsim.log"
LOG_LEVEL_ENV = "DISTRICTHEATINGSIM_LOG_LEVEL"
LOG_DIR_ENV = "DISTRICTHEATINGSIM_LOG_DIR"

_MAX_BYTES = 2_000_000
_BACKUP_COUNT = 3
_FILE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s [%(threadName)s]: %(message)s"
_CONSOLE_FORMAT = "%(levelname)-8s %(name)s: %(message)s"
_OWN_HANDLER = "_districtheatingsim_handler"


def default_log_dir() -> str:
    """
    Return the per-user log folder.

    The exe may be installed in a read-only folder, so the log goes to
    ``%LOCALAPPDATA%\\DistrictHeatingSim\\logs`` (``~/.local/state/DistrictHeatingSim/logs``
    elsewhere) unless ``DISTRICTHEATINGSIM_LOG_DIR`` is set.

    :return: Log folder path (not created here)
    :rtype: str
    """
    override = os.environ.get(LOG_DIR_ENV)
    if override:
        return override
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "DistrictHeatingSim", "logs")


def _resolve_level(level: int | str | None) -> int:
    if level is None:
        level = os.environ.get(LOG_LEVEL_ENV, "INFO")
    if isinstance(level, str):
        resolved = logging.getLevelName(level.strip().upper())
        return resolved if isinstance(resolved, int) else logging.INFO
    return level


def configure_logging(level: int | str | None = None, log_dir: str | None = None, console: bool = True) -> str | None:
    """
    Route log records to the console and a rotating log file.

    The package logger gets *level*; the root logger stays at WARNING so third-party packages
    only report warnings and errors. Python warnings are captured into the log as well.
    Calling it again replaces the handlers installed by an earlier call.

    :param level: Level of the ``districtheatingsim`` loggers; default from
        ``DISTRICTHEATINGSIM_LOG_LEVEL``, else INFO
    :type level: int | str | None
    :param log_dir: Folder of the log file; default :func:`default_log_dir`
    :type log_dir: str | None
    :param console: Also log to stderr (skipped when there is no stderr, as in the no-console exe)
    :type console: bool
    :return: Path of the log file, or None if it could not be created
    :rtype: str | None
    """
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, _OWN_HANDLER, False)]:
        root.removeHandler(handler)
        handler.close()

    root.setLevel(logging.WARNING)
    logging.getLogger(PACKAGE_LOGGER).setLevel(_resolve_level(level))
    logging.captureWarnings(True)

    handlers: list[logging.Handler] = []
    if console and sys.stderr is not None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
        handlers.append(stream_handler)

    log_path = None
    try:
        directory = log_dir or default_log_dir()
        os.makedirs(directory, exist_ok=True)
        log_path = os.path.join(directory, LOG_FILE_NAME)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        handlers.append(file_handler)
    except OSError:
        log_path = None  # read-only profile etc. — console only

    for handler in handlers:
        setattr(handler, _OWN_HANDLER, True)
        root.addHandler(handler)
    return log_path
