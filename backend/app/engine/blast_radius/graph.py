"""
Pipeline graph builder.

Constructs a directed graph representing the AI pipeline topology
from a PipelineProfile and optional explicit topology overlay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import re

import networkx as nx

from app.engine.recognition.fingerprinter import PipelineProfile
from app.engine.recognition.signatures import FrameworkType

# Criticality weights — used by the calculator to amplify scores
NODE_CRITICALITY: dict[str, float] = {
    # High-impact tools / integrations
    "database":      1.0,
    "sql":           1.0,
    "postgres":      1.0,
    "mysql":         1.0,
    "mongodb":       0.9,
    "filesystem":    0.9,
    "file":          0.8,
    "exec":          1.0,
    "shell":         1.0,
    "bash":          1.0,
    "code":          0.9,
    "email":         0.8,
    "smtp":          0.8,
    "http":          0.7,
    "requests":      0.7,
    "browser":       0.8,
    "search":        0.6,
    "memory":        0.7,
    "vector":        0.6,
    "retriever":     0.6,
    "agent":         0.8,
    "llm":           0.7,
    "chat":          0.5,
    "api":           0.6,
    # Low-impact
    "input":         0.3,
    "output":        0.3,
    "parser":        0.4,
    "formatter":     0.2,
}

_DEFAULT_CRITICALITY = 0.4


def _tool_criticality(tool_name: str) -> float:
    name = tool_name.lower()
    # Exact match first
    if name in NODE_CRITICALITY:
        return NODE_CRITICALITY[name]
    # Partial match
    for key, weight in NODE_CRITICALITY.items():
        if key in name:
            return weight
    return _DEFAULT_CRITICALITY


@dataclass
class PipelineNode:
    id:          str
    label:       str
    node_type:   str = "tool"   # tool | endpoint | agent | llm | unknown
    criticality: float = _DEFAULT_CRITICALITY
    metadata:    dict  = field(default_factory=dict)


class PipelineGraph:
    """
    Directed graph of a pipeline's components.

    Nodes carry criticality weights; edges represent data flow or
    invocation dependencies.
    """

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()

    def add_node(self, node: PipelineNode) -> None:
        self.graph.add_node(
            node.id,
            label=node.label,
            node_type=node.node_type,
            criticality=node.criticality,
            metadata=node.metadata,
        )

    def add_edge(self, src: str, dst: str, weight: float = 1.0) -> None:
        self.graph.add_edge(src, dst, weight=weight)

    @classmethod
    def from_profile(
        cls,
        profile: PipelineProfile,
        extra_topology: dict | None = None,
    ) -> "PipelineGraph":
        pg = cls()

        # ── Entry node (the invoke endpoint) ─────────────────────────
        entry_id = "entry"
        pg.add_node(PipelineNode(
            id=entry_id,
            label="Pipeline Entry",
            node_type="endpoint",
            criticality=0.5,
        ))

        # ── LLM node ─────────────────────────────────────────────────
        llm_id = "llm"
        pg.add_node(PipelineNode(
            id=llm_id,
            label="LLM Core",
            node_type="llm",
            criticality=0.7,
        ))
        pg.add_edge(entry_id, llm_id)

        # ── Tool nodes from detected tools ────────────────────────────
        prev = llm_id
        for tool_name in (profile.detected_tools or []):
            node_id = f"tool_{tool_name.lower().replace(' ', '_')}"
            crit = _tool_criticality(tool_name)
            pg.add_node(PipelineNode(
                id=node_id,
                label=tool_name,
                node_type="tool",
                criticality=crit,
            ))
            pg.add_edge(llm_id, node_id)

        # ── Capability nodes ──────────────────────────────────────────
        capabilities: list[str] = profile.capabilities or []
        for cap in capabilities:
            cap_id = f"cap_{cap.lower().replace(' ', '_')}"
            if cap_id not in pg.graph:
                pg.add_node(PipelineNode(
                    id=cap_id,
                    label=cap,
                    node_type="capability",
                    criticality=_tool_criticality(cap),
                ))
                pg.add_edge(llm_id, cap_id)

        # ── Framework-specific structural edges ───────────────────────
        match profile.framework:
            case FrameworkType.autogen:
                # Multi-agent: add a coordinator node
                coord_id = "coordinator"
                pg.add_node(PipelineNode(
                    id=coord_id,
                    label="Agent Coordinator",
                    node_type="agent",
                    criticality=0.85,
                ))
                pg.add_edge(entry_id, coord_id)
                pg.add_edge(coord_id, llm_id)
            case FrameworkType.n8n:
                # Workflow can trigger external systems
                trigger_id = "workflow_trigger"
                pg.add_node(PipelineNode(
                    id=trigger_id,
                    label="Workflow Trigger",
                    node_type="endpoint",
                    criticality=0.6,
                ))
                pg.add_edge(entry_id, trigger_id)
                pg.add_edge(trigger_id, llm_id)
            case _:
                pass

        # ── Extra topology overlay (caller-supplied) ──────────────────
        if extra_topology:
            pg._apply_extra(extra_topology)

        return pg

    def _apply_extra(self, topology: dict) -> None:
        for node_def in topology.get("nodes", []):
            node_id = node_def.get("id")
            if not node_id:
                continue
            pg_node = PipelineNode(
                id=node_id,
                label=re.sub(r'<[^>]+>', '', str(node_def.get("label", node_id) or node_id))[:128],
                node_type=node_def.get("type", "unknown"),
                criticality=float(node_def.get("criticality", _DEFAULT_CRITICALITY)),
                metadata=node_def.get("metadata", {}),
            )
            self.add_node(pg_node)

        for edge_def in topology.get("edges", []):
            src = edge_def.get("src") or edge_def.get("source")
            dst = edge_def.get("dst") or edge_def.get("target")
            if src and dst:
                self.add_edge(src, dst, weight=float(edge_def.get("weight", 1.0)))
