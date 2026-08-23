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

    try:
        from playwright.async_api import async_playwright
        report['method'] = 'playwright'
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': page_w_px, 'height': page_h_px})
            await page.goto('file://' + os.path.abspath(html_path))
            await page.add_style_tag(content=override_css)
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

    # Write report
    out_json = 'output/page_fit_report.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Print human summary
    print('Page fit report saved to', out_json)
    for p_r in report['pages']:
        s = f"Page {p_r['index']}: {p_r['height']}px tall (limit {report['page_size_px']['h']}px)"
        if p_r['overflow']:
            print(s + ' -> OVERFLOW')
            # list largest sections contributing
            sorted_secs = sorted(p_r['sections'], key=lambda x: x['height'], reverse=True)
            for sec in sorted_secs[:5]:
                print(f"  - {sec['height']:4d}px  {sec['title'][:80]}")
        else:
            print(s + ' OK')

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
