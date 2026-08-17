# StreamXL

**Stream large `.xlsx` files row-by-row in constant memory, powered by a Rust core with no `unsafe` code.**

`pip install`s as `streamxl`, `import streamxl`. Read multi-sheet Excel workbooks without loading them fully into memory, extract formulas and comments, write new `.xlsx` files, and append to existing ones — all through a small, plain Python API backed by a Rust engine.

[![PyPI](https://img.shields.io/pypi/v/streamxl)](https://pypi.org/project/streamxl/)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-blue.svg)](./LICENSE)

---

## Install

```bash
pip install streamxl
```

Prebuilt wheels are published for common platforms. If you're building from source you'll need a Rust toolchain (see `rust-toolchain.toml`) and [maturin](https://www.maturin.rs/).

## Quick start

```python
import streamxl

for row in streamxl.read("data.xlsx"):
    print(row)  # ['Name', 'Age', 'Score']
```

`read()` streams rows one at a time — memory use stays flat regardless of file size.

## Real, working examples

**Read as dictionaries, keyed by header row:**

```python
import streamxl

for row in streamxl.read("sales.xlsx", as_dict=True):
    print(row["Customer"], row["Amount"])
```

**Read only specific columns:**

```python
for row in streamxl.read("sales.xlsx", as_dict=True, columns=["Customer", "Amount"]):
    ...
```

**Read every sheet in a workbook:**

```python
sheet_names = streamxl.sheets("workbook.xlsx")
all_data = streamxl.read_all("workbook.xlsx")  # {sheet_name: [rows...]}
```

**Write a new `.xlsx` file:**

```python
import datetime
import streamxl

streamxl.write("report.xlsx", [
    ["Name", "Joined", "Score"],
    ["Alice", datetime.date(2024, 1, 15), 95.5],
    ["Bob", datetime.date(2024, 3, 2), 88.0],
])
```

**Stream-write multiple sheets without holding the whole file in memory:**

```python
with streamxl.writer("report.xlsx") as w:
    w.write_row(["Name", "Age"])
    w.write_row(["Alice", 30])
    w.add_sheet("Summary")
    w.write_row(["Total", 1])
```

**Append rows to an existing file (other sheets are preserved):**

```python
streamxl.write("log.xlsx", [["Date", "Event"]])
streamxl.append("log.xlsx", [[datetime.date.today(), "started"]])
streamxl.append("log.xlsx", [[datetime.date.today(), "finished"]])
```

**Extract formulas and comments:**

```python
rows = list(streamxl.read("model.xlsx", with_formulas=True))
# each cell is a dict: {"value": ..., "formula": ..., "formula_type": ...,
#                        "comment": ..., "comment_author": ...}

from streamxl import FormulaSerializer
export = FormulaSerializer.export_formulas(rows)
FormulaSerializer.export_to_json(rows, "formulas.json")
FormulaSerializer.export_to_csv(rows, "formulas.csv")  # sanitized against CSV/formula injection
```

**Export to CSV safely** — untrusted cell content is never written to CSV verbatim (see [Security](#security) below):

```python
import csv
import streamxl
from streamxl.security import sanitize_csv_cell

with open("output.csv", "w", newline="") as f:
    writer = csv.writer(f)
    for row in streamxl.read("large.xlsx"):
        writer.writerow([sanitize_csv_cell(cell) for cell in row])
```

**Validate a file and recover from bad cells instead of crashing:**

```python
from streamxl import validate_excel_file

report = validate_excel_file("questionable.xlsx")
if report.has_fatal_errors():
    print(report.format_summary())
```

More runnable examples live in [`examples/`](examples/).

## Honest feature list

What's here and real, backed by the Rust core and covered by the test suite:

- **Streaming reads** — `read()` / `stream()`: O(1) memory per row, regardless of file size.
- **Multi-sheet support** — `sheets()`, `read_all()`, and `writer().add_sheet()`.
- **Streaming writes** — `write()`, `writer()`, `append()`, all producing real `.xlsx` files.
- **Formula extraction** — read formula text and a best-effort formula-type classification (`with_formulas=True`), plus `FormulaReferenceMapper` for shifting/rewriting cell references and `FormulaSerializer` for exporting/importing formulas as JSON or CSV.
- **Comment extraction** — cell comments and authors, via `with_formulas=True`.
- **Type-aware cells** — strings, numbers, booleans, dates, datetimes, and empty cells round-trip correctly.
- **Error recovery & validation** — `validate_excel_file()` and `ErrorRecoveryHandler` classify and (optionally) recover from malformed cells instead of hard-failing on the whole file.
- **Security hardening** — path validation, file-size limits, and ZIP-bomb defenses (entry-size, compression-ratio, and total-decompressed-size limits) enforced before/while a file is opened. CSV export is sanitized against formula-injection (see below).
- **REST API (optional)** — `streamxl.server.StreamXLServer` / `create_flask_app()` wrap the real streaming engine behind HTTP endpoints (`/sources`, `/sources/<id>/query`, `/sources/<id>/export`, ...). Requires `pip install "streamxl[server]"`.

What's **not** here, so you don't have to find out the hard way:

- No SQL-style query language — `execute_query()` in the REST API streams rows from a named sheet, it does not parse arbitrary queries.
- No pandas/Parquet/Arrow export built in. Convert `read()`'s output yourself, or open an issue if this matters to you.
- No formula *evaluation* — formula text is extracted and classified, not recalculated.
- The `pystreamxl dashboard` CLI command currently renders sample data, not live telemetry — it's clearly labeled as such in its own output.

## Security

- **Path & size validation** — `validate_read_path()` / `validate_write_path()` reject non-`.xlsx` paths, path traversal, and oversized files before any parsing happens.
- **ZIP-bomb defenses** — the Rust core enforces a per-entry size limit, a compression-ratio limit, and a total-decompressed-size limit while unpacking a workbook (see `core/src/zip_reader.rs`), tested against real crafted archives in `core/tests/zip_bomb_defense.rs`.
- **CSV/formula-injection protection** — `streamxl.security.sanitize_csv_cell()` neutralizes any string cell that starts with `=`, `+`, `-`, `@`, TAB, or CR (the standard CSV-injection trigger set) by prefixing it with `'`, so a malicious workbook can't turn a CSV export into an executable formula when reopened in Excel/LibreOffice/Google Sheets. `FormulaSerializer.export_to_csv()` applies this automatically; apply it yourself when writing CSV from `read()` output (see the example above).

Found a security issue? See [SECURITY.md](SECURITY.md).

## Performance

Streaming keeps memory flat regardless of file size, since rows are parsed and yielded one at a time instead of materializing the whole workbook. See [`benchmarks/`](benchmarks/) for the scripts used to compare against `openpyxl`, and [`examples/memory_benchmark.py`](examples/memory_benchmark.py) to measure it yourself against your own files:

```bash
python examples/memory_benchmark.py your_file.xlsx
```

Actual numbers depend heavily on your file's structure (shared strings, formulas, formatting) — measure on your own workloads rather than trusting a generic table.

## CLI

```bash
pystreamxl dashboard          # sample extraction dashboard (see note above)
pystreamxl --version
```

## Development

```bash
git clone https://github.com/Mullassery/StreamXL.git
cd StreamXL
pip install -e ".[dev]"       # builds the Rust extension via maturin and installs test deps
pytest tests/ -v
cargo test --all-features     # Rust unit + integration tests
```

## License

Proprietary License — free to use with explicit attribution. See [LICENSE](LICENSE).

---

**StreamXL** | Constant-memory Excel streaming | Rust core, Python API
