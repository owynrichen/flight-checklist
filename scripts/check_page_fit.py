#!/usr/bin/env python3
"""
Measure printed page fit for each <main class="columns"> using Playwright.

Outputs a JSON report and a human-readable summary listing pages that
overflow the CSS @page height and candidate H2/H3 split locations.

Usage: python3 scripts/check_page_fit.py [--html output/checklist_print_ready.html]

This script assumes Playwright is installed and browsers are available.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import asyncio
import re
import shutil
import subprocess
import tempfile


DEFAULT_HTML = 'output/checklist_print_ready.html'


async def run(html_path: str, page_size: str = 'half', columns: int = 2):
    # Page size mapping in inches
    sizes = {
        'half': (5.5, 8.5),
        'letter': (8.5, 11.0),
    }
    if page_size not in sizes:
        raise ValueError('unknown page_size')

    DPI = 96
    page_w_in, page_h_in = sizes[page_size]
    page_w_px = int(page_w_in * DPI)
    page_h_px = int(page_h_in * DPI)

    report = {'pages': [], 'page_size': page_size, 'columns': columns, 'page_size_px': {'w': page_w_px, 'h': page_h_px}, 'method': None}

    # CSS override to set page size and columns
    override_css = f"""
      @page {{ size: {page_w_in}in {page_h_in}in; margin: 0.5in; }}
      main.columns {{ column-count: {columns}; column-gap: 12px; }}
      section.card {{ break-inside: avoid; -webkit-column-break-inside: avoid; }}
    """

    # Use the same renderer as build.sh to produce an HTML proof that includes
    # the same inline overrides. This prevents us from duplicating CSS logic
    # here and keeps the measurement faithful to the rendered outputs.
    try:
        from playwright.async_api import async_playwright
        report['method'] = 'playwright'
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': page_w_px, 'height': page_h_px})

            # Run the renderer to produce output/checklist_from_yaml.html which the
            # build script normally moves; renderer accepts --columns and --page-size
            renderer = os.path.join(os.path.dirname(__file__), 'render_checklist_v2.py')
            cmd = ['python3', renderer, '--columns', str(columns), '--page-size', page_size]
            if shutil.which('uv'):
                cmd = ['uv', 'run'] + cmd
            subprocess.run(cmd, check=True)

            # Prefer the build-style named output if present, else fall back to the
            # renderer's default output file
            candidate = os.path.join(os.path.dirname(__file__), '..', 'output', f'checklist_print_ready_{page_size}_{columns}c.html')
            if os.path.exists(candidate):
                html_path_to_load = candidate
            else:
                renderer_out = os.path.join(os.path.dirname(__file__), '..', 'output', 'checklist_from_yaml.html')
                if os.path.exists(renderer_out):
                    # copy to temp file to avoid concurrent edits
                    tmpf = tempfile.NamedTemporaryFile(prefix='check_page_fit_', suffix='.html', delete=False)
                    tmpf.close()
                    shutil.copy(renderer_out, tmpf.name)
                    html_path_to_load = tmpf.name
                else:
                    html_path_to_load = html_path

            await page.goto('file://' + os.path.abspath(html_path_to_load))
            # Ensure print media rules are applied so measurements match PDF output
            await page.emulate_media(media='print')
            await page.wait_for_timeout(300)

            mains = await page.query_selector_all('main.columns')
            for idx, m in enumerate(mains, start=1):
                box = await m.bounding_box()
                h = math.ceil(box['height']) if box else 0
                w = math.ceil(box['width']) if box else 0
                overflow = h > page_h_px
                sections = []
                for s_el in await m.query_selector_all('section.card'):
                    sb = await s_el.bounding_box()
                    title_el = await s_el.query_selector('h2')
                    title = await (await title_el.get_property('innerText')).json_value() if title_el else ''
                    sections.append({'title': title.strip(), 'height': math.ceil(sb['height']) if sb else 0})

                report['pages'].append({'index': idx, 'width': w, 'height': h, 'overflow': overflow, 'sections': sections})

            await browser.close()
            # Also capture any top-level <section.card> that are not inside a main.columns
            # These often represent full-width span blocks that become their own PDF pages.
            # We'll open the same page again (fresh) to measure them outside the main loop.
            # Create a second browser instance properly (async API) to measure
            browser2 = await p.chromium.launch()
            try:
                page2 = await browser2.new_page(viewport={'width': page_w_px, 'height': page_h_px})
                await page2.goto('file://' + os.path.abspath(html_path_to_load))
                await page2.emulate_media(media='print')
                await page2.wait_for_timeout(200)
                # find all section.card elements and pick those not contained in a main.columns
                extra_sections = []
                all_sections = await page2.query_selector_all('section.card')
                for s in all_sections:
                    # determine if this section has a main.columns ancestor
                    has_main = await s.evaluate('el => !!el.closest("main.columns")')
                    if not has_main:
                        sb = await s.bounding_box()
                        title_el = await s.query_selector('h2')
                        title = await (await title_el.get_property('innerText')).json_value() if title_el else ''
                        extra_sections.append({'title': title.strip(), 'height': math.ceil(sb['height']) if sb else 0})
                # append each extra section as its own "page" in the report
                for ex in extra_sections:
                    report['pages'].append({'index': len(report['pages']) + 1, 'width': page_w_px, 'height': ex['height'], 'overflow': ex['height'] > page_h_px, 'sections': [ex]})

                # Render an actual PDF of the page and count pages by scanning for PDF page markers
                out_pdf = os.path.join(os.path.dirname(__file__), '..', 'output', f'check_page_fit_render_{page_size}_{columns}.pdf')
                # produce a PDF using the same options as the build script
                try:
                    await page2.pdf(path=out_pdf, print_background=True, prefer_css_page_size=True, margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"})
                except TypeError:
                    # older playwright versions may not accept prefer_css_page_size; fallback
                    await page2.pdf(path=out_pdf, print_background=True)
                with open(out_pdf, 'rb') as pf:
                    pdf_bytes = pf.read()
                # crude page count: count occurrences of '/Type /Page'
                pdf_page_count = pdf_bytes.count(b'/Type /Page')
                report['pdf_page_count'] = pdf_page_count

                # Map section positions to PDF pages using document coordinates so the
                # report matches how the PDF was paginated. Use offsetTop walk to get
                # absolute top in document layout, then divide by page pixel height.
                page_sections = await page2.evaluate(f'''
                () => {{
                    const page_h = {page_h_px};
                    function absTop(el) {{
                        let t = 0;
                        let e = el;
                        while (e) {{ t += e.offsetTop || 0; e = e.offsetParent; }}
                        return t;
                    }}
                    const out = [];
                    document.querySelectorAll('section.card').forEach(s => {{
                        let h2 = s.querySelector('h2');
                        let title = h2 ? h2.innerText.trim() : '(no title)';
                        let top = absTop(s);
                        let h = s.offsetHeight || s.getBoundingClientRect().height || 0;
                        let page_index = Math.floor(top / page_h) + 1;
                        out.push({{title, top, height: Math.ceil(h), page: page_index}});
                    }});
                    return out;
                }}
                ''')
                report['pdf_section_map'] = page_sections
            finally:
                await browser2.close()
    except Exception as e:
        report['method'] = f'fallback-estimator ({type(e).__name__})'
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        mains_raw = []
        for m in re.finditer(r'<main[^>]*class=["\']?[^"\']*columns[^"\']*["\']?[^>]*>(.*?)</main>', html, flags=re.S|re.I):
            mains_raw.append(m.group(1))
        if not mains_raw:
            print('No <main class="columns"> containers found in HTML')
            return 2
        for idx, m_html in enumerate(mains_raw, start=1):
            h2_titles = [t.strip() for t in re.findall(r'<h2[^>]*>(.*?)</h2>', m_html, flags=re.S|re.I)]
            li_count = len(re.findall(r'<li\b', m_html, flags=re.I))
            p_count = len(re.findall(r'<p\b', m_html, flags=re.I))
            table_rows = len(re.findall(r'<tr\b', m_html, flags=re.I))
            header_h = 28
            li_h = 18
            p_h = 20
            tr_h = 18
            est_height = header_h + li_count * li_h + p_count * p_h + table_rows * tr_h
            overflow = est_height > page_h_px
            sec_list = []
            if h2_titles:
                share = max(1, math.ceil(est_height / len(h2_titles)))
                for t in h2_titles:
                    sec_list.append({'title': re.sub(r'<[^>]+>', '', t).strip(), 'height': share})
            else:
                sec_list = [{'title': '(no h2)', 'height': est_height}]
            report['pages'].append({'index': idx, 'width': page_w_px, 'height': est_height, 'overflow': overflow, 'sections': sec_list})

    # Write report files with layout-specific names so reviewers can inspect them
    out_dir = 'output'
    os.makedirs(out_dir, exist_ok=True)
    out_json = os.path.join(out_dir, f'page_fit_report_{report["page_size"]}_{report["columns"]}.json')
    out_txt = os.path.join(out_dir, f'page_fit_report_{report["page_size"]}_{report["columns"]}.txt')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # human summary text
    lines = [f'Page fit report for page_size={report["page_size"]} columns={report["columns"]}']
    for p_r in report['pages']:
        s = f"Page {p_r['index']}: {p_r['height']}px tall (limit {report['page_size_px']['h']}px)"
        if p_r['overflow']:
            lines.append(s + ' -> OVERFLOW')
            sorted_secs = sorted(p_r['sections'], key=lambda x: x['height'], reverse=True)
            for sec in sorted_secs[:10]:
                lines.append(f"  - {sec['height']:4d}px  {sec['title'][:200]}")
        else:
            lines.append(s + ' OK')

    # PDF diagnostics if available
    if 'pdf_page_count' in report:
        lines.append(f"\nPDF page count (rendered): {report['pdf_page_count']}")
        # Compare PDF page count to measured HTML pages
        measured_pages = len(report['pages'])
        if report['pdf_page_count'] != measured_pages:
            lines.append(f"WARNING: PDF page count ({report['pdf_page_count']}) != measured HTML page containers ({measured_pages})")
        # If we mapped sections to PDF pages, show a concise mapping and flag sections landing on later pages
        if 'pdf_section_map' in report:
            lines.append('\nSection -> PDF page mapping:')
            for s in report['pdf_section_map']:
                lines.append(f"  Page {s['page']:2d}: {s['title'][:60]:60s}  (top={s['top']} h={s['height']})")
            # Find sections that end up on a PDF page beyond the last measured page
            overflow_sections = [s for s in report['pdf_section_map'] if s['page'] > measured_pages]
            if overflow_sections:
                lines.append('\nSections placed on PDF pages beyond measured HTML containers:')
                for s in overflow_sections:
                    lines.append(f"  - {s['title'][:120]} -> PDF page {s['page']}")
    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('Page fit report saved to', out_json)
    print('Summary saved to', out_txt)
    for l in lines:
        print(l)

    # Return non-zero if any overflow detected or PDF page count mismatches measured pages
    any_overflow = any(p.get('overflow') for p in report['pages'])
    mismatch = ('pdf_page_count' in report) and (report['pdf_page_count'] != len(report['pages']))
    if any_overflow or mismatch:
        return 2
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', default=DEFAULT_HTML)
    parser.add_argument('--page-size', default='half', choices=['half', 'letter'])
    parser.add_argument('--columns', default=2, type=int, choices=[2,3,4])
    args = parser.parse_args()
    code = asyncio.run(run(args.html, page_size=args.page_size, columns=args.columns))
    sys.exit(code)


if __name__ == '__main__':
    main()
