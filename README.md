Checklist conversion toolkit

This repository contains scripts and templates to convert checklist source Markdown (Combined_VFR_IFR_Ch1.md) into a duplex, US half‑letter laminated checklist.

Setup

1. Install system tools: `pandoc` and `unzip`.
2. Install a global Python environment manager: `uv` (preferred) — install with `pipx install uv` or `python3 -m pip install --user uv`.
3. Create a project environment and install Python deps via `uv sync` (or `uv venv` + `uv pip install --project .`) and run project commands with `uv run` (recommended). Alternatively install required packages manually into a venv.


This repo supports two workflows:

- Recommended (uv + package.json):

```bash
# install uv globally (once)
python3 -m pip install --user pipx && python3 -m pipx ensurepath
pipx install uv

# install project Python deps declared in package.json
# Preferred sequence with modern uv:
# 1. Create/ensure project venv: uv venv .venv
# 2. Install deps into project venv: uv pip install --project .
# 3. Run commands in the project environment: uv run python scripts/...
# Example (recommended):
uv venv .venv --allow-existing -p 3.12 && uv pip install --project .

# To run project scripts use uv run, which ensures the project environment is active:
# uv run python3 scripts/check_setup.py
```

- Fallback (venv) — works everywhere:

```bash
python3 -m venv .venv
. .venv/bin/activate
# Install required runtime packages (declared in package.json). If not using uv,
# install them with pip:
python -m pip install PyYAML playwright
python -m playwright install chromium
```

Helper script (Debian/Ubuntu):

```bash
./scripts/install_deps.sh
```

Check your setup:

```bash
python3 scripts/check_setup.py
```


Required Dependencies

- Python 3.8+
- pandoc (DOCX → Markdown and small MD→HTML conversions)
- unzip (used to extract images from DOCX)
- PyYAML (required by rendering scripts)
- playwright (required for HTML→PDF rendering using Chromium)

Notes

- `uv` is the recommended global environment manager for running project Python commands. It is not a runtime dependency of the built artifacts; it only manages virtual environments and helps run Python commands consistently.
- weasyprint and wkhtmltopdf are no longer recommended and have been removed from the toolchain. Use playwright for PDF generation.

Checklist generation flow

```mermaid
flowchart LR
  A[Combined_VFR_IFR_Ch1.md] --> B[render_checklist_v2.py]
  B --> C[output/checklist_print_ready.html]
  C --> D[playwright - Chromium -> PDF]
  D --> E[output/checklist_from_yaml.html]
  E --> F[playwright - Chromium -> PDF]
  style A fill:#f9f,stroke:#333,stroke-width:1px
  style D fill:#9cf,stroke:#333
  style E fill:#cfc,stroke:#333
```

Quick build (HTML proof):

```bash
# from repo root (uses Combined_VFR_IFR_Ch1.md in the repo root)
./templates/html_css/us-halfletter/build.sh
```

Quick build (HTML -> PDF using Playwright):

```bash
# from repo root (uses Combined_VFR_IFR_Ch1.md in the repo root)
./templates/html_css/us-halfletter/build.sh
```

Outputs will be written to `output/`.

Heading / Page-break conventions
===============================

This project relies on a simple, well-defined mapping between Markdown
heading levels and the printed kneeboard layout. Keep these rules in mind
when editing the source Markdown (Combined_VFR_IFR_Ch1.md):

- Use H1 (#) once at the top of the document for the overall checklist
  title. The renderer will use the first H1 as the printed title band.
- Use H2 (##) to define top-level procedure groups that should appear as
  separate cards within a single kneeboard page segment. Each H2 becomes
  a <section class="card"> in the output HTML.
- Use H3 (###) for logical subsections that must stay visually grouped
  inside their parent H2 card (they render as .subsection inside the
  H2 card). The renderer hides H3 text in print but keeps the item
  groups together for layout safety.
- Use the explicit page break marker <!-- PAGE_BREAK --> on a line by
  itself to force a new kneeboard card. The renderer will partition the
  Markdown at these markers: everything between markers becomes one
  printed <main class="columns"> card (two-column layout). Place the
  marker on the line immediately before the H2 that should start the
  next card (no blank line between marker and the heading).

Automatic hierarchy normalization
--------------------------------

To reduce accidental layout drift (for example, many H2s in the same
segment causing them to render as separate cards within one printed
page), we provide a helper script `scripts/normalize_hierarchy.py`.

- Behavior: for each PAGE_BREAK-delimited segment the script keeps the
  first H2 as a top-level card and converts subsequent H2 headings to
  H3. This preserves author intent: sections that belong on the same
  physical card remain grouped under the first H2.
- Usage examples:

```bash
# produce a normalized copy (does not modify original)
python3 scripts/normalize_hierarchy.py Combined_VFR_IFR_Ch1.md

# apply in-place (will overwrite Combined_VFR_IFR_Ch1.md)
python3 scripts/normalize_hierarchy.py --inplace Combined_VFR_IFR_Ch1.md
```

If you prefer manual control, do not run the script and instead ensure
you use H2/H3 intentionally per the rules above. The validator will
still check that <!-- PAGE_BREAK --> markers exist where required.
