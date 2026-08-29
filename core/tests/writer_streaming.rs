//! Integration tests for the streaming/bounded-memory behavior of
//! `streamxl_core::writer::XlsxWriter`.
//!
//! These tests exercise the real write path end-to-end: rows are written
//! through the public `XlsxWriter` API, the resulting file is read back
//! through the real `XlsxStream` reader, and the internal flush bookkeeping
//! (`flush_count` / `buffered_len`) is used as direct evidence that the
//! in-memory XML buffer is flushed periodically in bounded-size chunks
//! rather than being held in full until `finish()`.

use streamxl_core::sheet_parser::CellValue;
use streamxl_core::stream::XlsxStream;
use streamxl_core::writer::{WriteCell, XlsxWriter, FLUSH_THRESHOLD};

fn temp_path(name: &str) -> std::path::PathBuf {
    let mut p = std::env::temp_dir();
    let pid = std::process::id();
    p.push(format!("streamxl_writer_test_{pid}_{name}.xlsx"));
    p
}

/// Writing a large number of rows must still produce a valid, readable
/// .xlsx file: every row round-trips through write -> read with matching
/// content, and (separately) the writer must have flushed its buffer
/// multiple times along the way rather than only once at `finish()`.
/// Builds a row wide enough (several numeric columns) that per-row XML size
/// is substantial, so a moderate row count reliably crosses FLUSH_THRESHOLD
/// several times over. (Note: string cells are deduplicated into the shared
/// string table and only contribute a small integer index to the row XML
/// itself, so we lean on numeric columns to control row XML size.)
fn wide_row(i: usize) -> Vec<WriteCell> {
    let mut cells = vec![WriteCell::Str(format!("row{i}"))];
    for j in 0..8 {
        cells.push(WriteCell::Num((i * 10 + j) as f64));
    }
    cells.push(WriteCell::Bool(i % 2 == 0));
    cells
}

#[test]
fn large_row_count_round_trips_and_flushes_incrementally() {
    let path = temp_path("roundtrip");
    let n_rows: usize = 250_000;

    let mut writer = XlsxWriter::new(&path).expect("create writer");
    for i in 0..n_rows {
        writer.write_row(&wide_row(i), false).expect("write_row");
    }

    // The whole point of the fix: by the time we're done writing rows
    // (before finish() is ever called), the buffer must already have been
    // flushed to the underlying ZIP stream many times over. A buffer that
    // only ever flushes once, at finish(), would leave flush_count() at 0
    // here since finish() hasn't run yet.
    let flush_count_before_finish = writer.flush_count();
    assert!(
        flush_count_before_finish > 10,
        "expected many incremental flushes while writing {n_rows} rows, got {flush_count_before_finish}"
    );

    // The buffered-but-not-yet-flushed XML must stay bounded near
    // FLUSH_THRESHOLD, not grow to hold the whole sheet.
    let buffered = writer.buffered_len();
    assert!(
        buffered < FLUSH_THRESHOLD * 2,
        "buffered_len() ({buffered}) grew well past FLUSH_THRESHOLD ({FLUSH_THRESHOLD}); \
         the writer appears to be accumulating the whole sheet instead of streaming it"
    );

    writer.finish().expect("finish");

    // Round-trip: read the file back for real and check row count/content.
    let stream = XlsxStream::open(&path, None).expect("open written file");
    let rows: Vec<Vec<CellValue>> = stream
        .rows()
        .collect::<Result<Vec<_>, _>>()
        .expect("all rows parse cleanly");

    assert_eq!(rows.len(), n_rows, "row count mismatch after round-trip");

    // Spot-check first, middle, and last rows for content correctness.
    for &i in &[0usize, n_rows / 2, n_rows - 1] {
        let row = &rows[i];
        match &row[0] {
            CellValue::String(s) => assert_eq!(s, &format!("row{i}")),
            other => panic!("row {i} cell 0: expected String, got {other:?}"),
        }
        match &row[1] {
            CellValue::Number(n) => assert_eq!(*n, (i * 10) as f64),
            other => panic!("row {i} cell 1: expected Number, got {other:?}"),
        }
        match &row[9] {
            CellValue::Bool(b) => assert_eq!(*b, i % 2 == 0),
            other => panic!("row {i} cell 9: expected Bool, got {other:?}"),
        }
    }

    let _ = std::fs::remove_file(&path);
}

/// Flushing must be proportional to the amount of data written (periodic
/// chunking), not a fixed one-shot event. Writing 10x more rows should
/// trigger roughly 10x more flushes, which could never happen under the
/// old "buffer everything, flush once in finish()" design (that design
/// would show flush_count() staying at 0 mid-write regardless of row
/// count, since nothing is flushed until finish() runs).
#[test]
fn flush_count_scales_with_rows_written_not_fixed() {
    let small_path = temp_path("small");
    let mut small_writer = XlsxWriter::new(&small_path).expect("create writer");
    for i in 0..30_000 {
        small_writer.write_row(&wide_row(i), false).expect("write_row");
    }
    let small_flushes = small_writer.flush_count();
    small_writer.finish().expect("finish");

    let large_path = temp_path("large");
    let mut large_writer = XlsxWriter::new(&large_path).expect("create writer");
    for i in 0..300_000 {
        large_writer.write_row(&wide_row(i), false).expect("write_row");
    }
    let large_flushes = large_writer.flush_count();
    large_writer.finish().expect("finish");

    assert!(
        small_flushes > 0,
        "expected at least one mid-write flush for the smaller file"
    );
    assert!(
        large_flushes > small_flushes * 3,
        "flush count should scale with data volume: small={small_flushes}, large={large_flushes}"
    );

    let _ = std::fs::remove_file(&small_path);
    let _ = std::fs::remove_file(&large_path);
}

/// Multi-sheet workbooks must also stream: switching sheets flushes and
/// resets the per-sheet buffer/counter rather than retaining every
/// previous sheet's full XML in memory until finish().
#[test]
fn multi_sheet_round_trip_with_streaming() {
    let path = temp_path("multisheet");
    let mut writer = XlsxWriter::new(&path).expect("create writer");

    for i in 0..5_000 {
        writer
            .write_row(&[WriteCell::Str(format!("s1-{i}"))], false)
            .expect("write_row sheet1");
    }
    writer.add_sheet("Sheet2").expect("add_sheet");
    for i in 0..5_000 {
        writer
            .write_row(&[WriteCell::Str(format!("s2-{i}"))], false)
            .expect("write_row sheet2");
    }
    writer.finish().expect("finish");

    let names = XlsxStream::sheet_names(&path).expect("sheet names");
    assert_eq!(names, vec!["Sheet1".to_string(), "Sheet2".to_string()]);

    let sheet1 = XlsxStream::open(&path, Some("Sheet1")).expect("open sheet1");
    let rows1: Vec<_> = sheet1.rows().collect::<Result<Vec<_>, _>>().unwrap();
    assert_eq!(rows1.len(), 5_000);

    let sheet2 = XlsxStream::open(&path, Some("Sheet2")).expect("open sheet2");
    let rows2: Vec<_> = sheet2.rows().collect::<Result<Vec<_>, _>>().unwrap();
    assert_eq!(rows2.len(), 5_000);

    let _ = std::fs::remove_file(&path);
}
