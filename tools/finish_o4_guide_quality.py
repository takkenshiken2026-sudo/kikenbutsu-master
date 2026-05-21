#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド品質の最終仕上げ（CSV更新 → 監査 → ビルド）。

  python3 tools/finish_o4_guide_quality.py
  python3 tools/finish_o4_guide_quality.py --skip-build
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    steps = [
        [sys.executable, "tools/enrich_o4_guide_articles.py", "--force"],
        [sys.executable, "tools/audit_guide_quality.py"],
    ]
    if not args.skip_build:
        steps.append([sys.executable, "tools/build_all.py"])

    for cmd in steps:
        code = run(cmd)
        if code != 0:
            return code
    print("finish_o4_guide_quality: done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
