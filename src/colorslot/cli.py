"""Command-line interface for ColorSlot."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from .coloring import ALGORITHM_LABELS
from .data_loader import DataValidationError, load_enrollments
from .exporter import (
    ensure_output_dir,
    export_comparison,
    export_conflicts,
    export_schedule,
    format_comparison_table,
    format_metrics_report,
    format_schedule_report,
)
from .graph import build_conflict_graph
from .metrics import compare_algorithms, compute_graph_metrics, run_algorithm
from .validation import ScheduleValidationError
from .visualization import VisualizationError, plot_conflict_graph


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="colorslot",
        description="Generate a conflict-free exam timetable using graph coloring.",
        epilog=(
            "example: python -m colorslot --input data/sample_enrollments.csv "
            "--algorithm dsatur --output-dir output --compare --plot"
        ),
    )
    parser.add_argument("-i", "--input", required=True, metavar="CSV",
                        help="enrollment CSV with columns student_id, course_id[, course_name]")
    parser.add_argument("-a", "--algorithm", choices=list(ALGORITHM_LABELS), default="dsatur",
                        help="coloring algorithm (default: %(default)s)")
    parser.add_argument("-o", "--output-dir", default="output", metavar="DIR",
                        help="directory for generated files, created if missing (default: %(default)s)")
    parser.add_argument("--compare", action="store_true",
                        help="run all algorithms and write comparison.csv")
    parser.add_argument("--plot", action="store_true",
                        help="save network.png (requires matplotlib)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def run(args: argparse.Namespace) -> int:
    data = load_enrollments(args.input)
    graph = build_conflict_graph(data)

    result = run_algorithm(graph, args.algorithm)
    if not result.valid:
        raise ScheduleValidationError(
            f"{result.label} produced an invalid schedule: " + "; ".join(result.errors)
        )

    out_dir = ensure_output_dir(args.output_dir)
    written = [
        export_schedule(graph, result.coloring, out_dir / "schedule.csv"),
        export_conflicts(graph, out_dir / "conflicts.csv"),
    ]

    print(f"Loaded {data.row_count} enrollment rows: {data.student_count} students, "
          f"{graph.num_vertices} courses")
    if data.duplicate_rows:
        print(f"Ignored {data.duplicate_rows} duplicate enrollment row(s).")
    print()
    print(format_metrics_report(compute_graph_metrics(graph)))
    print()
    print(format_schedule_report(graph, result.coloring, result.label))
    print(f"\nValidation: PASSED ({result.label}, {result.slots_used} slot(s), "
          f"{result.execution_time_ms:.3f} ms)")

    if args.compare:
        results = compare_algorithms(graph)
        written.append(export_comparison(results, out_dir / "comparison.csv"))
        print()
        print(format_comparison_table(results))

    if args.plot:
        written.append(plot_conflict_graph(
            graph, result.coloring, out_dir / "network.png",
            title=f"Course conflict graph - {result.label}",
        ))

    print("\nFiles written:")
    for path in written:
        print(f"  {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (DataValidationError, ScheduleValidationError, VisualizationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
