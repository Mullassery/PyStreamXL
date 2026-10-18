"""Formula-analysis tools backed by Rust (`streamxl-core`).

These three analyzers were implemented and unit-tested in the Rust core but
were not reachable from Python until now (PYSTREAMXL-004):

- :class:`CrossSheetAnalyzer` — cross-sheet dependency tracking, redundant
  formula detection, consolidation/critical-path hints.
- :class:`IncrementalRecalculator` — invalidation-graph-based targeted
  recalculation when a cell changes, with a dirty-cell set and change log.
- :class:`CollaborationDetector` — groups of cells that co-vary, optimization
  opportunities (merge/cache/parallelize/extract_common), and circular
  dependency detection.

They operate on formula strings you register explicitly; they do not read a
workbook themselves (use :func:`pystreamxl.read` / :func:`stream` for that).
"""

from __future__ import annotations

from ._core import (
    CollaborationDetectorPy as CollaborationDetector,
    CrossSheetAnalyzerPy as CrossSheetAnalyzer,
    IncrementalRecalculatorPy as IncrementalRecalculator,
)

__all__ = [
    "CollaborationDetector",
    "CrossSheetAnalyzer",
    "IncrementalRecalculator",
]
