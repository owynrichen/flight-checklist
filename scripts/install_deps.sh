#!/usr/bin/env bash
set -euo pipefail

# Simple logger
log() { printf '%s %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install system build dependencies." >&2
  exit 1
fi

echo "This installer prefers 'uv' if installed globally. If you don't have uv, the script will bootstrap a .venv."

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y \
    pandoc \
    unzip \
    python3-venv \
    python3-pip
  echo "Note: xelatex is optional (only needed for LaTeX builds). Playwright is required for PDF generation and must be installed into your project environment via uv or pip."
elif command -v brew >/dev/null 2>&1; then
  echo "Detected Homebrew — installing platform packages via brew."
  brew update
  brew install pandoc
  echo "Note: install a TeX distribution (MacTeX) separately if you need LaTeX builds. Playwright is required for PDF generation and must be installed into your project environment via uv or pip."
else
  echo "Unsupported package manager. Please install pandoc and unzip manually."
fi

# Prefer global uv if present
if command -v uv >/dev/null 2>&1; then
  log "Using global 'uv' to manage project environment. Ensuring venv and syncing packages."
  # Create or ensure the project venv exists
  if ! uv venv .venv --allow-existing -p 3.12; then
    log "ERROR: uv venv failed"
    exit 1
  fi
  # Try a high-level sync, fall back to explicit pip install into the project
  if uv sync --project . 2>/dev/null; then
    log "uv sync succeeded"
  else
    log "uv sync failed or not supported for this project; installing packages explicitly into project environment"
    if ! uv pip install --project . PyYAML playwright; then
      log "ERROR: uv pip install failed"
      exit 1
    fi
  fi
  # Ensure Playwright browser binaries are installed inside the project venv
  if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    if ! "$REPO_ROOT/.venv/bin/python" -m playwright install chromium; then
      log "ERROR: playwright browser install failed"
      exit 1
    fi
  else
    log "ERROR: Project venv python not found; please run 'uv venv .venv' and install Playwright browsers manually."
    exit 1
  fi
else
  log "'uv' not found — creating a local .venv and installing dependencies there."
  if [ ! -d "$REPO_ROOT/.venv" ]; then
    if ! python3 -m venv "$REPO_ROOT/.venv"; then
      log "ERROR: python3 -m venv failed"
      exit 1
    fi
  fi
  . "$REPO_ROOT/.venv/bin/activate"
  if ! python -m pip install --upgrade pip; then
    log "ERROR: pip upgrade failed inside venv"
    deactivate || true
    exit 1
  fi
  if ! python -m pip install PyYAML playwright; then
    log "ERROR: pip install PyYAML playwright failed"
    deactivate || true
    exit 1
  fi
  if ! python -m playwright install chromium; then
    log "ERROR: playwright browser install failed"
    deactivate || true
    exit 1
  fi
  deactivate || true
fi

echo "All build dependencies installed."
