.PHONY: install install-dev build test lint fmt clean help setup-hooks

help:
	@echo "streamxl development tasks:"
	@echo "  make install         Install pre-commit hooks"
	@echo "  make build           Build Python wheel (maturin)"
	@echo "  make dev             Dev install with hot reload"
	@echo "  make test            Run all tests"
	@echo "  make test-core       Run Rust core tests only"
	@echo "  make lint            Run clippy + ruff linters"
	@echo "  make fmt             Format code"
	@echo "  make fmt-check       Check format without changing"
	@echo "  make clean           Remove build artifacts"

install: setup-hooks
	@echo "✓ Development environment ready"

setup-hooks:
	@command -v pre-commit >/dev/null 2>&1 || pip install pre-commit
	pre-commit install

dev:
	maturin develop

build:
	maturin build --release

test:
	maturin develop
	pytest tests/ -v

test-core:
	cargo test --manifest-path core/Cargo.toml --release

lint:
	cargo clippy --manifest-path core/Cargo.toml --all-targets
	ruff check .

fmt:
	cargo fmt --manifest-path core/Cargo.toml
	black .
	ruff check . --fix

fmt-check:
	cargo fmt --manifest-path core/Cargo.toml -- --check
	black --check .

clean:
	cargo clean
	rm -rf target build dist *.egg-info .pytest_cache
