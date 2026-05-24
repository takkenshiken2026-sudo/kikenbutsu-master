#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用語詳細・試験ガイドをプロ品質まで一括引き上げする。

  python3 tools/enrich_seo_pro_all.py
  python3 tools/enrich_seo_pro_all.py --skip-glossary-enrich
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.seo_pro_quality import (  # noqa: E402
    apply_glossary_pro_row,
    apply_guide_pro_row,
    ensure_glossary_csv_columns,
    ensure_guide_csv_columns,
)

GLOSSARY_CSV = ROOT / "data" / "glossary_terms.csv"
GUIDE_CSV = ROOT / "data" / "guide_articles.csv"


def run_py(script: str, *args: str) -> int:
    cmd = [sys.executable, str(ROOT / "tools" / script), *args]
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


def enrich_glossary_pro() -> int:
    with GLOSSARY_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = ensure_glossary_csv_columns(list(reader.fieldnames or []))
        rows = list(reader)
    for row in rows:
        for col in fieldnames:
            row.setdefault(col, "")
        if norm_term := (row.get("term") or "").strip():
            apply_glossary_pro_row(row)
    with GLOSSARY_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Glossary pro: {len(rows)} terms → {GLOSSARY_CSV}")
    return 0


def enrich_guide_pro() -> int:
    with GUIDE_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = ensure_guide_csv_columns(list(reader.fieldnames or []))
        rows = list(reader)
    for row in rows:
        for col in fieldnames:
            row.setdefault(col, "")
        apply_guide_pro_row(row)
    with GUIDE_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Guide pro: {len(rows)} articles → {GUIDE_CSV}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SEO記事（用語・試験ガイド）プロ品質一括引き上げ")
    ap.add_argument("--skip-glossary-enrich", action="store_true")
    ap.add_argument("--skip-guide-enrich", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    if not args.skip_glossary_enrich:
        if run_py("enrich_o4_glossary_details.py") != 0:
            return 1
    if enrich_glossary_pro() != 0:
        return 1

    if not args.skip_guide_enrich:
        if run_py("enrich_o4_guide_articles.py", "--force") != 0:
            return 1
    if enrich_guide_pro() != 0:
        return 1

    if not args.skip_build:
        if run_py("build_all.py") != 0:
            return 1

    print("enrich_seo_pro_all: done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
