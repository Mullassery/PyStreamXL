# PyStreamXL Security & Hardening Guide

This document describes the security-relevant behavior of the current
codebase (last checked against v5.3.0). It is not versioned separately
from the package — read it against whatever version you have installed,
and verify against `python/streamxl/security.py` and
`core/src/zip_reader.rs` if it matters for your use case.

## Executive Summary

PyStreamXL includes hardening against:
- **ZIP bomb attacks** (decompression bombs)
- **Denial-of-service (DOS) attacks** via resource exhaustion (oversized files/entries)
- **File format violations**

Path-traversal confinement is available but **opt-in** — see "Path
Handling" below; by default (no `base_dir` passed) any resolved path is
still accepted, same as always.

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

### 3. Path Handling — confinement is real, but opt-in via `base_dir`

**History:** until this fix, `validate_xlsx_path()` resolved the path with
`Path(path).resolve()` and *then* checked for the literal substring `".."`.
`resolve()` collapses `..` segments as part of normalizing the path, so by
the time the check ran, a traversal input like `"../../../etc/passwd.xlsx"`
had already become an absolute path (`/etc/passwd.xlsx`) with no literal
`".."` left in it — the check could never fire on a real traversal attempt
and was dead code. A call like `read("../../../etc/passwd.xlsx")` still
raised `SecurityError`, but only because `/etc/passwd.xlsx` didn't exist or
wasn't a `.xlsx`/`.xls` file — not because traversal was detected.

**What's fixed now (`python/streamxl/security.py`):**
`validate_xlsx_path()`, `validate_read_path()`, and `validate_write_path()`
all accept an optional `base_dir` argument. When passed, the path is
resolved (`Path(path).resolve()`, which also collapses `..` and symlinks)
and then the *resolved* path is checked with `os.path.commonpath([path,
base_dir]) == base_dir` — a real, working confinement check performed
after normalization instead of a dead substring check performed too late
to matter:

```python
from streamxl.security import validate_read_path, SecurityError

try:
    validate_read_path(user_supplied_path, base_dir="/var/app/uploads")
except SecurityError:
    ...  # traversal attempt or path outside the allowed directory
```

**This is opt-in, not automatic:** when `base_dir` is omitted (the
default), no confinement is enforced and any resolved path is accepted —
same behavior as every prior release. This library is used both as a
general-purpose file-path API (arbitrary absolute paths anywhere on disk
are a legitimate, existing use case — see `python/streamxl/api.py`) and
potentially embedded in services with a real trust boundary (e.g. a
multi-tenant upload handler). Those are different confinement contracts,
so the check is available but must be deliberately opted into by callers
that have an actual base directory to enforce; `streamxl.read()`/`write()`
and the bundled `StreamXLServer` do not pass `base_dir` today. If you're
embedding this in a service that accepts user-supplied paths, call
`validate_read_path()`/`validate_write_path()` yourself with `base_dir` set
to your trust boundary before opening the file.

**What is real:**
- File extension is validated (`.xlsx`/`.xls` only)
- The path is normalized via `Path.resolve()`
- The resolved file must exist and actually be a file (for reads)
- With `base_dir` passed, the resolved path is verified to actually be
  inside that directory (see above); see `tests/test_security.py` for
  tests that perform real traversal attempts and confirm rejection.

### 4. File Format Validation

**Checks:**
- File extension must be .xlsx or .xls
- File must exist (for read operations)
- Parent directory must exist (for write operations)
- File must not be empty (0 bytes)

### 5. Write-Side Memory & Size Limits (added v5.3.0)

**What it protects against:** Prior to v5.3.0, the write path had no
counterpart to the read-side protections above — `XlsxWriter` buffered an
entire worksheet's XML in memory (`Vec<u8>`) and only flushed to the ZIP
archive once, in `finish()`, so peak memory scaled linearly with rows
written and there was no cap on how large a single sheet or workbook could
grow.

**PyStreamXL Protection (`core/src/writer.rs`):**
```rust
FLUSH_THRESHOLD = 4 MB    // buffered XML flushed to the ZIP stream once this is exceeded
MAX_ENTRY_SIZE  = 512 MB  // per worksheet, mirrors the read-side limit
MAX_TOTAL_SIZE  = 1 GB    // across the whole workbook, mirrors the read-side limit
```

