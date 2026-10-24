# Competitive intelligence in roadmap and upgrade work

**Policy date:** 2026-10-19

Competitive findings are an input to product decisions, not a one-off report.
Every pending roadmap item, new feature, and routine dependency upgrade should
check the repository's [`AUDIT_FINDINGS.md`](AUDIT_FINDINGS.md) before work
starts, and record the decision in the PR or changelog.

## Required check before building

1. **Read `AUDIT_FINDINGS.md`.** Find the relevant competitor row and the
   ranked next actions. If the finding is stale, update it with a dated source.
2. **Name the competitor and the user problem.** A feature is not justified by
   "competitor has it". State the workflow it unlocks, who needs it, and how
   often. Mark unverified demand as a hypothesis.
3. **Prefer reuse over new code.** Check whether an existing Mullassery repo
   already provides the capability (see `BUNDLES.md` in the profile repo and
   the bundle role file in this repo, when present). Typical reuse:
   - crawling/fetching/robots/SSRF → **MudFish**
   - architecture maps / PR diffs → **CodeAtlas**
   - data-quality contracts / validation → **StatGuardian**
   - token counting / cost tables → **PyTokenCalc**
   - dependency graph / advisories / SBOM → **PyDeepMesh**
   - segmentation / CLV / churn → **ClusterAudienceKit**
   - activation / lineage / PII → **PyReverseETL**
   - fleet state sync → **SyncFleet** (only after conflict resolution)
4. **Choose one disposition:** build, integrate, defer, or reject. Write it
   down. A rejection with a reason is a successful outcome.
5. **For routine upgrades**, check whether the upgrade closes a known
   competitor gap or breaks a differentiated capability. Run the tests that
   cover the affected path; do not merge a green build that silently changes a
   user-visible contract.

## PR / changelog checklist

- [ ] Competitor and source URL/date recorded (or "no direct competitor").
- [ ] User impact and frequency stated; unverified demand labelled.
- [ ] Reuse check done against sibling repos/bundles.
- [ ] Failure mode and rollback considered (especially auth, PII, cost).
- [ ] Docs/roadmap status updated honestly.
- [ ] Tests or a manual verification command included.

## Review cadence

- Refresh the competitor row when a release changes the capability.
- Re-check the full `AUDIT_FINDINGS.md` at least quarterly and before a major
  release.
- If a finding is wrong or stale, correct it in the same PR that relies on it.

## Non-goals

- Copying features for parity.
- Adding a dependency just because a competitor uses it.
- Treating star counts or download counts as proof of user need.

## OSS gap analysis — 2026-10-24

**What matters most here:** install coverage and honest memory claims. macOS-arm64-only contradicts the README, and RSS grows to ~69 MB at 250k rows; ship multi-platform wheels and prove 1M-row behavior before claiming constant memory.

Scope: Compared PyStreamXL's streaming `.xlsx` reader/writer, formula fidelity, and memory behavior against the four libraries a data engineer would shortlist for large-workbook ingestion.

### Comparable OSS projects
| Project | GitHub | License | Last activity | Why it is the comparison |
| --- | --- | --- | --- | --- |
| python-calamine | https://github.com/dimastbk/python-calamine | MIT | 0.9.0, 2026-10-16 | Rust/calamine binding; the speed and format-coverage benchmark |
| Polars | https://github.com/pola-rs/polars | MIT | 2.0.0, 2026 | `read_excel` defaults to calamine; DataFrame-native alternative |
| openpyxl | Heptapod: https://foss.heptapod.net/openpyxl/openpyxl (not GitHub) | MIT | 3.1.5, 2024-06-28 | Read-only mode is the incumbent streaming baseline |
| xlsx2csv | https://github.com/dilshod/xlsx2csv | MIT | 0.8.6, 2026-01-30 | Purpose-built large-file converter; closest "just stream it" rival |

