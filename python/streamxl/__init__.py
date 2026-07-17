from .api import read, stream, write, writer, sheets, read_all, append
from .core import XlsxWriter
from .security import SecurityError, get_security_limits

# Formula preservation support (unblocks finance teams)
from ._formula_support import (
    FormulaAnalyzer,
    FormulaPreserver,
    FormulaSubstitution,
    FormulaType,
    FormulaCell,
    FormulaMapping,
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
]
__version__ = "1.1.0"  # Security hardening release
