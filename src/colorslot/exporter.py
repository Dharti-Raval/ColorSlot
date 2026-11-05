"""CSV export and plain-text reports."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

from .graph import ConflictGraph
from .metrics import AlgorithmResult, GraphMetrics, fewest_slots
from .validation import ensure_valid

SCHEDULE_HEADER = ["course_id", "course_name", "slot_number", "slot_name", "degree"]
CONFLICTS_HEADER = ["course_a", "course_b", "shared_students"]
COMPARISON_HEADER = ["algorithm", "slots_used", "execution_time_ms", "valid"]


def slot_name(slot_number: int) -> str:
    return f"Slot {slot_number}"


def ensure_output_dir(path: str | Path) -> Path:
    """Create the output directory (and parents) if needed."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _write_csv(path: Path, header: list[str], rows: Sequence[Sequence[object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def export_schedule(graph: ConflictGraph, coloring: Mapping[str, int], path: str | Path) -> Path:
    """Write schedule.csv. Raises if the coloring is not a valid schedule."""
    ensure_valid(graph, coloring)
    ordered = sorted(graph.vertices(), key=lambda course: (coloring[course], course))
    rows = [
        [c, graph.course_name(c), coloring[c], slot_name(coloring[c]), graph.degree(c)]
        for c in ordered
    ]
    return _write_csv(Path(path), SCHEDULE_HEADER, rows)


def export_conflicts(graph: ConflictGraph, path: str | Path) -> Path:
    """Write conflicts.csv with one row per conflicting course pair."""
    return _write_csv(Path(path), CONFLICTS_HEADER, graph.edges())


def export_comparison(results: Sequence[AlgorithmResult], path: str | Path) -> Path:
    """Write comparison.csv with one row per algorithm."""
    rows = [
        [r.label, r.slots_used, f"{r.execution_time_ms:.3f}", "Yes" if r.valid else "No"]
        for r in results
    ]
    return _write_csv(Path(path), COMPARISON_HEADER, rows)


def format_metrics_report(metrics: GraphMetrics) -> str:
    lines = [
        "Graph analysis",
        f"  Courses (vertices):     {metrics.total_courses}",
        f"  Conflict edges:         {metrics.total_edges}",
        f"  Maximum degree:         {metrics.max_degree}",
        f"  Average degree:         {metrics.average_degree:.2f}",
        f"  Graph density:          {metrics.density:.3f}",
        f"  Connected components:   {metrics.components}",
        "  Most conflict-heavy courses:",
    ]
    lines += [f"    {course:<12} {degree} conflicting course(s)" for course, degree in metrics.most_conflicting]
    return "\n".join(lines)


def format_schedule_report(graph: ConflictGraph, coloring: Mapping[str, int], label: str) -> str:
    """Courses grouped by exam slot."""
    slots: dict[int, list[str]] = {}
    for course in graph.vertices():
        slots.setdefault(coloring[course], []).append(course)

    lines = [f"Exam timetable ({label}): {len(slots)} time slot(s)"]
    for number in sorted(slots):
        lines.append(f"  {slot_name(number)}:")
        for course in slots[number]:
            name = graph.course_name(course)
            lines.append(f"    {course}" + (f" - {name}" if name else ""))
    return "\n".join(lines)


def format_comparison_table(results: Sequence[AlgorithmResult]) -> str:
    """Comparison table plus a cautious statement about which used fewest slots."""
    header = ("Algorithm", "Time Slots", "Execution Time", "Valid Schedule")
    rows = [
        (r.label, str(r.slots_used), f"{r.execution_time_ms:.3f} ms", "Yes" if r.valid else "No")
        for r in results
    ]
    widths = [max(len(row[i]) for row in [header, *rows]) for i in range(len(header))]

    def fmt(row: Sequence[str]) -> str:
        return "| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |"

    lines = ["Algorithm comparison", fmt(header), "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    lines += [fmt(row) for row in rows]

    best = fewest_slots(list(results))
    if not best:
        lines.append("No algorithm produced a valid schedule.")
    else:
        slots = best[0].slots_used
        if len(best) == len(results):
            lines.append(f"All algorithms used {slots} slot(s) on this input.")
        else:
            names = ", ".join(r.label for r in best)
            lines.append(f"Fewest slots on this input: {names} ({slots}).")
        lines.append(
            "Note: these are heuristics; a valid coloring is not proven to be optimal."
        )
    return "\n".join(lines)
