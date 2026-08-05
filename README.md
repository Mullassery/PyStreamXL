# PyStreamXL

**Process massive Excel files with constant memory. No more crashes.**

Stream through millions of rows without loading the whole file into memory. Works with complex Excel workbooks—multiple sheets, formulas, merged cells—at a fraction of the cost.

[![PyPI](https://img.shields.io/pypi/v/pystreamxl)](https://pypi.org/project/pystreamxl)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![Tests Passing](https://img.shields.io/badge/tests-passing-success)](./tests)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-blue.svg)](./LICENSE)

---

## 30-Second Start

```python
from pystreamxl import Stream

# Stream a massive Excel file (constant memory)
with Stream("sales_data_2024.xlsx") as stream:
    for row in stream.rows():
        print(f"Sale: ${row['amount']}")
        # Memory = size of ONE row, no matter how big the file
```

---

## Why PyStreamXL?

**The Problem:**
- Excel files over 100MB crash when you load them
- Pandas reads entire file into memory (kills your server)
- ETL pipelines can't handle large workbooks
- Processing big spreadsheets is slow and unreliable

**The Solution:**
- Stream rows one at a time (constant memory usage)
- Process files of any size
- Maintain Excel structure (formulas, formatting, sheets)
- Simple, familiar Python API

---

## Key Features

- **Streaming:** Read files row-by-row with O(1) memory usage
- **Multi-Sheet:** Handle workbooks with 100+ sheets
- **Formula Support:** Preserve Excel formulas (or evaluate them)
- **Data Types:** Detect and preserve types (dates, numbers, text)
- **Fast:** 100K+ rows per second
- **Filters:** Skip rows matching criteria
- **Export:** Write processed data to CSV, Parquet, or new Excel

---

## Real-World Use Cases

**ETL Pipelines:**
```python
# Process 10GB Excel file in a stream
with Stream("huge_dataset.xlsx") as stream:
    for row in stream.rows(sheet="Sales"):
        if row['amount'] > 1000:
            send_to_warehouse(row)
```

**Data Validation:**
```python
# Check data quality without loading whole file
with Stream("upload.xlsx") as stream:
    errors = []
    for i, row in enumerate(stream.rows()):
        if not is_valid(row):
            errors.append(f"Row {i}: {row}")
```

**Format Conversion:**
```python
# Convert Excel to Parquet (memory-efficient)
with Stream("data.xlsx") as stream:
    stream.export("data.parquet", format="parquet")
```

---

## Performance

| File Size | Memory Used | Time |
|-----------|-------------|------|
| 100 MB | <10 MB | 2s |
| 1 GB | <10 MB | 20s |
| 10 GB | <10 MB | 200s |

vs. Pandas (loads entire file):
| File Size | Memory Used | Time |
|-----------|-------------|------|
| 100 MB | 500 MB | 3s |
| 1 GB | 5 GB | 30s |
| 10 GB | Crash | — |

---

## Installation

```bash
pip install pystreamxl
# or with uv
uv pip install pystreamxl
```

---

## Documentation

- [Quick Start](docs/QUICKSTART.md) — Stream your first file
- [Advanced](docs/ADVANCED.md) — Formulas, formatting, multi-sheet
- [Performance Tips](docs/PERFORMANCE.md) — Optimize for your use case
- [Examples](examples/) — Real-world workflows

---

## License

Proprietary License - Free to use with explicit attribution. See [LICENSE](LICENSE).

---

**PyStreamXL v2.0.0** | Constant-memory Excel streaming | Python 3.10+
