use quick_xml::events::Event;
use quick_xml::Reader;
use std::collections::HashMap;

/// Parse xl/workbook.xml → ordered list of (sheet_name, r_id).
pub fn parse_sheet_names(xml: &[u8]) -> Result<Vec<(String, String)>, Box<dyn std::error::Error>> {
    let mut reader = Reader::from_reader(xml);
    reader.config_mut().trim_text(true);
    let mut sheets = Vec::new();

    loop {
        match reader.read_event()? {
            Event::Empty(ref e) | Event::Start(ref e) if e.name().as_ref() == b"sheet" => {
                let name = e
                    .attributes().flatten()
                    .find(|a| a.key.as_ref() == b"name")
                    .map(|a| String::from_utf8_lossy(&a.value).into_owned())
                    .unwrap_or_default();
                // The r:id attribute is stored with the namespace prefix as part of the key bytes
                let r_id = e
                    .attributes().flatten()
                    .find(|a| {
                        let k = a.key.as_ref();
                        k == b"r:id" || k.ends_with(b":id")
                    })
                    .map(|a| String::from_utf8_lossy(&a.value).into_owned())
                    .unwrap_or_default();
                if !name.is_empty() {
                    sheets.push((name, r_id));
                }
            }
            Event::Eof => break,
            _ => {}
        }
    }

    Ok(sheets)
}

/// Parse xl/_rels/workbook.xml.rels → map of relationship Id → target path.
pub fn parse_rels(xml: &[u8]) -> Result<HashMap<String, String>, Box<dyn std::error::Error>> {
    let mut reader = Reader::from_reader(xml);
    reader.config_mut().trim_text(true);
    let mut rels = HashMap::new();

    loop {
        match reader.read_event()? {
            Event::Empty(ref e) | Event::Start(ref e)
                if e.name().as_ref() == b"Relationship" =>
            {
                let id = e
                    .attributes().flatten()
                    .find(|a| a.key.as_ref() == b"Id")
                    .map(|a| String::from_utf8_lossy(&a.value).into_owned())
                    .unwrap_or_default();
                let target = e
                    .attributes().flatten()
                    .find(|a| a.key.as_ref() == b"Target")
                    .map(|a| String::from_utf8_lossy(&a.value).into_owned())
                    .unwrap_or_default();
                if !id.is_empty() {
                    rels.insert(id, target);
                }
            }
            Event::Eof => break,
            _ => {}
        }
    }

    Ok(rels)
}

/// Resolve a relationship target to a ZIP entry path.
/// Target is relative to xl/ unless it starts with '/'.
pub fn resolve_target(target: &str) -> String {
    if target.starts_with('/') {
        target.trim_start_matches('/').to_string()
    } else {
        format!("xl/{target}")
    }
}
