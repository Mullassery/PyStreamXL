"""User-friendly error messages for Excel operations."""


class ExcelError:
    """Excel file operation error with recovery."""
    
    def __init__(self, title: str, message: str, recovery: list = None):
        self.title = title
        self.message = message
        self.recovery = recovery or []
    
    def format(self) -> str:
        """Format error."""
        lines = [f"\n❌ {self.title}\n", f"   {self.message}\n"]
        if self.recovery:
            lines.append("   🔧 Recovery steps:")
            for i, step in enumerate(self.recovery, 1):
                lines.append(f"      {i}. {step}")
        return "\n".join(lines)
    
    def __str__(self) -> str:
        return self.format()


# Read errors
FILE_NOT_FOUND = ExcelError(
    title="Excel File Not Found",
    message="Cannot find the specified Excel file.",
    recovery=[
        "Check file path: ls /path/to/file.xlsx",
        "Verify file exists and extension is .xlsx or .xls",
        "Use absolute path to avoid directory confusion",
        "Check file permissions: chmod 644 /path/to/file.xlsx",
    ]
)

CORRUPTED_EXCEL_FILE = ExcelError(
    title="Excel File Appears Corrupted",
    message="Cannot read Excel file. May be damaged or incomplete.",
    recovery=[
        "Try opening in Excel/Sheets to see if readable",
        "Check file integrity: file /path/to/file.xlsx",
        "Re-download file if from external source",
        "Try older backup if available",
    ]
)

INVALID_SHEET_NAME = ExcelError(
    title="Sheet Not Found",
    message="Specified sheet name does not exist in workbook.",
    recovery=[
        "List available sheets: pystreamxl.sheets('file.xlsx')",
        "Check sheet name spelling (case-sensitive)",
        "Try sheet index instead: read('file.xlsx', sheet=0)",
        "Verify sheet wasn't deleted or renamed",
    ]
)

ENCODING_ERROR = ExcelError(
    title="Character Encoding Error",
    message="Cannot decode file. May contain unsupported characters.",
    recovery=[
        "Verify file is valid XLSX (Office Open XML) format",
        "Check if file is actually XLSX or misnamed XLS",
        "Try opening in Excel and re-saving as XLSX",
        "Check for corrupted headers or embedded data",
    ]
)

# Write errors
OUTPUT_DIR_NOT_FOUND = ExcelError(
    title="Output Directory Not Found",
    message="Cannot write file. Output directory doesn't exist.",
    recovery=[
        "Create directory: mkdir -p /path/to/directory",
        "Verify path is correct: pwd",
        "Check directory permissions: chmod 755 /path/to/directory",
        "Ensure you have write permissions",
    ]
)

WRITE_PERMISSION_DENIED = ExcelError(
    title="Permission Denied - Cannot Write File",
    message="Insufficient permissions to write to output location.",
    recovery=[
        "Check file permissions: ls -la /path/to/file.xlsx",
        "Make file writable: chmod 644 /path/to/file.xlsx",
        "Try different output directory",
        "Ensure not writing to read-only location",
    ]
)

DISK_SPACE_ERROR = ExcelError(
    title="Out of Disk Space",
    message="Cannot write file. No space left on device.",
    recovery=[
        "Check available space: df -h",
        "Free up space by deleting old files",
        "Try writing to different drive/partition",
        "Reduce file size by filtering data",
    ]
)

PARTIAL_WRITE_ERROR = ExcelError(
    title="File Write Incomplete",
    message="File was partially written. May be corrupted.",
    recovery=[
        "File should be automatically cleaned up",
        "Delete partial file: rm /path/to/file.xlsx",
        "Retry write operation",
        "Check disk space is sufficient",
    ]
)


def get_sheet_error(available_sheets: list) -> ExcelError:
    """Error listing available sheets."""
    return ExcelError(
        title="Sheet Not Found - Invalid Name Provided",
        message=f"Available sheets: {', '.join(available_sheets)}",
        recovery=[
            f"Use one of: {', '.join(available_sheets)}",
            "Sheet names are case-sensitive",
            "Try sheet index: 0, 1, 2, etc.",
        ]
    )


def get_size_error(file_mb: float) -> ExcelError:
    """Error for very large files."""
    return ExcelError(
        title=f"File Very Large ({file_mb:.1f}MB)",
        message="Large files may consume significant memory.",
        recovery=[
            "PyStreamXL streams rows, so memory is O(1)",
            "Processing should work despite size",
            "Monitor memory usage: top or Activity Monitor",
            "Report if processing is slower than expected",
        ]
    )
