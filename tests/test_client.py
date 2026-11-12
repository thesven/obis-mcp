from __future__ import annotations

import httpx
import pytest

from obis_mcp.client import ObisClient, ObisError


def test_client_init() -> None:
    client = ObisClient(base_url="https://api.obis.org/v3/")
    assert client.base_url == "https://api.obis.org/v3"
    assert client.timeout == 30.0


def test_fallback_taxon_and_occurrences() -> None:
    client = ObisClient(transport=httpx.MockTransport(lambda req: httpx.Response(500)))
    taxon = client.get_marine_taxon("Balaenoptera musculus")
    assert taxon["aphia_id"] == 137090
    assert taxon["is_marine"] is True

    occ = client.search_marine_occurrences("Balaenoptera musculus")
    assert occ["total_records"] == 1
    assert "Balaenoptera" in occ["records"][0]["scientific_name"]

    nearby = client.marine_occurrences_nearby(24.5, -81.8)
    assert nearby["total_records"] == 1

    checklist = client.get_marine_checklist(24.5, -81.8)
    assert len(checklist) >= 1


def test_get_marine_taxon_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v3/taxon/Delphinus delphis"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "aphia_id": 137094,
                        "scientificName": "Delphinus delphis Linnaeus, 1758",
                        "species": "Delphinus delphis",
                        "rank": "Species",
                        "family": "Delphinidae",
                        "isMarine": True,
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = ObisClient(transport=transport)
    taxon = client.get_marine_taxon("Delphinus delphis")
    assert taxon["aphia_id"] == 137094
    assert taxon["family"] == "Delphinidae"


def test_search_marine_occurrences_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v3/occurrence"
        assert request.url.params["depth"] == "10,200"
        return httpx.Response(
            200,
            json={
                "total": 1,
                "results": [
                    {
                        "id": "occ-123",
                        "scientificName": "Delphinus delphis",
                        "decimalLatitude": 36.5,
                        "decimalLongitude": -122.0,
                        "depth": 45.0,
                        "waterBody": "Monterey Bay",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = ObisClient(transport=transport)
    res = client.search_marine_occurrences(
        scientific_name="Delphinus delphis", min_depth=10, max_depth=200
    )
    assert res["total_records"] == 1
    assert res["records"][0]["water_body"] == "Monterey Bay"
    assert res["records"][0]["depth_meters"] == 45.0


def test_marine_occurrences_nearby_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "geometry" in request.url.params
        return httpx.Response(
            200,
            json={
                "total": 1,
                "results": [
                    {
                        "id": "occ-nearby-1",
                        "scientificName": "Orcinus orca",
                        "decimalLatitude": 48.5,
                        "decimalLongitude": -123.0,
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = ObisClient(transport=transport)
    res = client.marine_occurrences_nearby(
        48.5, -123.0, radius_km=30, scientific_name="Orcinus orca"
    )
    assert res["total_records"] == 1
    assert res["records"][0]["scientific_name"] == "Orcinus orca"


def test_get_marine_checklist_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v3/checklist"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "aphia_id": 137090,
                        "scientificName": "Balaenoptera musculus",
                        "records": 15,
                        "phylum": "Chordata",
                        "family": "Balaenopteridae",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = ObisClient(transport=transport)
    checklist = client.get_marine_checklist(48.5, -123.0)
    assert len(checklist) == 1
    assert checklist[0]["scientific_name"] == "Balaenoptera musculus"


def test_get_marine_depth_profile() -> None:
    # 1. Fallback depth profile
    client_fallback = ObisClient()
    prof_fallback = client_fallback.get_marine_depth_profile("Balaenoptera musculus")
    assert prof_fallback["primary_zone"] in ["epipelagic", "mesopelagic"]
    assert prof_fallback["samples_analyzed"] >= 1

    # 2. Mock API depth profile
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v3/occurrence"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"depth": 25.0},
                    {"depth": 50.0},
                    {"depth": 150.0},
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client_api = ObisClient(transport=transport)
    prof_api = client_api.get_marine_depth_profile("Sample Fish", aphia_id=999)
    assert prof_api["primary_zone"] == "epipelagic"
    assert prof_api["min_depth_meters"] == 25.0
    assert prof_api["max_depth_meters"] == 150.0


def test_error_handling() -> None:
    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="OBIS Server Error")

    client = ObisClient(transport=httpx.MockTransport(handler_500))
    with pytest.raises(ObisError, match="not found in WoRMS/OBIS"):
        client.get_marine_taxon("NonexistentSpeciesX")

    def handler_bad_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"invalid-json{")

    client2 = ObisClient(transport=httpx.MockTransport(handler_bad_json))
    with pytest.raises(ObisError, match="Invalid JSON"):
        client2.search_marine_occurrences("NonexistentSpeciesX")
