Checklist conversion toolkit

This repository contains scripts and templates to convert `Combined VFR and IFR Flight Ch 1.docx` into a duplex, US half‑letter laminated checklist.

Setup

1. Install system tools: `pandoc`, `unzip`, `xelatex`, and `weasyprint`.
1. Install Python support packages: `python3-venv` and `python3-pip`.
1. Create a virtual environment and install the Python deps from `requirements.txt`.

Helper scripts:

```bash
./scripts/install_deps.sh
```

Example on Debian/Ubuntu:

```bash
./scripts/install_deps.sh
```

Check your setup:

```bash
python3 scripts/check_setup.py
```

Dependencies
- Python 3.8+
- pip packages: see `requirements.txt`
- pandoc
- xelatex (TeX distribution) for LaTeX build
- weasyprint (required for HTML→PDF; supports CSS3 multi-column)
- wkhtmltopdf (legacy fallback only; does NOT render multi-column correctly)

Quick build (HTML proof):

```bash
# from repo root
./templates/html_css/us-halfletter/build.sh "/path/to/Combined VFR and IFR Flight Ch 1.docx"
```

Quick build (LaTeX/pdf proof):

```bash
./templates/latex/us-halfletter/build.sh "/path/to/Combined VFR and IFR Flight Ch 1.docx"
```

Outputs will be written to `output/`.
