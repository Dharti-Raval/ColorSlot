"""Load and validate student-course enrollment data from CSV files."""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_COLUMNS = ("student_id", "course_id")
OPTIONAL_COLUMN = "course_name"


class DataValidationError(ValueError):
    """Raised when the input file is missing, malformed, or inconsistent."""


@dataclass
class EnrollmentData:
    """Validated enrollment data.

    ``course_students`` maps each course ID to the *set* of distinct students
    enrolled in it, so duplicate rows can never inflate conflict counts.
    """

    course_students: dict[str, set[str]] = field(default_factory=dict)
    course_names: dict[str, str] = field(default_factory=dict)
    row_count: int = 0
    duplicate_rows: int = 0

    @property
    def student_count(self) -> int:
        students: set[str] = set()
        for enrolled in self.course_students.values():
            students |= enrolled
        return len(students)


def _clean_identifier(raw: str | None, column: str, line: int) -> str:
    """Strip whitespace and reject empty or control-character identifiers.

    Identifiers stay strings, so values such as ``007`` keep their zeros.
    """
    value = (raw or "").strip()
    if not value:
        raise DataValidationError(f"line {line}: {column} is empty")
    if any(unicodedata.category(ch).startswith("C") for ch in value):
        raise DataValidationError(
            f"line {line}: {column} {value!r} contains control or invisible characters"
        )
    return value


def load_enrollments(path: str | Path) -> EnrollmentData:
    """Read an enrollment CSV file and return validated :class:`EnrollmentData`."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise DataValidationError(f"input file not found: {csv_path}")
    if not csv_path.is_file():
        raise DataValidationError(f"input path is not a file: {csv_path}")

    data = EnrollmentData()
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames
            if not header:
                raise DataValidationError(f"input file is empty: {csv_path}")

            columns: dict[str, str] = {}
            for name in header:
                key = (name or "").strip().lower()
                if not key:
                    continue
                if key in columns:
                    raise DataValidationError(f"duplicate column in header: {key!r}")
                columns[key] = name

            missing = [c for c in REQUIRED_COLUMNS if c not in columns]
            if missing:
                raise DataValidationError(
                    "missing required column(s): "
                    + ", ".join(missing)
                    + f" (found: {', '.join(columns) or 'none'})"
                )

            name_column = columns.get(OPTIONAL_COLUMN)
            for row in reader:
                line = reader.line_num
                student = _clean_identifier(row.get(columns["student_id"]), "student_id", line)
                course = _clean_identifier(row.get(columns["course_id"]), "course_id", line)
                data.row_count += 1

                if name_column is not None:
                    name = (row.get(name_column) or "").strip()
                    if name:
                        known = data.course_names.setdefault(course, name)
                        if known != name:
                            raise DataValidationError(
                                f"line {line}: course {course!r} has inconsistent names "
                                f"({known!r} vs {name!r})"
                            )

                enrolled = data.course_students.setdefault(course, set())
                if student in enrolled:
                    data.duplicate_rows += 1
                else:
                    enrolled.add(student)
    except UnicodeDecodeError as exc:
        raise DataValidationError(f"input file is not valid UTF-8 text: {csv_path}") from exc
    except csv.Error as exc:
        raise DataValidationError(f"malformed CSV in {csv_path}: {exc}") from exc

    if data.row_count == 0:
        raise DataValidationError(f"input file has a header but no enrollment records: {csv_path}")
    return data
