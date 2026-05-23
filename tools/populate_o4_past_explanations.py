#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
past_questions.csv の解説欄を o4_past_explanation_content で一括再生成する。

  python3 tools/populate_o4_past_explanations.py
  python3 tools/populate_o4_past_explanations.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.o4_past_explanation_content import build_package

CSV_PATH = ROOT / "data" / "past_questions.csv"
MIN_WRONG = 48


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=CSV_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = args.csv.resolve()
    if not path.is_file():
        print(f"error: not found {path}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    if not rows:
        print("error: empty CSV", file=sys.stderr)
        return 1
    fieldnames = list(rows[0].keys())
    short = 0

    for row in rows:
        pkg = build_package(row)
        if args.dry_run:
            ec = pkg["explanation_choices"]
            if ec:
                avg = sum(len(p.split(":", 1)[1]) for p in ec.split(";")) / max(
                    ec.count(";") + 1, 1
                )
                if avg < MIN_WRONG:
                    short += 1
            continue
        row.update(pkg)

    if args.dry_run:
        print(f"rows={len(rows)} short_wrong_avg={short}")
        r = rows[0]
        pkg = build_package(r)
        print("sample q1 correct:", pkg["explanation_correct"][:120])
        print("sample q1 wrong:", pkg["explanation_choices"][:160])
        return 0

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")
    print("Next: python3 tools/build_all.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
