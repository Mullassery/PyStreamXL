use std::collections::HashMap;
use std::fmt;
use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};
use zip::write::SimpleFileOptions;
use zip::ZipWriter;

// SECURITY: Limits to bound memory/disk growth on the write path, mirroring
// the read-side protections in `zip_reader.rs` (MAX_ENTRY_SIZE / MAX_TOTAL_SIZE).
//
// Without these, a caller feeding an unbounded row iterator (or a hostile
// caller deliberately trying to exhaust memory/disk) could grow a single
// worksheet's XML buffer, or the workbook as a whole, without limit before
// `finish()` is ever reached.

/// Bytes of buffered worksheet XML we accumulate in memory before flushing
/// to the underlying ZIP stream. Keeps peak memory roughly constant instead
/// of growing linearly with the number of rows written.
pub const FLUSH_THRESHOLD: usize = 4 * 1024 * 1024; // 4MB

/// Maximum uncompressed size of a single worksheet's XML. Mirrors
/// `zip_reader::MAX_ENTRY_SIZE` so nothing we write here would be rejected
/// as an oversized entry if it were read back.
pub const MAX_ENTRY_SIZE: u64 = 512 * 1024 * 1024; // 512MB per sheet

/// Maximum cumulative uncompressed size of worksheet XML across the whole
/// workbook. Mirrors `zip_reader::MAX_TOTAL_SIZE`.
pub const MAX_TOTAL_SIZE: u64 = 1024 * 1024 * 1024; // 1GB total

/// Errors that can occur while writing an XLSX file.
#[derive(Debug)]
pub enum WriterError {
    /// A single worksheet's XML grew beyond [`MAX_ENTRY_SIZE`].
    EntryTooLarge {
        sheet: String,
        size: u64,
        limit: u64,
    },
    /// Cumulative worksheet XML size across the workbook would exceed
    /// [`MAX_TOTAL_SIZE`].
    TotalTooLarge { size: u64, limit: u64 },
    /// Underlying I/O error (disk full, permission denied, etc).
    Io(std::io::Error),
    /// Underlying ZIP-format error.
    Zip(zip::result::ZipError),
}

impl fmt::Display for WriterError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WriterError::EntryTooLarge { sheet, size, limit } => write!(
                f,
                "worksheet '{sheet}' XML exceeds size limit: {size} > {limit} bytes"
            ),
            WriterError::TotalTooLarge { size, limit } => write!(
                f,
                "total worksheet XML size would exceed limit: {size} > {limit} bytes"
            ),
            WriterError::Io(e) => write!(f, "I/O error writing XLSX: {e}"),
            WriterError::Zip(e) => write!(f, "ZIP error writing XLSX: {e}"),
        }
    }
}

impl std::error::Error for WriterError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            WriterError::Io(e) => Some(e),
            WriterError::Zip(e) => Some(e),
            _ => None,
        }
    }
}

impl From<std::io::Error> for WriterError {
    fn from(e: std::io::Error) -> Self {
        WriterError::Io(e)
    }
}

impl From<zip::result::ZipError> for WriterError {
    fn from(e: zip::result::ZipError) -> Self {
        WriterError::Zip(e)
    }
}

pub enum WriteCell {
    Str(String),
    Num(f64),
    Bool(bool),
    Date(u32),     // Excel serial date (days, integer)
    DateTime(f64), // Excel serial datetime (days + fractional time)
    Empty,
}

/// Streaming XLSX writer.
///
/// Worksheet XML is written directly to the underlying ZIP stream in
/// bounded-size chunks (see [`FLUSH_THRESHOLD`]) as rows come in, rather
/// than being buffered in full and written once in [`XlsxWriter::finish`].
/// This keeps peak memory roughly constant relative to sheet size. Size
/// limits (mirroring the read-side ZIP-bomb defenses in `zip_reader.rs`)
/// are enforced as data is flushed so a runaway caller fails fast with a
/// clear error instead of exhausting memory or disk.
pub struct XlsxWriter {
    zip: ZipWriter<File>,
    opts: SimpleFileOptions,
    output_path: PathBuf,
    // Names of all sheets started so far, in order (including the current one).
    sheet_names: Vec<String>,
    // XML buffered for the sheet currently being written, not yet flushed.
    current_buf: Vec<u8>,
    // Uncompressed bytes already flushed to the ZIP stream for the current sheet.
    current_sheet_flushed: u64,
    // Uncompressed bytes already flushed to the ZIP stream across all sheets.
    total_flushed: u64,
    // Number of times `current_buf` has been flushed. Exposed for tests /
    // diagnostics to confirm streaming (bounded-memory) behavior rather than
    // a single flush-everything-at-finish() pattern.
    flush_count: usize,
    // Shared string table across all sheets
    sst: Vec<String>,
    sst_index: HashMap<String, usize>,
}

