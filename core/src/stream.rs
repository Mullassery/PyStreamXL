use crate::shared_strings;
use crate::sheet_parser::{CellValue, SheetParser};
use crate::styles::{self, StyleInfo};
use crate::workbook;
use crate::zip_reader::XlsxZip;
use std::fs::File;
use std::path::Path;

pub struct XlsxStream {
    sheet_xml: Vec<u8>,
    sst: Vec<String>,
    style_info: StyleInfo,
}

impl XlsxStream {
    /// Open an XLSX file. `sheet` selects by name; `None` uses the first sheet.
    pub fn open(path: impl AsRef<Path>, sheet: Option<&str>) -> Result<Self, Box<dyn std::error::Error>> {
        let file = File::open(path)?;
        let mut zip = XlsxZip::new(file)?;

        let sst = if zip.has_entry("xl/sharedStrings.xml") {
            let raw = zip.read_entry("xl/sharedStrings.xml")?;
            shared_strings::parse(&raw)?
        } else {
            Vec::new()
        };

        let style_info = if zip.has_entry("xl/styles.xml") {
            let raw = zip.read_entry("xl/styles.xml")?;
            styles::parse(&raw).unwrap_or_default()
        } else {
            StyleInfo::default()
        };

        let sheet_path = resolve_sheet_path(&mut zip, sheet)?;
        let sheet_xml = zip.read_entry(&sheet_path)?;

        Ok(Self { sheet_xml, sst, style_info })
    }

    /// Return all sheet names from the workbook.
    pub fn sheet_names(path: impl AsRef<Path>) -> Result<Vec<String>, Box<dyn std::error::Error>> {
        let file = File::open(path)?;
        let mut zip = XlsxZip::new(file)?;
        let wb_xml = zip.read_entry("xl/workbook.xml")?;
        Ok(workbook::parse_sheet_names(&wb_xml)?
            .into_iter()
            .map(|(name, _)| name)
            .collect())
    }

    pub fn rows(&self) -> RowIter<'_> {
        RowIter {
            parser: SheetParser::new(&self.sheet_xml, &self.sst, &self.style_info),
            done: false,
        }
    }
}

fn resolve_sheet_path(
    zip: &mut XlsxZip<File>,
    sheet: Option<&str>,
) -> Result<String, Box<dyn std::error::Error>> {
    if !zip.has_entry("xl/workbook.xml") {
        return Ok("xl/worksheets/sheet1.xml".to_string());
    }

    let wb_xml = zip.read_entry("xl/workbook.xml")?;
    let rels_xml = zip.read_entry("xl/_rels/workbook.xml.rels")?;
    let sheet_list = workbook::parse_sheet_names(&wb_xml)?;
    let rels = workbook::parse_rels(&rels_xml)?;

    let r_id = match sheet {
        Some(name) => sheet_list
            .iter()
            .find(|(n, _)| n.as_str() == name)
            .map(|(_, r)| r.clone())
            .ok_or_else(|| format!("sheet '{name}' not found"))?,
        None => sheet_list
            .first()
            .map(|(_, r)| r.clone())
            .unwrap_or_else(|| "rId1".to_string()),
    };

    let target = rels
        .get(&r_id)
        .ok_or_else(|| format!("relationship '{r_id}' not found in workbook.xml.rels"))?;

    Ok(workbook::resolve_target(target))
}

pub struct RowIter<'a> {
    parser: SheetParser<'a>,
    done: bool,
}

impl<'a> Iterator for RowIter<'a> {
    type Item = Result<Vec<CellValue>, Box<dyn std::error::Error>>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.done {
            return None;
        }
        match self.parser.next_row() {
            Ok(Some(row)) => Some(Ok(row)),
            Ok(None) => {
                self.done = true;
                None
            }
            Err(e) => {
                self.done = true;
                Some(Err(e))
            }
        }
    }
}
