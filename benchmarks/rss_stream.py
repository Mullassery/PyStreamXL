"""Measure peak RSS while streaming a large XLSX with PyStreamXL.

This is the missing evidence for the "flat memory" claim: generate a large
file, read it row-by-row, and print process peak RSS before/after. It measures
the process, not just the Rust iterator, so Python-row overhead is included.

Usage: python benchmarks/rss_stream.py [rows]
"""

from __future__ import annotations

import resource
import sys
from pathlib import Path

from openpyxl import Workbook


def peak_rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes; Linux reports KiB.
    return value / (1024 * 1024) if sys.platform == "darwin" else value / 1024


def make_file(path: Path, rows: int) -> None:
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Data")
    ws.append(["id", "name", "value", "category", "notes"])
    for i in range(1, rows + 1):
        ws.append([i, f"User_{i}", i * 1.5, f"Cat_{i % 20}", f"Note {i}"])
    wb.save(path)


def main() -> int:
    import pystreamxl

    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 500_000
    path = Path("benchmarks/rss_stream.xlsx")
    if not path.exists():
        print(f"generating {rows} rows...", flush=True)
        make_file(path, rows)
    before = peak_rss_mb()
    count = 0
    for _ in pystreamxl.read(str(path)):
        count += 1
    after = peak_rss_mb()
    print(f"rows={count} peak_rss_before={before:.1f}MB peak_rss_after={after:.1f}MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
