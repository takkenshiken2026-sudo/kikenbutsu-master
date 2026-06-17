#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glossary_terms.csv の index_summary（用語一覧・概要）を監査する。

  python3 tools/audit_glossary_index_summaries.py
  python3 tools/audit_glossary_index_summaries.py --strict
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.glossary_index_summary_rules import (  # noqa: E402
    INDEX_SUMMARY_MAX_LEN,
    INDEX_SUMMARY_MIN_LEN,
    audit_index_summary_cross_rows,
    check_index_summary_row,
    index_summary_fill_stats,
    norm,
)

CSV_PATH = ROOT / "data" / "glossary_terms.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description="用語一覧 index_summary の品質・重複監査")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="WARN も失敗扱い（index_summary 全件記入後の公開ゲート用）",
    )
    args = ap.parse_args()

    if not CSV_PATH.is_file():
        print(f"missing: {CSV_PATH}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    filled, total = index_summary_fill_stats(rows)
    print(
        f"index_summary 記入: {filled} / {total} 語"
        f"（目標 {INDEX_SUMMARY_MIN_LEN}〜{INDEX_SUMMARY_MAX_LEN} 字・オリジナル文）"
    )

    errors = warns = 0
    for idx, row in enumerate(rows, start=2):
        term = norm(row.get("term"))
        if not term:
            continue
        for issue in check_index_summary_row(row):
            msg = f"glossary_terms.csv:{idx} ({term}) [{issue.column}] {issue.message}"
            if issue.level == "ERROR":
                errors += 1
                print(msg, file=sys.stderr)
            else:
                warns += 1
                if args.strict:
                    print(msg, file=sys.stderr)
                else:
                    print(msg)

    for issue in audit_index_summary_cross_rows(rows):
        term = issue.term or "?"
        msg = f"glossary_terms.csv [cross] ({term}) [{issue.column}] {issue.message}"
        errors += 1
        print(msg, file=sys.stderr)

    print(f"\nindex_summary 監査: ERROR {errors} / WARN {warns}")
    if errors:
        return 1
    if args.strict and warns:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
