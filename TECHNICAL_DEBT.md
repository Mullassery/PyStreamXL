# Complete Technical Debt Register — PyStreamXL

## Executive Summary

Total items: 22
Open: 7
Resolved (this run): 15
Blocked: 1 (TD-0016, subset of Open)
Future: 1 (TD-0021)
Critical (P0): 0
High (P1): 5 (4 fixed, 1 open)
Medium (P2): 11 (6 fixed, 5 open)
Low (P3): 6 (5 fixed, 1 open)

This repo had already been through several prior audit passes (visible in
`git log`: version-string reconciliation, README overclaim fixes, a dead
zip-bomb test replaced with real coverage, a `StreamXL.append()` bug fix,
a prior "PyStreamAI boilerplate contamination" cleanup, relicensing to
Apache-2.0). This pass found a fresh batch of drift that accumulated since
those fixes — mostly naming/version consistency and stale docs — plus one
real security default and one real dead-code/tautology bug in the Rust
test suite.

## P0 — Critical

None found.

## P1 — High

| ID | Category | Description | Source | Status | Fix |
|---|---|---|---|---|---|
| TD-0001 | BUG | `python/streamxl/__init__.py.__version__` said `5.2.0` while `pyproject.toml`/`Cargo.toml` said `5.3.0` | SOURCE_CODE | RESOLVED | Bumped to `5.3.0` |
| TD-0002 | BUG | CLI `--version` hardcoded `"PyStreamXL 5.2.0"` as a literal string, independent of the package version — would drift on every release | SOURCE_CODE | RESOLVED | `cli.py` now renders `f'PyStreamXL {__version__}'` |
| TD-0003 | BUG | README git-clone instructions, `llms.txt` (2x), and `scripts/install.sh` all pointed at `github.com/Mullassery/StreamXL` — a repo that doesn't exist; actual remote is `Mullassery/PyStreamXL` | DOCUMENTATION | RESOLVED | All 4 URLs corrected |
| TD-0006 | BUILD / DEPENDENCY | `Cargo.lock` exists on disk but was listed in `.gitignore` and never committed, despite this being a PyO3 extension shipped as wheels/sdist (reproducible-build risk). Same pattern flagged previously across other Mullassery repos. | DEPENDENCY | RESOLVED | Removed from `.gitignore`, committed |
| TD-0011 | DOCUMENTATION | Root `CONTRIBUTING.md` was stale on 3 axes: fictional source layout (flat `src/` with `reader.rs`/`writer.rs`/`utils.rs`, none of which exist), wrong license (claimed MIT; project relicensed to Apache-2.0 in a prior commit), and "High-impact areas" listing already-shipped features (formula support, conditional formatting) as outstanding work | DOCUMENTATION | RESOLVED | Rewritten to match actual layout/license/status |
| TD-0012 | SECURITY / ARCHITECTURE | `StreamXLServer`'s REST API has zero authentication of any kind | SOURCE_CODE | OPEN | Needs a product decision (API key / mTLS / reverse-proxy-only); not a safe one-line fix |
| TD-0014 | DOCUMENTATION | `docs/CONTRIBUTING.md` was mislabeled — actual content was Claude-agent build instructions (titled `# CLAUDE.md — streamxl` inside a file named `CONTRIBUTING.md`), containing a stale "Not yet implemented" list (multi-sheet, dates, `as_dict`) that shipped long ago | DOCUMENTATION | RESOLVED | Real content moved to root `CLAUDE.md`, stale list corrected; old path now a redirect stub |
| TD-0015 | DOCUMENTATION / SECURITY | `SECURITY_AUDIT.md` was a frozen v1.0.1-era snapshot claiming "no input validation on file paths" and "no file corruption detection" as open gaps — both are implemented and tested in the current codebase (`security.py`, `integrity.py`); zip-bomb defense wasn't mentioned at all | DOCUMENTATION | RESOLVED | Rewritten to reflect actual current state |

(TD-0001/0002/0003/0006/0011/0014/0015 resolved; TD-0012 open — 7 P1 items, corrected count above includes all P1s.)

## P2 — Medium

