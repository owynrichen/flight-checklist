#!/usr/bin/env python3
"""Check whether the local environment can build this repo.

This script uses only the Python standard library so it can run on a minimal
system and report the exact missing pieces needed for setup.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys


def have_command(name: str) -> bool:
    return shutil.which(name) is not None


def have_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def have_module_in_python(python: str, module: str) -> bool:
    result = subprocess.run(
        [python, "-c", f"import importlib.util; print(importlib.util.find_spec('{module}') is not None)"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "True"


def python_version_ok() -> bool:
    return sys.version_info >= (3, 8)


def main() -> int:
    missing = []
    notes = []
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    venv_python = os.path.join(repo_root, ".venv", "bin", "python")
    # The canonical source of truth is the repository Markdown file
    # (Combined_VFR_IFR_Ch1.md). A DOCX can be used to regenerate the
    # Markdown via scripts/extract_docx_structure.py but it is optional.
    source_docx = os.path.join(repo_root, "Combined VFR and IFR Flight Ch 1.docx")

    print("Environment check")
    print(f"  Python: {sys.version.split()[0]}")

    if os.path.exists(source_docx):
        print("  source docx: available (optional)")
    else:
        print("  source docx: not present (optional)")

    if not python_version_ok():
        missing.append("python3.8+")

    for cmd in ["pandoc", "unzip"]:
        if have_command(cmd):
            print(f"  {cmd}: ok")
        else:
            print(f"  {cmd}: missing")
            missing.append(cmd)

    # We no longer rely on weasyprint/wkhtmltopdf — Playwright (Chromium) is the
    # supported PDF renderer. Report their presence only as informational.
    if have_command("weasyprint"):
        print("  weasyprint: available (not required)")
    if have_command("wkhtmltopdf"):
        print("  wkhtmltopdf: available (legacy, not recommended)")

    # YAML and playwright are required for rendering and PDF generation.
    for mod in ["yaml", "playwright"]:
        if have_module(mod):
            print(f"  python module {mod}: ok")
        else:
            print(f"  python module {mod}: missing")
            missing.append(f"python module {mod}")

    # check for uv manager globally
    if have_command('uv'):
        print('  uv: ok (global environment manager)')
    else:
        print('  uv: missing (optional)')

    # python-docx is optional; extraction uses pandoc + unzip. If you prefer
    # python-docx extraction, install it into your project environment.
    if os.path.exists(venv_python) and have_module_in_python(venv_python, "docx"):
        print("  python module docx (.venv): ok (optional)")
    elif have_module("docx"):
        print("  python module docx: ok (optional)")
    else:
        print("  python module docx: not installed (optional)")

    # Playwright is required for high-fidelity PDF rendering using Chromium.
    if os.path.exists(venv_python) and have_module_in_python(venv_python, "playwright"):
        print("  python module playwright (.venv): ok")
    elif have_module("playwright"):
        print("  python module playwright: ok")
    else:
        print("  python module playwright: missing")
        # already added to 'missing' above

    if subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True).returncode == 0:
        print("  pip: ok")
    else:
        print("  pip: missing")
        notes.append("install python3-pip so the requirements file can be installed")

    if have_module("venv"):
        print("  venv module: ok")
    else:
        print("  venv module: missing")
        notes.append("install python3-venv to create a virtual environment")

    if have_module("ensurepip"):
        print("  ensurepip module: ok")
    else:
        print("  ensurepip module: missing")
        notes.append("install python3-venv so venv can bootstrap pip")

    if missing:
        print("\nMissing prerequisites:")
        for item in missing:
            print(f"  - {item}")
        print("\nSuggested Debian/Ubuntu install:")
        print("  sudo apt install python3-venv python3-pip pandoc unzip")
        print("\nThe repository Markdown (Combined_VFR_IFR_Ch1.md) is the canonical" \
              " source of checklist content. If you have a DOCX you may place it in" \
              " the repo root and run scripts/extract_docx_structure.py to" \
              " re-generate the Markdown, but it is not required for normal builds.")
        print("\nThen set up Python deps:")
        print("  python3 -m venv .venv")
        print("  . .venv/bin/activate")
        print("  Use 'uv sync' (or 'uv venv' + 'uv pip install --project .') and run commands with 'uv run' or: python -m pip install PyYAML playwright")
        print("  python -m playwright install chromium")
        return 1

    if notes:
        print("\nNotes:")
        for note in notes:
            print(f"  - {note}")

    print("\nEnvironment looks ready for builds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
