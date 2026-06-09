"""
Tests for the OSM Overpass import module configuration.

These pin the HTTP-406 fix (see BACKLOG): overpy 0.7 sends no User-Agent, so
overpass-api.de rejects the default ``Python-urllib`` UA with HTTP 406. The module
installs a global urllib opener with a descriptive User-Agent and targets the
HTTPS endpoint. Non-network tests — they assert the configuration, not a live query.
"""

from districtheatingsim.osm import import_osm_data_geojson as osm_import


def test_endpoint_is_https():
    assert osm_import.OVERPASS_ENDPOINT.startswith("https://")


def test_user_agent_is_descriptive():
    opener = osm_import._install_user_agent_opener()
    user_agents = [v for (k, v) in opener.addheaders if k.lower() == "user-agent"]
    assert user_agents, "no User-Agent header configured"
    # Must be our descriptive UA, not urllib's default (which Overpass rejects).
    assert "DistrictHeatingSim" in user_agents[0]
    assert not any("Python-urllib" in ua for ua in user_agents)
