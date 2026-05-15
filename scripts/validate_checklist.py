#!/usr/bin/env python3
"""Validate checklist outputs against Markdown source.

Checks performed:
- Headings in `Combined_VFR_IFR_Ch1.md` appear in `output/checklist_print_ready.html`.
- Checkbox lines in Markdown appear as list items in HTML.
- Each HTML <section> has a `data-category` attribute and it matches an inferred
  category derived from the Markdown heading text.

Exit codes: 0 = success, 2 = validation failure
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / 'Combined_VFR_IFR_Ch1.md'
HTML = ROOT / 'output' / 'checklist_print_ready.html'

if not MD.exists():
    print('Missing', MD)
    sys.exit(2)
if not HTML.exists():
    print('Missing', HTML)
    sys.exit(2)

md = MD.read_text(encoding='utf-8')
html = HTML.read_text(encoding='utf-8')

def infer_category(title):
    t = title.lower()
    if any(k in t for k in ['emerg', 'critical', 'missed', 'engine failure', 'fire', 'immediate', 'memory']):
        return 'emergency'
    if any(k in t for k in ['preflight', 'taxi', 'shutdown', 'before takeoff', 'run-up', 'run‑up']):
        return 'grey'
    if any(k in t for k in ['flight', 'ifr', 'inflight', 'in‑flight', 'takeoff', 'climb', 'enroute', 'departure', 'approach']):
        return 'blue'
    return 'green'

def normalize(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.lower()
    s = re.sub(r"\*\*|\*|__|_", '', s)
    s = re.sub(r"[^\w\s%°≥≤'\-\.]+", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

# Headings: consider only markdown headings that actually have checklist items under them.
# Scan the markdown and record the most recent heading; if list items follow, mark that heading as a section.
md_lines = md.splitlines()
current_heading = 'General'
md_headings = []
heading_has_items = {}
for line in md_lines:
    hmatch = re.match(r'^(#{1,6})\s+(.*)', line)
    if hmatch:
        current_heading = hmatch.group(2).strip()
        # initialize
        heading_has_items.setdefault(current_heading, False)
        continue
    # treat checklist list prefixes and checkbox glyphs as items
    if re.match(r'^\s*([-*+]|\d+\.)\s+.+', line) or re.match(r'^\s*[☐⛔✔✅☑]', line):
        heading_has_items[current_heading] = True

# only include headings that have items under them
md_headings = [h for h, has in heading_has_items.items() if has]
html_headings = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html, flags=re.S)
html_headings_clean = [re.sub(r'<[^>]+>', '', h).strip() for h in html_headings]

missing_heads = [h for h in md_headings if not any(normalize(h) in normalize(hh) or normalize(hh) in normalize(h) for hh in html_headings_clean)]

# Checkbox lines
md_checkbox_lines = [line.strip() for line in md.splitlines() if re.match(r'^\s*[☐⛔✔✅☑]', line)]
html_lis = re.findall(r'<li>(.*?)</li>', html, flags=re.S)
html_items = [re.sub(r'<[^>]+>', '', li).strip() for li in html_lis]

missing_items = []
for m in md_checkbox_lines:
    norm_m = normalize(m)
    if not any(norm_m in normalize(h) or normalize(h) in norm_m for h in html_items):
        missing_items.append(m)

# Section category checks
section_pattern = re.compile(r'<section([^>]*)>\s*<h2[^>]*>(.*?)</h2>', flags=re.S)
sections = section_pattern.findall(html)
missing_attrs = []
category_mismatches = []
for attr, raw_title in sections:
    title = re.sub(r'<[^>]+>', '', raw_title).strip()
    inferred = infer_category(title)
    m = re.search(r'data-category="([^"]+)"', attr)
    if not m:
        missing_attrs.append(title)
    else:
        got = m.group(1)
        if got != inferred:
            category_mismatches.append((title, inferred, got))

# Print report
ok = True
print('Validation report')
print('-----------------')
print(f'Markdown headings: {len(md_headings)}; HTML headings: {len(html_headings_clean)}')
if missing_heads:
    ok = False
    print('\nMissing headings in HTML:')
    for h in missing_heads:
        print(' -', h)
else:
    print('All markdown headings present in HTML (approx).')

print(f'\nMarkdown checkbox lines: {len(md_checkbox_lines)}; HTML list items: {len(html_items)}')
if missing_items:
    ok = False
    print('\nMissing checklist items in HTML:')
    for it in missing_items[:50]:
        print(' -', it)
else:
    print('All markdown checkbox lines found in HTML.')

if missing_attrs:
    ok = False
    print('\nSections missing data-category attribute:')
    for t in missing_attrs:
        print(' -', t)
else:
    print('\nAll sections include data-category attribute.')

if category_mismatches:
    ok = False
    print('\nSection category mismatches (title, expected, found):')
    for t, exp, got in category_mismatches:
        print(f' - {t} -> expected {exp}, found {got}')
else:
    print('\nNo category mismatches detected.')

if not ok:
    print('\nValidation FAILED')
    sys.exit(2)
else:
    print('\nValidation passed.')
    sys.exit(0)
