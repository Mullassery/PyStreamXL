use quick_xml::events::Event;
use quick_xml::Reader;
use std::collections::HashSet;

// Excel built-in date format IDs (no time component)
const BUILTIN_DATE_IDS: &[u32] = &[14, 15, 16, 17];
// Excel built-in datetime format IDs (have time component)
const BUILTIN_DATETIME_IDS: &[u32] = &[22];

/// Per-file style information needed to detect date/datetime cells.
#[derive(Default)]
pub struct StyleInfo {
    xf_is_date: Vec<bool>,
    xf_is_datetime: Vec<bool>,
}

impl StyleInfo {
    pub fn is_date(&self, xf_idx: usize) -> bool {
        self.xf_is_date.get(xf_idx).copied().unwrap_or(false)
    }
    pub fn is_datetime(&self, xf_idx: usize) -> bool {
        self.xf_is_datetime.get(xf_idx).copied().unwrap_or(false)
    }
}

/// Heuristic: strip quoted sections, then check for date/time tokens.
fn classify_format(fmt: &str) -> (bool, bool) {
    let mut clean = String::new();
    let mut in_quote = false;
    for ch in fmt.chars() {
        match ch {
            '"' => in_quote = !in_quote,
            _ if !in_quote => clean.push(ch.to_ascii_lowercase()),
            _ => {}
        }
    }
    let has_date = clean.contains('y')
        || clean.contains("mmm")
        || (clean.contains('d') && !clean.starts_with('['));
    let has_time = clean.contains('h') || clean.contains("ss");
    (has_date || has_time, has_time)
}

pub fn parse(xml: &[u8]) -> Result<StyleInfo, Box<dyn std::error::Error>> {
    let mut reader = Reader::from_reader(xml);
    reader.config_mut().trim_text(true);

    let mut custom_date_ids: HashSet<u32> = HashSet::new();
    let mut custom_datetime_ids: HashSet<u32> = HashSet::new();
    let mut in_num_fmts = false;
    let mut in_cell_xfs = false;
    let mut xf_is_date: Vec<bool> = Vec::new();
    let mut xf_is_datetime: Vec<bool> = Vec::new();

    loop {
        match reader.read_event()? {
            Event::Start(ref e) | Event::Empty(ref e) => {
                match e.name().as_ref() {
                    b"numFmts" => in_num_fmts = true,
                    b"cellXfs" => in_cell_xfs = true,
                    b"numFmt" if in_num_fmts => {
                        let id: u32 = e
                            .attributes().flatten()
                            .find(|a| a.key.as_ref() == b"numFmtId")
                            .and_then(|a| String::from_utf8_lossy(&a.value).parse().ok())
                            .unwrap_or(0);
                        if id >= 164 {
                            let fmt = e
                                .attributes().flatten()
                                .find(|a| a.key.as_ref() == b"formatCode")
                                .map(|a| String::from_utf8_lossy(&a.value).into_owned())
                                .unwrap_or_default();
                            let (is_d, is_dt) = classify_format(&fmt);
                            if is_dt {
                                custom_datetime_ids.insert(id);
                            } else if is_d {
                                custom_date_ids.insert(id);
                            }
                        }
                    }
                    b"xf" if in_cell_xfs => {
                        let fmt_id: u32 = e
                            .attributes().flatten()
                            .find(|a| a.key.as_ref() == b"numFmtId")
                            .and_then(|a| String::from_utf8_lossy(&a.value).parse().ok())
                            .unwrap_or(0);
                        let is_datetime = BUILTIN_DATETIME_IDS.contains(&fmt_id)
                            || custom_datetime_ids.contains(&fmt_id);
                        let is_date = BUILTIN_DATE_IDS.contains(&fmt_id)
                            || custom_date_ids.contains(&fmt_id)
                            || is_datetime;
                        xf_is_date.push(is_date);
                        xf_is_datetime.push(is_datetime);
                    }
                    _ => {}
                }
            }
            Event::End(ref e) => match e.name().as_ref() {
                b"numFmts" => in_num_fmts = false,
                b"cellXfs" => in_cell_xfs = false,
                _ => {}
            },
            Event::Eof => break,
            _ => {}
        }
    }

    Ok(StyleInfo { xf_is_date, xf_is_datetime })
}
