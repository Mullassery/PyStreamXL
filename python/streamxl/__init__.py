from .api import read, stream, write, writer, sheets, read_all, append
from .core import XlsxWriter
from .security import SecurityError, get_security_limits

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
    "read", "stream", "write", "writer", "sheets", "read_all", "append", "XlsxWriter",
    # Security
    "SecurityError", "get_security_limits",
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
__version__ = "1.2.0"  # Formulas + Tools + Comments + Error Recovery (Phases 1,3-5)
