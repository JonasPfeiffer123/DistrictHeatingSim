"""
German messages for failed calculations (user test 2026-10-08, UT-M1).

The worker threads showed raw, often English tracebacks ("Unknown building types: nan",
"unsupported operand type(s) … 'NoneType'", "No optimization parameters available"). They now
log the traceback and show what failed, why and what to do; the traceback is in the log file.

:author: M.Eng. Jonas Pfeiffer
"""

import logging

logger = logging.getLogger(__name__)

_CONVERGENCE_HINT = (
    "Häufige Ursachen: ein getrennter Netzteil oder nicht angebundene Hausanschlüsse "
    "(Kartenansicht → Datei → „Konnektivität prüfen“), ein zu kleiner Pumpendruck oder sehr kleine Lasten."
)


def _explain(exc: BaseException) -> tuple[str, str | None]:
    """(what happened, what to do) for an exception."""
    from districtheatingsim.utilities.web_services import ServiceUnavailableError

    text = str(exc).strip()
    name = type(exc).__name__
    if isinstance(exc, ServiceUnavailableError):
        return text, None
    if isinstance(exc, FileNotFoundError):
        path = exc.filename or text
        return f"Die Datei gibt es nicht:\n{path}", "Wurde der vorherige Schritt berechnet und gespeichert?"
    if isinstance(exc, PermissionError):
        path = exc.filename or text
        return (
            f"Auf die Datei kann nicht zugegriffen werden:\n{path}",
            "Ist sie in einem anderen Programm (z. B. Excel) geöffnet?",
        )
    if isinstance(exc, MemoryError):
        return (
            "Der Arbeitsspeicher reicht nicht aus.",
            "Wählen Sie einen kürzeren Zeitraum oder die vereinfachte Berechnung.",
        )
    if "NotConverged" in name or "did not converge" in text.lower():
        return "Die hydraulische Berechnung des Netzes ist nicht konvergiert.", _CONVERGENCE_HINT
    if isinstance(exc, KeyError):
        return f"Es fehlt der Eintrag {text}.", "Prüfen Sie, ob die Eingabedatei alle Spalten enthält."
    if isinstance(exc, TypeError) and "NoneType" in text:
        return (
            "Ein benötigter Wert fehlt (leeres Feld oder ein Schritt, der noch nicht berechnet wurde).",
            "Prüfen Sie die Eingabefelder und ob die vorherigen Schritte berechnet sind.",
        )
    if isinstance(exc, (ValueError, RuntimeError)) and text:
        return text, None
    return f"{name}: {text}" if text else name, None


def describe_error(exc: BaseException, action: str, log_file: str | None = None) -> str:
    """
    German message for a failed action, without a traceback.

    :param exc: The exception.
    :param action: What failed, e.g. "Die Berechnung der Gebäudelastgänge".
    :param log_file: Where the details are (default: the application's log file).
    """
    from districtheatingsim.utilities.logging_setup import current_log_file

    explanation, hint = _explain(exc)
    lines = [f"{action} ist fehlgeschlagen.", "", explanation]
    if hint:
        lines += ["", hint]
    log_file = log_file or current_log_file()
    if log_file:
        lines += ["", f"Technische Details stehen in der Logdatei:\n{log_file}"]
    return "\n".join(lines)


def report_error(exc: BaseException, action: str) -> str:
    """Log ``exc`` with its traceback and return :func:`describe_error`'s message for the user."""
    logger.error("%s ist fehlgeschlagen", action, exc_info=(type(exc), exc, exc.__traceback__))
    return describe_error(exc, action)
