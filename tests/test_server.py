"""
Tests for streamxl.server — the REST API layer.

These exercise the *real* StreamXL streaming engine end-to-end: a real
.xlsx file is written to disk, connected as a "source", then queried and
exported through StreamXLServer / the Flask app. The previous
implementation of this module returned hardcoded/fake data (e.g. always
"sheet_count": 5, always "rows_returned": min(limit, 1000)) regardless of
the actual source file — these tests assert on values that can only be
correct if real data is being read.
"""
import json

import pytest

import streamxl
from streamxl.server import StreamXLServer, create_flask_app


@pytest.fixture
def two_sheet_xlsx(tmp_path):
    """A real .xlsx file with two sheets of known, distinct content."""
    path = str(tmp_path / "server_source.xlsx")
    with streamxl.writer(path) as w:
        w.write_row(["Name", "Age", "Score"])
        w.write_row(["Alice", 30, 95.5])
        w.write_row(["Bob", 25, 88.0])
        w.write_row(["Carol", 40, 72.25])
        w.add_sheet("Summary")
        w.write_row(["Metric", "Value"])
        w.write_row(["Count", 3])
    return path


class TestStreamXLServerReal:
    """Direct tests of StreamXLServer methods (no Flask/HTTP needed)."""

    def test_connect_source_reads_real_sheets(self, two_sheet_xlsx):
        server = StreamXLServer()
        result = server.connect_source("src1", {"path": two_sheet_xlsx})

        assert result["status"] == "success"
        # Real file has exactly 2 sheets: Sheet1 + Summary.
        assert result["sheet_count"] == 2
        assert server.sources["src1"]["sheets"] == streamxl.sheets(two_sheet_xlsx)

    def test_connect_source_missing_path_is_error(self):
        server = StreamXLServer()
        result = server.connect_source("src1", {})
        assert result["status"] == "error"
        assert "src1" not in server.sources

    def test_connect_source_nonexistent_file_is_error(self, tmp_path):
        server = StreamXLServer()
        result = server.connect_source("src1", {"path": str(tmp_path / "does_not_exist.xlsx")})
        assert result["status"] == "error"
        assert "src1" not in server.sources

    def test_list_sheets_matches_real_file(self, two_sheet_xlsx):
        server = StreamXLServer()
        server.connect_source("src1", {"path": two_sheet_xlsx})
        result = server.list_sheets("src1")

        assert result["status"] == "success"
        assert result["sheet_count"] == 2
        assert set(result["sheets"]) == set(streamxl.sheets(two_sheet_xlsx))

    def test_execute_query_returns_real_rows(self, two_sheet_xlsx):
        server = StreamXLServer()
        server.connect_source("src1", {"path": two_sheet_xlsx})
        sheet_name = streamxl.sheets(two_sheet_xlsx)[0]

        result = server.execute_query("src1", sheet_name, limit=1000)

        assert result["status"] == "success"
        # 4 rows: header + Alice + Bob + Carol. This can only be correct
        # if the server actually streamed the real file.
        assert result["rows_returned"] == 4
        assert result["rows"][0] == ["Name", "Age", "Score"]
        assert result["rows"][1][0] == "Alice"
        assert result["rows"][3][0] == "Carol"

    def test_execute_query_respects_limit_on_real_data(self, two_sheet_xlsx):
        server = StreamXLServer()
        server.connect_source("src1", {"path": two_sheet_xlsx})
        sheet_name = streamxl.sheets(two_sheet_xlsx)[0]

        result = server.execute_query("src1", sheet_name, limit=2)

        assert result["status"] == "success"
        assert result["rows_returned"] == 2
        assert result["rows"] == [["Name", "Age", "Score"], ["Alice", 30.0, 95.5]]

    def test_execute_query_unknown_sheet_falls_back_to_first_real_sheet(self, two_sheet_xlsx):
        server = StreamXLServer()
        server.connect_source("src1", {"path": two_sheet_xlsx})

        result = server.execute_query("src1", "nonexistent-sheet-name", limit=100)

        assert result["status"] == "success"
        assert result["sheet"] == streamxl.sheets(two_sheet_xlsx)[0]
        assert result["rows_returned"] == 4

    def test_execute_query_unknown_source_is_error(self):
        server = StreamXLServer()
        result = server.execute_query("nope", "Sheet1")
        assert result["status"] == "error"

    def test_export_data_json_matches_real_content(self, two_sheet_xlsx):
        server = StreamXLServer()
        server.connect_source("src1", {"path": two_sheet_xlsx})
        sheet_name = streamxl.sheets(two_sheet_xlsx)[0]

        result = server.export_data("src1", sheet_name, format="json")

        assert result["status"] == "success"
        assert result["rows_exported"] == 4
        assert result["data"][1][0] == "Alice"

    def test_export_data_csv_matches_real_content_and_is_sanitized(self, tmp_path):
        # Build a source containing a formula-injection-style value.
        path = str(tmp_path / "malicious.xlsx")
        streamxl.write(path, [
            ["Name", "Note"],
            ["Alice", "=cmd|'/c calc'!A0"],
        ])
        server = StreamXLServer()
        server.connect_source("src1", {"path": path})
        sheet_name = streamxl.sheets(path)[0]

        result = server.export_data("src1", sheet_name, format="csv")

        assert result["status"] == "success"
        assert result["rows_exported"] == 2
        # The dangerous cell must be neutralized in the CSV text.
        assert "'=cmd|'/c calc'!A0" in result["data"]
        assert ',"=cmd|' not in result["data"]

    def test_export_data_unknown_sheet_is_error(self, two_sheet_xlsx):
        server = StreamXLServer()
        server.connect_source("src1", {"path": two_sheet_xlsx})
        result = server.export_data("src1", "NoSuchSheet", format="json")
        assert result["status"] == "error"

    def test_list_sources_does_not_leak_filesystem_paths(self, two_sheet_xlsx):
        server = StreamXLServer()
        server.connect_source("src1", {"path": two_sheet_xlsx})
        result = server.list_sources()

        assert result["count"] == 1
        assert "path" not in result["sources"][0]

    def test_health_check_reports_real_counts_and_version(self, two_sheet_xlsx):
        server = StreamXLServer()
        assert server.health_check()["sources_connected"] == 0
        assert server.health_check()["queries_executed"] == 0
        assert server.health_check()["version"] == streamxl.__version__

        server.connect_source("src1", {"path": two_sheet_xlsx})
        sheet_name = streamxl.sheets(two_sheet_xlsx)[0]
        server.execute_query("src1", sheet_name)

        health = server.health_check()
        assert health["sources_connected"] == 1
        assert health["queries_executed"] == 1


