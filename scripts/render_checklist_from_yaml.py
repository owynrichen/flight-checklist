#!/usr/bin/env python3
"""Render checklist_source.yaml into the HTML template.

Usage: python3 scripts/render_checklist_from_yaml.py
"""
import os
import yaml
import subprocess
import html
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
YAML_PATH = os.path.join(ROOT, 'checklist_source.yaml')
TEMPLATE = os.path.join(ROOT, 'templates', 'html_css', 'us-halfletter', 'checklist.html')
OUT = os.path.join(ROOT, 'output', 'checklist_from_yaml.html')

def load_yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)

def build_html(checklist):
    # Group by section preserving order
    sections = []
    idx = {}
    for entry in checklist:
        sec = entry.get('section', 'General')
        itm = entry.get('item', '')
        if sec not in idx:
            idx[sec] = len(sections)
            sections.append({'section': sec, 'items': []})
        sections[idx[sec]]['items'].append(itm)

    parts = []
    # simple SVG icon map for common symbols
    ICON_MAP = {
        '✅': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><path fill='currentColor' d='M6.173 11.414 2.76 8l-1.06 1.06L6.173 13.53l9.127-9.127L14.24 3.47z'/></svg>", 'OK'),
        '🟩': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><rect width='16' height='16' fill='currentColor'/></svg>", 'Normal'),
        '🚨': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='6' fill='currentColor'/></svg>", 'Alert'),
        '🔵': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='6' stroke='currentColor' fill='none'/></svg>", 'IFR'),
        '🎨': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><rect x='1' y='1' width='14' height='14' fill='none' stroke='currentColor'/></svg>", 'Style'),
        '⛔': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><path fill='currentColor' d='M8 1.2 15 13H1L8 1.2z'/></svg>", 'Immediate'),
        '☑': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><path fill='currentColor' d='M6.173 11.414 2.76 8l-1.06 1.06L6.173 13.53l9.127-9.127L14.24 3.47z'/></svg>", 'Verified')
    }

    def replace_icons(text):
        # replace known emoji with inline svg + sr-only text
        for k, (svg, desc) in ICON_MAP.items():
            if k in text:
                icon_html = f"<span class=\"icon\" aria-hidden=\"true\">{svg}</span><span class=\"sr-only\">{html.escape(desc)}</span>"
                text = text.replace(k, icon_html)
        return text

    def infer_category(title):
        t = title.lower()
        if 'missed approach' in t:
            return 'green'
        # emergency keywords
        if any(k in t for k in ['emerg', 'critical', 'missed', 'engine failure', 'fire', 'immediate', 'memory']):
            return 'emergency'
        # preflight / shutdown
        if any(k in t for k in ['preflight', 'taxi', 'shutdown', 'before takeoff', 'run-up', 'run‑up', 'prefight']):
            return 'grey'
        # in-flight / IFR
        if any(k in t for k in ['flight', 'ifr', 'inflight', 'in‑flight', 'takeoff', 'climb', 'enroute', 'departure', 'approach']):
            return 'blue'
        return 'green'

    def md_to_html(md):
        # convert a small markdown fragment to HTML using pandoc
        try:
            p = subprocess.run(['pandoc', '-f', 'gfm', '-t', 'html'], input=md, text=True, capture_output=True, check=True)
            out = p.stdout.strip()
            # strip enclosing <p> if present
            if out.startswith('<p>') and out.endswith('</p>'):
                out = out[3:-4]
            return out
        except Exception:
            return html.escape(md)

    for s in sections:
        raw_title = s['section']
        sec_title = replace_icons(raw_title)
        category = infer_category(raw_title)
        parts.append(f"  <section data-category=\"{category}\">\n    <h2>{sec_title}</h2>\n    <ul class='checklist'>")
        for it in s['items']:
            item_html = md_to_html(it)
            item_html = replace_icons(item_html)
            parts.append(f"      <li><span class='box' role='checkbox' aria-checked='false' tabindex='0' aria-label='Checklist checkbox'></span> {item_html}</li>")
        parts.append('    </ul>\n  </section>')
    return '\n'.join(parts)

def load_markdown_entries(md_path):
    """Parse a simple flat markdown checklist into a list of {section, item} entries.
    Heuristic: headings (#, ##, ###) start new sections; list lines (-, +, *, or leading emoji macro) are items.
    """
    entries = []
    current_section = 'General'
    with open(md_path, encoding='utf-8') as f:
        for line in f:
            raw = line.rstrip('\n')
            if not raw.strip():
                continue
            if raw.lstrip().startswith('#'):
                m = re.match(r'^(#+)\s*(.*)$', raw.lstrip())
                if m:
                    current_section = m.group(2).strip()
                continue
            if re.match(r'^\s*[-*+]\s+', raw) or '\\emoji{' in raw or raw.strip().startswith(tuple('☐☑✅⛔✔')):
                t = strip_item_prefix(raw)
                # unwrap \emoji{...} -> the inner glyph if present
                t = re.sub(r'\\emoji\{(.*?)\}', r'\1', t)
                entries.append({'section': current_section, 'item': t.strip()})
    return entries


def main():
    # Prefer YAML if explicitly intended, otherwise fall back to parsing the canonical markdown
    checklist = None
    if os.path.exists(YAML_PATH):
        checklist = load_yaml(YAML_PATH)
    else:
        md_path = os.path.join(ROOT, 'Combined_VFR_IFR_Ch1.md')
        if os.path.exists(md_path):
            print('No YAML found — parsing markdown source for checklist entries...')
            checklist = load_markdown_entries(md_path)
        else:
            print('Missing both', YAML_PATH, 'and Combined_VFR_IFR_Ch1.md')
            return

    html_block = build_html(checklist)

    # try to read the markdown source title (first H1) to use as page header
    title_text = None
    md_path = os.path.join(ROOT, 'Combined_VFR_IFR_Ch1.md')
    if os.path.exists(md_path):
        with open(md_path, encoding='utf-8') as fm:
            for line in fm:
                if line.startswith('#'):
                    # use the first H1 as the page title
                    title_text = line.lstrip('#').strip()
                    break

    with open(TEMPLATE, encoding='utf-8') as ft, open(OUT, 'w', encoding='utf-8') as fo:
        tpl = ft.read()
        if title_text:
            tpl = tpl.replace('<h1>CHECKLIST</h1>', f'<h1>{html.escape(title_text)}</h1>')
        # legend inserted for visual color mapping
        legend_html = '''\n      <div class="legend" aria-hidden="true">\n        <span class="legend-item" data-category="emergency"><span class="legend-dot"></span> Emergency</span>\n        <span class="legend-item" data-category="grey"><span class="legend-dot"></span> Preflight / Shutdown</span>\n        <span class="legend-item" data-category="blue"><span class="legend-dot"></span> In‑flight</span>\n        <span class="legend-item" data-category="green"><span class="legend-dot"></span> Other</span>\n      </div>\n    '''
        tpl = tpl.replace('</header>', legend_html + '\n</header>')
        tpl = tpl.replace('<!-- Replace with generated HTML from checklist_source.yaml -->', html_block)
        fo.write(tpl)

    print('Wrote', OUT)

if __name__ == '__main__':
    main()
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
