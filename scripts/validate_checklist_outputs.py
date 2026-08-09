#!/usr/bin/env python3
"""
Validate checklist outputs against source markdown per AGENTS.md.

Checks performed:
- Heading presence: all markdown headings appear in HTML and LaTeX markdown
- Checklist item counts & presence: all checklist items appear in HTML and LaTeX markdown
- Section color-coding: HTML <section> elements have data-category attributes and LaTeX markdown contains data-category annotations

Usage:
  python3 scripts/validate_checklist_outputs.py [--source SOURCE_MD] [--latex-md LATEX_MD] [--html HTML_FILE]

Exit codes:
 - 0: success (no validation failures)
 - 2: validation failures
 - 3: missing required files
"""

import argparse
import os
import re
import sys
import html as htmllib

ALLOWED_CATEGORIES = set(['emergency', 'grey', 'blue', 'green'])

LEADING_MARKERS = (
    '☐', '☑', '✅', '✔', '⛔', '➡', '🟥', '🟩', '🟫', '🔁', '🔄',
    '🛫', '🛬', '🚨', '⚠️', '⚠', '⚡', '🎯', '📘', '🔥', '🧭', '▶', '✈️', '✈', '🔍',
)


def strip_item_prefix(text):
    text = re.sub(r'^\s*[-*+]\s*', '', text)
    text = re.sub(r'^\s*\[(?: |x|X)\]\s*', '', text)
    for marker in sorted(LEADING_MARKERS, key=len, reverse=True):
        if text.startswith(marker):
            return text[len(marker):].lstrip()
    return text.strip()

# Normalization: keep word characters and digits, join with spaces, lower-case
def normalize_text(s):
    if s is None:
        return ''
    # drop HTML tags
    s = re.sub(r'<[^>]+>', '', s)
    # drop LaTeX \emoji{...} markers
    s = re.sub(r'\\emoji\{.*?\}', '', s)
    # replace common dashes with hyphen
    s = s.replace('\u2013', '-').replace('\u2014', '-')
    # extract word tokens (unicode-aware)
    tokens = re.findall(r'\w+', s, flags=re.UNICODE)
    return ' '.join(tokens).lower().strip()

# Parse a markdown file for headings and checklist-like items
def parse_md(md_path):
    headings = []
    items = []
    with open(md_path, encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines, start=1):
        stripped = line.rstrip('\n')
        # headings like '#', '##'
        m = re.match(r'^(?P<prefix>\s*#+)\s*(?P<text>.+?)\s*$', stripped)
        if m:
            text = m.group('text').strip()
            if not text:
                continue
            level = len(m.group('prefix').strip())
            headings.append({'level': level, 'text': text, 'line': i})
            continue
        # item detection: list markers or leading emoji macros or leading emoji characters
        if re.match(r'^\s*[-*+]\s+', stripped) or '\\emoji{' in stripped or stripped.strip().startswith(tuple('☐☑✅⛔✔🔁🔄')):
            t = strip_item_prefix(stripped)
            t = re.sub(r'\\emoji\{.*?\}\s*', '', t)
            # unescape common markdown escapes (underscore) so normalization matches rendered HTML
            t = t.replace('\\_', '_')
            if t.strip():
                items.append({'text': t.strip(), 'line': i})
        elif re.match(r'^[A-Za-z0-9]', stripped):
            items.append({'text': stripped, 'line': i})
    return headings, items

# Parse generated HTML to extract headings, sections (with data-category) and items
def parse_html(html_path):
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    # headings
    headings = []
    for level in (1,2,3):
        for match in re.finditer(rf'<h{level}[^>]*>(.*?)</h{level}>', html, flags=re.S|re.I):
            inner = match.group(1)
            inner = re.sub(r'<[^>]+>', '', inner)
            inner = htmllib.unescape(inner).strip()
            headings.append({'level': level, 'text': inner})
    # sections
    sections = []
    for match in re.finditer(r'<section\b([^>]*)>(.*?)</section>', html, flags=re.S|re.I):
        attrs = match.group(1)
        inner = match.group(2)
        cat_m = re.search(r'data-category=["\']([^"\']+)["\']', attrs)
        category = cat_m.group(1) if cat_m else None
        h2_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', inner, flags=re.S|re.I)
        title = ''
        if h2_m:
            title = re.sub(r'<[^>]+>', '', h2_m.group(1))
            title = htmllib.unescape(title).strip()
        items = []
        for li in re.finditer(r'<li\b[^>]*>(.*?)</li>', inner, flags=re.S|re.I):
            li_html = li.group(1)
            li_html = re.sub(r'<span[^>]*class=["\']box["\'][^>]*>.*?</span>', '', li_html, flags=re.S|re.I)
            li_text = re.sub(r'<[^>]+>', '', li_html)
            li_text = htmllib.unescape(li_text).strip()
            if li_text:
                items.append(li_text)
        sections.append({'title': title, 'category': category, 'items': items})
    # fallback: all li in document
    all_items = []
    for li in re.finditer(r'<li\b[^>]*>(.*?)</li>', html, flags=re.S|re.I):
        li_html = li.group(1)
        li_html = re.sub(r'<[^>]+>', '', li_html)
        li_text = htmllib.unescape(li_html).strip()
        if li_text:
            all_items.append(li_text)
    # Also collect <p class='note'> and <p class='subheader'> texts so source items
    # rendered as notes / sub-headers still satisfy parity checks.
    for p in re.finditer(r"<p[^>]*class=[\"'](?:note|subheader)[\"'][^>]*>(.*?)</p>", html, flags=re.S|re.I):
        txt = re.sub(r'<[^>]+>', '', p.group(1))
        txt = htmllib.unescape(txt).strip()
        if txt:
            all_items.append(txt)
    return headings, sections, all_items

