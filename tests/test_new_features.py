"""Tests for read_all(), append(), and bold cell formatting."""
import os
import datetime
import streamxl


# ── read_all() ────────────────────────────────────────────────────────────────

def test_read_all_single_sheet(tmp_path):
    path = str(tmp_path / "r.xlsx")
    streamxl.write(path, [["a", "b"], [1.0, 2.0]])
    result = streamxl.read_all(path)
    assert list(result.keys()) == ["Sheet1"]
    assert result["Sheet1"] == [["a", "b"], [1.0, 2.0]]


def test_read_all_multi_sheet(tmp_path):
    path = str(tmp_path / "r.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["x"])
        w.add_sheet("S2")
        w.write_row(["y"])
        w.add_sheet("S3")
        w.write_row(["z"])
    result = streamxl.read_all(path)
    assert list(result.keys()) == ["Sheet1", "S2", "S3"]
    assert result["S2"] == [["y"]]


def test_read_all_as_dict(tmp_path):
    path = str(tmp_path / "r.xlsx")
    streamxl.write(path, [["Name", "Age"], ["Alice", 30.0]])
    result = streamxl.read_all(path, as_dict=True)
    assert result["Sheet1"] == [{"Name": "Alice", "Age": 30.0}]


def test_read_all_empty_file(tmp_path):
    path = str(tmp_path / "r.xlsx")
    streamxl.write(path, [])
    result = streamxl.read_all(path)
    assert result == {"Sheet1": []}


# ── append() ──────────────────────────────────────────────────────────────────

def test_append_basic(tmp_path):
    path = str(tmp_path / "a.xlsx")
    streamxl.write(path, [["a"], ["b"]])
    streamxl.append(path, [["c"], ["d"]])
    result = list(streamxl.read(path))
    assert result == [["a"], ["b"], ["c"], ["d"]]


def test_append_preserves_other_sheets(tmp_path):
    path = str(tmp_path / "a.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["sheet1"])
        w.add_sheet("S2")
        w.write_row(["sheet2"])
    streamxl.append(path, [["appended"]])
    s1 = list(streamxl.read(path, sheet="Sheet1"))
    s2 = list(streamxl.read(path, sheet="S2"))
    assert s1 == [["sheet1"], ["appended"]]
    assert s2 == [["sheet2"]]


def test_append_to_named_sheet(tmp_path):
    path = str(tmp_path / "a.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["s1"])
        w.add_sheet("Data")
        w.write_row(["s2"])
    streamxl.append(path, [["new"]], sheet="Data")
    assert list(streamxl.read(path, sheet="Data")) == [["s2"], ["new"]]
    assert list(streamxl.read(path, sheet="Sheet1")) == [["s1"]]


def test_append_invalid_sheet_raises(tmp_path):
    path = str(tmp_path / "a.xlsx")
    streamxl.write(path, [["x"]])
    try:
        streamxl.append(path, [["y"]], sheet="NoSuchSheet")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_append_with_dates(tmp_path):
    path = str(tmp_path / "a.xlsx")
    d1 = datetime.date(2024, 1, 1)
    d2 = datetime.date(2024, 6, 1)
    streamxl.write(path, [[d1]])
    streamxl.append(path, [[d2]])
    result = list(streamxl.read(path))
    assert result[0][0] == d1
    assert result[1][0] == d2


def test_append_file_unchanged_on_error(tmp_path):
    path = str(tmp_path / "a.xlsx")
    streamxl.write(path, [["original"]])
    original_size = os.path.getsize(path)
    try:
        streamxl.append(path, [["x"]], sheet="NoSuchSheet")
    except ValueError:
        pass
    assert os.path.getsize(path) == original_size


# ── bold formatting ───────────────────────────────────────────────────────────

def test_bold_row_roundtrip(tmp_path):
    path = str(tmp_path / "b.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["Name", "Score"], bold=True)
        w.write_row(["Alice", 95.5])
    result = list(streamxl.read(path))
    assert result[0] == ["Name", "Score"]   # bold doesn't change values
    assert result[1] == ["Alice", 95.5]


def test_bold_with_all_types(tmp_path):
    path = str(tmp_path / "b.xlsx")
    d = datetime.date(2024, 1, 1)
    dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
    with streamxl.writer(path) as w:
        w.write_row(["text", 42.0, True, None, d, dt], bold=True)
    result = list(streamxl.read(path))
    assert result[0][0] == "text"
    assert result[0][1] == 42.0
    assert result[0][2] is True
    assert result[0][3] is None
    assert result[0][4] == d
    assert isinstance(result[0][5], datetime.datetime)


def test_bold_default_is_false(tmp_path):
    path = str(tmp_path / "b.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["a", "b"])   # no bold kwarg
    result = list(streamxl.read(path))
    assert result[0] == ["a", "b"]


def test_bold_multi_sheet(tmp_path):
    path = str(tmp_path / "b.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["Header"], bold=True)
        w.write_row(["data"])
        w.add_sheet("S2")
        w.write_row(["H2"], bold=True)
        w.write_row(["d2"])
    s1 = list(streamxl.read(path, sheet="Sheet1"))
    s2 = list(streamxl.read(path, sheet="S2"))
    assert s1 == [["Header"], ["data"]]
    assert s2 == [["H2"], ["d2"]]
