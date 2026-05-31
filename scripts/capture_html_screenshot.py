#!/usr/bin/env python3
"""Capture screenshots of the generated checklist into output/.

The HTML screenshot is written to `output/checklist-html-screenshot.png` by default.
If `pdftoppm` is available and the PDF exists, page images are also written as
`output/checklist-page-1.png`, `output/checklist-page-2.png`, etc.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a checklist HTML screenshot")
    parser.add_argument(
        "--html",
        default=os.path.join(os.path.dirname(__file__), "..", "output", "checklist_print_ready.html"),
        help="HTML file to capture",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(__file__), "..", "output", "checklist-html-screenshot.png"),
        help="Screenshot output path",
    )
    parser.add_argument(
        "--pdf",
        default=os.path.join(os.path.dirname(__file__), "..", "output", "checklist_print_ready.pdf"),
        help="PDF file to split into page images",
    )
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--height", type=int, default=6000)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - import-time dependency check
        print(f"Error: playwright is not installed: {exc}", file=sys.stderr)
        return 2

    html_path = os.path.abspath(args.html)
    out_path = os.path.abspath(args.out)
    if not os.path.exists(html_path):
        print(f"Error: HTML not found: {html_path}", file=sys.stderr)
        return 3

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    file_url = f"file://{html_path}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.emulate_media(media="print")
        page.goto(file_url, wait_until="networkidle")
        page.screenshot(path=out_path, full_page=True)
        browser.close()

    print(f"Wrote {out_path}")

    pdf_path = os.path.abspath(args.pdf)
    pdf_prefix = os.path.join(os.path.dirname(out_path), "checklist-page")
    if os.path.exists(pdf_path) and shutil.which("pdftoppm"):
        for existing in sorted(
            f for f in os.listdir(os.path.dirname(out_path)) if f.startswith("checklist-page-") and f.endswith(".png")
        ):
            try:
                os.remove(os.path.join(os.path.dirname(out_path), existing))
            except OSError:
                pass
        subprocess.run(["pdftoppm", "-png", "-f", "1", "-l", "999", pdf_path, pdf_prefix], check=True)
        print(f"Wrote page images to {os.path.dirname(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
