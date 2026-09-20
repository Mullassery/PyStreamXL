# Architecture

Streamxl is a two-layer system:

```
Python caller
     │
     ▼
python/streamxl/api.py   ← public Python API
     │
     ▼
python/bindings.rs        ← PyO3 bridge
     │
     ▼
core/src/stream.rs        ← XlsxStream: orchestrates zip + parsing
     ├── zip_reader.rs    ← wraps the `zip` crate for entry access
     ├── shared_strings.rs← parses xl/sharedStrings.xml into Vec<String>
     └── sheet_parser.rs  ← streams rows from xl/worksheets/sheet1.xml
```

## Data flow

1. `XlsxStream::open(path)` opens the ZIP, reads sharedStrings into memory (small).
2. `stream.rows()` returns an iterator — each `.next()` parses exactly one `<row>` element.
3. Cell values referencing shared strings are resolved via index lookup.
4. PyO3 converts each Rust `Vec<CellValue>` to a Python `list` on demand.

## Why Rust?

- ZIP + XML parsing in Python is slow and allocates heavily
- Rust's `zip` + `quick-xml` operate without GC pressure
- PyO3 gives near-zero-cost FFI for iterator protocols
