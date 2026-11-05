"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from colorslot.data_loader import load_enrollments
from colorslot.graph import build_conflict_graph

SAMPLE_CSV = """student_id,course_id,course_name
S001,MATH101,Mathematics
S001,PHY101,Physics
S002,MATH101,Mathematics
S002,CS101,Computer Science
S003,CS101,Computer Science
S003,STAT101,Statistics
S004,MATH101,Mathematics
S004,PHY101,Physics
S005,BIO101,Biology
"""

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def write_csv(tmp_path):
    """Return a function that writes CSV text to a temp file and returns its path."""

    def _write(text: str, name: str = "enrollments.csv") -> Path:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8", newline="")
        return path

    return _write


@pytest.fixture
def sample_graph(write_csv):
    """Graph from SAMPLE_CSV: edges MATH101-PHY101 (2), MATH101-CS101 (1), CS101-STAT101 (1); BIO101 isolated."""
    return build_conflict_graph(load_enrollments(write_csv(SAMPLE_CSV)))


@pytest.fixture
def sample_dataset_path() -> Path:
    return REPO_ROOT / "data" / "sample_enrollments.csv"
