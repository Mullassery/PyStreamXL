"""Pre-flight formula validation wired into write()."""

from __future__ import annotations

import pytest

import pystreamxl


def test_write_rejects_circular_formulas_when_enabled(tmp_path) -> None:
    path = tmp_path / "cycle.xlsx"
    with pytest.raises(ValueError, match="Circular formula dependencies"):
        pystreamxl.write(str(path), [["=B1", "=A1"]], validate_formulas=True)
    assert not path.exists()


def test_write_allows_acyclic_formulas_when_enabled(tmp_path) -> None:
    path = tmp_path / "ok.xlsx"
    pystreamxl.write(str(path), [["=B1+1", 2.0]], validate_formulas=True)
    assert path.exists()


def test_write_default_preserves_streaming_behavior(tmp_path) -> None:
    path = tmp_path / "default.xlsx"
    pystreamxl.write(str(path), [["=B1", "=A1"]])
    assert path.exists()


def test_validate_formula_rows_detects_cycles() -> None:
    assert pystreamxl.validate_formula_rows([["=B1", "=A1"]])
    assert pystreamxl.validate_formula_rows([["=B1+1", 2.0]]) == []
