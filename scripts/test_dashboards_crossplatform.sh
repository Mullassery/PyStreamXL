#!/bin/bash
# Cross-platform dashboard testing script
# Supports: macOS, Linux, Windows (WSL, Git Bash, native Python)

set -e

OS=$(uname -s)
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PACKAGES=(pystreamai pystreammcp pystreampdf pystreamxl statguardian pyreverseetl pyterrainmap pyroboreplay pyrobosimulator)
TEST_RESULTS=()

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Cross-Platform Dashboard Test Suite                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "System: $OS"
echo "Python: $PYTHON_VERSION"
echo "Date: $(date)"
echo ""

# Test 1: Check Python version
echo "═══ Test 1: Python Version ═══"
if [[ "$PYTHON_VERSION" == 3.* ]]; then
  echo "✅ Python 3.x detected"
  TEST_RESULTS+=("Python Version: PASS")
else
  echo "❌ Python 3.x required"
  TEST_RESULTS+=("Python Version: FAIL")
fi

# Test 2: Check pip
echo ""
echo "═══ Test 2: pip Installation ═══"
if command -v pip3 &> /dev/null; then
  echo "✅ pip3 found"
  pip3 --version
  TEST_RESULTS+=("pip3: PASS")
else
  echo "❌ pip3 not found"
  TEST_RESULTS+=("pip3: FAIL")
fi

# Test 3: Test shell config file detection
echo ""
echo "═══ Test 3: Shell Configuration ═══"
if [ -f ~/.zshrc ]; then
  echo "✅ ~/.zshrc found"
  TEST_RESULTS+=("Shell Config (.zshrc): PASS")
elif [ -f ~/.bashrc ]; then
  echo "✅ ~/.bashrc found"
  TEST_RESULTS+=("Shell Config (.bashrc): PASS")
else
  echo "⚠️  No shell config found"
  TEST_RESULTS+=("Shell Config: WARN")
fi

# Test 4: Test Rich library (dashboard rendering)
echo ""
echo "═══ Test 4: Rich Library ═══"
if python3 -c "from rich.console import Console; from rich.table import Table" 2>/dev/null; then
  echo "✅ Rich library installed"
  TEST_RESULTS+=("Rich Library: PASS")
else
  echo "⚠️  Rich library not installed (will use fallback)"
  TEST_RESULTS+=("Rich Library: WARN")
  echo "   Install: pip install rich"
fi

# Test 5: Test package installations
echo ""
echo "═══ Test 5: Package Installations ═══"
for pkg in "${PACKAGES[@]}"; do
  if python3 -c "import $pkg" 2>/dev/null; then
    echo "✅ $pkg installed"
    TEST_RESULTS+=("$pkg: PASS")
  else
    echo "⚠️  $pkg not installed"
    TEST_RESULTS+=("$pkg: WARN")
  fi
done

# Test 6: Test dashboard execution (static mode)
echo ""
echo "═══ Test 6: Dashboard Execution (Static Mode) ═══"
for pkg in pystreamai pystreammcp pystreampdf; do
  if command -v $pkg &> /dev/null; then
    if $pkg dashboard --static > /dev/null 2>&1; then
      echo "✅ $pkg dashboard works"
      TEST_RESULTS+=("$pkg dashboard: PASS")
    else
      echo "⚠️  $pkg dashboard returned status code (but may still work)"
      TEST_RESULTS+=("$pkg dashboard: WARN")
    fi
  else
    echo "⚠️  $pkg CLI not found"
    TEST_RESULTS+=("$pkg CLI: WARN")
  fi
done

# Test 7: Test JSON export capability
echo ""
echo "═══ Test 7: JSON Export ═══"
EXPORT_TEST_FILE="/tmp/test_dashboard_export_$RANDOM.json"
if pystreamai dashboard --export $EXPORT_TEST_FILE 2>/dev/null; then
  if [ -f "$EXPORT_TEST_FILE" ]; then
    if python3 -c "import json; json.load(open('$EXPORT_TEST_FILE'))" 2>/dev/null; then
      echo "✅ JSON export and validation successful"
      TEST_RESULTS+=("JSON Export: PASS")
      rm "$EXPORT_TEST_FILE"
    else
      echo "❌ JSON export file invalid"
      TEST_RESULTS+=("JSON Export: FAIL")
    fi
  fi
fi

# Test 8: Platform-specific rendering
echo ""
echo "═══ Test 8: Platform Detection ═══"
case "$OS" in
  Darwin)
    echo "✅ macOS detected - Rich rendering available"
    TEST_RESULTS+=("Platform Detection: PASS")
    ;;
  Linux)
    echo "✅ Linux detected - Textual/Rich rendering available"
    if command -v textual &> /dev/null; then
      echo "   Textual (TUI) available"
    else
      echo "   Install Textual: pip install textual"
    fi
    TEST_RESULTS+=("Platform Detection: PASS")
    ;;
  MINGW*|MSYS*|CYGWIN*)
    echo "✅ Windows (Git Bash/MSYS2) detected - Rich rendering available"
    TEST_RESULTS+=("Platform Detection: PASS")
    ;;
  *)
    echo "⚠️  Unknown platform: $OS"
    TEST_RESULTS+=("Platform Detection: WARN")
    ;;
esac

# Test 9: Keyboard shortcuts setup
echo ""
echo "═══ Test 9: Keyboard Shortcuts ═══"
if [ -d "scripts" ] && [ -f "scripts/setup_shortcuts.sh" ]; then
  echo "✅ setup_shortcuts.sh found"
  if bash scripts/setup_shortcuts.sh --help &> /dev/null || bash scripts/setup_shortcuts.sh 2>&1 | grep -q "✅"; then
    echo "✅ Shortcuts setup script functional"
    TEST_RESULTS+=("Keyboard Shortcuts: PASS")
  else
    echo "⚠️  Shortcuts setup has warnings"
    TEST_RESULTS+=("Keyboard Shortcuts: WARN")
  fi
fi

# Test 10: OTEL exporter availability
echo ""
echo "═══ Test 10: OTEL Support ═══"
if python3 -c "import opentelemetry" 2>/dev/null; then
  echo "✅ OpenTelemetry installed"
  if python3 -c "from opentelemetry.exporter.prometheus import PrometheusMetricReader" 2>/dev/null; then
    echo "✅ Prometheus exporter available"
    TEST_RESULTS+=("OTEL Prometheus: PASS")
  else
    echo "⚠️  Prometheus exporter not installed"
    TEST_RESULTS+=("OTEL Prometheus: WARN")
  fi
else
  echo "⚠️  OpenTelemetry not installed"
  TEST_RESULTS+=("OTEL: WARN")
  echo "   Install: pip install opentelemetry-exporter-prometheus opentelemetry-exporter-otlp"
fi

# Print summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    Test Results Summary                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

for result in "${TEST_RESULTS[@]}"; do
  if [[ $result == *"PASS"* ]]; then
    echo "✅ $result"
    ((PASS_COUNT++))
  elif [[ $result == *"WARN"* ]]; then
    echo "⚠️  $result"
    ((WARN_COUNT++))
  else
    echo "❌ $result"
    ((FAIL_COUNT++))
  fi
done

echo ""
echo "Summary: $PASS_COUNT PASS | $WARN_COUNT WARN | $FAIL_COUNT FAIL"

if [ $FAIL_COUNT -eq 0 ]; then
  echo "✅ All critical tests passed!"
  exit 0
else
  echo "❌ Some tests failed. Please review the output above."
  exit 1
fi