fn sheet_header() -> Vec<u8> {
    let mut buf = Vec::with_capacity(64 * 1024);
    buf.extend_from_slice(
        b"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">\
\n<sheetData>\n",
    );
    buf
}

impl XlsxWriter {
    pub fn new(path: impl AsRef<Path>) -> Result<Self, WriterError> {
        let output_path = path.as_ref().to_path_buf();
        let file = File::create(&output_path)?;
        let mut zip = ZipWriter::new(file);
        let opts =
            SimpleFileOptions::default().compression_method(zip::CompressionMethod::Deflated);

        // Open the first worksheet entry immediately so rows can stream
        // straight into it instead of accumulating in memory.
        zip.start_file("xl/worksheets/sheet1.xml", opts)?;

        Ok(Self {
            zip,
            opts,
            output_path,
            sheet_names: vec!["Sheet1".to_string()],
            current_buf: sheet_header(),
            current_sheet_flushed: 0,
            total_flushed: 0,
            flush_count: 0,
            sst: Vec::new(),
            sst_index: HashMap::new(),
        })
    }

    /// Number of times the internal buffer has been flushed to the ZIP
    /// stream so far. Useful for tests/diagnostics confirming that memory
    /// use is bounded rather than growing until `finish()`.
    pub fn flush_count(&self) -> usize {
        self.flush_count
    }

    /// Current size (bytes) of the not-yet-flushed XML buffer for the
    /// in-progress sheet. Exposed for tests/diagnostics: this should stay
    /// bounded around [`FLUSH_THRESHOLD`] no matter how many rows have been
    /// written, proving memory use doesn't grow linearly with row count.
    pub fn buffered_len(&self) -> usize {
        self.current_buf.len()
    }

    /// Flush any buffered XML for the current sheet to the underlying ZIP
    /// stream, enforcing the entry/total size limits as we go.
    fn flush_current(&mut self) -> Result<(), WriterError> {
        if self.current_buf.is_empty() {
            return Ok(());
        }
        let len = self.current_buf.len() as u64;

        let new_sheet_total = self.current_sheet_flushed.saturating_add(len);
        if new_sheet_total > MAX_ENTRY_SIZE {
            return Err(WriterError::EntryTooLarge {
                sheet: self
                    .sheet_names
                    .last()
                    .cloned()
                    .unwrap_or_else(|| "<unknown>".to_string()),
                size: new_sheet_total,
                limit: MAX_ENTRY_SIZE,
            });
        }

        let new_total = self.total_flushed.saturating_add(len);
        if new_total > MAX_TOTAL_SIZE {
            return Err(WriterError::TotalTooLarge {
                size: new_total,
                limit: MAX_TOTAL_SIZE,
            });
        }

        self.zip.write_all(&self.current_buf)?;
        self.current_buf.clear();
        self.current_sheet_flushed = new_sheet_total;
        self.total_flushed = new_total;
        self.flush_count += 1;
        Ok(())
    }

    /// Finalise the current sheet and start a new one with the given name.
    pub fn add_sheet(&mut self, name: &str) -> Result<(), WriterError> {
        self.current_buf
            .extend_from_slice(b"</sheetData>\n</worksheet>");
        self.flush_current()?;

        let next_index = self.sheet_names.len() + 1;
        self.zip
            .start_file(format!("xl/worksheets/sheet{next_index}.xml"), self.opts)?;

        self.sheet_names.push(name.to_string());
        self.current_buf = sheet_header();
        self.current_sheet_flushed = 0;
        Ok(())
    }

