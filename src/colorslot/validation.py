"""Independent validation of a coloring against its conflict graph.

This module does not call any coloring algorithm: it only inspects the graph
and the proposed ``course_id -> color`` mapping.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .graph import ConflictGraph


class ScheduleValidationError(ValueError):
    """Raised when a schedule that must be valid is not."""


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    conflicts: list[tuple[str, str, int]] = field(default_factory=list)


def validate_coloring(graph: ConflictGraph, coloring: Mapping[str, object]) -> ValidationResult:
    """Check that ``coloring`` is a proper coloring of ``graph``.

    Valid means: every vertex has exactly one color, no unknown course is
    present, every color is an integer in ``1..n`` (n = number of courses), and
    no two adjacent courses share a color.
    """
    errors: list[str] = []
    conflicts: list[tuple[str, str, int]] = []
    vertices = set(graph.adjacency)

    missing = sorted(vertices - set(coloring))
    if missing:
        errors.append("courses without a slot: " + ", ".join(missing))
    unknown = sorted(set(coloring) - vertices)
    if unknown:
        errors.append("slots assigned to unknown courses: " + ", ".join(unknown))

    max_color = graph.num_vertices
    invalid_colors: set[str] = set()
    for course in sorted(set(coloring) & vertices):
        color = coloring[course]
        is_int = isinstance(color, int) and not isinstance(color, bool)
        if not is_int or color < 1 or color > max_color:
            invalid_colors.add(course)
            errors.append(
                f"course {course} has invalid slot {color!r} (must be an integer 1..{max_color})"
            )

    for a, b, _weight in graph.edges():
        if a in invalid_colors or b in invalid_colors:
            continue
        if a in coloring and b in coloring and coloring[a] == coloring[b]:
            conflicts.append((a, b, int(coloring[a])))  # type: ignore[call-overload]
            errors.append(f"conflict: {a} and {b} share slot {coloring[a]}")

    return ValidationResult(valid=not errors, errors=errors, conflicts=conflicts)


def ensure_valid(graph: ConflictGraph, coloring: Mapping[str, object]) -> None:
    """Raise :class:`ScheduleValidationError` unless the coloring is valid."""
    result = validate_coloring(graph, coloring)
    if not result.valid:
        raise ScheduleValidationError("invalid schedule: " + "; ".join(result.errors))
