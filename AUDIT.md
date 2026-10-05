# Repository Audit — PyStreamXL

## Health

**GREEN** (upgraded from an initial YELLOW assessment). Between this
audit's first pass and reconciliation, upstream's independent "OSS
maturity pass" fixed nearly everything this audit found — and found a
genuinely more serious bug (a dead path-traversal check) this audit
missed entirely. What's left open is a short, well-understood list: no
server auth, a couple of dependency decisions, and PyPI OIDC setup.

## Reconciliation note

This audit's fixes were committed locally against `cc67d06`. By the time
they were ready to push, `origin/main` had moved 10 commits ahead (to
`v6.1.0`) via an unrelated, much larger pass that renamed the package
(`streamxl`→`pystreamxl`), renamed `StreamXLServer`→`PyStreamXLServer`,
fixed a real path-traversal bug, added `CHANGELOG.md`/`ROADMAP_HONEST.md`,
and added CI dependency scanning + a multi-platform release workflow. The
two histories were merged (git handled the rename-tracking for the
Python-package move correctly) and conflicts resolved by hand, preferring
upstream's version wherever both sides touched the same thing. See
`TECHNICAL_DEBT.md` for the full, attributed breakdown of what was
already fixed upstream vs. what this audit actually contributed.

## Before Audit (this audit's original baseline, commit cc67d06)

Open debt: 22
Critical: 0 · High: 5 · Medium: 11 · Low: 6

## After Reconciliation

Open debt: 6
Critical: 0 · High: 1 (TD-0012, server auth) · Medium: 4 · Low: 1

## Items This Audit Actually Fixed (surviving, non-redundant)

1. **TD-0007** — `PyStreamXLServer`/`run_server` default bind changed `0.0.0.0` → `127.0.0.1`. Confirmed upstream's tree still had `0.0.0.0` at merge time — not redundant.
2. **TD-0008** — `rich` dependency capped `>=13.0,<15` (now in tension with an open Dependabot branch proposing `rich>=15` — flagged as TD-0018, needs a human call).
3. **TD-0009** — Two tautological Rust test assertions (`.len() >= 0`, clippy hard error) fixed in `collaboration_detection.rs`/`cross_sheet_analysis.rs`. Confirmed upstream never touched these files.
4. **TD-0010** — Unnecessary-parens clippy warning fixed in `incremental_recalculation.rs`.
5. **TD-0014** — New root `CLAUDE.md` with agent build-instructions (maturin workflow, PyO3 0.23 gotchas, cell-type table), carried forward from the old mislabeled `docs/CONTRIBUTING.md` and corrected for the `pystreamxl` rename. Upstream deleted the stale file but didn't replace it with equivalent agent-facing guidance — this fills that gap.

## Items This Audit Found But Upstream Already Fixed (better, independently)

Version-string drift, hardcoded CLI version, broken GitHub URLs, bare
"StreamXL" naming throughout docs/source, `Cargo.lock` not committed,
`StreamXLServer`→`PyStreamXLServer` rename, stale `CONTRIBUTING.md`,
orphaned `pystreaxl`/`streamxl` contamination, boilerplate
`docs/ROADMAP.md`, missing `CHANGELOG.md`, missing CI dependency
scanning/release workflow. Full detail and attribution in
`TECHNICAL_DEBT.md`.

Notably, this audit's own rewrite of `SECURITY_AUDIT.md` was **discarded**
during reconciliation: upstream's new `SECURITY.md` is more thorough and
accurate (it documents a real path-traversal bug — a dead substring check
that ran *after* `Path.resolve()` already collapsed `..` segments —
that this audit's security review never caught). Publishing this audit's
version alongside upstream's would have created two documents describing
current security posture, guaranteed to drift apart. The original
`SECURITY_AUDIT.md` was restored to its true, unedited v1.0.1-era content
at its archived path (`docs/archive/SECURITY_AUDIT_v1_2026-07_STALE.md`)
rather than left holding this audit's now-superseded rewrite.

## Items Remaining

- **TD-0012** (P1) — No authentication on the REST server. Product decision required.
- **TD-0018** (P2) — Dependabot backlog, including a `pyo3` major-version bump needing compatibility testing, and a direct conflict between this audit's `rich<15` cap and an open `rich>=15` Dependabot branch.
- **TD-0023** (P2) — Release workflow builds wheels for Linux/macOS/Windows but can't publish: PyPI Trusted Publisher (OIDC) isn't configured yet. Same recurring gap pattern seen elsewhere in this org. Requires either OIDC setup on the PyPI project or a manual `twine upload` with credentials this audit doesn't have access to.
- **TD-0021** (P2, partially complete) — Multi-platform wheel building is now defined in CI but has never actually been run (no release tag pushed with it yet).
- **TD-0017** (P2, resolved-with-caveat) — Dependency-audit CI job added but self-described by its author as unverified end-to-end.
- **TD-0019** (P3) — ~16 low-priority clippy style warnings, concentrated in Rust modules (`collaboration_detection.rs`, `cross_sheet_analysis.rs`, `incremental_recalculation.rs`) that are compiled and tested but **completely unused** — not wired into the PyO3 bridge at all. This dead-code situation is the single biggest piece of architecture debt in the repo; fixing style warnings in modules that might get deleted isn't worth doing before that decision is made.

## CI Status

`ci.yml`: rust-build + python-tests (3.10/3.11/3.12 matrix) + new
dependency-audit job. `release.yml`: new, builds wheels across 3
platforms × 2 architectures, not yet exercised by an actual tag push.

## Test Status

169/169 Python tests passing (verified post-reconciliation; grew from 160
as upstream added `tests/test_security.py` and expanded others). 9/9 Rust
tests passing (3 lib + 6 zip-bomb-defense integration). `cargo clippy`:
0 errors (was 2 before this audit's fixes), ~16 non-blocking style
warnings remain in dead-code modules.

## Build Status

`cargo build --release --all-features` succeeds. `pip install -e ".[dev]"`
via maturin succeeds against the renamed `pystreamxl` package; `import
pystreamxl` and `pystreamxl --version` both confirmed working and
reporting `6.1.0` correctly.

## Security Status

See `SECURITY.md` (upstream, comprehensive) for the authoritative current
posture — it documents a real path-traversal fix, ZIP-bomb defenses,
write-side size caps, and the deliberate choice to make path confinement
opt-in rather than default. This audit's net contribution to security was
the server default-bind fix (TD-0007); everything else security-related
this audit found was either already covered better upstream or is now
tracked as genuinely open (TD-0012, TD-0023).

## Dependency Status

`rich` capped (this audit). `Cargo.lock` committed (upstream, independently
also done by this audit — redundant). 13 Dependabot branches remain open;
2 of them (`actions/checkout`/`setup-python` → v7) are functionally
obsolete since both workflow files already use `@v7` directly from manual
edits. The rest need evaluation, not blind merging — flagged as TD-0018.

## Final Assessment

This audit's standalone value, after honest reconciliation against a
much larger independent pass that landed concurrently, is small but real:
one security default fix that upstream missed, one dependency ceiling,
two dead-code test/lint fixes, and a build-instructions doc (`CLAUDE.md`)
that fills a gap upstream's own cleanup left behind. The bulk of what this
audit originally flagged as debt was independently found and fixed —
generally better — by the concurrent pass, including a real security bug
(the dead path-traversal check) this audit's own security review did not
catch. What remains open is a short, concrete list: server authentication
(a product decision), a few dependency calls, and finishing PyPI OIDC
setup so the new multi-platform release workflow can actually publish.
