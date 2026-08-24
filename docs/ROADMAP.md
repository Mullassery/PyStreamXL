# PyStreamXL v2.0.0: Task Roadmap

## Current Status: Production Ready

**Version:** 2.0.0  
**Status:** Production Ready (MCP 2.0 Platform member)  
**Last Updated:** 2026-07-31  

## Pending Tasks by Priority

### 🚨 CRITICAL (Blocking Production)
None - v2.0.0 production-ready

### 🔴 HIGH (Before Q3 Release)

#### Testing & Quality
- [ ] Add MCP-specific unit tests (50-100 lines per project)
- [ ] Coverage target: >80% for MCP tools
- [ ] Integration tests with other projects
- [ ] Performance benchmarking (latency/throughput)

#### Documentation
- [ ] Add MCP tool examples (examples/mcp_*.py)
- [ ] API documentation for each tool
- [ ] Integration guide for dependent projects
- [ ] Troubleshooting guide

#### Performance
- [ ] Optimize hot paths (profile + identify 20% taking 80%)
- [ ] Caching strategy for repeated queries
- [ ] Memory optimization (target <200MB)
- [ ] Connection pooling
- [x] Reactive backpressure for row streaming — **Done (v5.2.0).** `read()`/`stream()` previously called the eager `_core.read()` binding, materializing the entire sheet into a Python list before yielding row 0 at all — "streaming" in name only, worse than the originally-described gap. Fixed with a real `__iter__`/`__next__` Python iterator (`PyRowIter`/`PyRowIterMetadata` in `python/src/lib.rs`, built on `self_cell` to safely pair the owned `XlsxStream` with a borrowed `RowIter`) that pulls exactly one row per `next()` call from the already-correct Rust-level `RowIter`/`RowIterMetadata`. The old eager behavior is preserved under explicit `read_rows_all_at_once()`/`read_rows_with_metadata_all_at_once()` names for callers that need random access or repeated iteration. Regression-tested in `tests/test_streaming.py` via a wall-clock timing ratio (time-to-first-row vs. total time), since `tracemalloc` doesn't reliably track PyO3/Rust-native allocations.

### 🟡 MEDIUM (Q3-Q4 2026)

#### Features
- [ ] Advanced error handling
- [ ] Retry logic with exponential backoff
- [ ] Graceful degradation
- [ ] Fallback mechanisms
- [x] Conditional formatting rule parsing — **Done (v5.2.0).** New `core/src/conditional_formatting.rs` parses every `<conditionalFormatting>`/`<cfRule>` block in worksheet XML (type, operator, formula(s), priority, `stopIfTrue`) and `core/src/dxf.rs` parses `xl/styles.xml`'s `<dxfs>`; each rule's `dxfId` is resolved into the differential format's font color/bold/italic and fill colors. Exposed as `streamxl.conditional_formats(path, sheet=None)`. `colorScale`/`dataBar`/`iconSet` rules are captured (type, sqref, priority) but their inline color-stop/threshold children aren't modeled — those rule types don't reference `dxfId` at all, so this is a distinct, larger scope than closing the "no parsing at all" gap.

#### Architecture
- [ ] Code refactoring (simplify hot paths)
- [ ] Remove technical debt
- [ ] Modernize dependencies
- [ ] Cleanup unused code

#### Integration
- [ ] Test with all 19 platform projects
- [ ] Document cross-project workflows
- [ ] Validate end-to-end scenarios
- [ ] Performance testing at scale

### 🟢 LOW (2027+)

#### Enhancements
- [ ] Machine learning optimizations
- [ ] Predictive modeling
- [ ] Advanced analytics
- [ ] Autonomous features

#### Platform
- [ ] Enterprise features
- [ ] SaaS deployment
- [ ] Multi-tenancy
- [ ] Advanced security

---

## Phase Timeline

### Phase 2: Q3 2026 (Jul-Sep)
**Goal:** Critical tests + examples + cross-project integration

- Week 1-2: MCP unit tests (all 19 projects)
- Week 2-3: MCP examples (examples/mcp_*.py)
- Week 3-4: Cross-project integration testing
- Week 4: Performance optimization
- **Completion Target:** 2026-09-30

### Phase 3: Q4 2026 (Oct-Dec)
**Goal:** Advanced features + enterprise deployment

- Week 1: Feature enhancements
- Week 2: Advanced error handling
- Week 3: Enterprise security
- Week 4: SLA automation
- **Completion Target:** 2026-12-31

### Phase 4: 2027
**Goal:** AI-native enhancements + autonomous features

- Predictive modeling
- Autonomous optimization
- Advanced analytics
- Next-generation architecture

---

## Testing Checklist

### Unit Tests
- [ ] All MCP tool handlers tested
- [ ] Edge case coverage
- [ ] Error path testing
- [ ] Performance regression tests

### Integration Tests
- [ ] With dependent projects
- [ ] Cross-project workflows
- [ ] End-to-end scenarios
- [ ] Production-like data volumes

### Performance Tests
- [ ] Latency benchmarks (<100ms)
- [ ] Throughput testing
- [ ] Memory profiling
- [ ] Connection pooling

---

## Dependency Status

### Inbound Dependencies
Check status of upstream projects:
- [ ] All inbound dependencies are v2.0.0+
- [ ] No breaking API changes
- [ ] Security patches applied

### Outbound Dependency Status
Monitor projects depending on this one:
- [ ] All dependent projects passing tests
- [ ] No regression reports
- [ ] SLA targets maintained

---

## Release Checklist (v2.1.0)

Before release to PyPI:
- [ ] All tests passing (>80% coverage)
- [ ] MCP tools documented
- [ ] Examples created and tested
- [ ] Performance benchmarks meet targets
- [ ] Security audit completed
- [ ] Changelog updated
- [ ] Version bumped (v2.0.0 → v2.1.0)
- [ ] Wheels built (wheels-only)
- [ ] GitHub tag created
- [ ] PyPI package published

---

## Metrics & Success Criteria

### Performance Targets
- Latency: <100ms (p99)
- Throughput: Platform-dependent
- Memory: <200MB (typical)
- CPU: <50% single core

### Quality Targets
- Test Coverage: >80%
- MCP Tool Coverage: 100%
- Documentation: 100%
- Uptime: >99.5%

### Adoption Targets
- Integrated with all dependent projects
- Used in production by >5 teams
- Zero critical bugs in Phase 2

---

## Questions & Decisions

- [ ] Should we add async streaming support?
- [ ] Do we need multi-region deployment?
- [ ] What's the migration path from v2.0.0 → v2.1.0?
- [ ] Should we support older Python versions (<3.10)?

---

## Contact & Escalation

**Primary Owner:** Product Team  
**Escalation Contact:** Platform Lead  
**Review Schedule:** Every 2 weeks (Phase 2-3)  

---

**Next Review:** 2026-08-14 (Phase 2 progress check)
