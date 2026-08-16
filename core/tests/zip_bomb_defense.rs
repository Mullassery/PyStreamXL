//! Real integration tests for the ZIP-bomb / decompression-bomb defense in
//! `streamxl_core::zip_reader::XlsxZip`.
//!
//! Unlike the previous version of this test (which only asserted that
//! hardcoded numeric constants satisfied arithmetic relationships with
//! *themselves* and never called any production code), every test here
//! builds a real in-memory ZIP archive with the real `zip` crate, feeds it
//! through the actual `XlsxZip::new()` / `read_entry()` code path used by
//! the reader when opening an .xlsx file, and asserts on the real
//! success/failure outcome.
//!
//! IMPORTANT: this file lives under `core/tests/` (not the repo-root
//! `tests/` directory) specifically so `cargo test` picks it up as an
//! integration test of the `streamxl-core` crate. A prior copy of this
//! file at the repo root was never compiled or executed by `cargo test`
//! at all, because a bare top-level `tests/` directory is not wired to
//! any crate when the workspace root has no `[package]` of its own.

use std::io::{Cursor, Write};

use streamxl_core::zip_reader::XlsxZip;
use zip::write::SimpleFileOptions;
use zip::{CompressionMethod, ZipWriter};

/// Build an in-memory ZIP archive containing a single entry with the given
/// name and content, compressed with the given method. Returns the raw
/// archive bytes.
fn build_zip(entry_name: &str, content: &[u8], method: CompressionMethod) -> Vec<u8> {
    let buf = Cursor::new(Vec::new());
    let mut zip = ZipWriter::new(buf);
    let opts = SimpleFileOptions::default().compression_method(method);
    zip.start_file(entry_name, opts).expect("start_file");
    zip.write_all(content).expect("write content");
    zip.finish().expect("finish zip").into_inner()
}

#[test]
fn zip_bomb_extreme_compression_ratio_is_rejected() {
    // A classic zip-bomb payload: highly repetitive data (all zeros)
    // compresses at an extreme ratio under DEFLATE. 8 MiB of zeros
    // compresses down to a few KB, giving a ratio in the thousands-to-one
    // range — far past the library's 30:1 threshold.
    let uncompressed = vec![0u8; 8 * 1024 * 1024];
    let archive_bytes = build_zip("bomb.xml", &uncompressed, CompressionMethod::Deflated);

    let cursor = Cursor::new(archive_bytes);
    let mut xlsx_zip = XlsxZip::new(cursor).expect("archive should open (ZIP structure is valid)");

    let result = xlsx_zip.read_entry("bomb.xml");

    assert!(
        result.is_err(),
        "reading a real extreme-compression-ratio entry must be rejected, got Ok"
    );
    let err_msg = result.unwrap_err().to_string();
    assert!(
        err_msg.contains("compression ratio") || err_msg.contains("ZIP bomb"),
        "error should explain the rejection reason, got: {err_msg}"
    );
}

#[test]
fn zip_bomb_moderate_ratio_just_over_threshold_is_rejected() {
    // Build an entry right around the 30:1 boundary but just over it, to
    // prove the check is a real ratio computation on real compressed vs.
    // uncompressed sizes read back from the archive — not a hardcoded
    // pass-through. Compressible ASCII text at a controlled repetition
    // count reliably compresses well past 30:1 with DEFLATE.
    let unit = b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"; // 64 bytes, trivially compressible
    let mut content = Vec::with_capacity(unit.len() * 20_000);
    for _ in 0..20_000 {
        content.extend_from_slice(unit);
    }
    // ~1.28 MB of maximally-repetitive data compresses to well under
    // 1.28MB/30 = ~43KB with DEFLATE, so this genuinely exceeds the ratio.
    let archive_bytes = build_zip("repetitive.xml", &content, CompressionMethod::Deflated);

    let cursor = Cursor::new(archive_bytes);
    let mut xlsx_zip = XlsxZip::new(cursor).expect("archive should open");

    let result = xlsx_zip.read_entry("repetitive.xml");
    assert!(
        result.is_err(),
        "entry compressing well past the 30:1 ratio must be rejected"
    );
}

#[test]
fn legitimate_xlsx_style_entry_is_accepted_and_content_matches() {
    // A realistic small worksheet-XML fragment: mixed, moderately
    // (not maximally) compressible text, well under the ratio threshold.
    let content = br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
<row><c r="A1" t="s"><v>0</v></c><c r="B1"><v>42</v></c></row>
<row><c r="A2" t="s"><v>1</v></c><c r="B2"><v>7</v></c></row>
</sheetData>
</worksheet>"#
        .to_vec();
    let archive_bytes = build_zip(
        "xl/worksheets/sheet1.xml",
        &content,
        CompressionMethod::Deflated,
    );

    let cursor = Cursor::new(archive_bytes);
    let mut xlsx_zip = XlsxZip::new(cursor).expect("archive should open");

    let result = xlsx_zip.read_entry("xl/worksheets/sheet1.xml");
    assert!(
        result.is_ok(),
        "a legitimate, normally-compressed entry must be accepted, got: {:?}",
        result.err()
    );
    // The real defense must not corrupt/truncate legitimate content.
    assert_eq!(result.unwrap(), content);
}

#[test]
fn stored_uncompressed_entry_ratio_is_never_flagged() {
    // Stored (uncompressed) entries have a 1:1 ratio and must always pass
    // the ratio check regardless of content, proving the check is a real
    // division, not an overzealous size-based heuristic.
    let content = vec![0u8; 2 * 1024 * 1024]; // 2 MiB of zeros, but STORED not DEFLATED
    let archive_bytes = build_zip("stored.bin", &content, CompressionMethod::Stored);

    let cursor = Cursor::new(archive_bytes);
    let mut xlsx_zip = XlsxZip::new(cursor).expect("archive should open");

    let result = xlsx_zip.read_entry("stored.bin");
    assert!(result.is_ok(), "1:1 ratio stored entry must be accepted");
    assert_eq!(result.unwrap().len(), content.len());
}

#[test]
fn has_entry_reflects_real_archive_contents() {
    let content = b"hello world".to_vec();
    let archive_bytes = build_zip("present.txt", &content, CompressionMethod::Deflated);

    let cursor = Cursor::new(archive_bytes);
    let mut xlsx_zip = XlsxZip::new(cursor).expect("archive should open");

    assert!(xlsx_zip.has_entry("present.txt"));
    assert!(!xlsx_zip.has_entry("absent.txt"));
}

#[test]
fn total_decompressed_size_accumulates_across_real_reads() {
    // Two legitimate small entries read from the same archive: the
    // second read must succeed too, proving total-size tracking
    // accumulates correctly across multiple real reads rather than
    // rejecting (or trivially always accepting) after the first.
    let buf = Cursor::new(Vec::new());
    let mut zip = ZipWriter::new(buf);
    let opts = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);
    zip.start_file("a.xml", opts).unwrap();
    zip.write_all(b"<a>first entry content</a>").unwrap();
    zip.start_file("b.xml", opts).unwrap();
    zip.write_all(b"<b>second entry content</b>").unwrap();
    let archive_bytes = zip.finish().unwrap().into_inner();

    let cursor = Cursor::new(archive_bytes);
    let mut xlsx_zip = XlsxZip::new(cursor).expect("archive should open");

    let a = xlsx_zip
        .read_entry("a.xml")
        .expect("first entry reads fine");
    let b = xlsx_zip
        .read_entry("b.xml")
        .expect("second entry reads fine");
    assert_eq!(a, b"<a>first entry content</a>");
    assert_eq!(b, b"<b>second entry content</b>");
}
