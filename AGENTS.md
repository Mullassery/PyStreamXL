# Agent Instructions — streamxl

This file tells AI coding agents (Copilot, Cursor, Gemini, etc.) everything they need to understand, build, test, and extend this repository correctly.

---

## What this repo is

**streamxl** is a Python library that reads `.xlsx` files row-by-row using a high-performance engine. It is designed to process large Excel files in ETL and data pipelines without loading the full file into memory.

- Language split: Rust (engine) + Python (API layer)
- Build tool: [maturin](https://github.com/PyO3/maturin)
- Rust crates: `zip`, `quick-xml`

---

## Repository layout

```
streamxl/
├── core/                        # Rust library crate — the parsing engine
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs               # re-exports XlsxStream
│       ├── zip_reader.rs        # wraps the zip crate; reads ZIP entries into Vec<u8>
│       ├── shared_strings.rs    # parses xl/sharedStrings.xml → Vec<String>
│       ├── sheet_parser.rs      # event-driven XML parser; yields Vec<CellValue> per row
│       └── stream.rs            # XlsxStream: opens file, holds SST + sheet bytes, owns RowIter
│
├── python/                      # PyO3 extension crate — bridges Rust → Python
│   ├── Cargo.toml               # standalone [workspace]; built by maturin, not cargo
│   ├── src/
│   │   └── lib.rs               # #[pyfunction] read(), #[pymodule] _core
│   └── streamxl/                # Python package (installed alongside the .so)
│       ├── __init__.py          # exports read, stream, __version__
│       ├── api.py               # streamxl.read() and streamxl.stream() iterators
│       └── core.py              # read_rows() — thin wrapper over _core.read()
│
├── benchmarks/
│   ├── openpyxl_vs_streamxl.py  # timing + peak-memory comparison script
│   └── results.md               # captured benchmark numbers
│
├── tests/
│   ├── test_basic.py            # row count, type checks
│   ├── test_shared_strings.py   # SST parsing unit tests
│   └── test_streaming.py        # iterator protocol, memory invariant
│
├── docs/
│   ├── architecture.md          # two-layer design, data flow diagram
│   ├── design_decisions.md      # why quick-xml, why maturin, SST eager load
│   ├── xlsx_format.md           # OOXML ZIP structure, cell types, sharedStrings
│   ├── performance_model.md     # memory and time complexity analysis
│   └── api_spec.md              # public Python API contract
│
├── examples/
│   ├── basic_read.py
│   ├── streaming_etl.py
│   └── memory_benchmark.py
│
├── scripts/
│   ├── install.sh               # curl-installable one-liner script
│   ├── build.sh                 # maturin develop --release
│   └── benchmark.sh             # runs openpyxl_vs_streamxl.py
│
├── pyproject.toml               # maturin build config; python-source = "python"
├── Cargo.toml                   # workspace root (members: ["core"] only)
├── rust-toolchain.toml          # pins stable Rust channel
└── .github/workflows/           # CI: rust-build.yml, test-python.yml, ci.yml
```

---

## How to build

### Prerequisites

```bash
# Rust (stable)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# maturin + pytest
pip install maturin pytest
```

### Development build (editable install)

```bash
maturin develop
```

### Release build (optimised wheel)

```bash
maturin build --release
# wheel written to target/wheels/
pip install target/wheels/streamxl-*.whl
```

### Rust core only (no Python)

```bash
cargo build --manifest-path core/Cargo.toml
cargo test  --manifest-path core/Cargo.toml
```

> **Do not run `cargo build --workspace`** — the `python/` crate has its own `[workspace]` and requires Python headers; it is only buildable via maturin.

---

## How to test

```bash
# Build first
maturin develop

# Run all Python tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_basic.py -v
```

---

## Critical files to understand before editing

| File | Why it matters |
|------|----------------|
| `core/src/sheet_parser.rs` | All cell type logic lives here. Handles `inlineStr`, `sharedString`, `bool`, `number`, `empty`. Wrong changes here break all string output. |
| `core/src/shared_strings.rs` | Parses the SST. If this breaks, all `t="s"` cells return `None`. |
| `core/src/stream.rs` | Owns the `sheet_xml: Vec<u8>` buffer and the `RowIter`. The sheet XML is decompressed once and held in memory; the parser borrows from it. |
| `python/src/lib.rs` | PyO3 bridge. Uses `read_event()` not `read_event_into()` — do not change this without understanding the borrowing difference. |
| `pyproject.toml` | `manifest-path = "python/Cargo.toml"` tells maturin which crate to build. |
| `python/Cargo.toml` | Has `[workspace]` at the top — this makes it a standalone workspace so maturin doesn't conflict with the root workspace. |

---

## Known constraints and gotchas

- **`inlineStr` vs `sharedString`**: openpyxl writes strings as `t="inlineStr"` (text in `<is><t>`), not `t="s"` (SST index). Both are handled in `sheet_parser.rs`. Do not remove either branch.
- **`read_event()` vs `read_event_into()`**: The sheet parser uses `read_event()` on `Reader<&[u8]>`. Switching to `read_event_into(&mut buf)` silently breaks string resolution — do not change this.
- **Workspace split**: `core/` is in the root workspace. `python/` is its own standalone workspace (has `[workspace]` in its `Cargo.toml`). maturin builds `python/` directly. `cargo build --workspace` will fail for `python/` because it needs Python headers.
- **sheet1.xml only**: Multi-sheet support is not yet implemented. `stream.rs` always reads `xl/worksheets/sheet1.xml`.
- **`sheet_xml: Vec<u8>`**: The decompressed sheet XML is held in memory. For very large files this can be significant. This is a known limitation — fixing it requires unsafe lifetime extension or a different architecture.

---

## Cell value types

| XLSX cell `t` attribute | Rust `CellValue` variant | Python type |
|------------------------|--------------------------|-------------|
| `s` (shared string) | `CellValue::String` | `str` |
| `inlineStr` | `CellValue::String` | `str` |
| `b` (boolean) | `CellValue::Bool` | `bool` |
| `n` or absent (number) | `CellValue::Number` | `float` |
| empty / absent value | `CellValue::Empty` | `None` |

---

## Public Python API

```python
import streamxl

# Primary interface — returns an iterator of lists
for row in streamxl.read("file.xlsx"):
    ...  # row is List[str | float | bool | None]

# Alias
for row in streamxl.stream("file.xlsx"):
    ...
```

No keyword arguments are implemented yet. `sheet=` parameter is on the roadmap.

---

## Roadmap (what is NOT yet implemented)

- Multi-sheet support (`sheet="SheetName"` parameter)
- Date/datetime cell type (`t="n"` with a date format style)
- `as_dict=True` — yield dicts keyed by header row
- PyPI wheel publishing (manylinux + macOS + Windows cross-compilation)
