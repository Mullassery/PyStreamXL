"""Compare PyStreamXL, python-calamine, and Polars on the same .xlsx file.

PyStreamXL streams rows; calamine/Polars load a sheet. Report wall-clock and
note the semantic difference rather than claiming a like-for-like speed win.

Usage:
    python benchmarks/calamine_vs_pystreamxl.py [rows]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from openpyxl import Workbook


def make_file(path: Path, rows: int) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Name", "Value", "Score", "Category", "Flag", "Amount", "Date", "Code", "Notes"])
    for i in range(1, rows + 1):
        ws.append(
            [
                i,
                f"User_{i}",
                i * 1.5,
                round(i * 0.37, 2),
                f"Cat_{i % 10}",
                i % 2 == 0,
                i * 100,
                f"2024-{(i % 12) + 1:02d}-01",
                f"CODE{i:06d}",
                f"Note {i}",
            ]
        )
    wb.save(path)


def time_pystreamxl(path: str) -> tuple[float, int]:
    import pystreamxl

    start = time.perf_counter()
    count = sum(1 for _ in pystreamxl.read(path))
    return time.perf_counter() - start, count


def time_calamine(path: str) -> tuple[float, int]:
    from python_calamine import CalamineWorkbook

    start = time.perf_counter()
    rows = CalamineWorkbook.from_path(path).get_sheet_by_index(0).to_python()
    return time.perf_counter() - start, len(rows)


def time_polars(path: str) -> tuple[float, int]:
    import polars as pl

    start = time.perf_counter()
    frame = pl.read_excel(path)
    return time.perf_counter() - start, frame.height


def main() -> int:
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
    path = Path("benchmarks/calamine_vs_pystreamxl.xlsx")
    path.parent.mkdir(exist_ok=True)
    if not path.exists() or rows > 0:
        make_file(path, rows)

    print(f"rows={rows} file={path}")
    for name, func in (
        ("pystreamxl (stream)", time_pystreamxl),
        ("python-calamine (load)", time_calamine),
        ("polars (load)", time_polars),
    ):
        try:
            elapsed, count = func(str(path))
            print(f"{name:24} {elapsed:8.3f}s  rows={count}")
        except ImportError as exc:
            print(f"{name:24} skipped ({exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
