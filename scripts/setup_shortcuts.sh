#!/bin/bash
# Setup keyboard shortcuts for PyStreamXL

add_shortcuts() {
  if [ -f ~/.zshrc ]; then
    RC_FILE=~/.zshrc
  elif [ -f ~/.bashrc ]; then
    RC_FILE=~/.bashrc
  else
    echo "❌ No shell config found"; return 1
  fi
  
  if grep -q "dash-pystreamxl" "$RC_FILE"; then
    echo "⚠️  Shortcuts already installed"; return 0
  fi
  
  cat >> "$RC_FILE" << 'ALIASES'

# PyStreamXL dashboard shortcuts
alias dash-pystreamxl='pystreamxl dashboard --static'
alias dash-pystreamxl-live='pystreamxl dashboard'
alias dash-pystreamxl-export='pystreamxl dashboard --export /tmp/pystreamxl_metrics.json && echo ✓ Exported'
ALIASES
  
  echo "✅ Shortcuts added to $RC_FILE"
  echo "   Run: source $RC_FILE"
}

remove_shortcuts() {
  sed -i '' '/# PyStreamXL dashboard shortcuts/,/alias dash-pystreamxl-export=/d' ~/.zshrc 2>/dev/null
  sed -i '' '/# PyStreamXL dashboard shortcuts/,/alias dash-pystreamxl-export=/d' ~/.bashrc 2>/dev/null
  echo "✅ Shortcuts removed"
}

case "${1:-}" in --remove) remove_shortcuts ;; *) add_shortcuts ;; esac
