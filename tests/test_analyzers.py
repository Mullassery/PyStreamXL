"""Tests for the Rust-backed formula analyzers (PYSTREAMXL-004)."""

from pystreamxl.analyzers import (
    CollaborationDetector,
    CrossSheetAnalyzer,
    IncrementalRecalculator,
)


def test_analyzers_are_importable_from_package_root():
    import pystreamxl

    assert pystreamxl.CrossSheetAnalyzer is CrossSheetAnalyzer
    assert pystreamxl.IncrementalRecalculator is IncrementalRecalculator
    assert pystreamxl.CollaborationDetector is CollaborationDetector


def test_cross_sheet_redundancy_detection():
    a = CrossSheetAnalyzer()
    a.add_sheet("S1")
    a.add_sheet("S2")
    a.add_formula("S1", "A1", "=SUM(B:B)")
    a.add_formula("S2", "B2", "=SUM(B:B)")

    a.detect_redundancies()

    assert a.redundancy_count == 1
    opps = a.consolidation_opportunities()
    assert opps and isinstance(opps[0][0], str)
    assert a.statistics()["num_sheets"] == 2.0


def test_cross_sheet_dependency_and_critical_paths():
    a = CrossSheetAnalyzer()
    a.add_sheet("S1")
    a.add_sheet("S2")
    a.add_formula("S1", "A1", "=S2!B1+1")
    a.add_formula("S2", "B1", "=10")

    a.analyze_dependencies()

    assert a.dependency_count >= 1
    assert isinstance(a.critical_paths(), list)


def test_incremental_recalculation_propagates():
    r = IncrementalRecalculator(0.0)  # every change propagates
    r.register_cell("A1", "")
    r.register_cell("B1", "=A1")
    r.add_dependency("B1", "A1")

    change = r.update_cell("A1", 5.0)
    assert change["cell_id"] == "A1"
    assert change["new_value"] == 5.0
    assert "B1" in change["affected_cells"]

    dirty = r.get_dirty_cells()
    assert "A1" in dirty and "B1" in dirty

    batch = r.recalculate_batch()
    assert batch.get("B1") == 5.0

    stats = r.recalc_stats()
    assert stats["active_cells"] == 2
    # dirty set cleared by the batch recalculation
    assert r.estimate_recalc_scope() == 0.0


def test_collaboration_detector_surface():
    d = CollaborationDetector()
    d.register_cell("A1", "")
    d.register_cell("B1", "")
    d.add_reference("A1", "B1")

    d.detect_collaboration_groups()
    d.identify_optimizations()

    assert d.statistics()["total_cells"] == 2.0
    assert isinstance(d.circular_dependencies(), list)
    assert isinstance(d.top_optimizations(5), list)