class TestFlaskAppReal:
    """End-to-end tests through the actual Flask HTTP layer."""

    @pytest.fixture(autouse=True)
    def _require_flask(self):
        pytest.importorskip("flask")

    @pytest.fixture
    def client(self):
        app = create_flask_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "healthy"
        assert body["version"] == streamxl.__version__

    def test_full_workflow_connect_query_export(self, client, two_sheet_xlsx):
        # Connect a real source.
        resp = client.post(
            "/sources",
            data=json.dumps({"source_id": "s1", "config": {"path": two_sheet_xlsx}}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["sheet_count"] == 2

        # List sheets — must reflect the real file.
        resp = client.get("/sources/s1/sheets")
        assert resp.status_code == 200
        sheets_body = resp.get_json()
        assert sheets_body["sheet_count"] == 2

        first_sheet = sheets_body["sheets"][0]

        # Query real rows.
        resp = client.post(
            f"/sources/s1/query",
            data=json.dumps({"query": first_sheet, "limit": 100}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        query_body = resp.get_json()
        assert query_body["rows_returned"] == 4
        assert query_body["rows"][1][0] == "Alice"

        # Export real rows as CSV.
        resp = client.post(
            f"/sources/s1/export",
            data=json.dumps({"sheet": first_sheet, "format": "csv"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        export_body = resp.get_json()
        assert export_body["rows_exported"] == 4
        assert "Alice" in export_body["data"]

    def test_connect_source_missing_path_returns_400(self, client):
        resp = client.post(
            "/sources",
            data=json.dumps({"source_id": "s1", "config": {}}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["status"] == "error"

    def test_query_unknown_source_returns_400(self, client):
        resp = client.post(
            "/sources/does-not-exist/query",
            data=json.dumps({"query": "Sheet1"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
