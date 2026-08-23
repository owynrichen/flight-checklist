#!/usr/bin/env python3
"""
Normalize Markdown heading hierarchy inside page segments.

When explicit <!-- PAGE_BREAK --> markers are used the renderer treats each
segment as a single kneeboard card. The renderer maps H2 headings to
top-level cards (<section class="card">). To keep multiple logical
subsections together on the same printed card, convert additional H2
headings in the same segment to H3 (nesting them under the first H2).

Usage:
  # dry-run (writes Combined_VFR_IFR_Ch1.normalized.md)
  python3 scripts/normalize_hierarchy.py Combined_VFR_IFR_Ch1.md

  # apply in-place (overwrite original)
  python3 scripts/normalize_hierarchy.py --inplace Combined_VFR_IFR_Ch1.md

The script is conservative: only transforms H2 (lines that start with
"## ") into H3 ("### ") when they are not the first H2 in their
PAGE_BREAK segment. It preserves other heading levels and blank lines.
"""
import argparse
from pathlib import Path

PAGE_BREAK = '<!-- PAGE_BREAK -->'


def normalize_text(lines):
    out = []
    i = 0
    n = len(lines)
    while i < n:
        # process a segment up to the next PAGE_BREAK (inclusive)
        seg = []
        while i < n:
            seg.append(lines[i])
            if lines[i].strip() == PAGE_BREAK:
                i += 1
                break
            i += 1
        # transform H2s inside seg: keep the first H2 as-is, convert others to H3
        first_h2_seen = False
        for idx, ln in enumerate(seg):
            stripped = ln.lstrip()
            # match markdown H2 heading (starts with '##' followed by space)
            if stripped.startswith('## '):
                if not first_h2_seen:
                    first_h2_seen = True
                    out.append(ln)
                else:
                    # preserve leading indentation if any
                    leading = ln[:len(ln) - len(stripped)]
                    out.append(leading + '### ' + stripped[3:])
            else:
                out.append(ln)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('file', help='Markdown file to process')
    p.add_argument('--inplace', action='store_true', help='Overwrite the input file')
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f'File not found: {path}')

    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    normalized = normalize_text(lines)
    out_path = path if args.inplace else path.with_suffix('.normalized.md')
    out_path.write_text(''.join(normalized), encoding='utf-8')
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
