from __future__ import annotations

import argparse
import sys
from typing import Any

from mcp.server import MCPServer

from . import __version__
from .client import ObisClient, ObisError

DEFAULT_INSTRUCTIONS = """
OBIS MCP Server: Query marine biodiversity occurrence data, ocean depth profiles,
and World Register of Marine Species (WoRMS) classifications from the Ocean Biodiversity
Information System (OBIS).

Key Best Practices:
1. When investigating a marine organism, call `get_marine_taxon` to verify whether it is an
   accepted marine species, obtain its WoRMS AphiaID, and inspect higher classification.
2. Call `search_marine_occurrences` to query marine records with optional `min_depth` and
   `max_depth` constraints in meters (e.g. epipelagic 0-200m, mesopelagic 200-1000m).
3. Call `marine_occurrences_nearby` with marine GPS coordinates (`lat`, `lon`, `radius_km`)
   to search pelagic and benthic sightings around reefs, oceanic trenches, or coastal zones.
4. Call `get_marine_checklist` to survey dominant marine species recorded near ocean coordinates.
""".strip()


def _format_marine_summary(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No marine occurrence records found."
    lines = []
    for r in records[:10]:
        name = r.get("scientific_name") or "Unknown marine taxon"
        d = r.get("depth_meters")
        depth = f"at {d}m depth" if d is not None else "depth unstated"
        loc = r.get("locality") or r.get("water_body") or "open ocean"
        date = r.get("event_date") or "date unknown"
        lines.append(f"- {name} ({depth}) in {loc} on {date}")
    return "\n".join(lines)


def create_server(client: ObisClient | None = None) -> MCPServer:
    """Create and configure the OBIS MCPServer instance."""
    api = client or ObisClient()

    server = MCPServer(
        "obis",
        version=__version__,
        instructions=DEFAULT_INSTRUCTIONS,
    )

    @server.tool()
    def get_marine_taxon(scientific_name: str) -> dict[str, Any]:
        """Look up WoRMS AphiaID and marine taxonomic classification for a species."""
        try:
            taxon = api.get_marine_taxon(scientific_name=scientific_name)
            name = taxon.get("scientific_name") or taxon.get("canonical_name")
            aphia = taxon.get("aphia_id")
            fam = taxon.get("family") or "Unknown family"
            summary = (
                f"{name} (WoRMS AphiaID: {aphia}) | Family: {fam} | "
                f"Marine: {taxon.get('is_marine')}"
            )
            return {"taxon": taxon, "summary": summary}
        except ObisError as exc:
            return {"error": str(exc), "summary": f"Marine taxon lookup failed: {exc}"}

    @server.tool()
    def search_marine_occurrences(
        scientific_name: str | None = None,
        aphia_id: int | None = None,
        min_depth: float | None = None,
        max_depth: float | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search ocean species occurrences with depth bounds and taxonomic filters."""
        try:
            res = api.search_marine_occurrences(
                scientific_name=scientific_name,
                aphia_id=aphia_id,
                min_depth=min_depth,
                max_depth=max_depth,
                limit=limit,
            )
            res["summary"] = _format_marine_summary(res["records"])
            return res
        except ObisError as exc:
            return {
                "error": str(exc),
                "records": [],
                "count": 0,
                "summary": f"Marine query failed: {exc}",
            }

    @server.tool()
    def marine_occurrences_nearby(
        lat: float,
        lon: float,
        radius_km: int = 50,
        scientific_name: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search marine records within a spatial polygon around ocean GPS coordinates."""
        try:
            res = api.marine_occurrences_nearby(
                lat=lat, lon=lon, radius_km=radius_km, scientific_name=scientific_name, limit=limit
            )
            res["summary"] = _format_marine_summary(res["records"])
            return res
        except ObisError as exc:
            return {
                "error": str(exc),
                "records": [],
                "count": 0,
                "summary": f"Nearby marine search failed: {exc}",
            }

    @server.tool()
    def get_marine_checklist(
        lat: float,
        lon: float,
        radius_km: int = 50,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Retrieve checklist of marine species observed around oceanic coordinates."""
        try:
            checklist = api.get_marine_checklist(lat=lat, lon=lon, radius_km=radius_km, limit=limit)
            lines = [
                f"- {item.get('scientific_name')} ({item.get('records_count', 0)} records) "
                f"[AphiaID: {item.get('aphia_id')}]"
                for item in checklist[:10]
            ]
            summary = "\n".join(lines) if lines else "No marine species checklist records found."
            return {"checklist": checklist, "count": len(checklist), "summary": summary}
        except ObisError as exc:
            return {
                "error": str(exc),
                "checklist": [],
                "count": 0,
                "summary": f"Checklist lookup failed: {exc}",
            }

    @server.tool()
    def get_marine_depth_profile(
        scientific_name: str, aphia_id: int | None = None
    ) -> dict[str, Any]:
        """Classify marine occurrences across oceanic bathymetric zones (0-200m, 200-1000m)."""
        try:
            profile = api.get_marine_depth_profile(
                scientific_name=scientific_name, aphia_id=aphia_id
            )
            summary = (
                f"Depth profile for {scientific_name}: {profile.get('min_depth_meters')}m to "
                f"{profile.get('max_depth_meters')}m depth "
                f"(Primary zone: {profile.get('primary_zone_label')})"
            )
            return {"depth_profile": profile, "summary": summary}
        except ObisError as exc:
            return {"error": str(exc), "summary": f"Depth profile lookup failed: {exc}"}

    @server.tool()
    def get_marine_environmental_parameters(
        scientific_name: str, aphia_id: int | None = None
    ) -> dict[str, Any]:
        """Extract ocean salinity, water temperature, and dissolved oxygen profiles."""
        try:
            env = api.get_marine_environmental_parameters(
                scientific_name=scientific_name, aphia_id=aphia_id
            )
            t = env.get("temperature_celsius", {})
            s = env.get("salinity_psu", {})
            summary = (
                f"Environmental parameters for {scientific_name}: "
                f"SST {t.get('min')}°C to {t.get('max')}°C (mean {t.get('mean')}°C) | "
                f"Salinity {s.get('min')} to {s.get('max')} PSU (mean {s.get('mean')} PSU)"
            )
            return {"environmental_parameters": env, "summary": summary}
        except ObisError as exc:
            return {"error": str(exc), "summary": f"Environmental lookup failed: {exc}"}

    @server.tool()
    def get_ocean_area_statistics(area_name: str) -> dict[str, Any]:
        """Retrieve marine biodiversity statistics and occurrence totals for an oceanic basin."""
        try:
            stats = api.get_ocean_area_statistics(area_name=area_name)
            name = stats.get("area_name", area_name)
            sp = stats.get("species_count") or stats.get("total_species", "N/A")
            occ = stats.get("total_occurrences") or stats.get("total_records", "N/A")
            summary = f"Ocean Area: {name} | Species Richness: {sp:,} | Total Occurrences: {occ:,}"
            return {"statistics": stats, "summary": summary}
        except ObisError as exc:
            return {"error": str(exc), "summary": f"Ocean area query failed: {exc}"}

    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="obis-mcp",
        description="Model Context Protocol (MCP) server for OBIS marine biodiversity",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for SSE transport (default: 8000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = create_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="sse", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
