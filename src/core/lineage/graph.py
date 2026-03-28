"""NetworkX DAG builder for lineage visualization.

Builds a directed acyclic graph from lineage events and exports
to Mermaid format for documentation.
"""

from __future__ import annotations

import networkx as nx  # type: ignore[import-untyped]

from src.core.lineage.events import HealthcareLineageEvent, RunState


def build_lineage_dag(events: list[HealthcareLineageEvent]) -> nx.DiGraph:
    """Build a directed graph from lineage events.

    Nodes: agents + data assets
    Edges: data flow (input -> agent -> output)
    """
    g = nx.DiGraph()

    for event in events:
        if event.event_type not in (RunState.COMPLETE, RunState.FAIL):
            continue

        agent_node = f"{event.agent_id}:{event.job_name}"
        g.add_node(
            agent_node,
            type="agent",
            agent_id=event.agent_id,
            job_name=event.job_name,
            status=event.event_type.value,
        )

        for inp in event.inputs:
            dataset_node = f"{inp.namespace}/{inp.name}"
            g.add_node(dataset_node, type="dataset", namespace=inp.namespace)
            g.add_edge(dataset_node, agent_node)

        for out in event.outputs:
            dataset_node = f"{out.namespace}/{out.name}"
            g.add_node(dataset_node, type="dataset", namespace=out.namespace)
            g.add_edge(agent_node, dataset_node)

        # Parent-child edges between agent operations
        if event.parent_run_id:
            parent_events = [
                e
                for e in events
                if e.run_id == event.parent_run_id
                and e.event_type in (RunState.COMPLETE, RunState.FAIL)
            ]
            for parent in parent_events:
                parent_node = f"{parent.agent_id}:{parent.job_name}"
                if parent_node in g and agent_node in g:
                    g.add_edge(parent_node, agent_node, type="delegation")

    return g


def validate_dag(g: nx.DiGraph) -> bool:
    """Verify the lineage graph is a valid DAG (no cycles)."""
    return bool(nx.is_directed_acyclic_graph(g))


def export_mermaid(g: nx.DiGraph) -> str:
    """Export the lineage graph as a Mermaid diagram."""
    lines = ["graph LR"]

    for node, data in g.nodes(data=True):
        safe_node = node.replace("/", "_").replace(":", "_").replace(" ", "_")
        if data.get("type") == "agent":
            lines.append(f'    {safe_node}["{node}"]')
        else:
            lines.append(f'    {safe_node}[("{node}")]')

    for u, v, data in g.edges(data=True):
        safe_u = u.replace("/", "_").replace(":", "_").replace(" ", "_")
        safe_v = v.replace("/", "_").replace(":", "_").replace(" ", "_")
        if data.get("type") == "delegation":
            lines.append(f"    {safe_u} -.-> {safe_v}")
        else:
            lines.append(f"    {safe_u} --> {safe_v}")

    return "\n".join(lines)
