use crate::styles::StyleInfo;
use quick_xml::events::Event;
use quick_xml::Reader;

#[derive(Debug, Clone)]
pub enum CellValue {
    String(String),
    Number(f64),
    Bool(bool),
    Date(f64),     // Excel serial date (integer, stored as f64)
    DateTime(f64), // Excel serial datetime (integer + fractional time)
    Error(String), // Excel error value (#DIV/0!, #REF!, #VALUE!, etc)
    Empty,
}

#[derive(Debug, Clone)]
pub struct CellMetadata {
    pub value: CellValue,
    pub formula: Option<String>,      // e.g., "=SUM(A1:A10)"
    pub formula_type: Option<String>, // "sum", "vlookup", "custom", etc
}

impl CellMetadata {
    pub fn new(value: CellValue) -> Self {
        Self {
            value,
            formula: None,
            formula_type: None,
        }
    }

    pub fn with_formula(mut self, formula: String, ftype: String) -> Self {
        self.formula = Some(formula);
        self.formula_type = Some(ftype);
        self
    }
}

/// Streams rows from sheet XML, resolving shared strings and detecting date cells.
pub struct SheetParser<'a> {
    reader: Reader<&'a [u8]>,
    sst: &'a [String],
    styles: &'a StyleInfo,
}

impl<'a> SheetParser<'a> {
    pub fn new(xml: &'a [u8], sst: &'a [String], styles: &'a StyleInfo) -> Self {
        let mut reader = Reader::from_reader(xml);
        reader.config_mut().trim_text(true);
        Self {
            reader,
            sst,
            styles,
        }
    }

    pub fn next_row(&mut self) -> Result<Option<Vec<CellValue>>, Box<dyn std::error::Error>> {
        let mut row: Option<Vec<CellValue>> = None;
        let mut cell_type = String::new();
        let mut cell_style: usize = 0;
        let mut cell_value = String::new();
        let mut in_v = false;
        let mut in_t = false;

        loop {
            match self.reader.read_event()? {
                Event::Start(ref e) => match e.name().as_ref() {
                    b"row" => row = Some(Vec::new()),
                    b"c" => {
                        cell_type = e
                            .attributes()
                            .flatten()
                            .find(|a| a.key.as_ref() == b"t")
                            .map(|a| String::from_utf8_lossy(&a.value).into_owned())
                            .unwrap_or_else(|| "n".to_string());
                        cell_style = e
                            .attributes()
                            .flatten()
                            .find(|a| a.key.as_ref() == b"s")
                            .and_then(|a| String::from_utf8_lossy(&a.value).parse().ok())
                            .unwrap_or(0);
                        cell_value.clear();
                    }
                    b"v" => in_v = true,
                    b"t" if cell_type == "inlineStr" => in_t = true,
                    _ => {}
                },
                Event::Text(ref e) if in_v || in_t => {
                    cell_value.push_str(&e.unescape()?);
                }
                // Self-closing empty cell: <c/> or <c r="A1"/>
                Event::Empty(ref e) if e.name().as_ref() == b"c" => {
                    if let Some(ref mut r) = row {
                        r.push(CellValue::Empty);
                    }
                }
                Event::End(ref e) => match e.name().as_ref() {
                    b"v" => in_v = false,
                    b"t" => in_t = false,
                    b"c" => {
                        if let Some(ref mut r) = row {
                            r.push(self.resolve_cell(&cell_type, &cell_value, cell_style));
                        }
                    }
                    b"row" => {
                        if let Some(r) = row.take() {
                            return Ok(Some(r));
                        }
                    }
                    b"sheetData" => return Ok(None),
                    _ => {}
                },
                Event::Eof => return Ok(None),
                _ => {}
            }
        }
    }

