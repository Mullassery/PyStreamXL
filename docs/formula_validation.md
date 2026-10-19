# Formula dependency validation

Static pre-flight checks for circular formula dependencies. This is **not**
formula evaluation: it never computes cell values and does not resolve dynamic
references such as `INDIRECT` or `OFFSET`.

## API

```python
from pystreamxl import FormulaCell, detect_circular_references, validate_formula_rows

# Cells use 0-based (row, col): (0, 0) is A1.
cycles = detect_circular_references([
    FormulaCell(0, 0, "=B1"),
    FormulaCell(0, 1, "=A1"),
])
# [['A1', 'B1', 'A1']]
```

`validate_formula_rows(rows)` accepts the same row-major shape as
`pystreamxl.write`:

```python
cycles = validate_formula_rows([["=B1", "=A1"]])
```

Gate export before writing anything:

```python
pystreamxl.write("out.xlsx", rows, validate_formulas=True)
# raises ValueError listing the cycles; the file is not created
```

`validate_formulas=True` is opt-in. The default path remains streaming and
unchanged; enabling it materializes `rows` so the whole dependency graph can be
checked before the writer starts.

## What is detected

- Multi-cell cycles (`A1 → B1 → C1 → A1`).
- Self-references (`A1 = "=A1"`).
- Ranges, expanded to every cell (`A1:A10`, `$A$1:$A$10`).
- Absolute markers (`$`) are ignored for dependency identity.

## What is not detected

- Dynamic references (`INDIRECT`, `OFFSET`, named ranges).
- Cross-sheet semantics. Sheet-qualified references are reduced to their cell
  part, so `Sheet2!A1` may be matched against a same-sheet `A1` (a false
  positive or missed cross-sheet edge).
- External workbooks.

## Implementation

A directed graph is built from formula cells to referenced cells, then a DFS
reports back-edges. Complexity is `O(V + E)` in the number of formula cells and
references. Cycles are de-duplicated and returned as label paths.
