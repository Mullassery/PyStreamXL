"""Pre-flight formula dependency-cycle detection."""

from __future__ import annotations

from pystreamxl import FormulaCell, detect_circular_references


def test_detects_three_cell_cycle() -> None:
    cycles = detect_circular_references(
        [
            FormulaCell(0, 0, "=B1"),
            FormulaCell(0, 1, "=C1"),
            FormulaCell(0, 2, "=A1"),
        ]
    )
    assert cycles
    assert {label for label in cycles[0]} == {"A1", "B1", "C1"}


def test_acyclic_formulas_pass() -> None:
    assert (
        detect_circular_references(
            [
                FormulaCell(0, 0, "=B1"),
                FormulaCell(0, 1, "=C1"),
                FormulaCell(0, 2, "=1"),
            ]
        )
        == []
    )


def test_self_reference_is_a_cycle() -> None:
    cycles = detect_circular_references([FormulaCell(0, 0, "=A1")])
    assert cycles == [["A1", "A1"]]


def test_range_references_are_expanded() -> None:
    # A1 sums A2:A3; A2 and A3 both depend on A1 -> a cycle through the range.
    cycles = detect_circular_references(
        [
            FormulaCell(0, 0, "=SUM(A2:A3)"),
            FormulaCell(1, 0, "=A1"),
            FormulaCell(2, 0, "=A1"),
        ]
    )
    assert cycles


def test_external_cell_references_are_ignored() -> None:
    assert detect_circular_references([FormulaCell(0, 0, "=Z99")]) == []
