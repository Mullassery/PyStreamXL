#!/usr/bin/env bash
# Manual PyPI publish fallback for when Trusted Publishing (OIDC) is not yet
# configured on the PyPI project.
#
# Usage:
#   PYPI_API_TOKEN=pypi-... scripts/publish_pypi.sh [dist-dir]
#
# Builds the sdist + a wheel for the active interpreter (or uploads an existing
# dist/ directory if present), checks the artifacts, and uploads with twine.
set -euo pipefail

DIST_DIR="${1:-dist}"
if [[ -z "${PYPI_API_TOKEN:-}" ]]; then
  echo "PYPI_API_TOKEN is required (create a PyPI API token scoped to pystreamxl)." >&2
  exit 1
fi

python -m pip install --upgrade pip maturin twine >/dev/null
rm -rf "$DIST_DIR"
maturin build --release --out "$DIST_DIR"
maturin sdist --out "$DIST_DIR"

echo "Artifacts:"
ls -l "$DIST_DIR"
twine check "$DIST_DIR"/*

echo "Uploading to PyPI..."
twine upload --non-interactive \
  --username __token__ \
  --password "$PYPI_API_TOKEN" \
  "$DIST_DIR"/*

echo "Done. Verify: https://pypi.org/project/pystreamxl/"
