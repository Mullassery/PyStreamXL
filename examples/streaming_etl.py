"""Stream a large XLSX file and write to CSV — constant memory.

Cell values come from the source .xlsx file and must be treated as
untrusted: a cell containing e.g. "=cmd|'/c calc'!A0" will be executed as a
formula by Excel/LibreOffice/Google Sheets if written to CSV verbatim and
reopened later (CSV/formula-injection). We neutralize each cell with
streamxl.security.sanitize_csv_cell() before writing it out.
"""
import csv
import streamxl
from streamxl.security import sanitize_csv_cell

INPUT = "large.xlsx"
OUTPUT = "output.csv"

with open(OUTPUT, "w", newline="") as f:
    writer = csv.writer(f)
    for row in streamxl.read(INPUT):
        writer.writerow([sanitize_csv_cell(cell) for cell in row])

print(f"Done. Written to {OUTPUT}")
