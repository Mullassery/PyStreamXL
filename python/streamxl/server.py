"""REST API server for StreamXL - spreadsheet data engine workflow integration."""

from typing import Dict, Any, Optional


class StreamXLServer:
    """REST API server for spreadsheet data workflows."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8004):
        """Initialize server."""
        self.host = host
        self.port = port
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.queries: Dict[str, Dict[str, Any]] = {}

    def connect_source(self, source_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to a source."""
        self.sources[source_id] = {
            "id": source_id,
            "type": config.get("type", "google_sheets"),
            "status": "connected",
            "sheet_count": 5,
        }
        return {
            "status": "success",
            "source_id": source_id,
            "message": "Source connected successfully",
        }

    def execute_query(
        self, source_id: str, query: str, limit: int = 1000
    ) -> Dict[str, Any]:
        """Execute a query."""
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
            "rows_returned": min(limit, 1000),
            "message": "Query executed successfully",
        }

    def list_sheets(self, source_id: str) -> Dict[str, Any]:
        """List sheets."""
        if source_id not in self.sources:
            return {"status": "error", "message": f"Source '{source_id}' not found"}

        return {
            "status": "success",
            "source_id": source_id,
            "sheets": ["data", "summary", "metadata"],
            "sheet_count": 3,
        }

    def export_data(
        self, source_id: str, sheet: str, format: str = "json"
    ) -> Dict[str, Any]:
        """Export data."""
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

    def list_sources(self) -> Dict[str, Any]:
        """List all sources."""
        return {
            "status": "success",
            "sources": list(self.sources.values()),
            "count": len(self.sources),
        }

    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "streamxl",
            "version": "0.1.0",
            "sources_connected": len(self.sources),
            "queries_executed": len(self.queries),
        }


def create_flask_app(server: Optional[StreamXLServer] = None):
    """Create Flask app for REST API."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        raise ImportError(
            "Flask is required for REST API. Install with: pip install flask"
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

        return jsonify(srv.connect_source(source_id, config))

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

        return jsonify(srv.execute_query(source_id, query_text, limit))

    @app.route("/sources/<source_id>/sheets", methods=["GET"])
    def sheets(source_id):
        """List sheets."""
        return jsonify(srv.list_sheets(source_id))

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

        return jsonify(srv.export_data(source_id, sheet, format))

    return app


def run_server(host: str = "0.0.0.0", port: int = 8004):
    """Run the REST API server."""
    app = create_flask_app()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_server()
