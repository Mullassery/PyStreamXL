from typing import Any, Dict, Iterable, Iterator, List, Optional, Union
from .core import list_sheets, read_rows, write_rows, XlsxWriter as _XlsxWriter
from .security import validate_read_path, validate_write_path, SecurityError


def read(
    path: str,
    sheet: Optional[str] = None,
    as_dict: bool = False,
    columns: Optional[List[Union[int, str]]] = None,
) -> Iterator[Any]:
    """
    Stream rows from an Excel (.xlsx) file.

    Args:
        path:     Path to the .xlsx file.
        sheet:    Sheet name to read. Defaults to the first sheet.
        as_dict:  If True, yield each row as a dict keyed by the header row.
                  The header row itself is consumed and not yielded.
        columns:  Filter columns to include.
                  - List of int: zero-based column indices to keep.
                  - List of str: column names to keep (requires the file to
                    have a header row; works with or without as_dict=True).

    Yields:
        List of cell values per row, or dict if as_dict=True.

    Raises:
        SecurityError: If file fails security validation (ZIP bomb protection).
    """
    # Validate path before attempting to read (DOS/ZIP bomb protection)
    validate_read_path(path)
    raw = read_rows(path, sheet)

    if not as_dict and columns is None:
        yield from raw
        return

    header: Optional[List[Any]] = None
    col_idx: Optional[List[int]] = None

    for i, row in enumerate(raw):
        if i == 0:
            header = row
            if columns is not None:
                if all(isinstance(c, str) for c in columns):
                    name_to_pos = {h: j for j, h in enumerate(header)}
                    col_idx = [name_to_pos[c] for c in columns if c in name_to_pos]
                else:
                    col_idx = [c for c in columns if isinstance(c, int) and c < len(header)]
            if not as_dict:
                # Yield the (possibly filtered) header row
                yield [row[j] for j in col_idx] if col_idx is not None else row
            continue

        filtered = [row[j] for j in col_idx if j < len(row)] if col_idx is not None else row

        if as_dict:
            keys = [header[j] for j in col_idx if j < len(header)] if col_idx is not None else header
            yield dict(zip(keys, filtered))
        else:
            yield filtered


def stream(path: str) -> Iterator[List[Any]]:
    """Alias for read()."""
    yield from read(path)


def write(path: str, rows: Iterable[Iterable[Any]]) -> None:
    """
    Write rows to an Excel (.xlsx) file.

    Args:
        path: Destination .xlsx path.
        rows: Iterable of iterables of cell values.
              Supported types: str, int, float, bool, None,
              datetime.date, datetime.datetime.

    Example::

        streamxl.write("report.xlsx", [
            ["Name", "Joined", "Score"],
            ["Alice", datetime.date(2024, 1, 15), 95.5],
        ])

    Raises:
        SecurityError: If path fails security validation.
    """
    validate_write_path(path)
    write_rows(path, rows)


def writer(path: str) -> _XlsxWriter:
    """
    Return a streaming writer for row-by-row XLSX writing.

    Supports multiple sheets via add_sheet(). Use as a context manager::

        with streamxl.writer("report.xlsx") as w:
            w.write_row(["Name", "Age"])
            w.write_row(["Alice", 30])
            w.add_sheet("Summary")
            w.write_row(["Total", 1])

    Raises:
        SecurityError: If path fails security validation.
    """
    validate_write_path(path)
    return _XlsxWriter(path)


def sheets(path: str) -> List[str]:
    """
    Return the list of sheet names in an Excel (.xlsx) file.

    Raises:
        SecurityError: If file fails security validation (ZIP bomb protection).
    """
    validate_read_path(path)
    return list_sheets(path)


def read_all(
    path: str,
    as_dict: bool = False,
) -> Dict[str, List[Any]]:
    """
    Read every sheet from an Excel (.xlsx) file.

    Returns a dict mapping each sheet name to its rows::

        {
            "Sheet1": [["Name", "Age"], ["Alice", 30.0]],
            "Summary": [["Total", 1.0]],
        }

    Args:
        path:     Path to the .xlsx file.
        as_dict:  If True, each sheet's rows are returned as dicts
                  keyed by the header row (same semantics as read(as_dict=True)).
    """
    return {
        name: list(read(path, sheet=name, as_dict=as_dict))
        for name in sheets(path)
    }


def append(path: str, rows: Iterable[Iterable[Any]], sheet: Optional[str] = None) -> None:
    """
    Append rows to a sheet in an existing Excel (.xlsx) file.

    All other sheets in the file are preserved unchanged. The file is
    rewritten atomically (write to a temp file, then replace).

    Args:
        path:  Path to the existing .xlsx file.
        rows:  Rows to append to the target sheet.
        sheet: Sheet name to append to. Defaults to the first sheet.

    Example::

        streamxl.write("log.xlsx", [["Date", "Event"]])
        streamxl.append("log.xlsx", [[datetime.date.today(), "started"]])
        streamxl.append("log.xlsx", [[datetime.date.today(), "finished"]])

    Raises:
        SecurityError: If file fails security validation (ZIP bomb protection).
    """
    import os, tempfile

    # Validate path before attempting to read/write
    validate_read_path(path)
    sheet_names = sheets(path)
    if not sheet_names:
        write(path, rows)
        return

    target = sheet or sheet_names[0]
    if target not in sheet_names:
        raise ValueError(f"sheet '{target}' not found; available: {sheet_names}")

    new_rows = list(rows)
    tmp = path + ".~tmp"
    try:
        with writer(tmp) as w:
            for i, name in enumerate(sheet_names):
                if i > 0:
                    w.add_sheet(name)
                for row in read(path, sheet=name):
                    w.write_row(row)
                if name == target:
                    for row in new_rows:
                        w.write_row(list(row))
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
