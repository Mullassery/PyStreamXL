"""REST API server for StreamXL - spreadsheet data engine workflow integration.

Every endpoint below is backed by the real StreamXL streaming/ETL engine
(``streamxl.api.read`` / ``streamxl.api.sheets``): a "source" is a real
``.xlsx`` file on disk, "query" streams actual rows from it, and "export"
serializes actual sheet data (CSV output is sanitized against
formula-injection via :func:`streamxl.security.sanitize_csv_cell`).
Nothing here returns synthetic/hardcoded data.
"""

import csv
import io
from typing import Any, Dict, List, Optional

from . import __version__
from .api import read, sheets as list_sheet_names
from .security import SecurityError, sanitize_csv_cell, validate_read_path


class StreamXLServer:
    """REST API server for spreadsheet data workflows.

    Sources are registered with a real filesystem path to a ``.xlsx`` file
    (validated with the same security checks — extension, size limits,
    ZIP-bomb defenses — used by the rest of the library). Queries and
    exports stream rows from that file through the real Rust streaming
    engine.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8004):
        """Initialize server."""
        self.host = host
        self.port = port
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.queries: Dict[str, Dict[str, Any]] = {}
        self._query_seq = 0

    def connect_source(self, source_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a real ``.xlsx`` file as a source.

        ``config`` must contain ``"path"``: the filesystem path to a
        ``.xlsx`` file. The path is validated immediately (existence,
        extension, size / ZIP-bomb limits) and its real sheet list is read
        so a bad source fails fast at connect time instead of at query
        time.
        """
        path = config.get("path")
        if not path:
            return {
                "status": "error",
                "message": "config.path is required (filesystem path to a .xlsx file)",
            }

        try:
            validated_path = validate_read_path(path)
            sheet_names = list_sheet_names(str(validated_path))
        except SecurityError as e:
            return {"status": "error", "message": f"Invalid source file: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to open '{path}': {e}"}

        self.sources[source_id] = {
            "id": source_id,
            "type": config.get("type", "xlsx"),
            "path": str(validated_path),
            "status": "connected",
            "sheets": sheet_names,
            "sheet_count": len(sheet_names),
        }
        return {
            "status": "success",
            "source_id": source_id,
            "sheet_count": len(sheet_names),
            "message": "Source connected successfully",
        }

    def execute_query(
        self, source_id: str, query: str, limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Stream real rows from a sheet in the connected source.

        ``query`` is treated as a sheet name; if it doesn't name a sheet in
        the source, the first sheet is used. Up to ``limit`` rows are
        streamed from the real file — ``rows_returned`` reflects the
        actual number of rows read (which may be less than ``limit`` for
        small sheets), not a hardcoded value.
        """
        source = self.sources.get(source_id)
        if source is None:
            return {"status": "error", "message": f"Source '{source_id}' not found"}

        sheet_names = source["sheets"]
        sheet_name = query if query in sheet_names else (sheet_names[0] if sheet_names else None)

        try:
            rows: List[Any] = []
            for row in read(source["path"], sheet=sheet_name):
                if len(rows) >= limit:
                    break
                rows.append(row)
        except Exception as e:
            return {"status": "error", "message": f"Query failed: {e}"}

        self._query_seq += 1
        query_id = f"query_{source_id}_{self._query_seq}"
        self.queries[query_id] = {
            "id": query_id,
            "source_id": source_id,
            "query": query,
            "sheet": sheet_name,
            "rows_returned": len(rows),
        }

        return {
            "status": "success",
            "query_id": query_id,
            "sheet": sheet_name,
            "rows_returned": len(rows),
            "rows": rows,
            "message": "Query executed successfully",
        }

    def list_sheets(self, source_id: str) -> Dict[str, Any]:
        """List the real sheet names of a connected source."""
        source = self.sources.get(source_id)
        if source is None:
            return {"status": "error", "message": f"Source '{source_id}' not found"}

        return {
            "status": "success",
            "source_id": source_id,
            "sheets": source["sheets"],
            "sheet_count": len(source["sheets"]),
        }

    def export_data(
        self, source_id: str, sheet: str, format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export a real sheet's rows as CSV or JSON.

        CSV output has every cell passed through
        :func:`streamxl.security.sanitize_csv_cell` to prevent
        formula-injection when the export is later opened in a
        spreadsheet application.
        """
        source = self.sources.get(source_id)
        if source is None:
            return {"status": "error", "message": f"Source '{source_id}' not found"}

        if sheet not in source["sheets"]:
            return {
                "status": "error",
                "message": f"Sheet '{sheet}' not found in source '{source_id}'; available: {source['sheets']}",
            }

        if format not in ("json", "csv"):
            return {"status": "error", "message": f"Unsupported format: '{format}' (use 'json' or 'csv')"}

        try:
            rows = list(read(source["path"], sheet=sheet))
        except Exception as e:
            return {"status": "error", "message": f"Export failed: {e}"}

        if format == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            for row in rows:
                writer.writerow([sanitize_csv_cell(cell) for cell in row])
            data: Any = buf.getvalue()
        else:
            data = rows

        return {
            "status": "success",
            "source_id": source_id,
            "sheet": sheet,
            "format": format,
            "rows_exported": len(rows),
            "data": data,
            "message": f"Data exported as {format}",
        }

    def list_sources(self) -> Dict[str, Any]:
        """List all connected sources (filesystem paths are not exposed)."""
        return {
            "status": "success",
            "sources": [
                {k: v for k, v in s.items() if k != "path"}
                for s in self.sources.values()
            ],
            "count": len(self.sources),
        }

    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "streamxl",
            "version": __version__,
            "sources_connected": len(self.sources),
            "queries_executed": len(self.queries),
        }


