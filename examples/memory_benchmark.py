"""Measure peak memory while streaming a file."""

import tracemalloc
import pystreamxl
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "data.xlsx"

tracemalloc.start()
count = sum(1 for _ in pystreamxl.read(path))
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Rows: {count:,}")
print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
