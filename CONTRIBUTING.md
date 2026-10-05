# Contributing to PyStreamXL

Thanks for your interest! PyStreamXL is a pure Rust + Python library for
streaming large `.xlsx` files in constant memory.

## Project layout

```
core/                  # Rust engine (sheet parsing, streaming, writing, zip handling)
├── src/
└── tests/

python/                # PyO3 bridge crate + the installable Python package
├── src/lib.rs          # PyO3 bindings (-> streamxl._core)
└── streamxl/           # Python package: api.py, core.py, security.py, server.py, cli.py, ...

tests/                 # Python integration tests (pytest)
benchmarks/            # Performance benchmarks vs. openpyxl
```

See `CLAUDE.md` for the build-system constraints (maturin vs. plain
`cargo build`) and a few non-obvious correctness gotchas in the Rust core.

## Dev setup

### Prerequisites
- Rust (version pinned in `rust-toolchain.toml`)
- Python 3.8+
- [maturin](https://www.maturin.rs/) (PyO3 build backend)

### Setup

```bash
git clone https://github.com/Mullassery/PyStreamXL.git
cd PyStreamXL
pip install -e ".[dev]"   # builds the Rust extension via maturin, installs test deps
pytest tests/ -v
```

## Before opening a PR

- `cargo fmt --all` and `cargo clippy --manifest-path core/Cargo.toml --all-targets -- -D warnings`
- `cargo test --manifest-path core/Cargo.toml` and `pytest tests/ -v` pass
- New functionality has tests (prefer Rust-side tests for pure parsing/streaming logic)
- Performance-sensitive changes: check `benchmarks/` shows no regression

## License

By contributing, you agree your contributions are licensed under the
[Apache License 2.0](./LICENSE).
