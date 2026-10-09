"""
Busy or unreachable OSM services (BACKLOG UT-H3, user test 2026-10-08).

Overpass answered "Server load too high" or dropped the connection; the building and street
downloads had one endpoint and no retry, and the user saw a raw traceback. A blocked Nominatim
was swallowed by geopy's RateLimiter, so every address looked "not found".
"""

import http.client
import urllib.error

import pytest

from districtheatingsim.utilities import web_services
from districtheatingsim.utilities.web_services import (
    OVERPASS_SERVERS,
    ServiceUnavailableError,
    call_with_retries,
    is_transient,
)


def _flaky(failures, result="ok"):
    """A request that raises the given exceptions in turn, then returns ``result``; records endpoints."""
    calls = []

    def request(endpoint):
        calls.append(endpoint)
        if len(calls) <= len(failures):
            raise failures[len(calls) - 1]
        return result

    return request, calls


class TestClassification:
    @pytest.mark.parametrize(
        "exc",
        [
            http.client.RemoteDisconnected("Remote end closed connection without response"),
            ConnectionResetError(),
            TimeoutError(),
            urllib.error.URLError("timed out"),
            urllib.error.HTTPError("u", 503, "Service Unavailable", {}, None),
        ],
    )
    def test_network_failures_are_transient(self, exc):
        assert is_transient(exc)

    def test_overpass_answers(self):
        import overpy.exception as e

        assert is_transient(e.OverpassGatewayTimeout())
        assert is_transient(e.OverpassTooManyRequests())
        assert is_transient(e.OverpassRuntimeError(msg="runtime error: Query timed out"))
        assert is_transient(e.OverpassUnknownHTTPStatusCode(502))
        assert not is_transient(e.OverpassBadRequest("[out:json];", msgs=["parse error"]))
        assert not is_transient(e.OverpassUnknownHTTPStatusCode(404))

    def test_osmnx_answers(self):
        from osmnx._errors import InsufficientResponseError, ResponseStatusCodeError

        assert is_transient(ResponseStatusCodeError("'overpass-api.de' responded: 502 Bad Gateway <html>"))
        assert is_transient(InsufficientResponseError("'overpass-api.de' responded: 200 OK <html>"))
        # An area without streets is no server problem: retrying would not help.
        assert not is_transient(InsufficientResponseError("No data elements in server response."))

    def test_requests_and_geopy(self):
        import requests
        from geopy.exc import GeocoderQueryError, GeocoderRateLimited, GeocoderUnavailable

        assert is_transient(requests.exceptions.ConnectionError())
        assert is_transient(requests.exceptions.ReadTimeout())
        too_many = requests.Response()
        too_many.status_code = 429
        not_found = requests.Response()
        not_found.status_code = 404
        assert is_transient(requests.exceptions.HTTPError(response=too_many))
        assert not is_transient(requests.exceptions.HTTPError(response=not_found))
        assert is_transient(GeocoderRateLimited("429"))
        assert is_transient(GeocoderUnavailable())
        assert not is_transient(GeocoderQueryError("bad query"))

    def test_programming_errors_are_not_transient(self):
        assert not is_transient(ValueError("Buildings GeoDataFrame is empty"))
        assert not is_transient(KeyError("UTM_X"))


class TestRetries:
    def test_each_round_asks_every_server_then_pauses(self):
        request, calls = _flaky([ConnectionResetError(), TimeoutError(), ConnectionResetError()])
        waits = []
        assert call_with_retries(request, service="Overpass", endpoints=("a", "b"), sleep=waits.append) == "ok"
        assert calls == ["a", "b", "a", "b"]
        assert waits == [web_services.RETRY_WAITS_S[0]]  # the second server is tried at once

    def test_gives_up_with_a_message_for_the_user(self):
        request, calls = _flaky([ConnectionResetError()] * 6)
        waits = []
        with pytest.raises(ServiceUnavailableError) as info:
            call_with_retries(request, service="Overpass", endpoints=("a", "b"), sleep=waits.append)
        assert calls == ["a", "b"] * 3 and waits == list(web_services.RETRY_WAITS_S)
        message = str(info.value)
        assert "Overpass" in message and "überlastet oder nicht erreichbar" in message
        assert "3-mal versucht, auch über einen Ausweichserver" in message
        assert "Traceback" not in message
        assert isinstance(info.value.__cause__, ConnectionResetError)

    def test_other_errors_propagate_at_once(self):
        request, calls = _flaky([ValueError("bad polygon")])
        with pytest.raises(ValueError, match="bad polygon"):
            call_with_retries(request, service="Overpass", sleep=lambda s: pytest.fail("waited"))
        assert len(calls) == 1


