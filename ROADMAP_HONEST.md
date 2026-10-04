# Honest Roadmap / Technical Debt

This is a blunt list of what's missing, broken, or unfinished, as of a
2026-09 audit against v5.3.0. No hedging: if something doesn't work or
doesn't exist, it says so. Cross-reference the README's "Honest feature
list" for what *does* work.

Validated by actually running: `cargo test --release --all-features`
(61 tests, all pass), `pytest tests/ -v` (160 tests, all pass),
`cargo clippy --release --all-features`, `cargo fmt --check`.

Updated 2026-09-22 after a quick-fix pass (items #1 and #2 below fixed,
adding 8 tests in `tests/test_security.py`; 61 Rust / 168 Python tests
pass; clippy/fmt findings unchanged since #4-#9 below were explicitly out
of scope for that pass).

## Bugs / security gaps

1. ~~**Path-traversal check is dead code.**~~ **FIXED (2026-09-22).**
   `python/pystreamxl/security.py` — the old `if '..' in str(path)` check
   ran after `Path.resolve()` had already collapsed `..` segments and
   could never fire. `validate_xlsx_path()`/`validate_read_path()`/
   `validate_write_path()` now accept an optional `base_dir`; when passed,
   the resolved path is checked against it with `os.path.commonpath()`
   after resolution, so it actually catches traversal. Opt-in (default
   `base_dir=None` preserves the library's existing arbitrary-path
   behavior — forcing confinement on every call would break legitimate
   uses like `api.py`/`server.py` that read absolute paths anywhere on
   disk). See `tests/test_security.py` and `SECURITY.md` "Path Handling".

2. ~~**`validate_write_path()` uses `print()` for overwrite warnings**~~
   **FIXED (2026-09-22).** `python/pystreamxl/security.py` now logs via
   `logging.getLogger(__name__).warning(...)` instead of `print()`.

3. **No dependency-audit CI job.** Neither `cargo audit`/`cargo deny`
   nor `pip-audit` run in CI. `.github/workflows/ci.yml` only builds and
   tests. This sandbox has no network access to actually run either
   tool and confirm current findings — that's an environment
   limitation, not evidence either way about the dependency tree's
   health.

## Dead code / abandoned features

4. **`core/src/collaboration_detection.rs` (470 lines),
   `core/src/incremental_recalculation.rs` (412 lines), and
   `core/src/cross_sheet_analysis.rs` (298 lines) — 1,180 lines total —
   are unreachable from Python.** All three are `pub mod`/`pub use` in
   `core/src/lib.rs`, each has its own passing unit-test suite, and per
   git history they were the headline features of the v4.0.0
   ("Real-time Collaboration Detection") and v5.0.0 ("Cross-Sheet
   Dependency Analysis") releases — but **none of the three symbols is
   referenced anywhere in `python/src/lib.rs`**. They compile, they
   pass their own tests, and they do nothing for any actual caller of
   the `pystreamxl` package. This needs a real decision: finish wiring
   them into the Python API and the README's feature list, or delete
   them. Left as-is, they're maintenance burden (compile time, contributor
   confusion, a stale mental model of "what phase 4/5 shipped") with zero
   product value.

## Missing platform coverage

5. **No Linux or Windows wheels have ever been published to PyPI.**
   Every release 1.2.0 through 5.3.0 shipped exactly one platform wheel
   (macOS arm64) plus an sdist. Anyone on Linux/Windows/x86_64-mac
   builds from source, which requires a Rust toolchain — this is a real
   adoption barrier for a "high-performance" pitch, not a footnote.
   (Already disclosed in README; repeated here because it's the single
   biggest practical limitation for most potential users.)

## CI / lint / format gaps

6. **`cargo fmt --check` currently fails** with 54 diffs across 8 files
   (`collaboration_detection.rs`, `conditional_formatting.rs`,
   `cross_sheet_analysis.rs`, `dxf.rs`, `formula_parser.rs`,
   `incremental_recalculation.rs`, `lib.rs`,
   `core/tests/writer_streaming.rs`). Not gated in CI or pre-commit in
   any way that's actually run.

7. **`cargo clippy --release --all-features` currently emits 18
   warnings** (mostly `new_without_default`, `or_insert_with(Vec::new)`
   instead of `.or_default()`, an unnecessary `sort_by` instead of
   `sort_by_key`, one unused import, one unused `mut`, two dead struct
   fields in `collaboration_detection.rs`). None are correctness bugs;
   all are in the codebase described in finding #4 above except for one
   in `incremental_recalculation.rs`. Not gated in CI.

