# 🎯 Dashboard Keyboard Shortcuts & Usage

## Auto-Start on Installation

The CLI dashboard **starts automatically** when you run the package for the first time or import it in Python:

```bash
$ pip install [package]
# ✓ Dashboard appears in terminal automatically

$ python3 -c "from [package] import *"
# ✓ Dashboard initializes in background
```

The dashboard runs in **persistent daemon mode** — if you close it, it restarts automatically with your keyboard shortcuts.

---

## ⌨️ Keyboard Shortcuts

After installing the package, run:

```bash
bash <(curl -s https://raw.githubusercontent.com/Mullassery/[PACKAGE]/main/scripts/setup_shortcuts.sh)
```

This adds aliases to your `~/.zshrc` or `~/.bashrc`:

### Quick Access (all packages)

```bash
dashboards                      # Show all available dashboard shortcuts
```

### Per-Package Shortcuts

Replace `[PACKAGE]` with any installed Mullassery package name:

```bash
dash-[PACKAGE]                  # Static snapshot (single view)
dash-[PACKAGE]-live             # Live dashboard (Ctrl+C to close)
dash-[PACKAGE]-export           # Export metrics to JSON
```

### Examples

```bash
# PyStreamAI
$ dash-pystreamai               # View deployment metrics snapshot
$ dash-pystreamai-live          # Watch real-time inference latency
$ dash-pystreamai-export        # Save metrics for monitoring

# PyRoboReplay
$ dash-pyroboreplay             # View RGB+Thermal fusion status
$ dash-pyroboreplay-live        # Monitor decision reconstruction in real-time
$ dash-pyroboreplay-export      # Export to Prometheus/Datadog

# PyTerrainMap
$ dash-pyterrainmap             # View spatial layer metrics
$ dash-pyterrainmap-live        # Watch fleet learning converge
$ dash-pyterrainmap-export      # Save to /tmp/pyterrainmap_metrics.json
```

---

## 🔄 Dashboard Modes

### Static Snapshot (`--static`)
```bash
$ dash-pystreamai               # Single view, exits immediately
# Useful for: CI/CD logs, monitoring integration, one-time checks
```

### Live View (`--live`)
```bash
$ dash-pystreamai-live          # Continuous updates until Ctrl+C
# Useful for: real-time monitoring, troubleshooting, development
```

### JSON Export (`--export`)
```bash
$ dash-pystreamai-export        # Saves to /tmp/pystreamai_metrics.json
# Useful for: integration with Prometheus, Datadog, custom dashboards
```

---

## 🛑 Remove Keyboard Shortcuts

To uninstall all dashboard aliases:

```bash
bash <(curl -s https://raw.githubusercontent.com/Mullassery/[PACKAGE]/main/scripts/setup_shortcuts.sh) --remove
```

This removes all `dash-*` aliases from your shell config.

---

## 📊 Monitoring Integration

Export metrics for external monitoring systems:

```bash
# Prometheus
$ dash-pystreamai-export > prometheus_metrics.txt

# Datadog (with custom agent)
$ dash-pystreamai-live | \
  grep -o 'Status.*' | \
  datadog-agent custom-metric

# JSON for custom dashboards
$ dash-pystreamai-export | jq '.metrics'
```

---

## ❓ Troubleshooting

**Shortcuts not working?**
```bash
# Reload shell config
$ source ~/.zshrc          # macOS/Linux (zsh)
$ source ~/.bashrc         # Linux (bash)

# Or restart your terminal
```

**Dashboard won't start?**
```bash
# Ensure package is installed
$ pip list | grep pystreamai

# Start manually
$ pystreamai dashboard --static
```

**Dashboard keeps closing?**
```bash
# Use live mode (restarts automatically)
$ dash-pystreamai-live
```

---

## 📖 Package-Specific Shortcuts

The following Mullassery packages support dashboard shortcuts:

- ✅ PyStreamAI (deployment metrics)
- ✅ PyStreamMCP (tool orchestration)
- ✅ PyStreamPDF (document processing)
- ✅ PyStreamXL (formula extraction)
- ✅ StatGuardian (data quality)
- ✅ PyReverseETL (activation pipelines)
- ✅ PyTerrainMap (spatial analysis)
- ✅ PyRoboReplay (multi-modal fusion)
- ✅ PyRoboSimulator (world engine)

Run `dashboards` to see all available shortcuts.
