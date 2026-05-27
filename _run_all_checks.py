#!/usr/bin/env python3
"""One-off: build, audits, deploy docs, git status → _command_outputs.txt"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_command_outputs.txt"


def append(label: str, cmd: list[str]) -> int:
    with OUT.open("a", encoding="utf-8") as f:
        f.write(f"\n{'='*72}\n=== {label} ===\n{'='*72}\n")
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if p.stdout:
            f.write(p.stdout)
            if not p.stdout.endswith("\n"):
                f.write("\n")
        if p.stderr:
            f.write("--- stderr ---\n")
            f.write(p.stderr)
            if not p.stderr.endswith("\n"):
                f.write("\n")
        f.write(f"EXIT: {p.returncode}\n")
    return p.returncode


def main() -> int:
    OUT.write_text(f"ROOT={ROOT}\n", encoding="utf-8")
    steps = [
        ("1 cat tools/build_all.py", ["cat", "tools/build_all.py"]),
        ("2 python3 tools/build_all.py", [sys.executable, "tools/build_all.py"]),
        ("3 validate_public_content", [sys.executable, "tools/validate_public_content.py"]),
        ("4 audit_guide_quality", [sys.executable, "tools/audit_guide_quality.py"]),
        ("5 audit_glossary_quality", [sys.executable, "tools/audit_glossary_quality.py"]),
        ("6 audit_glossary_article_quality", [sys.executable, "tools/audit_glossary_article_quality.py"]),
        ("7a cat docs/DEPLOY.md", ["cat", "docs/DEPLOY.md"]),
        ("7b cat tools/deploy_gh_pages.sh", ["cat", "tools/deploy_gh_pages.sh"]),
        ("8a git remote -v", ["git", "remote", "-v"]),
        ("8b git branch", ["git", "branch"]),
        ("8c git status --short (head 20)", ["git", "status", "--short"]),
    ]
    for label, cmd in steps:
        code = append(label, cmd)
        if label.startswith("2 ") and code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
