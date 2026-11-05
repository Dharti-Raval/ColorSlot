import pytest

from colorslot.graph import ConflictGraph
from colorslot.validation import ScheduleValidationError, ensure_valid, validate_coloring


@pytest.fixture
def triangle_plus_isolated():
    return ConflictGraph.from_edges([("A", "B"), ("B", "C"), ("A", "C")], vertices=["D"])


def test_valid_coloring_passes(triangle_plus_isolated):
    result = validate_coloring(triangle_plus_isolated, {"A": 1, "B": 2, "C": 3, "D": 1})
    assert result.valid and result.errors == [] and result.conflicts == []


def test_adjacent_courses_in_same_slot_are_reported(triangle_plus_isolated):
    result = validate_coloring(triangle_plus_isolated, {"A": 1, "B": 1, "C": 2, "D": 1})
    assert not result.valid
    assert result.conflicts == [("A", "B", 1)]
    assert any("A and B share slot 1" in e for e in result.errors)


def test_non_adjacent_courses_may_share_a_slot():
    graph = ConflictGraph.from_edges([("A", "B")], vertices=["C"])
    assert validate_coloring(graph, {"A": 1, "B": 2, "C": 1}).valid


def test_missing_course_detected(triangle_plus_isolated):
    result = validate_coloring(triangle_plus_isolated, {"A": 1, "B": 2, "C": 3})
    assert not result.valid
    assert any("without a slot" in e and "D" in e for e in result.errors)


def test_unknown_course_detected(triangle_plus_isolated):
    result = validate_coloring(
        triangle_plus_isolated, {"A": 1, "B": 2, "C": 3, "D": 1, "ZZZ": 1}
    )
    assert not result.valid
    assert any("unknown courses" in e and "ZZZ" in e for e in result.errors)


@pytest.mark.parametrize("bad", [0, -1, 5, 1.5, "1", None, True])
def test_invalid_color_values_detected(triangle_plus_isolated, bad):
    # 4 courses, so valid colors are the integers 1..4 (True is a bool, not a slot number)
    result = validate_coloring(triangle_plus_isolated, {"A": bad, "B": 2, "C": 3, "D": 1})
    assert not result.valid
    assert any("invalid slot" in e for e in result.errors)


def test_empty_coloring_of_nonempty_graph_is_invalid(triangle_plus_isolated):
    assert not validate_coloring(triangle_plus_isolated, {}).valid


def test_empty_graph_with_empty_coloring_is_valid():
    assert validate_coloring(ConflictGraph(), {}).valid


def test_ensure_valid_raises_with_details(triangle_plus_isolated):
    with pytest.raises(ScheduleValidationError, match="conflict: A and B"):
        ensure_valid(triangle_plus_isolated, {"A": 1, "B": 1, "C": 2, "D": 1})
    ensure_valid(triangle_plus_isolated, {"A": 1, "B": 2, "C": 3, "D": 1})  # no error