# Parse LaTeX-friendly markdown which includes raw latex comments inserted by latex_prepare.py
def parse_latex_md(md_path):
    with open(md_path, encoding='utf-8') as f:
        lines = f.readlines()
    headings = []
    items = []
    categories_map = {}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip().startswith('```{=latex}'):
            j = i+1
            while j < n and lines[j].strip() == '':
                j += 1
            if j < n and lines[j].strip().startswith('%'):
                cm = re.search(r'%\s*data-category:\s*([\w-]+)', lines[j])
                if cm:
                    cat = cm.group(1)
                    k = j+1
                    while k < n and not lines[k].strip().startswith('```'):
                        k += 1
                    l = k+1
                    while l < n and lines[l].strip() == '':
                        l += 1
                    if l < n and lines[l].lstrip().startswith('#'):
                        m = re.match(r'^(#+)\s*(.*)$', lines[l].lstrip())
                        if m:
                            level = len(m.group(1))
                            text = m.group(2).strip()
                            headings.append({'level': level, 'text': text, 'line': l+1, 'category': cat})
                            categories_map[normalize_text(text)] = cat
                            i = l+1
                            continue
            i += 1
            continue
        if line.lstrip().startswith('#'):
            m = re.match(r'^(#+)\s*(.*)$', line.lstrip())
            if m:
                level = len(m.group(1))
                text = m.group(2).strip()
                headings.append({'level': level, 'text': text, 'line': i+1})
        if re.match(r'^\s*[-*+]\s+', line) or '\\emoji{' in line or line.strip().startswith(tuple('☐☑✅⛔✔')):
            t = line.strip()
            t = strip_item_prefix(t)
            t = re.sub(r'\\emoji\{.*?\}\s*', '', t)
            # unescape backslash-escaped underscores to match HTML rendering
            t = t.replace('\\_', '_')
            if t.strip():
                items.append({'text': t.strip(), 'line': i+1})
        i += 1
    return headings, items, categories_map

# Matching helpers
def find_match_norm(norm, norm_list):
    if not norm:
        return None
    if norm in norm_list:
        return norm
    for t in norm_list:
        if norm in t or t in norm:
            return t
    return None

# Infer category heuristics duplicated from renderer
def infer_category(title):
    t = (title or '').lower()
    EMERGENCY_KW = [
        'emerg', 'critical', 'missed', 'engine failure', 'fire', 'immediate',
        'memory', 'forced landing', 'alternator', 'electrical fire', 'smoke',
        '🟥', '🚨', '⚡',
    ]
    if any(k in t for k in EMERGENCY_KW):
        return 'emergency'
    if any(k in t for k in ['preflight', 'taxi', 'shutdown', 'before takeoff', 'run-up', 'run\u2011up', 'prefight']):
        return 'grey'
    if any(k in t for k in ['flight', 'ifr', 'inflight', 'in\u2011flight', 'takeoff', 'climb',
                            'enroute', 'departure', 'approach', 'landing', 'go\u2011around', 'go-around']):
        return 'blue'
    return 'green'

