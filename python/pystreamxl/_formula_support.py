"""
Formula preservation and management for Excel files.

Supports reading, writing, and modifying formulas in XLSX files.
This CRITICAL feature unblocks finance/accounting teams.
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class FormulaType(Enum):
    """Types of Excel formulas."""
    SUM = "sum"
    AVERAGE = "average"
    IF = "if"
    VLOOKUP = "vlookup"
    INDEX_MATCH = "index_match"
    COUNT = "count"
    PRODUCT = "product"
    SUBTOTAL = "subtotal"
    CUSTOM = "custom"


@dataclass
class FormulaCell:
    """Represents a cell containing a formula."""
    row: int
    col: int
    formula: str  # e.g., "=SUM(A1:A10)"
    value: Optional[float] = None  # Calculated value (if available)
    formula_type: FormulaType = FormulaType.CUSTOM
    error: Optional[str] = None  # e.g., "#DIV/0!"


@dataclass
class FormulaMapping:
    """Mapping of cell references in formulas."""
    original_cell: Tuple[int, int]
    mapped_cell: Tuple[int, int]
    formula_before: str
    formula_after: str


class FormulaAnalyzer:
    """Analyzes and extracts information from Excel formulas."""

    # Regex patterns for common formulas
    FORMULA_PATTERNS = {
        FormulaType.SUM: r"=SUM\s*\(",
        FormulaType.AVERAGE: r"=AVERAGE\s*\(",
        FormulaType.IF: r"=IF\s*\(",
        FormulaType.VLOOKUP: r"=VLOOKUP\s*\(",
        FormulaType.INDEX_MATCH: r"=INDEX\s*\(.+MATCH",
        FormulaType.COUNT: r"=COUNT.{0,2}\s*\(",
        FormulaType.PRODUCT: r"=PRODUCT\s*\(",
        FormulaType.SUBTOTAL: r"=SUBTOTAL\s*\(",
    }

    @staticmethod
    def is_formula(value: Any) -> bool:
        """Check if value is a formula."""
        if isinstance(value, str):
            return value.startswith("=")
        return False

    @staticmethod
    def get_formula_type(formula: str) -> FormulaType:
        """Determine formula type from formula string."""
        formula_upper = formula.upper()
        for ftype, pattern in FormulaAnalyzer.FORMULA_PATTERNS.items():
            if re.search(pattern, formula_upper):
                return ftype
        return FormulaType.CUSTOM

    @staticmethod
    def extract_references(formula: str) -> List[str]:
        """Extract cell references from formula."""
        # Pattern for cell references (A1, $A$1, etc.)
        pattern = r"\$?[A-Z]+\$?[0-9]+"
        refs = re.findall(pattern, formula)
        return list(set(refs))  # Unique references

    @staticmethod
    def extract_ranges(formula: str) -> List[Tuple[str, str]]:
        """Extract range references from formula (e.g., A1:A10)."""
        pattern = r"(\$?[A-Z]+\$?[0-9]+):(\$?[A-Z]+\$?[0-9]+)"
        ranges = re.findall(pattern, formula)
        return ranges

    @staticmethod
    def is_circular_reference(formula: str, cell_ref: str) -> bool:
        """Check if formula has circular reference to own cell."""
        refs = FormulaAnalyzer.extract_references(formula)
        return cell_ref.upper() in [r.upper() for r in refs]


class FormulaPreserver:
    """Preserves formulas when reading/writing Excel files."""

    def __init__(self, preserve_calculated_values: bool = False):
        """
        Args:
            preserve_calculated_values: Keep pre-calculated values alongside formulas
        """
        self.preserve_calculated_values = preserve_calculated_values
        self.formulas: Dict[Tuple[int, int], FormulaCell] = {}
        self.analyzer = FormulaAnalyzer()

    def add_formula(self, row: int, col: int, formula: str, value: Optional[float] = None):
        """Register a formula to preserve."""
        if not self.analyzer.is_formula(formula):
            raise ValueError(f"Invalid formula: {formula}. Must start with '='")

        formula_type = self.analyzer.get_formula_type(formula)
        cell = FormulaCell(
            row=row,
            col=col,
            formula=formula,
            value=value,
            formula_type=formula_type
        )
        self.formulas[(row, col)] = cell
        logger.debug(f"Added formula at ({row}, {col}): {formula}")

    def get_formula(self, row: int, col: int) -> Optional[str]:
        """Get formula at cell, if exists."""
        if (row, col) in self.formulas:
            return self.formulas[(row, col)].formula
        return None

    def update_references(self, row_offset: int = 0, col_offset: int = 0) -> List[FormulaMapping]:
        """
        Update cell references in all formulas (e.g., after inserting rows/columns).

        Args:
            row_offset: Number of rows to shift references
            col_offset: Number of columns to shift references

        Returns:
            List of formula updates
        """
        updates = []

        for (row, col), cell in self.formulas.items():
            old_formula = cell.formula
            new_formula = self._shift_references(old_formula, row_offset, col_offset)

            if old_formula != new_formula:
                updates.append(FormulaMapping(
                    original_cell=(row, col),
                    mapped_cell=(row + row_offset, col + col_offset),
                    formula_before=old_formula,
                    formula_after=new_formula
                ))
                cell.formula = new_formula

        logger.info(f"Updated {len(updates)} formula references")
        return updates

    def validate_formulas(self) -> Dict[str, List[str]]:
        """
        Validate all formulas for potential issues.

        Returns:
            Dict mapping issue type to list of problematic formulas
        """
        issues = {
            "circular_references": [],
            "invalid_ranges": [],
            "unmatched_parentheses": [],
        }

        for (row, col), cell in self.formulas.items():
            formula = cell.formula
            cell_ref = self._index_to_cell_ref(row, col)

            # Check for circular references
            if self.analyzer.is_circular_reference(formula, cell_ref):
                issues["circular_references"].append(f"({row}, {col}): {formula}")

            # Check for unmatched parentheses
            if formula.count("(") != formula.count(")"):
                issues["unmatched_parentheses"].append(f"({row}, {col}): {formula}")

        return {k: v for k, v in issues.items() if v}

    def export_formulas(self) -> Dict[str, Any]:
        """Export all formulas for backup/migration."""
        return {
            "formulas": {
                f"({row},{col})": {
                    "formula": cell.formula,
                    "type": cell.formula_type.value,
                    "value": cell.value,
                }
                for (row, col), cell in self.formulas.items()
            },
            "total_formulas": len(self.formulas),
        }

    def import_formulas(self, data: Dict[str, Any]):
        """Import formulas from export format."""
        for cell_str, cell_data in data.get("formulas", {}).items():
            # Parse cell coordinate string "(<row>,<col>)"
            row, col = map(int, cell_str.strip("()").split(","))
            self.add_formula(
                row=row,
                col=col,
                formula=cell_data["formula"],
                value=cell_data.get("value")
            )

    @staticmethod
    def _shift_references(formula: str, row_offset: int, col_offset: int) -> str:
        """Shift cell references in formula."""
        if row_offset == 0 and col_offset == 0:
            return formula

        def shift_cell_ref(match):
            ref = match.group(0)
            # Parse absolute/relative
            is_col_abs = ref.startswith("$")
            rest = ref[1:] if is_col_abs else ref

            col_part = ""
            row_part = ""
            for char in rest:
                if char.isalpha():
                    col_part += char
                else:
                    row_part = rest[len(col_part):]
                    break

            is_row_abs = row_part.startswith("$")
            row_num = int(row_part.lstrip("$")) if row_part else 1

            if not is_col_abs:
                col_num = FormulaPreserver._col_to_num(col_part) + col_offset
                col_part = FormulaPreserver._num_to_col(col_num)

            if not is_row_abs:
                row_num += row_offset

            new_ref = ""
            if is_col_abs:
                new_ref += "$"
            new_ref += col_part
            if is_row_abs:
                new_ref += "$"
            new_ref += str(row_num)

            return new_ref

        # Replace cell references (non-absolute only)
        pattern = r"\$?[A-Z]+\$?[0-9]+"
        return re.sub(pattern, shift_cell_ref, formula)

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
    def _index_to_cell_ref(row: int, col: int) -> str:
        """Convert (row, col) index to cell reference."""
        col_letter = FormulaPreserver._num_to_col(col + 1)
        return f"{col_letter}{row + 1}"


class FormulaSubstitution:
    """Find and replace in formulas while maintaining references."""

    @staticmethod
    def substitute(formula: str, find: str, replace: str,
                  case_sensitive: bool = False) -> str:
        """
        Replace text in formula, preserving cell references.

        Args:
            formula: Formula to modify
            find: Text to find
            replace: Replacement text
            case_sensitive: Whether to match case

        Returns:
            Updated formula
        """
        if not case_sensitive:
            find_lower = find.lower()
            formula_lower = formula.lower()
            if find_lower not in formula_lower:
                return formula

        # Don't replace inside cell references
        pattern = r"[A-Z]+[0-9]+"  # Cell references
        parts = re.split(f"({pattern})", formula)

        result = []
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Non-reference part
                if case_sensitive:
                    part = part.replace(find, replace)
                else:
                    # Case-insensitive replacement
                    import re as regex_module
                    part = regex_module.sub(
                        re.escape(find),
                        replace,
                        part,
                        flags=re.IGNORECASE
                    )
            result.append(part)

        return "".join(result)

    @staticmethod
    def substitute_range(formula: str, old_range: str, new_range: str) -> str:
        """
        Replace range references in formula (e.g., A1:A10 → C5:C15).

        Args:
            formula: Formula containing range
            old_range: Old range (e.g., "A1:A10")
            new_range: New range (e.g., "C5:C15")

        Returns:
            Updated formula
        """
        pattern = re.escape(old_range)
        return re.sub(pattern, new_range, formula, flags=re.IGNORECASE)
