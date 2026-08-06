/// PyStreamXL Phase 3: Incremental Recalculation - Real-time formula updates
///
/// Enable fast, targeted recalculation of formulas when their dependencies change.
/// Uses invalidation graph to minimize recalc scope.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecalcNode {
    pub cell_id: String,
    pub formula: String,
    pub current_value: f64,
    pub dependencies: Vec<String>,      // Cells this depends on
    pub dependents: Vec<String>,        // Cells that depend on this
    pub last_recalc_time: u64,
    pub recalc_count: usize,
}

impl RecalcNode {
    pub fn new(cell_id: String, formula: String) -> Self {
        RecalcNode {
            cell_id,
            formula,
            current_value: 0.0,
            dependencies: Vec::new(),
            dependents: Vec::new(),
            last_recalc_time: 0,
            recalc_count: 0,
        }
    }

    pub fn add_dependency(&mut self, dep: String) {
        if !self.dependencies.contains(&dep) {
            self.dependencies.push(dep);
        }
    }

    pub fn add_dependent(&mut self, dep: String) {
        if !self.dependents.contains(&dep) {
            self.dependents.push(dep);
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecalcChange {
    pub cell_id: String,
    pub old_value: f64,
    pub new_value: f64,
    pub affected_cells: Vec<String>,    // All cells transitively affected
    pub recalc_time_ms: u64,
}

pub struct IncrementalRecalculator {
    cells: HashMap<String, RecalcNode>,
    change_log: Vec<RecalcChange>,
    dirty_cells: HashSet<String>,
    recalc_threshold: f64,              // Min relative change to trigger propagation
}

impl IncrementalRecalculator {
    pub fn new(threshold: f64) -> Self {
        IncrementalRecalculator {
            cells: HashMap::new(),
            change_log: Vec::new(),
            dirty_cells: HashSet::new(),
            recalc_threshold: threshold,
        }
    }

    pub fn register_cell(&mut self, cell_id: String, formula: String) {
        self.cells.insert(cell_id.clone(), RecalcNode::new(cell_id, formula));
    }

    pub fn add_dependency(&mut self, cell: &str, dep: &str) {
        if let Some(node) = self.cells.get_mut(cell) {
            node.add_dependency(dep.to_string());
        }
        if let Some(dep_node) = self.cells.get_mut(dep) {
            dep_node.add_dependent(cell.to_string());
        }
    }

    /// Update a cell value and propagate changes
    pub fn update_cell(&mut self, cell_id: &str, new_value: f64) -> RecalcChange {
        let start_time = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        let old_value = self.cells.get(cell_id).map(|c| c.current_value).unwrap_or(0.0);

        // Update the cell
        if let Some(node) = self.cells.get_mut(cell_id) {
            node.current_value = new_value;
            node.last_recalc_time = start_time;
            node.recalc_count += 1;
        }

        // Check if change is significant enough to propagate
        let relative_change = if old_value.abs() > 1e-10 {
            ((new_value - old_value) / old_value.abs()).abs()
        } else {
            if new_value.abs() > 1e-10 { 1.0 } else { 0.0 }
        };

        let mut affected_cells = vec![cell_id.to_string()];

        // Only propagate if change is significant
        if relative_change >= self.recalc_threshold {
            self.dirty_cells.insert(cell_id.to_string());
            let transitively_affected = self._propagate_changes(cell_id);
            affected_cells.extend(transitively_affected);
        }

        let recalc_time = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64 - start_time;

        let change = RecalcChange {
            cell_id: cell_id.to_string(),
            old_value,
            new_value,
            affected_cells,
            recalc_time_ms: recalc_time,
        };

        self.change_log.push(change.clone());
        change
    }

    fn _propagate_changes(&mut self, cell_id: &str) -> Vec<String> {
        let mut affected = Vec::new();
        let mut queue: VecDeque<String> = VecDeque::new();
        queue.push_back(cell_id.to_string());
        let mut visited = HashSet::new();

        while let Some(current) = queue.pop_front() {
            if visited.contains(&current) {
                continue;
            }
            visited.insert(current.clone());

            if let Some(node) = self.cells.get(&current) {
                for dependent in &node.dependents {
                    if !visited.contains(dependent) {
                        self.dirty_cells.insert(dependent.clone());
                        affected.push(dependent.clone());
                        queue.push_back(dependent.clone());
                    }
                }
            }
        }

        affected
    }

    /// Get all cells that need recalculation
    pub fn get_dirty_cells(&self) -> Vec<String> {
        self.dirty_cells.iter().cloned().collect()
    }

    /// Batch recalculate dirty cells
    pub fn recalculate_batch(&mut self) -> HashMap<String, f64> {
        let mut results = HashMap::new();
        let dirty: Vec<String> = self.dirty_cells.iter().cloned().collect();

        for cell_id in dirty {
            // Collect dependency values first
            let deps = self.cells.get(&cell_id)
                .map(|n| n.dependencies.clone())
                .unwrap_or_default();

            let new_value: f64 = deps.iter()
                .filter_map(|dep| self.cells.get(dep).map(|c| c.current_value))
                .sum();

            if let Some(node) = self.cells.get_mut(&cell_id) {
                node.current_value = new_value;
                node.last_recalc_time = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_millis() as u64;
                node.recalc_count += 1;

                results.insert(cell_id, new_value);
            }
        }

        self.dirty_cells.clear();
        results
    }

    /// Get recalculation statistics
    pub fn get_recalc_stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();
        let total_recalcs: usize = self.cells.values().map(|c| c.recalc_count).sum();
        let total_changes = self.change_log.len();

        stats.insert("total_recalcs".to_string(), total_recalcs);
        stats.insert("total_changes".to_string(), total_changes);
        stats.insert("active_cells".to_string(), self.cells.len());

        if total_changes > 0 {
            let avg_affected: f64 = self.change_log.iter()
                .map(|c| c.affected_cells.len() as f64)
                .sum::<f64>() / total_changes as f64;
            stats.insert("avg_affected_cells".to_string(), avg_affected as usize);
        }

        stats
    }

    /// Estimate recalc scope (% of cells affected)
    pub fn estimate_recalc_scope(&self) -> f32 {
        if self.cells.is_empty() {
            return 0.0;
        }
        (self.dirty_cells.len() as f32 / self.cells.len() as f32) * 100.0
    }

    /// Get change history
    pub fn get_change_history(&self, limit: usize) -> Vec<RecalcChange> {
        self.change_log.iter().rev().take(limit).cloned().collect()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecalcProfile {
    pub operation_name: String,
    pub cells_affected: usize,
    pub recalc_time_ms: u64,
    pub efficiency_score: f32,     // Time / cells_affected
}

pub struct RecalcOptimizer {
    profiles: Vec<RecalcProfile>,
}

impl RecalcOptimizer {
    pub fn new() -> Self {
        RecalcOptimizer {
            profiles: Vec::new(),
        }
    }

    pub fn profile_operation(&mut self, name: String, cells_affected: usize, time_ms: u64) {
        let efficiency = if cells_affected > 0 {
            (time_ms as f32 / cells_affected as f32)
        } else {
            0.0
        };

        self.profiles.push(RecalcProfile {
            operation_name: name,
            cells_affected,
            recalc_time_ms: time_ms,
            efficiency_score: efficiency,
        });
    }

    pub fn get_slowest_operations(&self, n: usize) -> Vec<RecalcProfile> {
        let mut sorted = self.profiles.clone();
        sorted.sort_by(|a, b| b.recalc_time_ms.cmp(&a.recalc_time_ms));
        sorted.into_iter().take(n).collect()
    }

    pub fn get_optimization_opportunities(&self) -> Vec<String> {
        let mut opportunities = Vec::new();

        // Find operations with poor efficiency (high time per cell)
        for profile in &self.profiles {
            if profile.efficiency_score > 10.0 {  // >10ms per cell is slow
                opportunities.push(format!(
                    "Optimize {}: {}ms for {} cells",
                    profile.operation_name, profile.recalc_time_ms, profile.cells_affected
                ));
            }
        }

        opportunities
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_recalc_node_creation() {
        let node = RecalcNode::new("A1".to_string(), "=SUM(A2:A3)".to_string());
        assert_eq!(node.cell_id, "A1");
        assert_eq!(node.recalc_count, 0);
    }

    #[test]
    fn test_recalc_node_dependencies() {
        let mut node = RecalcNode::new("A1".to_string(), "=A2+A3".to_string());
        node.add_dependency("A2".to_string());
        node.add_dependency("A3".to_string());

        assert_eq!(node.dependencies.len(), 2);
    }

    #[test]
    fn test_incremental_recalculator_creation() {
        let calc = IncrementalRecalculator::new(0.01);
        assert!(calc.dirty_cells.is_empty());
    }

    #[test]
    fn test_register_cell() {
        let mut calc = IncrementalRecalculator::new(0.01);
        calc.register_cell("A1".to_string(), "=1+1".to_string());

        assert!(calc.cells.contains_key("A1"));
    }

    #[test]
    fn test_add_dependency() {
        let mut calc = IncrementalRecalculator::new(0.01);
        calc.register_cell("A1".to_string(), "=A2+A3".to_string());
        calc.register_cell("A2".to_string(), "=5".to_string());

        calc.add_dependency("A1", "A2");

        let a1 = calc.cells.get("A1").unwrap();
        assert!(a1.dependencies.contains(&"A2".to_string()));
    }

    #[test]
    fn test_update_cell() {
        let mut calc = IncrementalRecalculator::new(0.01);
        calc.register_cell("A1".to_string(), "=5".to_string());

        let change = calc.update_cell("A1", 10.0);
        assert_eq!(change.cell_id, "A1");
        assert_eq!(change.new_value, 10.0);
    }

    #[test]
    fn test_propagate_changes() {
        let mut calc = IncrementalRecalculator::new(0.01);
        calc.register_cell("A1".to_string(), "=5".to_string());
        calc.register_cell("A2".to_string(), "=A1*2".to_string());
        calc.register_cell("A3".to_string(), "=A2+1".to_string());

        calc.add_dependency("A2", "A1");
        calc.add_dependency("A3", "A2");

        calc.update_cell("A1", 100.0);
        let dirty = calc.get_dirty_cells();

        assert!(dirty.contains(&"A2".to_string()));
        assert!(dirty.contains(&"A3".to_string()));
    }

    #[test]
    fn test_recalculate_batch() {
        let mut calc = IncrementalRecalculator::new(0.01);
        calc.register_cell("A1".to_string(), "=5".to_string());
        calc.register_cell("A2".to_string(), "=A1*2".to_string());

        calc.add_dependency("A2", "A1");
        calc.update_cell("A1", 10.0);

        let results = calc.recalculate_batch();
        assert!(results.contains_key("A2"));
    }

    #[test]
    fn test_recalc_stats() {
        let mut calc = IncrementalRecalculator::new(0.01);
        calc.register_cell("A1".to_string(), "=1".to_string());
        calc.update_cell("A1", 2.0);

        let stats = calc.get_recalc_stats();
        assert!(stats.contains_key("total_changes"));
    }

    #[test]
    fn test_estimate_recalc_scope() {
        let mut calc = IncrementalRecalculator::new(0.01);
        calc.register_cell("A1".to_string(), "=1".to_string());
        calc.register_cell("A2".to_string(), "=2".to_string());
        calc.update_cell("A1", 5.0);

        let scope = calc.estimate_recalc_scope();
        assert!(scope > 0.0);
    }

    #[test]
    fn test_recalc_optimizer() {
        let mut optimizer = RecalcOptimizer::new();
        optimizer.profile_operation("op1".to_string(), 10, 50);
        optimizer.profile_operation("op2".to_string(), 20, 30);

        let slowest = optimizer.get_slowest_operations(1);
        assert_eq!(slowest[0].operation_name, "op1");
    }

    #[test]
    fn test_optimization_opportunities() {
        let mut optimizer = RecalcOptimizer::new();
        optimizer.profile_operation("slow_op".to_string(), 1, 50);

        let opportunities = optimizer.get_optimization_opportunities();
        assert!(!opportunities.is_empty());
    }
}
