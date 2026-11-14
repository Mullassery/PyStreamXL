#!/usr/bin/env python3
"""CodeAtlas adapter -- embedded architecture/knowledge-graph backend.

`CodeAtlas <https://github.com/Mullassery/CodeAtlas>`_ is a Rust-native engine
that turns a codebase into a deterministic architecture map: components, the
relations between them, and the symbols each one owns. Coding agents
(OpenCode, Claude Code, Codex, ...) can then answer structural questions from
the map instead of scanning every file, which keeps agent context small.

This adapter is the *only* integration point. It embeds the ``codeatlas_rs``
engine **in process** -- no external CLI, no network, no API key -- and exposes
a small, stable JSON-on-stdout interface so other tooling can consume results
without depending on CodeAtlas internals or version-specific flags.

Usage:
    python tools/codeatlas/codeatlas_adapter.py check
    python tools/codeatlas/codeatlas_adapter.py build --root . --out codeatlas-out
    python tools/codeatlas/codeatlas_adapter.py query "where is config parsed?"
    python tools/codeatlas/codeatlas_adapter.py god-nodes
    python tools/codeatlas/codeatlas_adapter.py explain "core"
    python tools/codeatlas/codeatlas_adapter.py affected "core"
    python tools/codeatlas/codeatlas_adapter.py path "cli" "store"
    python tools/codeatlas/codeatlas_adapter.py diagnose

Install the engine (optional, per developer):
    pip install codeatlas-rs        # or: pip install ".[architecture]"

Exit codes:
    0  success, or engine unavailable and --require was not passed
    1  the engine failed, or is unavailable and --require was passed
    2  bad usage
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

BACKEND = "codeatlas"

INSTALL_HINT = (
    "the 'codeatlas_rs' engine is not installed. CodeAtlas is an optional "
    "analysis backend; install it with `pip install codeatlas-rs` (or "
    '`pip install ".[architecture]"`).'
)


def _load_engine():
    """Import the embedded engine lazily so the adapter stays import-safe."""
    try:  # pragma: no cover - exercised via subprocess in tests
        import codeatlas_rs  # type: ignore

        return codeatlas_rs
    except Exception:  # noqa: BLE001 - availability probe must never be fatal
        return None


def _emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


def _unavailable(args: argparse.Namespace) -> int:
    print(INSTALL_HINT, file=sys.stderr)
    return _emit(
        {"backend": BACKEND, "available": False, "message": INSTALL_HINT},
        1 if getattr(args, "require", False) else 0,
    )


# --------------------------------------------------------------------------- #
# Graph helpers
# --------------------------------------------------------------------------- #
def _iter_components(components: list[dict]) -> Any:
    for component in components:
        yield component
        yield from _iter_components(component.get("components") or [])


def _build_graph(data: dict) -> dict:
    """Flatten the nested component tree into id/name indexed nodes + edges."""
    nodes: dict[str, dict] = {}
    for component in _iter_components(data.get("components") or []):
        cid = component.get("component_id") or component.get("name", "")
        nodes[cid] = {
            "id": cid,
            "name": component.get("name", cid),
            "description": component.get("description", ""),
            "symbols": _component_symbols(component),
            "parent": component.get("_parent"),
        }
    edges: list[dict] = []

    def collect(components: list[dict]) -> None:
        for component in components:
            for relation in component.get("components_relations") or []:
                edges.append(_edge(relation))
            collect(component.get("components") or [])

    for relation in data.get("components_relations") or []:
        edges.append(_edge(relation))
    collect(data.get("components") or [])

    return {"nodes": nodes, "edges": edges}


def _edge(relation: dict) -> dict:
    return {
        "src_id": relation.get("src_id", ""),
        "src_name": relation.get("src_name", ""),
        "dst_id": relation.get("dst_id", ""),
        "dst_name": relation.get("dst_name", ""),
        "relation": relation.get("relation", ""),
    }


def _component_symbols(component: dict, limit: int = 40) -> list[str]:
    symbols: list[str] = []
    for entry in component.get("file_methods") or []:
        symbols.extend(entry.get("methods") or [])
    return symbols[:limit]


def _resolve(graph: dict, name: str) -> dict | None:
    """Resolve a node by id or (case-insensitive) name."""
    nodes = graph["nodes"]
    if name in nodes:
        return nodes[name]
    lowered = name.lower()
    for node in nodes.values():
        if node["name"].lower() == lowered:
            return node
    for node in nodes.values():
        if lowered in node["name"].lower():
            return node
    return None


def _degree(graph: dict) -> dict[str, int]:
    counts: dict[str, int] = {nid: 0 for nid in graph["nodes"]}
    for edge in graph["edges"]:
        counts[edge["src_id"]] = counts.get(edge["src_id"], 0) + 1
        counts[edge["dst_id"]] = counts.get(edge["dst_id"], 0) + 1
    return counts


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_check(args: argparse.Namespace) -> int:
    engine = _load_engine()
    if engine is None:
        return _unavailable(args)
    return _emit(
        {
            "backend": BACKEND,
            "available": True,
            "version": getattr(engine, "__version__", None),
        },
        0,
    )


def _run_analysis(args: argparse.Namespace) -> tuple[dict, Path]:
    engine = _load_engine()
    root = Path(args.root).resolve()
    out = Path(args.out)
    out = out if out.is_absolute() else (root / out)
    analysis_json, _fingerprint, _coverage = engine.analyze(
        str(root),
        project_name=None,
        depth_cap=args.depth,
        ignore_paths=[str(out)],
    )
    out.mkdir(parents=True, exist_ok=True)
    analysis_path = out / "analysis.json"
    analysis_path.write_text(analysis_json, encoding="utf-8")
    return json.loads(analysis_json), analysis_path


def cmd_build(args: argparse.Namespace) -> int:
    if _load_engine() is None:
        return _unavailable(args)
    try:
        data, analysis_path = _run_analysis(args)
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        return _emit({"backend": BACKEND, "available": True, "error": str(exc)}, 1)

    written = [str(analysis_path)]
    try:
        from codeatlas_rs.render import render

        out_dir = analysis_path.parent
        written += [str(p) for p in render("md", analysis_path, out_dir)]
        written += [str(p) for p in render("html", analysis_path, out_dir)]
    except Exception as exc:  # noqa: BLE001 - analysis is the primary artifact
        return _emit(
            {
                "backend": BACKEND,
                "available": True,
                "output": str(analysis_path.parent),
                "written": written,
                "render_error": str(exc),
                "components": len(data.get("components") or []),
                "symbols": len(data.get("methods_index") or {}),
            },
            1,
        )

    return _emit(
        {
            "backend": BACKEND,
            "available": True,
            "output": str(analysis_path.parent),
            "written": sorted(written),
            "components": len(data.get("components") or []),
            "symbols": len(data.get("methods_index") or {}),
        },
        0,
    )


def cmd_god_nodes(args: argparse.Namespace) -> int:
    if _load_engine() is None:
        return _unavailable(args)
    data, _ = _run_analysis(args)
    graph = _build_graph(data)
    counts = _degree(graph)
    ranked = sorted(
        graph["nodes"].values(), key=lambda n: counts.get(n["id"], 0), reverse=True
    )
    return _emit(
        {
            "backend": BACKEND,
            "available": True,
            "nodes": [
                {"name": n["name"], "id": n["id"], "degree": counts.get(n["id"], 0)}
                for n in ranked
                if counts.get(n["id"], 0) > 0
            ][: args.limit],
        },
        0,
    )


def cmd_explain(args: argparse.Namespace) -> int:
    if _load_engine() is None:
        return _unavailable(args)
    data, _ = _run_analysis(args)
    graph = _build_graph(data)
    node = _resolve(graph, args.node)
    if node is None:
        return _emit(
            {"backend": BACKEND, "available": True, "error": "node not found"}, 1
        )
    out_edges = [e for e in graph["edges"] if e["src_id"] == node["id"]]
    in_edges = [e for e in graph["edges"] if e["dst_id"] == node["id"]]
    return _emit(
        {
            "backend": BACKEND,
            "available": True,
            "node": {
                "name": node["name"],
                "id": node["id"],
                "description": node["description"],
                "symbols": node["symbols"],
                "depends_on": sorted({e["dst_name"] for e in out_edges}),
                "depended_on_by": sorted({e["src_name"] for e in in_edges}),
            },
        },
        0,
    )


def cmd_affected(args: argparse.Namespace) -> int:
    if _load_engine() is None:
        return _unavailable(args)
    data, _ = _run_analysis(args)
    graph = _build_graph(data)
    node = _resolve(graph, args.node)
    if node is None:
        return _emit(
            {"backend": BACKEND, "available": True, "error": "node not found"}, 1
        )
    # Transitive dependents: components that (transitively) call into `node`.
    reverse: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        reverse.setdefault(edge["dst_id"], set()).add(edge["src_id"])
    seen: set[str] = set()
    queue = deque(reverse.get(node["id"], set()))
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(reverse.get(current, set()))
    affected = sorted(graph["nodes"][n]["name"] for n in seen if n in graph["nodes"])
    return _emit(
        {
            "backend": BACKEND,
            "available": True,
            "node": node["name"],
            "affected": affected,
        },
        0,
    )


def cmd_path(args: argparse.Namespace) -> int:
    if _load_engine() is None:
        return _unavailable(args)
    data, _ = _run_analysis(args)
    graph = _build_graph(data)
    start = _resolve(graph, args.start)
    end = _resolve(graph, args.end)
    if start is None or end is None:
        return _emit(
            {"backend": BACKEND, "available": True, "error": "node not found"}, 1
        )
    adjacency: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["src_id"], set()).add(edge["dst_id"])
        adjacency.setdefault(edge["dst_id"], set()).add(edge["src_id"])
    previous: dict[str, str | None] = {start["id"]: None}
    queue = deque([start["id"]])
    while queue:
        current = queue.popleft()
        if current == end["id"]:
            break
        for neighbour in adjacency.get(current, set()):
            if neighbour not in previous:
                previous[neighbour] = current
                queue.append(neighbour)
    if end["id"] not in previous:
        return _emit(
            {"backend": BACKEND, "available": True, "path": [], "connected": False}, 0
        )
    chain: list[str] = []
    cursor: str | None = end["id"]
    while cursor is not None:
        chain.append(graph["nodes"].get(cursor, {}).get("name", cursor))
        cursor = previous[cursor]
    chain.reverse()
    return _emit(
        {"backend": BACKEND, "available": True, "path": chain, "connected": True}, 0
    )


def cmd_query(args: argparse.Namespace) -> int:
    if _load_engine() is None:
        return _unavailable(args)
    data, _ = _run_analysis(args)
    needle = args.text.lower()
    matches: list[dict] = []
    for component in _iter_components(data.get("components") or []):
        cid = component.get("component_id") or component.get("name", "")
        name = component.get("name", cid)
        symbols = _component_symbols(component, limit=1000)
        hit_symbols = [s for s in symbols if needle in s.lower()]
        if needle in name.lower() or hit_symbols:
            matches.append(
                {
                    "component": name,
                    "id": cid,
                    "description": component.get("description", ""),
                    "matching_symbols": hit_symbols[: args.limit],
                }
            )
    return _emit(
        {
            "backend": BACKEND,
            "available": True,
            "query": args.text,
            "matches": matches[: args.limit],
        },
        0,
    )


def cmd_diagnose(args: argparse.Namespace) -> int:
    if _load_engine() is None:
        return _unavailable(args)
    data, _ = _run_analysis(args)
    graph = _build_graph(data)
    symbol_files = {
        entry.get("file_path")
        for entry in (data.get("methods_index") or {}).values()
    }
    return _emit(
        {
            "backend": BACKEND,
            "available": True,
            "components": len(graph["nodes"]),
            "relations": len(graph["edges"]),
            "symbols": len(data.get("methods_index") or {}),
            "files": len(data.get("files") or []),
            "files_with_symbols": len(symbol_files),
            "depth_cap": data.get("metadata", {}).get("depth_cap"),
            "repo_name": data.get("metadata", {}).get("repo_name"),
        },
        0,
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeatlas_adapter",
        description="Embedded architecture/knowledge-graph backend (CodeAtlas).",
    )
    sub = parser.add_subparsers(dest="command")

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--root", default=".", help="Project root (default: .).")
        p.add_argument("--out", default="codeatlas-out", help="Output directory.")
        p.add_argument("--depth", type=int, default=3, help="Component depth cap.")
        p.add_argument("--limit", type=int, default=20, help="Max results returned.")
        p.add_argument(
            "--require",
            action="store_true",
            help="Exit non-zero if the CodeAtlas engine is unavailable.",
        )

    p = sub.add_parser("check", help="Report whether the engine is available.")
    common(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("build", help="Analyze and write the architecture map.")
    common(p)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("god-nodes", help="List the most connected components.")
    common(p)
    p.set_defaults(func=cmd_god_nodes)

    p = sub.add_parser("explain", help="Explain a single component.")
    common(p)
    p.add_argument("node")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("affected", help="Components impacted by a component.")
    common(p)
    p.add_argument("node")
    p.set_defaults(func=cmd_affected)

    p = sub.add_parser("path", help="Shortest path between two components.")
    common(p)
    p.add_argument("start")
    p.add_argument("end")
    p.set_defaults(func=cmd_path)

    p = sub.add_parser("query", help="Search components and symbols.")
    common(p)
    p.add_argument("text")
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("diagnose", help="Summary of the architecture map.")
    common(p)
    p.set_defaults(func=cmd_diagnose)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
