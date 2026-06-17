import datetime
import streamxl


def roundtrip(tmp_path, rows):
    path = str(tmp_path / "dates.xlsx")
    streamxl.write(path, rows)
    return list(streamxl.read(path))


# ── date write/read ───────────────────────────────────────────────────────────

def test_date_roundtrip(tmp_path):
    d = datetime.date(2024, 6, 15)
    result = roundtrip(tmp_path, [[d]])
    assert result[0][0] == d


def test_date_type_preserved(tmp_path):
    d = datetime.date(2000, 1, 1)
    result = roundtrip(tmp_path, [[d]])
    assert isinstance(result[0][0], datetime.date)
    assert not isinstance(result[0][0], datetime.datetime)


def test_date_epoch_boundary(tmp_path):
    # 1900-03-01 is the first real date after Excel's fake leap day (serial 60)
    d = datetime.date(1900, 3, 1)
    result = roundtrip(tmp_path, [[d]])
    assert result[0][0] == d


def test_date_modern(tmp_path):
    d = datetime.date(2026, 6, 17)
    result = roundtrip(tmp_path, [[d]])
    assert result[0][0] == d


def test_multiple_dates_in_row(tmp_path):
    row = [datetime.date(2024, 1, 1), datetime.date(2024, 12, 31)]
    result = roundtrip(tmp_path, [row])
    assert result[0] == row


def test_date_mixed_with_other_types(tmp_path):
    rows = [
        ["Name", "DOB", "Score"],
        ["Alice", datetime.date(1990, 5, 20), 95.5],
        ["Bob", datetime.date(1985, 11, 3), 88.0],
    ]
    result = roundtrip(tmp_path, rows)
    assert result[1][1] == datetime.date(1990, 5, 20)
    assert result[2][1] == datetime.date(1985, 11, 3)
    assert result[1][2] == 95.5


# ── datetime write/read ───────────────────────────────────────────────────────

def test_datetime_roundtrip(tmp_path):
    dt = datetime.datetime(2024, 6, 15, 14, 30, 0)
    result = roundtrip(tmp_path, [[dt]])
    assert isinstance(result[0][0], datetime.datetime)
    r = result[0][0]
    assert r.year == 2024
    assert r.month == 6
    assert r.day == 15
    assert r.hour == 14
    assert r.minute == 30
    assert r.second == 0


def test_datetime_midnight(tmp_path):
    dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
    result = roundtrip(tmp_path, [[dt]])
    r = result[0][0]
    assert r.year == 2024 and r.month == 1 and r.day == 1
    assert r.hour == 0 and r.minute == 0 and r.second == 0


def test_datetime_end_of_day(tmp_path):
    dt = datetime.datetime(2024, 6, 15, 23, 59, 59)
    result = roundtrip(tmp_path, [[dt]])
    r = result[0][0]
    assert r.hour == 23 and r.minute == 59 and r.second == 59


# ── context manager writer with dates ────────────────────────────────────────

def test_writer_with_dates(tmp_path):
    path = str(tmp_path / "w_dates.xlsx")
    d = datetime.date(2025, 3, 10)
    dt = datetime.datetime(2025, 3, 10, 9, 0, 0)
    with streamxl.writer(path) as w:
        w.write_row(["Date", "DateTime"])
        w.write_row([d, dt])
    result = list(streamxl.read(path))
    assert result[1][0] == d
    assert isinstance(result[1][1], datetime.datetime)
