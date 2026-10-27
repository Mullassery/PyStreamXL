# Audit findings — 2026-10-26

This file records the current portfolio-audit findings for PyStreamXL. It is
documentation only; no code or release artifacts were changed. The fuller
evidence report is kept in the portfolio workspace at
`.audit/reports/PyStreamXL/audit.md`.

## What it is

A Rust-backed streaming `.xlsx` reader/writer with formula extraction, comments,
conditional formatting, cross-sheet analysis, error recovery, CSV/JSON/optional
Parquet export, and a small optional Flask REST server.

## Verified strengths

- Real Rust streaming reader/writer; rows are not fully materialized on read.
- Formula/comment/conditional-format handling and cross-sheet analysis.
- Security limits for path validation, file size, and ZIP bombs.
- CSV-injection sanitization at export.
- Optional API-key auth (`PYSTREAMXL_API_KEY`) and optional PyArrow Parquet
  export are implemented.
- Committed benchmarks against openpyxl.
- 20 test files, 189 static Python and 63 static Rust test definitions.

## Verified gaps and user-facing risks

- **Documentation contradicts code:** README still says there is no auth and no
  Parquet/Arrow export, but both now exist.
- **Auth is optional with warning-only fallback:** without an API key the server
  remains open. Default bind is loopback, but a non-loopback bind is unsafe.
- **Server is not production-grade:** Flask development server, in-memory source
  and query registries, no durable state, and no multi-worker correctness.
- **Memory exhaustion:** query `limit` is caller-controlled with no server
  maximum; export materializes the whole sheet (`list(read(...))`).
- **Unbounded query metadata:** `queries` grows per executed query.
- **Race:** `_query_seq += 1` is not locked under threaded serving.
- **Production/stable claim outruns optional surfaces:** the core is credible,
  the server is a local adapter.
- **Dead/optional Rust modules:** some modules are not wired to Python callers.
- **Error responses can expose local paths.**
- Some README claims/outputs still overstate speed or "constant memory" relative
  to the committed benchmark evidence.

## Direct positioning

Against python-calamine, Polars `read_excel`, and openpyxl. The defensible wedge
is bounded-memory streaming plus formula/metadata fidelity, not raw whole-sheet
speed.

## Ranked next actions

1. P0: require auth for non-loopback binds, or refuse to start without a key.
2. P0: add a server-side row cap and stream/chunk export instead of
   materializing the whole sheet.
3. P1: correct README claims about auth, Parquet, speed, and memory.
4. P1: make query/source state durable or document single-process ephemerality.
5. P1: lock query ID generation and bound/evict query metadata.
6. P2: replace the Flask dev server with a production-ready WSGI/ASGI setup if
   the server is a supported product.
7. P2: wire or remove dead Rust modules; expand benchmark coverage to calamine
   and Polars.
8. P2: avoid returning filesystem paths in errors.

## Do not build

- A SQL query engine, formula recalculation engine, or live dashboard. Stay an
  I/O/streaming engine.

## Evidence gaps / validation needed

- No 1M-row RSS proof.
- No full calamine/Polars comparison on all workloads.
- No Linux runtime test for every optional path.
- No load test of the REST server.

## Recommended disposition

Invest in the streaming core. Treat the REST server as a local convenience until
auth, memory bounds, and durability are addressed.
