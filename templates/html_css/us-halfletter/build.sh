#!/usr/bin/env bash
set -euo pipefail

# Build script (HTML -> PDF) for US half-letter checklist
# Requires: pandoc, playwright (Chromium via Playwright)
# Usage: ./build.sh [optional path to DOCX]

# Resolve paths so the script can be run from any working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

DOCX_PATH=""
# Optional flags: --page-size half|letter, --columns N
PAGE_SIZE="half"
COLUMNS=2
while [ "$#" -gt 0 ]; do
  case "$1" in
    --page-size)
      PAGE_SIZE="$2"; shift 2;;
    --columns)
      COLUMNS="$2"; shift 2;;
    *)
      # treat any other positional arg as the optional DOCX path
      DOCX_PATH="$1"; shift;;
  esac
done

OUTDIR="$REPO_ROOT/output"
mkdir -p "$OUTDIR"

# Fail fast if the host can't support a build yet.
if command -v uv >/dev/null 2>&1; then
  uv run python3 "$REPO_ROOT/scripts/check_setup.py"
else
  python3 "$REPO_ROOT/scripts/check_setup.py"
fi

# Clear only artifacts this build owns so HTML/PDF can coexist for validation
SUFFIX="${PAGE_SIZE}_${COLUMNS}c"
rm -f "$OUTDIR/checklist_print_ready_${SUFFIX}.html" "$OUTDIR/checklist_print_ready_${SUFFIX}.pdf" "$OUTDIR/checklist_from_yaml.html" || true

# Step 1: optionally extract markdown and images using the repo script
  if [ -n "$DOCX_PATH" ]; then
  echo "DOCX path supplied — regenerating Markdown and images from DOCX"
  if command -v uv >/dev/null 2>&1; then
    uv run python3 "$REPO_ROOT/scripts/extract_docx_structure.py" "$DOCX_PATH"
  else
    python3 "$REPO_ROOT/scripts/extract_docx_structure.py" "$DOCX_PATH"
  fi
else
  echo "No DOCX path supplied — using existing Combined_VFR_IFR_Ch1.md in repo root"
fi

# Step 2: convert Markdown to HTML
PANDOC_INPUT="$REPO_ROOT/Combined_VFR_IFR_Ch1.md"
if [ ! -f "$PANDOC_INPUT" ]; then
  echo "Expected markdown $PANDOC_INPUT not found. Extraction may have failed."
  exit 1
fi

# Ensure styles and images are copied into output
cp "$SCRIPT_DIR/checklist.css" "$OUTDIR/" || true
if [ -d "$REPO_ROOT/docx_images" ]; then
  cp -r "$REPO_ROOT/docx_images" "$OUTDIR/" || true
fi

# Render HTML using the repository renderer (supports YAML or Markdown source)
if [ -x "$(command -v python3)" ]; then
  echo "Rendering HTML using scripts/render_checklist_v2.py (markdown, hierarchical)..."
  # Run the renderer under the project environment via uv run if available
  if command -v uv >/dev/null 2>&1; then
    uv run python3 "$REPO_ROOT/scripts/render_checklist_v2.py" --columns "$COLUMNS" --page-size "$PAGE_SIZE"
  else
    python3 "$REPO_ROOT/scripts/render_checklist_v2.py" --columns "$COLUMNS" --page-size "$PAGE_SIZE"
  fi
  # ensure output filename matches expected
  if [ -f "$REPO_ROOT/output/checklist_from_yaml.html" ]; then
    mv "$REPO_ROOT/output/checklist_from_yaml.html" "$OUTDIR/checklist_print_ready_${SUFFIX}.html"
  fi
  # Inline critical stylesheet into generated HTML for portability
  if [ -f "$OUTDIR/checklist_print_ready_${SUFFIX}.html" ] && [ -f "$OUTDIR/checklist.css" ]; then
    # Inline CSS into the generated HTML in a portable way using Python
    if command -v uv >/dev/null 2>&1; then
      uv run python3 - <<PY
from pathlib import Path
f=Path('$OUTDIR/checklist_print_ready_${SUFFIX}.html')
css=Path('$OUTDIR/checklist.css').read_text(encoding='utf-8')
html=f.read_text(encoding='utf-8')
html=html.replace('<link rel="stylesheet" href="checklist.css">', f'<style>{css}</style>')
f.write_text(html, encoding='utf-8')
print('Inlined CSS into', f)
PY
    else
      python3 - <<PY
