# Complete Technical Debt Register — PyStreamXL

## Executive Summary

This register was produced across two passes that ended up overlapping:
this audit started from commit `cc67d06`, but by the time its fixes were
ready to push, `origin/main` had moved 10 commits ahead (through `v6.1.0`)
via a separate, much larger "OSS maturity pass" that independently found
and fixed most of the same issues — generally more thoroughly (a real
package rename `streamxl`→`pystreamxl`, a genuine path-traversal bug this
audit missed, a new `CHANGELOG.md`, `ROADMAP_HONEST.md`, and
`release.yml`). The two histories were merged (not rebased — the package
rename made a clean rebase impractical) and reconciled by hand.

**Attribution below is honest**: items are marked RESOLVED with their
actual source (upstream's maturity pass vs. this audit) so credit isn't
misattributed. Only a handful of this audit's findings survived as
genuinely unique contributions after reconciliation.

Total items: 23
Open: 6
Resolved: 17 (4 by this audit, 13 by upstream's independent pass)
Critical (P0): 0
High (P1): 1 open, rest resolved
Medium (P2): 4 open
Low (P3): 1 open

## P0 — Critical

None found.

## P1 — High

| ID | Category | Description | Status | Resolved by |
|---|---|---|---|---|
| TD-0001 | BUG | `__version__` disagreed with `pyproject.toml`/`Cargo.toml` (5.2.0 vs 5.3.0 at the time) | RESOLVED | Upstream (version now unified at 6.1.0 across all manifests) |
| TD-0002 | BUG | CLI `--version` hardcoded a literal version string, independent of the package version | RESOLVED | Upstream |
| TD-0012 | SECURITY / ARCHITECTURE | `PyStreamXLServer`'s REST API has no authentication of any kind | **OPEN** | — (needs a product decision: API key / mTLS / reverse-proxy-only) |

## P2 — Medium

| ID | Category | Description | Status | Resolved by |
|---|---|---|---|---|
| TD-0003 | DOCUMENTATION | README/`llms.txt`/`scripts/install.sh` pointed at nonexistent `Mullassery/StreamXL` instead of `Mullassery/PyStreamXL` | RESOLVED | Upstream |
| TD-0006 | BUILD / DEPENDENCY | `Cargo.lock` existed on disk but was gitignored, never committed | RESOLVED | Upstream (this audit made the identical fix independently — redundant, no unique credit) |
| TD-0007 | SECURITY | `PyStreamXLServer`/`run_server` default bind was `0.0.0.0` (all interfaces) | RESOLVED | **This audit** — upstream's tree still had `0.0.0.0` at merge time; verified this fix is not redundant |
| TD-0013 | ARCHITECTURE | Public class `StreamXLServer` kept "StreamXL" naming though the product is PyStreamXL | RESOLVED | Upstream — renamed to `PyStreamXLServer` with a proper `DeprecationWarning`-emitting backward-compat alias (better than this audit's original plan to leave it open) |
| TD-0016 | ARCHITECTURE / CLEANUP | Orphaned `pystreaxl/`, `pystreaxl.toml`, top-level `streamxl/` (shadowing the real package name) boilerplate contamination | RESOLVED | Upstream (deleted outright; this audit found the same issue but was blocked from deleting by its own sandbox — see Resolved Historical Issues) |
| TD-0017 | CI_CD | No dependency/secret scanning in CI, no release/publish workflow | RESOLVED (caveat) | Upstream added a `dependency-audit` job (`cargo-audit` + `pip-audit`) and `.github/workflows/release.yml`. Upstream's own comment in `ci.yml` notes the audit job "has not been run/verified end-to-end" (authored without network access to verify). Treat as resolved-but-unverified, not battle-tested. |
| TD-0018 | DEPENDENCY | Unmerged Dependabot branches for `pyo3` 0.23→0.29 (major), `quick-xml`, `zip`→8, `flask`/`maturin`/`pytest`/`pytest-cov`/`rich` bumps | **OPEN** | `actions/checkout`→7 and `actions/setup-python`→7 are now effectively applied (both workflow files use `@v7` directly) even though their Dependabot branches are still technically open/unclosed. The `rich-gte-15.0.0` branch now directly conflicts with this audit's own `rich<15` ceiling (TD-0008) — needs an explicit decision, not an automatic merge. `pyo3` 0.29 still needs compatibility testing against the documented 0.23-specific bool-conversion workaround in `CLAUDE.md` before merging. |
| TD-0020 | DOCUMENTATION | `docs/ROADMAP.md` was generic cross-project boilerplate, not this repo's real roadmap | RESOLVED | Upstream — deleted `docs/ROADMAP.md` and `docs/PRODUCT_VISION.md`, replaced with `ROADMAP_HONEST.md` |
| TD-0021 | BUILD | Only macOS arm64 wheels ever published to PyPI | PARTIALLY_COMPLETE | Upstream's `release.yml` now builds Linux (x86_64/aarch64), macOS (x86_64/aarch64), and Windows wheels across Python 3.10-3.12 — but this has never actually been run end-to-end (no tag pushed yet), and the publish step needs TD-0023 resolved first. |
| TD-0023 | CI_CD (new) | `release.yml`'s `publish` job uses PyPI Trusted Publishing (OIDC), which requires a Trusted Publisher entry added on the `pystreamxl` PyPI project before it will work — not yet configured (upstream's own comment in the workflow file says so explicitly) | **OPEN** | Same recurring pattern seen elsewhere in this org (e.g. PyDependencyCheck's release CI gap) — needs manual `twine upload` of the built wheel artifacts until OIDC trust is set up, or the PyPI project owner to add the Trusted Publisher. Not something this audit can configure (no PyPI credentials available). |

## P3 — Low

| ID | Category | Description | Status | Resolved by |
|---|---|---|---|---|
| TD-0004 | DOCUMENTATION | README's post-clone `cd StreamXL` wouldn't match the cloned dir name | RESOLVED | Upstream |
| TD-0005 | DOCUMENTATION | Bare "StreamXL" product-name prose mentions across docs/source | RESOLVED | Upstream (as part of the full rename; this audit made several identical edits independently, redundant, no unique credit) |
| TD-0008 | DEPENDENCY | `rich` dependency had an open-ended `>=13.0` range | RESOLVED | **This audit** — capped to `>=13.0,<15`. Now in tension with the open `rich-gte-15.0.0` Dependabot branch (TD-0018) — needs a human decision on which to take. |
| TD-0009 | BUG / TEST_DEBT | Two Rust unit tests asserted `.len() >= 0` on a `usize` — always true, a clippy hard error (`absurd_extreme_comparisons`) | RESOLVED | **This audit** — upstream never touched `collaboration_detection.rs`/`cross_sheet_analysis.rs` (confirmed via diff against the merge base); these are in modules upstream's own `CONTRIBUTING.md` now documents as dead code, not wired into Python at all |
| TD-0010 | REFACTOR | Unnecessary-parens clippy warning in `incremental_recalculation.rs` (also dead/unwired code) | RESOLVED | **This audit** |
| TD-0011 | DOCUMENTATION | Root `CONTRIBUTING.md` had a stale layout, wrong license claim (MIT vs actual Apache-2.0), and listed shipped features as outstanding | RESOLVED | Upstream — comprehensively rewritten (correct layout including the dead-code-module callout, correct license, points at `CHANGELOG.md`/`ROADMAP_HONEST.md`). This audit's own rewrite was superseded and discarded in favor of upstream's during reconciliation. |
| TD-0014 | DOCUMENTATION | `docs/CONTRIBUTING.md` was actually mislabeled Claude-agent build instructions with a stale "not yet implemented" list | RESOLVED | **This audit** (partially) — upstream deleted the stale file outright (correctly recognizing the problem) but didn't replace it with equivalent agent-facing build guidance. This audit's content survives as the new root `CLAUDE.md`, corrected for the `pystreamxl` rename. |
| TD-0015 | DOCUMENTATION / SECURITY | `SECURITY_AUDIT.md` was a frozen v1.0.1-era snapshot contradicting the current codebase | RESOLVED | Upstream — archived verbatim as `docs/archive/SECURITY_AUDIT_v1_2026-07_STALE.md` (historical record, correctly left unedited) and superseded by a new, much more thorough `SECURITY.md` that documents a real path-traversal bug this audit never found (see Resolved Historical Issues). This audit's own rewrite of `SECURITY_AUDIT.md` was discarded during reconciliation — it would have been a redundant, less-accurate duplicate of upstream's `SECURITY.md`. |
| TD-0019 | REFACTOR / TEST_DEBT | ~16 non-blocking clippy style warnings (`Default` impls, `is_multiple_of`, dead fields, empty doc-comment lines) | **OPEN** | Low priority; concentrated in the dead/unwired `collaboration_detection.rs`/`cross_sheet_analysis.rs`/`incremental_recalculation.rs`/`formula_parser.rs` modules upstream has flagged as needing a wire-up-or-delete decision — fixing style warnings in code that might get deleted isn't worth doing yet. |
| TD-0022 | DOCUMENTATION | No `CHANGELOG.md` existed despite a long version history | RESOLVED | Upstream — added `CHANGELOG.md` |

## Explicit TODOs / FIXMEs / stubs

None found in source. Confirmed again post-reconciliation.

## Partial Implementations

- `colorScale`/`dataBar`/`iconSet` conditional-formatting rule types parsed for type/sqref/priority only, not inline color-stop/threshold children — already honestly disclosed, not new debt.
- `collaboration_detection.rs`, `cross_sheet_analysis.rs`, `incremental_recalculation.rs` — entire Rust modules compiled and tested but never wired into the PyO3 bridge (`python/src/lib.rs`) or exposed to Python at all. Explicitly documented by upstream in `CONTRIBUTING.md` as abandoned feature work needing a finish-or-delete decision. This is the single largest piece of architecture debt in the repo.

## CI/CD Debt

- TD-0018 (unmerged Dependabot branches, one now in direct conflict with this audit's dependency cap)
- TD-0023 (PyPI OIDC Trusted Publisher not configured; release workflow can build wheels but can't actually publish them yet)
- TD-0017's dependency-audit job is unverified end-to-end (authored without CI network access to confirm it runs cleanly)

## Test Debt

- No regression test exists for the version-string-consistency bug class (TD-0001/TD-0002) that both this audit and upstream independently hit — a `test_version_consistency.py` asserting `pystreamxl.__version__ == importlib.metadata.version("pystreamxl")` would catch future drift. Not added this run.
- 169/169 Python tests passing (up from 160 pre-reconciliation — upstream added `tests/test_security.py` and expanded others).

## Dependency Debt

- TD-0008, TD-0018

## Security Debt

- TD-0012 (open — no server auth)
- TD-0023 (open — PyPI publishing not fully set up)
- See `SECURITY.md` for the comprehensive current security posture — it now supersedes this file for anything beyond the ID-tracked items above.

## Architecture Debt

- Three entire Rust modules (collaboration detection, cross-sheet analysis, incremental recalculation) compiled, tested, and completely unused — see Partial Implementations above. This is more significant than anything originally captured as TD-0013/TD-0016 and wasn't flagged by this audit's first pass; found only while reconciling against upstream's `CONTRIBUTING.md` note.

## Performance Debt

None found beyond what's already disclosed in `benchmarks/results.md`.

## Documentation Debt

All originally-flagged documentation debt (TD-0003/0004/0005/0011/0014/0015/0020/0022) is now resolved — see table above for attribution.

## Resolved Historical Issues

- Reactive backpressure for row streaming (v5.2.0), `append()` always raising `SecurityError`, 6 conflicting version strings reconciled, dead zip-bomb test replaced, bad `rust-toolchain@v1` tag, prior README overclaims, MIT→Apache-2.0 relicense — all pre-date both this audit and upstream's maturity pass; already fixed before either started.
- **Real path-traversal bug found by upstream, not this audit**: `validate_xlsx_path()` resolved the path with `Path.resolve()` (which collapses `..` segments) *before* checking for a literal `".."` substring — meaning the check could never actually fire on a real traversal attempt and was dead code. Fixed with a proper `base_dir`-based confinement check performed after normalization. This is a more serious and more subtle finding than anything this audit's own security pass turned up, and is now the centerpiece of the new `SECURITY.md`.
- **Real bug found by upstream**: false "O(1) memory" claim in docs — actual streaming behavior corrected and benchmarked for real.
- **Real bug found by upstream**: `validate_write_path()` used `print()` instead of logging for an overwrite warning.
- This audit's `TD-0016` finding (orphaned `pystreaxl/`/`streamxl/` contamination) — flagged but **blocked from fixing** in this audit's first pass because its sandbox (a backgrounded, non-interactive run) denied both `rm -rf` and `git rm` as destructive actions with no one available to approve them. Resolved anyway once upstream's independent pass deleted the same files and the merge brought that deletion in.
