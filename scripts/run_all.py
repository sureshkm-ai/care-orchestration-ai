"""Launch all local services (2 MCP servers + 2 A2A agents).

Services (once implemented):
  - FHIR MCP Server      :8001
  - Scheduling MCP Server :8003
  - Triage Agent          :9001
  - Care Coordinator Agent:9002

Currently a placeholder that validates configuration and seeds
data. The actual service processes will be added in Phase 2.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import get_settings
from src.core.observability.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

SERVICE_MAP = {
    "FHIR MCP Server": (
        "src.mcp_servers.fhir",
        settings.fhir_mcp_port,
    ),
    "Scheduling MCP Server": (
        "src.mcp_servers.scheduling",
        settings.scheduling_mcp_port,
    ),
    "Triage Agent": (
        "src.agents.triage",
        settings.triage_agent_port,
    ),
    "Care Coordinator Agent": (
        "src.agents.care_coordinator",
        settings.care_coordinator_agent_port,
    ),
}


def main() -> None:
    print("=" * 60)
    print("  Care Orchestration AI - Local Runner")
    print("=" * 60)
    print()
    print(f"  Environment : {settings.app_env.value}")
    print(f"  Log level   : {settings.log_level}")
    print(f"  Database dir: {settings.db_dir}")
    print()

    print("  Services:")
    for name, (module, port) in SERVICE_MAP.items():
        print(f"    {name:<28} :{port}  ({module})")
    print()

    # Check that databases exist
    fhir_db = settings.db_dir / "fhir.db"
    sched_db = settings.db_dir / "scheduling.db"
    if not fhir_db.exists() or not sched_db.exists():
        print("  [!] Databases not found. Run 'make seed' first.")
        print()
        sys.exit(1)

    print(
        "  Phase 2 will launch the services above via "
        "uvicorn / MCP stdio.\n"
        "  For now, run 'make test' to exercise the "
        "core infrastructure.\n"
    )


if __name__ == "__main__":
    main()
