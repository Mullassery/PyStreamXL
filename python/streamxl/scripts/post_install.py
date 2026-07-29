"""Post-installation message for PyStreamXL"""


def post_install():
    message = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ PyStreamXL v1.2.0 installed successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 WHAT IS PyStreamXL?
   Spreadsheet formula extraction and analysis. Parse Excel formulas, build
   dependency graphs, identify broken references, and export structured data.

🚀 GET STARTED IN 2 MINUTES:

   Step 1 — Parse an Excel file:
   $ pystreamxl parse myfile.xlsx

   Step 2 — Analyze formulas and references:
   $ pystreamxl analyze myfile.xlsx --show-dependencies

   Step 3 — View extraction dashboard:
   $ pystreamxl dashboard

📚 KEY FEATURES YOU CAN DO:
   • Parse Excel formulas and extract their structure
   • Generate formula dependency graphs for analysis
   • Identify broken cell references and circular dependencies
   • Export formulas as structured JSON or CSV
   • Analyze formula complexity and reuse patterns
   • Batch process multiple files with progress tracking

📊 VIEW DASHBOARD:
   $ pystreamxl dashboard              # Interactive extraction view
   $ pystreamxl dashboard --static     # Static snapshot
   $ pystreamxl dashboard --alerts     # Show alerts only

📖 LEARN MORE:
   Quick Start:  https://github.com/mullassery/pystreamxl#usage
   Examples:     https://github.com/mullassery/pystreamxl/tree/main/examples
   Issues:       https://github.com/mullassery/pystreamxl/issues

❓ GET HELP ANYTIME:
   $ pystreamxl --help
   $ pystreamxl --version
   $ pystreamxl parse --help          # Help for specific command

⏱️  NEXT STEP: Run `pystreamxl parse yourfile.xlsx` to analyze formulas!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(message)


if __name__ == "__main__":
    post_install()