class TestOverpassBuildings:
    def test_download_retries_on_the_second_server(self, monkeypatch):
        import overpy
        import overpy.exception as e

        from districtheatingsim.osm import import_osm_data_geojson as osm_import

        urls = []
        empty = overpy.Result()

        class FakeOverpass:
            def __init__(self, url):
                self.url = url

            def query(self, query):
                urls.append(self.url)
                if len(urls) == 1:
                    raise e.OverpassGatewayTimeout()
                return empty

        monkeypatch.setattr(osm_import.overpy, "Overpass", FakeOverpass)
        monkeypatch.setattr(web_services.time, "sleep", lambda s: None)
        collection = osm_import.download_data("[out:json];", element_type="building")
        assert collection["features"] == []
        assert urls == [f"{OVERPASS_SERVERS[0]}/interpreter", f"{OVERPASS_SERVERS[1]}/interpreter"]


class TestOsmnx:
    def test_each_attempt_targets_the_next_server_and_the_setting_is_restored(self, monkeypatch):
        import osmnx as ox
        import requests

        original = ox.settings.overpass_url
        seen = []

        def request():
            seen.append(ox.settings.overpass_url)
            if len(seen) == 1:
                raise requests.exceptions.ConnectionError("Remote end closed connection")
            return "graph"

        monkeypatch.setattr(web_services.time, "sleep", lambda s: None)
        assert web_services.osmnx_with_retries(request) == "graph"
        assert seen == list(OVERPASS_SERVERS)
        assert ox.settings.overpass_url == original


class TestNominatim:
    @pytest.fixture
    def nominatim(self, monkeypatch):
        """The real rate limiter around a fake Nominatim, without pauses."""
        from districtheatingsim.geocoding import geocoding

        monkeypatch.setattr(geocoding._geocode, "_sleep", lambda seconds: None)
        monkeypatch.setattr(geocoding._geocode, "min_delay_seconds", 0)

        def answer(result):
            def geocode(address):
                if isinstance(result, Exception):
                    raise result
                return result

            monkeypatch.setattr(geocoding._geocode, "func", geocode)

        return geocoding, answer

    def test_blocked_nominatim_is_reported_not_swallowed(self, nominatim):
        from geopy.exc import GeocoderRateLimited

        geocoding, answer = nominatim
        answer(GeocoderRateLimited("Non-successful status code 429"))
        with pytest.raises(ServiceUnavailableError, match="Nominatim"):
            geocoding.get_coordinates("Markt 1, Zittau", to_crs="EPSG:25833")

    def test_unknown_address_is_still_not_found(self, nominatim):
        from geopy.exc import GeocoderQueryError

        geocoding, answer = nominatim
        answer(None)
        assert geocoding.get_coordinates("Nirgendwo 1", to_crs="EPSG:25833") == (None, None)
        answer(GeocoderQueryError("bad request"))
        assert geocoding.get_coordinates("???", to_crs="EPSG:25833") == (None, None)

    def test_geocoding_run_leaves_the_csv_unchanged(self, tmp_path, monkeypatch):
        from districtheatingsim.geocoding import geocoding

        path = tmp_path / "Quartier IST.csv"
        content = "Land;Bundesland;Stadt;Adresse\nDeutschland;Sachsen;Zittau;Markt 1\n"
        path.write_text(content, encoding="utf-8-sig")

        def blocked(address, to_crs=None):
            raise ServiceUnavailableError("gesperrt")

        monkeypatch.setattr(geocoding, "get_coordinates", blocked)
        with pytest.raises(ServiceUnavailableError):
            geocoding.process_data(str(path), crs="EPSG:25833")
        assert path.read_text(encoding="utf-8-sig") == content


class TestThreads:
    def test_geocoding_thread_shows_the_message_without_traceback(self, qapp, monkeypatch):
        from districtheatingsim.gui.LeafletTab import net_generation_threads as threads

        def blocked(path, crs):
            raise ServiceUnavailableError("Der Adressdienst von OpenStreetMap (Nominatim) antwortet nicht.")

        monkeypatch.setattr(threads, "process_data", blocked)
        thread = threads.GeocodingThread("Quartier IST.csv", "EPSG:25833")
        errors = []
        thread.calculation_error.connect(errors.append)
        thread.run()
        assert errors == ["Der Adressdienst von OpenStreetMap (Nominatim) antwortet nicht."]

    def test_download_thread_shows_the_message_without_traceback(self, qapp):
        from districtheatingsim.gui.LeafletTab.net_generation_threads import OSMBuildingDownloadThread

        def busy():
            raise ServiceUnavailableError("Der OpenStreetMap-Server (Overpass) ist gerade überlastet.")

        thread = OSMBuildingDownloadThread(busy)
        errors = []
        thread.download_error.connect(errors.append)
        thread.run()
        assert errors == ["Der OpenStreetMap-Server (Overpass) ist gerade überlastet."]
