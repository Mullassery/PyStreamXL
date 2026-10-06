use crate::comments::CommentCache;
use crate::conditional_formatting::{self, ConditionalFormatRule};
use crate::dxf;
use crate::shared_strings;
use crate::sheet_parser::{CellMetadata, CellValue, SheetParser};
use crate::styles::{self, StyleInfo};
use crate::workbook;
use crate::zip_reader::XlsxZip;
use self_cell::{self_cell, MutBorrow};
use std::fs::File;
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::rc::Rc;
use zip::read::ZipFile;
use zip::ZipArchive;

type StreamingParser<'a> = SheetParser<BufReader<ZipFile<'a, File>>>;

self_cell!(
    struct StreamingSheetCell {
        owner: MutBorrow<ZipArchive<File>>,

        #[not_covariant]
        dependent: StreamingParser,
    }
);

/// Open a real streaming parser over a sheet entry: decompresses and parses
/// incrementally as rows are pulled, rather than buffering the whole sheet
/// XML into memory up front. `ZipFile<'_>` (the decompressing entry reader)
/// borrows `&mut ZipArchive`, so pairing an owned archive with a borrowed
/// reader over it needs a self-referential struct -- `self_cell` builds one
/// safely (see its docs), with no unsafe code written in this crate.
/// `MutBorrow` is `self_cell`'s own helper for dependents that need a one-time
/// `&mut Owner` to construct (self_cell's builder closure otherwise only
/// gives `&Owner`); it panics if misused, it never requires `unsafe` here.
fn open_streaming_parser(
    path: &Path,
    sheet_entry: &str,
    sst: Rc<Vec<String>>,
    styles: Rc<StyleInfo>,
) -> Result<StreamingSheetCell, Box<dyn std::error::Error>> {
    let file = File::open(path)?;
    let mut zip = XlsxZip::new(file)?;
    zip.check_and_register_entry(sheet_entry)?;
    let archive = zip.into_archive();

    let entry_name = sheet_entry.to_string();
    StreamingSheetCell::try_new(MutBorrow::new(archive), move |owner| {
        let archive_mut: &mut ZipArchive<File> = owner.borrow_mut();
        let zip_file = archive_mut.by_name(&entry_name)?;
        let buffered = BufReader::new(zip_file);
        Ok::<_, Box<dyn std::error::Error>>(SheetParser::new(buffered, sst, styles))
    })
}

pub struct XlsxStream {
    path: PathBuf,
    sheet_entry: String,
    sst: Rc<Vec<String>>,
    style_info: Rc<StyleInfo>,
    comments: Rc<CommentCache>,
    conditional_formats: Vec<ConditionalFormatRule>,
}

impl XlsxStream {
    /// Open an XLSX file. `sheet` selects by name; `None` uses the first sheet.
    pub fn open(
        path: impl AsRef<Path>,
        sheet: Option<&str>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let path_buf = path.as_ref().to_path_buf();
        let file = File::open(&path_buf)?;
        let mut zip = XlsxZip::new(file)?;

        let sst = if zip.has_entry("xl/sharedStrings.xml") {
            let raw = zip.read_entry("xl/sharedStrings.xml")?;
            shared_strings::parse(&raw)?
        } else {
            Vec::new()
        };

        let (style_info, dxfs) = if zip.has_entry("xl/styles.xml") {
            let raw = zip.read_entry("xl/styles.xml")?;
            let style_info = styles::parse(&raw).unwrap_or_default();
            let dxfs = dxf::parse_dxfs(&raw).unwrap_or_default();
            (style_info, dxfs)
        } else {
            (StyleInfo::default(), Vec::new())
        };

        // Load comments (typically from xl/comments1.xml for first sheet)
        let comments = if zip.has_entry("xl/comments1.xml") {
            let raw = zip.read_entry("xl/comments1.xml")?;
            CommentCache::from_xml(&raw).unwrap_or_default()
        } else {
            CommentCache::new()
        };

        let sheet_entry = resolve_sheet_path(&mut zip, sheet)?;

        // Conditional-formatting rules (<conditionalFormatting>/<cfRule>)
        // are siblings of <sheetData>, not children of it, so extracting
        // them needs the whole worksheet XML scanned -- unlike row data,
        // there's no way to stream just that part out. This is a one-time,
        // transient read at open() time (the buffer is dropped immediately
        // after, not held for the life of XlsxStream): real row iteration
        // via `.rows()`/`.rows_with_metadata()` below re-opens and streams
        // the same entry incrementally instead -- that's the actual gap
        // this fixes (ROADMAP_HONEST.md gap #10): peak memory *during
        // iteration* no longer scales with sheet size, only this one
        // upfront, short-lived pass does.
        let sheet_xml_for_cf = zip.read_entry(&sheet_entry)?;
        let conditional_formats =
            conditional_formatting::parse(&sheet_xml_for_cf, &dxfs).unwrap_or_default();
        drop(sheet_xml_for_cf);

        Ok(Self {
            path: path_buf,
            sheet_entry,
            sst: Rc::new(sst),
            style_info: Rc::new(style_info),
            comments: Rc::new(comments),
            conditional_formats,
        })
    }

