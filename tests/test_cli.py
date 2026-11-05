import csv
import subprocess
import sys

import pytest

from colorslot.cli import main
from colorslot.data_loader import load_enrollments
from colorslot.graph import build_conflict_graph
from colorslot.validation import validate_coloring


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.parametrize("algorithm", ["greedy", "welsh-powell", "dsatur"])
def test_end_to_end_on_sample_dataset(algorithm, sample_dataset_path, tmp_path, capsys):
    out = tmp_path / "out"
    code = main(["--input", str(sample_dataset_path), "--algorithm", algorithm,
                 "--output-dir", str(out), "--compare"])
    assert code == 0
    assert "Validation: PASSED" in capsys.readouterr().out

    graph = build_conflict_graph(load_enrollments(sample_dataset_path))
    schedule = read_rows(out / "schedule.csv")
    coloring = {r["course_id"]: int(r["slot_number"]) for r in schedule}
    assert validate_coloring(graph, coloring).valid
    assert len(read_rows(out / "conflicts.csv")) == graph.num_edges
    assert len(read_rows(out / "comparison.csv")) == 3
    assert not (out / "network.png").exists()  # plotting is opt-in


def test_defaults_to_dsatur_without_extra_files(sample_dataset_path, tmp_path, capsys):
    assert main(["-i", str(sample_dataset_path), "-o", str(tmp_path)]) == 0
    assert "Exam timetable (DSATUR)" in capsys.readouterr().out
    assert not (tmp_path / "comparison.csv").exists()


def test_plot_flag_creates_png(sample_dataset_path, tmp_path):
    pytest.importorskip("matplotlib")
    assert main(["-i", str(sample_dataset_path), "-o", str(tmp_path), "--plot"]) == 0
    assert (tmp_path / "network.png").stat().st_size > 0


def test_invalid_input_gives_clean_error(write_csv, tmp_path, capsys):
    bad = write_csv("student_id,course_id\n,A\n")
    assert main(["-i", str(bad), "-o", str(tmp_path / "out")]) == 1
    assert "error: line 2: student_id is empty" in capsys.readouterr().err
    assert not (tmp_path / "out" / "schedule.csv").exists()


def test_missing_input_file(tmp_path, capsys):
    assert main(["-i", str(tmp_path / "missing.csv")]) == 1
    assert "not found" in capsys.readouterr().err


def test_duplicate_rows_are_reported(write_csv, tmp_path, capsys):
    path = write_csv("student_id,course_id\nS1,A\nS1,A\nS1,B\n")
    assert main(["-i", str(path), "-o", str(tmp_path)]) == 0
    assert "Ignored 1 duplicate" in capsys.readouterr().out


def test_bad_arguments_exit_with_usage_error(sample_dataset_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["-i", str(sample_dataset_path), "--algorithm", "bogus"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_python_dash_m_entry_point(sample_dataset_path, tmp_path):
    import os
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src"
    env = dict(os.environ, PYTHONPATH=str(src))
    proc = subprocess.run(
        [sys.executable, "-m", "colorslot", "-i", str(sample_dataset_path), "-o", str(tmp_path)],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "schedule.csv").is_file()
