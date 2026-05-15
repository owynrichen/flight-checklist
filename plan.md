# Plan: Convert DOCX to Double‑Sided Laminated Checklist

Goal: Convert `Combined VFR and IFR Flight Ch 1.docx` into a US half‑letter (5.5"×8.5") double‑sided laminated checklist PDF. This repo contains extraction scripts, LaTeX and HTML/CSS templates, and build scripts to produce print‑ready PDFs.

Steps
1. Extract text and images from DOCX to Markdown and an images folder.
2. Generate a structured checklist source (`checklist_source.yaml`).
3. Build proofs using LaTeX (precise control) and HTML/CSS (fast iteration).
4. Produce `output/checklist_print_ready.pdf`, `output/checklist_front.pdf`, and `output/checklist_back.pdf` for duplex printing.

Decisions
- Paper size: US half‑letter (5.5"×8.5")
- Single double‑sided card
- Spot color allowed; include diagrams
- Font: Roboto/Arial (sans‑serif)
- Highlighting: categorize items and color code

See `README.md` for build instructions and dependencies.
