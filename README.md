# PyStreamXL

## Problem

`openpyxl` and similar pure-Python Excel readers load the whole workbook
into memory before you can touch a single row — fine for small files, a
real ceiling for ETL pipelines and data engineering workloads working
against large `.xlsx` exports.

## Solution

**Stream large `.xlsx` files row-by-row in constant memory, powered by a Rust core with no `unsafe` code.**

`pip install`s as `pystreamxl`, `import pystreamxl`. Read multi-sheet Excel workbooks without loading them fully into memory, extract formulas and comments, write new `.xlsx` files, and append to existing ones — all through a small, plain Python API backed by a Rust engine.

[![PyPI](https://img.shields.io/pypi/v/pystreamxl)](https://pypi.org/project/pystreamxl/)
[![CI](https://github.com/Mullassery/PyStreamXL/actions/workflows/ci.yml/badge.svg)](https://github.com/Mullassery/PyStreamXL/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)

## Use cases

- **ETL against large Excel exports** that don't fit comfortably in memory
  with `openpyxl` — `read()` keeps memory flat regardless of file size.
- **Extracting formulas/comments for audit or migration tooling**, not
  just cell values.
- **Appending to a growing log-style `.xlsx` file** without rewriting the
  whole workbook or losing other sheets.
- **Not yet a good fit for:** SQL-style querying across sheets, formula
  *evaluation* (only extraction/classification), or pandas/Parquet/Arrow
  export built in — see [Honest feature list](#honest-feature-list) for
  the full "what's not here" list.

---

## Install

```bash
pip install pystreamxl
```

A prebuilt wheel is currently published only for macOS (arm64); other platforms install from the source distribution, which requires a Rust toolchain (see `rust-toolchain.toml`) and [maturin](https://www.maturin.rs/) to build. Every PyPI release to date (1.2.0 through 5.2.0) has shipped exactly one platform wheel plus an sdist — no Linux or Windows wheels have been published yet.

## Quick start

```python
import pystreamxl

for row in pystreamxl.read("data.xlsx"):
    print(row)  # ['Name', 'Age', 'Score']
```

`read()` streams rows one at a time — memory use stays flat regardless of file size.

## Real, working examples

**Read as dictionaries, keyed by header row:**

```python
import pystreamxl

for row in pystreamxl.read("sales.xlsx", as_dict=True):
    print(row["Customer"], row["Amount"])
```

**Read only specific columns:**

```python
for row in pystreamxl.read("sales.xlsx", as_dict=True, columns=["Customer", "Amount"]):
    ...
```

**Read every sheet in a workbook:**

```python
sheet_names = pystreamxl.sheets("workbook.xlsx")
all_data = pystreamxl.read_all("workbook.xlsx")  # {sheet_name: [rows...]}
```

**Write a new `.xlsx` file:**

```python
import datetime
import pystreamxl

pystreamxl.write("report.xlsx", [
    ["Name", "Joined", "Score"],
    ["Alice", datetime.date(2024, 1, 15), 95.5],
    ["Bob", datetime.date(2024, 3, 2), 88.0],
])
```

**Stream-write multiple sheets without holding the whole file in memory:**

```python
with pystreamxl.writer("report.xlsx") as w:
    w.write_row(["Name", "Age"])
    w.write_row(["Alice", 30])
    w.add_sheet("Summary")
    w.write_row(["Total", 1])
```

**Append rows to an existing file (other sheets are preserved):**

```python
pystreamxl.write("log.xlsx", [["Date", "Event"]])
pystreamxl.append("log.xlsx", [[datetime.date.today(), "started"]])
pystreamxl.append("log.xlsx", [[datetime.date.today(), "finished"]])
```

**Extract formulas and comments:**

```python
rows = list(pystreamxl.read("model.xlsx", with_formulas=True))
# each cell is a dict: {"value": ..., "formula": ..., "formula_type": ...,
#                        "comment": ..., "comment_author": ...}

from pystreamxl import FormulaSerializer
export = FormulaSerializer.export_formulas(rows)
FormulaSerializer.export_to_json(rows, "formulas.json")
FormulaSerializer.export_to_csv(rows, "formulas.csv")  # sanitized against CSV/formula injection
```

**Export to CSV safely** — untrusted cell content is never written to CSV verbatim (see [Security](#security) below):

```python
import csv
import pystreamxl
from pystreamxl.security import sanitize_csv_cell

with open("output.csv", "w", newline="") as f:
    writer = csv.writer(f)
    for row in pystreamxl.read("large.xlsx"):
        writer.writerow([sanitize_csv_cell(cell) for cell in row])
```

**Validate a file and recover from bad cells instead of crashing:**

```python
from pystreamxl import validate_excel_file

report = validate_excel_file("questionable.xlsx")
if report.has_fatal_errors():
    print(report.format_summary())
```

More runnable examples live in [`examples/`](examples/).

## Honest feature list

What's here and real, backed by the Rust core and covered by the test suite:

- **Streaming reads** — `read()` / `stream()`: a real Rust `__iter__`/`__next__` iterator over the sheet — you get rows one at a time, not a pre-built Python list. **Fixed for real (2026-10-04):** a 2026-09-22 benchmark had found this was *not* actually O(1) memory as claimed (`XlsxStream::open()` decompressed the whole sheet XML before iteration started, so peak RSS scaled with sheet size). `SheetParser` now streams the zip entry's body incrementally via a real `BufRead` source instead of buffering it first — re-verified via live RSS sampling across a 1.2M-row file: memory plateaus within the first 50k rows and stays flat (<0.1% drift) for the remaining 1.15M rows. See gap #10 in [`ROADMAP_HONEST.md`](ROADMAP_HONEST.md) for the full before/after and the one remaining, intentional per-file (not per-row) cost. `read_rows_all_at_once()`/`read_rows_with_metadata_all_at_once()` remain available as an explicit escape hatch for callers that need random access or to iterate the result more than once.
- **Multi-sheet support** — `sheets()`, `read_all()`, and `writer().add_sheet()`.
- **Streaming writes** — `write()`, `writer()`, `append()`, all producing real `.xlsx` files.
- **Formula extraction** — read formula text and a best-effort formula-type classification (`with_formulas=True`), plus `FormulaReferenceMapper` for shifting/rewriting cell references and `FormulaSerializer` for exporting/importing formulas as JSON or CSV.
- **Comment extraction** — cell comments and authors, via `with_formulas=True`.
- **Conditional formatting rules** — `conditional_formats()` reads every `<conditionalFormatting>`/`<cfRule>` in a sheet (type, operator, formulas, priority, `stopIfTrue`) and resolves each rule's `dxfId` against `xl/styles.xml`'s `<dxfs>` into concrete font color/bold/italic and fill colors. `colorScale`/`dataBar`/`iconSet` rules are captured (type, sqref, priority) but their inline color-stop/threshold definitions aren't modeled — those rule types don't use `dxfId` in the first place.
- **Type-aware cells** — strings, numbers, booleans, dates, datetimes, and empty cells round-trip correctly.
- **Error recovery & validation** — `validate_excel_file()` and `ErrorRecoveryHandler` classify and (optionally) recover from malformed cells instead of hard-failing on the whole file.
- **Security hardening** — path validation, file-size limits, and ZIP-bomb defenses (entry-size, compression-ratio, and total-decompressed-size limits) enforced before/while a file is opened. CSV export is sanitized against formula-injection (see below).
- **REST API (optional)** — `pystreamxl.server.StreamXLServer` / `create_flask_app()` wrap the real streaming engine behind HTTP endpoints (`/sources`, `/sources/<id>/query`, `/sources/<id>/export`, ...). Requires `pip install "pystreamxl[server]"`.

What's **not** here, so you don't have to find out the hard way:

- No SQL-style query language — `execute_query()` in the REST API streams rows from a named sheet, it does not parse arbitrary queries.
- No pandas/Parquet/Arrow export built in. Convert `read()`'s output yourself, or open an issue if this matters to you.
- No formula *evaluation* — formula text is extracted and classified, not recalculated.
- The `pystreamxl dashboard` CLI command renders sample data, not live telemetry — every mode (bare, `--static`, `--alerts`, `--recommendations`, `--export`) shows the same explicit "SAMPLE DATA — not live" warning.

## Security

- **Path & size validation** — `validate_read_path()` / `validate_write_path()` reject non-`.xlsx` paths, path traversal, and oversized files before any parsing happens.
- **ZIP-bomb defenses** — the Rust core enforces a per-entry size limit, a compression-ratio limit, and a total-decompressed-size limit while unpacking a workbook (see `core/src/zip_reader.rs`), tested against real crafted archives in `core/tests/zip_bomb_defense.rs`.
- **CSV/formula-injection protection** — `pystreamxl.security.sanitize_csv_cell()` neutralizes any string cell that starts with `=`, `+`, `-`, `@`, TAB, or CR (the standard CSV-injection trigger set) by prefixing it with `'`, so a malicious workbook can't turn a CSV export into an executable formula when reopened in Excel/LibreOffice/Google Sheets. `FormulaSerializer.export_to_csv()` applies this automatically; apply it yourself when writing CSV from `read()` output (see the example above).

**Limits, enforced by default (no configuration needed):**

| Limit | Value |
|---|---|
| Max file size | 512 MB |
| Max size per ZIP entry | 512 MB |
| Max total decompressed size | 1 GB |
| Max compression ratio | 30:1 |

Handle malformed or malicious files by catching `SecurityError`:

```python
from pystreamxl import SecurityError, read

try:
    for row in read("data.xlsx"):
        process(row)
except SecurityError as e:
    print(f"Security violation: {e}")
```

Found a security issue? See [SECURITY.md](SECURITY.md).

## Performance

Rows are parsed and yielded one at a time rather than being collected into a Python list up front, and it's consistently faster than `openpyxl` on both reads and writes. Memory now stays flat during iteration regardless of sheet size (fixed 2026-10-04 — see "Honest feature list" above and [`ROADMAP_HONEST.md`](ROADMAP_HONEST.md) gap #10 for the before/after). See [`benchmarks/`](benchmarks/) for the scripts used to compare against `openpyxl`, and [`examples/memory_benchmark.py`](examples/memory_benchmark.py) to measure it yourself against your own files (note: that script uses `tracemalloc`, which only tracks Python-allocator memory, not the Rust-side heap — for a true peak-RSS measurement use `resource.getrusage`/`psutil` sampled during iteration instead, as `ROADMAP_HONEST.md` gap #10 did):

```bash
python examples/memory_benchmark.py your_file.xlsx
```

Actual numbers depend heavily on your file's structure (shared strings, formulas, formatting) — measure on your own workloads rather than trusting a generic table.

### vs openpyxl, on real data

Methodology: 150,000 real, live NYC 311 Service Request rows pulled from
NYC Open Data's Socrata API (`data.cityofnewyork.us/resource/erm2-nwe9`,
current as of 2026-09-22 — not synthetic/fabricated rows), 14 columns,
written to a real 2-sheet `.xlsx` workbook (75k rows/sheet, 19MB) via
`openpyxl`. Both libraries iterated every row of every sheet; row counts
and a positional checksum matched exactly across all three methods
(correctness verified, not just speed). 3 runs each, median reported,
single-process wall-clock via `time.perf_counter()`, peak RSS via
`resource.getrusage(...).ru_maxrss` on macOS/arm64, Python 3.13.

| Rows | pystreamxl `read()` | openpyxl `read_only=True` | openpyxl full load |
|------|---|---|---|
| 10,000  | 0.07s · 28MB peak RSS | 0.61s · 31MB peak RSS | — |
| 30,000  | 0.19s · 52MB peak RSS | 1.89s · 32MB peak RSS | — |
| 75,000  | 0.48s · 103MB peak RSS | 4.72s · 36MB peak RSS | — |
| 150,000 (2 sheets) | 0.96s · 192MB peak RSS | 9.27s · 43MB peak RSS | 13.5s · 1,040MB peak RSS |

**pystreamxl is ~9.7x faster than `openpyxl(read_only=True)` and ~14x
faster than `openpyxl()` full-load** at 150k rows — but at that size it
uses **~4.5x more peak memory than `openpyxl(read_only=True)`** (192MB
vs 43MB), because `read()` isn't actually O(1) yet (see above). If your
bottleneck is wall-clock time, pystreamxl wins clearly. If your bottleneck
is memory on a very large file and you don't need every column loaded at
once, `openpyxl(read_only=True)` currently uses less RAM. Reproduce with
`benchmarks/openpyxl_vs_streamxl.py` against any real `.xlsx` file.

## CLI

```bash
pystreamxl dashboard          # sample extraction dashboard (unlabeled placeholder, see note above)
pystreamxl dashboard --static # same sample data, clearly labeled "SAMPLE DATA — not live"
pystreamxl --version
```

## Development

```bash
git clone https://github.com/Mullassery/PyStreamXL.git
cd PyStreamXL
pip install -e ".[dev]"       # builds the Rust extension via maturin and installs test deps
pytest tests/ -v
cargo test --release --all-features     # Rust unit + integration tests (both core and python crates)
```

On macOS you may need `RUSTFLAGS="-C link-args=-undefined -C link-args=dynamic_lookup"` before `cargo build`/`cargo test` for the PyO3 extension crate to link outside of `maturin`/`pip install`.

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

## Docs

- [`docs/architecture/README.md`](docs/architecture/README.md) — how the Rust engine and Python API fit together, including known dead code
- [`docs/xlsx_format.md`](docs/xlsx_format.md) — XLSX/ZIP/XML format notes
- [`ROADMAP_HONEST.md`](ROADMAP_HONEST.md) — unvarnished list of what's missing, broken, or technical debt
- [`CHANGELOG.md`](CHANGELOG.md) — release history
- [`SECURITY.md`](SECURITY.md) — security model, limits, and what it does *not* protect against

## License

This project is licensed under the [Apache License 2.0](LICENSE).

---

**PyStreamXL** | Constant-memory Excel streaming | Rust core, Python API
