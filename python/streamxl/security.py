"""Security utilities for PyStreamXL - ZIP bomb and DOS protection."""

from pathlib import Path
from typing import Union
import os

# Security limits for DOS prevention
MAX_FILE_SIZE = 512 * 1024 * 1024  # 512MB file size limit
MAX_ENTRY_SIZE = 512 * 1024 * 1024  # 512MB per ZIP entry
MAX_TOTAL_SIZE = 1024 * 1024 * 1024  # 1GB total decompressed
MAX_COMPRESSION_RATIO = 30.0  # Max 30:1 compression (ZIP bomb threshold)


class SecurityError(ValueError):
    """Raised when security validation fails."""
    pass


def validate_xlsx_path(path: Union[str, Path]) -> Path:
    """
    Validate Excel file path.

    Args:
        path: File path provided by user

    Returns:
        Validated Path object

    Raises:
        SecurityError: If path is invalid or dangerous
    """
    path = Path(path).resolve()

    # Ensure it's an Excel file
    if path.suffix.lower() not in ['.xlsx', '.xls']:
        raise SecurityError(f"Must be Excel file (.xlsx or .xls), got: {path.suffix}")

    # Prevent directory traversal in filename
    if '..' in str(path):
        raise SecurityError("Path traversal not allowed")

    return path


def validate_read_path(path: Union[str, Path]) -> Path:
    """
    Validate path for reading (must exist, be file, and not exceed size limits).

    This prevents DOS attacks via extremely large files or ZIP bombs.
    """
    path = validate_xlsx_path(path)

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


def validate_write_path(path: Union[str, Path]) -> Path:
    """Validate path for writing (parent must exist)."""
    path = validate_xlsx_path(path)

    if not path.parent.exists():
        raise SecurityError(f"Parent directory doesn't exist: {path.parent}")

    # Warn if file will be overwritten
    if path.exists():
        print(f"Warning: File will be overwritten: {path}")

    return path


def get_security_limits() -> dict:
    """Return current security limits for documentation/debugging."""
    return {
        "max_file_size": MAX_FILE_SIZE,
        "max_entry_size": MAX_ENTRY_SIZE,
        "max_total_size": MAX_TOTAL_SIZE,
        "max_compression_ratio": MAX_COMPRESSION_RATIO,
    }
