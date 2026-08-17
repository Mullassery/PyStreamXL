use quick_xml::events::Event;
use quick_xml::Reader;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Comment {
    pub text: String,
    pub author: Option<String>,
    pub row: usize,
    pub col: usize,
}

/// Cache of comments from xl/comments*.xml files
pub struct CommentCache {
    comments: HashMap<(usize, usize), Comment>,
}

impl CommentCache {
    /// Create empty comment cache
    pub fn new() -> Self {
        Self {
            comments: HashMap::new(),
        }
    }

    /// Parse comments from XML (xl/comments1.xml format)
    pub fn from_xml(xml: &[u8]) -> Result<Self, Box<dyn std::error::Error>> {
        let mut reader = Reader::from_reader(xml);
        reader.config_mut().trim_text(true);

        let mut comments = HashMap::new();
        let mut in_text = false;
        let mut current_ref = String::new();
        let mut current_author = String::new();
        let mut current_text = String::new();

        loop {
            match reader.read_event()? {
                Event::Start(ref e) => match e.name().as_ref() {
                    b"comment" => {
                        // Extract ref="A1" attribute
                        for attr in e.attributes().flatten() {
                            if attr.key.as_ref() == b"ref" {
                                current_ref = String::from_utf8_lossy(&attr.value).into_owned();
                            } else if attr.key.as_ref() == b"authorId" {
                                current_author = String::from_utf8_lossy(&attr.value).into_owned();
                            }
                        }
                    }
                    b"t" => in_text = true,
                    _ => {}
                },
                Event::Text(ref e) if in_text => {
                    current_text.push_str(&e.unescape()?);
                }
                Event::End(ref e) => match e.name().as_ref() {
                    b"t" => in_text = false,
                    b"comment" => {
                        if !current_ref.is_empty() && !current_text.is_empty() {
                            if let Ok((row, col)) = Self::parse_cell_ref(&current_ref) {
                                comments.insert(
                                    (row, col),
                                    Comment {
                                        text: current_text.clone(),
                                        author: if current_author.is_empty() {
                                            None
                                        } else {
                                            Some(current_author.clone())
                                        },
                                        row,
                                        col,
                                    },
                                );
                            }
                        }
                        current_ref.clear();
                        current_author.clear();
                        current_text.clear();
                    }
                    _ => {}
                },
                Event::Eof => break,
                _ => {}
            }
        }

        Ok(CommentCache { comments })
    }

    /// Get comment for a cell (0-indexed row, col)
    pub fn get(&self, row: usize, col: usize) -> Option<&Comment> {
        self.comments.get(&(row, col))
    }

    /// Get all comments
    pub fn all(&self) -> Vec<&Comment> {
        self.comments.values().collect()
    }

    /// Get comment count
    pub fn len(&self) -> usize {
        self.comments.len()
    }

    pub fn is_empty(&self) -> bool {
        self.comments.is_empty()
    }

    /// Parse cell reference "A1" to (row, col) as 0-indexed
    fn parse_cell_ref(cell_ref: &str) -> Result<(usize, usize), Box<dyn std::error::Error>> {
        let mut col_str = String::new();
        let mut row_str = String::new();

        for ch in cell_ref.chars() {
            if ch.is_alphabetic() {
                col_str.push(ch);
            } else {
                row_str.push(ch);
            }
        }

        // Convert column letters to number (A=0, B=1, ..., Z=25, AA=26, etc)
        let col = Self::col_str_to_num(&col_str)? as usize;
        let row = row_str.parse::<usize>()? - 1; // Excel rows are 1-indexed

        Ok((row, col))
    }

    /// Convert column string (A, Z, AA, etc) to 0-indexed number
    fn col_str_to_num(col: &str) -> Result<i32, Box<dyn std::error::Error>> {
        let mut num = 0;
        for ch in col.chars() {
            if !ch.is_alphabetic() {
                return Err("Invalid column reference".into());
            }
            num = num * 26 + (ch.to_uppercase().to_string().as_bytes()[0] - b'A' + 1) as i32;
        }
        Ok(num - 1) // Convert to 0-indexed
    }
}

impl Default for CommentCache {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_col_str_to_num() {
        assert_eq!(CommentCache::col_str_to_num("A").unwrap(), 0);
        assert_eq!(CommentCache::col_str_to_num("B").unwrap(), 1);
        assert_eq!(CommentCache::col_str_to_num("Z").unwrap(), 25);
        assert_eq!(CommentCache::col_str_to_num("AA").unwrap(), 26);
        assert_eq!(CommentCache::col_str_to_num("AB").unwrap(), 27);
    }

    #[test]
    fn test_parse_cell_ref() {
        assert_eq!(CommentCache::parse_cell_ref("A1").unwrap(), (0, 0));
        assert_eq!(CommentCache::parse_cell_ref("B2").unwrap(), (1, 1));
        assert_eq!(CommentCache::parse_cell_ref("Z10").unwrap(), (9, 25));
        assert_eq!(CommentCache::parse_cell_ref("AA1").unwrap(), (0, 26));
    }

    #[test]
    fn test_parse_comments_xml() {
        let xml = br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<comments xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <commentList>
    <comment ref="A1" authorId="0">
      <text><t>This is a comment</t></text>
    </comment>
  </commentList>
</comments>"#;

        let cache = CommentCache::from_xml(xml).unwrap();
        assert_eq!(cache.len(), 1);
        assert!(cache.get(0, 0).is_some());
    }
}
