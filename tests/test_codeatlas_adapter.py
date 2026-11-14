"""Tests for the embedded CodeAtlas architecture adapter.

These require the optional `codeatlas_rs` engine (`pip install
".[architecture]"`); they are skipped when it is not installed, so the
default test suite stays dependency-free.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

pytest.importorskip("codeatlas_rs")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAPTER = os.path.join(REPO_ROOT, "tools", "codeatlas", "codeatlas_adapter.py")


def _run(*args: str) -> tuple[subprocess.CompletedProcess, dict]:
    proc = subprocess.run(
        [sys.executable, ADAPTER, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc, json.loads(proc.stdout)


def test_check_reports_the_embedded_engine_available():
    proc, payload = _run("check")
    assert proc.returncode == 0
    assert payload["available"] is True
    assert payload["backend"] == "codeatlas"


def test_diagnose_summarises_the_architecture_map():
    proc, payload = _run("diagnose", "--root", REPO_ROOT)
    assert proc.returncode == 0
    assert payload["components"] >= 1
    assert payload["symbols"] >= 1


def test_god_nodes_are_ranked_by_degree():
    proc, payload = _run("god-nodes", "--root", REPO_ROOT)
    assert proc.returncode == 0
    degrees = [node["degree"] for node in payload["nodes"]]
    assert degrees == sorted(degrees, reverse=True)


def test_explain_reports_an_unknown_node_as_an_error():
    proc, payload = _run("explain", "no-such-component", "--root", REPO_ROOT)
    assert payload.get("error") == "node not found"
