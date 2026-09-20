# Archive

Historical status docs, kept for reference only. For current status see
the main [`README.md`](../../README.md)'s "Honest feature list" section,
and [`docs/architecture/README.md`](../architecture/README.md) for the
current architecture.

`architecture_v1_2026-07_STALE.md`, `design_decisions_v1_2026-07_STALE.md`,
`api_spec_v1_2026-07_STALE.md`, and `performance_model_v1_2026-07_STALE.md`
describe the original single-sheet, read-only MVP (v0.x/v1.x). They
predate multi-sheet support, the writer, formula/comment extraction,
conditional formatting, and the security hardening added since — several
of their specific claims (e.g. "sheet1.xml only", "sheet= param post-MVP")
are no longer true. `SECURITY_AUDIT_v1_2026-07_STALE.md` is a similarly
outdated v1.0-era security review whose findings were resolved long ago
and whose version-target roadmap (v1.0.1, v1.1.0, ...) was superseded by
the version history actually shipped. `docs/ROADMAP.md` and
`docs/PRODUCT_VISION.md` were deleted outright rather than archived here:
both described a fictional "MCP 2.0 Platform" (19 projects, 228 tools,
a "StatGuardian" dependency, an "8781" MCP port) that never existed in
this codebase — boilerplate contamination from an unrelated project
template, not a real historical state of PyStreamXL.
