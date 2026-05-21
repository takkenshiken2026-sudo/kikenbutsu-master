#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glossary_terms.csv の short_def を definition / 詳細本文から再生成する（一覧の定義抜粋用）。

  python3 tools/refresh_glossary_short_defs.py
  python3 tools/refresh_glossary_short_defs.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.enrich_o4_glossary_details import (  # noqa: E402
    KEEP_TERMS,
    build_short_def,
    is_exam_stem,
    is_generic_sentence,
    norm,
    split_sentences,
    trim_lead_sentence,
)

CSV_PATH = ROOT / "data" / "glossary_terms.csv"

_WEAK_MARKERS = (
    "で頻出する",
    "出題範囲において重要な概念",
    "選択肢の言い換え",
    "実践演習で誤答した",
)


def is_weak_short(text: str, term: str) -> bool:
    t = norm(text)
    if not t or t in (term, f"{term}。"):
        return True
    if len(t) < 20:
        return True
    if is_generic_sentence(t):
        return True
    if any(m in t for m in _WEAK_MARKERS) and len(t) < 100:
        return True
    return False


def lead_from_definition(term: str, definition: str) -> str:
    m = re.search(rf"まず「{re.escape(term)}」は、([^。]+。)", definition)
    if not m:
        return ""
    body = trim_lead_sentence(term, m.group(0))
    if len(body) < 18 or is_exam_stem(body) or is_generic_sentence(body):
        return ""
    return body


def lead_from_detail(term: str, detail: str) -> str:
    for para in (detail or "").split("\n\n"):
        for sent in split_sentences(para, 4):
            body = trim_lead_sentence(term, sent)
            if len(body) < 22 or is_exam_stem(body) or is_generic_sentence(body):
                continue
            return body
    return ""


def refresh_short_def(row: dict[str, str]) -> str | None:
    term = norm(row.get("term"))
    if not term or term in KEEP_TERMS:
        return None

    category = norm(row.get("category")) or "危険物"
    current = norm(row.get("short_def"))
    definition = norm(row.get("definition"))
    detail = norm(row.get("term_detail_body"))

    lead = lead_from_definition(term, definition)
    if not lead:
        lead = lead_from_detail(term, detail)
    if not lead and current and not is_weak_short(current, term):
        return None

    if not lead:
        return None

    new_short = build_short_def(term, lead, category)
    if new_short == current or is_weak_short(new_short, term):
        return None
    return new_short


def main() -> int:
    ap = argparse.ArgumentParser(description="用語一覧向け short_def を再生成")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CSV_PATH.is_file():
        print(f"入力がありません: {CSV_PATH}", file=sys.stderr)
        return 1

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    updated = 0
    for row in rows:
        new_short = refresh_short_def(row)
        if new_short:
            row["short_def"] = new_short
            updated += 1

    print(f"short_def 更新: {updated} / {len(rows)} 件")

    if args.dry_run:
        return 0

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {CSV_PATH}")
    print("Next: python3 tools/build_glossary_pages.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
