# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This file starts at the point it was introduced (2026-09). Earlier
releases (v1.0.0 through v5.3.0) predate it and are not reconstructed
here to avoid fabricating dates/details that weren't tracked at the
time — see `git log` and GitHub Releases for that history.

## [6.1.0] - 2026-10-05

### Changed
- **`pystreamxl.server.StreamXLServer` renamed to `PyStreamXLServer`** to
  match the project's own naming convention — it was the one class still
  missing the `Py` prefix that the rest of the codebase (`PyStreamXLDashboard`,
  the `pystreamxl` package itself) already used post-6.0.0. The old name
  remains available as a subclass that emits a `DeprecationWarning` and
  delegates to the new one.

### Fixed
- **Real O(1) memory for `read()`/`stream()`** (ROADMAP_HONEST.md gap #10).
  `XlsxStream::open()` previously decompressed the entire sheet XML into a
  `Vec<u8>` before any row was yielded, so peak RSS scaled with sheet size
  despite the Python-facing API already being a real row-by-row iterator.
  `SheetParser` is now generic over any `BufRead` source and streams the
  zip entry's body incrementally instead of buffering it first; the
  self-referential owned-archive-plus-borrowed-reader this needs is built
  safely via the `self_cell` crate, with no unsafe code added. Verified via
  live RSS sampling across a 1.2M-row file: memory plateaus in the first
  50k rows and stays flat for the remaining 1.15M. All 61 Rust + 168 Python
  tests still pass.

## [6.0.0] - 2026-09-27

### Changed
- **Breaking: PyPI project and import name changed from `streamxl` to
  `pystreamxl`**, to match the CLI command, class names
  (`PyStreamXLDashboard`, `StreamXLServer`), and repo name
  (`Mullassery/PyStreamXL`), which already used the `PyStreamXL`/
  `pystreamxl` spelling — `streamxl` was the odd one out and a real
  source of confusion (reviewers flagged the two names being used
  interchangeably without realizing they referred to the same
  project). `pip install pystreamxl`, `import pystreamxl` going
  forward. The old `streamxl` PyPI project gets one final release
  (see below) that re-exports from `pystreamxl` with a deprecation
  warning rather than being silently abandoned at 5.3.2.

## [5.3.2] - 2026-09-27

### Added
- `.github/workflows/release.yml`: builds wheels for Linux (x86_64,
  aarch64), macOS (x86_64, aarch64), and Windows on Python 3.10-3.12 via
  `PyO3/maturin-action`, plus an sdist, on a version-tag push. Every
  release to date (1.2.0 through 5.3.1) was built by hand with local
  `maturin build`, which produced exactly one wheel per release —
  always `macosx_11_0_arm64`, with the interpreter tag drifting between
  releases based on whichever Python happened to be active locally
  (`cp313` for 1.2.0-5.0.0, `cp39` for 5.1.0, `cp311` for 5.2.0-5.3.0,
  `cp39` again for 5.3.1) — so no Linux/Windows install has ever
  resolved a prebuilt wheel, and even macOS installs on an interpreter
  other than that release's one supported version had to build the
  sdist from source. The workflow's `publish` job (PyPI Trusted
  Publishing) hasn't been exercised end-to-end; it needs a Trusted
  Publisher added on the `streamxl` PyPI project before it will work.

### Fixed
- `pystreamxl --version` (`python/streamxl/cli.py`) was hardcoded to
  `PyStreamXL 5.2.0`, one release behind the actual package version. It
  now reads `streamxl.__version__`.
- The bare `pystreamxl dashboard` (interactive mode) rendered a
  different, unlabeled `Status: Active` placeholder instead of the
  `SAMPLE DATA — not live` metrics shown by `--static`/`--alerts`/
  `--recommendations`/`--export` — despite there being no actual live
  update loop behind "interactive" mode to justify the different
  output. All modes now render the same labeled sample data.

### Removed
- `python/streamxl/scripts/post_install.py`: dead code (nothing
  imported or invoked it — no build hook, no console script) that
  printed fabricated install-time stats (`45,234 formulas extracted`,
  `46x faster than openpyxl` — contradicting the `3.8-5.6x` figure in
  this repo's own benchmarks) and a stale `v1.2.0` banner, as if they
  were real output from the user's own install.

## [5.3.1] - 2026-09-22

### Security
- Fixed dead path-traversal check in `python/streamxl/security.py`. The
  `".." in str(path)` check ran *after* `Path.resolve()` had already
  collapsed any `..` segments, so it could structurally never fire on a
  real traversal attempt. `validate_xlsx_path()`, `validate_read_path()`,
  and `validate_write_path()` now accept an optional `base_dir` argument;
  when passed, the resolved path is verified to actually be inside
  `base_dir` via `os.path.commonpath()`, performed after resolution rather
  than before it. This is opt-in (omitting `base_dir` preserves prior
  behavior — no confinement, matching the library's existing arbitrary-path
  use case) since a general-purpose file API and a service with a real
  trust boundary have different confinement contracts. See
  `tests/test_security.py` for tests exercising real traversal attempts
  and legitimate in-bounds paths.

### Fixed
- `validate_write_path()` (`python/streamxl/security.py:87`) used `print()`
  for overwrite warnings instead of the `logging` module. Now uses
  `logging.getLogger(__name__).warning(...)`, consistent with
  `_formula_support.py`/`integrity.py`/`error_recovery.py`.
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
