use std::fmt;

/// Classification of parsing/reading errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorSeverity {
    /// Fatal error - must stop reading
    Fatal,
    /// Recoverable error - can skip cell/row and continue
    Recoverable,
    /// Warning - continue but flag for user attention
    Warning,
}

/// Classification of error types
#[derive(Debug, Clone)]
pub enum ErrorKind {
    /// ZIP file is corrupted or invalid
    ZipCorrupted { reason: &'static str },
    /// Missing required file in ZIP (workbook.xml, etc)
    MissingRequiredFile { file: String },
    /// XML parsing error
    XmlParseError { location: String, reason: String },
    /// Invalid cell format
    InvalidCellFormat { cell_ref: String, reason: String },
    /// Formula syntax error
    FormulaError { cell_ref: String, formula: String, reason: String },
    /// Circular reference detected
    CircularReference { cell_ref: String, references: Vec<String> },
    /// Invalid style/format reference
    InvalidStyleReference { style_id: usize },
    /// Invalid shared string reference
    InvalidStringReference { index: usize },
    /// Cell comment parsing error
    CommentError { cell_ref: String, reason: String },
    /// Generic parsing error
    ParseError { context: String, reason: String },
}

impl ErrorKind {
    pub fn severity(&self) -> ErrorSeverity {
        match self {
            // Fatal errors
            ErrorKind::ZipCorrupted { .. } => ErrorSeverity::Fatal,
            ErrorKind::MissingRequiredFile { .. } => ErrorSeverity::Fatal,
            ErrorKind::XmlParseError { .. } => ErrorSeverity::Fatal,

            // Recoverable errors
            ErrorKind::InvalidCellFormat { .. } => ErrorSeverity::Recoverable,
            ErrorKind::FormulaError { .. } => ErrorSeverity::Recoverable,
            ErrorKind::InvalidStyleReference { .. } => ErrorSeverity::Recoverable,
            ErrorKind::InvalidStringReference { .. } => ErrorSeverity::Recoverable,
            ErrorKind::CommentError { .. } => ErrorSeverity::Recoverable,

            // Warnings
            ErrorKind::CircularReference { .. } => ErrorSeverity::Warning,
            ErrorKind::ParseError { .. } => ErrorSeverity::Warning,
        }
    }

    pub fn category(&self) -> &'static str {
        match self {
            ErrorKind::ZipCorrupted { .. } => "zip_corruption",
            ErrorKind::MissingRequiredFile { .. } => "missing_file",
            ErrorKind::XmlParseError { .. } => "xml_parsing",
            ErrorKind::InvalidCellFormat { .. } => "cell_format",
            ErrorKind::FormulaError { .. } => "formula_syntax",
            ErrorKind::CircularReference { .. } => "circular_reference",
            ErrorKind::InvalidStyleReference { .. } => "invalid_style",
            ErrorKind::InvalidStringReference { .. } => "invalid_string",
            ErrorKind::CommentError { .. } => "comment_error",
            ErrorKind::ParseError { .. } => "parse_error",
        }
    }
}

impl fmt::Display for ErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ErrorKind::ZipCorrupted { reason } => write!(f, "ZIP corruption: {}", reason),
            ErrorKind::MissingRequiredFile { file } => write!(f, "Missing required file: {}", file),
            ErrorKind::XmlParseError { location, reason } => {
                write!(f, "XML parse error at {}: {}", location, reason)
            }
            ErrorKind::InvalidCellFormat { cell_ref, reason } => {
                write!(f, "Invalid cell format at {}: {}", cell_ref, reason)
            }
            ErrorKind::FormulaError {
                cell_ref,
                formula,
                reason,
            } => {
                write!(
                    f,
                    "Formula error in {}: {} ({})",
                    cell_ref, formula, reason
                )
            }
            ErrorKind::CircularReference {
                cell_ref,
                references,
            } => {
                write!(
                    f,
                    "Circular reference in {}: references {}",
                    cell_ref,
                    references.join(", ")
                )
            }
            ErrorKind::InvalidStyleReference { style_id } => {
                write!(f, "Invalid style reference: ID {}", style_id)
            }
            ErrorKind::InvalidStringReference { index } => {
                write!(f, "Invalid string reference: index {}", index)
            }
            ErrorKind::CommentError { cell_ref, reason } => {
                write!(f, "Comment error in {}: {}", cell_ref, reason)
            }
            ErrorKind::ParseError { context, reason } => {
                write!(f, "Parse error in {}: {}", context, reason)
            }
        }
    }
}

