# PyStreamXL

[![PyPI](https://img.shields.io/pypi/v/pystreamxl)](https://pypi.org/project/pystreamxl/)
[![CI](https://github.com/Mullassery/PyStreamXL/actions/workflows/ci.yml/badge.svg)](https://github.com/Mullassery/PyStreamXL/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](./LICENSE)

Stream large `.xlsx` files row-by-row in constant memory, powered by a Rust core with no `unsafe` code.

## What it is

PyStreamXL reads multi-sheet Excel workbooks without loading them fully into memory,
extracts formulas and comments, writes new `.xlsx` files, and appends to existing ones —
all through a small, plain Python API backed by a Rust engine. It installs as
`pystreamxl` and imports as `pystreamxl`. Compared with `openpyxl` on large exports, the
goal is flat memory use and faster wall-clock time for streaming iteration.

## Features / Highlights

- **Streaming reads** — `read()` / `stream()` return a real Rust iterator; rows are
  parsed and yielded one at a time, not collected into a Python list up front.
- **Multi-sheet support** — `sheets()`, `read_all()`, and `writer().add_sheet()`.
- **Streaming writes** — `write()`, `writer()`, and `append()` produce real `.xlsx`
  files; `append()` preserves other sheets.
- **Formula extraction** — formula text plus a best-effort formula-type classification
  (`with_formulas=True`), `FormulaReferenceMapper` for shifting/rewriting references,
  and `FormulaSerializer` for exporting/importing formulas as JSON or CSV.
- **Comment extraction** — cell comments and authors, via `with_formulas=True`.
- **Conditional formatting** — `conditional_formats()` reads every
  `<conditionalFormatting>`/`<cfRule>` (type, operator, formulas, priority,
  `stopIfTrue`) and resolves `dxfId` against `xl/styles.xml` into concrete font/fill
  values.
- **Type-aware cells** — strings, numbers, booleans, dates, datetimes, and empty cells
  round-trip correctly.
- **Error recovery & validation** — `validate_excel_file()` and `ErrorRecoveryHandler`
  classify and optionally recover from malformed cells instead of hard-failing.
- **Security hardening** — path validation, file-size limits, and ZIP-bomb defenses
  enforced before/while a file is opened; CSV export is sanitized against
  formula-injection.
- **Optional REST API** — `pystreamxl.server` (requires `pystreamxl[server]`) wraps the
  streaming engine behind HTTP endpoints. No authentication — see limitations.

## Who it's for / Use cases

- **ETL against large Excel exports** that don't fit comfortably in memory with
  `openpyxl` — `read()` keeps memory flat regardless of file size.
- **Extracting formulas and comments for audit or migration tooling**, not just cell
  values.
- **Appending to a growing log-style `.xlsx` file** without rewriting the whole workbook
  or losing other sheets.
- **Data engineering pipelines** that need a fast, dependency-light reader for `.xlsx`
  with an optional HTTP surface.

## What it is not

- **No SQL-style query language.** `execute_query()` in the REST API streams rows from a
  named sheet; it does not parse arbitrary queries.
- **No pandas/Parquet/Arrow export built in.** Convert `read()`'s output yourself.
- **No formula *evaluation*.** Formula text is extracted and classified, not recalculated.
- **The `pystreamxl dashboard` CLI renders sample data, not live telemetry.** Every mode
  prints an explicit "SAMPLE DATA — not live" warning.
- **The optional REST server has no authentication.** `PyStreamXLServer` /
  `create_flask_app()` have no login, API key, or token check — anyone who can reach the
  port can read and query every loaded source. Keep it on `localhost` or behind your own
  auth layer (reverse proxy, API gateway).
- **Prebuilt wheels are macOS arm64 only.** Every PyPI release has shipped exactly one
  platform wheel plus an sdist; Linux/Windows/x86_64-mac users build from source, which
  requires a Rust toolchain and [maturin](https://www.maturin.rs/).
- **Some listed release features are not reachable from Python.** ~1,180 lines of Rust
  (collaboration detection, incremental recalculation, cross-sheet dependency analysis)
  compile and pass their own tests but are not referenced by `python/src/lib.rs`; see
  [`ROADMAP_HONEST.md`](ROADMAP_HONEST.md).
- **Not all conditional-formatting detail is modeled.** `colorScale`/`dataBar`/`iconSet`
  rules are captured at the type/sqref/priority level only; their inline color-stop and
  threshold definitions are not represented.

## Project status

**Production/stable core, with disclosed gaps.** Current version **6.1.2**
(`Development Status :: 5 - Production/Stable`). The read/write/stream engine is covered
by the Rust and Python test suites and streams in flat memory (verified 2026-10-04 — see
[`ROADMAP_HONEST.md`](ROADMAP_HONEST.md) gap #10). The `Production/Stable` classifier is
broader than the test coverage of every optional surface; the honest technical-debt list
lives in `ROADMAP_HONEST.md`.

## Installation

```bash
pip install pystreamxl
```

A prebuilt wheel is currently published only for macOS (arm64). Other platforms install
from the source distribution, which requires a Rust toolchain (see `rust-toolchain.toml`)
and [maturin](https://www.maturin.rs/).

Requires Python 3.9+. The REST server extra:

```bash
pip install "pystreamxl[server]"
```

## Quick start

```python
import pystreamxl

for row in pystreamxl.read("data.xlsx"):
    print(row)  # ['Name', 'Age', 'Score']
```

## Usage

**Read as dictionaries, keyed by header row:**

```python
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
from pystreamxl import FormulaSerializer

rows = list(pystreamxl.read("model.xlsx", with_formulas=True))
# each cell is a dict: {"value": ..., "formula": ..., "formula_type": ...,
#                        "comment": ..., "comment_author": ...}
FormulaSerializer.export_to_json(rows, "formulas.json")
FormulaSerializer.export_to_csv(rows, "formulas.csv")  # sanitized against CSV/formula injection
```

**Export to CSV safely** — untrusted cell content is never written verbatim:

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

**CLI:**

```bash
pystreamxl dashboard          # sample extraction dashboard
pystreamxl dashboard --static # same sample data, clearly labeled "SAMPLE DATA — not live"
pystreamxl --version
```

## Security

- **Path & size validation** — `validate_read_path()` / `validate_write_path()` reject
  non-`.xlsx` paths, path traversal (when a `base_dir` is supplied), and oversized files
  before parsing.
- **ZIP-bomb defenses** — per-entry size limit, compression-ratio limit, and total
  decompressed-size limit enforced by the Rust core (`core/src/zip_reader.rs`).
- **CSV / formula-injection protection** — `pystreamxl.security.sanitize_csv_cell()`
  neutralizes string cells starting with `=`, `+`, `-`, `@`, TAB, or CR.
- **Known gap:** the optional REST server has no authentication.

Enforced limits (by default): max file size 512 MB, max size per ZIP entry 512 MB, max
total decompressed size 1 GB, max compression ratio 30:1. Handle malicious files with:

```python
from pystreamxl import SecurityError, read

try:
    for row in read("data.xlsx"):
        process(row)
except SecurityError as e:
    print(f"Security violation: {e}")
```

Found a security issue? See [SECURITY.md](SECURITY.md).

## Documentation

- [`docs/architecture/README.md`](docs/architecture/README.md) — how the Rust engine and Python API fit together, including known dead code
- [`docs/xlsx_format.md`](docs/xlsx_format.md) — XLSX/ZIP/XML format notes
- [`ROADMAP_HONEST.md`](ROADMAP_HONEST.md) — unvarnished list of what's missing, broken, or technical debt
- [`benchmarks/`](benchmarks/) — benchmark scripts and committed results comparing against `openpyxl`
- [`examples/`](examples/) — runnable examples, including `memory_benchmark.py`
- [`CHANGELOG.md`](CHANGELOG.md) — release history
- [`SECURITY.md`](SECURITY.md) — security model, limits, and what it does *not* protect against

Rows are yielded one at a time, and memory stays flat during iteration regardless of sheet
size (fixed 2026-10-04; see `ROADMAP_HONEST.md` gap #10). The `pyproject.toml` description
cites **3.8–5.6x faster than `openpyxl`** in this repo's committed benchmarks
(`benchmarks/results.md`). That is an openpyxl baseline: python-calamine is much
faster at whole-sheet loads (see `benchmarks/calamine_vs_pystreamxl.md`), so
choose PyStreamXL for bounded-memory streaming, not raw speed. Actual numbers
depend heavily on file structure, so measure on
your own workloads rather than trusting a generic table.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a
PR. See [CODE_OF_CONDUCT.md](docs/CODE_OF_CONDUCT.md) for community expectations.

```bash
git clone https://github.com/Mullassery/PyStreamXL.git
cd PyStreamXL
pip install -e ".[dev]"        # builds the Rust extension via maturin and installs test deps
pytest tests/ -v
cargo test --release --all-features
```

## Related projects

- [PyStreamXL](https://github.com/Mullassery/PyStreamXL) — stream large Excel workbooks with constant memory
- [PyStreamPDF](https://github.com/Mullassery/PyStreamPDF) — token-efficient PDF extraction for RAG
- [PyStreamMCP](https://github.com/Mullassery/PyStreamMCP) — context and token optimization for AI agents
- [PyStreamAI](https://github.com/Mullassery/PyStreamAI) — ML deployment toolkit (canary/A-B, cost tracking, ONNX)
- [PyTokenCalc](https://github.com/Mullassery/PyTokenCalc) — LLM token counting and cost estimation
- [Browse all projects](https://github.com/Mullassery?tab=repositories)

## License

This project is licensed under the [Apache License 2.0](LICENSE).
