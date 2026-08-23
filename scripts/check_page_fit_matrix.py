#!/usr/bin/env python3
"""
Run check_page_fit across a matrix of page sizes and column counts.

Produces output/page_fit_matrix.json and a human-readable summary at
output/page_fit_matrix.txt
"""
from __future__ import annotations

import asyncio
import json
import os
from subprocess import run, PIPE

HTML = 'output/checklist_print_ready.html'
OUT_JSON = 'output/page_fit_matrix.json'
OUT_TXT = 'output/page_fit_matrix.txt'

async def run_matrix():
    combos = []
    for page in ('half', 'letter'):
        for cols in (2,3,4):
            combos.append((page, cols))

    results = []
    for page, cols in combos:
        print(f'Running: page={page} cols={cols}')
        p = run(['uv', 'run', 'python3', 'scripts/check_page_fit.py', '--html', HTML, '--page-size', page, '--columns', str(cols)], stdout=PIPE, stderr=PIPE, text=True)
        out = p.stdout
        err = p.stderr
        # load the JSON report written by the script
        rpt_path = f'output/page_fit_report_{page}_{cols}.json'
        rpt = None
        if os.path.exists(rpt_path):
            with open(rpt_path, 'r', encoding='utf-8') as f:
                rpt = json.load(f)
        results.append({'page': page, 'columns': cols, 'rc': p.returncode, 'stdout': out, 'stderr': err, 'report': rpt})

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    # human summary
    lines = []
    for r in results:
        lines.append(f"page={r['page']} cols={r['columns']} rc={r['rc']}")
        if r['report']:
            for p_r in r['report'].get('pages', []):
                lines.append(f"  Page {p_r['index']}: height={p_r['height']} overflow={p_r['overflow']}")
    with open(OUT_TXT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('Wrote', OUT_JSON, 'and', OUT_TXT)


if __name__ == '__main__':
    asyncio.run(run_matrix())
