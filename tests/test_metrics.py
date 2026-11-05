import pytest

from colorslot.graph import ConflictGraph
from colorslot.metrics import (
    compare_algorithms,
    compute_graph_metrics,
    fewest_slots,
    run_algorithm,
)


def test_graph_metrics_on_sample(sample_graph):
    m = compute_graph_metrics(sample_graph, top_n=2)
    assert m.total_courses == 5
    assert m.total_edges == 3
    assert m.max_degree == 2
    assert m.average_degree == pytest.approx(6 / 5)  # sum of degrees / n
    assert m.density == pytest.approx(0.3)
    assert m.components == 2
    assert m.most_conflicting == [("CS101", 2), ("MATH101", 2)]  # ties broken by course ID


def test_graph_metrics_on_empty_graph():
    m = compute_graph_metrics(ConflictGraph())
    assert (m.total_courses, m.total_edges, m.max_degree, m.components) == (0, 0, 0, 0)
    assert m.average_degree == 0.0 and m.density == 0.0 and m.most_conflicting == []


def test_run_algorithm_reports_slots_time_and_validity(sample_graph):
    result = run_algorithm(sample_graph, "dsatur")
    assert result.label == "DSATUR"
    assert result.valid and result.errors == []
    assert result.slots_used == len(set(result.coloring.values()))
    assert result.execution_time_ms >= 0


def test_compare_runs_all_three_on_same_graph(sample_graph):
    results = compare_algorithms(sample_graph)
    assert [r.label for r in results] == ["Greedy", "Welsh-Powell", "DSATUR"]
    assert all(r.valid for r in results)


def test_fewest_slots_returns_all_ties(sample_graph):
    results = compare_algorithms(sample_graph)
    best = fewest_slots(results)
    assert best and all(r.slots_used == min(x.slots_used for x in results) for r in best)
    assert fewest_slots([]) == []