# Main validation
def main():
    parser = argparse.ArgumentParser(description='Validate checklist outputs against source')
    parser.add_argument('--source', default='Combined_VFR_IFR_Ch1.md')
    parser.add_argument('--latex-md', default='Combined_VFR_IFR_Ch1_latex.md')
    parser.add_argument('--html', default='output/checklist_print_ready.html')
    args = parser.parse_args()

    # ensure files exist
    missing = [p for p in (args.source, args.latex_md, args.html) if not os.path.exists(p)]
    if missing:
        print('Error: missing files:', ', '.join(missing))
        sys.exit(3)

    src_headings, src_items = parse_md(args.source)
    latex_headings, latex_items, latex_cats = parse_latex_md(args.latex_md)
    html_headings, html_sections, html_all_items = parse_html(args.html)

    src_head_norm = [normalize_text(h['text']) for h in src_headings]
    src_item_norm = [normalize_text(it['text']) for it in src_items]
    html_head_norm = [normalize_text(h['text']) for h in html_headings]
    html_item_norm = [normalize_text(it) for it in html_all_items]
    latex_head_norm = [normalize_text(h['text']) for h in latex_headings]
    latex_item_norm = [normalize_text(it['text']) for it in latex_items]

    issues = []
    print('Validation summary:')
    print(f'  Source headings: {len(src_head_norm)}')
    print(f'  HTML headings:   {len(html_head_norm)}')
    print(f'  LaTeX headings:  {len(latex_head_norm)}')
    print(f'  Source items:    {len(src_item_norm)}')
    print(f'  HTML items:      {len(html_item_norm)}')
    print(f'  LaTeX items:     {len(latex_item_norm)}')

    # Headings present?
    missing_in_html = []
    missing_in_latex = []
    for h in src_headings:
        hn = normalize_text(h['text'])
        if h['level'] == 1 and h['line'] == 1:
            # The document title H1 is intentionally suppressed in HTML and
            # rendered in the page header instead.
            continue
        m_html = find_match_norm(hn, html_head_norm)
        m_latex = find_match_norm(hn, latex_head_norm)
        if not m_html:
            missing_in_html.append((h['text'], h['line']))
        if not m_latex:
            missing_in_latex.append((h['text'], h['line']))
    if missing_in_html:
        issues.append(f'Missing headings in HTML: {len(missing_in_html)}')
        print('\nMissing headings in HTML:')
        for t, ln in missing_in_html[:50]:
            print(f'  Line {ln}: {t}')
    if missing_in_latex:
        issues.append(f'Missing headings in LaTeX: {len(missing_in_latex)}')
        print('\nMissing headings in LaTeX:')
        for t, ln in missing_in_latex[:50]:
            print(f'  Line {ln}: {t}')

    # Items present?
    missing_items_in_html = []
    missing_items_in_latex = []
    for it in src_items:
        n = normalize_text(it['text'])
        m_html = find_match_norm(n, html_item_norm)
        m_latex = find_match_norm(n, latex_item_norm)
        if not m_html:
            missing_items_in_html.append((it['text'], it['line']))
        if not m_latex:
            missing_items_in_latex.append((it['text'], it['line']))
    if missing_items_in_html:
        issues.append(f'Missing items in HTML: {len(missing_items_in_html)}')
        print('\nMissing checklist items in HTML:')
        for t, ln in missing_items_in_html[:100]:
            print(f'  Line {ln}: {t}')
    if missing_items_in_latex:
        issues.append(f'Missing items in LaTeX: {len(missing_items_in_latex)}')
        print('\nMissing checklist items in LaTeX:')
        for t, ln in missing_items_in_latex[:100]:
            print(f'  Line {ln}: {t}')

    # Section color-coding in HTML
    bad_sections = []
    for s in html_sections:
        title = s.get('title') or ''
        cat = s.get('category')
        if not cat:
            bad_sections.append(('missing-data-category', title))
        elif cat not in ALLOWED_CATEGORIES:
            bad_sections.append(('invalid-category', title, cat))
        else:
            inferred = infer_category(title)
            if inferred != cat:
                bad_sections.append(('mismatch-inferred', title, cat, inferred))
    if bad_sections:
        issues.append(f'Section color-coding issues: {len(bad_sections)}')
        print('\nSection color-coding issues:')
        for b in bad_sections[:50]:
            print(' ', b)

    # LaTeX categories present?
    missing_latex_cats = []
    for h in latex_headings:
        n = normalize_text(h['text'])
        if n not in latex_cats:
            missing_latex_cats.append((h['text'], h.get('line')))
    if missing_latex_cats:
        issues.append(f'Missing LaTeX data-category annotations: {len(missing_latex_cats)}')
        print('\nMissing LaTeX data-category annotations:')
        for t, ln in missing_latex_cats[:50]:
            print(f'  Line {ln}: {t}')

    if not issues:
        print('\nValidation PASSED: all checks OK.')
        sys.exit(0)
    else:
        print('\nValidation FAILED:')
        for it in issues:
            print(' -', it)
        sys.exit(2)

if __name__ == '__main__':
    main()
