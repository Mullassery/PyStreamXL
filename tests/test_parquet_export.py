"""Optional Parquet export tests (skipped without pyarrow)."""

from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq
from openpyxl import Workbook

import pystreamxl


def _workbook(path: Path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    for row in rows:
        ws.append(row)
    wb.save(path)


def test_streams_rows_to_parquet(tmp_path):
    source = tmp_path / "in.xlsx"
    output = tmp_path / "out.parquet"
    _workbook(source, [["id", "name"], [1, "Ada"], [2, "Grace"]])

    result = pystreamxl.to_parquet(str(source), str(output), batch_size=1)
    assert result["rows"] == 2
    assert result["columns"] == ["id", "name"]

    table = pq.read_table(output)
    assert table.num_rows == 2
    assert table.column("name").to_pylist() == ["Ada", "Grace"]
