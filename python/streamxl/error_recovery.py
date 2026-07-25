"""
Error Recovery and Validation - Handle errors gracefully with detailed diagnostics.

Provides:
- Error classification (fatal vs recoverable)
- Detailed diagnostic messages
- Recovery strategies (fail-fast vs skip-non-fatal)
- Validation report generation
- Cell-level error tracking
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for parsing errors."""
    FATAL = "fatal"           # Must stop reading
    RECOVERABLE = "recoverable"  # Can skip cell/row and continue
    WARNING = "warning"       # Continue but flag for attention


class ErrorCategory(Enum):
    """Categories of errors."""
    ZIP_CORRUPTION = "zip_corruption"
    MISSING_FILE = "missing_file"
    XML_PARSING = "xml_parsing"
    CELL_FORMAT = "cell_format"
    FORMULA_SYNTAX = "formula_syntax"
    CIRCULAR_REFERENCE = "circular_reference"
    INVALID_STYLE = "invalid_style"
    INVALID_STRING = "invalid_string"
    COMMENT_ERROR = "comment_error"
    PARSE_ERROR = "parse_error"


class RecoveryMode(Enum):
    """Strategies for handling errors during reading."""
    FAIL_FAST = "fail_fast"          # Stop on first error
    SKIP_ROW = "skip_row"            # Skip problematic row, continue
    SKIP_SHEET = "skip_sheet"        # Skip problematic sheet, continue
    SKIP_NON_FATAL = "skip_non_fatal"  # Skip non-fatal errors, keep data


@dataclass
class CellError:
    """Error encountered in a specific cell."""
    category: ErrorCategory
    message: str
    cell_ref: Optional[str] = None
    row: Optional[int] = None
    col: Optional[int] = None
    severity: ErrorSeverity = ErrorSeverity.WARNING
    suggestion: Optional[str] = None

    def format_detailed(self) -> str:
        """Format error with full context."""
        lines = [
            f"❌ {self.category.value}",
            f"   {self.message}",
        ]

        if self.cell_ref or self.row is not None:
            lines.append("📍 Location:")
            if self.cell_ref:
                lines.append(f"   Cell: {self.cell_ref}")
            if self.row is not None:
                lines.append(f"   Row: {self.row + 1}")
            if self.col is not None:
                lines.append(f"   Column: {self.col + 1}")

        lines.append(f"⚠️  Severity: {self.severity.value}")

        if self.suggestion:
            lines.append("💡 Suggestion:")
            lines.append(f"   {self.suggestion}")

        return "\n".join(lines)


@dataclass
class ValidationReport:
    """Report of validation issues in a workbook."""
    file_path: str
    sheet_name: str
    total_cells: int = 0
    errors: List[CellError] = field(default_factory=list)
    warnings: List[CellError] = field(default_factory=list)
    skipped_rows: int = 0
    skipped_cells: int = 0

    def add_error(self, error: CellError) -> None:
        """Add an error to the report."""
        if error.severity == ErrorSeverity.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)

    def has_fatal_errors(self) -> bool:
        """Check if there are fatal errors."""
        return any(e.severity == ErrorSeverity.FATAL for e in self.errors)

    def has_recoverable_errors(self) -> bool:
        """Check if there are recoverable errors."""
        return any(e.severity == ErrorSeverity.RECOVERABLE for e in self.errors)

    def error_count(self) -> int:
        """Get count of errors (excluding warnings)."""
        return len(self.errors)

    def warning_count(self) -> int:
        """Get count of warnings."""
        return len(self.warnings)

    def error_percentage(self) -> float:
        """Get percentage of cells with errors."""
        if self.total_cells == 0:
            return 0.0
        return (self.error_count() / self.total_cells) * 100

    def errors_by_category(self) -> Dict[ErrorCategory, List[CellError]]:
        """Group errors by category."""
        grouped = {}
        for error in self.errors:
            if error.category not in grouped:
                grouped[error.category] = []
            grouped[error.category].append(error)
        return grouped

    def format_summary(self) -> str:
        """Format a summary report."""
        lines = [
            f"📊 Validation Report: {self.file_path} ({self.sheet_name})",
            "",
            f"Total cells: {self.total_cells}",
            f"Errors: {self.error_count()} ({self.error_percentage():.1f}%)",
            f"Warnings: {self.warning_count()}",
            f"Skipped rows: {self.skipped_rows}",
            f"Skipped cells: {self.skipped_cells}",
        ]

        if self.errors:
            lines.append("")
            lines.append("Errors by category:")
            for category, errors in self.errors_by_category().items():
                lines.append(f"  {category.value}: {len(errors)}")

        return "\n".join(lines)

    def format_detailed(self) -> str:
        """Format detailed error list."""
        lines = [self.format_summary()]

        if self.errors:
            lines.append("")
            lines.append("Detailed errors:")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"\n{i}. {error.format_detailed()}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"\n{i}. {warning.format_detailed()}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "file_path": self.file_path,
            "sheet_name": self.sheet_name,
            "total_cells": self.total_cells,
            "error_count": self.error_count(),
            "warning_count": self.warning_count(),
            "error_percentage": self.error_percentage(),
            "skipped_rows": self.skipped_rows,
            "skipped_cells": self.skipped_cells,
            "errors_by_category": {
                cat.value: len(errors)
                for cat, errors in self.errors_by_category().items()
            },
            "errors": [
                {
                    "category": e.category.value,
                    "message": e.message,
                    "cell_ref": e.cell_ref,
                    "severity": e.severity.value,
                    "suggestion": e.suggestion,
                }
                for e in self.errors
            ],
        }


