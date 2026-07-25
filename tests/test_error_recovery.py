"""
Phase 5: Error Recovery & Validation Tests

Tests for:
- Error classification (severity, category)
- Detailed error reporting
- Recovery strategies
- Validation reports
- Error suggestions
"""

import pytest
from streamxl import (
    ErrorSeverity,
    ErrorCategory,
    RecoveryMode,
    CellError,
    ValidationReport,
    ErrorRecoveryHandler,
    ExcelValidationError,
)


class TestCellError:
    """Test individual cell error representation."""

    def test_cell_error_creation(self):
        """Create a cell error."""
        error = CellError(
            category=ErrorCategory.FORMULA_SYNTAX,
            message="Missing closing parenthesis",
            cell_ref="C5",
            severity=ErrorSeverity.RECOVERABLE,
        )
        assert error.category == ErrorCategory.FORMULA_SYNTAX
        assert error.message == "Missing closing parenthesis"
        assert error.cell_ref == "C5"
        assert error.severity == ErrorSeverity.RECOVERABLE

    def test_cell_error_with_location(self):
        """Cell error with row/column location."""
        error = CellError(
            category=ErrorCategory.CELL_FORMAT,
            message="Invalid format",
            row=4,
            col=2,
            severity=ErrorSeverity.RECOVERABLE,
        )
        assert error.row == 4
        assert error.col == 2

    def test_cell_error_with_suggestion(self):
        """Cell error with recovery suggestion."""
        error = CellError(
            category=ErrorCategory.FORMULA_SYNTAX,
            message="Unmatched parenthesis",
            suggestion="Add closing parenthesis",
            severity=ErrorSeverity.RECOVERABLE,
        )
        assert error.suggestion == "Add closing parenthesis"

    def test_cell_error_formatting(self):
        """Format error as string."""
        error = CellError(
            category=ErrorCategory.INVALID_STYLE,
            message="Style ID 999 not found",
            cell_ref="A1",
            severity=ErrorSeverity.RECOVERABLE,
            suggestion="Re-save file from Excel",
        )
        formatted = error.format_detailed()
        assert "invalid_style" in formatted
        assert "Style ID 999" in formatted
        assert "A1" in formatted
        assert "Re-save file" in formatted


