# PyStreamXL Security Audit

**Last Updated:** 2026-10 (v5.3.0)
**Status:** Core file-handling controls implemented; CI-level scanning still missing.

This file previously described a v1.0.1-era snapshot that was stale against the
current (v5.3.0) codebase — several "open" items below were already fixed in
later releases and are now marked resolved. See `TECHNICAL_DEBT.md` for the
full, ID-tracked backlog this file now defers to.

---

## Resolved

### Path traversal / invalid-path writes
`python/streamxl/security.py` (`validate_xlsx_path`, `validate_read_path`,
`validate_write_path`) rejects non-`.xlsx`/`.xls` extensions, path-traversal
sequences, missing files/parents, and empty files before any read/write
touches the filesystem. Covered by the test suite.

### Zip-bomb / decompression-bomb defense
`core/src/zip_reader.rs` enforces `MAX_FILE_SIZE` (512MB), `MAX_ENTRY_SIZE`
(512MB), `MAX_TOTAL_SIZE` (1GB decompressed), and `MAX_COMPRESSION_RATIO`
(30:1) — see `core/tests/zip_bomb_defense.rs`. Not present at all in the
original version of this document.

### File corruption on partial writes
`python/streamxl/integrity.py` implements write-to-temp-then-rename atomic
writes (`atomic_write`, `AtomicFileWriter`), used by the writer path
(`api.py` write/append).

### CSV formula injection on export
`python/streamxl/security.py::sanitize_csv_cell`, used by `server.py`'s
`/export` endpoint.

---

## Open

### No supply-chain scanning in CI (TD: see SECURITY category)
`.github/workflows/ci.yml` runs `cargo test`/`pytest` only — no `cargo audit`,
`pip-audit`, `bandit`, or secret scanning (e.g. gitleaks). Dependabot is
configured (`.github/dependabot.yml`) and opens PRs, but nothing validates
dependencies for known CVEs on every push, and nothing scans for committed
secrets.

### Open-ended dependency version range
`pyproject.toml` pins `rich>=13.0` with no upper bound; a future breaking
`rich` release could silently break builds. Low severity (single, well-known
dependency) but worth a ceiling (`rich>=13.0,<15`) or Dependabot-managed caps.

### REST server has no authentication, binds all interfaces by default
`python/streamxl/server.py`'s `StreamXLServer`/Flask app exposes filesystem
read access (within the validated-path sandbox) over HTTP with no auth of
any kind. Default bind was `0.0.0.0` (now changed to `127.0.0.1` — see
`TECHNICAL_DEBT.md`); still no API-key/token check for callers that
explicitly bind it to a non-loopback address. Documented as an open item
rather than fixed here since adding real auth is a product decision
(API key? mTLS? reverse-proxy-only?), not a one-line fix.

---

## Testing

```bash
pytest tests/ -v              # includes security.py + integrity.py coverage
cargo test --release --manifest-path core/Cargo.toml   # includes zip_bomb_defense.rs
```

No `pip-audit`/`cargo audit`/`bandit` step exists yet locally or in CI — see
the Open section above.
