"""Graph coloring heuristics: Greedy, Welsh-Powell and DSATUR.

All algorithms return ``{course_id: color}`` with 1-based colors and are fully
deterministic (ties are always broken by course ID). They are heuristics: each
returns a *valid* coloring, but none is guaranteed to use the minimum number
of colors.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .graph import ConflictGraph

Coloring = dict[str, int]

ALGORITHM_LABELS: dict[str, str] = {
    "greedy": "Greedy",
    "welsh-powell": "Welsh-Powell",
    "dsatur": "DSATUR",
}


def _smallest_free_color(used: set[int]) -> int:
    """Smallest positive integer not present in ``used``."""
    color = 1
    while color in used:
        color += 1
    return color


def _color_in_order(graph: ConflictGraph, order: Iterable[str]) -> Coloring:
    """First-fit coloring: give each vertex the smallest color unused by its neighbors."""
    coloring: Coloring = {}
    for vertex in order:
        used = {coloring[n] for n in graph.neighbors(vertex) if n in coloring}
        coloring[vertex] = _smallest_free_color(used)
    return coloring


def greedy_coloring(graph: ConflictGraph) -> Coloring:
    """Greedy coloring, processing vertices in ascending course-ID order."""
    return _color_in_order(graph, graph.vertices())


def welsh_powell_order(graph: ConflictGraph) -> list[str]:
    """Vertices by descending degree; equal degrees are ordered by course ID."""
    return sorted(graph.vertices(), key=lambda v: (-graph.degree(v), v))


def welsh_powell_coloring(graph: ConflictGraph) -> Coloring:
    """Welsh-Powell: first-fit coloring in descending-degree order."""
    return _color_in_order(graph, welsh_powell_order(graph))


def dsatur_coloring(graph: ConflictGraph) -> Coloring:
    """DSATUR (degree of saturation) coloring.

    Repeatedly pick the uncolored vertex whose neighbors already use the most
    distinct colors. Ties go to the vertex with more uncolored neighbors, then
    to the smaller course ID. The chosen vertex gets the smallest free color.
    """
    coloring: Coloring = {}
    neighbor_colors: dict[str, set[int]] = {v: set() for v in graph.adjacency}
    uncolored_neighbors: dict[str, int] = {v: graph.degree(v) for v in graph.adjacency}
    uncolored: set[str] = set(graph.adjacency)

    while uncolored:
        chosen = min(
            uncolored,
            key=lambda v: (-len(neighbor_colors[v]), -uncolored_neighbors[v], v),
        )
        color = _smallest_free_color(neighbor_colors[chosen])
        coloring[chosen] = color
        uncolored.remove(chosen)
        for neighbor in graph.neighbors(chosen):
            uncolored_neighbors[neighbor] -= 1
            neighbor_colors[neighbor].add(color)
    return coloring


ALGORITHMS: dict[str, Callable[[ConflictGraph], Coloring]] = {
    "greedy": greedy_coloring,
    "welsh-powell": welsh_powell_coloring,
    "dsatur": dsatur_coloring,
}


def get_algorithm(name: str) -> Callable[[ConflictGraph], Coloring]:
    """Look up an algorithm by its CLI name."""
    try:
        return ALGORITHMS[name]
    except KeyError:
        raise ValueError(
            f"unknown algorithm {name!r}; choose from: {', '.join(ALGORITHMS)}"
        ) from None
