"""Graph metrics and algorithm benchmarking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .coloring import ALGORITHM_LABELS, Coloring, get_algorithm
from .graph import ConflictGraph
from .validation import validate_coloring


@dataclass
class GraphMetrics:
    total_courses: int
    total_edges: int
    max_degree: int
    average_degree: float
    density: float
    components: int
    most_conflicting: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class AlgorithmResult:
    key: str
    label: str
    coloring: Coloring
    slots_used: int
    execution_time_ms: float
    valid: bool
    errors: list[str] = field(default_factory=list)


def compute_graph_metrics(graph: ConflictGraph, top_n: int = 5) -> GraphMetrics:
    """Summary statistics; ``most_conflicting`` lists the top-degree courses."""
    degrees = graph.degrees()
    n = graph.num_vertices
    ranked = sorted(degrees.items(), key=lambda item: (-item[1], item[0]))
    return GraphMetrics(
        total_courses=n,
        total_edges=graph.num_edges,
        max_degree=max(degrees.values(), default=0),
        average_degree=(2 * graph.num_edges / n) if n else 0.0,
        density=graph.density(),
        components=len(graph.connected_components()),
        most_conflicting=ranked[:top_n],
    )


def run_algorithm(graph: ConflictGraph, key: str) -> AlgorithmResult:
    """Run one algorithm, time it with ``perf_counter`` and validate its output."""
    algorithm = get_algorithm(key)
    start = time.perf_counter()
    coloring = algorithm(graph)
    elapsed_ms = (time.perf_counter() - start) * 1000
    validation = validate_coloring(graph, coloring)
    return AlgorithmResult(
        key=key,
        label=ALGORITHM_LABELS[key],
        coloring=coloring,
        slots_used=len(set(coloring.values())),
        execution_time_ms=elapsed_ms,
        valid=validation.valid,
        errors=validation.errors,
    )


def compare_algorithms(graph: ConflictGraph) -> list[AlgorithmResult]:
    """Run every algorithm on the same graph."""
    return [run_algorithm(graph, key) for key in ALGORITHM_LABELS]


def fewest_slots(results: list[AlgorithmResult]) -> list[AlgorithmResult]:
    """Valid results that use the fewest slots (several on a tie)."""
    valid = [r for r in results if r.valid]
    if not valid:
        return []
    best = min(r.slots_used for r in valid)
    return [r for r in valid if r.slots_used == best]
