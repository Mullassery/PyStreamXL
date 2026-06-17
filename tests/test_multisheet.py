import streamxl


# ── sheets() listing ──────────────────────────────────────────────────────────

def test_sheets_single(tmp_path):
    path = str(tmp_path / "s.xlsx")
    streamxl.write(path, [["a"]])
    assert streamxl.sheets(path) == ["Sheet1"]


def test_sheets_multi(tmp_path):
    path = str(tmp_path / "m.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["x"])
        w.add_sheet("Sales")
        w.write_row(["y"])
        w.add_sheet("Summary")
        w.write_row(["z"])
    names = streamxl.sheets(path)
    assert names == ["Sheet1", "Sales", "Summary"]


# ── multi-sheet write + read ──────────────────────────────────────────────────

def test_multisheet_write_read_first(tmp_path):
    path = str(tmp_path / "ms.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["Sheet1 col"])
        w.write_row(["row1"])
        w.add_sheet("Sheet2")
        w.write_row(["Sheet2 col"])
        w.write_row(["other"])
    result = list(streamxl.read(path))
    assert result[0][0] == "Sheet1 col"
    assert result[1][0] == "row1"


def test_multisheet_read_by_name(tmp_path):
    path = str(tmp_path / "ms.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["A"])
        w.add_sheet("Data")
        w.write_row(["B"])
        w.write_row(["C"])
    result = list(streamxl.read(path, sheet="Data"))
    assert result[0][0] == "B"
    assert result[1][0] == "C"


def test_multisheet_each_sheet_independent(tmp_path):
    path = str(tmp_path / "ms.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["sheet1"])
        w.add_sheet("Second")
        w.write_row(["sheet2"])
    s1 = list(streamxl.read(path, sheet="Sheet1"))
    s2 = list(streamxl.read(path, sheet="Second"))
    assert s1[0][0] == "sheet1"
    assert s2[0][0] == "sheet2"


def test_read_invalid_sheet_raises(tmp_path):
    path = str(tmp_path / "ms.xlsx")
    streamxl.write(path, [["x"]])
    try:
        list(streamxl.read(path, sheet="DoesNotExist"))
        assert False, "expected an error"
    except Exception:
        pass


def test_multisheet_preserves_data_types(tmp_path):
    path = str(tmp_path / "ms.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["text", 42.0, True, None])
        w.add_sheet("S2")
        w.write_row(["other", 99.0])
    s1 = list(streamxl.read(path, sheet="Sheet1"))
    assert s1[0] == ["text", 42.0, True, None]


def test_multisheet_shared_strings_across_sheets(tmp_path):
    path = str(tmp_path / "ms.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["hello", "world"])
        w.add_sheet("S2")
        w.write_row(["hello", "again"])
    s1 = list(streamxl.read(path, sheet="Sheet1"))
    s2 = list(streamxl.read(path, sheet="S2"))
    assert s1[0][0] == "hello"
    assert s2[0][0] == "hello"


# ── as_dict ───────────────────────────────────────────────────────────────────

def test_as_dict_basic(tmp_path):
    path = str(tmp_path / "d.xlsx")
    streamxl.write(path, [
        ["Name", "Age", "Score"],
        ["Alice", 30.0, 95.5],
        ["Bob", 25.0, 88.0],
    ])
    result = list(streamxl.read(path, as_dict=True))
    assert len(result) == 2
    assert result[0] == {"Name": "Alice", "Age": 30.0, "Score": 95.5}
    assert result[1]["Name"] == "Bob"


def test_as_dict_header_not_in_result(tmp_path):
    path = str(tmp_path / "d.xlsx")
    streamxl.write(path, [["H1", "H2"], ["v1", "v2"]])
    result = list(streamxl.read(path, as_dict=True))
    assert len(result) == 1
    assert "H1" in result[0]


def test_as_dict_empty_data(tmp_path):
    path = str(tmp_path / "d.xlsx")
    streamxl.write(path, [["H1", "H2"]])
    result = list(streamxl.read(path, as_dict=True))
    assert result == []


# ── column filtering ──────────────────────────────────────────────────────────

def test_columns_by_index(tmp_path):
    path = str(tmp_path / "c.xlsx")
    streamxl.write(path, [
        ["A", "B", "C"],
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
    ])
    result = list(streamxl.read(path, columns=[0, 2]))
    assert result[0] == ["A", "C"]
    assert result[1] == [1.0, 3.0]


def test_columns_by_name_with_as_dict(tmp_path):
    path = str(tmp_path / "c.xlsx")
    streamxl.write(path, [
        ["Name", "Age", "City"],
        ["Alice", 30.0, "London"],
        ["Bob", 25.0, "Paris"],
    ])
    result = list(streamxl.read(path, as_dict=True, columns=["Name", "City"]))
    assert result[0] == {"Name": "Alice", "City": "London"}
    assert "Age" not in result[0]


def test_columns_by_name_without_as_dict(tmp_path):
    path = str(tmp_path / "c.xlsx")
    streamxl.write(path, [
        ["Name", "Age", "City"],
        ["Alice", 30.0, "London"],
    ])
    result = list(streamxl.read(path, columns=["Name", "City"]))
    assert result[0] == ["Name", "City"]   # filtered header
    assert result[1] == ["Alice", "London"]
