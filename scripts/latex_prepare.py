#!/usr/bin/env python3
r"""Preprocess Combined_VFR_IFR_Ch1.md for LaTeX:
- wrap emoji characters with \emoji{...} so fontspec can use an emoji-capable font
- insert raw LaTeX comment markers before headings with inferred data-category
  so the generated LaTeX can be validated for semantic color mapping

This script is intentionally conservative: it only adds lightweight raw LaTeX
comment blocks (```{=latex} % data-category: ... ```), which pandoc preserves
into the generated .tex. These comments are easy for validators/CI to parse.
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IN = os.path.join(ROOT, 'Combined_VFR_IFR_Ch1.md')
OUT = os.path.join(ROOT, 'Combined_VFR_IFR_Ch1_latex.md')

# List of emoji characters to wrap in \emoji{...}
EMOJI_CHARS = [
    '✅','🟩','🧭','▶','☐','🔍','🛫','🔵','✈','🎯','📘','🚨','🛬','🔥','⚡',
    '⚠️','🟥','🔁','🔄','☑','🟫','🔵','✈️','🔍','⛔','✔'
]


def wrap_emojis(text: str) -> str:
    for e in EMOJI_CHARS:
        if e in text:
            text = text.replace(e, f"\\emoji{{{e}}}")
    return text


def infer_category(title: str) -> str:
    """Heuristic to map a heading/title to one of: emergency, grey, blue, green
    Matches the same intent used by the HTML renderer so outputs stay consistent.
    """
    t = title.lower()
    if any(k in t for k in ['emerg', 'critical', 'missed', 'engine failure', 'fire', 'immediate', 'memory']):
        return 'emergency'
    if any(k in t for k in ['preflight', 'taxi', 'shutdown', 'before takeoff', 'run-up', 'run‑up', 'prefight']):
        return 'grey'
    if any(k in t for k in ['flight', 'ifr', 'inflight', 'in‑flight', 'takeoff', 'climb', 'enroute', 'departure', 'approach', 'landing']):
        return 'blue'
    return 'green'


def insert_category_comments(md: str) -> str:
    """Insert raw LaTeX comment blocks before markdown headings.

    Example insertion before a heading `## 🚨 MISSED APPROACH`:

    ```{=latex}
    % data-category: emergency
    ```
    ## \emoji{🚨} MISSED APPROACH
    """
    out_lines = []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            # extract heading text without leading #'s and trailing attributes
            heading = stripped.lstrip('#').strip()
            category = infer_category(heading)
            out_lines.append('```{=latex}')
            out_lines.append(f'% data-category: {category}')
            out_lines.append('```')
            out_lines.append(line)
        else:
            out_lines.append(line)
    return '\n'.join(out_lines) + '\n'


def main():
    if not os.path.exists(IN):
        print('Input markdown not found:', IN)
        return
    with open(IN, encoding='utf-8') as f:
        content = f.read()

    # Wrap emoji glyphs for LaTeX
    content = wrap_emojis(content)

    # Insert raw LaTeX comment markers so LaTeX source is semantically annoted
    content = insert_category_comments(content)

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Wrote', OUT)


if __name__ == '__main__':
    main()