    /// Conditional formatting rules (`<conditionalFormatting>`/`<cfRule>`) for
    /// the sheet this stream was opened on, with each rule's `dxfId` already
    /// resolved against `xl/styles.xml`'s `<dxfs>`.
    pub fn conditional_formats(&self) -> &[ConditionalFormatRule] {
        &self.conditional_formats
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

    /// Real, row-by-row streaming iterator: decompresses and parses the
    /// sheet incrementally, one row at a time, instead of buffering the
    /// whole sheet XML into memory first (see ROADMAP_HONEST.md gap #10).
    /// Re-opens the file fresh on each call, so this can be called more
    /// than once on the same `XlsxStream`.
    pub fn rows(&self) -> Result<RowIter, Box<dyn std::error::Error>> {
        let cell = open_streaming_parser(
            &self.path,
            &self.sheet_entry,
            Rc::clone(&self.sst),
            Rc::clone(&self.style_info),
        )?;
        Ok(RowIter { cell, done: false })
    }

    /// Same real streaming behavior as `rows()`, with formula/comment
    /// metadata attached to each cell.
    pub fn rows_with_metadata(&self) -> Result<RowIterMetadata, Box<dyn std::error::Error>> {
        let cell = open_streaming_parser(
            &self.path,
            &self.sheet_entry,
            Rc::clone(&self.sst),
            Rc::clone(&self.style_info),
        )?;
        Ok(RowIterMetadata {
            cell,
            comments: Rc::clone(&self.comments),
            done: false,
            current_row: 0,
        })
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

/// Real streaming row iterator: decompresses and parses the sheet XML
/// incrementally as rows are pulled, owning its own `ZipArchive` + decompressing
/// reader rather than borrowing from an `XlsxStream` (see `open_streaming_parser`).
pub struct RowIter {
    cell: StreamingSheetCell,
    done: bool,
}

impl Iterator for RowIter {
    type Item = Result<Vec<CellValue>, Box<dyn std::error::Error>>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.done {
            return None;
        }
        let next = self
            .cell
            .with_dependent_mut(|_owner, parser| parser.next_row());
        match next {
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

/// Same real streaming behavior as `RowIter`, with formula/comment metadata
/// attached to each cell.
pub struct RowIterMetadata {
    cell: StreamingSheetCell,
    comments: Rc<CommentCache>,
    done: bool,
    current_row: usize,
}

impl Iterator for RowIterMetadata {
    type Item = Result<Vec<CellMetadata>, Box<dyn std::error::Error>>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.done {
            return None;
        }
        let next = self
            .cell
            .with_dependent_mut(|_owner, parser| parser.next_row_with_metadata());
        match next {
            Ok(Some(mut row)) => {
                for (col_idx, cell) in row.iter_mut().enumerate() {
                    if let Some(comment) = self.comments.get(self.current_row, col_idx) {
                        cell.comment = Some(comment.text.clone());
                        cell.comment_author = comment.author.clone();
                    }
                }
                self.current_row += 1;
                Some(Ok(row))
            }
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