### Capability comparison
| Capability | Ours | python-calamine | Polars | openpyxl | xlsx2csv | Gap |
| --- | --- | --- | --- | --- | --- | --- |
| Row-by-row streaming read | Yes | Partial | No | Partial | Yes | Ahead |
| Bounded RSS at scale | Partial | No | No | Partial | Yes | Moderate |
| Multi-sheet | Yes | Yes | Yes | Yes | Yes | Parity |
| Formula text extraction | Yes | Yes | No | Yes | No | Ahead |
| Circular-reference detection | Yes | No | No | No | No | Ahead |
| Comments / conditional formats | Yes | Partial | No | Yes | No | Parity |
| Streaming write / append | Yes | No | Partial | Partial | No | Ahead |
| `.xls` / `.xlsb` / `.ods` | No | Yes | Yes | No | No | Large |
| pandas/Polars/Arrow handoff | Partial | Yes | Yes | No | No | Moderate |
| Projection / filter pushdown | Partial | Partial | Partial | No | Partial | Moderate |
| Zip-bomb / CSV-injection guards | Yes | Partial | Partial | No | Partial | Ahead |
| Cross-platform wheels | No | Yes | Yes | Yes | Yes | Critical |

Nuance: "Ours" streams a real Rust iterator, but the committed benchmark shows process RSS rising from 2.8 MB to 68.7 MB at 250k rows, so "constant memory" is bounded-ish rather than flat. The same benchmark records python-calamine at 0.192s vs PyStreamXL at 3.87s for a 50k-row whole-sheet load, so we are the slower choice unless memory is the constraint. openpyxl is effectively frozen (3.1.5, June 2024) but remains the default everyone compares against. Wheel coverage is disputed in-repo: the README claims Linux/macOS/Windows builds, while `AUDIT_FINDINGS.md` (2026-10-19) records only a macOS arm64 wheel on PyPI; treat current PyPI coverage as unverified.

### Gaps that matter (ranked)
1. **Install coverage is not what the README implies** — the audit found only macOS arm64 on PyPI even though a release workflow exists, while every comparable installs everywhere. A Linux CI or Docker user cannot adopt us. Effort S/M.
2. **Memory is bounded, not constant** — RSS grows to ~69 MB at 250k rows and there is no 1M-row proof. Teams choosing us specifically to avoid OOM need that number, and calamine/Polars are far faster if the sheet fits in RAM. Effort M.
3. **Raw read speed loses to calamine and Polars** — the repo's own comparison (0.192s vs 3.87s at 50k rows) concedes this. We need to win on memory or fidelity, not throughput, and say so. Effort M (positioning) / L (engine).
4. **No `.xls`, `.xlsb`, or `.ods`** — calamine and Polars read all three; legacy `.xls` alone disqualifies us from many finance/ETL pipelines. Effort M via calamine reuse.
5. **Weak DataFrame interop and no pushdown** — `read(columns=...)` projects, but there is no native pandas/Polars handoff and no predicate pushdown; `to_parquet` exists only behind `[arrow]`. Effort M.
6. **Optional REST server is unauthenticated** — README states anyone reaching the port can read every source; this blocks any shared deployment. Effort S.

### Where we are differentiated
- Formula text, comments, and conditional-format resolution plus circular-reference validation — none of the read-focused comparables do dependency analysis.
- True streaming writer and `append()` that preserves other sheets, which calamine and xlsx2csv cannot do at all.
- Explicit ZIP-bomb limits and CSV/formula-injection sanitization in the core path.
- Fidelity features (formulas, comments, dxf styles) on a streaming reader, not only on a whole-workbook object model.

### Disposition
- **Build:** ship the existing multi-platform wheel workflow and a 1M-row RSS benchmark; make the memory claim match the measurement.
- **Integrate/reuse:** calamine (via python-calamine/fastexcel) for `.xls`/`.xlsb`/`.ods` and as an optional fast path; expose Arrow/pandas/Polars handoff.
- **Defer/reject:** SQL query language, formula recalculation, and live dashboard; stay an I/O + fidelity engine.

### Sources
- https://github.com/dimastbk/python-calamine (accessed 2026-10-24)
- https://github.com/pola-rs/polars (accessed 2026-10-24)
- https://foss.heptapod.net/openpyxl/openpyxl (accessed 2026-10-24)
- https://github.com/dilshod/xlsx2csv (accessed 2026-10-24)
- Repo files inspected: `README.md`, `COMPETITIVE_INTELLIGENCE.md`, `AUDIT_FINDINGS.md`, `docs/architecture/README.md`, `pyproject.toml`, `Cargo.toml`, `python/pystreamxl/__init__.py`