    /// Write a row. `bold=true` applies bold font to every cell in the row.
    ///
    /// Flushes the buffered XML to the underlying ZIP stream whenever it
    /// grows past [`FLUSH_THRESHOLD`], so memory use stays roughly constant
    /// no matter how many rows are written. Returns an error (without
    /// panicking or silently truncating) if the configured size limits
    /// would be exceeded.
    pub fn write_row(&mut self, cells: &[WriteCell], bold: bool) -> Result<(), WriterError> {
        self.current_buf.extend_from_slice(b"<row>");
        for cell in cells {
            // xf index: 0=default, 1=date, 2=datetime, 3=bold, 4=bold-date, 5=bold-datetime
            let xf: Option<u8> = match (cell, bold) {
                (WriteCell::Date(_), false) => Some(1),
                (WriteCell::DateTime(_), false) => Some(2),
                (WriteCell::Empty, _) => None,
                (WriteCell::Date(_), true) => Some(4),
                (WriteCell::DateTime(_), true) => Some(5),
                (_, true) => Some(3),
                _ => None,
            };
            let s_attr: std::borrow::Cow<str> = match xf {
                Some(n) => format!(" s=\"{n}\"").into(),
                None => "".into(),
            };
            match cell {
                WriteCell::Str(s) => {
                    let idx = match self.sst_index.get(s) {
                        Some(&i) => i,
                        None => {
                            let i = self.sst.len();
                            self.sst.push(s.clone());
                            self.sst_index.insert(s.clone(), i);
                            i
                        }
                    };
                    write!(self.current_buf, "<c t=\"s\"{s_attr}><v>{idx}</v></c>").unwrap();
                }
                WriteCell::Num(n) => {
                    write!(self.current_buf, "<c{s_attr}><v>{n}</v></c>").unwrap();
                }
                WriteCell::Bool(b) => {
                    let v = if *b { 1u8 } else { 0u8 };
                    write!(self.current_buf, "<c t=\"b\"{s_attr}><v>{v}</v></c>").unwrap();
                }
                WriteCell::Date(serial) => {
                    write!(self.current_buf, "<c{s_attr}><v>{serial}</v></c>").unwrap();
                }
                WriteCell::DateTime(serial) => {
                    write!(self.current_buf, "<c{s_attr}><v>{serial}</v></c>").unwrap();
                }
                WriteCell::Empty => {
                    self.current_buf.extend_from_slice(b"<c/>");
                }
            }
        }
        self.current_buf.extend_from_slice(b"</row>\n");

        if self.current_buf.len() >= FLUSH_THRESHOLD {
            self.flush_current()?;
        }
        Ok(())
    }

    pub fn finish(mut self) -> Result<(), WriterError> {
        // Finalise and flush the last sheet.
        self.current_buf
            .extend_from_slice(b"</sheetData>\n</worksheet>");
        self.flush_current()?;

        let n_sheets = self.sheet_names.len();
        let has_sst = !self.sst.is_empty();
        let opts = self.opts;

        // Starting a new entry implicitly finishes the previously-open
        // worksheet entry, so this safely closes out the last sheet.
        self.zip.start_file("[Content_Types].xml", opts)?;
        self.zip
            .write_all(build_content_types(n_sheets, has_sst).as_bytes())?;

        self.zip.start_file("_rels/.rels", opts)?;
        self.zip.write_all(RELS_XML)?;

        self.zip.start_file("xl/workbook.xml", opts)?;
        self.zip
            .write_all(build_workbook_xml(&self.sheet_names).as_bytes())?;

        self.zip.start_file("xl/_rels/workbook.xml.rels", opts)?;
        self.zip
            .write_all(build_workbook_rels(n_sheets, has_sst).as_bytes())?;

        self.zip.start_file("xl/styles.xml", opts)?;
        self.zip.write_all(STYLES_XML)?;

        if has_sst {
            self.zip.start_file("xl/sharedStrings.xml", opts)?;
            self.zip.write_all(build_sst(&self.sst).as_bytes())?;
        }

        self.zip.finish()?;
        Ok(())
    }

    /// Path this writer will produce output at. Exposed mainly for tests.
    pub fn output_path(&self) -> &Path {
        &self.output_path
    }
}

// ── XML builders ──────────────────────────────────────────────────────────────

