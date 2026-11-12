# obis-mcp

[![CI](https://github.com/thesven/obis-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/thesven/obis-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A dedicated marine ecology and oceanography **Model Context Protocol (MCP)** server for the [Ocean Biodiversity Information System (OBIS) API v3](https://api.obis.org/).

Fills the oceanic and pelagic data gap in terrestrial biodiversity collections (iNaturalist, eBird) by providing direct access to ocean depth profiling, World Register of Marine Species (WoRMS) classifications, and marine species occurrences.

---

## Key Features

- **Bathymetric Depth Profiling**: Classifies species observations across sunlight (epipelagic 0–200m), twilight (mesopelagic 200–1000m), and midnight (bathypelagic >1000m) oceanic zones.
- **Ocean Depth & Bathymetric Filtering**: Query occurrences constrained by water column depth (`min_depth` and `max_depth` in meters), differentiating epipelagic, mesopelagic, bathypelagic, and benthic habitats.
- **WoRMS Taxonomic Authority**: Resolve marine species names to official World Register of Marine Species (WoRMS) AphiaIDs and verify marine status.
- **Geographic Ocean Boundaries**: Query marine biodiversity around offshore coordinates, marine protected areas, and coral reef ecosystems using polygon spatial filters.
- **Ocean Species Checklists**: Survey dominant marine taxa recorded in oceanic quadrants.
- **Zero-Credential Access**: Works out of the box using OBIS open REST API v3.

---

## Available Tools

| Tool | Description |
| :--- | :--- |
| `get_marine_taxon` | Look up WoRMS AphiaID and marine taxonomic classification for a species. |
| `get_marine_depth_profile` | Classify marine occurrences across oceanic bathymetric zones (0-200m, 200-1000m). |
| `get_marine_environmental_parameters` | Extract ocean salinity, water temperature, and dissolved oxygen profiles for a marine taxon. |
| `get_ocean_area_statistics` | Retrieve marine biodiversity statistics and occurrence totals for an oceanic basin or MPA. |
| `search_marine_occurrences` | Search ocean species occurrences with depth bounds and taxonomic filters. |
| `marine_occurrences_nearby` | Search marine records within a spatial polygon around ocean GPS coordinates. |
| `get_marine_checklist` | Retrieve a checklist of marine species observed around oceanic coordinates. |

---

## Installation & Usage

### Running with `uvx` (Recommended)

```bash
uvx --from git+https://github.com/thesven/obis-mcp.git obis-mcp
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obis": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/thesven/obis-mcp.git", "obis-mcp"]
    }
  }
}
```

---

## Development & Quality Gate

```bash
# Run code formatting check
uv run ruff format --check src tests scripts

# Run linting
uv run ruff check src tests scripts

# Run test suite with strict coverage floor (>90%)
uv run pytest --cov=obis_mcp --cov-branch --cov-report=term-missing

# Build wheel and sdist
uv build

# Run package distribution check & smoke test
uv run python scripts/check_dist.py
uv run python scripts/smoke.py
```

## License

MIT License. See [LICENSE](LICENSE) for details.
