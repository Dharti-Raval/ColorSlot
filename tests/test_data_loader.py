import pytest

from colorslot.data_loader import DataValidationError, load_enrollments


def test_loads_valid_file(write_csv):
    data = load_enrollments(
        write_csv("student_id,course_id,course_name\nS1,MATH101,Maths\nS2,MATH101,Maths\nS1,CS101,CS\n")
    )
    assert data.course_students == {"MATH101": {"S1", "S2"}, "CS101": {"S1"}}
    assert data.course_names == {"MATH101": "Maths", "CS101": "CS"}
    assert data.row_count == 3
    assert data.student_count == 2


def test_course_name_column_is_optional(write_csv):
    data = load_enrollments(write_csv("student_id,course_id\nS1,A\n"))
    assert data.course_names == {}


def test_identifiers_stay_strings_with_leading_zeros(write_csv):
    data = load_enrollments(write_csv("student_id,course_id\n0012,007\n"))
    assert data.course_students == {"007": {"0012"}}


def test_whitespace_is_stripped_and_header_case_ignored(write_csv):
    data = load_enrollments(write_csv(" Student_ID , COURSE_ID \n  S1 , A \n"))
    assert data.course_students == {"A": {"S1"}}


def test_utf8_bom_is_accepted(write_csv):
    data = load_enrollments(write_csv("\ufeffstudent_id,course_id\nS1,A\n"))
    assert "A" in data.course_students


def test_unusual_but_legal_identifiers_are_kept(write_csv):
    data = load_enrollments(write_csv('student_id,course_id\nS-1/é,"MATH 101, Honours"\n'))
    assert data.course_students == {"MATH 101, Honours": {"S-1/é"}}


def test_duplicate_rows_are_collapsed_and_counted(write_csv):
    data = load_enrollments(write_csv("student_id,course_id\nS1,A\nS1,A\nS1,A\nS2,A\n"))
    assert data.course_students["A"] == {"S1", "S2"}
    assert data.row_count == 4
    assert data.duplicate_rows == 2


def test_missing_file(tmp_path):
    with pytest.raises(DataValidationError, match="not found"):
        load_enrollments(tmp_path / "nope.csv")


def test_directory_instead_of_file(tmp_path):
    with pytest.raises(DataValidationError, match="not a file"):
        load_enrollments(tmp_path)


def test_empty_file(write_csv):
    with pytest.raises(DataValidationError, match="empty"):
        load_enrollments(write_csv(""))


def test_header_only_file(write_csv):
    with pytest.raises(DataValidationError, match="no enrollment records"):
        load_enrollments(write_csv("student_id,course_id\n"))


@pytest.mark.parametrize(
    "text, missing",
    [
        ("student_id,name\nS1,x\n", "course_id"),
        ("course_id,name\nA,x\n", "student_id"),
        ("a,b\n1,2\n", "student_id, course_id"),
    ],
)
def test_missing_required_columns(write_csv, text, missing):
    with pytest.raises(DataValidationError, match=f"missing required column.*{missing}"):
        load_enrollments(write_csv(text))


def test_duplicate_header_columns(write_csv):
    with pytest.raises(DataValidationError, match="duplicate column"):
        load_enrollments(write_csv("student_id,course_id,course_id\nS1,A,B\n"))


@pytest.mark.parametrize(
    "row, column",
    [(",A", "student_id"), ("S1,", "course_id"), ("   ,A", "student_id"), ("S1,   ", "course_id")],
)
def test_empty_identifiers_report_line_number(write_csv, row, column):
    with pytest.raises(DataValidationError, match=rf"line 3: {column} is empty"):
        load_enrollments(write_csv(f"student_id,course_id\nS0,A\n{row}\n"))


def test_short_row_counts_as_empty_course(write_csv):
    with pytest.raises(DataValidationError, match="course_id is empty"):
        load_enrollments(write_csv("student_id,course_id\nS1\n"))


def test_control_characters_rejected(write_csv):
    with pytest.raises(DataValidationError, match="control or invisible"):
        load_enrollments(write_csv("student_id,course_id\nS1,A\u200bB\n"))


def test_inconsistent_course_names(write_csv):
    with pytest.raises(DataValidationError, match="inconsistent names"):
        load_enrollments(
            write_csv("student_id,course_id,course_name\nS1,A,Alpha\nS2,A,Beta\n")
        )


def test_blank_name_on_some_rows_is_not_inconsistent(write_csv):
    data = load_enrollments(write_csv("student_id,course_id,course_name\nS1,A,Alpha\nS2,A,\n"))
    assert data.course_names == {"A": "Alpha"}


def test_invalid_utf8(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_bytes(b"student_id,course_id\nS1,\xff\xfe\n")
    with pytest.raises(DataValidationError, match="UTF-8"):
        load_enrollments(path)


def test_shipped_sample_dataset_loads(sample_dataset_path):
    data = load_enrollments(sample_dataset_path)
    assert data.duplicate_rows == 0
    assert len(data.course_students) >= 10
