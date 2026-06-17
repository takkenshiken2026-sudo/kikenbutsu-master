#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用語詳細記事の手直しキューを Excel 出力（1本ずつレビュー用）。

  python3 tools/export_glossary_remediation_review.py ~/Desktop/用語詳細_手直しレビュー.xlsx
  python3 tools/export_glossary_remediation_review.py --term アセトアルデヒド
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.glossary_remediation_rules import (  # noqa: E402
    CHECK_LABELS,
    audit_remediation_row,
    norm,
)

CSV_PATH = ROOT / "data" / "glossary_terms.csv"

IMPORTANCE_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}


def build_review_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue
        checks = audit_remediation_row(row)
        if not checks.priority_score():
            continue
        out.append(
            {
                "term": term,
                "category": norm(row.get("category")),
                "importance": norm(row.get("importance")),
                "priority_score": checks.priority_score(),
                "failing_checks": ";".join(checks.failing_labels()),
                "review_status": "",
                "review_notes": "",
                **{f"check_{label}": "Y" if getattr(checks, label) else "" for label in CHECK_LABELS},
                "faq_1_answer_preview": norm(row.get("faq_1_answer"))[:120],
                "term_detail_body_preview": norm(row.get("term_detail_body"))[:120],
            }
        )
    out.sort(
        key=lambda r: (
            IMPORTANCE_ORDER.get(str(r["importance"]), 9),
            -int(r["priority_score"]),
            str(r["term"]),
        )
    )
    return out


def print_term_report(row: dict[str, str]) -> None:
    term = norm(row.get("term"))
    checks = audit_remediation_row(row)
    print(f"=== {term} ({norm(row.get('category'))} / {norm(row.get('importance'))}) ===")
    print(f"優先スコア: {checks.priority_score()}")
    for label in CHECK_LABELS:
        if getattr(checks, label):
            print(f"  [ ] {label}")
    print()
    for n in range(1, 5):
        print(f"FAQ{n} Q: {norm(row.get(f'faq_{n}_question'))}")
        print(f"FAQ{n} A: {norm(row.get(f'faq_{n}_answer'))[:200]}")
        print()


def export_xlsx(path: Path, review_rows: list[dict[str, object]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "remediation"
    headers = [
        "term",
        "category",
        "importance",
        "priority_score",
        "failing_checks",
        "review_status",
        "review_notes",
        *[f"check_{label}" for label in CHECK_LABELS],
        "faq_1_answer_preview",
        "term_detail_body_preview",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for item in review_rows:
        ws.append([item.get(h, "") for h in headers])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="用語詳細手直しレビュー Excel 出力")
    ap.add_argument("output", nargs="?", help="出力 .xlsx パス")
    ap.add_argument("--term", help="1語だけチェックリスト表示")
    args = ap.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    if args.term:
        match = next((r for r in rows if norm(r.get("term")) == args.term), None)
        if not match:
            print(f"term not found: {args.term}", file=sys.stderr)
            return 1
        print_term_report(match)
        return 0

    review_rows = build_review_rows(rows)
    out = Path(args.output or "~/Desktop/用語詳細_手直しレビュー.xlsx").expanduser()
    export_xlsx(out, review_rows)
    print(f"手直し対象: {len(review_rows)} / {len(rows)} 語")
    print(f"出力: {out}")
    print("review_status に done と記入 → 将来 apply 用に利用可能")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
