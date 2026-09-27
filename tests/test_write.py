import os
import pytest
import pystreamxl


# ── helpers ───────────────────────────────────────────────────────────────────

SAMPLE_ROWS = [
    ["Name", "Age", "Score", "Active"],
    ["Alice", 30.0, 95.5, True],
    ["Bob", 25.0, 88.0, False],
    ["Carol", None, 72.3, True],
]


def roundtrip(tmp_path, rows):
    """Write rows to a temp XLSX, read them back."""
    path = str(tmp_path / "out.xlsx")
    pystreamxl.write(path, rows)
    return list(pystreamxl.read(path))


# ── write() API ───────────────────────────────────────────────────────────────

def test_write_creates_file(tmp_path):
    path = str(tmp_path / "out.xlsx")
    pystreamxl.write(path, SAMPLE_ROWS)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


def test_write_roundtrip_row_count(tmp_path):
    result = roundtrip(tmp_path, SAMPLE_ROWS)
    assert len(result) == len(SAMPLE_ROWS)


def test_write_roundtrip_strings(tmp_path):
    result = roundtrip(tmp_path, SAMPLE_ROWS)
    assert result[0][0] == "Name"
    assert result[1][0] == "Alice"


def test_write_roundtrip_numbers(tmp_path):
    result = roundtrip(tmp_path, SAMPLE_ROWS)
    assert result[1][1] == 30.0
    assert result[1][2] == 95.5


def test_write_roundtrip_booleans(tmp_path):
    result = roundtrip(tmp_path, SAMPLE_ROWS)
    assert result[1][3] is True
    assert result[2][3] is False


def test_write_roundtrip_none(tmp_path):
    result = roundtrip(tmp_path, SAMPLE_ROWS)
    assert result[3][1] is None


def test_write_empty_rows(tmp_path):
    result = roundtrip(tmp_path, [])
    assert result == []


def test_write_single_row(tmp_path):
    result = roundtrip(tmp_path, [["only"]])
    assert result == [["only"]]


def test_write_integers_become_floats(tmp_path):
    result = roundtrip(tmp_path, [[1, 2, 3]])
    # XLSX numbers are always float on read
    assert result[0] == [1.0, 2.0, 3.0]


def test_write_special_chars(tmp_path):
    rows = [["<tag>", "a & b", '"quoted"']]
    result = roundtrip(tmp_path, rows)
    assert result[0][0] == "<tag>"
    assert result[0][1] == "a & b"
    assert result[0][2] == '"quoted"'


def test_write_large_roundtrip(tmp_path):
    N = 10_000
    rows = [[f"row{i}", float(i), i % 2 == 0] for i in range(N)]
    result = roundtrip(tmp_path, rows)
    assert len(result) == N
    assert result[0][0] == "row0"
    assert result[N - 1][0] == f"row{N - 1}"


# ── writer() context-manager API ──────────────────────────────────────────────

def test_context_manager_creates_file(tmp_path):
    path = str(tmp_path / "cm.xlsx")
    with pystreamxl.writer(path) as w:
        w.write_row(["a", "b"])
        w.write_row([1, 2])
    assert os.path.exists(path)


def test_context_manager_roundtrip(tmp_path):
    path = str(tmp_path / "cm.xlsx")
    with pystreamxl.writer(path) as w:
        for row in SAMPLE_ROWS:
            w.write_row(row)
    result = list(pystreamxl.read(path))
    assert len(result) == len(SAMPLE_ROWS)
    assert result[0][0] == "Name"


def test_context_manager_close_is_idempotent(tmp_path):
    path = str(tmp_path / "cm.xlsx")
    w = pystreamxl.writer(path)
    w.write_row(["x"])
    w.close()
    w.close()  # should not raise


def test_writer_error_after_close(tmp_path):
    path = str(tmp_path / "cm.xlsx")
    w = pystreamxl.writer(path)
    w.write_row(["x"])
    w.close()
    with pytest.raises(Exception):
        w.write_row(["should fail"])
