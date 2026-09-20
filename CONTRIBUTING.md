# Contributing to PyStreamXL

Thanks for your interest! PyStreamXL (`pip install streamxl`, `import streamxl`) is a Rust + Python library that streams large `.xlsx` files row-by-row without loading the whole workbook into memory.

## Project layout

```
core/                    # Rust engine (streamxl-core crate)
├── src/
│   ├── stream.rs         # XlsxStream: opens the ZIP, orchestrates parsing
│   ├── zip_reader.rs     # ZIP-bomb defenses (entry/ratio/total-size limits)
│   ├── sheet_parser.rs   # Row-by-row worksheet XML parsing
│   ├── sheet_manager.rs  # Multi-sheet name -> path resolution (xl/workbook.xml)
│   ├── shared_strings.rs # SST parser
│   ├── writer.rs         # XlsxWriter: bounded-buffer streaming writes
│   ├── comments.rs, conditional_formatting.rs, dxf.rs, styles.rs, dates.rs
│   ├── formula_parser.rs # Formula text extraction/classification
│   └── error_handling.rs
└── tests/                # Rust integration tests (zip-bomb defense, streaming writer, etc.)

python/
├── src/lib.rs            # PyO3 bridge exposing the Rust engine to Python
└── streamxl/             # Python package: api.py, core.py, security.py, server.py, cli.py, ...

tests/                    # Python test suite (pytest)
benchmarks/                # openpyxl-vs-streamxl comparison scripts
examples/                  # runnable usage examples
docs/                       # architecture, feature, and format docs
```

Note: `core/src/lib.rs` also declares `collaboration_detection.rs`, `incremental_recalculation.rs`, and `cross_sheet_analysis.rs`. These are **not** wired into `python/src/lib.rs` or exposed to Python at all — they are dead code left over from abandoned feature work (see `ROADMAP_HONEST.md`). Don't build on top of them without first deciding whether to finish wiring them up or delete them.

## Dev setup

### Prerequisites

- Rust (see `rust-toolchain.toml` for the pinned version)
- Python 3.8+
- [maturin](https://www.maturin.rs/) (installed automatically as a build dependency)

### Build and test

```bash
pip install -e ".[dev]"      # builds the Rust extension via maturin, installs test deps
pytest tests/ -v              # Python test suite

cargo test --release --all-features    # Rust unit + integration tests (core + python crates)
cargo clippy --release --all-features  # currently has pre-existing warnings, not yet gated in CI
cargo fmt --check                       # currently has pre-existing diffs, not yet gated in CI
```

On macOS, building the Rust workspace directly with `cargo` (rather than through `maturin`/`pip install`) may require:

```bash
export RUSTFLAGS="-C link-args=-undefined -C link-args=dynamic_lookup"
```

`maturin develop` also works for an editable install if you're iterating on the Rust side only.

## Before opening a PR

- `cargo test --release --all-features` and `pytest tests/ -v` both pass
- New functionality has tests — prefer Rust-side tests for pure parsing/writing logic, Python-side tests for the public API surface
- If you touch `README.md`'s "Honest feature list" or "What's not here" sections, make sure they still describe reality, not aspiration
- Update `CHANGELOG.md` under `[Unreleased]`

`cargo fmt --check` and `cargo clippy` are not currently enforced in CI (see `ROADMAP_HONEST.md`), so passing them isn't a hard requirement yet, but please don't add new warnings in files you touch.

## Known gaps if you're looking for something to work on

See the "What's not here" section of `README.md` and `ROADMAP_HONEST.md` for the current, honest list of missing features and technical debt (dead Rust modules, single-platform wheel, no CI lint/fmt gate, etc.).

## License

By contributing, you agree your contributions are licensed under the [Apache License 2.0](./LICENSE).
