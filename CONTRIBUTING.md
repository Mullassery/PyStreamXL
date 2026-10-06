# Contributing to PyStreamXL

Thanks for your interest! PyStreamXL (`pip install pystreamxl`, `import pystreamxl`) is a Rust + Python library that streams large `.xlsx` files row-by-row without loading the whole workbook into memory.

## Project layout

```
core/                    # Rust engine (pystreamxl-core crate)
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
└── pystreamxl/             # Python package: api.py, core.py, security.py, server.py, cli.py, ...

tests/                    # Python test suite (pytest)
benchmarks/                # openpyxl-vs-pystreamxl comparison scripts
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
cargo clippy --manifest-path core/Cargo.toml --all-targets -- -D warnings  # enforced in CI
cargo fmt --check --manifest-path core/Cargo.toml                          # enforced in CI
black --check python/ tests/            # enforced in CI
ruff check python/ tests/               # enforced in CI
```

All four are run by the `lint` job in `.github/workflows/ci.yml` and by `pre-commit run --all-files` (see `.pre-commit-config.yaml`) — both pinned to the same tool versions so they can't silently diverge.

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

`cargo fmt --check`, `cargo clippy -- -D warnings`, `black --check`, and `ruff check` are all enforced in CI's `lint` job (see above) — a PR that fails any of them won't pass CI.

## Known gaps if you're looking for something to work on

See the "What's not here" section of `README.md` and `ROADMAP_HONEST.md` for the current, honest list of missing features and technical debt (dead Rust modules, single-platform wheel, etc.) — the lint/fmt CI gate mentioned there is now in place. Full tracked backlog: [Mullassery/RepoIssues](https://github.com/Mullassery/RepoIssues), filtered to the `repo:PyStreamXL` label, with [#52](https://github.com/Mullassery/RepoIssues/issues/52) as the master index.

**Maintainer-only action items** (need repo/PyPI-project settings access this audit process doesn't have):

- **PyPI Trusted Publisher (OIDC) is not configured** for this project ([RepoIssues #46](https://github.com/Mullassery/RepoIssues/issues/46)). `.github/workflows/release.yml` is structurally correct (builds wheels for Linux/macOS/Windows, verified with `actionlint`) but its `publish` job will fail on the first real tag push until OIDC trust is set up at https://pypi.org/manage/project/pystreamxl/settings/publishing/ for this repo. The workflow has never been fired end-to-end with a real tag.
- **1,180 lines of dead Rust code** (`collaboration_detection.rs`, `incremental_recalculation.rs`, `cross_sheet_analysis.rs` — the v4.0.0/v5.0.0 "headline features" that were never wired into the Python API) need a finish-or-delete decision ([RepoIssues #48](https://github.com/Mullassery/RepoIssues/issues/48)).
- **The "5 - Production/Stable" PyPI classifier** may be more confident than the current state (no server auth, some dependency bumps blocked, etc.) warrants — a maintainer call, not a bug ([RepoIssues #51](https://github.com/Mullassery/RepoIssues/issues/51)).

## License

By contributing, you agree your contributions are licensed under the [Apache License 2.0](./LICENSE).
