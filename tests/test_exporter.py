import csv

import pytest

from colorslot.coloring import greedy_coloring
from colorslot.exporter import (
    ensure_output_dir,
    export_comparison,
    export_conflicts,
    export_schedule,
    format_comparison_table,
    format_schedule_report,
)
from colorslot.metrics import AlgorithmResult, compare_algorithms
from colorslot.validation import ScheduleValidationError


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


# Valid coloring of the sample graph (edges: CS101-MATH101, CS101-STAT101, MATH101-PHY101)
COLORING = {"BIO101": 1, "CS101": 1, "MATH101": 2, "PHY101": 1, "STAT101": 2}


def test_schedule_csv_content(sample_graph, tmp_path):
    path = export_schedule(sample_graph, COLORING, tmp_path / "schedule.csv")
    assert read_rows(path) == [
        ["course_id", "course_name", "slot_number", "slot_name", "degree"],
        ["BIO101", "Biology", "1", "Slot 1", "0"],
        ["CS101", "Computer Science", "1", "Slot 1", "2"],
        ["PHY101", "Physics", "1", "Slot 1", "1"],
        ["MATH101", "Mathematics", "2", "Slot 2", "2"],
        ["STAT101", "Statistics", "2", "Slot 2", "1"],
    ]


def test_schedule_export_refuses_invalid_coloring(sample_graph, tmp_path):
    bad = dict(COLORING, MATH101=1)  # clashes with CS101
    target = tmp_path / "schedule.csv"
    with pytest.raises(ScheduleValidationError):
        export_schedule(sample_graph, bad, target)
    assert not target.exists()


def test_schedule_export_refuses_incomplete_coloring(sample_graph, tmp_path):
    incomplete = {k: v for k, v in COLORING.items() if k != "BIO101"}
    with pytest.raises(ScheduleValidationError, match="BIO101"):
        export_schedule(sample_graph, incomplete, tmp_path / "schedule.csv")


def test_conflicts_csv_content(sample_graph, tmp_path):
    path = export_conflicts(sample_graph, tmp_path / "conflicts.csv")
    assert read_rows(path) == [
        ["course_a", "course_b", "shared_students"],
        ["CS101", "MATH101", "1"],
        ["CS101", "STAT101", "1"],
        ["MATH101", "PHY101", "2"],
    ]


def test_conflicts_csv_header_only_for_edgeless_graph(tmp_path):
    from colorslot.graph import ConflictGraph

    graph = ConflictGraph.from_edges([], vertices=["A"])
    path = export_conflicts(graph, tmp_path / "conflicts.csv")
    assert read_rows(path) == [["course_a", "course_b", "shared_students"]]


def test_comparison_csv_content(sample_graph, tmp_path):
    results = compare_algorithms(sample_graph)
    rows = read_rows(export_comparison(results, tmp_path / "comparison.csv"))
    assert rows[0] == ["algorithm", "slots_used", "execution_time_ms", "valid"]
    assert [r[0] for r in rows[1:]] == ["Greedy", "Welsh-Powell", "DSATUR"]
    for row, result in zip(rows[1:], results):
        assert int(row[1]) == result.slots_used
        assert float(row[2]) >= 0
        assert row[3] == "Yes"


def test_export_creates_missing_output_directory(sample_graph, tmp_path):
    nested = tmp_path / "a" / "b" / "out"
    ensure_output_dir(nested)
    assert nested.is_dir()
    export_schedule(sample_graph, COLORING, tmp_path / "x" / "y" / "schedule.csv")
    assert (tmp_path / "x" / "y" / "schedule.csv").is_file()


def test_exported_schedule_roundtrips_a_real_algorithm(sample_graph, tmp_path):
    coloring = greedy_coloring(sample_graph)
    rows = read_rows(export_schedule(sample_graph, coloring, tmp_path / "s.csv"))[1:]
    assert {r[0]: int(r[2]) for r in rows} == coloring


def test_schedule_report_groups_courses_by_slot(sample_graph):
    report = format_schedule_report(sample_graph, COLORING, "Test")
    assert "2 time slot(s)" in report
    slot1 = report.index("Slot 1:")
    slot2 = report.index("Slot 2:")
    assert slot1 < report.index("BIO101") < slot2 < report.index("MATH101")
    assert "PHY101 - Physics" in report


def _result(label, slots, valid=True):
    return AlgorithmResult(label.lower(), label, {}, slots, 1.0, valid)


def test_comparison_table_names_fewest_slots_without_claiming_optimality():
    table = format_comparison_table([_result("Greedy", 5), _result("Welsh-Powell", 4), _result("DSATUR", 4)])
    assert "| Algorithm" in table and "Valid Schedule" in table
    assert "Fewest slots on this input: Welsh-Powell, DSATUR (4)." in table
    assert "not proven to be optimal" in table
    assert "globally optimal" not in table


def test_comparison_table_when_all_tie_or_all_invalid():
    tie = format_comparison_table([_result("Greedy", 3), _result("Welsh-Powell", 3), _result("DSATUR", 3)])
    assert "All algorithms used 3 slot(s)" in tie
    none_valid = format_comparison_table([_result("Greedy", 3, False)])
    assert "No algorithm produced a valid schedule" in none_valid
