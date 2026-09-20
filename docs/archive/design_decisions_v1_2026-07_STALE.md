# Design Decisions

## sharedStrings loaded eagerly

The sharedStrings table is typically small (< 1 MB). Loading it once upfront avoids random access into a streaming ZIP. This is the only full-load in the system.

## sheet1.xml only (MVP)

Multi-sheet support requires parsing `xl/workbook.xml` to map sheet names to file paths. Deferred to post-MVP.

## quick-xml over serde-xml-rs

`quick-xml` is event-driven and zero-copy. `serde-xml-rs` deserializes into structs — overkill for streaming rows and adds allocations.

## maturin over setuptools-rust

Maturin handles wheel building, cross-compilation, and PyPI upload with minimal config. It's the community standard for PyO3 projects.
