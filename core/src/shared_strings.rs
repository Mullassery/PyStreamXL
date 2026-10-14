use quick_xml::events::Event;
use quick_xml::Reader;

/// Parses the sharedStrings.xml table into an indexed Vec.
pub fn parse(xml: &[u8]) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let mut reader = Reader::from_reader(xml);
    reader.config_mut().trim_text(true);

    let mut strings = Vec::new();
    let mut current = String::new();
    let mut in_t = false;

    loop {
        match reader.read_event()? {
            Event::Start(ref e) if e.name().as_ref() == b"t" => in_t = true,
            Event::Text(e) if in_t => current.push_str(&quick_xml::escape::unescape(&e.decode()?)?),
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