class TestValidationReport:
    """Test validation report generation."""

    def test_report_creation(self):
        """Create a validation report."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            total_cells=100,
        )
        assert report.file_path == "test.xlsx"
        assert report.sheet_name == "Sheet1"
        assert report.total_cells == 100
        assert report.error_count() == 0
        assert report.warning_count() == 0

    def test_report_add_error(self):
        """Add error to report."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            total_cells=100,
        )
        error = CellError(
            category=ErrorCategory.FORMULA_SYNTAX,
            message="Syntax error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        report.add_error(error)
        assert report.error_count() == 1

    def test_report_add_warning(self):
        """Add warning to report."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            total_cells=100,
        )
        warning = CellError(
            category=ErrorCategory.PARSE_ERROR,
            message="Parse warning",
            severity=ErrorSeverity.WARNING,
        )
        report.add_error(warning)
        assert report.warning_count() == 1
        assert report.error_count() == 0

    def test_report_error_percentage(self):
        """Calculate error percentage."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            total_cells=100,
        )
        for i in range(10):
            error = CellError(
                category=ErrorCategory.CELL_FORMAT,
                message="Error",
                severity=ErrorSeverity.RECOVERABLE,
            )
            report.add_error(error)

        assert report.error_percentage() == 10.0

    def test_report_empty_error_percentage(self):
        """Error percentage with no cells."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            total_cells=0,
        )
        assert report.error_percentage() == 0.0

    def test_report_errors_by_category(self):
        """Group errors by category."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            total_cells=100,
        )
        for i in range(3):
            error = CellError(
                category=ErrorCategory.FORMULA_SYNTAX,
                message="Syntax error",
                severity=ErrorSeverity.RECOVERABLE,
            )
            report.add_error(error)

        for i in range(2):
            error = CellError(
                category=ErrorCategory.INVALID_STYLE,
                message="Style error",
                severity=ErrorSeverity.RECOVERABLE,
            )
            report.add_error(error)

        grouped = report.errors_by_category()
        assert len(grouped[ErrorCategory.FORMULA_SYNTAX]) == 3
        assert len(grouped[ErrorCategory.INVALID_STYLE]) == 2

    def test_report_summary_format(self):
        """Format report summary."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Data",
            total_cells=100,
        )
        error = CellError(
            category=ErrorCategory.CELL_FORMAT,
            message="Format error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        report.add_error(error)
        report.skipped_rows = 2

        summary = report.format_summary()
        assert "test.xlsx" in summary
        assert "Data" in summary
        assert "100" in summary
        assert "1" in summary  # 1 error
        assert "2" in summary  # 2 skipped rows

    def test_report_to_dict(self):
        """Convert report to dictionary."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
            total_cells=50,
        )
        error = CellError(
            category=ErrorCategory.FORMULA_SYNTAX,
            message="Syntax error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        report.add_error(error)

        data = report.to_dict()
        assert data["file_path"] == "test.xlsx"
        assert data["sheet_name"] == "Sheet1"
        assert data["total_cells"] == 50
        assert data["error_count"] == 1
        assert "formula_syntax" in data["errors_by_category"]


class TestErrorRecoveryHandler:
    """Test error recovery handling strategies."""

    def test_handler_fail_fast(self):
        """Fail immediately on any error."""
        handler = ErrorRecoveryHandler(mode=RecoveryMode.FAIL_FAST)
        error = CellError(
            category=ErrorCategory.FORMULA_SYNTAX,
            message="Error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        assert not handler.add_error(error)  # Should return False (stop)

    def test_handler_skip_non_fatal(self):
        """Skip non-fatal errors, continue."""
        handler = ErrorRecoveryHandler(mode=RecoveryMode.SKIP_NON_FATAL)
        error = CellError(
            category=ErrorCategory.FORMULA_SYNTAX,
            message="Error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        assert handler.add_error(error)  # Should return True (continue)

    def test_handler_max_errors(self):
        """Stop after max error count."""
        handler = ErrorRecoveryHandler(
            mode=RecoveryMode.SKIP_NON_FATAL,
            max_errors=2,
        )
        errors_added = []
        for i in range(4):
            error = CellError(
                category=ErrorCategory.FORMULA_SYNTAX,
                message="Error",
                severity=ErrorSeverity.RECOVERABLE,
            )
            result = handler.add_error(error)
            errors_added.append(result)

        # Should continue for first 2 errors, then stop
        assert errors_added[0]  # 1st error: continue
        assert errors_added[1]  # 2nd error: continue
        assert not errors_added[2]  # 3rd error: stop (exceeded max)

    def test_handler_should_skip_cell(self):
        """Determine if cell should be skipped."""
        handler = ErrorRecoveryHandler(mode=RecoveryMode.SKIP_NON_FATAL)
        error = CellError(
            category=ErrorCategory.CELL_FORMAT,
            message="Format error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        assert handler.should_skip_cell(error)

    def test_handler_recovery_suggestions(self):
        """Get recovery suggestions for error type."""
        handler = ErrorRecoveryHandler()

        # Formula error
        formula_error = CellError(
            category=ErrorCategory.FORMULA_SYNTAX,
            message="Formula error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        suggestions = handler.get_recovery_suggestions(formula_error)
        assert len(suggestions) > 0
        assert any("formula" in s.lower() for s in suggestions)

        # Circular reference
        circ_error = CellError(
            category=ErrorCategory.CIRCULAR_REFERENCE,
            message="Circular reference",
            severity=ErrorSeverity.WARNING,
        )
        suggestions = handler.get_recovery_suggestions(circ_error)
        assert len(suggestions) > 0

    def test_handler_with_report(self):
        """Handler with validation report."""
        report = ValidationReport(
            file_path="test.xlsx",
            sheet_name="Sheet1",
        )
        handler = ErrorRecoveryHandler(mode=RecoveryMode.SKIP_NON_FATAL)
        handler.report = report

        error = CellError(
            category=ErrorCategory.CELL_FORMAT,
            message="Format error",
            severity=ErrorSeverity.RECOVERABLE,
        )
        handler.add_error(error)

        assert report.error_count() == 1


class TestErrorSeverity:
    """Test error severity enum."""

    def test_severity_values(self):
        """Verify severity enum values."""
        assert ErrorSeverity.FATAL.value == "fatal"
        assert ErrorSeverity.RECOVERABLE.value == "recoverable"
        assert ErrorSeverity.WARNING.value == "warning"


class TestErrorCategory:
    """Test error category enum."""

    def test_category_values(self):
        """Verify category enum values."""
        assert ErrorCategory.ZIP_CORRUPTION.value == "zip_corruption"
        assert ErrorCategory.FORMULA_SYNTAX.value == "formula_syntax"
        assert ErrorCategory.CIRCULAR_REFERENCE.value == "circular_reference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
