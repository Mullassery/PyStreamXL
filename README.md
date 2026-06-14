# streamxl

**High-performance streaming XLSX reader for Python — powered by Rust**

[![CI](https://github.com/Mullassery/StreamXL/actions/workflows/ci.yml/badge.svg)](https://github.com/Mullassery/StreamXL/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/streamxl)](https://pypi.org/project/streamxl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The problem with existing XLSX libraries

Benchmarked on Apple Silicon, Python 3.13, Rust 1.96 — 10 mixed-type columns:

| Rows | streamxl | openpyxl read_only | openpyxl full load | Speedup |
|------|----------|--------------------|--------------------|---------|
| 10,000 | **0.40s** / 2.8 MB | 1.52s / 1.5 MB | 1.94s / 38 MB | **3.8×** |
| 50,000 | **1.81s** / 13.8 MB | 7.72s / 4.3 MB | 9.83s / 186 MB | **4.3×** |
| 100,000 | **3.59s** / 27.5 MB | 15.80s / 8.1 MB | 19.77s / 373 MB | **4.4×** |
| 250,000 | **9.04s** / 68.7 MB | 40.46s / 19.6 MB | 50.67s / **911 MB** | **4.5×** |

streamxl processes ~27,000 rows/sec consistently. openpyxl full load approaches 1 GB RAM at 250k rows and crashes beyond that on typical cloud instances. See [`benchmarks/results.md`](benchmarks/results.md) for full details.

---

## Installation

```bash
pip install streamxl
```

Requires Python 3.8+. Pre-built wheels for Linux, macOS (Apple Silicon + Intel), Windows.

---

## Usage

### Basic — iterate rows

```python
import streamxl

for row in streamxl.read("data.xlsx"):
    print(row)
# ['Name', 'Age', 'Score']
# ['Alice', 30.0, 95.5]
# ...
```

### ETL pipeline — stream to CSV

```python
import csv, streamxl

with open("output.csv", "w", newline="") as f:
    writer = csv.writer(f)
    for row in streamxl.read("large.xlsx"):
        writer.writerow(row)
```

### Stream to pandas (chunk by chunk)

```python
import pandas as pd, streamxl

CHUNK = 10_000
rows = []
for row in streamxl.read("large.xlsx"):
    rows.append(row)
    if len(rows) == CHUNK:
        df = pd.DataFrame(rows)
        process(df)
        rows.clear()
```

---

## Cell value types

| XLSX type | Python type |
|-----------|-------------|
| String (shared string) | `str` |
| Number | `float` |
| Boolean | `bool` |
| Empty cell | `None` |

---

## How it works

streamxl is built in two layers:

```
streamxl.read("file.xlsx")
        │
        ▼
python/streamxl/api.py        Python iterator API
        │
        ▼
python/src/lib.rs             PyO3 bridge (zero-copy FFI)
        │
        ▼
core/src/stream.rs            Rust: orchestrates ZIP + XML parsing
   ├── zip_reader.rs          wraps the zip crate
   ├── shared_strings.rs      parses xl/sharedStrings.xml → Vec<String>
   └── sheet_parser.rs        streams <row> elements one at a time
```

1. The XLSX ZIP is opened and `sharedStrings.xml` is read once into memory (typically < 1 MB).
2. `sheet1.xml` is parsed as a stream — only one `<row>` is in memory at any time.
3. Cell values are resolved via index lookup into the shared string table.
4. PyO3 converts each Rust `Vec<CellValue>` to a Python `list` on demand.

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Benchmarks

Apple Silicon, Python 3.13, Rust 1.96 — 10 mixed-type columns (strings, floats, booleans, dates).

| Rows | streamxl | openpyxl read_only | openpyxl full load | Speedup |
|------|----------|--------------------|--------------------|---------|
| 10k  | **0.40s** · 2.8 MB | 1.52s · 1.5 MB | 1.94s · 38 MB | **3.8×** |
| 50k  | **1.81s** · 13.8 MB | 7.72s · 4.3 MB | 9.83s · 186 MB | **4.3×** |
| 100k | **3.59s** · 27.5 MB | 15.80s · 8.1 MB | 19.77s · 373 MB | **4.4×** |
| 250k | **9.04s** · 68.7 MB | 40.46s · 19.6 MB | 50.67s · **911 MB** | **4.5×** |

**4–5× faster than openpyxl across all file sizes. Throughput: ~27,000 rows/sec.**

Full results and reproduction steps: [`benchmarks/results.md`](benchmarks/results.md)

```bash
python benchmarks/openpyxl_vs_streamxl.py your_file.xlsx
```

---

## Roadmap

- [x] Streaming XLSX reader (sheet1)
- [x] sharedStrings resolution
- [x] PyO3 Python bindings
- [x] Boolean and numeric cell types
- [ ] Multi-sheet support (`sheet` parameter)
- [ ] Date/datetime cell type
- [ ] Header row as dict keys
- [ ] PyPI wheel distribution (manylinux + macOS + Windows)

---

## Development

### Prerequisites

- Rust (stable): `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- maturin: `pip install maturin`

### Build

```bash
git clone https://github.com/Mullassery/StreamXL.git
cd StreamXL
maturin develop
```

### Test

```bash
pip install pytest
pytest tests/
```

### Benchmark

```bash
bash scripts/benchmark.sh path/to/large_file.xlsx
```

---

## Contributing

PRs welcome. See [docs/design_decisions.md](docs/design_decisions.md) for context on key architectural choices before opening a large PR.

---

## License

MIT © Georgi Mullassery
