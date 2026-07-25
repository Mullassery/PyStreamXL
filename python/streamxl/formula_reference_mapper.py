"""
Formula Reference Mapping - Extract and modify cell references in formulas.

Enables:
- Extracting all cell references from a formula
- Finding ranges (A1:A10)
- Mapping references when rows/columns are inserted
- Preserving absolute vs relative references
"""

import re
from typing import List, Tuple, Optional


class FormulaReferenceMapper:
    """Extract and modify cell references in Excel formulas."""

    # Regex pattern for cell references (A1, $A$1, $A1, A$1)
    CELL_REF_PATTERN = r'\$?[A-Z]+\$?[0-9]+'
    # Regex pattern for ranges (A1:A10, $A$1:$B$10, etc)
    RANGE_PATTERN = r'(\$?[A-Z]+\$?[0-9]+):(\$?[A-Z]+\$?[0-9]+)'

    @staticmethod
    def extract_cell_refs(formula: str) -> List[str]:
        """
        Extract all cell references from a formula.

        Args:
            formula: Excel formula (e.g., "=SUM(A1:A10, C5)")

        Returns:
            List of unique cell references (e.g., ['A1', 'A10', 'C5'])

        Examples:
            >>> extract_cell_refs("=A1+B2")
            ['A1', 'B2']
            >>> extract_cell_refs("=SUM(A1:A10)")
            ['A1', 'A10']
            >>> extract_cell_refs("=$A$1+B2")
            ['$A$1', 'B2']
        """
        # Remove the leading "=" if present
        formula_text = formula.lstrip("=")
        refs = re.findall(FormulaReferenceMapper.CELL_REF_PATTERN, formula_text)
        return list(set(refs))  # Return unique refs

    @staticmethod
    def extract_ranges(formula: str) -> List[Tuple[str, str]]:
        """
        Extract range references from a formula.

        Args:
            formula: Excel formula (e.g., "=SUM(A1:A10, C5:C15)")

        Returns:
            List of tuples (start, end) for each range

        Examples:
            >>> extract_ranges("=SUM(A1:A10)")
            [('A1', 'A10')]
            >>> extract_ranges("=SUM(A1:A10, C5:C15)")
            [('A1', 'A10'), ('C5', 'C15')]
        """
        formula_text = formula.lstrip("=")
        ranges = re.findall(FormulaReferenceMapper.RANGE_PATTERN, formula_text)
        return ranges

    @staticmethod
    def map_cell_coordinates(
        formula: str, row_offset: int = 0, col_offset: int = 0
    ) -> str:
        """
        Adjust cell references in formula by row/column offset.

        Preserves absolute references ($A$1 stays $A$1).
        Shifts relative references (A1 becomes C2 if col_offset=2, row_offset=1).

        Args:
            formula: Excel formula
            row_offset: Number of rows to shift (can be negative)
            col_offset: Number of columns to shift (can be negative)

        Returns:
            Updated formula with shifted references

        Examples:
            >>> map_cell_coordinates("=A1+B2", row_offset=1, col_offset=2)
            '=C2+D3'
            >>> map_cell_coordinates("=$A$1+B2", row_offset=1, col_offset=2)
            '=$A$1+D3'  # Absolute reference unchanged
        """
        if row_offset == 0 and col_offset == 0:
            return formula

        def shift_cell_ref(match):
            ref = match.group(0)
            return FormulaReferenceMapper._shift_single_ref(
                ref, row_offset, col_offset
            )

        formula_text = formula.lstrip("=")
        shifted = re.sub(
            FormulaReferenceMapper.CELL_REF_PATTERN, shift_cell_ref, formula_text
        )
        return f"={shifted}"

    @staticmethod
    def _shift_single_ref(ref: str, row_offset: int, col_offset: int) -> str:
        """
        Shift a single cell reference by row/column offset.

        Examples:
            _shift_single_ref("A1", 1, 2) → "C2"
            _shift_single_ref("$A$1", 1, 2) → "$A$1"  (absolute, unchanged)
            _shift_single_ref("$A1", 1, 2) → "$C1"  (col absolute, row shifts)
            _shift_single_ref("A$1", 1, 2) → "C$1"  (col relative, row absolute)
        """
        # Parse column and row parts with their absolute flags
        col_absolute = ref.startswith("$")
        ref_without_first_dollar = ref[1:] if col_absolute else ref

        # Check if row part is absolute
        row_absolute = "$" in ref_without_first_dollar

        if row_absolute:
            # Format: A$1 or $A$1
            col_part, row_part = FormulaReferenceMapper._parse_col_row(
                ref_without_first_dollar.replace("$", "")
            )
        else:
            # Format: A1 or $A1
            col_part, row_part = FormulaReferenceMapper._parse_col_row(ref_without_first_dollar)

        # Convert to numbers
        col_num = FormulaReferenceMapper._col_to_num(col_part)
        row_num = int(row_part) if row_part else 1

        # Apply offset (only if not absolute)
        if not col_absolute:
            col_num += col_offset
        if not row_absolute:
            row_num += row_offset

        # Convert back to letters/numbers
        if col_num < 1:
            col_num = 1  # Prevent negative columns
        if row_num < 1:
            row_num = 1  # Prevent negative rows

        new_col = FormulaReferenceMapper._num_to_col(col_num)
        new_row = str(row_num)

        # Reconstruct with absolute markers
        result = ""
        if col_absolute:
            result += "$"
        result += new_col
        if row_absolute:
            result += "$"
        result += new_row

        return result

    @staticmethod
    def _parse_col_row(ref: str) -> Tuple[str, str]:
        """Parse 'A1' into ('A', '1')."""
        match = re.match(r"([A-Z]+)([0-9]+)", ref)
        if match:
            return match.group(1), match.group(2)
        return "", ""

    @staticmethod
    def _col_to_num(col: str) -> int:
        """Convert column letter (A, Z, AA) to number (1, 26, 27)."""
        result = 0
        for char in col:
            result = result * 26 + (ord(char) - ord("A") + 1)
        return result

    @staticmethod
    def _num_to_col(num: int) -> str:
        """Convert column number (1, 26, 27) to letter (A, Z, AA)."""
        result = ""
        while num > 0:
            num -= 1
            result = chr(ord("A") + (num % 26)) + result
            num //= 26
        return result

    @staticmethod
    def get_affected_cells(formula: str) -> List[Tuple[int, int]]:
        """
        Get list of (row, col) tuples that this formula depends on.

        Returns addresses as 0-indexed tuples.

        Examples:
            >>> get_affected_cells("=A1+B2")
            [(0, 0), (1, 1)]  # A1=(0,0), B2=(1,1)
        """
        refs = FormulaReferenceMapper.extract_cell_refs(formula)
        cells = []
        for ref in refs:
            col, row = FormulaReferenceMapper._parse_col_row(ref.replace("$", ""))
            if col and row:
                col_num = FormulaReferenceMapper._col_to_num(col)
                row_num = int(row)
                cells.append((row_num - 1, col_num - 1))  # Convert to 0-indexed
        return cells

    @staticmethod
    def substitute_reference(
        formula: str, old_ref: str, new_ref: str, case_sensitive: bool = True
    ) -> str:
        """
        Replace a specific cell reference in a formula.

        Args:
            formula: Excel formula
            old_ref: Reference to replace (e.g., "A1")
            new_ref: Replacement reference (e.g., "C5")
            case_sensitive: Whether to match case

        Returns:
            Updated formula

        Examples:
            >>> substitute_reference("=A1+B2", "A1", "C5")
            '=C5+B2'
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        # Use word boundaries to avoid partial matches
        pattern = r"\b" + re.escape(old_ref) + r"\b"
        return re.sub(pattern, new_ref, formula, flags=flags)
