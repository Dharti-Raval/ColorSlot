import pytest

from colorslot.data_loader import load_enrollments
from colorslot.graph import ConflictGraph, build_conflict_graph


def test_vertices_and_edges(sample_graph):
    assert sample_graph.vertices() == ["BIO101", "CS101", "MATH101", "PHY101", "STAT101"]
    assert sample_graph.num_vertices == 5
    assert sample_graph.num_edges == 3
    assert sample_graph.edges() == [
        ("CS101", "MATH101", 1),
        ("CS101", "STAT101", 1),
        ("MATH101", "PHY101", 2),
    ]


def test_edge_weights_count_distinct_shared_students(sample_graph):
    assert sample_graph.weight("MATH101", "PHY101") == 2  # S001 and S004
    assert sample_graph.weight("PHY101", "MATH101") == 2  # order does not matter
    assert sample_graph.weight("MATH101", "CS101") == 1
    assert sample_graph.weight("PHY101", "STAT101") == 0


def test_no_shared_students_means_no_edge(sample_graph):
    assert not sample_graph.has_edge("PHY101", "STAT101")
    assert not sample_graph.has_edge("MATH101", "STAT101")  # no student takes both


def test_adjacency_is_symmetric_and_loop_free(sample_graph):
    for u, neighbors in sample_graph.adjacency.items():
        assert u not in neighbors
        for v in neighbors:
            assert u in sample_graph.adjacency[v]
    assert sample_graph.num_edges == sum(len(n) for n in sample_graph.adjacency.values()) // 2


def test_isolated_course_stays_in_graph(sample_graph):
    assert "BIO101" in sample_graph.adjacency
    assert sample_graph.degree("BIO101") == 0


def test_degrees(sample_graph):
    assert sample_graph.degrees() == {
        "BIO101": 0, "CS101": 2, "MATH101": 2, "PHY101": 1, "STAT101": 1,
    }
    assert sum(sample_graph.degrees().values()) == 2 * sample_graph.num_edges


def test_density(sample_graph):
    assert sample_graph.density() == pytest.approx(3 / 10)  # 3 of C(5,2)=10 possible edges


def test_density_of_tiny_graphs():
    assert ConflictGraph().density() == 0.0
    assert ConflictGraph.from_edges([], vertices=["A"]).density() == 0.0
    assert ConflictGraph.from_edges([("A", "B")]).density() == 1.0


def test_connected_components(sample_graph):
    assert sample_graph.connected_components() == [
        ["BIO101"],
        ["CS101", "MATH101", "PHY101", "STAT101"],
    ]


def test_connected_components_two_clusters():
    graph = ConflictGraph.from_edges([("A", "B"), ("C", "D"), ("D", "E")])
    assert graph.connected_components() == [["A", "B"], ["C", "D", "E"]]


def test_duplicate_enrollments_do_not_inflate_weights(write_csv):
    text = "student_id,course_id\nS1,A\nS1,B\nS1,A\nS1,B\nS1,B\nS2,A\nS2,B\n"
    graph = build_conflict_graph(load_enrollments(write_csv(text)))
    assert graph.weight("A", "B") == 2  # S1 and S2, once each
    assert graph.num_edges == 1


def test_student_in_three_courses_creates_triangle(write_csv):
    graph = build_conflict_graph(
        load_enrollments(write_csv("student_id,course_id\nS1,A\nS1,B\nS1,C\n"))
    )
    assert graph.num_edges == 3
    assert all(w == 1 for _, _, w in graph.edges())


def test_single_enrollment_gives_single_vertex(write_csv):
    graph = build_conflict_graph(load_enrollments(write_csv("student_id,course_id\nS1,A\n")))
    assert graph.num_vertices == 1 and graph.num_edges == 0


def test_course_names_carried_into_graph(sample_graph):
    assert sample_graph.course_name("PHY101") == "Physics"


def test_add_edge_rejects_self_loops_and_bad_weights():
    graph = ConflictGraph()
    with pytest.raises(ValueError, match="self-loop"):
        graph.add_edge("A", "A")
    with pytest.raises(ValueError, match="weight"):
        graph.add_edge("A", "B", 0)
