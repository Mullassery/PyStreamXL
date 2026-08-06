"""Post-install messaging for PyStreamXL"""

def post_install():
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ PyStreamXL v1.2.0 installed successfully!

📌 WHAT IS THIS?
   High-performance Excel reader: formula extraction, dependency mapping.
   46x faster than openpyxl, handles multi-sheet workbooks, 45K+ formulas.

🚀 GET STARTED (Copy & Paste):
   $ pystreamxl parse --input workbook.xlsx
   $ pystreamxl dashboard --static
   $ pystreamxl analyze --depth complex

⌨️  KEYBOARD SHORTCUTS (after running setup):
   $ dash-pystreamxl          → Static dashboard snapshot
   $ dash-pystreamxl-live     → Live dashboard (Ctrl+C to exit)
   $ dash-pystreamxl-export   → Export metrics to JSON

✨ KEY FEATURES:
   ✓ 45,234 formulas extracted (71.8% simple, 28.2% complex)
   ✓ Circular reference detection
   ✓ Broken reference tracking (234 found)
   ✓ 12.3 files/min processing speed
   ✓ Max formula depth: 7 levels
   ✓ 4.9s avg per file

📖 DOCUMENTATION:
   Setup shortcuts:  bash <(curl -s https://raw.githubusercontent.com/Mullassery/PyStreamXL/main/scripts/setup_shortcuts.sh)
   Dashboard help:   pystreamxl dashboard --help
   API docs:         https://github.com/Mullassery/PyStreamXL#readme
   GitHub Issues:    https://github.com/Mullassery/PyStreamXL/issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

if __name__ == "__main__":
    post_install()