**How it works:**
1. Worksheet XML is flushed to the underlying ZIP stream every `FLUSH_THRESHOLD`
   bytes instead of only at `finish()`, keeping peak memory roughly constant
   relative to sheet size rather than linear in row count.
2. Per-sheet and total-workbook size are checked as data is flushed —
   writing fails fast with a clear error the moment either limit would be
   exceeded, instead of allowing unbounded growth.

---

## API Reference

### SecurityError Exception

Raised when file fails security validation.

```python
from streamxl import SecurityError, read

try:
    for row in read("data.xlsx"):
        process(row)
except SecurityError as e:
    print(f"Security violation: {e}")
```

### get_security_limits()

Returns current security configuration.

```python
from streamxl import get_security_limits

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

## Deployment Checklist

Before relying on this in a service that accepts file paths or uploads
from outside callers, verify:

- [ ] File size limits appropriate for use case
- [ ] Error handling catches `SecurityError`
- [ ] Logging captures security violations
- [ ] No silent exception suppression
- [ ] Files read from trusted sources only
- [ ] File uploads validated server-side, **including your own
      base-directory confinement** — see the "Path Handling" note above;
      this library does not provide that
- [ ] Monitoring alerts on violations

**Example code:**
```python
import streamxl
import logging

logger = logging.getLogger(__name__)

def process_excel(filepath: str):
    try:
        for row in streamxl.read(filepath):
            yield row
    except streamxl.SecurityError as e:
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
for row in streamxl.read("data_part1.xlsx"):
    process(row)
for row in streamxl.read("data_part2.xlsx"):
    process(row)
```

**Option 2: Append incrementally**
```python
with streamxl.writer("log.xlsx") as w:
    w.write_row(["Date", "Event"])

# Append in smaller batches
for event in events:
    streamxl.append("log.xlsx", [[event.date, event.msg]])
```

**Option 3: Custom build**
Open an issue with business justification for custom limits.

---

## Testing Security

```python
import streamxl
import tempfile
import pytest

def test_zip_bomb_protection():
    """Verify ZIP bomb protection."""
    with pytest.raises(streamxl.SecurityError):
        streamxl.read("fake_huge_file.xlsx")

def test_nonexistent_or_wrong_extension_path_raises():
    """A path that doesn't resolve to a real .xlsx/.xls file raises
    SecurityError — but note this is existence/extension validation,
    not path-traversal confinement (see "Path Handling" above)."""
    with pytest.raises(streamxl.SecurityError):
        streamxl.read("../../../etc/passwd.xlsx")

def test_empty_file_rejection():
    """Verify empty files are rejected."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
        with pytest.raises(streamxl.SecurityError):
            streamxl.read(f.name)
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

Security-relevant changes are tracked in `CHANGELOG.md`. As of this
writing: ZIP-bomb defenses and file-size limits are read-side (present
since early releases); write-side bounded buffering/size caps were added
in v5.3.0 (see the "Write-Side Memory & Size Limits" section above).

---

## FAQ

**Q: Can I increase the limits?**  
A: Open an issue with business justification.

**Q: Why 512 MB?**  
A: Most Excel files are < 50 MB. 512 MB is safe margin.

**Q: Will legitimate files be rejected?**  
A: Extremely unlikely. If rejected, file is probably malicious.

**Q: What if I need to process larger files?**  
A: Split into smaller files, or open an issue describing your use case.

---

## Summary

What's real and enabled by default, no configuration needed:

- ZIP bombs blocked via compression-ratio, per-entry, and total-decompressed-size limits (read and write)
- Oversized files rejected via a file-size check before parsing
- File extension and basic format validated
- Empty files rejected
- CSV/formula-injection sanitization available via `streamxl.security.sanitize_csv_cell()` (opt-in for your own CSV writes; automatic in `FormulaSerializer.export_to_csv()`)

What's **not** real, despite being implied by earlier drafts of this
document: this library does not sandbox/confine file paths to a base
directory (see "Path Handling" above) — that responsibility is the
caller's if paths come from an untrusted source.
