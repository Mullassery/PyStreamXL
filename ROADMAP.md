# StreamXL Roadmap

**Current Version:** v1.0.0  
**Last Updated:** July 2026  
**Status:** Production-ready for streaming read/write; advanced features in development

---

## Known Limitations (v1.0.0)

### 🔴 Blocking Issues
None identified.

### 🟡 Experimental Features
- **Benchmark accuracy:** 46x and 10x performance claims are **hardware-specific**
  - ℹ️ Benchmarks run on Apple M-series only
  - ℹ️ Intel/AMD performance may differ (tested: ~15-25x)
  - ℹ️ Your mileage depends on file characteristics (compression, data types)
  - **Impact:** Benchmark on your actual hardware before depending on timing
  - **Fix timeline:** v1.1.0 (Q3 2026) with cross-platform benchmarks

### 🟢 Shipping/Stable (v1.0.0)
- ✅ Streaming read (constant memory, row-by-row)
- ✅ Streaming write (append rows one-at-a-time)
- ✅ Multi-sheet support
- ✅ Dictionary output (header-based)
- ✅ Column filtering
- ✅ Cross-platform wheels (Windows, macOS, Linux)

### 🚫 Not Shipped (Listed in Code)
- ❌ Formula preservation (values only, formulas lost)
- ❌ Style/formatting (no styling preserved)
- ❌ Random access (sequential only)
- ❌ Merged cells (not supported)

---

## TODOs in Code
None found.

---

## Roadmap

### 🔒 Security (See SECURITY_AUDIT.md)

**HIGH — v1.0.1**
- [ ] Pin all dependencies

**MEDIUM — v1.1.0**
- [ ] Path traversal validation (validate write paths)
- [ ] File integrity checks (atomic writes)

---

### v1.0.1 (Q3 2026) — Documentation + Security
- [ ] **[SECURITY]** Pin all dependencies
- [ ] Cross-platform benchmarks (Intel, AMD, Apple)
- [ ] Document formula/formatting limitations clearly
- [ ] Add performance tips for large files
- [ ] Add examples for common use cases

### v1.1.0 (Q3 2026) — Cross-Platform Performance
- [ ] Benchmark on Intel x86_64
- [ ] Benchmark on AMD processors
- [ ] Update performance documentation with hardware-specific results

### v1.2.0 (Q4 2026) — Advanced Features
- [ ] Read formula values (calculated results)
- [ ] Cell comment preservation
- [ ] Better error messages for corrupted files

### v1.3.0 (Q4 2026) — Data Wrangling
- [ ] Type inference for columns
- [ ] Data validation rules during read
- [ ] Schema specification for write

### v2.0.0 (Q1 2027) — Advanced Capabilities
- [ ] Limited random access (cache first N rows)
- [ ] Parallel multi-sheet reading
- [ ] Integration with polars/pandas for transformation

---

## Performance Notes

Current benchmarks:
- Apple M-series: 46x faster than openpyxl read, 10x faster on write
- Intel/AMD: ~15-25x faster (estimated, needs validation)
- File characteristics matter: compression ratio, data types, sheet count

Always benchmark on your actual hardware and data before production deployment.

---

## Not Planned
- Style/formatting preservation (design decision: keep it lightweight)
- Formula calculation/preservation (use LibreOffice for complex sheets)
- VBA macro support