    pub fn next_row_with_metadata(&mut self) -> Result<Option<Vec<CellMetadata>>, Box<dyn std::error::Error>> {
        let mut row: Option<Vec<CellMetadata>> = None;
        let mut cell_type = String::new();
        let mut cell_style: usize = 0;
        let mut cell_value = String::new();
        let mut cell_formula = String::new();
        let mut in_v = false;
        let mut in_f = false;
        let mut in_t = false;

        loop {
            match self.reader.read_event()? {
                Event::Start(ref e) => match e.name().as_ref() {
                    b"row" => row = Some(Vec::new()),
                    b"c" => {
                        cell_type = e
                            .attributes()
                            .flatten()
                            .find(|a| a.key.as_ref() == b"t")
                            .map(|a| String::from_utf8_lossy(&a.value).into_owned())
                            .unwrap_or_else(|| "n".to_string());
                        cell_style = e
                            .attributes()
                            .flatten()
                            .find(|a| a.key.as_ref() == b"s")
                            .and_then(|a| String::from_utf8_lossy(&a.value).parse().ok())
                            .unwrap_or(0);
                        cell_value.clear();
                        cell_formula.clear();
                    }
                    b"v" => in_v = true,
                    b"f" => in_f = true,
                    b"t" if cell_type == "inlineStr" => in_t = true,
                    _ => {}
                },
                Event::Text(ref e) if in_v || in_t => {
                    cell_value.push_str(&e.unescape()?);
                }
                Event::Text(ref e) if in_f => {
                    cell_formula.push_str(&e.unescape()?);
                }
                Event::Empty(ref e) if e.name().as_ref() == b"c" => {
                    if let Some(ref mut r) = row {
                        r.push(CellMetadata::new(CellValue::Empty));
                    }
                }
                Event::End(ref e) => match e.name().as_ref() {
                    b"v" => in_v = false,
                    b"f" => in_f = false,
                    b"t" => in_t = false,
                    b"c" => {
                        if let Some(ref mut r) = row {
                            let value = self.resolve_cell(&cell_type, &cell_value, cell_style);
                            let mut metadata = CellMetadata::new(value);

                            if !cell_formula.is_empty() {
                                let ftype = Self::detect_formula_type(&cell_formula);
                                metadata = metadata.with_formula(cell_formula.clone(), ftype);
                            }

                            r.push(metadata);
                        }
                    }
                    b"row" => {
                        if let Some(r) = row.take() {
                            return Ok(Some(r));
                        }
                    }
                    b"sheetData" => return Ok(None),
                    _ => {}
                },
                Event::Eof => return Ok(None),
                _ => {}
            }
        }
    }

    fn resolve_cell(&self, cell_type: &str, value: &str, style_idx: usize) -> CellValue {
        match cell_type {
            "s" => {
                let idx: usize = value.parse().unwrap_or(0);
                self.sst
                    .get(idx)
                    .map(|s| CellValue::String(s.clone()))
                    .unwrap_or(CellValue::Empty)
            }
            "inlineStr" => CellValue::String(value.to_string()),
            "b" => CellValue::Bool(value == "1"),
            "e" => CellValue::Error(value.to_string()), // Error cell type
            _ if value.is_empty() => CellValue::Empty,
            _ => {
                if let Ok(n) = value.parse::<f64>() {
                    if self.styles.is_datetime(style_idx) {
                        CellValue::DateTime(n)
                    } else if self.styles.is_date(style_idx) {
                        CellValue::Date(n)
                    } else {
                        CellValue::Number(n)
                    }
                } else {
                    CellValue::String(value.to_string())
                }
            }
        }
    }

    fn detect_formula_type(formula: &str) -> String {
        let formula_upper = formula.to_uppercase();
        if formula_upper.starts_with("=SUM(") {
            "sum".to_string()
        } else if formula_upper.starts_with("=AVERAGE(") || formula_upper.starts_with("=AVG(") {
            "average".to_string()
        } else if formula_upper.starts_with("=IF(") {
            "if".to_string()
        } else if formula_upper.starts_with("=VLOOKUP(") {
            "vlookup".to_string()
        } else if formula_upper.starts_with("=INDEX(") && formula_upper.contains("MATCH") {
            "index_match".to_string()
        } else if formula_upper.starts_with("=COUNT") {
            "count".to_string()
        } else if formula_upper.starts_with("=PRODUCT(") {
            "product".to_string()
        } else if formula_upper.starts_with("=SUBTOTAL(") {
            "subtotal".to_string()
        } else {
            "custom".to_string()
        }
    }
}