8. **`.pre-commit-config.yaml` references `rust-lang/rust-clippy` and
   `rust-lang/rustfmt` as pre-commit hook repos.** These are the
   upstream tool source repos, not the commonly-used community
   pre-commit-hook mirrors (e.g. `doublify/pre-commit-rust`) — whether
   they actually expose a working `.pre-commit-hooks.yaml` for external
   consumption is unverified in this sandbox (no network access to
   pre-commit.com/GitHub to test `pre-commit run --all-files`). Flagging
   as unverified rather than confirmed-broken; worth an actual
   `pre-commit install && pre-commit run --all-files` check with
   network access before trusting this file.

9. **CI (`ci.yml`) doesn't run `cargo fmt --check`, `cargo clippy`, or
   any Python linter** (ruff/black are configured in
   `.pre-commit-config.yaml` and now declared as dev deps, but nothing
   enforces them). It only builds and runs tests. Given findings #6/#7
   already show real drift, adding these gates now would immediately
   fail CI — enabling them requires either fixing the drift first or
   allowing failures temporarily, which is a real decision, not a
   drive-by fix.

10. ~~**`read()`/`stream()` are NOT O(1) memory — the README's "Honest
    feature list" claim is false.**~~ **FIXED (2026-10-04).** Root cause
    was exactly as diagnosed above: `XlsxStream::open()` decompressed the
    *entire* sheet XML into a `Vec<u8>` via `zip.read_entry()` before any
    row was yielded, and `SheetParser` held a `quick_xml::Reader` borrowed
    over that whole buffer. Fixed by making `SheetParser` generic over any
    `BufRead` source (`core/src/sheet_parser.rs`) and streaming the zip
    entry's body directly via `quick_xml::Reader<BufReader<ZipFile<'_>>>`
    instead of buffering it first (`core/src/stream.rs`'s
    `open_streaming_parser`). `ZipFile<'_>` borrows `&mut ZipArchive`, so
    pairing an owned archive with a borrowed decompressing reader over it
    needs a self-referential struct — built safely via the `self_cell`
    crate (`MutBorrow` helper, for the one-time `&mut` needed to open the
    entry), with no unsafe code added to this crate. `RowIter`/
    `RowIterMetadata` now own their `ZipArchive` + reader outright rather
    than borrowing from `XlsxStream`, which also let `python/src/lib.rs`
    drop its own, now-unnecessary, self_cell wrapping around them.
    Conditional-formatting extraction (`<conditionalFormatting>`/`<cfRule>`
    blocks are siblings of `<sheetData>`, not children, so there's no way
    to stream just that part) still does one transient, one-time full-buffer
    read at `open()` time, immediately freed afterward — not held for the
    life of `XlsxStream` or during row iteration, which is what the
    benchmark actually measured.
    **Re-verified empirically** (2026-10-04, real `.xlsx` files up to 1.2M
    rows / 33MB, via `psutil`-sampled live RSS at 50k-row checkpoints
    during a single streaming run — not `tracemalloc`, which can't see
    Rust-heap allocations outside Python's own allocator): memory plateaus
    within the first 50k rows and then stays flat (309.03MB → 309.05MB,
    effectively measurement noise) across the remaining 1,150,000 rows.
    All 61 Rust + 168 Python tests still pass. The remaining per-*file*
    (not per-row) baseline scales with the one-time conditional-formatting
    pre-read above, not with rows processed — that's a known, intentional,
    documented tradeoff, not a regression of this fix.

## Feature gaps (already honestly disclosed in README, listed here for completeness)

- No SQL-style query language (`execute_query()` in the REST API streams
  a named sheet; it doesn't parse arbitrary queries).
- No pandas/Parquet/Arrow export built in.
- No formula *evaluation* — extraction/classification only.
- `colorScale`/`dataBar`/`iconSet` conditional-formatting rules are
  captured at the type/sqref/priority level only; their inline
  color-stop/threshold definitions aren't modeled.

## Debatable, not changed in this pass

- `pyproject.toml` classifies this as `Development Status :: 5 -
  Production/Stable`. Given a single supported platform wheel (#5),
  1,180 lines of shipped-but-unreachable "phase" features (#4), and no
  CI lint/fmt gate (#9), that classifier is generous. The core
  read/write engine itself is solidly tested (61 Rust + 160 Python
  tests, all passing) and the README is honest about limitations, so
  this isn't fabricated — but "Production/Stable" is a packaging-wide
  claim, not just a claim about the tested core. Left unchanged because
  downgrading a release classifier is a maintainer call about release
  posture, not a documentation fix; flagged here so it's a conscious
  decision rather than an oversight.
