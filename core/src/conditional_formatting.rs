use crate::dxf::DxfFormat;
use quick_xml::events::Event;
use quick_xml::Reader;

/// A single `<cfRule>` inside a worksheet's `<conditionalFormatting sqref="...">`
/// block, with its `dxfId` already resolved against the workbook's `dxfs`.
///
/// `colorScale`/`dataBar`/`iconSet` rules are captured too (type, sqref,
/// priority) but their inline color-stop/threshold children aren't modeled --
/// those rule types define formatting directly rather than via `dxfId`, and
/// mapping their full stop/threshold structure is a separate, larger scope
/// than "conditional formatting rules are parsed at all" (the gap this closes).
#[derive(Debug, Clone, PartialEq)]
pub struct ConditionalFormatRule {
    pub sqref: String,
    pub rule_type: String,
    pub operator: Option<String>,
    pub formulas: Vec<String>,
    pub priority: i32,
    pub dxf_id: Option<usize>,
    pub format: Option<DxfFormat>,
    pub stop_if_true: bool,
}

/// Parse every `<conditionalFormatting>` block in worksheet XML. These are
/// siblings of `<sheetData>` (not children of it), so this scans the whole
/// document with its own reader rather than reusing `SheetParser`, which
/// stops at `</sheetData>`.
pub fn parse(
    xml: &[u8],
    dxfs: &[DxfFormat],
) -> Result<Vec<ConditionalFormatRule>, Box<dyn std::error::Error>> {
    let mut reader = Reader::from_reader(xml);
    reader.config_mut().trim_text(true);

    let mut rules = Vec::new();
    let mut current_sqref = String::new();
    let mut in_cf = false;
    let mut in_formula = false;
    let mut pending: Option<PendingRule> = None;
    let mut pending_formula = String::new();

    loop {
        match reader.read_event()? {
            Event::Start(ref e) => match e.name().as_ref() {
                b"conditionalFormatting" => {
                    in_cf = true;
                    current_sqref = attr(e, b"sqref").unwrap_or_default();
                }
                b"cfRule" if in_cf => pending = Some(pending_rule_from_attrs(e)),
                b"formula" if pending.is_some() => {
                    in_formula = true;
                    pending_formula.clear();
                }
                _ => {}
            },
            // `<cfRule .../>` self-closes when it has no `<formula>` children
            // (e.g. containsBlanks, duplicateValues, top10) -- it never
            // reaches `Event::End`, so finalize it immediately here instead.
            Event::Empty(ref e) => match e.name().as_ref() {
                b"cfRule" if in_cf => {
                    push_rule(&mut rules, pending_rule_from_attrs(e), &current_sqref, dxfs);
                }
                _ => {}
            },
            Event::Text(ref e) if in_formula => {
                pending_formula.push_str(&e.unescape()?);
            }
            Event::End(ref e) => match e.name().as_ref() {
                b"formula" => {
                    in_formula = false;
                    if let Some(ref mut p) = pending {
                        p.formulas.push(pending_formula.clone());
                    }
                }
                b"cfRule" => {
                    if let Some(p) = pending.take() {
                        push_rule(&mut rules, p, &current_sqref, dxfs);
                    }
                }
                b"conditionalFormatting" => in_cf = false,
                _ => {}
            },
            Event::Eof => break,
            _ => {}
        }
    }

    Ok(rules)
}

fn pending_rule_from_attrs(e: &quick_xml::events::BytesStart) -> PendingRule {
    PendingRule {
        rule_type: attr(e, b"type").unwrap_or_default(),
        operator: attr(e, b"operator"),
        priority: attr(e, b"priority").and_then(|v| v.parse().ok()).unwrap_or(0),
        dxf_id: attr(e, b"dxfId").and_then(|v| v.parse().ok()),
        stop_if_true: attr(e, b"stopIfTrue").map(|v| v == "1").unwrap_or(false),
        formulas: Vec::new(),
    }
}

fn push_rule(
    rules: &mut Vec<ConditionalFormatRule>,
    p: PendingRule,
    sqref: &str,
    dxfs: &[DxfFormat],
) {
    let format = p.dxf_id.and_then(|idx| dxfs.get(idx).cloned());
    rules.push(ConditionalFormatRule {
        sqref: sqref.to_string(),
        rule_type: p.rule_type,
        operator: p.operator,
        formulas: p.formulas,
        priority: p.priority,
        dxf_id: p.dxf_id,
        format,
        stop_if_true: p.stop_if_true,
    });
}

