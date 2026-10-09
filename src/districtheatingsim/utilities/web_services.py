"""
Calls to the public OpenStreetMap services (Overpass, Nominatim).

The public servers are shared and often busy: Overpass answers "Server load too high" or drops
the connection, Nominatim blocks a client that asks too fast. Users saw raw tracebacks for this
(BACKLOG UT-H3). This module retries transient failures in rounds - each round asks every server,
for Overpass also a second public instance - with a pause between the rounds, and turns a final
failure into :class:`ServiceUnavailableError`, whose message is meant for the user.

GUI-free; the HTTP libraries are imported lazily.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import http.client
import logging
import time
import urllib.error
from collections.abc import Callable, Sequence
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Public Overpass servers (base URL; overpy appends ``/interpreter``, OSMnx adds the endpoint
#: itself). The main server first; private.coffee is a public instance listed on the OSM wiki.
OVERPASS_SERVERS = ("https://overpass-api.de/api", "https://overpass.private.coffee/api")

#: Pauses before the second and the third round [s]. A busy Overpass often answers again within a
#: minute (its backends alternate between 200 and 504 under load).
RETRY_WAITS_S = (15.0, 45.0)

_SERVICE_NAMES = {
    "Overpass": "Der OpenStreetMap-Server (Overpass)",
    "Nominatim": "Der Adressdienst von OpenStreetMap (Nominatim)",
}

_TRANSIENT_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})


class ServiceUnavailableError(RuntimeError):
    """A public web service failed after all retries; ``str()`` is a German message for the user."""


def is_transient(exc: BaseException) -> bool:
    """
    True if ``exc`` is a busy or unreachable server, which may work a little later.

    A bad query, an unknown place or an empty result are not transient.
    """
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _TRANSIENT_HTTP_STATUS
    if isinstance(exc, (ConnectionError, TimeoutError, urllib.error.URLError, http.client.HTTPException)):
        return True

    try:
        import requests

        if isinstance(exc, requests.exceptions.HTTPError):
            response = exc.response
            return response is not None and response.status_code in _TRANSIENT_HTTP_STATUS
        if isinstance(
            exc,
            (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ),
        ):
            return True
    except ImportError:  # pragma: no cover - requests comes with osmnx/geopy
        pass

    try:
        import overpy.exception as overpy_exc

        if isinstance(
            exc,
            (
                overpy_exc.OverpassTooManyRequests,
                overpy_exc.OverpassGatewayTimeout,
                overpy_exc.OverpassRuntimeError,  # "runtime error: Query timed out / out of memory"
                overpy_exc.OverpassUnknownContentType,  # an HTML error page instead of JSON
                overpy_exc.MaxRetriesReached,
            ),
        ):
            return True
        if isinstance(exc, overpy_exc.OverpassUnknownHTTPStatusCode):
            return exc.code in _TRANSIENT_HTTP_STATUS
    except ImportError:  # pragma: no cover
        pass

    try:
        from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError

        if isinstance(exc, ResponseStatusCodeError):
            return True
        # A non-JSON answer with status OK is a server problem; "No data elements" is an empty area.
        if isinstance(exc, InsufficientResponseError):
            return "responded:" in str(exc)
    except ImportError:  # pragma: no cover
        pass

    try:
        import geopy.exc as geopy_exc

        if isinstance(exc, (geopy_exc.GeocoderRateLimited, geopy_exc.GeocoderUnavailable, geopy_exc.GeocoderTimedOut)):
            return True
    except ImportError:  # pragma: no cover
        pass

    return False


def describe_service_error(service: str, exc: BaseException, attempts: int = 1, servers: int = 1) -> str:
    """
    German message for a failed call to ``service`` ('Overpass' or 'Nominatim').

    :param attempts: How often the call was tried (rounds).
    :param servers: How many servers each round asked.
    """
    name = _SERVICE_NAMES.get(service, f"Der Dienst {service}")
    tried = f" Es wurde {attempts}-mal versucht" if attempts > 1 else ""
    if tried:
        tried += ", auch über einen Ausweichserver." if servers > 1 else "."
    if service == "Nominatim":
        what = "antwortet nicht oder hat weitere Anfragen vorübergehend gesperrt."
    else:
        what = "ist gerade überlastet oder nicht erreichbar."
    return (
        f"{name} {what}{tried}\n\n"
        "Das liegt nicht an Ihren Daten. Bitte versuchen Sie es in einigen Minuten erneut.\n\n"
        f"(Technisch: {type(exc).__name__}: {str(exc)[:300]})"
    )


def call_with_retries(
    func: Callable[[str | None], T],
    *,
    service: str,
    endpoints: Sequence[str | None] = (None,),
    waits: Sequence[float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> T:
    """
    Call ``func(endpoint)`` until it succeeds; transient failures are retried in rounds.

    Each round tries every endpoint in order, without a pause, so a broken second server costs the
    main server no attempt; between the rounds the call pauses. Other exceptions propagate unchanged.

    :param func: The request; receives the endpoint of this attempt.
    :param service: 'Overpass' or 'Nominatim' (for the message).
    :param endpoints: Endpoints in the order to try (``None`` = the library's default).
    :param waits: Pause before each further round [s]; ``len(waits) + 1`` rounds in total
        (default :data:`RETRY_WAITS_S`).
    :param sleep: Pause function (default ``time.sleep``).
    :raises ServiceUnavailableError: When every attempt failed transiently.
    """
    waits = RETRY_WAITS_S if waits is None else waits
    sleep = sleep or time.sleep
    rounds = len(waits) + 1
    for round_index in range(rounds):
        if round_index:
            sleep(waits[round_index - 1])
        for endpoint in endpoints:
            try:
                return func(endpoint)
            except Exception as exc:
                if not is_transient(exc):
                    raise
                logger.warning("%s round %d/%d (%s) failed: %r", service, round_index + 1, rounds, endpoint, exc)
                last = exc
    raise ServiceUnavailableError(describe_service_error(service, last, rounds, len(endpoints))) from last


def osmnx_with_retries(request: Callable[[], T]) -> T:
    """
    Run an OSMnx download (``graph_from_place``, ``graph_from_polygon`` …) with retries.

    OSMnx itself only waits on HTTP 429/504; a dropped connection or a non-JSON error page
    raised at once. Each attempt points OSMnx at the next server of :data:`OVERPASS_SERVERS`.
    """
    import osmnx as ox

    original = ox.settings.overpass_url

    def attempt(server: str | None) -> T:
        ox.settings.overpass_url = server or original
        return request()

    try:
        return call_with_retries(attempt, service="Overpass", endpoints=OVERPASS_SERVERS)
    finally:
        ox.settings.overpass_url = original
