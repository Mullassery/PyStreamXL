#!/usr/bin/env bash
set -euo pipefail

echo "Building pystreamxl..."
maturin develop --release
echo "Build complete."
