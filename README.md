Checklist conversion toolkit

This repository contains scripts and templates to convert `Combined VFR and IFR Flight Ch 1.docx` into a duplex, US half‑letter laminated checklist.

Dependencies
- Python 3.8+
- pip packages: python-docx, pyyaml
- pandoc
- xelatex (TeX distribution) for LaTeX build
- wkhtmltopdf (optional) for HTML->PDF

Install python deps:

```bash
python3 -m pip install --user python-docx pyyaml
```

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
