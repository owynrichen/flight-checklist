#!/usr/bin/env python3
"""
Validate checklist outputs against source markdown per AGENTS.md.

This script compares the repository Markdown (Combined_VFR_IFR_Ch1.md)
against the rendered HTML (`output/checklist_print_ready.html`). It checks
heading presence, checklist item presence, and that rendered sections carry
the required `data-category` attribute.

Usage:
  python3 scripts/validate_checklist_outputs.py [--source SOURCE_MD] [--html HTML_FILE]

Exit codes:
  0: success
  2: validation failures
  3: missing required files
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import html as htmllib

ALLOWED_CATEGORIES = set(['emergency', 'grey', 'blue', 'green'])

def normalize_text(s: str) -> str:
    if s is None:
        return ''
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('\u2013', '-').replace('\u2014', '-')
    tokens = re.findall(r'\w+', s, flags=re.UNICODE)
    return ' '.join(tokens).lower().strip()

def parse_md(md_path: str):
    headings = []
    items = []
    with open(md_path, encoding='utf-8') as f:
        for i, line in enumerate(f, start=1):
            s = line.rstrip('\n')
            m = re.match(r'^(?P<prefix>\s*#+)\s*(?P<text>.+?)\s*$', s)
            if m:
                text = m.group('text').strip()
                if not text:
                    continue
                level = len(m.group('prefix').strip())
                headings.append({'level': level, 'text': text, 'line': i})
                continue
            if re.match(r'^\s*[-*+]\s+', s) or s.strip().startswith(tuple('☐☑✅⛔✔')):
                t = re.sub(r'^\s*[-*+]\s*', '', s)
                t = re.sub(r'^\s*\[.?\]\s*', '', t)
                t = re.sub(r'\\emoji\{.*?\}\s*', '', t)
                if t.strip():
                    items.append({'text': t.strip(), 'line': i})
            elif re.match(r'^[A-Za-z0-9]', s):
                items.append({'text': s, 'line': i})
    return headings, items

def parse_html(html_path: str):
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    headings = []
    for level in (1,2,3):
        for match in re.finditer(rf'<h{level}[^>]*>(.*?)</h{level}>', html, flags=re.S|re.I):
            inner = re.sub(r'<[^>]+>', '', match.group(1))
            inner = htmllib.unescape(inner).strip()
            headings.append({'level': level, 'text': inner})
    sections = []
    for match in re.finditer(r'<section\b([^>]*)>(.*?)</section>', html, flags=re.S|re.I):
        attrs = match.group(1)
        inner = match.group(2)
        cat_m = re.search(r'data-category=["\']([^"\']+)["\']', attrs)
        category = cat_m.group(1) if cat_m else None
        h_m = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', inner, flags=re.S|re.I)
        title = ''
        if h_m:
            title = re.sub(r'<[^>]+>', '', h_m.group(1)).strip()
        items = []
        for li in re.finditer(r'<li\b[^>]*>(.*?)</li>', inner, flags=re.S|re.I):
            li_text = re.sub(r'<[^>]+>', '', li.group(1))
            li_text = htmllib.unescape(li_text).strip()
            if li_text:
                items.append(li_text)
        sections.append({'title': title, 'category': category, 'items': items})
    all_items = []
    for li in re.finditer(r'<li\b[^>]*>(.*?)</li>', html, flags=re.S|re.I):
        txt = re.sub(r'<[^>]+>', '', li.group(1)).strip()
        if txt:
            all_items.append(htmllib.unescape(txt))
    return headings, sections, all_items

def find_match_norm(norm, norm_list):
    if not norm:
        return None
    if norm in norm_list:
        return norm
    for t in norm_list:
        if norm in t or t in norm:
            return t
    return None

def main():
    parser = argparse.ArgumentParser(description='Validate checklist outputs against source')
    parser.add_argument('--source', default='Combined_VFR_IFR_Ch1.md')
    parser.add_argument('--html', default='output/checklist_print_ready.html')
    args = parser.parse_args()

    missing = [p for p in (args.source, args.html) if not os.path.exists(p)]
    if missing:
        print('Error: missing files:', ', '.join(missing))
        sys.exit(3)

    src_headings, src_items = parse_md(args.source)
    html_headings, html_sections, html_all_items = parse_html(args.html)

    src_head_norm = [normalize_text(h['text']) for h in src_headings]
    src_item_norm = [normalize_text(it['text']) for it in src_items]
    html_head_norm = [normalize_text(h['text']) for h in html_headings]
    html_item_norm = [normalize_text(it) for it in html_all_items]

    issues = []
    print('Validation summary:')
    print(f'  Source headings: {len(src_head_norm)}')
    print(f'  HTML headings:   {len(html_head_norm)}')
    print(f'  Source items:    {len(src_item_norm)}')
    print(f'  HTML items:      {len(html_item_norm)}')

    missing_in_html = []
    for h in src_headings:
        hn = normalize_text(h['text'])
        if h['level'] == 1 and h['line'] == 1:
            continue
        m_html = find_match_norm(hn, html_head_norm)
        if not m_html:
            missing_in_html.append((h['text'], h['line']))
    if missing_in_html:
        issues.append(f'Missing headings in HTML: {len(missing_in_html)}')
        print('\nMissing headings in HTML:')
        for t, ln in missing_in_html[:50]:
            print(f'  Line {ln}: {t}')

    missing_items_in_html = []
    for it in src_items:
        n = normalize_text(it['text'])
        m_html = find_match_norm(n, html_item_norm)
        if not m_html:
            missing_items_in_html.append((it['text'], it['line']))
    if missing_items_in_html:
        issues.append(f'Missing items in HTML: {len(missing_items_in_html)}')
        print('\nMissing checklist items in HTML:')
        for t, ln in missing_items_in_html[:100]:
            print(f'  Line {ln}: {t}')

    bad_sections = []
    for s in html_sections:
        title = s.get('title') or ''
        cat = s.get('category')
        if not cat:
            bad_sections.append(('missing-data-category', title))
        elif cat not in ALLOWED_CATEGORIES:
            bad_sections.append(('invalid-category', title, cat))
    if bad_sections:
        issues.append(f'Section color-coding issues: {len(bad_sections)}')
        print('\nSection color-coding issues:')
        for b in bad_sections[:50]:
            print(' ', b)

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
