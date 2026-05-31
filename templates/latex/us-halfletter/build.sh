#!/usr/bin/env bash
set -euo pipefail

# Build script for LaTeX checklist (US half-letter)
# Requires: pandoc, xelatex
# Usage: ./build.sh /path/to/Combined\ VFR\ and\ IFR\ Flight\ Ch\ 1.docx

# Resolve paths so the script can be run from any working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Optional DOCX path
DOCX_PATH="${1:-}"

OUTDIR="$REPO_ROOT/output"
mkdir -p "$OUTDIR"

# Fail fast if the host can't support a build yet.
python3 "$REPO_ROOT/scripts/check_setup.py"

# Clear output directory for reproducible builds
rm -rf "$OUTDIR"/* || true

# Step 1: optionally extract markdown and images using the repo script
if [ -n "$DOCX_PATH" ]; then
  python3 "$REPO_ROOT/scripts/extract_docx_structure.py" "$DOCX_PATH"
else
  echo "No DOCX path supplied — using existing Markdown/YAML in repo root"
fi

# Step 2: render PDF via pandoc -> xelatex with US half-letter geometry
PANDOC_INPUT="$REPO_ROOT/Combined_VFR_IFR_Ch1.md"
if [ ! -f "$PANDOC_INPUT" ]; then
		echo "Expected markdown $PANDOC_INPUT not found. Extraction may have failed."
		exit 1
fi

# Prepare a LaTeX-friendly markdown that wraps emoji characters with \emoji{...}
LATEX_MD="$REPO_ROOT/Combined_VFR_IFR_Ch1_latex.md"
if [ -f "$REPO_ROOT/scripts/latex_prepare.py" ]; then
	python3 "$REPO_ROOT/scripts/latex_prepare.py"
fi
if [ -f "$LATEX_MD" ]; then
	PANDOC_INPUT="$LATEX_MD"
fi

# Copy any extracted images to output so PDF generation can find them
if [ -d "$REPO_ROOT/docx_images" ]; then
	cp -r "$REPO_ROOT/docx_images" "$OUTDIR/" || true
fi

FONT_FILE="$REPO_ROOT/output/fonts/NotoColorEmoji.ttf"
TEMP_HEADER=""
if [ -f "$FONT_FILE" ]; then
	echo "Using local emoji font: $FONT_FILE"
	TEMP_HEADER=$(mktemp)
	cat > "$TEMP_HEADER" <<EOF
\\usepackage{fontspec}
\\newfontfamily\\Emoji[Path=$(dirname "$FONT_FILE")/]{NotoColorEmoji.ttf}
\\DeclareRobustCommand{\\emoji}[1]{{\\Emoji #1}}
EOF
	HEADER="$TEMP_HEADER"
else
	# Fallback header (may use system font names)
	HEADER="$SCRIPT_DIR/emoji-header.tex"
fi

pandoc "$PANDOC_INPUT" -o "$OUTDIR/checklist_print_ready.pdf" \
		--pdf-engine=xelatex \
		-H "$HEADER" \
		-V geometry:paperwidth=5.5in -V geometry:paperheight=8.5in -V geometry:margin=0.4in

if [ -n "$TEMP_HEADER" ] && [ -f "$TEMP_HEADER" ]; then
	rm -f "$TEMP_HEADER"
fi

echo "PDF written to $OUTDIR/checklist_print_ready.pdf"
