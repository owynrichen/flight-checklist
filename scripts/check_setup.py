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
    source_docx = os.path.join(repo_root, "Combined VFR and IFR Flight Ch 1.docx")

    print("Environment check")
    print(f"  Python: {sys.version.split()[0]}")

    if os.path.exists(source_docx):
        print("  source docx: ok")
    else:
        print("  source docx: missing")
        missing.append("Combined VFR and IFR Flight Ch 1.docx")

    if not python_version_ok():
        missing.append("python3.8+")

    for cmd in ["pandoc", "unzip", "xelatex"]:
        if have_command(cmd):
            print(f"  {cmd}: ok")
        else:
            print(f"  {cmd}: missing")
            missing.append(cmd)

    if have_command("weasyprint"):
        print("  weasyprint: ok")
    elif have_command("wkhtmltopdf"):
        print("  wkhtmltopdf: ok (legacy fallback)")
        notes.append("weasyprint is preferred for correct multi-column PDF output")
    else:
        print("  weasyprint/wkhtmltopdf: missing")
        missing.append("weasyprint or wkhtmltopdf")

    for mod in ["yaml"]:
        if have_module(mod):
            print(f"  python module {mod}: ok")
        else:
            print(f"  python module {mod}: missing")
            missing.append(f"python module {mod}")

    if os.path.exists(venv_python):
        if have_module_in_python(venv_python, "docx"):
            print("  python module docx (.venv): ok")
        else:
            print("  python module docx (.venv): missing")
            missing.append("python module docx in .venv")
    elif have_module("docx"):
        print("  python module docx: ok")
    else:
        print("  python module docx: missing")
        missing.append("python module docx")

    if os.path.exists(venv_python):
        if have_module_in_python(venv_python, "playwright"):
            print("  python module playwright (.venv): ok")
        else:
            print("  python module playwright (.venv): missing")
            missing.append("python module playwright in .venv")
    elif have_module("playwright"):
        print("  python module playwright: ok")
    else:
        print("  python module playwright: missing")
        missing.append("python module playwright")

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
        print("  sudo apt install python3-venv python3-pip pandoc texlive-xetex unzip weasyprint")
        print("\nMake sure the source DOCX is present in the repo root:")
        print("  Combined VFR and IFR Flight Ch 1.docx")
        print("\nThen set up Python deps:")
        print("  python3 -m venv .venv")
        print("  . .venv/bin/activate")
        print("  python -m pip install -r requirements.txt")
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
