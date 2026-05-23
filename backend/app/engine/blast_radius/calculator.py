"""
Blast radius calculator.

Combines structural graph metrics with propagation cascade scores
to produce a final 0-100 blast radius score.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from .propagation import propagate


@dataclass
class BlastRadiusResult:
    score:          float                # 0-100
    affected_nodes: list[str]
    cascade_depth:  int
    entry_node:     str
    node_details:   list[dict]           = field(default_factory=list)
    edges:          list[tuple[str,str]] = field(default_factory=list)
    metadata:       dict                 = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score":          round(self.score, 2),
            "affected_nodes": self.affected_nodes,
            "cascade_depth":  self.cascade_depth,
            "entry_node":     self.entry_node,
            "node_details":   self.node_details,
            "edges":          [{"src": s, "dst": d} for s, d in self.edges],
            "metadata":       self.metadata,
        }


class BlastRadiusCalculator:
    """
    Computes blast radius for an injection entering the pipeline
    at *entry_node*.

    Score formula (0-100):
        base     = reachability_ratio * 40          (structural reach)
        cascade  = cascade_score * 40               (criticality-weighted)
        density  = edge_density_bonus * 10          (graph connectivity)
        critical = critical_node_bonus * 10         (any critical nodes hit)
    """

    CRITICAL_TYPES = {"database", "shell", "exec", "filesystem", "email"}

    def calculate(
        self,
        graph: nx.DiGraph,
        entry_node: str,
    ) -> BlastRadiusResult:
        total_nodes = graph.number_of_nodes()
        if total_nodes == 0:
            return BlastRadiusResult(
                score=0.0,
                affected_nodes=[],
                cascade_depth=0,
                entry_node=entry_node,
            )

        prop = propagate(graph, entry_node)
        reached = list(prop.reached)
        depth = max(prop.depth_map.values(), default=0)

        # ── Component scores ──────────────────────────────────────────
        reachability_ratio = len(reached) / max(total_nodes - 1, 1)
        base_score         = reachability_ratio * 40.0

        cascade_score = prop.cascade_score * 40.0

        # Edge density bonus: denser pipelines amplify blast
        max_edges    = total_nodes * (total_nodes - 1) or 1
        edge_density = graph.number_of_edges() / max_edges
        density_bonus = edge_density * 10.0

        # Critical node bonus: any database/shell/exec node reachable
        critical_hit = any(
            graph.nodes[n].get("node_type", "") in self.CRITICAL_TYPES
            or any(ct in n.lower() for ct in self.CRITICAL_TYPES)
            for n in reached
        )
        critical_bonus = 10.0 if critical_hit else 0.0

        total_score = min(100.0, base_score + cascade_score + density_bonus + critical_bonus)

        # ── Node detail list ──────────────────────────────────────────
        node_details = [
            {
                "id":          n,
                "label":       graph.nodes[n].get("label", n),
                "type":        graph.nodes[n].get("node_type", "unknown"),
                "criticality": graph.nodes[n].get("criticality", 0.4),
                "depth":       prop.depth_map.get(n, 0),
            }
            for n in reached
        ]
        node_details.sort(key=lambda x: (-x["criticality"], x["depth"]))

        return BlastRadiusResult(
            score=total_score,
            affected_nodes=reached,
            cascade_depth=depth,
            entry_node=entry_node,
            node_details=node_details,
            edges=prop.edges,
            metadata={
                "reachability_ratio": round(reachability_ratio, 3),
                "cascade_score":      round(prop.cascade_score, 3),
                "edge_density":       round(edge_density, 3),
                "critical_node_hit":  critical_hit,
                "total_nodes":        total_nodes,
            },
        )