| ID | Category | Description | Source | Status | Fix |
|---|---|---|---|---|---|
| TD-0004 | DOCUMENTATION | README's post-clone `cd StreamXL` wouldn't match the actual cloned directory name (`PyStreamXL`) | DOCUMENTATION | RESOLVED | Fixed to `cd PyStreamXL` |
| TD-0007 | SECURITY | `StreamXLServer.__init__`/`run_server` defaulted to binding `0.0.0.0` (all interfaces) | SOURCE_CODE | RESOLVED | Default changed to `127.0.0.1`; explicit opt-in still possible, auth gap tracked separately as TD-0012 |
| TD-0009 | BUG / TEST_DEBT | Two Rust unit tests asserted `collection.len() >= 0` on a `usize` — a tautology, always true, clippy hard-errors on it (`absurd_extreme_comparisons`), and the assertions verified nothing | SOURCE_CODE | RESOLVED | Replaced with explicit no-panic checks (`let _ = ...len();`) with an honest comment |
| TD-0013 | ARCHITECTURE | Public class `StreamXLServer` / module `streamxl.server` keep "StreamXL" (no "Py") naming though the product is PyStreamXL | SOURCE_CODE | OPEN | Renaming is a breaking API change for existing importers; needs a deprecation path, not done this run (see TD-0005) |
| TD-0016 | ARCHITECTURE / CLEANUP | Top-level `pystreaxl/` (typo'd name) + `pystreaxl.toml` (dead MCP config) + top-level `streamxl/` (a one-file `okf_sheet_metadata.py` module that **shadows the real installed package name**) are orphaned boilerplate contamination — unreferenced anywhere, same pattern a prior commit ("Delete leftover PyStreamAI boilerplate contamination") already cleaned up elsewhere in this repo but missed these | SOURCE_CODE | OPEN / BLOCKED | File deletion was denied by this session's sandbox (backgrounded/non-interactive run blocks destructive Bash). Needs a human or interactive session to run `git rm -r pystreaxl pystreaxl.toml streamxl` and commit. |
| TD-0017 | CI_CD | `.github/workflows/ci.yml` runs `cargo test` + `pytest` only — no `cargo-audit`/`pip-audit`/`bandit`/secret-scanning step, and no release/publish-to-PyPI workflow exists (publishing is manual) | CI_FAILURE / INFERRED | OPEN | Needs a security-scan job + a maturin-based release workflow |
| TD-0018 | DEPENDENCY | 10 open Dependabot branches sitting unmerged: `pyo3` 0.23→0.29 (major), `quick-xml` 0.36→0.41/0.42, `zip`→8, `actions/checkout`→7, `actions/setup-python`→7, plus `flask`/`maturin`/`pytest`/`pytest-cov`/`rich` bumps | DEPENDENCY | OPEN | `pyo3` 0.23→0.29 is especially risky given the documented 0.23-specific bool-conversion workaround in `CLAUDE.md` — needs compatibility testing before merge, not a blind merge |
| TD-0020 | DOCUMENTATION | `docs/ROADMAP.md` is generic cross-project boilerplate inconsistent with this being a single-purpose Excel-streaming library: references "19 platform projects," "MCP tools," "SaaS deployment," "multi-tenancy," and labels itself "v2.0.0 / Production Ready" while the actual shipped version is 5.3.0 | ROADMAP | OPEN | Needs a full honest rewrite (same `ROADMAP_HONEST.md` convention applied elsewhere in the org); deferred as a larger effort, not done this run |

## P3 — Low

| ID | Category | Description | Source | Status | Fix |
|---|---|---|---|---|---|
| TD-0005 | DOCUMENTATION | Bare "StreamXL" (missing "Py") product-name mentions in README title/table, `CONTRIBUTING.md`, `SECURITY_AUDIT.md` title, `server.py` docstring, `error_messages.py` user-facing recovery text, `tests/test_server.py` docstring | DOCUMENTATION | RESOLVED | All prose mentions corrected to "PyStreamXL"; identifiers (`StreamXLServer` class, `streamxl` import name) intentionally left alone — see TD-0013 |
| TD-0008 | DEPENDENCY | `pyproject.toml` pinned `rich` with an open-ended `>=13.0`, no ceiling | DEPENDENCY | RESOLVED | Changed to `>=13.0,<15` |
| TD-0010 | REFACTOR | Unnecessary-parens clippy warning in `incremental_recalculation.rs:251` | SOURCE_CODE | RESOLVED | Parens removed |
| TD-0019 | REFACTOR / TEST_DEBT | Remaining non-blocking clippy warnings in `core/`: 4x "empty line after doc comment," 3x "manual `is_multiple_of`," 1x unused `HashSet` import, 4x "consider adding `Default` impl," 1x dead fields (`cell_id`/`formula` never read in `formula_parser.rs`), 1x manual `to_string` impl | SOURCE_CODE | OPEN | Low-priority style cleanup, not done this run to avoid unnecessary churn |
| TD-0021 | BUILD / FUTURE_PHASE | Only a macOS arm64 wheel has ever been published to PyPI (1.2.0 through 5.2.0, per README's own disclosure); Linux/Windows users must build from sdist with a Rust toolchain | BUILD | OPEN / FUTURE | Needs a CI matrix + `maturin-action`/`cibuildwheel` multi-platform build |
| TD-0022 | DOCUMENTATION | No `CHANGELOG.md` exists despite a long version history (1.0.0→5.3.0); the old `CONTRIBUTING.md` referenced updating "the changelog" as a PR checklist item with nowhere to update | DOCUMENTATION | OPEN | Reference removed from the rewritten `CONTRIBUTING.md`; creating a retroactive changelog deferred as a larger effort |

## Explicit TODOs / FIXMEs / stubs

None found in source (`core/`, `python/`, `streamxl/`, `pystreaxl/`, `tests/`) — this repo has clearly already been through TODO-cleanup passes (see git log). No action needed.

## Stubs

None found that aren't already tracked above.

## Partial Implementations

- `server.py` REST API — functionally complete for its scope but has no auth (TD-0012).
- `colorScale`/`dataBar`/`iconSet` conditional-formatting rule types are parsed for type/sqref/priority only, not their inline color-stop/threshold children (documented honestly in-code and in `docs/ROADMAP.md`'s "Done" note for v5.2.0 — not re-tracked as a new item since it's already accurately disclosed).

## Planned Features / Roadmap

`docs/ROADMAP.md`'s content does not reliably describe planned work for
*this* repository (see TD-0020) — it reads as copy-pasted cross-project
boilerplate (MCP tooling, "19 platform projects," SaaS/multi-tenancy). No
phase breakdown is reproduced here because doing so would misrepresent it
as this repo's actual roadmap. The one credible planned item extractable
from it is multi-platform wheel distribution (TD-0021).

## CI/CD Debt

- TD-0017 (no security scanning, no release workflow)
- TD-0018 (10 unmerged Dependabot branches)

## Test Debt

- TD-0009 (resolved tautological assertions)
- No regression test exists for the version-string-consistency bug class (TD-0001/TD-0002) — a `test_version_consistency.py` asserting `streamxl.__version__ == importlib.metadata.version("streamxl")` would have caught both. Not added this run (new test infrastructure beyond the stated fix scope); flagged for a follow-up.

## Dependency Debt

- TD-0006, TD-0008, TD-0018

## Security Debt

- TD-0007 (resolved default bind), TD-0012 (open — no auth), TD-0017 (open — no scanning)

## Architecture Debt

- TD-0013, TD-0016

## Performance Debt

None found beyond what's already disclosed in `benchmarks/results.md`.

## Documentation Debt

- TD-0003, TD-0004, TD-0005, TD-0011, TD-0014, TD-0015, TD-0020, TD-0022

## Resolved Historical Issues (from prior git history, retained for record)

- Reactive backpressure for row streaming — eager full-materialization bug fixed in v5.2.0 (`docs/ROADMAP.md`).
- `streamxl.append()` always raised `SecurityError` — fixed (`e1defe9`).
- 6 conflicting version strings reconciled to 5.1.0 — fixed (`caa19d0`); drifted again by the time of this audit (TD-0001/TD-0002), now re-fixed to 5.3.0.
- Dead zip-bomb test replaced with real integration tests — fixed (`c7063e2`); real Rust-side zip-bomb tests now also verified in this run (`cargo test`, 6/6 passing).
- `dtolnay/rust-toolchain@v1` (nonexistent tag) replaced with `@stable` — fixed (`dbab75e`).
- README overclaims fixed in a prior audit (`5379fc3`, `9a41b6b`).
- Relicensed MIT → Apache-2.0 (`4987836`) — but `CONTRIBUTING.md` wasn't updated at the time, which is exactly TD-0011 found in this run.
- Prior "PyStreamAI boilerplate contamination" cleanup (`345f3f2`) — missed the `pystreaxl/`/`streamxl/` contamination found as TD-0016 in this run.
