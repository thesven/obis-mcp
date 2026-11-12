from __future__ import annotations

import httpx
import pytest

from obis_mcp.client import ObisClient
from obis_mcp.server import create_server


@pytest.fixture
def mock_client() -> ObisClient:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/taxon/" in path:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "aphia_id": 137090,
                            "scientificName": "Balaenoptera musculus",
                            "family": "Balaenopteridae",
                            "isMarine": True,
                        }
                    ]
                },
            )
        if "/occurrence" in path:
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "results": [
                        {
                            "id": "1",
                            "scientificName": "Balaenoptera musculus",
                            "depth": 50.0,
                            "waterBody": "Pacific Ocean",
                            "eventDate": "2024-01-01",
                        }
                    ],
                },
            )
        if "/checklist" in path:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "aphia_id": 137090,
                            "scientificName": "Balaenoptera musculus",
                            "records": 10,
                        }
                    ]
                },
            )
        return httpx.Response(404, text="Not Found")

    return ObisClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def failing_client() -> ObisClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Server Error")

    return ObisClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_server_tools(mock_client: ObisClient) -> None:
    server = create_server(mock_client)

    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert "get_marine_taxon" in tool_names
    assert "search_marine_occurrences" in tool_names
    assert "marine_occurrences_nearby" in tool_names
    assert "get_marine_checklist" in tool_names
    assert "get_marine_depth_profile" in tool_names

    res = await server.call_tool("get_marine_taxon", {"scientific_name": "Balaenoptera musculus"})
    assert "Balaenoptera musculus" in res.content[0].text

    res = await server.call_tool(
        "search_marine_occurrences", {"scientific_name": "Balaenoptera musculus"}
    )
    assert "Pacific Ocean" in res.content[0].text

    res = await server.call_tool(
        "marine_occurrences_nearby", {"lat": 20.0, "lon": -156.0, "radius_km": 50}
    )
    assert "Pacific Ocean" in res.content[0].text

    res = await server.call_tool(
        "get_marine_checklist", {"lat": 20.0, "lon": -156.0, "radius_km": 50}
    )
    assert "Balaenoptera musculus" in res.content[0].text

    res = await server.call_tool(
        "get_marine_depth_profile", {"scientific_name": "Balaenoptera musculus"}
    )
    assert "Depth profile" in res.content[0].text


@pytest.mark.asyncio
async def test_server_tool_errors(failing_client: ObisClient) -> None:
    server = create_server(failing_client)

    res = await server.call_tool("get_marine_taxon", {"scientific_name": "NonexistentUnknownFish"})
    assert "failed" in res.content[0].text

    res = await server.call_tool(
        "search_marine_occurrences", {"scientific_name": "NonexistentUnknownFish"}
    )
    assert "failed" in res.content[0].text

    res = await server.call_tool(
        "get_marine_depth_profile", {"scientific_name": "NonexistentUnknownFish"}
    )
    assert "Depth profile" in res.content[0].text or "failed" in res.content[0].text