/// Detailed error context for diagnostics
#[derive(Debug, Clone)]
pub struct ErrorContext {
    pub kind: ErrorKind,
    pub file_path: Option<String>,
    pub sheet_name: Option<String>,
    pub row_number: Option<usize>,
    pub column_number: Option<usize>,
    pub suggestion: Option<String>,
}

impl ErrorContext {
    pub fn new(kind: ErrorKind) -> Self {
        Self {
            kind,
            file_path: None,
            sheet_name: None,
            row_number: None,
            column_number: None,
            suggestion: None,
        }
    }

    pub fn with_file(mut self, path: String) -> Self {
        self.file_path = Some(path);
        self
    }

    pub fn with_sheet(mut self, name: String) -> Self {
        self.sheet_name = Some(name);
        self
    }

    pub fn with_location(mut self, row: usize, col: usize) -> Self {
        self.row_number = Some(row);
        self.column_number = Some(col);
        self
    }

    pub fn with_suggestion(mut self, suggestion: String) -> Self {
        self.suggestion = Some(suggestion);
        self
    }

    pub fn severity(&self) -> ErrorSeverity {
        self.kind.severity()
    }

    pub fn category(&self) -> &'static str {
        self.kind.category()
    }

    pub fn format_detailed(&self) -> String {
        let mut output = String::new();

        // Title
        output.push_str(&format!("❌ {}\n", self.kind.category()));
        output.push_str(&format!("   {}\n\n", self.kind));

        // Location info
        if self.file_path.is_some() || self.sheet_name.is_some() || self.row_number.is_some() {
            output.push_str("📍 Location:\n");
            if let Some(file) = &self.file_path {
                output.push_str(&format!("   File: {}\n", file));
            }
            if let Some(sheet) = &self.sheet_name {
                output.push_str(&format!("   Sheet: {}\n", sheet));
            }
            if let Some(row) = self.row_number {
                output.push_str(&format!("   Row: {}\n", row + 1)); // Convert to 1-indexed
            }
            if let Some(col) = self.column_number {
                output.push_str(&format!("   Column: {}\n", col + 1)); // Convert to 1-indexed
            }
            output.push('\n');
        }

        // Severity
        output.push_str(&format!(
            "⚠️  Severity: {}\n\n",
            match self.severity() {
                ErrorSeverity::Fatal => "Fatal",
                ErrorSeverity::Recoverable => "Recoverable",
                ErrorSeverity::Warning => "Warning",
            }
        ));

        // Suggestion
        if let Some(suggestion) = &self.suggestion {
            output.push_str("💡 Suggestion:\n");
            output.push_str(&format!("   {}\n", suggestion));
        }

        output
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_severity() {
        let fatal = ErrorKind::ZipCorrupted {
            reason: "Invalid central directory",
        };
        assert_eq!(fatal.severity(), ErrorSeverity::Fatal);

        let recoverable = ErrorKind::InvalidCellFormat {
            cell_ref: "A1".to_string(),
            reason: "Invalid format".to_string(),
        };
        assert_eq!(recoverable.severity(), ErrorSeverity::Recoverable);

        let warning = ErrorKind::CircularReference {
            cell_ref: "A1".to_string(),
            references: vec!["B1".to_string()],
        };
        assert_eq!(warning.severity(), ErrorSeverity::Warning);
    }

    #[test]
    fn test_error_context_formatting() {
        let error = ErrorContext::new(ErrorKind::FormulaError {
            cell_ref: "C5".to_string(),
            formula: "=SUM(A1:A10".to_string(),
            reason: "Missing closing parenthesis".to_string(),
        })
        .with_file("report.xlsx".to_string())
        .with_sheet("Data".to_string())
        .with_location(4, 2)
        .with_suggestion("Add closing parenthesis: =SUM(A1:A10)".to_string());

        let formatted = error.format_detailed();
        assert!(formatted.contains("formula_syntax"));
        assert!(formatted.contains("report.xlsx"));
        assert!(formatted.contains("Data"));
        assert!(formatted.contains("Row: 5"));
        assert!(formatted.contains("Column: 3"));
    }
}
