from .api import read, stream, write, writer, sheets, read_all, append, conditional_formats
from .core import XlsxWriter
from .security import SecurityError, get_security_limits, sanitize_csv_cell

# Formula support (v1.2.0+)
from ._formula_support import (
    FormulaAnalyzer,
    FormulaPreserver,
    FormulaSubstitution,
    FormulaType,
    FormulaCell,
    FormulaMapping,
)
# Phase 3: Formula Tools
from .formula_reference_mapper import FormulaReferenceMapper
from .formula_io import FormulaSerializer
# Phase 5: Error Recovery & Validation
from .error_recovery import (
    ErrorSeverity,
    ErrorCategory,
    RecoveryMode,
    CellError,
    ValidationReport,
    ErrorRecoveryHandler,
    ExcelValidationError,
    validate_excel_file,
)

__all__ = [
    "read", "stream", "write", "writer", "sheets", "read_all", "append", "conditional_formats", "XlsxWriter",
    # Security
    "SecurityError", "get_security_limits", "sanitize_csv_cell",
    # Formula support (v1.2.0+)
    "FormulaAnalyzer",
    "FormulaPreserver",
    "FormulaSubstitution",
    "FormulaType",
    "FormulaCell",
    "FormulaMapping",
    # Phase 3: Formula Tools (v1.2.0+)
    "FormulaReferenceMapper",
    "FormulaSerializer",
    # Phase 5: Error Recovery & Validation (v1.2.0+)
    "ErrorSeverity",
    "ErrorCategory",
    "RecoveryMode",
    "CellError",
    "ValidationReport",
    "ErrorRecoveryHandler",
    "ExcelValidationError",
    "validate_excel_file",
]
__version__ = "5.2.0"
