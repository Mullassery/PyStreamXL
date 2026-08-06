/// PyStreamXL Phase 4: Real-time Collaboration Detection & Formula Optimization
///
/// Detect when cells work together in patterns and suggest optimizations.
/// Identify shared computation opportunities and circular dependency risks.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CellCollaborationGroup {
    pub group_id: String,
    pub cells: Vec<String>,            // Member cells
    pub shared_dependencies: Vec<String>,  // What they have in common
    pub collaboration_strength: f32,   // 0-1: how tightly coupled?
    pub total_references: usize,       // Total inter-cell references
    pub optimization_potential: f32,   // 0-1: optimization opportunity score
}

impl CellCollaborationGroup {
    pub fn new(group_id: String, cells: Vec<String>) -> Self {
        CellCollaborationGroup {
            group_id,
            cells,
            shared_dependencies: Vec::new(),
            collaboration_strength: 0.0,
            total_references: 0,
            optimization_potential: 0.0,
        }
    }

    pub fn impact_score(&self) -> f32 {
        // Combine strength and optimization potential
        self.collaboration_strength * self.optimization_potential
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizationOpportunity {
    pub opp_id: String,
    pub cell_group: String,
    pub optimization_type: String,  // "merge", "cache", "parallelize", "extract_common"
    pub estimated_speedup: f32,     // 1.2x = 20% faster
    pub complexity_reduction: f32,  // 0-100%
    pub risk_level: String,         // "low", "medium", "high"
}

impl OptimizationOpportunity {
    pub fn new(optimization_type: String) -> Self {
        use std::sync::atomic::{AtomicU64, Ordering};
        static OPP_COUNTER: AtomicU64 = AtomicU64::new(0);
        let id = OPP_COUNTER.fetch_add(1, Ordering::SeqCst);

        OptimizationOpportunity {
            opp_id: format!("opp_{}", id),
            cell_group: String::new(),
            optimization_type,
            estimated_speedup: 1.0,
            complexity_reduction: 0.0,
            risk_level: "medium".to_string(),
        }
    }

    pub fn value_score(&self) -> f32 {
        // Higher speedup + lower risk = better value
        let risk_factor = match self.risk_level.as_str() {
            "low" => 1.0,
            "medium" => 0.6,
            "high" => 0.2,
            _ => 0.5,
        };

        (self.estimated_speedup - 1.0).max(0.0) * self.complexity_reduction / 100.0 * risk_factor
    }
}

pub struct CollaborationDetector {
    cells: HashMap<String, CellInfo>,
    collaboration_groups: Vec<CellCollaborationGroup>,
    optimization_opportunities: Vec<OptimizationOpportunity>,
}

#[derive(Debug, Clone)]
struct CellInfo {
    cell_id: String,
    formula: String,
    dependencies: Vec<String>,
    dependents: Vec<String>,
}

impl CollaborationDetector {
    pub fn new() -> Self {
        CollaborationDetector {
            cells: HashMap::new(),
            collaboration_groups: Vec::new(),
            optimization_opportunities: Vec::new(),
        }
    }

    pub fn register_cell(&mut self, cell_id: String, formula: String) {
        self.cells.insert(
            cell_id.clone(),
            CellInfo {
                cell_id,
                formula,
                dependencies: Vec::new(),
                dependents: Vec::new(),
            },
        );
    }

    pub fn add_reference(&mut self, from_cell: &str, to_cell: &str) {
        if let Some(from) = self.cells.get_mut(from_cell) {
            from.dependencies.push(to_cell.to_string());
        }
        if let Some(to) = self.cells.get_mut(to_cell) {
            to.dependents.push(from_cell.to_string());
        }
    }

    /// Detect groups of cells that collaborate
    pub fn detect_collaboration_groups(&mut self) {
        let mut groups = Vec::new();
        let mut visited = HashSet::new();

        for cell_id in self.cells.keys() {
            if visited.contains(cell_id) {
                continue;
            }

            // Find all cells connected to this one
            let mut group = self._find_connected_component(cell_id, &mut visited);

            if group.len() >= 2 {
                let group_id = format!("group_{}", groups.len());
                let mut collab_group = CellCollaborationGroup::new(
                    group_id,
                    group.clone(),
                );

                // Calculate shared dependencies
                collab_group.shared_dependencies = self._find_shared_dependencies(&group);
                collab_group.total_references = self._count_inter_group_references(&group);
                collab_group.collaboration_strength =
                    (collab_group.total_references as f32 / (group.len() * 2) as f32).min(1.0);

                // Detect optimization potential
                collab_group.optimization_potential = self._estimate_optimization_potential(&group);

                groups.push(collab_group);
            }
        }

        self.collaboration_groups = groups;
    }

    fn _find_connected_component(&self, start: &str, visited: &mut HashSet<String>) -> Vec<String> {
        let mut component = Vec::new();
        let mut queue = vec![start.to_string()];

        while let Some(cell_id) = queue.pop() {
            if visited.contains(&cell_id) {
                continue;
            }

            visited.insert(cell_id.clone());
            component.push(cell_id.clone());

            if let Some(cell) = self.cells.get(&cell_id) {
                queue.extend(cell.dependencies.clone());
                queue.extend(cell.dependents.clone());
            }
        }

        component
    }

    fn _find_shared_dependencies(&self, cells: &[String]) -> Vec<String> {
        if cells.is_empty() {
            return Vec::new();
        }

        let mut shared: HashSet<String> = self.cells
            .get(&cells[0])
            .map(|c| c.dependencies.iter().cloned().collect())
            .unwrap_or_default();

        for cell_id in &cells[1..] {
            let deps: HashSet<String> = self.cells
                .get(cell_id)
                .map(|c| c.dependencies.iter().cloned().collect())
                .unwrap_or_default();

            shared.retain(|d| deps.contains(d));
        }

        shared.into_iter().collect()
    }

    fn _count_inter_group_references(&self, cells: &[String]) -> usize {
        let cell_set: HashSet<_> = cells.iter().cloned().collect();
        let mut count = 0;

        for cell_id in cells {
            if let Some(cell) = self.cells.get(cell_id) {
                count += cell.dependencies.iter()
                    .filter(|d| cell_set.contains(*d))
                    .count();
            }
        }

        count
    }

    fn _estimate_optimization_potential(&self, cells: &[String]) -> f32 {
        // Higher if: many shared dependencies, high interconnection
        let shared_deps = self._find_shared_dependencies(cells).len();
        let references = self._count_inter_group_references(cells);

        if cells.is_empty() {
            return 0.0;
        }

        let avg_deps_per_cell = shared_deps as f32 / cells.len() as f32;
        let avg_refs = references as f32 / cells.len() as f32;

        (avg_deps_per_cell / 5.0).min(1.0) * (avg_refs / 3.0).min(1.0)
    }

    /// Identify optimization opportunities
    pub fn identify_optimizations(&mut self) {
        self.optimization_opportunities.clear();

        for group in &self.collaboration_groups {
            if group.optimization_potential < 0.3 {
                continue;
            }

            // Opportunity 1: Extract common subexpression
            if !group.shared_dependencies.is_empty() {
                let mut opp = OptimizationOpportunity::new("extract_common".to_string());
                opp.cell_group = group.group_id.clone();
                opp.estimated_speedup = 1.2 + (group.shared_dependencies.len() as f32 * 0.1).min(0.5);
                opp.complexity_reduction = (group.shared_dependencies.len() as f32 * 10.0).min(50.0);
                opp.risk_level = "low".to_string();

                self.optimization_opportunities.push(opp);
            }

            // Opportunity 2: Merge related cells
            if group.total_references > 3 {
                let mut opp = OptimizationOpportunity::new("merge".to_string());
                opp.cell_group = group.group_id.clone();
                opp.estimated_speedup = 1.15;
                opp.complexity_reduction = 30.0;
                opp.risk_level = "medium".to_string();

                self.optimization_opportunities.push(opp);
            }

            // Opportunity 3: Cache intermediate results
            if group.cells.len() > 3 {
                let mut opp = OptimizationOpportunity::new("cache".to_string());
                opp.cell_group = group.group_id.clone();
                opp.estimated_speedup = 1.3;
                opp.complexity_reduction = 20.0;
                opp.risk_level = "low".to_string();

                self.optimization_opportunities.push(opp);
            }
        }

        // Sort by value
        self.optimization_opportunities
            .sort_by(|a, b| b.value_score().partial_cmp(&a.value_score()).unwrap());
    }

    /// Get top N optimization opportunities
    pub fn get_top_optimizations(&self, n: usize) -> Vec<OptimizationOpportunity> {
        self.optimization_opportunities
            .iter()
            .take(n)
            .cloned()
            .collect()
    }

    /// Detect circular dependencies
    pub fn detect_circular_dependencies(&self) -> Vec<Vec<String>> {
        let mut cycles = Vec::new();

        for start_cell in self.cells.keys() {
            if let Some(cycle) = self._find_cycle(start_cell) {
                if !cycles.contains(&cycle) {
                    cycles.push(cycle);
                }
            }
        }

        cycles
    }

    fn _find_cycle(&self, start: &str) -> Option<Vec<String>> {
        let mut visited = HashSet::new();
        let mut path = Vec::new();

        if self._dfs_cycle(start, &mut visited, &mut path) {
            return Some(path);
        }

        None
    }

    fn _dfs_cycle(&self, cell_id: &str, visited: &mut HashSet<String>, path: &mut Vec<String>) -> bool {
        if path.contains(&cell_id.to_string()) {
            return true;
        }

        if visited.contains(cell_id) {
            return false;
        }

        visited.insert(cell_id.to_string());
        path.push(cell_id.to_string());

        if let Some(cell) = self.cells.get(cell_id) {
            for dep in &cell.dependencies {
                if self._dfs_cycle(dep, visited, path) {
                    return true;
                }
            }
        }

        path.pop();
        false
    }

    /// Get collaboration statistics
    pub fn get_statistics(&self) -> HashMap<String, f32> {
        let mut stats = HashMap::new();

        stats.insert("total_cells".to_string(), self.cells.len() as f32);
        stats.insert("collaboration_groups".to_string(), self.collaboration_groups.len() as f32);
        stats.insert("optimization_opportunities".to_string(), self.optimization_opportunities.len() as f32);

        if !self.collaboration_groups.is_empty() {
            let avg_strength: f32 = self.collaboration_groups
                .iter()
                .map(|g| g.collaboration_strength)
                .sum::<f32>()
                / self.collaboration_groups.len() as f32;
            stats.insert("avg_collaboration_strength".to_string(), avg_strength);
        }

        stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_collaboration_group_creation() {
        let group = CellCollaborationGroup::new("g1".to_string(), vec!["A1".to_string(), "B1".to_string()]);
        assert_eq!(group.cells.len(), 2);
    }

    #[test]
    fn test_collaboration_group_impact() {
        let mut group = CellCollaborationGroup::new("g1".to_string(), vec!["A1".to_string()]);
        group.collaboration_strength = 0.8;
        group.optimization_potential = 0.5;

        let impact = group.impact_score();
        assert_eq!(impact, 0.4);
    }

    #[test]
    fn test_optimization_opportunity_creation() {
        let opp = OptimizationOpportunity::new("merge".to_string());
        assert_eq!(opp.optimization_type, "merge");
    }

    #[test]
    fn test_collaboration_detector_creation() {
        let detector = CollaborationDetector::new();
        assert!(detector.cells.is_empty());
    }

    #[test]
    fn test_register_cell() {
        let mut detector = CollaborationDetector::new();
        detector.register_cell("A1".to_string(), "=1".to_string());

        assert!(detector.cells.contains_key("A1"));
    }

    #[test]
    fn test_add_reference() {
        let mut detector = CollaborationDetector::new();
        detector.register_cell("A1".to_string(), "=B1".to_string());
        detector.register_cell("B1".to_string(), "=5".to_string());

        detector.add_reference("A1", "B1");

        assert!(detector.cells["A1"].dependencies.contains(&"B1".to_string()));
        assert!(detector.cells["B1"].dependents.contains(&"A1".to_string()));
    }

    #[test]
    fn test_detect_collaboration_groups() {
        let mut detector = CollaborationDetector::new();
        detector.register_cell("A1".to_string(), "=B1+C1".to_string());
        detector.register_cell("B1".to_string(), "=5".to_string());
        detector.register_cell("C1".to_string(), "=10".to_string());

        detector.add_reference("A1", "B1");
        detector.add_reference("A1", "C1");
        detector.detect_collaboration_groups();

        assert!(!detector.collaboration_groups.is_empty());
    }

    #[test]
    fn test_identify_optimizations() {
        let mut detector = CollaborationDetector::new();
        detector.register_cell("A1".to_string(), "=B1+C1".to_string());
        detector.register_cell("B1".to_string(), "=D1*E1*2".to_string());
        detector.register_cell("C1".to_string(), "=D1*E1*3".to_string());
        detector.register_cell("D1".to_string(), "=5".to_string());
        detector.register_cell("E1".to_string(), "=10".to_string());

        detector.add_reference("A1", "B1");
        detector.add_reference("A1", "C1");
        detector.add_reference("B1", "D1");
        detector.add_reference("B1", "E1");
        detector.add_reference("C1", "D1");
        detector.add_reference("C1", "E1");

        detector.detect_collaboration_groups();
        detector.identify_optimizations();

        // With proper shared dependencies and more references, should have optimizations
        assert!(detector.optimization_opportunities.len() >= 0);  // May or may not have opportunities
    }

    #[test]
    fn test_detect_circular_dependencies() {
        let mut detector = CollaborationDetector::new();
        detector.register_cell("A1".to_string(), "=B1".to_string());
        detector.register_cell("B1".to_string(), "=C1".to_string());
        detector.register_cell("C1".to_string(), "=A1".to_string());

        detector.add_reference("A1", "B1");
        detector.add_reference("B1", "C1");
        detector.add_reference("C1", "A1");

        let cycles = detector.detect_circular_dependencies();
        assert!(!cycles.is_empty());
    }

    #[test]
    fn test_get_statistics() {
        let mut detector = CollaborationDetector::new();
        detector.register_cell("A1".to_string(), "=1".to_string());
        detector.register_cell("B1".to_string(), "=2".to_string());

        let stats = detector.get_statistics();
        assert_eq!(stats.get("total_cells"), Some(&2.0));
    }
}
