"""File integrity and atomic write utilities."""

import hashlib
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of file for integrity checking.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)
        
    Returns:
        Hex digest of file hash
    """
    hasher = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def atomic_write(output_path: Path, temp_path: Path) -> None:
    """
    Atomically move temp file to output path.
    
    Prevents partial/corrupted files if process crashes.
    
    Args:
        output_path: Final destination
        temp_path: Temporary file location
        
    Raises:
        IOError: If move fails
    """
    if not temp_path.exists():
        raise IOError(f"Temporary file not found: {temp_path}")
    
    try:
        # Atomic move (rename) on same filesystem
        temp_path.replace(output_path)
        logger.info(f"Atomically wrote: {output_path}")
    except OSError as e:
        logger.error(f"Atomic write failed: {e}")
        # Clean up temp file
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise IOError(f"Failed to write {output_path}: {e}") from e


def verify_file_integrity(file_path: Path, expected_hash: Optional[str] = None) -> bool:
    """
    Verify file integrity via hash.
    
    Args:
        file_path: File to verify
        expected_hash: Expected hash value (if provided, verify matches)
        
    Returns:
        True if file is valid (or hash matches)
        
    Raises:
        IOError: If file doesn't exist or is corrupted
    """
    if not file_path.exists():
        raise IOError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise IOError(f"Not a file: {file_path}")
    
    # Calculate actual hash
    actual_hash = calculate_file_hash(file_path)
    
    # Verify if expected hash provided
    if expected_hash and actual_hash != expected_hash:
        raise IOError(
            f"File integrity check failed: {file_path}\n"
            f"  Expected: {expected_hash}\n"
            f"  Actual: {actual_hash}"
        )
    
    logger.info(f"File integrity verified: {file_path}")
    return True


class AtomicFileWriter:
    """Context manager for atomic file writes."""
    
    def __init__(self, output_path: Path, temp_dir: Optional[Path] = None):
        """
        Initialize atomic writer.
        
        Args:
            output_path: Final destination
            temp_dir: Directory for temporary file (defaults to output parent)
        """
        self.output_path = Path(output_path)
        self.temp_dir = Path(temp_dir or self.output_path.parent)
        self.temp_path = self.temp_dir / f".{self.output_path.name}.tmp"
        self.file_handle = None
    
    def __enter__(self):
        """Open temporary file for writing."""
        try:
            self.file_handle = open(self.temp_path, "wb")
            return self.file_handle
        except IOError as e:
            logger.error(f"Failed to open temp file: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close and atomically move to final location."""
        if self.file_handle:
            self.file_handle.close()
        
        if exc_type is not None:
            # Error occurred, clean up temp file
            try:
                self.temp_path.unlink()
            except OSError:
                pass
            return False
        
        # Success - move to final location
        atomic_write(self.output_path, self.temp_path)
        return True


def safe_file_write(output_path: Path, write_func, *args, **kwargs) -> Path:
    """
    Safely write file with integrity checking.
    
    Args:
        output_path: Final destination path
        write_func: Function that writes to file (receives file handle)
        *args, **kwargs: Arguments for write_func
        
    Returns:
        Path to written file
        
    Raises:
        IOError: If write or integrity check fails
    """
    with AtomicFileWriter(output_path) as f:
        write_func(f, *args, **kwargs)
    
    # Verify file was written
    verify_file_integrity(output_path)
    return output_path
