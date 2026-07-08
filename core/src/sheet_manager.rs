/// Multi-sheet management for Excel workbooks.
///
/// Provides functionality to enumerate sheets, select specific sheets,
/// and handle cross-sheet references.
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct SheetMetadata {
    pub name: String,
    pub index: usize,
    pub rid: String,
    pub path: String,
}

pub struct SheetManager {
    sheets: Vec<SheetMetadata>,
    name_to_index: HashMap<String, usize>,
}

impl SheetManager {
    /// Create a new sheet manager from parsed sheet names and relationships.
    pub fn new(
        sheet_names: Vec<(String, String)>,
        rels: &HashMap<String, String>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let mut sheets = Vec::new();
        let mut name_to_index = HashMap::new();

        for (index, (name, rid)) in sheet_names.into_iter().enumerate() {
            let path = rels
                .get(&rid)
                .ok_or(format!("Sheet relationship '{}' not found", rid))?
                .clone();

            let resolved_path = if path.starts_with('/') {
                path.trim_start_matches('/').to_string()
            } else {
                format!("xl/{}", path)
            };

            let metadata = SheetMetadata {
                name: name.clone(),
                index,
                rid,
                path: resolved_path,
            };

            name_to_index.insert(name, index);
            sheets.push(metadata);
        }

        Ok(Self {
            sheets,
            name_to_index,
        })
    }

    /// Get sheet by name.
    pub fn get_sheet_by_name(&self, name: &str) -> Option<&SheetMetadata> {
        self.name_to_index
            .get(name)
            .and_then(|idx| self.sheets.get(*idx))
    }

    /// Get sheet by index (0-based).
    pub fn get_sheet_by_index(&self, index: usize) -> Option<&SheetMetadata> {
        self.sheets.get(index)
    }

    /// Get sheet by index (1-based, for user-facing APIs).
    pub fn get_sheet_by_position(&self, position: usize) -> Option<&SheetMetadata> {
        if position == 0 {
            return None;
        }
        self.get_sheet_by_index(position - 1)
    }

    /// List all sheet names in order.
    pub fn list_sheets(&self) -> Vec<&str> {
        self.sheets.iter().map(|s| s.name.as_str()).collect()
    }

    /// Get total number of sheets.
    pub fn sheet_count(&self) -> usize {
        self.sheets.len()
    }

    /// Get first sheet (default).
    pub fn get_first_sheet(&self) -> Option<&SheetMetadata> {
        self.sheets.first()
    }

    /// Parse a sheet reference (e.g., "Sheet2!A1:B5").
    pub fn parse_sheet_reference(reference: &str) -> Option<(String, String)> {
        if let Some(exclamation_pos) = reference.find('!') {
            let sheet_name = reference[..exclamation_pos].to_string();
            let cell_range = reference[exclamation_pos + 1..].to_string();
            Some((sheet_name, cell_range))
        } else {
            None
        }
    }

    /// Resolve a sheet reference to a sheet and cell range.
    pub fn resolve_sheet_reference(&self, reference: &str) -> Option<(&SheetMetadata, String)> {
        let (sheet_name, cell_range) = Self::parse_sheet_reference(reference)?;
        let sheet = self.get_sheet_by_name(&sheet_name)?;
        Some((sheet, cell_range))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sheet_manager_creation() {
        let sheet_names = vec![
            ("Sheet1".to_string(), "rId1".to_string()),
            ("Sheet2".to_string(), "rId2".to_string()),
        ];
        let mut rels = HashMap::new();
        rels.insert("rId1".to_string(), "worksheets/sheet1.xml".to_string());
        rels.insert("rId2".to_string(), "worksheets/sheet2.xml".to_string());

        let manager = SheetManager::new(sheet_names, &rels).unwrap();
        assert_eq!(manager.sheet_count(), 2);
    }

    #[test]
    fn test_get_sheet_by_name() {
        let sheet_names = vec![("Sheet1".to_string(), "rId1".to_string())];
        let mut rels = HashMap::new();
        rels.insert("rId1".to_string(), "worksheets/sheet1.xml".to_string());

        let manager = SheetManager::new(sheet_names, &rels).unwrap();
        let sheet = manager.get_sheet_by_name("Sheet1");
        assert!(sheet.is_some());
        assert_eq!(sheet.unwrap().name, "Sheet1");
    }

    #[test]
    fn test_parse_sheet_reference() {
        let reference = "Sheet2!A1:B5";
        let (sheet, range) = SheetManager::parse_sheet_reference(reference).unwrap();
        assert_eq!(sheet, "Sheet2");
        assert_eq!(range, "A1:B5");
    }

    #[test]
    fn test_list_sheets() {
        let sheet_names = vec![
            ("Sheet1".to_string(), "rId1".to_string()),
            ("Data".to_string(), "rId2".to_string()),
        ];
        let mut rels = HashMap::new();
        rels.insert("rId1".to_string(), "worksheets/sheet1.xml".to_string());
        rels.insert("rId2".to_string(), "worksheets/sheet2.xml".to_string());

        let manager = SheetManager::new(sheet_names, &rels).unwrap();
        let sheets = manager.list_sheets();
        assert_eq!(sheets.len(), 2);
        assert_eq!(sheets[0], "Sheet1");
        assert_eq!(sheets[1], "Data");
    }
}
