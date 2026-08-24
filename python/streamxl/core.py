from streamxl._core import read as _read_all
from streamxl._core import read_with_metadata as _read_with_metadata
from streamxl._core import stream_rows as _stream_rows
from streamxl._core import stream_rows_with_metadata as _stream_rows_with_metadata
from streamxl._core import write as _write_all
from streamxl._core import sheets as _list_sheets
from streamxl._core import conditional_formats as _conditional_formats
from streamxl._core import PyXlsxWriter as XlsxWriter


def read_rows(path: str, sheet=None):
    """Real, constant-memory streaming: `_stream_rows` is a Rust iterator
    (PyRowIter) that produces one row at a time, not a pre-materialized
    list. Previously this called `_read_all`, which built the entire sheet
    into a Python list before this generator ever yielded its first row --
    "streaming" in name only. See `stream_rows`/`stream_rows_with_metadata`
    in python/src/lib.rs for what changed and why.
    """
    yield from _stream_rows(path, sheet)


def read_rows_with_metadata(path: str, sheet=None):
    """Real, constant-memory streaming -- see `read_rows` above."""
    yield from _stream_rows_with_metadata(path, sheet)


def read_rows_all_at_once(path: str, sheet=None):
    """The old eager behavior (`_core.read`): materializes the entire sheet
    into memory before returning. Kept as an explicit escape hatch for
    callers that already assumed random access or repeated iteration over
    the full result (e.g. `list(read_rows_all_at_once(...))` twice) -- the
    streaming generators above are one-shot, like any Python iterator.
    """
    yield from _read_all(path, sheet)


def read_rows_with_metadata_all_at_once(path: str, sheet=None):
    """The old eager behavior -- see `read_rows_all_at_once` above."""
    yield from _read_with_metadata(path, sheet)


def write_rows(path: str, rows):
    _write_all(path, rows)


def list_sheets(path: str):
    return _list_sheets(path)


def get_conditional_formats(path: str, sheet=None):
    """Conditional formatting rules (`<conditionalFormatting>`/`<cfRule>`) for
    a sheet, each with its `dxfId` resolved against `xl/styles.xml`'s
    `<dxfs>`. Returns a list of dicts with keys: sqref, type, operator,
    formulas, priority, stop_if_true, format (font_color/font_bold/
    font_italic/fill_bg_color/fill_fg_color, or None if the rule type --
    e.g. colorScale/dataBar/iconSet -- doesn't use a dxfId).
    """
    return _conditional_formats(path, sheet)
