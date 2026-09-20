# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This file starts at the point it was introduced (2026-09). Earlier
releases (v1.0.0 through v5.3.0) predate it and are not reconstructed
here to avoid fabricating dates/details that weren't tracked at the
time — see `git log` and GitHub Releases for that history.

## [Unreleased]

### Fixed
- `Cargo.lock` was gitignored and not committed despite this repo
  shipping a compiled Python extension (PyO3/maturin) — it is now
  tracked for reproducible builds.
- Broken repository URLs (`Mullassery/StreamXL` instead of
  `Mullassery/PyStreamXL`) in `README.md`, `llms.txt`, and
  `scripts/install.sh`.
- `SECURITY.md` code examples imported from the nonexistent
  `pystreamxl` package instead of `streamxl`.
- `CONTRIBUTING.md` told contributors this project was MIT-licensed;
  it has been Apache-2.0 since the 2026-09-06 relicense.
- Stale `.cursorrules` claim that multi-sheet support wasn't
  implemented (it has been, via `core/src/sheet_manager.rs`, since
  before this fix).

### Removed
- `pystreaxl/` (`_mcp_tools.py`, `_mcp_connector.py`), `pystreaxl.toml`,
  and `streamxl/okf_sheet_metadata.py` — unused, unreferenced
  boilerplate contamination from an unrelated project template (fake
  "MCP" tool stubs returning hardcoded data, a connector referencing a
  nonexistent `statguardian` package and a `dab` CLI). Not imported by
  any real code or test.
- `docs/ROADMAP.md` and `docs/PRODUCT_VISION.md` — described a
  fictional "MCP 2.0 Platform" (19 projects, 228 tools, a
  `StatGuardian` dependency) with no basis in this codebase.
- `docs/CONTRIBUTING.md` — a stale, misnamed duplicate ("# CLAUDE.md —
  streamxl") of the real `CONTRIBUTING.md`, claiming multi-sheet
  support, dates, and `as_dict=True` were "not yet implemented" when
  all three have shipped for multiple major versions.

### Documentation
- Corrected `SECURITY.md`'s path-traversal claims: the `".." in
  str(path)` check in `python/streamxl/security.py` runs *after*
  `Path.resolve()` already collapsed any `..` segments, so it can never
  fire on a real traversal attempt. The library does not provide
  base-directory confinement; this is now stated plainly instead of
  implied to be a working protection.
- Archived (`docs/archive/*_STALE.md`) four docs describing the
  original single-sheet, read-only MVP, whose specific claims (e.g.
  "sheet1.xml only", multi-sheet "post-MVP") are no longer true:
  `architecture.md`, `design_decisions.md`, `api_spec.md`,
  `performance_model.md`, plus a v1.0-era `SECURITY_AUDIT.md`.
- Added `docs/architecture/README.md` with a current, accurate
  component diagram, including an explicit callout that
  `collaboration_detection.rs`, `incremental_recalculation.rs`, and
  `cross_sheet_analysis.rs` (1,180 lines) are dead code never wired
  into the Python bridge.
- Added `ROADMAP_HONEST.md`.
- Added `Cargo.lock` to `[tool.maturin]` reproducibility story (see
  Fixed above).

### Changed
- Added `ruff`/`black` to the `dev` optional-dependency group so
  `make lint`/`make fmt` work after `pip install -e ".[dev]"` without
  a separate `pre-commit` install.
