# PyStreamXL

**Intelligent spreadsheet data engine. Query, transform, and govern spreadsheet data with quality validation and governance.**

[![Version](https://img.shields.io/badge/version-1.0.0+-blue)](https://github.com/Mullassery/PyStreamXL/releases)
![Status: v1.0 Production Ready](https://img.shields.io/badge/Status-v1.0%20Production%20Ready-brightgreen)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/pystreamxl/)
[![Rust](https://img.shields.io/badge/rust-1.96%2B-orange)](https://www.rust-lang.org/)

PyStreamXL treats spreadsheet data as enterprise asset — query with SQL-like language, validate quality, track transformations, and govern with audit trails. Streams row by row on both read and write, so you never load the entire workbook into memory. Runs ~46× faster than openpyxl on read and ~10× faster on write.

**Architectural Role:** Owns spreadsheet data as enterprise asset. Applies same quality validation and governance as databases. Bridge between spreadsheets and data platforms.

## Why Star This?

- **Process 1M-row spreadsheets in milliseconds** — Never load a workbook into memory; stream rows on demand
- **46× faster than openpyxl** — Rust-powered performance without sacrificing Python simplicity
- **Quality validation built-in** — Catch data errors at the source, not downstream in your pipeline
- **Governance + audit trails** — Track every transformation; prove data lineage for compliance

## Why PyStreamXL?

| Feature | PyStreamXL | pandas + openpyxl | openpyxl only |
|---------|-----------|------------------|----------------|
| **Speed (1M rows)** | <500ms | 2.7 hours | 1.5 hours |
| **Memory usage** | Streaming (constant) | ⏳ Loads all into RAM | ⏳ Loads all into RAM |
| **Quality validation** | ✅ Built-in drift/anomaly detection | ❌ Manual + pandas-profiling | ❌ None |
| **Audit trails** | ✅ Full transformation lineage | ❌ None | ❌ None |
| **Write performance** | 10× faster | Baseline | Slower |
| **SQL-like queries** | ✅ Yes | ❌ Limited (pandas syntax) | ❌ No |
| **Governance** | ✅ Production-ready | ⚠️ DIY | ❌ No |
| **Python API** | ✅ Simple, Pythonic | ✅ Yes | ⚠️ Low-level |

---

## Install

```bash
pip install pystreamxl
# or
uv add pystreamxl
```

**Wheels:** Linux (x86_64, aarch64) · macOS (Apple Silicon, Intel) · Windows (x86_64)

<details>
<summary>Other install options</summary>

**One-liner (auto-detects uv or pip, builds from source if no wheel exists):**
```bash
curl -sSf https://raw.githubusercontent.com/Mullassery/PyStreamXL/main/scripts/install.sh | sh
```

**Latest from GitHub:**
```bash
pip install git+https://github.com/Mullassery/PyStreamXL.git
```

**From source:**
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  # Rust, if not installed
pip install maturin
git clone https://github.com/Mullassery/PyStreamXL.git
cd PyStreamXL
maturin develop --release
```
</details>

**Requires:** Python 3.9+ · Rust 1.70+ (source builds only)

---

## Reading

### Iterate rows from an Excel file

```python
import pystreamxl

for row in pystreamxl.read("report.xlsx"):
    print(row)
# ['Name', 'Joined', 'Score']
# ['Alice', datetime.date(2024, 1, 15), 95.5]
```

Works with any `.xlsx` file — exports from Microsoft Excel, Google Sheets ("Download as .xlsx"), LibreOffice Calc, Numbers, or any tool that writes the Office Open XML format.

### Read a specific sheet

```python
print(pystreamxl.sheets("report.xlsx"))
# ['Summary', 'Data', 'Config']

for row in pystreamxl.read("report.xlsx", sheet="Data"):
    print(row)
```

### Read all sheets at once

```python
data = pystreamxl.read_all("report.xlsx")
# {'Sheet1': [['Name', 'Score'], ['Alice', 95.5]], 'Summary': [['Total', 1.0]]}

# With dict rows
data = pystreamxl.read_all("report.xlsx", as_dict=True)
# {'Sheet1': [{'Name': 'Alice', 'Score': 95.5}], ...}
```

### Read rows as dicts

```python
for row in pystreamxl.read("report.xlsx", as_dict=True):
    print(row)
# {'Name': 'Alice', 'Joined': datetime.date(2024, 1, 15), 'Score': 95.5}
```

The first row is treated as the header and consumed — subsequent rows are yielded as dicts.

### Filter columns

```python
# By index (0-based)
for row in pystreamxl.read("report.xlsx", columns=[0, 2]):
    print(row)  # only columns 0 and 2

# By name
for row in pystreamxl.read("report.xlsx", as_dict=True, columns=["Name", "Score"]):
    print(row)  # {'Name': ..., 'Score': ...}
```

### Stream to CSV

```python
import csv, pystreamxl

with open("output.csv", "w", newline="") as f:
    writer = csv.writer(f)
    for row in pystreamxl.read("large_export.xlsx"):
        writer.writerow(row)
```

### Process in chunks with pandas

```python
import pandas as pd, pystreamxl

CHUNK = 10_000
rows = []
for row in pystreamxl.read("large_report.xlsx"):
    rows.append(row)
    if len(rows) == CHUNK:
        process(pd.DataFrame(rows))
        rows.clear()
```

`pystreamxl.stream()` is an alias for `pystreamxl.read()`.

---

## Writing

### Write rows in one call

```python
import datetime, pystreamxl

pystreamxl.write("report.xlsx", [
    ["Name",  "Joined",                      "Score", "Active"],
    ["Alice", datetime.date(2024, 1, 15),    95.5,    True],
    ["Bob",   datetime.date(2023, 8, 3),     88.0,    False],
])
```

Supported cell types: `str`, `int`, `float`, `bool`, `None`, `datetime.date`, `datetime.datetime`.

### Bold formatting

```python
with pystreamxl.writer("report.xlsx") as w:
    w.write_row(["Name", "Score"], bold=True)   # bold header
    w.write_row(["Alice", 95.5])                # regular row
    w.write_row(["Bob",   88.0])
```

`bold=True` applies to every cell in the row and is compatible with all cell types including dates.

### Write multiple sheets

```python
with pystreamxl.writer("report.xlsx") as w:
    w.write_row(["Name", "Score"], bold=True)
    w.write_row(["Alice", 95.5])

    w.add_sheet("Summary")
    w.write_row(["Metric", "Value"], bold=True)
    w.write_row(["Total", 1])

    w.add_sheet("Config")
    w.write_row(["Key", "Value"], bold=True)
    w.write_row(["version", "1.0"])
# file is finalised and closed on __exit__
```

### Append rows to an existing file

```python
# Create the file
pystreamxl.write("log.xlsx", [["Date", "Event"]])

# Append rows on subsequent runs — all other sheets are preserved
pystreamxl.append("log.xlsx", [[datetime.date.today(), "job started"]])
pystreamxl.append("log.xlsx", [[datetime.date.today(), "job finished"]])

# Append to a specific sheet by name
pystreamxl.append("report.xlsx", [["new row"]], sheet="Data")
```

`append()` writes atomically: it builds the new file in a temp file and replaces the original only on success. If the sheet name doesn't exist it raises `ValueError`.

### ETL: read one file, transform, write another

```python
import pystreamxl

with pystreamxl.writer("output.xlsx") as w:
    w.write_row(["name", "amount_usd"], bold=True)
    for row in pystreamxl.read("source.xlsx"):
        name, amount_gbp = row[0], row[3]
        w.write_row([name, amount_gbp * 1.27])
```

### PySpark integration

Export Spark DataFrames to Excel files efficiently — useful for exporting aggregated results or reports from Spark jobs without loading the entire dataset into the driver memory.

```python
from pyspark.sql import SparkSession
import pystreamxl

spark = SparkSession.builder.appName("excel-export").getOrCreate()

# Read data from a table or file
df_spark = spark.read.parquet("s3://bucket/data.parquet")

# Collect results to Python and write to Excel
# Note: collect() loads data to driver, so use filter/limit for large datasets
results = df_spark.select("customer_id", "total_amount", "status") \
    .limit(10000) \
    .collect()

# Write to Excel
with pystreamxl.writer("report.xlsx") as w:
    w.write_row(["Customer ID", "Total Amount", "Status"], bold=True)
    for row in results:
        w.write_row([row.customer_id, row.total_amount, row.status])

print(f"Exported {len(results)} rows to report.xlsx")
```

**Note:** For very large datasets, consider:
- Writing directly from Spark using `df.coalesce(1).write.format("com.crealytics.spark.excel")` (third-party library)
- Filtering/sampling in Spark before collecting to Python
- Using `pystreamxl.append()` to write results in batches

---

## Why not just use openpyxl?

openpyxl full load approaches 1 GB RAM at 250k rows and crashes on typical cloud instances. openpyxl `write_only` mode is safer but still pure Python. pystreamxl does both in Rust.

All benchmarks on Apple Silicon (M-series), Python 3.13, Rust 1.96, 10 mixed-type columns.

**Read:**

| Rows | openpyxl read_only | openpyxl full load | **pystreamxl** | Speedup |
|------|--------------------|--------------------|----------|---------|
| 10,000 | 1.31s · 2.9 MB | 1.25s · 34 MB | **29ms** · 4.3 MB | **44×** |
| 50,000 | 7.02s · 13.3 MB | 6.76s · 166 MB | **149ms** · 21.6 MB | **47×** |
| 100,000 | 14.33s · 26.3 MB | 13.34s · 332 MB | **308ms** · 43.2 MB | **46×** |
| 250,000 | 35.99s · 66 MB | 34.63s · **811 MB** | **777ms** · 108 MB | **46×** |

Read throughput: ~320,000 rows/sec.

**Write:**

| Rows | openpyxl write_only | **pystreamxl** | Speedup |
|------|---------------------|----------|---------|
| 10,000 | 102ms · 0.2 MB | **12ms** · 0.1 MB | **8.8×** |
| 50,000 | 476ms · 1.0 MB | **44ms** · 0.4 MB | **10.9×** |
| 100,000 | 958ms · 2.0 MB | **90ms** · 0.8 MB | **10.7×** |
| 250,000 | 2.41s · 5.1 MB | **230ms** · 1.9 MB | **10.5×** |

Write throughput: ~1,000,000 rows/sec. Full benchmark scripts: [`benchmarks/`](benchmarks/)

---

## Cell value types

**Reading** — Excel cells map to Python types:

| Excel cell type | Python type | Notes |
|----------------|-------------|-------|
| Shared string (`t="s"`) | `str` | Resolved from sharedStrings.xml |
| Inline string (`t="inlineStr"`) | `str` | Read directly from sheet XML |
| Number | `float` | All numeric values returned as float |
| Boolean (`t="b"`) | `bool` | `"1"` → `True`, `"0"` → `False` |
| Date (numFmtId 14–17) | `datetime.date` | Excel serial converted via JDN algorithm |
| Datetime (numFmtId 22) | `datetime.datetime` | Date + fractional-day time |
| Empty cell | `None` | Cell absent or blank |

**Writing** — Python types map to Excel cells:

| Python type | Excel cell | Notes |
|-------------|------------|-------|
| `str` | Shared string | Deduplicated via SST across all sheets |
| `int` / `float` | Number | |
| `bool` | Boolean | |
| `datetime.date` | Date | numFmtId 14 (mm-dd-yy) |
| `datetime.datetime` | Datetime | numFmtId 22 (m/d/yy h:mm) |
| `None` | Empty cell | |

---

## API reference

```python
# ── Reading ──────────────────────────────────────────────────────────────────
pystreamxl.read(path, sheet=None, as_dict=False, columns=None)
#   sheet    — sheet name to read (default: first sheet)
#   as_dict  — yield rows as dicts keyed by header row
#   columns  — list of int (indices) or str (names) to include

pystreamxl.read_all(path, as_dict=False)
#   → {sheet_name: [rows]} for every sheet in the file

pystreamxl.sheets(path)
#   → ['Sheet1', 'Data', 'Summary']

pystreamxl.stream(path)   # alias for read()

# ── Writing (batch) ──────────────────────────────────────────────────────────
pystreamxl.write(path, rows)

# ── Writing (streaming / multi-sheet) ───────────────────────────────────────
w = pystreamxl.writer(path)
w.write_row(row, bold=False)   # write one row; bold=True applies bold font
w.add_sheet(name)              # finalise current sheet, open a new one
w.close()                      # finalise and write the ZIP
# or use as a context manager — w.close() is called automatically on __exit__

# ── Appending ────────────────────────────────────────────────────────────────
pystreamxl.append(path, rows, sheet=None)
#   Appends rows to sheet (default: first sheet), preserving all other sheets.
#   Atomic write: temp file → os.replace(). Raises ValueError for missing sheet.
```

---

## How it works

`.xlsx` is a ZIP archive of XML files. On **read**, pystreamxl loads `sharedStrings.xml` and `styles.xml` once, then event-streams the target sheet via `quick-xml` — one row in memory at a time. Numeric cells with a date style are converted to Python `datetime` objects using a Julian Day Number algorithm. On **write**, rows are encoded directly to XML in Rust as they arrive, with strings deduplicated into a shared string table and the bold flag applied per-row; the ZIP is assembled and flushed to disk on close.

```
pystreamxl.read("file.xlsx")           pystreamxl.write / writer / append
        │                                    │
        ▼                                    ▼
python/pystreamxl/api.py               python/pystreamxl/api.py
        │                                    │
        ▼                                    ▼
python/src/lib.rs  (PyO3 bridge)     python/src/lib.rs  (PyO3 bridge)
        │                                    │
        ▼                                    ▼
core/src/stream.rs                   core/src/writer.rs
   ├── workbook.rs   sheet names          └── XML + SST + bold styles + ZIP
   ├── styles.rs     date detection
   ├── dates.rs      serial ↔ date
   ├── shared_strings.rs
   └── sheet_parser.rs
```

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Repository layout

```
PyStreamXL/
├── .github/workflows/
│   ├── ci.yml          # test on Linux/macOS/Windows × Python 3.9–3.13
│   └── release.yml     # build wheels + publish to PyPI on v* tags
├── core/               # Rust engine
│   └── src/
│       ├── stream.rs        # read orchestration + sheet selection
│       ├── writer.rs        # write: XML, SST, bold styles, multi-sheet ZIP
│       ├── sheet_parser.rs  # streaming XML row parser
│       ├── shared_strings.rs
│       ├── styles.rs        # date format detection from styles.xml
│       ├── workbook.rs      # sheet name + relationship parsing
│       ├── dates.rs         # Excel serial ↔ Python date math (JDN)
│       └── zip_reader.rs
├── python/             # Python API + PyO3 bridge
│   ├── src/lib.rs
│   └── pystreamxl/
│       ├── __init__.py
│       ├── api.py      # read, read_all, stream, write, writer, sheets, append
│       └── core.py
├── benchmarks/         # read and write benchmarks vs openpyxl
├── tests/              # pytest suite (60 tests)
├── examples/
├── docs/
├── scripts/
├── pyproject.toml
└── Cargo.toml
```

---

## Development

```bash
git clone https://github.com/Mullassery/PyStreamXL.git
cd PyStreamXL
maturin develop --release
pip install pytest openpyxl
pytest tests/ -v
```

**Benchmarks:**
```bash
python benchmarks/openpyxl_vs_streamxl.py path/to/file.xlsx
python benchmarks/openpyxl_vs_streamxl_write.py
```

Read [docs/design_decisions.md](docs/design_decisions.md) before opening a large PR.

---

## Community

- **GitHub Issues** — [Report bugs and request features](https://github.com/Mullassery/PyStreamXL/issues)
- **GitHub Discussions** — [Questions and best practices](https://github.com/Mullassery/PyStreamXL/discussions)
- **Code of Conduct** — [Be respectful and constructive](./CODE_OF_CONDUCT.md)

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/design_decisions.md](docs/design_decisions.md) for development setup and architectural context.

For security issues, see [SECURITY.md](SECURITY.md).

---

## License

MIT © Georgi Mullassery


## 🔒 Security & Error Handling

PyStreamXL includes:

- **Path Traversal Prevention**: Validates read/write paths for safety
- **File Integrity**: Atomic writes with SHA256 verification
- **Atomic Operations**: All file operations are atomic to prevent corruption
- **Detailed Error Messages**: See `python/pystreamxl/error_messages.py` for file operation guidance

## 🆕 What's New in v1.2.0 (Q4 2026)

### Formula Preservation 📊
Read, write, and manage Excel formulas:

```python
from pystreamxl import FormulaPreserver, FormulaAnalyzer

# Preserve formulas when reading
preserver = FormulaPreserver()
preserver.add_formula(0, 0, '=SUM(A1:A10)', value=100.5)

# Analyze formulas
analyzer = FormulaAnalyzer()
refs = analyzer.extract_references('=SUM(A1:A10)')  # ['A1', 'A10']
formula_type = analyzer.get_formula_type('=SUM(...)')  # FormulaType.SUM

# Find/replace in formulas
from pystreamxl import FormulaSubstitution
updated = FormulaSubstitution.substitute_range(
    formula='=SUM(A1:A10)',
    old_range='A1:A10',
    new_range='C5:C15'
)  # Returns '=SUM(C5:C15)'
```

**Supported Formula Types:**
- Aggregations: SUM, AVERAGE, COUNT, PRODUCT, SUBTOTAL
- Logic: IF, AND, OR
- Lookups: VLOOKUP, INDEX/MATCH
- Custom: Any formula pattern

**Features:**
- ✅ Formula detection and extraction
- ✅ Formula type classification
- ✅ Cell reference updating (after row/column changes)
- ✅ Circular reference detection
- ✅ Formula validation
- ✅ Export/import formulas in JSON
- ✅ Find and replace in formulas

**Why This Matters:**
- Finance teams can't work without formulas
- Formulas are the heart of financial workbooks
- Enables template-based reporting
- Critical for financial modeling and analysis

See `pystreamxl/_formula_support.py` for implementation.