class ExcelValidationError(Exception):
    """Exception raised when Excel file validation fails."""

    def __init__(self, message: str, report: Optional[ValidationReport] = None):
        super().__init__(message)
        self.report = report


class ErrorRecoveryHandler:
    """Handle errors during Excel reading with configurable recovery strategies."""

    def __init__(
        self,
        mode: RecoveryMode = RecoveryMode.SKIP_NON_FATAL,
        max_errors: int = 100,
        max_warnings: int = 1000,
    ):
        """
        Initialize error handler.

        Args:
            mode: Recovery strategy to use
            max_errors: Maximum errors before giving up
            max_warnings: Maximum warnings to collect
        """
        self.mode = mode
        self.max_errors = max_errors
        self.max_warnings = max_warnings
        self.report: Optional[ValidationReport] = None
        self.error_count = 0

    def add_error(self, error: CellError) -> bool:
        """
        Add an error and decide whether to continue.

        Returns:
            True if should continue, False if should stop
        """
        if self.report:
            self.report.add_error(error)

        if error.severity == ErrorSeverity.FATAL:
            if self.mode == RecoveryMode.FAIL_FAST:
                return False
            self.error_count += 1
            return self.error_count <= self.max_errors

        elif error.severity == ErrorSeverity.RECOVERABLE:
            if self.mode == RecoveryMode.FAIL_FAST:
                return False
            self.error_count += 1
            if self.error_count > self.max_errors:
                return False  # Exceeded max errors, stop
            if self.mode == RecoveryMode.SKIP_NON_FATAL:
                return True  # Skip this cell/row, continue
            return True

        return True  # Continue on warnings

    def should_skip_cell(self, error: CellError) -> bool:
        """Determine if a cell should be skipped based on error and mode."""
        if error.severity == ErrorSeverity.FATAL:
            return self.mode != RecoveryMode.FAIL_FAST
        if error.severity == ErrorSeverity.RECOVERABLE:
            return self.mode in (
                RecoveryMode.SKIP_ROW,
                RecoveryMode.SKIP_NON_FATAL,
            )
        return False

    def get_recovery_suggestions(self, error: CellError) -> List[str]:
        """Get suggested recovery actions for an error."""
        suggestions = []

        if error.category == ErrorCategory.FORMULA_SYNTAX:
            suggestions.extend([
                "Open file in Excel to auto-correct formula",
                "Check formula syntax manually",
                "Use FormulaAnalyzer to validate formula",
            ])

        elif error.category == ErrorCategory.CIRCULAR_REFERENCE:
            suggestions.extend([
                "Identify and remove circular reference",
                "Use INDIRECT() or other workarounds",
                "Restructure calculation order",
            ])

        elif error.category == ErrorCategory.INVALID_STYLE:
            suggestions.extend([
                "Re-save file from Excel to rebuild styles",
                "Remove custom styles and reapply",
            ])

        elif error.category == ErrorCategory.ZIP_CORRUPTION:
            suggestions.extend([
                "Try to open and re-save file in Excel",
                "Use recovery tools if available",
                "Restore from backup",
            ])

        return suggestions


def validate_excel_file(
    file_path: str,
    mode: RecoveryMode = RecoveryMode.SKIP_NON_FATAL,
) -> ValidationReport:
    """
    Validate an Excel file and return detailed report.

    Args:
        file_path: Path to Excel file
        mode: Error recovery mode

    Returns:
        ValidationReport with findings
    """
    import streamxl

    report = ValidationReport(file_path=file_path, sheet_name="All")

    try:
        # Try to read file with metadata to detect errors
        rows = list(
            streamxl.read(file_path, with_formulas=True)
        )
        report.total_cells = sum(len(row) for row in rows)

        # Check for common issues
        for row_idx, row in enumerate(rows):
            for col_idx, cell in enumerate(row):
                if isinstance(cell, dict):
                    # Check for error values
                    if isinstance(cell.get("value"), str):
                        val = cell["value"]
                        if val.startswith("#"):
                            error = CellError(
                                category=ErrorCategory.PARSE_ERROR,
                                message=f"Error value in cell: {val}",
                                cell_ref=f"{_num_to_col(col_idx)}{row_idx + 1}",
                                row=row_idx,
                                col=col_idx,
                                severity=ErrorSeverity.WARNING,
                            )
                            report.add_error(error)

    except Exception as e:
        error = CellError(
            category=ErrorCategory.PARSE_ERROR,
            message=str(e),
            severity=ErrorSeverity.FATAL,
        )
        report.add_error(error)

    return report


def _num_to_col(num: int) -> str:
    """Convert 0-indexed column number to letter."""
    result = ""
    num += 1  # Convert to 1-indexed
    while num > 0:
        num -= 1
        result = chr(ord("A") + (num % 26)) + result
        num //= 26
    return result
