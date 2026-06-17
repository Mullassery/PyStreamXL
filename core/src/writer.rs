use std::collections::HashMap;
use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};
use zip::write::SimpleFileOptions;
use zip::ZipWriter;

pub enum WriteCell {
    Str(String),
    Num(f64),
    Bool(bool),
    Date(u32),      // Excel serial date (days, integer)
    DateTime(f64),  // Excel serial datetime (days + fractional time)
    Empty,
}

pub struct XlsxWriter {
    output_path: PathBuf,
    // Completed sheets: (name, finalized XML bytes)
    sheets: Vec<(String, Vec<u8>)>,
    // Current sheet being written
    current_name: String,
    current_buf: Vec<u8>,
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
    pub fn new(path: impl AsRef<Path>) -> Self {
        Self {
            output_path: path.as_ref().to_path_buf(),
            sheets: Vec::new(),
            current_name: "Sheet1".to_string(),
            current_buf: sheet_header(),
            sst: Vec::new(),
            sst_index: HashMap::new(),
        }
    }

    /// Finalise the current sheet and start a new one with the given name.
    pub fn add_sheet(&mut self, name: &str) {
        let mut buf = std::mem::take(&mut self.current_buf);
        buf.extend_from_slice(b"</sheetData>\n</worksheet>");
        let old_name = std::mem::replace(&mut self.current_name, name.to_string());
        self.sheets.push((old_name, buf));
        self.current_buf = sheet_header();
    }

    /// Write a row. `bold=true` applies bold font to every cell in the row.
    pub fn write_row(&mut self, cells: &[WriteCell], bold: bool) {
        self.current_buf.extend_from_slice(b"<row>");
        for cell in cells {
            // xf index: 0=default, 1=date, 2=datetime, 3=bold, 4=bold-date, 5=bold-datetime
            let xf: Option<u8> = match (cell, bold) {
                (WriteCell::Date(_), false)     => Some(1),
                (WriteCell::DateTime(_), false) => Some(2),
                (WriteCell::Empty, _)           => None,
                (WriteCell::Date(_), true)      => Some(4),
                (WriteCell::DateTime(_), true)  => Some(5),
                (_, true)                       => Some(3),
                _                               => None,
            };
            let s_attr: std::borrow::Cow<str> = match xf {
                Some(n) => format!(" s=\"{n}\"").into(),
                None    => "".into(),
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
    }

    pub fn finish(mut self) -> Result<(), Box<dyn std::error::Error>> {
        // Finalise the last sheet
        self.current_buf.extend_from_slice(b"</sheetData>\n</worksheet>");
        self.sheets.push((self.current_name, self.current_buf));

        let n_sheets = self.sheets.len();
        let has_sst = !self.sst.is_empty();

        let file = File::create(&self.output_path)?;
        let mut zip = ZipWriter::new(file);
        let opts = SimpleFileOptions::default()
            .compression_method(zip::CompressionMethod::Deflated);

        zip.start_file("[Content_Types].xml", opts)?;
        zip.write_all(build_content_types(n_sheets, has_sst).as_bytes())?;

        zip.start_file("_rels/.rels", opts)?;
        zip.write_all(RELS_XML)?;

        zip.start_file("xl/workbook.xml", opts)?;
        zip.write_all(build_workbook_xml(&self.sheets).as_bytes())?;

        zip.start_file("xl/_rels/workbook.xml.rels", opts)?;
        zip.write_all(build_workbook_rels(n_sheets, has_sst).as_bytes())?;

        zip.start_file("xl/styles.xml", opts)?;
        zip.write_all(STYLES_XML)?;

        if has_sst {
            zip.start_file("xl/sharedStrings.xml", opts)?;
            zip.write_all(build_sst(&self.sst).as_bytes())?;
        }

        for (i, (_, sheet_xml)) in self.sheets.iter().enumerate() {
            zip.start_file(format!("xl/worksheets/sheet{}.xml", i + 1), opts)?;
            zip.write_all(sheet_xml)?;
        }

        zip.finish()?;
        Ok(())
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

fn build_workbook_xml(sheets: &[(String, Vec<u8>)]) -> String {
    let mut xml = String::from(
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
\n<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" \
xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">\
\n<sheets>\n",
    );
    for (i, (name, _)) in sheets.iter().enumerate() {
        let escaped = name
            .replace('&', "&amp;").replace('<', "&lt;")
            .replace('>', "&gt;").replace('"', "&quot;");
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
            .replace('&', "&amp;").replace('<', "&lt;")
            .replace('>', "&gt;").replace('"', "&quot;");
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
