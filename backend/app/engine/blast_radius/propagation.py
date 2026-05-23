"""
Cascade propagation model.

Computes how an injection reaching a given node propagates through
the pipeline graph, weighted by edge trust and node criticality.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx


@dataclass
class PropagationResult:
    origin:         str
    reached:        set[str]               = field(default_factory=set)
    depth_map:      dict[str, int]         = field(default_factory=dict)   # node → min depth
    cascade_score:  float                  = 0.0
    edges:          list[tuple[str, str]]  = field(default_factory=list)   # (src, dst) BFS tree


def propagate(
    graph: nx.DiGraph,
    origin: str,
    *,
    max_depth: int = 10,
) -> PropagationResult:
    """
    BFS propagation from *origin*, respecting directed edges.

    Returns all reachable nodes, their minimum depth, the BFS tree
    edges, and a cascade_score that incorporates per-node criticality.
    """
    result = PropagationResult(origin=origin)

    if origin not in graph:
        return result

    queue: list[tuple[str, int]] = [(origin, 0)]
    visited: set[str] = {origin}
    total_criticality = 0.0

    while queue:
        current, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        for neighbor in graph.successors(current):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            result.reached.add(neighbor)
            result.depth_map[neighbor] = depth + 1
            result.edges.append((current, neighbor))

            crit = graph.nodes[neighbor].get("criticality", 0.4)
            # Criticality decays with depth (√depth dampening)
            effective_crit = crit / ((depth + 1) ** 0.5)
            total_criticality += effective_crit

            queue.append((neighbor, depth + 1))

    # Normalise to 0-1 (cap at 10 fully-critical nodes)
    result.cascade_score = min(1.0, total_criticality / 10.0)
    return result
