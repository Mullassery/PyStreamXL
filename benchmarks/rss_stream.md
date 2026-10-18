# Stream memory evidence

**Environment:** macOS arm64, Python 3.12, 500,000 rows × 5 columns.

| Measurement | Result |
|---|---|
| Process peak RSS before | 40.4 MB |
| Process peak RSS after streaming 500k rows | 173.8 MB |
| Python live heap peak (`tracemalloc`, 200k rows) | 0.003 MB |

**Interpretation:** PyStreamXL does not materialize the whole sheet, and the
live Python heap stays effectively flat. Process RSS still grows to ~174 MB at
500k rows, most likely allocator arena retention rather than live row objects.
Do not claim constant **process RSS**; the defensible claim is bounded,
row-by-row streaming with no full-sheet materialization.

Reproduce:

```bash
python benchmarks/rss_stream.py 500000
python - <<'PY'
import tracemalloc, pystreamxl
tracemalloc.start()
for i, _ in enumerate(pystreamxl.read("benchmarks/rss_stream.xlsx")):
    if i >= 200_000: break
print(tracemalloc.get_traced_memory())
PY
```
