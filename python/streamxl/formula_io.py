"""
Formula Export/Import - Serialize and deserialize formulas to/from JSON.

Enables:
- Exporting all formulas from a workbook
- Importing formulas back into Excel files
- Formula auditing and version control
- Programmatic formula modification
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class FormulaSerializer:
    """Export and import formulas from Excel files."""

    @staticmethod
    def export_formulas(
        rows_with_metadata: List[List[Dict]], sheet_name: str = "Sheet1"
    ) -> Dict[str, Any]:
        """
        Export formulas from rows with metadata.

        Args:
            rows_with_metadata: Rows from read(with_formulas=True)
            sheet_name: Name of the sheet being exported

        Returns:
            Dict with structure:
            {
                "version": "1.0",
                "sheets": {
                    "Sheet1": {
                        "(0, 0)": {"formula": "=SUM(...)", "type": "sum", "value": 100.5},
                        ...
                    }
                }
            }

        Examples:
            >>> rows = list(streamxl.read("file.xlsx", with_formulas=True))
            >>> export = FormulaSerializer.export_formulas(rows)
            >>> json.dump(export, open("formulas.json", "w"))
        """
        sheet_formulas = {}

        for row_idx, row in enumerate(rows_with_metadata):
            for col_idx, cell in enumerate(row):
                if cell.get("formula"):
                    key = f"({row_idx}, {col_idx})"
                    sheet_formulas[key] = {
                        "formula": cell["formula"],
                        "type": cell.get("formula_type") or "custom",
                        "value": cell.get("value"),
                    }

        return {
            "version": "1.0",
            "sheets": {sheet_name: sheet_formulas},
            "metadata": {"row_count": len(rows_with_metadata), "sheet_name": sheet_name},
        }

    @staticmethod
    def export_to_json(
        rows_with_metadata: List[List[Dict]], output_path: str, sheet_name: str = "Sheet1"
    ) -> None:
        """
        Export formulas to a JSON file.

        Args:
            rows_with_metadata: Rows from read(with_formulas=True)
            output_path: Path to save JSON file
            sheet_name: Name of the sheet being exported

        Examples:
            >>> rows = list(streamxl.read("file.xlsx", with_formulas=True))
            >>> FormulaSerializer.export_to_json(rows, "formulas.json")
        """
        export_data = FormulaSerializer.export_formulas(rows_with_metadata, sheet_name)
        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

    @staticmethod
    def export_to_csv(
        rows_with_metadata: List[List[Dict]], output_path: str, sheet_name: str = "Sheet1"
    ) -> None:
        """
        Export formulas to a CSV file for auditing.

        CSV format: row,col,formula,type,value

        Args:
            rows_with_metadata: Rows from read(with_formulas=True)
            output_path: Path to save CSV file
            sheet_name: Name of the sheet being exported

        Examples:
            >>> rows = list(streamxl.read("file.xlsx", with_formulas=True))
            >>> FormulaSerializer.export_to_csv(rows, "formulas.csv")
        """
        import csv

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["row", "col", "formula", "type", "value"])

            for row_idx, row in enumerate(rows_with_metadata):
                for col_idx, cell in enumerate(row):
                    if cell.get("formula"):
                        writer.writerow(
                            [
                                row_idx,
                                col_idx,
                                cell["formula"],
                                cell.get("formula_type") or "custom",
                                cell.get("value"),
                            ]
                        )

    @staticmethod
    def import_formulas(json_path: str) -> Dict[str, Dict[str, Dict]]:
        """
        Import formulas from a JSON file.

        Args:
            json_path: Path to JSON file created by export_to_json()

        Returns:
            Dict with structure matching export format

        Examples:
            >>> formulas = FormulaSerializer.import_formulas("formulas.json")
            >>> for cell_ref, data in formulas["sheets"]["Sheet1"].items():
            ...     print(f"{cell_ref}: {data['formula']}")
        """
        with open(json_path, "r") as f:
            return json.load(f)

    @staticmethod
    def get_formula_stats(
        rows_with_metadata: List[List[Dict]], sheet_name: str = "Sheet1"
    ) -> Dict[str, Any]:
        """
        Generate statistics about formulas in the worksheet.

        Args:
            rows_with_metadata: Rows from read(with_formulas=True)
            sheet_name: Name of the sheet

        Returns:
            Dict with statistics:
            {
                "total_cells": 100,
                "formula_cells": 25,
                "formula_percentage": 25.0,
                "by_type": {"sum": 10, "average": 5, "if": 3, "custom": 7},
                "error_formulas": 2,
                "average_formula_length": 45.3,
            }

        Examples:
            >>> rows = list(streamxl.read("file.xlsx", with_formulas=True))
            >>> stats = FormulaSerializer.get_formula_stats(rows)
            >>> print(f"Formulas: {stats['formula_cells']}/{stats['total_cells']}")
        """
        total_cells = 0
        formula_cells = 0
        formula_types = {}
        formula_lengths = []
        error_formulas = 0

        for row in rows_with_metadata:
            for cell in row:
                if cell is not None:
                    total_cells += 1
                    if cell.get("formula"):
                        formula_cells += 1
                        ftype = cell.get("formula_type") or "custom"
                        formula_types[ftype] = formula_types.get(ftype, 0) + 1
                        formula_lengths.append(len(cell["formula"]))

                        if cell.get("value") is None and "(" in cell["formula"]:
                            error_formulas += 1

        avg_length = (
            sum(formula_lengths) / len(formula_lengths) if formula_lengths else 0
        )

        return {
            "total_cells": total_cells,
            "formula_cells": formula_cells,
            "formula_percentage": (formula_cells / total_cells * 100) if total_cells > 0 else 0,
            "by_type": formula_types,
            "error_formulas": error_formulas,
            "average_formula_length": round(avg_length, 1),
            "sheet_name": sheet_name,
        }

    @staticmethod
    def validate_export_format(export_data: Dict[str, Any]) -> bool:
        """
        Validate that export data has correct structure.

        Args:
            export_data: Data from export_formulas()

        Returns:
            True if valid format
        """
        required_keys = {"version", "sheets", "metadata"}
        if not all(k in export_data for k in required_keys):
            return False

        if not isinstance(export_data["sheets"], dict):
            return False

        for sheet_name, formulas in export_data["sheets"].items():
            if not isinstance(formulas, dict):
                return False
            for cell_ref, formula_data in formulas.items():
                required_formula_keys = {"formula", "type", "value"}
                if not all(k in formula_data for k in required_formula_keys):
                    return False

        return True
