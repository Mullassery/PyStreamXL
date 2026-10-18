# PyStreamXL vs python-calamine / Polars

**Environment:** macOS arm64, Python 3.12, 50,000 rows × 10 columns.
Generated with openpyxl by `calamine_vs_pystreamxl.py`.

| Library | Time | Semantics |
|---|---:|---|
| PyStreamXL | 3.870s | Streams rows; no full-sheet materialization |
| python-calamine | 0.192s | Loads the whole sheet into Python lists |
| Polars | not run | Requires the optional `fastexcel` package |

**Interpretation:** calamine is much faster for whole-sheet loads, which is its
design. PyStreamXL's value is bounded memory on very large sheets, not raw
speed against a vectorized loader. Do not claim PyStreamXL is faster than
calamine or Polars; the committed openpyxl comparison (3.8–5.6×) is a different
baseline.

Reproduce:

```bash
pip install python-calamine polars fastexcel
python benchmarks/calamine_vs_pystreamxl.py 50000
```
