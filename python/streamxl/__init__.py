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
]
__version__ = "1.2.0"  # Formula tools + Comments (Phase 3-4)
