"""Smoke-test an installed (non-editable) pystreamxl wheel."""

import tempfile
from pathlib import Path

import pystreamxl
from pystreamxl import FormulaCell, detect_circular_references


def main() -> None:
    location = Path(pystreamxl.__file__).resolve()
    assert (
        "site-packages" in location.parts
    ), f"expected installed wheel, got {location}"
    assert pystreamxl.__version__ != "0.0.0+unknown", "wheel has no package metadata"

    cycles = detect_circular_references(
        [FormulaCell(0, 0, "=B1"), FormulaCell(0, 1, "=A1")]
    )
    assert cycles, "expected a cycle for A1 <-> B1"
    assert set(cycles[0]) == {"A1", "B1"}, cycles
    assert detect_circular_references([FormulaCell(0, 0, "=1+1")]) == []

    rows = [
        ["name", "value", "active"],
        ["alpha", 1.5, True],
        ['<tag> & "quote"', -2, False],
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "smoke.xlsx")
        pystreamxl.write(path, rows)
        result = list(pystreamxl.read(path))

    assert len(result) == len(rows), result
    assert result[0] == ["name", "value", "active"], result[0]
    assert result[1] == ["alpha", 1.5, True], result[1]
    assert result[2] == ['<tag> & "quote"', -2.0, False], result[2]

    print(f"wheel smoke OK: pystreamxl {pystreamxl.__version__} from {location}")


if __name__ == "__main__":
    main()