struct PendingRule {
    rule_type: String,
    operator: Option<String>,
    priority: i32,
    dxf_id: Option<usize>,
    stop_if_true: bool,
    formulas: Vec<String>,
}

fn attr(e: &quick_xml::events::BytesStart, key: &[u8]) -> Option<String> {
    e.attributes()
        .flatten()
        .find(|a| a.key.as_ref() == key)
        .map(|a| String::from_utf8_lossy(&a.value).into_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_cell_is_rule_with_dxf() {
        let xml = br#"<?xml version="1.0"?>
<worksheet>
  <sheetData></sheetData>
  <conditionalFormatting sqref="B2:B10">
    <cfRule type="cellIs" dxfId="0" priority="1" operator="greaterThan">
      <formula>100</formula>
    </cfRule>
  </conditionalFormatting>
</worksheet>"#;
        let dxfs = vec![DxfFormat {
            font_color: Some("FFFF0000".to_string()),
            ..Default::default()
        }];
        let rules = parse(xml, &dxfs).unwrap();
        assert_eq!(rules.len(), 1);
        assert_eq!(rules[0].sqref, "B2:B10");
        assert_eq!(rules[0].rule_type, "cellIs");
        assert_eq!(rules[0].operator.as_deref(), Some("greaterThan"));
        assert_eq!(rules[0].formulas, vec!["100".to_string()]);
        assert_eq!(rules[0].priority, 1);
        assert_eq!(
            rules[0].format.as_ref().unwrap().font_color.as_deref(),
            Some("FFFF0000")
        );
    }

    #[test]
    fn test_parse_expression_rule_two_formulas_between() {
        let xml = br#"<?xml version="1.0"?>
<worksheet>
  <sheetData></sheetData>
  <conditionalFormatting sqref="C2:C10">
    <cfRule type="cellIs" dxfId="0" priority="2" operator="between">
      <formula>1</formula>
      <formula>10</formula>
    </cfRule>
  </conditionalFormatting>
</worksheet>"#;
        let rules = parse(xml, &[]).unwrap();
        assert_eq!(rules.len(), 1);
        assert_eq!(rules[0].formulas, vec!["1".to_string(), "10".to_string()]);
        assert!(rules[0].format.is_none());
    }

    #[test]
    fn test_parse_multiple_conditional_formatting_blocks() {
        let xml = br#"<?xml version="1.0"?>
<worksheet>
  <sheetData></sheetData>
  <conditionalFormatting sqref="A1:A5">
    <cfRule type="containsBlanks" priority="1"/>
  </conditionalFormatting>
  <conditionalFormatting sqref="B1:B5">
    <cfRule type="duplicateValues" dxfId="1" priority="2"/>
  </conditionalFormatting>
</worksheet>"#;
        let dxfs = vec![DxfFormat::default(), DxfFormat {
            fill_bg_color: Some("FFFFFF00".to_string()),
            ..Default::default()
        }];
        let rules = parse(xml, &dxfs).unwrap();
        assert_eq!(rules.len(), 2);
        assert_eq!(rules[0].sqref, "A1:A5");
        assert_eq!(rules[0].rule_type, "containsBlanks");
        assert!(rules[0].formulas.is_empty());
        assert_eq!(rules[1].sqref, "B1:B5");
        assert_eq!(
            rules[1].format.as_ref().unwrap().fill_bg_color.as_deref(),
            Some("FFFFFF00")
        );
    }

    #[test]
    fn test_parse_no_conditional_formatting() {
        let xml = br#"<?xml version="1.0"?><worksheet><sheetData></sheetData></worksheet>"#;
        let rules = parse(xml, &[]).unwrap();
        assert!(rules.is_empty());
    }

    #[test]
    fn test_stop_if_true() {
        let xml = br#"<?xml version="1.0"?>
<worksheet>
  <sheetData></sheetData>
  <conditionalFormatting sqref="A1">
    <cfRule type="cellIs" priority="1" operator="equal" stopIfTrue="1">
      <formula>0</formula>
    </cfRule>
  </conditionalFormatting>
</worksheet>"#;
        let rules = parse(xml, &[]).unwrap();
        assert!(rules[0].stop_if_true);
    }
}
