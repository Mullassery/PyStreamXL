use quick_xml::events::Event;
use quick_xml::Reader;

/// A differential format (`<dxf>`) -- the subset of style overrides that
/// conditional formatting rules apply when their condition matches. Unlike
/// `<xf>` entries in `cellXfs`, a `<dxf>` only carries the *overridden*
/// properties (e.g. just a font color), so every field here is optional.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct DxfFormat {
    pub font_color: Option<String>,
    pub font_bold: Option<bool>,
    pub font_italic: Option<bool>,
    pub fill_bg_color: Option<String>,
    pub fill_fg_color: Option<String>,
}

/// Parse the `<dxfs>` block of `xl/styles.xml` into an index-ordered list of
/// differential formats. `cfRule/@dxfId` in worksheet XML is a 0-based index
/// into this list.
pub fn parse_dxfs(xml: &[u8]) -> Result<Vec<DxfFormat>, Box<dyn std::error::Error>> {
    let mut reader = Reader::from_reader(xml);
    reader.config_mut().trim_text(true);

    let mut dxfs = Vec::new();
    let mut in_dxfs = false;
    let mut in_font = false;
    let mut in_fill = false;
    let mut current: Option<DxfFormat> = None;

    loop {
        match reader.read_event()? {
            // Self-closed tags (`<font/>`) never get a matching `Event::End`,
            // so an empty `<font/>`/`<fill/>` must not flip `in_font`/`in_fill`
            // to true -- there'd be nothing to turn it back off.
            Event::Start(ref e) => {
                match e.name().as_ref() {
                    b"dxfs" => in_dxfs = true,
                    b"dxf" if in_dxfs => current = Some(DxfFormat::default()),
                    b"font" if current.is_some() => in_font = true,
                    b"fill" if current.is_some() => in_fill = true,
                    _ => {}
                }
            }
            Event::Empty(ref e) => match e.name().as_ref() {
                b"color" if in_font => {
                    if let Some(rgb) = attr(e, b"rgb") {
                        if let Some(ref mut c) = current {
                            c.font_color = Some(rgb);
                        }
                    }
                }
                b"b" if in_font => {
                    if let Some(ref mut c) = current {
                        c.font_bold = Some(true);
                    }
                }
                b"i" if in_font => {
                    if let Some(ref mut c) = current {
                        c.font_italic = Some(true);
                    }
                }
                b"bgColor" if in_fill => {
                    if let Some(rgb) = attr(e, b"rgb") {
                        if let Some(ref mut c) = current {
                            c.fill_bg_color = Some(rgb);
                        }
                    }
                }
                b"fgColor" if in_fill => {
                    if let Some(rgb) = attr(e, b"rgb") {
                        if let Some(ref mut c) = current {
                            c.fill_fg_color = Some(rgb);
                        }
                    }
                }
                _ => {}
            },
            Event::End(ref e) => match e.name().as_ref() {
                b"dxfs" => in_dxfs = false,
                b"font" => in_font = false,
                b"fill" => in_fill = false,
                b"dxf" => {
                    if let Some(c) = current.take() {
                        dxfs.push(c);
                    }
                }
                _ => {}
            },
            Event::Eof => break,
            _ => {}
        }
    }

    Ok(dxfs)
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
    fn test_parse_dxfs_font_color() {
        let xml = br#"<?xml version="1.0"?>
<styleSheet>
  <dxfs count="1">
    <dxf>
      <font>
        <color rgb="FFFF0000"/>
        <b/>
      </font>
      <fill>
        <patternFill>
          <bgColor rgb="FFFFFF00"/>
        </patternFill>
      </fill>
    </dxf>
  </dxfs>
</styleSheet>"#;
        let dxfs = parse_dxfs(xml).unwrap();
        assert_eq!(dxfs.len(), 1);
        assert_eq!(dxfs[0].font_color.as_deref(), Some("FFFF0000"));
        assert_eq!(dxfs[0].font_bold, Some(true));
        assert_eq!(dxfs[0].fill_bg_color.as_deref(), Some("FFFFFF00"));
    }

    #[test]
    fn test_parse_dxfs_multiple_preserves_order_for_dxfid_lookup() {
        let xml = br#"<?xml version="1.0"?>
<styleSheet>
  <dxfs count="2">
    <dxf><font><color rgb="FFFF0000"/></font></dxf>
    <dxf><font><color rgb="FF00FF00"/></font></dxf>
  </dxfs>
</styleSheet>"#;
        let dxfs = parse_dxfs(xml).unwrap();
        assert_eq!(dxfs.len(), 2);
        assert_eq!(dxfs[0].font_color.as_deref(), Some("FFFF0000"));
        assert_eq!(dxfs[1].font_color.as_deref(), Some("FF00FF00"));
    }

    #[test]
    fn test_parse_dxfs_no_dxfs_block() {
        let xml = br#"<?xml version="1.0"?><styleSheet></styleSheet>"#;
        let dxfs = parse_dxfs(xml).unwrap();
        assert!(dxfs.is_empty());
    }
}