fn build_content_types(n_sheets: usize, has_sst: bool) -> String {
    let mut xml = String::from(
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\
\n<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\
\n<Default Extension=\"xml\" ContentType=\"application/xml\"/>\
\n<Override PartName=\"/xl/workbook.xml\" \
ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>\n",
    );
    for i in 1..=n_sheets {
        xml.push_str(&format!(
            "<Override PartName=\"/xl/worksheets/sheet{i}.xml\" \
ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>\n"
        ));
    }
    xml.push_str(
        "<Override PartName=\"/xl/styles.xml\" \
ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>\n",
    );
    if has_sst {
        xml.push_str(
            "<Override PartName=\"/xl/sharedStrings.xml\" \
ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml\"/>\n",
        );
    }
    xml.push_str("</Types>");
    xml
}

fn build_workbook_xml(sheet_names: &[String]) -> String {
    let mut xml = String::from(
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" \
xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">\
\n<sheets>\n",
    );
    for (i, name) in sheet_names.iter().enumerate() {
        let escaped = name
            .replace('&', "&amp;")
            .replace('<', "&lt;")
            .replace('>', "&gt;")
            .replace('"', "&quot;");
        xml.push_str(&format!(
            "<sheet name=\"{escaped}\" sheetId=\"{sid}\" r:id=\"rId{rid}\"/>\n",
            sid = i + 1,
            rid = i + 1,
        ));
    }
    xml.push_str("</sheets>\n</workbook>");
    xml
}

fn build_workbook_rels(n_sheets: usize, has_sst: bool) -> String {
    let mut xml = String::from(
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\n",
    );
    for i in 1..=n_sheets {
        xml.push_str(&format!(
            "<Relationship Id=\"rId{i}\" \
Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" \
Target=\"worksheets/sheet{i}.xml\"/>\n"
        ));
    }
    xml.push_str(&format!(
        "<Relationship Id=\"rId{styles_id}\" \
Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" \
Target=\"styles.xml\"/>\n",
        styles_id = n_sheets + 1,
    ));
    if has_sst {
        xml.push_str(&format!(
            "<Relationship Id=\"rId{sst_id}\" \
Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings\" \
Target=\"sharedStrings.xml\"/>\n",
            sst_id = n_sheets + 2,
        ));
    }
    xml.push_str("</Relationships>");
    xml
}

fn build_sst(strings: &[String]) -> String {
    let count = strings.len();
    let mut out = format!(
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<sst xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" \
count=\"{count}\" uniqueCount=\"{count}\">\n"
    );
    for s in strings {
        let escaped = s
            .replace('&', "&amp;")
            .replace('<', "&lt;")
            .replace('>', "&gt;")
            .replace('"', "&quot;");
        out.push_str("<si><t>");
        out.push_str(&escaped);
        out.push_str("</t></si>\n");
    }
    out.push_str("</sst>");
    out
}

const RELS_XML: &[u8] = b"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\
\n<Relationship Id=\"rId1\" \
Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" \
Target=\"xl/workbook.xml\"/>\
\n</Relationships>";

// Styles with 6 xf entries:
//   0=default, 1=date, 2=datetime
//   3=bold,    4=bold-date, 5=bold-datetime
const STYLES_XML: &[u8] = b"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">\
\n<fonts count=\"2\">\
\n<font><sz val=\"11\"/><name val=\"Calibri\"/></font>\
\n<font><b/><sz val=\"11\"/><name val=\"Calibri\"/></font>\
\n</fonts>\
\n<fills count=\"2\">\
\n<fill><patternFill patternType=\"none\"/></fill>\
\n<fill><patternFill patternType=\"gray125\"/></fill>\
\n</fills>\
\n<borders count=\"1\"><border><left/><right/><top/><bottom/><diagonal/></border></borders>\
\n<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>\
\n<cellXfs count=\"6\">\
\n<xf numFmtId=\"0\"  fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>\
\n<xf numFmtId=\"14\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>\
\n<xf numFmtId=\"22\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>\
\n<xf numFmtId=\"0\"  fontId=\"1\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/>\
\n<xf numFmtId=\"14\" fontId=\"1\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/>\
\n<xf numFmtId=\"22\" fontId=\"1\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/>\
\n</cellXfs>\
\n</styleSheet>";
