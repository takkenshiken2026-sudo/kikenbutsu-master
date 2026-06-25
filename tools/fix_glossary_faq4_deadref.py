#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語FAQ(faq_4)のクリーンアップ。

旧 faq_4_answer は機械生成のテンプレで、退役済みページ（compare/numbers/関連ハブ）への
参照、プレースホルダ（観点D など）を含んでいた。これを term 固有の読みやすい比較ガイドに
置き換える。faq_4_question（語別）はそのまま。100字以上を満たす。

対象は faq 回答にテンプレ痕跡を含む用語のみ（手書きの良質 FAQ 用語には触れない）。
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "glossary_terms.csv"

GARBAGE_MARK = (
    "補足",
    "観点",
    "【1】",
    "【2】",
    "【3】",
    "【4】",
    "compareで整理",
    "compare で整理",
    "numbersページ",
    "関連ハブページ",
)


def has_garbage(row: dict) -> bool:
    return any(
        any(g in (row.get(f"faq_{i}_answer") or "") for g in GARBAGE_MARK)
        for i in (1, 2, 3, 4)
    )


def related_terms(row: dict) -> list[str]:
    """faq_4_question の「X」「Y」を優先、無ければ related_terms 列。"""
    q = row.get("faq_4_question") or ""
    xs = re.findall(r"「([^」]+)」", q)
    if not xs:
        xs = [x.strip() for x in re.split(r"[;；]", row.get("related_terms") or "") if x.strip()]
    return xs[:3]


def new_faq4(row: dict) -> str:
    term = (row.get("term") or "").strip()
    rel = related_terms(row)
    joined = "・".join(f"「{x}」" for x in rel) if rel else "近い分野の用語"
    return (
        f"{term}は{joined}と混同しやすい用語です。"
        f"それぞれの定義と適用条件や指定数量を表に1行ずつ並べ、"
        f"{term}だけにあてはまる特徴を確認すると違いを整理できます。"
        f"過去問で問われた論点はノートに書き出し、関連用語のページと照らして復習してください。"
    )


def main() -> int:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    if not rows:
        return 0
    fieldnames = list(rows[0].keys())
    fixed = 0
    for row in rows:
        if has_garbage(row):
            row["faq_4_answer"] = new_faq4(row)
            fixed += 1
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"faq_4 cleaned for {fixed} terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