def create_flask_app(server: Optional[StreamXLServer] = None):
    """Create Flask app for REST API."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        raise ImportError(
            "Flask is required for REST API. Install with: pip install 'streamxl[server]' or pip install flask"
        )

    app = Flask(__name__)
    srv = server or StreamXLServer()

    @app.route("/health", methods=["GET"])
    def health():
        """Health check."""
        return jsonify(srv.health_check())

    @app.route("/sources", methods=["GET"])
    def list_sources():
        """List sources."""
        return jsonify(srv.list_sources())

    @app.route("/sources", methods=["POST"])
    def connect_source():
        """Connect source."""
        data = request.get_json()
        source_id = data.get("source_id")
        config = data.get("config", {})

        if not source_id:
            return (
                jsonify({"status": "error", "message": "source_id required"}),
                400,
            )

        result = srv.connect_source(source_id, config)
        status_code = 200 if result.get("status") == "success" else 400
        return jsonify(result), status_code

    @app.route("/sources/<source_id>/query", methods=["POST"])
    def query(source_id):
        """Execute query."""
        data = request.get_json() or {}
        query_text = data.get("query")
        limit = data.get("limit", 1000)

        if not query_text:
            return (
                jsonify({"status": "error", "message": "query required"}),
                400,
            )

        result = srv.execute_query(source_id, query_text, limit)
        status_code = 200 if result.get("status") == "success" else 400
        return jsonify(result), status_code

    @app.route("/sources/<source_id>/sheets", methods=["GET"])
    def sheets(source_id):
        """List sheets."""
        result = srv.list_sheets(source_id)
        status_code = 200 if result.get("status") == "success" else 404
        return jsonify(result), status_code

    @app.route("/sources/<source_id>/export", methods=["POST"])
    def export(source_id):
        """Export data."""
        data = request.get_json() or {}
        sheet = data.get("sheet")
        format = data.get("format", "json")

        if not sheet:
            return (
                jsonify({"status": "error", "message": "sheet required"}),
                400,
            )

        result = srv.export_data(source_id, sheet, format)
        status_code = 200 if result.get("status") == "success" else 400
        return jsonify(result), status_code

    return app


def run_server(host: str = "0.0.0.0", port: int = 8004):
    """Run the REST API server."""
    app = create_flask_app()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_server()
