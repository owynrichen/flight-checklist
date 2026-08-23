# Agents expectations for checklist generation

This document defines required behaviours for automated agents that generate
and validate the checklist outputs in this repository.

1) Content parity validation

- The agent MUST verify that all content used to produce the checklist (source
  `Combined_VFR_IFR_Ch1.md` or the DOCX it was extracted from) appears in the
  generated visual outputs: the HTML (`output/checklist_print_ready.html`) and
  the PDF build (`output/checklist_print_ready.pdf`).
- Validation checks should include: heading presence, checklist item counts,
  and sampling of checklist lines (normalized text matching). Any missing
  items must be reported with file/line references.

2) Hierarchical flow preservation

- The agent MUST ensure the visual checklist follows the hierarchical flow of
  the original content. Heading levels in the Markdown (H1/H2/H3...) must map
  to section headings in the rendered outputs. The agent should report a diff
  of Markdown headings vs rendered headings when mismatches occur.

3) Section color-coding

- The agent MUST enforce the following color-coding by section type:
  - `red`  — emergency procedure
  - `grey` — preflight and shutdown
  - `blue` — in-flight
  - `green`— other
- The renderer should add a semantic class or data-attribute to section
  containers (e.g. `.section.emergency` or `data-category="emergency"`) so
  validation can assert the correct color mapping rather than relying on
  pixel-color sampling.

4) Page break markers

- The canonical Markdown source MAY include explicit page break markers to
  express physical page grouping in the printed checklist: use <!-- PAGE_BREAK -->
  on a line by itself. The renderer MUST honor these markers and emit separate
  page containers in the HTML output (one or more <main class="columns"> blocks)
  so CSS can control physical page breaks for PDF generation.
- Validation MUST check for the presence of expected page break markers at
  agreed locations when the source intends a specific page layout (for example
  a page break before "NORMAL OPERATIONS" and before "EMERGENCY & ABNORMAL
  OPERATIONS"). If the markers are missing, the validator should report the
  Markdown file and line numbers where markers are expected.

Validation reporting and failure behaviour

- Agents MUST emit a concise validation report when builds run. The report
  should include counts, mismatches, and suggested fixes. For CI usage,
  failures in any of the three expectations should return a non-zero exit
  status so the pipeline can fail fast.

Implementation notes

- Suggested checks: parse Markdown headings, parse HTML/PDF text (or HTML),
  normalize whitespace/punctuation, and perform substring matching. Use the
  generated HTML/PDF as the canonical rendered source for parity checks; the
  LaTeX pipeline has been removed from the recommended toolchain.

Additions or changes to these expectations must be reviewed and agreed before
agents are updated to follow them.
