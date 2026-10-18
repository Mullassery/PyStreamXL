"""Optional columnar exports for PyStreamXL row streams.

These helpers keep the streaming contract: rows are read from the XLSX in
batches and written to a Parquet sink without materializing the whole sheet in
Python. ``pyarrow`` is an optional dependency (``pip install
"pystreamxl[arrow]"``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .api import read
from .security import SecurityError, validate_read_path


def _require_pyarrow():
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError(
            "Parquet export requires pyarrow; install with "
            '`pip install "pystreamxl[arrow]"`'
        ) from exc
    return pa, pq


def to_parquet(
    source: str,
    destination: str,
    *,
    sheet: Optional[str] = None,
    batch_size: int = 100_000,
    compression: str = "snappy",
) -> Dict[str, Any]:
    """Stream ``source`` .xlsx rows into a Parquet file.

    The header row becomes the column names. Each batch is converted with
    ``pyarrow.Table.from_pylist`` and written with a single ``ParquetWriter``;
    the full sheet is never held in memory. If a later batch has a different
    inferred Arrow schema, the export fails with a clear error rather than
    silently coercing values.

    Returns ``{"rows": n, "columns": [...], "path": destination}``.
    """
    pa, pq = _require_pyarrow()
    validate_read_path(source)
    destination_path = Path(destination).resolve()
    if destination_path.suffix.lower() != ".parquet":
        raise SecurityError("Parquet destination must end in .parquet")
    if destination_path.exists() and destination_path.is_dir():
        raise SecurityError("Parquet destination is a directory")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination = str(destination_path)

    writer = None
    columns: List[str] = []
    rows = 0
    batch: List[Dict[str, Any]] = []

    def flush() -> None:
        nonlocal writer, columns, rows, batch
        if not batch:
            return
        table = pa.Table.from_pylist(batch)
        if writer is None:
            columns = list(table.column_names)
            writer = pq.ParquetWriter(destination, table.schema, compression=compression)
        elif table.schema != writer.schema:
            raise ValueError(
                "Arrow schema changed between batches; normalize column types "
                "or use a smaller consistent input"
            )
        writer.write_table(table)
        rows += len(batch)
        batch = []

    try:
        for row in read(source, sheet=sheet, as_dict=True):
            if not isinstance(row, dict):
                raise ValueError("Parquet export requires as_dict rows")
            batch.append(row)
            if len(batch) >= batch_size:
                flush()
        flush()
    finally:
        if writer is not None:
            writer.close()

    return {"rows": rows, "columns": columns, "path": destination}
