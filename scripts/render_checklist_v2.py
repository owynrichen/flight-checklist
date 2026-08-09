#!/usr/bin/env python3
"""
Render checklist from Markdown into HTML kneeboard template.

Improvements over previous version:
  - Hierarchical nesting: H2 sections wrap their H3 subsections.
  - Category inheritance: H3 inherits its H2 category for color discipline.
  - H1 as page-divider band (not a card); first H1 is suppressed (used in <header>).
  - Note/sub-header lines (✅ italic 'Goal:', ⛔ 'IMMEDIATE ACTIONS') render as
    .note / .subheader spans without checkboxes.
  - Markdown tables passed through pandoc and inserted inline.
  - Empty sections (no items, no children, no table) suppressed.
  - Refined category heuristics for forced landing / alternator / electrical.
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
MD_PATH = os.path.join(ROOT, 'Combined_VFR_IFR_Ch1.md')

ICON_MAP = {
    '✅': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><path fill='currentColor' d='M6.173 11.414 2.76 8l-1.06 1.06L6.173 13.53l9.127-9.127L14.24 3.47z'/></svg>", 'OK'),
    '🟩': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><rect width='16' height='16' fill='currentColor'/></svg>", 'Normal'),
    '🟥': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><rect width='16' height='16' fill='currentColor'/></svg>", 'Emergency'),
    '🚨': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='6' fill='currentColor'/></svg>", 'Alert'),
    '🔵': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='6' stroke='currentColor' fill='none'/></svg>", 'IFR'),
    '⛔': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><path fill='currentColor' d='M8 1.2 15 13H1L8 1.2z'/></svg>", 'Immediate'),
    '☑': ("<svg viewBox='0 0 16 16' width='12' height='12' xmlns='http://www.w3.org/2000/svg'><path fill='currentColor' d='M6.173 11.414 2.76 8l-1.06 1.06L6.173 13.53l9.127-9.127L14.24 3.47z'/></svg>", 'Verified'),
}

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


def is_plain_item_line(text):
    return bool(re.match(r'^[A-Za-z0-9(*\[]', text))


PAGE2_START_TITLES = (
    'clear runway',
    'shutdown',
    'critical memory items',
    'preflight',
    'safety checklist',
    'engine start',
    'ground check',
    'run up',
    'engine failure in flight',
    'engine restart in flight po h',
    'forced landing',
    'engine fire in flight',
    'electrical fire smoke po h aligned',
    'alternator failure no charge',
    'ifr acronyms mnemonics',
)


def normalize_text(s):
    return ' '.join(re.findall(r'\w+', (s or '').lower()))


def is_title_heading(text):
    norm = normalize_text(text)
    return 'flow verify checklist' in norm


def page_for_heading(title):
    norm = normalize_text(title)
    if any(k in norm for k in (
        'takeoff',
        'ifr departure enroute',
        'ifr approach configuration',
        'ifr performance profiles',
        'v speeds',
        'landing go around',
        'clear runway',
        'shutdown',
        'missed approach',
        'critical memory items',
    )):
        return 1
    if any(k in norm for k in (
        'preflight',
        'safety checklist',
        'engine start',
        'ground check',
        'run up',
    )):
        return 2
    if any(k in norm for k in (
        'ifr acronyms mnemonics',
        'engine failure in flight',
        'engine restart in flight',
        'forced landing',
        'engine fire in flight',
        'electrical fire smoke',
        'alternator failure no charge',
    )):
        return 3
    return 2


def replace_icons(text):
    for k, (svg, desc) in ICON_MAP.items():
        if k in text:
            icon_html = f"<span class=\"icon\" aria-hidden=\"true\">{svg}</span><span class=\"sr-only\">{html.escape(desc)}</span>"
            text = text.replace(k, icon_html)
    return text


def md_to_html(md):
    try:
        p = subprocess.run(['pandoc', '-f', 'gfm', '-t', 'html'], input=md, text=True, capture_output=True, check=True)
        out = p.stdout.strip()
        if out.startswith('<p>') and out.endswith('</p>'):
            out = out[3:-4]
        return out
    except Exception:
        return html.escape(md)


def infer_category(title):
    t = (title or '').lower()
    if 'missed approach' in t:
        return 'green'
    # Emergency keywords (broadened)
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


# --- Markdown parser ---------------------------------------------------------

def parse_markdown(md_path):
    """Tokenize the markdown into headings, items, notes, sub-headers, and table blocks."""
    tokens = []
    with open(md_path, encoding='utf-8') as f:
        lines = f.readlines()
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i].rstrip('\n')
        s = raw.strip()
        if not s:
            i += 1
            continue
        # Heading
        m = re.match(r'^(#+)\s*(.*)$', s)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if text:
                tokens.append({'type': 'heading', 'level': level, 'text': text, 'line': i + 1})
            i += 1
            continue
        # Markdown table: line that starts with | and the next line is a separator |---|
        if s.startswith('|') and i + 1 < n and re.match(r'^\s*\|?\s*:?-{2,}', lines[i + 1]):
            block = []
            while i < n and lines[i].strip().startswith('|'):
                block.append(lines[i].rstrip('\n'))
                i += 1
            tokens.append({'type': 'table', 'text': '\n'.join(block), 'line': i})
            continue
        # ✅ italic note: "✅ *Goal: Stabilized by FAF*"
        if s.startswith('✅') and re.search(r'\*[^*]+\*', s) and not s.startswith('✅ ☐'):
            txt = s.lstrip('✅').strip()
            tokens.append({'type': 'note', 'text': txt, 'line': i + 1})
            i += 1
            continue
        if re.fullmatch(r'\*\([^*]+\)\*', s):
            tokens.append({'type': 'note', 'text': s, 'line': i + 1})
            i += 1
            continue
        # ⛔ bold sub-header: ONLY when the entire content after ⛔ is wrapped in **...**
        # e.g. "⛔ **IMMEDIATE ACTIONS**". Other ⛔ lines are critical checklist items.
        if s.startswith('⛔'):
            rest = s.lstrip('⛔').strip()
            if re.fullmatch(r'\*\*[^*]+\*\*', rest):
                tokens.append({'type': 'subheader', 'text': rest, 'line': i + 1})
                i += 1
                continue
            # else fall through to item detection (with critical flag)
            tokens.append({'type': 'item', 'text': rest, 'line': i + 1, 'critical': True})
            i += 1
            continue
        # ➡ consequence / follow-through action (rendered as non-checkbox note styled
        # to look like an indented "then-do-this" step, e.g. "➡ Master OFF → Land ASAP").
        if s.startswith('➡'):
            rest = s.lstrip('➡').strip()
            tokens.append({'type': 'consequence', 'text': rest, 'line': i + 1})
            i += 1
            continue
        # Checklist items: list markers or leading checkbox glyph
        if re.match(r'^[-*+]\s+', s) or s.startswith(tuple(LEADING_MARKERS)):
            tokens.append({'type': 'item', 'text': strip_item_prefix(s), 'line': i + 1})
            i += 1
            continue
        if is_plain_item_line(s):
            tokens.append({'type': 'item', 'text': s.strip(), 'line': i + 1})
            i += 1
            continue
        i += 1
    return tokens


# --- HTML construction -------------------------------------------------------

def build_item_li(text, critical=False):
    item_html = md_to_html(text)
    item_html = replace_icons(item_html)
    cls = " class='critical'" if critical else ''
    return (f"        <li{cls}><span class='box' role='checkbox' aria-checked='false' "
            f"tabindex='0' aria-label='Checklist checkbox'></span> {item_html}</li>")


def build_note(text):
    return f"      <p class='note'>{replace_icons(md_to_html(text))}</p>"


def build_subheader(text):
    return f"      <p class='subheader'>{replace_icons(md_to_html(text))}</p>"


def build_consequence(text):
    inner = replace_icons(md_to_html(text))
    return f"      <p class='consequence'><span class='arrow' aria-hidden='true'>➡</span> {inner}</p>"


def build_table(md_table):
    return md_to_html(md_table)


def render_h2_block(h2, children_tokens):
    """children_tokens: tokens until the next H1/H2 (items, notes, subheaders, h3 groups, tables)."""
    cat = infer_category(h2['text'])
    title_html = replace_icons(html.escape(h2['text']).replace('&amp;', '&'))
    parts = [f"  <section class='card' data-category=\"{cat}\">",
             f"    <h2>{title_html}</h2>"]

    # Walk children: collect direct items/notes/tables, then group h3 subsections
    direct = []         # tokens belonging directly to this H2 (before any H3)
    h3_groups = []      # list of {h3, items}
    current_h3 = None
    for tok in children_tokens:
        if tok['type'] == 'heading' and tok['level'] == 3:
            current_h3 = {'h3': tok, 'items': []}
            h3_groups.append(current_h3)
        else:
            if current_h3 is None:
                direct.append(tok)
            else:
                current_h3['items'].append(tok)

    def render_token_list(toks, indent='      '):
        out = []
        items_buffer = []
        def flush():
            if items_buffer:
                out.append(f"{indent}<ul class='checklist'>")
                out.extend(items_buffer)
                out.append(f"{indent}</ul>")
                items_buffer.clear()
        k = 0
        while k < len(toks):
            t = toks[k]
            if t['type'] == 'item':
                # If a critical ⛔ condition is immediately followed by a ➡ consequence,
                # merge them into a single checklist item so the renderer can't break
                # the pair across pages/columns and the pilot reads "condition → action"
                # as one statement.
                if (t.get('critical') and k + 1 < len(toks)
                        and toks[k + 1]['type'] == 'consequence'):
                    cond = t['text'].rstrip(': ').rstrip()
                    cons = toks[k + 1]['text']
                    cond_html = replace_icons(md_to_html(cond))
                    cons_html = replace_icons(md_to_html(cons))
                    merged = (f"{cond_html} <span class='arrow' aria-hidden='true'>➡</span> "
                              f"<span class='consequence-inline'>{cons_html}</span>")
                    # build_item_li runs md_to_html on text; we've pre-built HTML, so
                    # feed it via a marker that md_to_html will pass through unchanged
                    # — easiest: skip md_to_html by inlining directly.
                    items_buffer.append(
                        "        <li class='critical'>"
                        "<span class='box' role='checkbox' aria-checked='false' "
                        "tabindex='0' aria-label='Checklist checkbox'></span> "
                        f"{merged}</li>"
                    )
                    k += 2
                    continue
                items_buffer.append(build_item_li(t['text'], critical=t.get('critical', False)))
            elif t['type'] == 'note':
                flush()
                out.append(indent + build_note(t['text']).lstrip())
            elif t['type'] == 'subheader':
                flush()
                out.append(indent + build_subheader(t['text']).lstrip())
            elif t['type'] == 'consequence':
                flush()
                out.append(indent + build_consequence(t['text']).lstrip())
            elif t['type'] == 'table':
                flush()
                out.append(indent + build_table(t['text']))
            k += 1
        flush()
        return out

    parts.extend(render_token_list(direct))

    for grp in h3_groups:
        h3 = grp['h3']
        h3_title = replace_icons(html.escape(h3['text']))
        # Inherit parent category for visual consistency
        parts.append(f"    <div class='subsection' data-category=\"{cat}\">")
        parts.append(f"      <h3>{h3_title}</h3>")
        parts.extend(render_token_list(grp['items'], indent='      '))
        parts.append("    </div>")

    # Preserve structural headings even when they don't own checklist lines.
    # This keeps parent section titles like PREFLIGHT visible in the output.
    body = '\n'.join(parts[2:])  # everything after the opening tags + h2
    if not body.strip():
        parts.append("    <ul class='checklist'></ul>")
    parts.append("  </section>")
    return '\n'.join(parts)


def build_html_from_tokens(tokens):
    """Group tokens into H1 dividers + H2 cards (with nested H3 subsections).
    When an 'emergency' H1 is encountered, emit a sentinel that splits the
    output into a second <main> container so a page break can be forced.
    """
    page1 = []
    page2 = []
    page3 = []
    seen_first_h1 = False
    suppress_preamble = True
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok['type'] == 'heading' and tok['level'] == 1:
            if not seen_first_h1:
                seen_first_h1 = True
                i += 1
                continue
            i += 1
            continue
        if tok['type'] == 'heading' and tok['level'] == 2:
            h2 = tok
            if suppress_preamble and is_title_heading(h2['text']):
                i += 1
                continue
            suppress_preamble = False
            j = i + 1
            children = []
            while j < n and not (tokens[j]['type'] == 'heading' and tokens[j]['level'] in (1, 2)):
                children.append(tokens[j])
                j += 1
            block = render_h2_block(h2, children)
            if block:
                page = page_for_heading(h2['text'])
                if page == 1:
                    page1.append(block)
                elif page == 2:
                    page2.append(block)
                else:
                    page3.append(block)
            i = j
            continue
        if tok['type'] in ('item', 'note', 'subheader', 'consequence', 'table'):
            if suppress_preamble:
                i += 1
                continue
            j = i
            children = []
            while j < n and tokens[j]['type'] in ('item', 'note', 'subheader', 'consequence', 'table'):
                children.append(tokens[j])
                j += 1
            block = render_h2_block({'text': 'General', 'level': 2}, children)
            if block:
                page2.append(block)
            i = j
            continue
        i += 1

    page1_html = '\n'.join(page1)
    page2_html = '\n'.join(page2)
    page3_html = '\n'.join(page3)
    return (
        '<div class="page page-1">\n'
        f'{page1_html}\n'
        '</div>\n'
        '<div class="page page-2">\n'
        f'{page2_html}\n'
        '</div>\n'
        '<div class="page page-3 emergency-page">\n'
        '<div class="page-edge" aria-hidden="true"></div>\n'
        f'{page3_html}\n'
        '</div>'
    )


# --- main --------------------------------------------------------------------

def main():
    if not os.path.exists(MD_PATH):
        # fall back to YAML if markdown missing
        if not os.path.exists(YAML_PATH):
            print('No source (markdown or YAML) found.')
            return
        print('Markdown missing, falling back to YAML — limited rendering.')
        with open(YAML_PATH, encoding='utf-8') as f:
            entries = yaml.safe_load(f)
        # synthesize tokens
        tokens = []
        last = None
        for e in entries:
            sec = e.get('section', 'General')
            if sec != last:
                tokens.append({'type': 'heading', 'level': 2, 'text': sec})
                last = sec
            tokens.append({'type': 'item', 'text': e.get('item', '')})
    else:
        print('Rendering HTML from markdown source...')
        tokens = parse_markdown(MD_PATH)

    html_block = build_html_from_tokens(tokens)

    # Title from first H1 of markdown
    title_text = None
    if os.path.exists(MD_PATH):
        with open(MD_PATH, encoding='utf-8') as fm:
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
