# Plan: Convert DOCX to Double‑Sided Laminated Checklist

Goal: Convert checklist source Markdown (Combined_VFR_IFR_Ch1.md) into a US half‑letter (5.5"×8.5") double‑sided laminated checklist PDF. This repo contains extraction scripts, HTML/CSS templates, and build scripts to produce print‑ready PDFs. If you have the original DOCX you can optionally regenerate the Markdown via scripts/extract_docx_structure.py.

Steps
1. Extract text and images from DOCX to Markdown and an images folder.
2. Generate a structured checklist source (`checklist_source.yaml`).
3. Build proofs using HTML/CSS + Playwright (fast iteration and reliable PDF rendering).
4. Produce `output/checklist_print_ready.pdf`, `output/checklist_front.pdf`, and `output/checklist_back.pdf` for duplex printing.

Decisions
- Paper size: US half‑letter (5.5"×8.5")
- Single double‑sided card
- Spot color allowed; include diagrams
- Font: Roboto/Arial (sans‑serif)
- Highlighting: categorize items and color code

See `README.md` for build instructions and dependencies.
