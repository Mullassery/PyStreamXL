# StreamXL Development Roadmap

**Current Version:** v1.0.0  
**Last Updated:** July 2026  
**Status:** Production-ready streaming Excel I/O

---

## ✅ Completed Milestones (v1.0.0 - v1.0.1)

### v1.0.0 — Core Streaming ✅
- ✅ Streaming read (constant memory)
- ✅ Streaming write (append rows)
- ✅ Multi-sheet support
- ✅ Column filtering
- ✅ Cross-platform wheels

### v1.0.1 — Security Hardening ✅
- ✅ **HIGH:** Pin all dependencies
- ✅ **MEDIUM:** Path traversal validation
  - validate_read_path() for safe reads
  - validate_write_path() for safe writes
- ✅ **MEDIUM:** File integrity checks
  - Atomic write operations
  - SHA256 verification
  - AtomicFileWriter context manager
- ✅ **Audit:** Security audit completed (SECURITY_AUDIT.md)
- ✅ **Error Messages:** 8 detailed error types with file operation guidance

---

## 🔒 Security Implementation Status

### HIGH Priority Issues — ✅ FIXED
- [x] Floating dependency versions
  - **Impact:** Supply chain vulnerability
  - **Fix:** Pinned all dependencies
  - **Timeline:** ✅ v1.0.1

### MEDIUM Priority Issues — ✅ FIXED
- [x] Path traversal vulnerabilities
  - **Impact:** Directory escape attacks
  - **Fix:** Path validation with resolve() checks
  - **Timeline:** ✅ v1.0.1

- [x] No file integrity checks
  - **Impact:** Silent file corruption on write failure
  - **Fix:** Atomic writes with SHA256 verification
  - **Timeline:** ✅ v1.0.1

- [x] No user-friendly error messages
  - **Impact:** Poor debugging of file operation failures
  - **Fix:** Added error_messages.py with 8 file-specific error types
  - **Timeline:** ✅ v1.0.1

---

## 📋 Roadmap

### v1.1.0 (Q3 2026) — Cross-Platform Benchmarks
- [ ] Intel x86_64 performance benchmarks
- [ ] AMD processor benchmarks
- [ ] Platform-specific performance tips
- [ ] Hardware-dependent optimization guide

### v1.2.0 (Q4 2026) — Advanced Features
- [ ] Read formula values (calculated results)
- [ ] Cell comment preservation
- [ ] Better error messages for corrupted files
- [ ] Recovery mode for partially corrupt sheets

### v1.3.0 (Q4 2026) — Data Wrangling
- [ ] Type inference for columns
- [ ] Data validation rules during read
- [ ] Schema specification for write
- [ ] Automatic type conversion

### v2.0.0 (Q1 2027) — Advanced Capabilities
- [ ] Limited random access (cache first N rows)
- [ ] Parallel multi-sheet reading
- [ ] Integration with polars/pandas

---

## Performance Notes

Current benchmarks (M-series):
- ✅ 46x faster than openpyxl on read
- ✅ 10x faster on write
- ⚠️  Intel/AMD performance varies (15-25x estimated)

**Important:** Always benchmark on your actual hardware!

---

## Known Limitations (v1.0.1)

### 🟢 Working
- ✅ Streaming read/write
- ✅ Multi-sheet support
- ✅ Column filtering
- ✅ Path-safe operations
- ✅ Atomic writes with verification

### 🟡 Coming Soon
- 🔄 Cross-platform benchmarks (v1.1.0)
- 🔄 Formula support (v1.2.0)
- 🔄 Type inference (v1.3.0)

### 🔴 Not Planned
- ❌ Style/formatting preservation (design decision: keep lightweight)
- ❌ VBA macro support
- ❌ Merged cell support

---

## Dependencies

All pinned to exact versions for reproducibility.

See `pyproject.toml` for full list.
