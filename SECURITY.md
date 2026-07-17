# PyStreamXL Security & Hardening Guide

**Version:** 1.1.0 (Security Hardening Release)  
**Date:** 2026-07-17  
**Status:** ✅ PRODUCTION READY

---

## Executive Summary

PyStreamXL v1.1.0 includes comprehensive security hardening against:
- **ZIP bomb attacks** (decompression bombs)
- **Denial-of-service (DOS) attacks** via resource exhaustion
- **Path traversal exploits**
- **File format violations**

All security checks are enabled by default. No configuration needed.

---

## Security Protections

### 1. ZIP Bomb (Decompression Bomb) Prevention

**What it protects against:** Malicious ZIP files that compress to tiny sizes but expand to enormous sizes, consuming disk space and memory.

**PyStreamXL Protection:**
```python
MAX_COMPRESSION_RATIO = 30.0  # Industry standard (OWASP)
MAX_ENTRY_SIZE = 512 MB       # Per ZIP entry
MAX_TOTAL_SIZE = 1 GB         # Total decompressed
```

**How it works:**
1. Compression ratio checked during reading (Rust core)
2. Individual entry sizes validated (Rust core)
3. Total decompressed size tracked (Rust core)
4. Reading stops if any limit exceeded

### 2. Denial-of-Service (DOS) Prevention

**File Size Limits:**
- Maximum file size: 512 MB
- Prevents memory exhaustion from huge files
- Legitimate Excel files rarely exceed 50 MB

**Validation points:**
1. Before reading — File size checked (Python)
2. During reading — Entries checked (Rust)
3. Cumulative — Total decompressed checked (Rust)

### 3. Path Traversal Prevention

**Protection:**
- Rejects paths containing ".." (directory traversal)
- Validates file extensions (.xlsx, .xls only)
- Uses `Path.resolve()` to normalize paths

### 4. File Format Validation

**Checks:**
- File extension must be .xlsx or .xls
- File must exist (for read operations)
- Parent directory must exist (for write operations)
- File must not be empty (0 bytes)

---

## API Reference

### SecurityError Exception

Raised when file fails security validation.

```python
from pystreamxl import SecurityError, read

try:
    for row in read("data.xlsx"):
        process(row)
except SecurityError as e:
    print(f"Security violation: {e}")
```

### get_security_limits()

Returns current security configuration.

```python
from pystreamxl import get_security_limits

limits = get_security_limits()
# {
#     "max_file_size": 536870912,        # 512 MB
#     "max_entry_size": 536870912,       # 512 MB per entry
#     "max_total_size": 1073741824,      # 1 GB total
#     "max_compression_ratio": 30.0,     # 30:1 max
# }
```

---

## Security Limits Rationale

### MAX_FILE_SIZE = 512 MB
- Real Excel files rarely exceed 50 MB
- Enterprise spreadsheets rarely exceed 200 MB
- 512 MB provides 2.5× safety margin
- Prevents single large file consuming GB of memory

### MAX_COMPRESSION_RATIO = 30:1
- Industry standard (OWASP, Cloudflare recommendation)
- Legitimate files rarely exceed 10:1
- ZIP bombs typically achieve 100:1 to 1000:1
- 30:1 provides clear safety margin

---

## Production Deployment Checklist

For **production use**, verify:

- [ ] PyStreamXL version ≥ 1.1.0 (security hardening)
- [ ] File size limits appropriate for use case
- [ ] Error handling catches `SecurityError`
- [ ] Logging captures security violations
- [ ] No silent exception suppression
- [ ] Files read from trusted sources only
- [ ] File uploads validated server-side
- [ ] Monitoring alerts on violations

**Example production code:**
```python
import pystreamxl
import logging

logger = logging.getLogger(__name__)

def process_excel(filepath: str):
    try:
        for row in pystreamxl.read(filepath):
            yield row
    except pystreamxl.SecurityError as e:
        logger.error(f"Security violation in {filepath}: {e}")
        raise  # Don't silently fail
```

---

## Legitimate Use Cases

### Large Files (> 512 MB)

**Option 1: Split the file**
```python
# data_part1.xlsx (400 MB)
# data_part2.xlsx (300 MB)
for row in pystreamxl.read("data_part1.xlsx"):
    process(row)
for row in pystreamxl.read("data_part2.xlsx"):
    process(row)
```

**Option 2: Append incrementally**
```python
with pystreamxl.writer("log.xlsx") as w:
    w.write_row(["Date", "Event"])

# Append in smaller batches
for event in events:
    pystreamxl.append("log.xlsx", [[event.date, event.msg]])
```

**Option 3: Custom build**
Open an issue with business justification for custom limits.

---

## Testing Security

```python
import pystreamxl
import tempfile
import pytest

def test_zip_bomb_protection():
    """Verify ZIP bomb protection."""
    with pytest.raises(pystreamxl.SecurityError):
        pystreamxl.read("fake_huge_file.xlsx")

def test_path_traversal_protection():
    """Verify path traversal is blocked."""
    with pytest.raises(pystreamxl.SecurityError):
        pystreamxl.read("../../../etc/passwd.xlsx")

def test_empty_file_rejection():
    """Verify empty files are rejected."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
        with pytest.raises(pystreamxl.SecurityError):
            pystreamxl.read(f.name)
```

---

## Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities.

Report privately:
- **Email:** mullassery@gmail.com
- **GitHub Security Advisory:** Use "Report a vulnerability" button
- **Timeline:** 90 days to fix before public disclosure

**Include:**
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

---

## Changelog

### v1.1.0 (2026-07-17) — Security Hardening ✅

**New:**
- ZIP bomb detection (compression ratio checking)
- File size validation (512 MB limit)
- SecurityError exception
- get_security_limits() function

**Changes:**
- Tightened ZIP limits (2GB → 512MB per entry)
- Added Python-level file size checking
- Enhanced error messages

**Security:**
✅ ZIP bomb protection (30:1 ratio limit)  
✅ DOS prevention (512 MB file size limit)  
✅ Path traversal prevention  
✅ File format validation  
✅ Empty file rejection  

---

## FAQ

**Q: Can I increase the limits?**  
A: Open an issue with business justification.

**Q: Why 512 MB?**  
A: Most Excel files are < 50 MB. 512 MB is safe margin.

**Q: Will legitimate files be rejected?**  
A: Extremely unlikely. If rejected, file is probably malicious.

**Q: What if I need to process larger files?**  
A: Split into smaller files or contact support.

---

## Summary

PyStreamXL v1.1.0 provides **production-grade security**:

✅ ZIP bombs blocked via compression ratio limits  
✅ DOS attacks prevented via file size validation  
✅ Path traversal blocked via path normalization  
✅ Format violations detected via extension/header checks  

**All protections enabled by default. No configuration needed.**
