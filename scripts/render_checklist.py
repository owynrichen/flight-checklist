#!/usr/bin/env python3
"""
Render checklist from Markdown or YAML into the HTML template with semantic sections.
Prefers Combined_VFR_IFR_Ch1.md when present (user-selected). Falls back to checklist_source.yaml.

Produces: output/checklist_from_yaml.html (same target used by previous script)
"""
import os
import re
import yaml
import subprocess
import html

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
YAML_PATH = os.path.join(ROOT, 'checklist_source.yaml')
TEMPLATE = os.path.join(ROOT, 'templates', 'html_css', 'us-halfletter', 'checklist.html')
OUT = os.path.join(ROOT, 'output', 'checklist_from_yaml.html')

# --- helpers

def load_yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def md_to_html(md):
    try:
        p = subprocess.run(['pandoc', '-f', 'gfm', '-t', 'html'], input=md, text=True, capture_output=True, check=True)
        out = p.stdout.strip()
        if out.startswith('<p>') and out.endswith('</p>'):
            out = out[3:-4]
        return out
    except Exception:
        return html.escape(md)

# Icon map
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
    for k, (svg, desc) in ICON_MAP.items():
        if k in text:
            icon_html = f"<span class=\"icon\" aria-hidden=\"true\">{svg}</span><span class=\"sr-only\">{html.escape(desc)}</span>"
            text = text.replace(k, icon_html)
    return text


def infer_category(title):
    t = (title or '').lower()
    if any(k in t for k in ['emerg', 'critical', 'missed', 'engine failure', 'fire', 'immediate', 'memory']):
        return 'emergency'
    if any(k in t for k in ['preflight', 'taxi', 'shutdown', 'before takeoff', 'run-up', 'run‑up', 'prefight']):
        return 'grey'
    if any(k in t for k in ['flight', 'ifr', 'inflight', 'in‑flight', 'takeoff', 'climb', 'enroute', 'departure', 'approach', 'landing']):
        return 'blue'
    return 'green'

# Parse markdown into ordered token stream of headings and items
def parse_markdown_tokens(md_path):
    tokens = []
    with open(md_path, encoding='utf-8') as f:
        for i, line in enumerate(f, start=1):
            raw = line.rstrip('\n')
            if not raw.strip():
                continue
            if raw.lstrip().startswith('#'):
                m = re.match(r'^(#+)\s*(.*)$', raw.lstrip())
                if m:
                    level = len(m.group(1))
                    title = m.group(2).strip()
                    tokens.append({'type': 'heading', 'level': level, 'text': title, 'line': i})
                continue
            if re.match(r'^\s*[-*+]\s+', raw) or '\\emoji{' in raw or raw.strip().startswith(tuple('☐☑✅⛔✔')):
                t = re.sub(r'^\s*[-*+]\s*', '', raw)
                t = re.sub(r'\\emoji\{(.*?)\}', r'\1', t)
                t = re.sub(r'^[\u2600-\u27BF\u1F300-\u1F6FF]\s*', '', t)
                tokens.append({'type': 'item', 'text': t.strip(), 'line': i})
    return tokens

# Build HTML from token stream (or YAML entries)
def build_html_from_tokens(tokens):
    parts = []
    open_section = False
    for token in tokens:
        if token.get('type') == 'heading':
            if open_section:
                parts.append('    </ul>\n  </section>')
                open_section = False
            raw_title = token.get('text', '')
            sec_title = replace_icons(raw_title)
            category = infer_category(raw_title)
            lvl = token.get('level', 2)
            parts.append(f"  <section data-category=\"{category}\">\n    <h{lvl}>{sec_title}</h{lvl}>\n    <ul class='checklist'>")
            open_section = True
        elif token.get('type') == 'item':
            item_html = md_to_html(token.get('text', ''))
            item_html = replace_icons(item_html)
            parts.append(f"      <li><span class='box' role='checkbox' aria-checked='false' tabindex='0' aria-label='Checklist checkbox'></span> {item_html}</li>")
    if open_section:
        parts.append('    </ul>\n  </section>')
    return '\n'.join(parts)

# YAML -> entries grouping as before
def build_html_from_yaml_entries(entries):
    # group by section preserving order
    sections = []
    idx = {}
    for entry in entries:
        sec = entry.get('section', 'General')
        itm = entry.get('item', '')
        if sec not in idx:
            idx[sec] = len(sections)
            sections.append({'section': sec, 'items': []})
        sections[idx[sec]]['items'].append(itm)

    parts = []
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


def main():
    # Prefer markdown source (user choice), else YAML
    md_path = os.path.join(ROOT, 'Combined_VFR_IFR_Ch1.md')
    html_block = ''
    if os.path.exists(md_path):
        print('Rendering HTML from markdown source...')
        tokens = parse_markdown_tokens(md_path)
        html_block = build_html_from_tokens(tokens)
    elif os.path.exists(YAML_PATH):
        print('Rendering HTML from checklist_source.yaml...')
        entries = load_yaml(YAML_PATH)
        html_block = build_html_from_yaml_entries(entries)
    else:
        print('No source (markdown or YAML) found for rendering.')
        return

    # try to get title from markdown H1 (if present)
    title_text = None
    if os.path.exists(md_path):
        with open(md_path, encoding='utf-8') as fm:
            for line in fm:
                if line.startswith('#'):
                    title_text = line.lstrip('#').strip()
                    break

    with open(TEMPLATE, encoding='utf-8') as ft, open(OUT, 'w', encoding='utf-8') as fo:
        tpl = ft.read()
        if title_text:
            tpl = tpl.replace('<h1>CHECKLIST</h1>', f'<h1>{html.escape(title_text)}</h1>')
        tpl = tpl.replace('<!-- Replace with generated HTML from checklist_source.yaml -->', html_block)
        fo.write(tpl)

    print('Wrote', OUT)

if __name__ == '__main__':
    main()
