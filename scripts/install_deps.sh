#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install system build dependencies." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  pandoc \
  unzip \
  texlive-xetex \
  weasyprint \
  wkhtmltopdf \
  python3-venv \
  python3-pip

if [ ! -d "$REPO_ROOT/.venv" ]; then
  python3 -m venv "$REPO_ROOT/.venv"
fi

"$REPO_ROOT/.venv/bin/python" -m pip install -r "$REPO_ROOT/requirements.txt"
"$REPO_ROOT/.venv/bin/python" -m playwright install chromium

echo "All build dependencies installed."
