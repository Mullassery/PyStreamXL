"""
Benchmark: pystreamxl.write() vs openpyxl write

Usage:
    python benchmarks/openpyxl_vs_streamxl_write.py
    python benchmarks/openpyxl_vs_streamxl_write.py --rows 100000
"""

import argparse
import time
import tempfile
import os

ROW_SIZES = [10_000, 50_000, 100_000, 250_000]


def make_rows(n):
    return [[f"Name{i}", float(i), i % 2 == 0, f"category_{i % 10}"] for i in range(n)]


def bench_streamxl_write(rows, path):
    import pystreamxl

    t0 = time.perf_counter()
    pystreamxl.write(path, rows)
    return time.perf_counter() - t0


def bench_openpyxl_write(rows, path):
    import openpyxl

    t0 = time.perf_counter()
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet()
    for row in rows:
        ws.append(row)
    wb.save(path)
    return time.perf_counter() - t0


def fmt(t):
    return f"{t * 1000:.0f}ms" if t < 1 else f"{t:.2f}s"


def file_mb(path):
    return os.path.getsize(path) / 1024 / 1024


def run(row_sizes):
    print(
        f"\n{'Rows':>10}  {'pystreamxl':>12}  {'openpyxl (write_only)':>22}  {'Speedup':>8}"
    )
    print("-" * 62)

    with tempfile.TemporaryDirectory() as tmp:
        for n in row_sizes:
            rows = make_rows(n)

            sx_path = os.path.join(tmp, f"streamxl_{n}.xlsx")
            op_path = os.path.join(tmp, f"openpyxl_{n}.xlsx")

            sx_t = bench_streamxl_write(rows, sx_path)
            op_t = bench_openpyxl_write(rows, op_path)

            speedup = op_t / sx_t if sx_t > 0 else float("inf")
            sx_mb = file_mb(sx_path)
            op_mb = file_mb(op_path)

            print(
                f"{n:>10,}  "
                f"{fmt(sx_t):>8} {sx_mb:>4.1f}MB  "
                f"{fmt(op_t):>18} {op_mb:>4.1f}MB  "
                f"{speedup:>6.1f}×"
            )

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=None)
    args = parser.parse_args()

    sizes = [args.rows] if args.rows else ROW_SIZES
    run(sizes)
