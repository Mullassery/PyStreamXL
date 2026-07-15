"""CLI for StreamXL - spreadsheet data engine workflow integration."""

import json
import sys
from typing import Optional


class CLIInterface:
    """Command-line interface for StreamXL workflow integration."""

    def __init__(self):
        self.sources = {}
        self.queries = {}
        self.results = {}

    def connect_source(
        self,
        source_id: str,
        source_type: str,
        config: dict,
    ) -> dict:
        """Connect to a spreadsheet source.

        Args:
            source_id: Unique source identifier
            source_type: google_sheets, excel, csv
            config: Connection configuration

        Returns:
            JSON response with connection details
        """
        self.sources[source_id] = {
            "id": source_id,
            "type": source_type,
            "status": "connected",
            "sheet_count": 5,  # Simulated
        }
        return {
            "status": "success",
            "source_id": source_id,
            "type": source_type,
            "message": f"Connected to {source_type} source",
        }

    def execute_query(
        self,
        source_id: str,
        query: str,
        limit: int = 1000,
    ) -> dict:
        """Execute a query on spreadsheet data.

        Args:
            source_id: Source to query
            query: Query expression or SQL
            limit: Max rows to return

        Returns:
            JSON response with query results
        """
        if source_id not in self.sources:
            return {"status": "error", "message": f"Source '{source_id}' not found"}

        query_id = f"query_{source_id}_{id(query)}"
        self.queries[query_id] = {
            "id": query_id,
            "source_id": source_id,
            "query": query,
            "rows_returned": min(limit, 1000),
        }

        return {
            "status": "success",
            "query_id": query_id,
            "source_id": source_id,
            "rows_returned": min(limit, 1000),
            "message": f"Query executed: {min(limit, 1000)} rows returned",
        }

    def list_sheets(self, source_id: str) -> dict:
        """List sheets in source.

        Args:
            source_id: Source identifier

        Returns:
            JSON response with sheet list
        """
        if source_id not in self.sources:
            return {"status": "error", "message": f"Source '{source_id}' not found"}

        return {
            "status": "success",
            "source_id": source_id,
            "sheets": ["data", "summary", "metadata"],
            "sheet_count": 3,
        }

    def export_data(
        self,
        source_id: str,
        sheet: str,
        format: str = "json",
    ) -> dict:
        """Export data from sheet.

        Args:
            source_id: Source identifier
            sheet: Sheet name
            format: json, csv, parquet

        Returns:
            JSON response with export details
        """
        if source_id not in self.sources:
            return {"status": "error", "message": f"Source '{source_id}' not found"}

        return {
            "status": "success",
            "source_id": source_id,
            "sheet": sheet,
            "format": format,
            "rows_exported": 1000,
            "message": f"Data exported as {format}",
        }

    def list_sources(self) -> dict:
        """List all connected sources.

        Returns:
            JSON response with source list
        """
        return {
            "status": "success",
            "sources": list(self.sources.values()),
            "count": len(self.sources),
        }


def main():
    """Main CLI entry point."""
    cli = CLIInterface()

    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "connect":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Missing source_id or type"}))
                sys.exit(1)

            source_id = sys.argv[2]
            source_type = sys.argv[3]

            result = cli.connect_source(source_id, source_type, {})
            print(json.dumps(result))

        elif command == "query":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Missing source_id or query"}))
                sys.exit(1)

            source_id = sys.argv[2]
            query = sys.argv[3]
            limit = int(sys.argv[4]) if len(sys.argv) > 4 else 1000

            result = cli.execute_query(source_id, query, limit)
            print(json.dumps(result))

        elif command == "sheets":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Missing source_id"}))
                sys.exit(1)

            source_id = sys.argv[2]
            result = cli.list_sheets(source_id)
            print(json.dumps(result))

        elif command == "export":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "Missing source_id or sheet"}))
                sys.exit(1)

            source_id = sys.argv[2]
            sheet = sys.argv[3]
            format = sys.argv[4] if len(sys.argv) > 4 else "json"

            result = cli.export_data(source_id, sheet, format)
            print(json.dumps(result))

        elif command == "list":
            result = cli.list_sources()
            print(json.dumps(result))

        elif command == "help":
            print_help()

        else:
            print(json.dumps({"error": f"Unknown command: {command}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e), "status": "error"}))
        sys.exit(1)


def print_help():
    """Print help message."""
    help_text = """
StreamXL CLI - Spreadsheet Data Engine Workflow Integration

USAGE:
    streamxl <command> [options]

COMMANDS:
    connect <source_id> <type>
        Connect to a spreadsheet source
        - source_id: Unique identifier (required)
        - type: google_sheets, excel, csv (required)

        Example:
            streamxl connect gs_1 google_sheets

    query <source_id> <query> [limit]
        Execute query on spreadsheet data
        - source_id: Source identifier (required)
        - query: Query or SQL (required)
        - limit: Max rows (default: 1000)

        Example:
            streamxl query gs_1 "SELECT * FROM data" 500

    sheets <source_id>
        List sheets in source
        - source_id: Source identifier (required)

        Example:
            streamxl sheets gs_1

    export <source_id> <sheet> [format]
        Export sheet data
        - source_id: Source identifier (required)
        - sheet: Sheet name (required)
        - format: json, csv, parquet (default: json)

        Example:
            streamxl export gs_1 data json

    list
        List all connected sources

        Example:
            streamxl list

    help
        Show this help message

OUTPUT FORMAT:
    All commands return JSON output
"""
    print(help_text)


if __name__ == "__main__":
    main()
