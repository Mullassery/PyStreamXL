# Queue status — 2026-10-19

This file records what was shipped, what is blocked/failed, and what is rejected for this repository. It complements `AUDIT_FINDINGS.md`.

## Shipped
- Analyzer bridge, streaming Parquet export, calamine/Polars benchmark, corrected memory claims.
- Published 6.1.7 wheels: macOS arm64/x86_64, Linux x86_64/aarch64.

## Blocked / failed
- Windows wheel — local cross-compile toolchain fails; use the GitHub release workflow.

## Rejected / deferred
- SQL query language, formula recalculation, dashboard.

## Policy

Any future feature or upgrade must check `AUDIT_FINDINGS.md` and this file before implementation. A blocked item is retried only when its external dependency is available; a rejected item needs new user evidence or a design change to reopen.
