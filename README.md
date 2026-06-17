# streamxl

**Read large `.xlsx` files row by row without loading them into memory — powered by Rust.**

[![CI](https://github.com/Mullassery/StreamXL/actions/workflows/ci.yml/badge.svg)](https://github.com/Mullassery/StreamXL/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/Mullassery/StreamXL/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/streamxl/)
[![Rust](https://img.shields.io/badge/rust-1.96%2B-orange)](https://www.rust-lang.org/)

If you've hit openpyxl's memory wall on a large file — or just watched it crawl through 100k rows for 20 seconds — streamxl is the drop-in fix. It streams the sheet XML one row at a time, never holding the full file in memory, and runs 4–5× faster than openpyxl across all file sizes.

---

## Install

```bash
pip install streamxl
# or
uv add streamxl
```

**Wheels:** Linux (x86_64, aarch64) · macOS (Apple Silicon, Intel) · Windows (x86_64)

<details>
<summary>Other install options</summary>

**One-liner (auto-detects uv or pip, builds from source if no wheel exists):**
```bash
curl -sSf https://raw.githubusercontent.com/Mullassery/StreamXL/main/scripts/install.sh | sh
```

**Latest from GitHub:**
```bash
pip install git+https://github.com/Mullassery/StreamXL.git
```

**From source:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  # Rust, if not installed
pip install maturin
git clone https://github.com/Mullassery/StreamXL.git
cd StreamXL
maturin develop --release
```
</details>

**Requires:** Python 3.9+ · Rust 1.70+ (source builds only)

---

## Usage

### Iterate rows

```python
import streamxl

for row in streamxl.read("data.xlsx"):
    print(row)
# ['Name', 'Age', 'Score']
# ['Alice', 30.0, 95.5]
# ...
```

### Stream to CSV

```python
import csv, streamxl

with open("output.csv", "w", newline="") as f:
    writer = csv.writer(f)
    for row in streamxl.read("large.xlsx"):
        writer.writerow(row)
```

### Process in chunks with pandas

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

`streamxl.stream()` is an alias for `streamxl.read()` — use whichever reads better in your context.

---

## Why not just use openpyxl?

Benchmarked on Apple Silicon, Python 3.13, Rust 1.96 — 10 mixed-type columns:

| Rows | streamxl | openpyxl read_only | openpyxl full load | Speedup |
|------|----------|--------------------|--------------------|---------|
| 10,000 | **0.40s** · 2.8 MB | 1.52s · 1.5 MB | 1.94s · 38 MB | **3.8×** |
| 50,000 | **1.81s** · 13.8 MB | 7.72s · 4.3 MB | 9.83s · 186 MB | **4.3×** |
| 100,000 | **3.59s** · 27.5 MB | 15.80s · 8.1 MB | 19.77s · 373 MB | **4.4×** |
| 250,000 | **9.04s** · 68.7 MB | 40.46s · 19.6 MB | 50.67s · **911 MB** | **4.5×** |

openpyxl full load approaches 1 GB RAM at 250k rows and crashes beyond that on typical cloud instances. streamxl processes ~27,000 rows/sec regardless of file size.

Full results and reproduction steps: [`benchmarks/results.md`](benchmarks/results.md)

```bash
python benchmarks/openpyxl_vs_streamxl.py your_file.xlsx
```

---

## Cell value types

| XLSX cell type | Python type | Notes |
|----------------|-------------|-------|
| Shared string (`t="s"`) | `str` | Resolved from sharedStrings.xml |
| Inline string (`t="inlineStr"`) | `str` | Read directly from sheet XML |
| Number (`t="n"` or default) | `float` | All numeric values returned as float |
| Boolean (`t="b"`) | `bool` | `"1"` → `True`, `"0"` → `False` |
| Empty cell | `None` | Cell absent or blank |

---

## Roadmap

- [x] Streaming XLSX reader (sheet1)
- [x] sharedStrings resolution
- [x] inlineStr cell type support
- [x] Boolean, numeric, and string cell types
- [x] pip and uv installable wheel
- [ ] Multi-sheet support (`sheet="SheetName"` parameter)
- [ ] Date/datetime cell type
- [ ] Header row as dict keys (`as_dict=True`)
- [ ] PyPI wheel distribution (manylinux + macOS + Windows)

---

## How it works

```
streamxl.read("file.xlsx")
        │
        ▼
python/streamxl/api.py        Python iterator API
        │
        ▼
python/src/lib.rs             Python bridge (zero-copy FFI)
        │
        ▼
core/src/stream.rs            Rust: orchestrates ZIP + XML parsing
   ├── zip_reader.rs          wraps the zip crate for entry access
   ├── shared_strings.rs      parses xl/sharedStrings.xml → Vec<String>
   └── sheet_parser.rs        streams <row> elements one at a time
```

1. The XLSX ZIP is opened; `sharedStrings.xml` is loaded once (typically < 1 MB).
2. `sheet1.xml` is event-streamed via `quick-xml` — only one `<row>` exists in memory at a time.
3. String cells are resolved via O(1) index lookup into the shared string table.
4. Each Rust `Vec<CellValue>` is converted into a Python `list` on demand, row by row.

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Repository layout

```
streamxl/
├── core/                    # Rust engine (ZIP + XML streaming)
│   └── src/
│       ├── lib.rs
│       ├── zip_reader.rs
│       ├── sheet_parser.rs  # inlineStr + sharedString + bool/number parsing
│       ├── shared_strings.rs
│       └── stream.rs
├── python/                  # Python API layer
│   ├── src/lib.rs           # Rust ↔ Python bridge
│   └── streamxl/
│       ├── __init__.py
│       ├── api.py           # streamxl.read() / streamxl.stream()
│       └── core.py
├── benchmarks/              # openpyxl vs streamxl comparison scripts
├── tests/                   # pytest test suite
├── examples/                # ETL, CSV export, memory benchmark
├── docs/                    # Architecture, API spec, XLSX format notes
├── scripts/                 # build.sh, benchmark.sh
├── pyproject.toml           # maturin build config
└── Cargo.toml               # Rust workspace root
```

---

## Development

```bash
git clone https://github.com/Mullassery/StreamXL.git
cd StreamXL
maturin develop
```

**Test:**
```bash
pip install pytest
pytest tests/ -v
```

**Benchmark:**
```bash
bash scripts/benchmark.sh path/to/large_file.xlsx
```

Read [docs/design_decisions.md](docs/design_decisions.md) before opening a large PR.

---

## Contributing

PRs welcome. See [docs/design_decisions.md](docs/design_decisions.md) for context on key architectural choices.

---

## License

MIT © Georgi Mullassery
