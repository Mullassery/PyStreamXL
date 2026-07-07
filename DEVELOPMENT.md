# Development Guide

## Setup

### Prerequisites
- Python 3.9+
- Rust 1.70+ (if working on Rust components)
- Git

### Local Installation

```bash
# Clone repository
git clone https://github.com/Mullassery/StreamXL
cd StreamXL

# Install dependencies
pip install -e ".[dev]"

# For Rust: build with maturin (if applicable)
maturin develop
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run Rust tests
cargo test --all
```

## Code Quality

```bash
# Format code
black .
cargo fmt --all

# Lint
ruff check .
cargo clippy --all-targets -- -D warnings

# Type check
mypy . --ignore-missing-imports
```

## Git Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and write tests
3. Commit with clear message: `git commit -m "feat: add feature"`
4. Push and create PR
5. Ensure CI/CD passes (GitHub Actions)

## Commit Message Format

```
<type>: <short description>

<optional longer description>

Closes #123
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `ci`

## Before Submitting PR

- [ ] Tests pass locally (`pytest` or `cargo test`)
- [ ] Code formatted (`black .`, `cargo fmt`)
- [ ] Linting passes (`ruff`, `cargo clippy`)
- [ ] Type checking passes (`mypy`)
- [ ] No secrets committed
- [ ] Commit messages are clear
- [ ] PR description explains the change

## Debugging

### Logging
Look for debug output in:
```bash
# Python
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"

# Rust
RUST_LOG=debug cargo run
```

### Common Issues

**Tests fail locally**
- Ensure all dependencies installed: `pip install -e ".[dev]"`
- Check Python version: `python --version`
- Clear cache: `rm -rf .pytest_cache`

**Cargo build fails**
- Update Rust: `rustup update`
- Clean build: `cargo clean && cargo build`

## Documentation

- Update README.md for user-facing changes
- Update docstrings for API changes
- Update CHANGELOG.md for releases
- Link issues in commit messages

## Questions?

- Open a GitHub Discussion for questions
- Check PRODUCTION_AUDIT_REPORT.md for current status
- See existing issues/PRs for similar problems

---

**Happy contributing!**
