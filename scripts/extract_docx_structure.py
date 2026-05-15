#!/usr/bin/env python3
"""
Extract structure from a .docx and produce Markdown and a YAML checklist source.

This version uses `pandoc` to convert DOCX to Markdown and `unzip` to extract images,
avoiding the need for `python-docx` so the script can run in minimal environments.

Usage:
  python3 scripts/extract_docx_structure.py /path/to/Combined VFR and IFR Flight Ch 1.docx

Outputs (in the repository root):
  - Combined_VFR_IFR_Ch1.md    (markdown of document)
  - docx_images/               (extracted images from word/media)
  - checklist_source.yaml      (YAML list of sections and items)

Dependencies: pandoc, unzip
"""
import sys
import os
import re
import subprocess
import yaml

LIST_PREFIX_RE = re.compile(r'^\s*([-*+]|\d+\.)\s+')

# common checkbox / marker glyphs we encounter in DOCX -> markdown conversions
CHECKBOX_GLYPHS = '\u2610\u2611\u2714\u2705\u26d4\u26a0\u26a1\u274c\u2705'
CHECKBOX_RE = re.compile(rf"^\s*[{CHECKBOX_GLYPHS}]\s+")


def extract_images(docx_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    # Use unzip to extract word/media
    try:
        subprocess.run(['unzip', '-o', docx_path, 'word/media/*', '-d', out_dir], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        # try fallback: use zipfile as last resort
        import zipfile
        with zipfile.ZipFile(docx_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('word/media/'):
                    z.extract(name, out_dir)
        # move files up if necessary
        media_dir = os.path.join(out_dir, 'word', 'media')
        if os.path.isdir(media_dir):
            for fname in os.listdir(media_dir):
                src = os.path.join(media_dir, fname)
                dst = os.path.join(out_dir, fname)
                if not os.path.exists(dst):
                    os.replace(src, dst)
            import shutil
            shutil.rmtree(os.path.join(out_dir, 'word'), ignore_errors=True)


def docx_to_markdown(docx_path, md_out):
    # Call pandoc to convert docx -> markdown (gfm)
    from shutil import which
    if which('pandoc') is None:
        print('Error: `pandoc` not found in PATH. Please install pandoc to continue.')
        print('  Visit https://pandoc.org/installing.html or use your package manager (e.g., apt, brew).')
        sys.exit(2)
    subprocess.run(['pandoc', docx_path, '-t', 'gfm', '-o', md_out], check=True)


def parse_markdown_for_checklist(md_path):
    checklist = []
    current_section = 'General'
    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.rstrip('\n')
            if not s.strip():
                continue
            # Heading
            if s.startswith('#'):
                # strip leading hashes and whitespace
                sec = s.lstrip('#').strip()
                if sec:
                    current_section = sec
                continue
            # list item if it uses a standard list prefix (-, *, +, 1.)
            if LIST_PREFIX_RE.match(s):
                # remove prefix
                item = LIST_PREFIX_RE.sub('', s).strip()
                # strip leading checkbox glyphs that remain (e.g. "☐ Fuel ...")
                item = re.sub(rf'^[{CHECKBOX_GLYPHS}]\s*', '', item)
                # remove trailing checkbox markers like [ ] or [x]
                item = re.sub(r'^\[.\]\s*', '', item)
                checklist.append({'section': current_section, 'item': item})
                continue

            # some documents render checklist lines without a list prefix,
            # starting the line directly with a checkbox glyph like "☐ Fuel..."
            if CHECKBOX_RE.match(s):
                item = CHECKBOX_RE.sub('', s).strip()
                checklist.append({'section': current_section, 'item': item})
                continue
            # table rows not treated as checklist
    return checklist


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/extract_docx_structure.py /path/to/doc.docx')
        sys.exit(1)
    docx_path = sys.argv[1]
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    base_out_md = os.path.join(repo_root, 'Combined_VFR_IFR_Ch1.md')
    images_out = os.path.join(repo_root, 'docx_images')

    print('Converting DOCX to Markdown with pandoc...')
    try:
        docx_to_markdown(docx_path, base_out_md)
    except subprocess.CalledProcessError as e:
        print('Error: pandoc conversion failed:', e)
        sys.exit(1)

    print('Extracting images...')
    try:
        extract_images(docx_path, images_out)
    except Exception as e:
        print('Image extraction warning:', e)

    print('Parsing markdown to generate checklist items...')
    checklist = parse_markdown_for_checklist(base_out_md)

    out_yaml = os.path.join(repo_root, 'checklist_source.yaml')
    with open(out_yaml, 'w', encoding='utf-8') as f:
        yaml.safe_dump(checklist, f, sort_keys=False, allow_unicode=True)

    print(f'Wrote {base_out_md}, extracted images to {images_out}, wrote {out_yaml} with {len(checklist)} items')


if __name__ == '__main__':
    main()
