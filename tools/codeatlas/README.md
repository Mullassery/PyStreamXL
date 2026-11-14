# CodeAtlas integration (embedded)

[CodeAtlas](https://github.com/Mullassery/CodeAtlas) turns this codebase into a
deterministic architecture map — components, the relations between them, and the
symbols each one owns. Coding agents (OpenCode, Claude Code, Codex, ...) can then
answer structural questions from the map instead of scanning every file, which
keeps agent context small.

Unlike a CLI wrapper, the `codeatlas_rs` engine is **embedded in process**: no
external binary, no network, no API key. The adapter is the single integration
point and exposes a small, stable JSON-on-stdout interface so other tooling can
consume results without depending on CodeAtlas internals.

## Layout

| Path | Purpose |
| - | - |
| `tools/codeatlas/codeatlas_adapter.py` | The single, isolated integration point. Embeds `codeatlas_rs`; never shells out. |
| `codeatlas-out/` | Generated analysis + rendered docs. Git-ignored; never committed. |

## Install (per developer, opt-in)

CodeAtlas is an optional analysis extra; nothing here is required to build, test,
or run the project:

```bash
pip install ".[architecture]"   # or: pip install codeatlas-rs
```

## Use

```bash
# Build the architecture map (no API key / model needed)
python tools/codeatlas/codeatlas_adapter.py build --root . --out codeatlas-out

# Query it
python tools/codeatlas/codeatlas_adapter.py query "where is config parsed?"
python tools/codeatlas/codeatlas_adapter.py god-nodes
python tools/codeatlas/codeatlas_adapter.py explain "core"
python tools/codeatlas/codeatlas_adapter.py affected "core"
python tools/codeatlas/codeatlas_adapter.py path "cli" "store"
python tools/codeatlas/codeatlas_adapter.py diagnose
```

Every subcommand prints a stable JSON object on stdout. If the engine is not
installed, the adapter reports `"available": false` and exits `0` unless
`--require` is passed.

## Relationship to Graphify

This adapter **replaces** the previous Graphify integration: same command
surface (`check`/`build`/`query`/`explain`/`affected`/`god-nodes`/`diagnose`),
now backed by an embedded, deterministic engine rather than an external CLI.
