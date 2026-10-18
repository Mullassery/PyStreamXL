# Audit findings — 2026-10-19

This file records the repository-specific findings from the portfolio audit
conducted on 2026-10-19. It is documentation only; no code or release artifacts
were changed in this pass unless explicitly noted under "Implementation status".

Sources: the repository's own README/source/workflows, GitHub metadata and
Actions runs, PyPI metadata, and official competitor documentation. Claims are
marked as verified, inferred, or open questions. "Absent" means not found in the
inspected repository/docs, not proof that it cannot exist.

## What it is

Stream large `.xlsx` files row-by-row in flat memory, with streaming writes, formula/comment extraction, and multi-sheet support.

## Verified strengths

- Real Rust streaming reader/writer; multi-sheet; formulas/comments/conditional formatting; type-aware cells; zip-bomb and CSV-injection defenses; 19 test files; committed benchmark vs openpyxl; all-platform release workflow exists.
- True streaming + formula fidelity is a genuine gap-filler.

## Verified gaps and user-facing risks

- PyPI ships only a macOS arm64 wheel; the release workflow has never produced Linux/Windows wheels and Trusted Publishing is not configured.
- Benchmark is only vs openpyxl, not python-calamine/Polars; its own table shows memory rising 2.8 MB → 68.7 MB at 250k rows, contradicting 'constant memory'.
- GitHub description says '46x faster'; README says 3.8–5.6x. No Arrow/Parquet, pandas/Polars integration, or projection/filter pushdown.
- Optional server is loopback-only and unauthenticated.

## Direct competitors

- python-calamine (MIT, 104 wheels, pandas 2.2 built-in), Polars (`read_excel` via calamine), openpyxl.

## Ranked next actions

- P1: execute the wheel workflow + Trusted Publishing (S).
- P1: benchmark vs calamine/Polars and prove/fix memory (M).
- P2: Arrow/Parquet sink + pandas/Polars handoff (M).
- P2: projection/filter pushdown (M).

## Do not build

- SQL query language, formula recalculation, live dashboard; it is an I/O engine.

## Evidence gaps / validation needed

- No 1M-row RSS proof; no calamine comparison; no Linux runtime test.

## Recommended disposition

Invest; packaging and honest claims are the blockers.

## Implementation status

No code changes in this pass.
