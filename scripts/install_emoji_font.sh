#!/usr/bin/env bash
set -euo pipefail

# Download Noto Color Emoji into output/fonts/ (may be useful for rendering emoji in
# HTML/PDF outputs). This script requires curl or wget and unzip (the release may be a zip).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTDIR="$REPO_ROOT/output/fonts"
mkdir -p "$OUTDIR"

# Try to download the latest release TTF from the noto-emoji GitHub releases
URL="https://github.com/googlefonts/noto-emoji/releases/latest/download/NotoColorEmoji.ttf"

echo "Downloading Noto Color Emoji to $OUTDIR..."
if command -v curl >/dev/null 2>&1; then
  curl -L -o "$OUTDIR/NotoColorEmoji.ttf" "$URL"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$OUTDIR/NotoColorEmoji.ttf" "$URL"
else
  echo "Please install curl or wget to download the emoji font." >&2
  exit 1
fi

if [ -f "$OUTDIR/NotoColorEmoji.ttf" ]; then
  echo "Downloaded NotoColorEmoji.ttf to $OUTDIR"
  ls -l "$OUTDIR/NotoColorEmoji.ttf"
else
  echo "Failed to download NotoColorEmoji.ttf" >&2
  exit 1
fi

echo "Downloaded emoji font. You can use it for rendering HTML/PDF outputs if needed."
