"""Security utilities for PyStreamXL - ZIP bomb and DOS protection."""

from pathlib import Path
from typing import Optional, Union
import logging
import os

logger = logging.getLogger(__name__)

# Security limits for DOS prevention
MAX_FILE_SIZE = 512 * 1024 * 1024  # 512MB file size limit
MAX_ENTRY_SIZE = 512 * 1024 * 1024  # 512MB per ZIP entry
MAX_TOTAL_SIZE = 1024 * 1024 * 1024  # 1GB total decompressed
MAX_COMPRESSION_RATIO = 30.0  # Max 30:1 compression (ZIP bomb threshold)


class SecurityError(ValueError):
    """Raised when security validation fails."""
    pass


def validate_xlsx_path(
    path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Validate Excel file path.

    Args:
        path: File path provided by user
        base_dir: Optional directory the resolved path must stay inside of.
            When provided, the path is confined with a real check performed
            *after* resolution: ``resolve()`` first collapses any ``..``
            segments and symlinks, then the fully-resolved path is compared
            against the fully-resolved ``base_dir`` with
            ``os.path.commonpath()``. A previous version of this function
            checked for the literal substring ``".."`` after resolving the
            path, which can never fire on a real traversal input (resolution
            already removes ``..`` segments) and provided no actual
            confinement. When ``base_dir`` is ``None`` (the default), no
            confinement is enforced and any resolved path is accepted, same
            as before this fix — pass ``base_dir`` explicitly when the
            caller has a real trust boundary (e.g. a server confining
            uploads to one directory).

    Returns:
        Validated Path object

    Raises:
        SecurityError: If path is invalid, dangerous, or (when base_dir is
            given) escapes base_dir.
    """
    path = Path(path).resolve()

    # Ensure it's an Excel file
    if path.suffix.lower() not in ['.xlsx', '.xls']:
        raise SecurityError(f"Must be Excel file (.xlsx or .xls), got: {path.suffix}")

    if base_dir is not None:
        resolved_base = Path(base_dir).resolve()
        try:
            inside_base = os.path.commonpath([str(path), str(resolved_base)]) == str(
                resolved_base
            )
        except ValueError:
            # Raised e.g. on Windows when the paths are on different drives.
            inside_base = False
        if not inside_base:
            raise SecurityError(
                f"Path traversal not allowed: '{path}' resolves outside of "
                f"base directory '{resolved_base}'"
            )

    return path


def validate_read_path(
    path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Validate path for reading (must exist, be file, and not exceed size limits).

    This prevents DOS attacks via extremely large files or ZIP bombs. Pass
    ``base_dir`` to also enforce that the resolved path stays inside a
    specific directory (see :func:`validate_xlsx_path`).
    """
    path = validate_xlsx_path(path, base_dir=base_dir)

    if not path.exists():
        raise SecurityError(f"File not found: {path}")

    if not path.is_file():
        raise SecurityError(f"Not a file: {path}")

    # Check file size before attempting to read (DOS prevention)
    try:
        file_size = os.path.getsize(path)
    except (OSError, ValueError) as e:
        raise SecurityError(f"Cannot determine file size: {e}")

    if file_size > MAX_FILE_SIZE:
        raise SecurityError(
            f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes). "
            f"This limit prevents denial-of-service attacks. "
            f"If this is a legitimate large file, contact support."
        )

    if file_size == 0:
        raise SecurityError("File is empty (0 bytes)")

    return path


def validate_write_path(
    path: Union[str, Path], base_dir: Optional[Union[str, Path]] = None
) -> Path:
    """Validate path for writing (parent must exist). Pass ``base_dir`` to
    also enforce that the resolved path stays inside a specific directory
    (see :func:`validate_xlsx_path`)."""
    path = validate_xlsx_path(path, base_dir=base_dir)

    if not path.parent.exists():
        raise SecurityError(f"Parent directory doesn't exist: {path.parent}")

    # Warn if file will be overwritten
    if path.exists():
        logger.warning("File will be overwritten: %s", path)

    return path


def get_security_limits() -> dict:
    """Return current security limits for documentation/debugging."""
    return {
        "max_file_size": MAX_FILE_SIZE,
        "max_entry_size": MAX_ENTRY_SIZE,
        "max_total_size": MAX_TOTAL_SIZE,
        "max_compression_ratio": MAX_COMPRESSION_RATIO,
    }


# Leading characters that Excel, LibreOffice Calc, Google Sheets, and other
# spreadsheet applications interpret as the start of a formula when a CSV
# cell is opened/imported. This is the well-known "CSV injection" /
# "formula injection" vulnerability class (CWE-1236 / OWASP CSV injection):
# an attacker who controls a cell value (e.g. "=cmd|'/c calc'!A0" or
# "@SUM(1+1)*cmd|' /c calc'!A0") can achieve formula execution, data
# exfiltration, or arbitrary command execution in the victim's spreadsheet
# application once the exported CSV is opened.
CSV_FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value):
    """
    Neutralize CSV/Excel formula-injection payloads in a single cell value.

    Any *string* value that begins with ``=``, ``+``, ``-``, ``@``, TAB, or
    CR is prefixed with a single quote (``'``) so spreadsheet applications
    render the cell as literal text instead of evaluating it as a formula.
    This is the standard, widely-used mitigation for CSV/formula injection.

    Non-string values (``int``, ``float``, ``bool``, ``None``, dates, ...)
    are returned unchanged: they are written by the CSV encoder as plain
    numeric/literal tokens and cannot carry a formula payload.

    Args:
        value: The raw cell value that will be written to a CSV file.

    Returns:
        The value, unchanged if safe, or prefixed with ``'`` if it starts
        with a formula-injection trigger character.

    Examples:
        >>> sanitize_csv_cell("=cmd|'/c calc'!A0")
        "'=cmd|'/c calc'!A0"
        >>> sanitize_csv_cell("Alice")
        'Alice'
        >>> sanitize_csv_cell(-42)
        -42
    """
    if not isinstance(value, str):
        return value
    if value and value[0] in CSV_FORMULA_TRIGGER_CHARS:
        return "'" + value
    return value
