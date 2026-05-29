#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一覧ページの定義・概要を記事本文ベースの要約に更新する。

  python3 tools/refresh_index_summaries.py
  python3 tools/refresh_index_summaries.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.index_summary_utils import (  # noqa: E402
    build_hub_index_summary,
    is_generic_hub_summary,
    norm,
)

HUB_CSVS: tuple[tuple[Path, str], ...] = (
    (ROOT / "data" / "comparisons.csv", "compare"),
    (ROOT / "data" / "numbers.csv", "numbers"),
    (ROOT / "data" / "mistakes.csv", "mistakes"),
)


def refresh_csv(path: Path, *, kind: str | None, field: str, dry_run: bool) -> int:
    if not path.is_file():
        print(f"skip (missing): {path}", file=sys.stderr)
        return 0

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    updated = 0
    for row in rows:
        new_val = build_hub_index_summary(row, kind=kind or "")
        if not new_val:
            continue
        old_val = norm(row.get(field))
        if old_val == new_val:
            continue
        row[field] = new_val
        updated += 1

    print(f"{path.name}: {field} 更新 {updated} / {len(rows)} 件")

    if dry_run or not updated:
        return updated

    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return updated


def main() -> int:
    ap = argparse.ArgumentParser(description="一覧用 定義/概要 を記事ベースで再生成")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total = 0
    for path, kind in HUB_CSVS:
        total += refresh_csv(path, kind=kind, field="summary", dry_run=args.dry_run)

    print(f"合計更新: {total} 件")
    if not args.dry_run:
        print("Next: python3 tools/build_glossary_pages.py && python3 tools/build_compare_pages.py && python3 tools/build_numbers_mistakes_pages.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