from pathlib import Path
f=Path('$OUTDIR/checklist_print_ready_${SUFFIX}.html')
css=Path('$OUTDIR/checklist.css').read_text(encoding='utf-8')
html=f.read_text(encoding='utf-8')
html=html.replace('<link rel="stylesheet" href="checklist.css">', f'<style>{css}</style>')
f.write_text(html, encoding='utf-8')
print('Inlined CSS into', f)
PY
    fi
  fi
else
  # Fallback: generate HTML from markdown and insert into template
  TMP_HTML=$(mktemp)
  pandoc "$PANDOC_INPUT" -f gfm -t html -o "$TMP_HTML"
  TEMPLATE="$SCRIPT_DIR/checklist.html"
  {
    while IFS= read -r line; do
      if [[ "$line" == *"<!-- Replace with generated HTML"* ]]; then
        cat "$TMP_HTML"
      else
        printf '%s\n' "$line"
      fi
    done < "$TEMPLATE"
  } > "$OUTDIR/checklist_print_ready.html"
  rm -f "$TMP_HTML"
fi

# Convert to PDF using Playwright so the browser and PDF use the same layout engine.
PDF_HTML="$OUTDIR/checklist_print_ready_${SUFFIX}.html"
# Use Playwright (Chromium) to render HTML -> PDF. Playwright must be installed
# in the project environment (uv or .venv) and browser binaries must be installed
# via: python -m playwright install chromium
if command -v uv >/dev/null 2>&1; then
  # Run Playwright PDF rendering under the project environment
  uv run python3 - <<PY
from pathlib import Path
from playwright.sync_api import sync_playwright

html_path = Path(r"$PDF_HTML").resolve()
pdf_path = Path(r"$OUTDIR/checklist_print_ready_${SUFFIX}.pdf").resolve()

# Determine viewport from page size (use 96 DPI)
page_sizes = {'half': (5.5,8.5), 'letter': (8.5,11.0)}
pw, ph = page_sizes.get('$PAGE_SIZE', (5.5,8.5))
vw = int(pw * 96)
vh = int(ph * 96)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": vw, "height": vh})
    page.goto(html_path.as_uri(), wait_until="networkidle")
    page.emulate_media(media="print")
    page.pdf(
        path=str(pdf_path),
        print_background=True,
        prefer_css_page_size=True,
        margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"},
    )
    browser.close()
print(f"PDF written to {pdf_path} (playwright)")
PY
else
  if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    "$REPO_ROOT/.venv/bin/python" - <<PY
from pathlib import Path
from playwright.sync_api import sync_playwright

html_path = Path(r"$PDF_HTML").resolve()
pdf_path = Path(r"$OUTDIR/checklist_print_ready_${SUFFIX}.pdf").resolve()

page_sizes = {'half': (5.5,8.5), 'letter': (8.5,11.0)}
pw, ph = page_sizes.get('$PAGE_SIZE', (5.5,8.5))
vw = int(pw * 96)
vh = int(ph * 96)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": vw, "height": vh})
    page.goto(html_path.as_uri(), wait_until="networkidle")
    page.emulate_media(media="print")
    page.pdf(
        path=str(pdf_path),
        print_background=True,
        prefer_css_page_size=True,
        margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"},
    )
    browser.close()
print(f"PDF written to {pdf_path} (playwright)")
PY
  else
    echo "Playwright not available in project environment. Please run 'uv venv .venv' and install playwright + browsers."
    echo "HTML proof written to $OUTDIR/checklist_print_ready.html"
  fi
fi
# end Playwright PDF rendering

# Capture screenshots after PDF generation so page images are available too.
if [ -x "$REPO_ROOT/.venv/bin/python" ] && [ -f "$OUTDIR/checklist_print_ready_${SUFFIX}.html" ]; then
  "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/capture_html_screenshot.py" --html "$OUTDIR/checklist_print_ready_${SUFFIX}.html" --out "$OUTDIR/checklist-html-screenshot_${SUFFIX}.png" --pdf "$OUTDIR/checklist_print_ready_${SUFFIX}.pdf" || true
fi

if [ -f "$OUTDIR/checklist-html-screenshot_${SUFFIX}.png" ]; then
  echo "Screenshot written to $OUTDIR/checklist-html-screenshot_${SUFFIX}.png"
fi
