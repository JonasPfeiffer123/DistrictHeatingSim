"""
Plausibility checks of calculation results (traffic light)
===========================================================

GUI-free checks of a calculated network and generator mix. Each check returns the value, a
rating and a German hint naming the threshold and where it comes from, so an implausible
result - a 773 m² collector field with a 16 m³ storage, network losses of 40 % - is visible
next to the numbers instead of being taken at face value (user test 2026-10-08, M15).

Ratings: ``"ok"`` (green), ``"warn"`` (yellow), ``"bad"`` (red) and ``"info"`` (no rating,
where no reliable threshold exists).

:author: M.Eng. Jonas Pfeiffer
"""

from dataclasses import dataclass

import numpy as np

from districtheatingsim.constants import SOLAR_STORAGE_MIN_L_PER_M2

#: Network heat loss share of the generation [%]: QM Holzheizwerke asks for at most 10 %.
LOSS_SHARE_OK = 10.0
LOSS_SHARE_WARN = 20.0

#: Linear heat density [MWh/(m·a)]: QM Holzheizwerke asks for at least 1.8; the former KfW
#: funding of heat networks (Marktanreizprogramm) required at least 0.5.
HEAT_DENSITY_OK = 1.8
HEAT_DENSITY_WARN = 0.5

#: Storage volume per m² collector [l/m²]: a daily storage holds about 50-100 l/m² (the optimizer's
#: lower limit); below 25 l/m² the storage overflows on most sunny days.
SOLAR_STORAGE_OK = SOLAR_STORAGE_MIN_L_PER_M2
SOLAR_STORAGE_WARN = 25.0


#: German label and colour of each rating, shared by the views.
RATING_LABELS = {"ok": "● plausibel", "warn": "● prüfen", "bad": "● unplausibel", "info": "Information"}
RATING_COLORS = {"ok": "#27ae60", "warn": "#e67e22", "bad": "#c0392b", "info": "#7f8c8d"}


@dataclass(frozen=True)
class PlausibilityCheck:
    """One checked indicator."""

    name: str
    value: float
    unit: str
    rating: str
    hint: str


def _de(value: float, digits: int) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def _rate_high_is_good(value: float, ok: float, warn: float) -> str:
    if value >= ok:
        return "ok"
    return "warn" if value >= warn else "bad"


def _rate_low_is_good(value: float, ok: float, warn: float) -> str:
    if value <= ok:
        return "ok"
    return "warn" if value <= warn else "bad"


def network_checks(
    kpis: dict, max_loss_pa_per_m: float | None = None, loss_limit_pa_per_m: float | None = None
) -> list[PlausibilityCheck]:
    """
    Checks of a calculated network.

    :param kpis: ``NetworkGenerationData.calculate_results()``.
    :param max_loss_pa_per_m: Highest specific friction pressure loss of the design state [Pa/m].
    :param loss_limit_pa_per_m: Pressure loss limit of the diameter sizing [Pa/m], if any.
    :return: The checks whose inputs are available.
    """
    checks = []
    share = kpis.get("rel. Verteilverluste [%]")
    # Only a time series over the whole year gives a loss share (a part of the year compares
    # its generation with the annual demand)
    if share is not None and np.isfinite(share) and 0 <= share < 100:
        checks.append(
            PlausibilityCheck(
                "Wärmeverluste des Netzes",
                share,
                "%",
                _rate_low_is_good(share, LOSS_SHARE_OK, LOSS_SHARE_WARN),
                f"Anteil an der erzeugten Wärme. QM Holzheizwerke fordert höchstens {LOSS_SHARE_OK:.0f} %; "
                f"über {LOSS_SHARE_WARN:.0f} % ist das Netz für den Bedarf zu lang oder zu groß dimensioniert.",
            )
        )
    density = kpis.get("Wärmebedarfsdichte [MWh/(a*m)]")
    if density is not None and np.isfinite(density):
        checks.append(
            PlausibilityCheck(
                "Wärmebelegungsdichte",
                density,
                "MWh/(m·a)",
                _rate_high_is_good(density, HEAT_DENSITY_OK, HEAT_DENSITY_WARN),
                f"Jahreswärmebedarf je Meter Trasse. QM Holzheizwerke fordert mindestens "
                f"{_de(HEAT_DENSITY_OK, 1)}; die frühere KfW-Förderung verlangte mindestens {_de(HEAT_DENSITY_WARN, 1)}.",
            )
        )
    if max_loss_pa_per_m is not None and np.isfinite(max_loss_pa_per_m):
        if loss_limit_pa_per_m:
            rating = "ok" if max_loss_pa_per_m <= loss_limit_pa_per_m * 1.01 else "warn"
            hint = (
                f"Höchster Druckverlust durch Reibung einer Leitung; Grenze der Durchmesserauslegung "
                f"{loss_limit_pa_per_m:.0f} Pa/m. Darüber liegen nur Leitungen in der größten Nennweite "
                "oder Netze ohne Durchmesseroptimierung."
            )
        else:
            rating = "info"
            hint = "Höchster Druckverlust durch Reibung einer Leitung (ohne Grenze ausgelegt)."
        checks.append(PlausibilityCheck("Spezifischer Druckverlust", max_loss_pa_per_m, "Pa/m", rating, hint))
    return checks


def generator_checks(technologies, results: dict) -> list[PlausibilityCheck]:
    """
    Checks of a calculated generator mix.

    :param technologies: The technologies of the energy system (in result order).
    :param results: ``EnergySystem.results`` after ``calculate_mix``.
    :return: Storage per collector area of every solar thermal plant, full-load hours of every
        generator that delivers heat.
    """
    checks = []
    for tech in technologies:
        area = getattr(tech, "bruttofläche_STA", None)
        volume = getattr(tech, "vs", None)
        if area and volume is not None and area > 0:
            litres = volume * 1000.0 / area
            checks.append(
                PlausibilityCheck(
                    f"{tech.name}: Speicher je m² Kollektor",
                    litres,
                    "l/m²",
                    _rate_high_is_good(litres, SOLAR_STORAGE_OK, SOLAR_STORAGE_WARN),
                    f"{_de(volume, 0)} m³ Speicher für {_de(area, 0)} m² Kollektor. Ein Tagesspeicher hat "
                    f"etwa 50-100 l/m²; unter {SOLAR_STORAGE_WARN:.0f} l/m² läuft er an den meisten Sonnentagen "
                    "über (Stagnation).",
                )
            )

    names = list(results.get("techs", []))
    amounts = list(results.get("Wärmemengen", []))
    profiles = list(results.get("Wärmeleistung_L", []))
    for name, amount_mwh, profile in zip(names, amounts, profiles, strict=False):
        peak_kw = float(np.max(profile)) if np.size(profile) else 0.0
        if name == "Ungedeckter Bedarf" or peak_kw <= 0 or not amount_mwh:
            continue
        hours = float(np.sum(amount_mwh)) * 1000.0 / peak_kw
        checks.append(
            PlausibilityCheck(
                f"{name}: Volllaststunden",
                hours,
                "h/a",
                "info",
                "Jahreswärmemenge geteilt durch die höchste Stundenleistung im Jahr. Grundlasterzeuger "
                "(BHKW, Biomasse, Wärmepumpe) mit wenigen tausend Stunden sind meist zu groß ausgelegt.",
            )
        )
    return checks


def format_value(check: PlausibilityCheck) -> str:
    """The value with a German decimal comma and its unit."""
    digits = 2 if check.unit == "MWh/(m·a)" else (1 if check.unit == "%" else 0)
    return f"{_de(check.value, digits)} {check.unit}"
