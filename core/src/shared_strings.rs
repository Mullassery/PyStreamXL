use quick_xml::events::{BytesRef, Event};
use quick_xml::Reader;

pub(crate) fn push_general_ref(
    out: &mut String,
    e: &BytesRef<'_>,
) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(ch) = e.resolve_char_ref()? {
        out.push(ch);
    } else {
        let raw = e.decode()?;
        if let Some(s) = quick_xml::escape::resolve_xml_entity(&raw) {
            out.push_str(s);
        } else {
            out.push('&');
            out.push_str(&raw);
            out.push(';');
        }
    }
    Ok(())
}

/// Parses the sharedStrings.xml table into an indexed Vec.
pub fn parse(xml: &[u8]) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let mut reader = Reader::from_reader(xml);

    let mut strings = Vec::new();
    let mut current = String::new();
    let mut in_t = false;

    loop {
        match reader.read_event()? {
            Event::Start(ref e) if e.name().as_ref() == b"t" => in_t = true,
            Event::Text(e) if in_t => {
                current.push_str(&quick_xml::escape::unescape(&e.decode()?)?);
            }
            Event::GeneralRef(ref e) if in_t => {
                push_general_ref(&mut current, e)?;
            }
            Event::End(ref e) if e.name().as_ref() == b"t" => in_t = false,
            Event::End(ref e) if e.name().as_ref() == b"si" => {
                strings.push(std::mem::take(&mut current));
            }
            Event::Eof => break,
            _ => {}
        }
    }

    Ok(strings)
}
