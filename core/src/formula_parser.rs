/// Formula Extraction & Analysis for Phase 2
///
/// Extract formulas from Excel cells, parse dependencies, and build reference maps.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CellReference {
    pub sheet: String,
    pub column: String,
    pub row: u32,
    pub absolute: bool,  // $A$1 vs A1
}

impl CellReference {
    pub fn new(sheet: String, column: String, row: u32) -> Self {
        CellReference {
            sheet,
            column,
            row,
            absolute: false,
        }
    }

    pub fn to_string(&self) -> String {
        let prefix = if self.absolute { "$" } else { "" };
        format!("{}{}!{}{}{}", prefix, self.sheet, prefix, self.column, self.row)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Formula {
    pub original: String,
    pub formula_type: String,  // SUM, IF, VLOOKUP, CONCATENATE, etc.
    pub references: Vec<CellReference>,
    pub complexity: u32,  // Nesting depth
    pub has_external_links: bool,
    pub is_array_formula: bool,
}

impl Formula {
    pub fn new(original: String) -> Self {
        let formula_type = Self::identify_type(&original);
        let complexity = Self::calculate_complexity(&original);
        let is_array = original.starts_with("{") && original.ends_with("}");

        Formula {
            original,
            formula_type,
            references: Vec::new(),
            complexity,
            has_external_links: false,
            is_array_formula: is_array,
        }
    }

    fn identify_type(formula: &str) -> String {
        let upper = formula.to_uppercase();

        if upper.contains("SUM(") {
            "SUM".to_string()
        } else if upper.contains("IF(") {
            "IF".to_string()
        } else if upper.contains("VLOOKUP(") {
            "VLOOKUP".to_string()
        } else if upper.contains("CONCATENATE(") || upper.contains("&") {
            "CONCATENATE".to_string()
        } else if upper.contains("INDEX(") || upper.contains("MATCH(") {
            "INDEX_MATCH".to_string()
        } else if upper.contains("SUMIF(") {
            "SUMIF".to_string()
        } else {
            "OTHER".to_string()
        }
    }

    fn calculate_complexity(formula: &str) -> u32 {
        let open_parens = formula.matches('(').count() as u32;
        let nested_ifs = formula.matches("IF(").count() as u32;
        open_parens + (nested_ifs * 2)  // Nested IFs add extra complexity
    }
}

pub struct FormulaExtractor;

impl FormulaExtractor {
    /// Extract all formulas from a cell value
    pub fn extract_formulas(cell_value: &str) -> Vec<Formula> {
        let mut formulas = Vec::new();

        if cell_value.starts_with('=') {
            let formula = Formula::new(cell_value.to_string());
            formulas.push(formula);
        }

        formulas
    }

    /// Parse cell references from a formula
    pub fn extract_references(formula: &str, current_sheet: &str) -> Vec<CellReference> {
        let mut references = Vec::new();

        // Pattern: Sheet!$A$1 or A1 or Sheet.A1
        let patterns = vec![
            r"([A-Za-z_]\w*)?[!.]?(\$?[A-Z]+\$?\d+)",  // Standard cell refs
            r"([A-Za-z_]\w*)?[!.]?(\$?[A-Z]+\$?\d+:\$?[A-Z]+\$?\d+)",  // Ranges
        ];

        for pattern_str in patterns {
            if let Ok(re) = Regex::new(pattern_str) {
                for cap in re.captures_iter(formula) {
                    if let Some(cell_match) = cap.get(2) {
                        let cell_str = cell_match.as_str();
                        if let Some(ref_obj) = Self::parse_cell_reference(cell_str, current_sheet) {
                            references.push(ref_obj);
                        }
                    }
                }
            }
        }

        references
    }

    fn parse_cell_reference(cell: &str, sheet: &str) -> Option<CellReference> {
        // Extract column (A-Z, AA-ZZ, etc.) and row number
        if let Some(pos) = cell.find(|c: char| c.is_numeric()) {
            let col_part = &cell[..pos];
            let row_part = &cell[pos..];

            if let Ok(row) = row_part.parse::<u32>() {
                let absolute = cell.contains('$');
                let col = col_part.trim_start_matches('$');

                return Some(CellReference {
                    sheet: sheet.to_string(),
                    column: col.to_string(),
                    row,
                    absolute,
                });
            }
        }

        None
    }
}

pub struct ReferenceMapper {
    formula_map: HashMap<String, Formula>,
    dependency_graph: HashMap<String, Vec<String>>,
    reverse_dependencies: HashMap<String, Vec<String>>,
}

impl ReferenceMapper {
    pub fn new() -> Self {
        ReferenceMapper {
            formula_map: HashMap::new(),
            dependency_graph: HashMap::new(),
            reverse_dependencies: HashMap::new(),
        }
    }

    /// Register a formula and its dependencies
    pub fn register_formula(&mut self, cell_id: String, formula: Formula) {
        self.formula_map.insert(cell_id.clone(), formula.clone());

        // Build dependency graph
        let refs: Vec<String> = formula
            .references
            .iter()
            .map(|r| r.to_string())
            .collect();

        self.dependency_graph.insert(cell_id.clone(), refs.clone());

        // Build reverse dependencies
        for ref_id in refs {
            self.reverse_dependencies
                .entry(ref_id)
                .or_insert_with(Vec::new)
                .push(cell_id.clone());
        }
    }

    /// Get all cells that depend on a given cell
    pub fn get_dependents(&self, cell_id: &str) -> Vec<String> {
        self.reverse_dependencies
            .get(cell_id)
            .cloned()
            .unwrap_or_default()
    }

    /// Get all cells that a formula depends on
    pub fn get_dependencies(&self, cell_id: &str) -> Vec<String> {
        self.dependency_graph
            .get(cell_id)
            .cloned()
            .unwrap_or_default()
    }

    /// Detect circular references
    pub fn detect_circular_references(&self) -> Vec<Vec<String>> {
        let mut cycles = Vec::new();
        let mut visited = HashSet::new();
        let mut rec_stack = HashSet::new();

        for cell in self.formula_map.keys() {
            if !visited.contains(cell) {
                self._find_cycles_dfs(cell, &mut visited, &mut rec_stack, &mut cycles, Vec::new());
            }
        }

        cycles
    }

    fn _find_cycles_dfs(
        &self,
        node: &str,
        visited: &mut HashSet<String>,
        rec_stack: &mut HashSet<String>,
        cycles: &mut Vec<Vec<String>>,
        mut path: Vec<String>,
    ) {
        visited.insert(node.to_string());
        rec_stack.insert(node.to_string());
        path.push(node.to_string());

        if let Some(deps) = self.dependency_graph.get(node) {
            for dep in deps {
                if !visited.contains(dep) {
                    self._find_cycles_dfs(dep, visited, rec_stack, cycles, path.clone());
                } else if rec_stack.contains(dep) {
                    // Found cycle
                    let cycle_start = path.iter().position(|x| x == dep).unwrap_or(0);
                    cycles.push(path[cycle_start..].to_vec());
                }
            }
        }

        rec_stack.remove(node);
    }

    /// Calculate impact score for a cell change
    pub fn calculate_impact_score(&self, cell_id: &str) -> usize {
        let mut visited = HashSet::new();
        self._count_impacted_cells(cell_id, &mut visited)
    }

    fn _count_impacted_cells(&self, cell_id: &str, visited: &mut HashSet<String>) -> usize {
        if visited.contains(cell_id) {
            return 0;
        }

        visited.insert(cell_id.to_string());
        let dependents = self.get_dependents(cell_id);

        let mut count = 1;
        for dep in dependents {
            count += self._count_impacted_cells(&dep, visited);
        }

        count
    }

    /// Get formula complexity statistics
    pub fn get_complexity_stats(&self) -> HashMap<String, u32> {
        let mut stats = HashMap::new();

        let total_formulas = self.formula_map.len() as u32;
        let avg_complexity = self.formula_map.values().map(|f| f.complexity).sum::<u32>() / total_formulas.max(1);
        let max_complexity = self.formula_map.values().map(|f| f.complexity).max().unwrap_or(0);

        stats.insert("total_formulas".to_string(), total_formulas);
        stats.insert("average_complexity".to_string(), avg_complexity);
        stats.insert("max_complexity".to_string(), max_complexity);

        stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cell_reference_creation() {
        let ref_obj = CellReference::new("Sheet1".to_string(), "A".to_string(), 1);
        assert_eq!(ref_obj.sheet, "Sheet1");
        assert_eq!(ref_obj.row, 1);
    }

    #[test]
    fn test_formula_type_identification() {
        assert_eq!(FormulaExtractor::extract_formulas("=SUM(A1:A10)")[0].formula_type, "SUM");
        assert_eq!(FormulaExtractor::extract_formulas("=IF(A1>0,1,0)")[0].formula_type, "IF");
    }

    #[test]
    fn test_formula_complexity() {
        let formula = Formula::new("=IF(A1>0,SUM(B1:B10),0)".to_string());
        assert!(formula.complexity > 0);
    }

    #[test]
    fn test_reference_mapper_creation() {
        let mapper = ReferenceMapper::new();
        assert_eq!(mapper.formula_map.len(), 0);
    }

    #[test]
    fn test_dependency_tracking() {
        let mut mapper = ReferenceMapper::new();
        let mut formula = Formula::new("=A1+B1".to_string());
        formula.references = vec![
            CellReference::new("Sheet1".to_string(), "A".to_string(), 1),
            CellReference::new("Sheet1".to_string(), "B".to_string(), 1),
        ];

        mapper.register_formula("C1".to_string(), formula);
        let deps = mapper.get_dependencies("C1");
        assert_eq!(deps.len(), 2);
    }
}
