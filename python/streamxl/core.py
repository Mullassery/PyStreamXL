from streamxl._core import read as _read_all
from streamxl._core import write as _write_all
from streamxl._core import sheets as _list_sheets
from streamxl._core import PyXlsxWriter as XlsxWriter


def read_rows(path: str, sheet=None):
    yield from _read_all(path, sheet)


def write_rows(path: str, rows):
    _write_all(path, rows)


def list_sheets(path: str):
    return _list_sheets(path)
