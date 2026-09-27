"""
Benchmark: openpyxl vs pystreamxl on large XLSX files.

Usage:
    python benchmarks/openpyxl_vs_streamxl.py benchmarks/large_file_test.xlsx
"""
import sys
import time
import tracemalloc


def bench_openpyxl(path: str):
    import openpyxl
    tracemalloc.start()
    t0 = time.perf_counter()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    count = sum(1 for _ in ws.iter_rows())
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return count, elapsed, peak / 1024 / 1024


def bench_streamxl(path: str):
    import pystreamxl
    tracemalloc.start()
    t0 = time.perf_counter()
    count = sum(1 for _ in pystreamxl.read(path))
    elapsed = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return count, elapsed, peak / 1024 / 1024


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "benchmarks/large_file_test.xlsx"

    print(f"File: {path}\n")

    rows, t, mem = bench_openpyxl(path)
    print(f"openpyxl:  {rows:,} rows | {t:.2f}s | {mem:.1f} MB peak")

    rows, t, mem = bench_streamxl(path)
    print(f"pystreamxl:  {rows:,} rows | {t:.2f}s | {mem:.1f} MB peak")
