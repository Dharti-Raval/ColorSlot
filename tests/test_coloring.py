import random

import pytest

from colorslot.coloring import (
    ALGORITHMS,
    dsatur_coloring,
    get_algorithm,
    greedy_coloring,
    welsh_powell_coloring,
    welsh_powell_order,
)
from colorslot.graph import ConflictGraph
from colorslot.validation import validate_coloring

ALL = pytest.mark.parametrize("name", list(ALGORITHMS))


def slots(coloring):
    return len(set(coloring.values()))


def crown_graph(n):
    """Bipartite 'crown' graph: i-a adjacent to j-b for i != j.

    Sorted vertex order interleaves the two sides (1a, 1b, 2a, 2b, ...), which is
    the classic bad order for first-fit coloring.
    """
    edges = [(f"{i}a", f"{j}b") for i in range(1, n + 1) for j in range(1, n + 1) if i != j]
    return ConflictGraph.from_edges(edges)


@ALL
def test_valid_on_sample_graph(name, sample_graph):
    coloring = get_algorithm(name)(sample_graph)
    assert validate_coloring(sample_graph, coloring).valid
    assert set(coloring) == set(sample_graph.vertices())


@ALL
def test_valid_on_shipped_sample_dataset(name, sample_dataset_path):
    from colorslot.data_loader import load_enrollments
    from colorslot.graph import build_conflict_graph

    graph = build_conflict_graph(load_enrollments(sample_dataset_path))
    assert validate_coloring(graph, ALGORITHMS[name](graph)).valid


@ALL
def test_triangle_needs_exactly_three_colors(name):
    graph = ConflictGraph.from_edges([("A", "B"), ("B", "C"), ("A", "C")])
    coloring = ALGORITHMS[name](graph)
    assert slots(coloring) == 3
    assert sorted(coloring.values()) == [1, 2, 3]


@ALL
def test_path_graph_uses_two_colors(name):
    graph = ConflictGraph.from_edges([("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")])
    coloring = ALGORITHMS[name](graph)
    assert slots(coloring) == 2
    assert validate_coloring(graph, coloring).valid


@ALL
def test_edgeless_graph_uses_one_color(name):
    graph = ConflictGraph.from_edges([], vertices=["A", "B", "C", "D"])
    assert set(ALGORITHMS[name](graph).values()) == {1}


@ALL
def test_single_vertex(name):
    graph = ConflictGraph.from_edges([], vertices=["X"])
    assert ALGORITHMS[name](graph) == {"X": 1}


@ALL
def test_empty_graph(name):
    assert ALGORITHMS[name](ConflictGraph()) == {}


@ALL
def test_complete_graph_needs_n_colors(name):
    vertices = [f"V{i}" for i in range(6)]
    edges = [(a, b) for i, a in enumerate(vertices) for b in vertices[i + 1:]]
    assert slots(ALGORITHMS[name](ConflictGraph.from_edges(edges))) == 6


@ALL
def test_even_cycle_valid_and_odd_cycle_needs_three(name):
    even = ConflictGraph.from_edges([(str(i), str((i + 1) % 6)) for i in range(6)])
    odd = ConflictGraph.from_edges([(str(i), str((i + 1) % 5)) for i in range(5)])
    assert validate_coloring(even, ALGORITHMS[name](even)).valid
    odd_coloring = ALGORITHMS[name](odd)
    assert validate_coloring(odd, odd_coloring).valid
    assert slots(odd_coloring) == 3  # odd cycles are not 2-colorable


@ALL
def test_colors_are_one_based(name, sample_graph):
    assert min(ALGORITHMS[name](sample_graph).values()) == 1


@ALL
def test_deterministic(name, sample_graph):
    first = ALGORITHMS[name](sample_graph)
    assert all(ALGORITHMS[name](sample_graph) == first for _ in range(5))


@ALL
def test_valid_and_within_max_degree_plus_one_on_random_graphs(name):
    rng = random.Random(12345)
    for _ in range(60):
        n = rng.randint(1, 25)
        vertices = [f"C{i:02d}" for i in range(n)]
        p = rng.choice([0.1, 0.3, 0.6, 0.9])
        edges = [(a, b) for i, a in enumerate(vertices) for b in vertices[i + 1:] if rng.random() < p]
        graph = ConflictGraph.from_edges(edges, vertices=vertices)
        coloring = ALGORITHMS[name](graph)
        assert validate_coloring(graph, coloring).valid
        max_degree = max(graph.degrees().values())
        assert slots(coloring) <= max_degree + 1  # guaranteed by first-fit coloring


def test_welsh_powell_order_by_degree_then_course_id():
    # degrees: B=3, A=1, C=1, D=1, E=0
    graph = ConflictGraph.from_edges([("B", "A"), ("B", "C"), ("B", "D")], vertices=["E"])
    assert welsh_powell_order(graph) == ["B", "A", "C", "D", "E"]


def test_greedy_follows_course_id_order():
    # Path Z-A-B: greedy colors A first (1), then B (2), then Z (2).
    graph = ConflictGraph.from_edges([("Z", "A"), ("A", "B")])
    assert greedy_coloring(graph) == {"A": 1, "B": 2, "Z": 2}


def test_welsh_powell_colors_highest_degree_first():
    graph = ConflictGraph.from_edges([("Z", "A"), ("A", "B")])
    coloring = welsh_powell_coloring(graph)
    assert coloring["A"] == 1  # A has degree 2, so it is colored first


def test_dsatur_ties_on_saturation_go_to_most_uncolored_neighbors():
    # Star with centre Z (sorts last by ID). All saturations start at 0, so only the
    # "most uncolored neighbors" rule can make DSATUR start at Z; plain ID order would not.
    graph = ConflictGraph.from_edges([("Z", "L1"), ("Z", "L2"), ("Z", "L3"), ("Z", "L4")])
    assert dsatur_coloring(graph) == {"Z": 1, "L1": 2, "L2": 2, "L3": 2, "L4": 2}


def test_dsatur_prefers_higher_saturation_over_higher_degree():
    # Triangle T1-T2-T3 plus pendant P attached to T1 and a hub X (degree 3) elsewhere.
    # After T1=1 (highest degree, ties by ID), T2/T3 have saturation 1 while the
    # degree-3 hub X has saturation 0, so a triangle vertex must be colored next.
    graph = ConflictGraph.from_edges([
        ("T1", "T2"), ("T1", "T3"), ("T2", "T3"), ("T1", "P"),
        ("X", "Y1"), ("X", "Y2"), ("X", "Y3"),
    ])
    coloring = dsatur_coloring(graph)
    assert validate_coloring(graph, coloring).valid
    assert coloring["T1"] == 1 and {coloring["T2"], coloring["T3"]} == {2, 3}
    assert coloring["X"] == 1  # X is colored after the triangle, with no constraints yet


def test_dsatur_is_optimal_on_bipartite_crown_graph_where_first_fit_is_not():
    graph = crown_graph(5)
    assert slots(dsatur_coloring(graph)) == 2
    # Heuristics are not optimal: first-fit in this order is forced to use n colors.
    assert slots(greedy_coloring(graph)) == 5
    assert slots(welsh_powell_coloring(graph)) == 5
    for coloring in (greedy_coloring(graph), welsh_powell_coloring(graph), dsatur_coloring(graph)):
        assert validate_coloring(graph, coloring).valid


def test_unknown_algorithm_name():
    with pytest.raises(ValueError, match="unknown algorithm"):
        get_algorithm("rainbow")
