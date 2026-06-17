#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用語ゼロ書き直しの一次ソース・ブリーフ（執筆前に必ず実行）。

演習 CSV・一問一答・過去問から、用語名が登場する問題だけを抽出し、
分類・ひっかけ・演習 ID を整理する。執筆はこの出力に載った事実だけを使う。

  python3 tools/glossary_rewrite_brief.py --term ジエチルエーテル
  python3 tools/glossary_rewrite_brief.py --term ジエチルエーテル --json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.glossary_past_questions import find_past_questions_for_term  # noqa: E402

PRACTICE_CSV = ROOT / "data" / "practice_questions.csv"
ICHIMON_CSV = ROOT / "data" / "ichimon_questions.csv"
O4_SOURCE = ROOT / "data" / "imported" / "o4_practice_500_source.csv"

EXAM_POINT_RE = re.compile(r"【試験ポイント】([^【]+)")
TRAP_RE = re.compile(r"【ひっかけ】([^【]+)")
PF_ID_RE = re.compile(r"PF-\d+")


def norm(value: object) -> str:
    return str(value or "").strip()


def term_in_text(term: str, text: str) -> bool:
    if not term or not text:
        return False
    if term in text:
        return True
    compact = term.replace("・", "").replace(" ", "")
    return bool(compact and compact in text.replace("・", "").replace(" ", ""))


def _parse_tags(tags: str) -> list[str]:
    return [t.strip() for t in norm(tags).split(";") if t.strip()]


def _extract_bullets(blob: str) -> list[str]:
    points = [norm(m.group(1)) for m in EXAM_POINT_RE.finditer(blob)]
    traps = [norm(m.group(1)) for m in TRAP_RE.finditer(blob)]
    out: list[str] = []
    for item in points + traps:
        if item and item not in out:
            out.append(item)
    return out


def load_practice_hits(term: str) -> list[dict[str, str]]:
    if not PRACTICE_CSV.is_file():
        return []
    hits: list[dict[str, str]] = []
    for row in csv.DictReader(PRACTICE_CSV.open(encoding="utf-8-sig")):
        stem = norm(row.get("stem"))
        expl = norm(row.get("explanation"))
        tags = norm(row.get("tags"))
        hay = " ".join([stem, expl, tags])
        if not term_in_text(term, hay):
            continue
        pf_ids = sorted(set(PF_ID_RE.findall(tags)))
        hits.append(
            {
                "source": "practice",
                "id": pf_ids[0] if pf_ids else f"practice-{row.get('id', '')}",
                "pf_ids": ";".join(pf_ids),
                "stem": stem[:120],
                "exam_points": _extract_bullets(expl),
                "legal_hint": "",
            }
        )
    return hits


def load_ichimon_hits(term: str) -> list[dict[str, str]]:
    if not ICHIMON_CSV.is_file():
        return []
    hits: list[dict[str, str]] = []
    for row in csv.DictReader(ICHIMON_CSV.open(encoding="utf-8-sig")):
        q = norm(row.get("question"))
        a = norm(row.get("answer"))
        tags = norm(row.get("tags"))
        if not term_in_text(term, " ".join([q, a, tags])):
            continue
        tf_id = norm(row.get("id")) or tags.split(";")[0]
        hits.append(
            {
                "source": "ichimon",
                "id": tf_id,
                "stem": q[:120],
                "correct": norm(row.get("correct")),
                "answer_preview": a[:160],
            }
        )
    return hits


def load_o4_legal(term: str) -> list[str]:
    if not O4_SOURCE.is_file():
        return []
    legal: list[str] = []
    for row in csv.DictReader(O4_SOURCE.open(encoding="utf-8-sig")):
        hay = " ".join(
            [
                norm(row.get("stem")),
                norm(row.get("main_explanation")),
                norm(row.get("exam_point")),
                norm(row.get("trap")),
                norm(row.get("tags")),
            ]
        )
        if term_in_text(term, hay):
            lb = norm(row.get("legal_basis"))
            if lb and lb not in legal:
                legal.append(lb)
    return legal


def build_brief(term: str) -> dict[str, object]:
    practice = load_practice_hits(term)
    ichimon = load_ichimon_hits(term)
    past = find_past_questions_for_term(term, limit=5, require_term_in_text=True)
    legal = load_o4_legal(term)

    exam_points: list[str] = []
    for hit in practice:
        for p in hit.get("exam_points", []):
            if p not in exam_points:
                exam_points.append(p)

    example_candidates = [
        {
            "id": h["id"],
            "question": h["stem"],
            "correct": h.get("correct", ""),
            "answer_preview": h.get("answer_preview", ""),
        }
        for h in ichimon[:5]
    ]

    return {
        "term": term,
        "practice_count": len(practice),
        "ichimon_count": len(ichimon),
        "past_question_count": len(past),
        "legal_basis_hints": legal,
        "exam_points_from_practice": exam_points[:8],
        "practice_ids": sorted({h["id"] for h in practice if h.get("id")}),
        "ichimon_ids": [h["id"] for h in ichimon[:8]],
        "example_candidates": example_candidates,
        "past_questions": [
            {
                "label": f"{p['year']}年 第{p['qno']}問",
                "href": p["href_rel"],
                "preview": p.get("stem_preview", ""),
            }
            for p in past
        ],
        "writing_rules": [
            "分類・代表例は上記 exam_points / 演習解説に載った表現のみ使う",
            "演習 ID（PF-xxx / TF-PF-xxx）を exam_points または article_lead に1件以上明記",
            "related_terms は rewrite:2026-06 済み、または同バッチで書き直す語だけ",
            "別表表記は「危険物の規制に関する政令 別表第1」に統一（別表第三は演習DB表記）",
        ],
    }


def print_brief(brief: dict[str, object]) -> None:
    term = brief["term"]
    print(f"# 書き直しブリーフ: {term}")
    print()
    print(f"演習: {brief['practice_count']}件 / 一問一答: {brief['ichimon_count']}件 / 過去問: {brief['past_question_count']}件")
    print()
    if brief["legal_basis_hints"]:
        print("## 法令ヒント（演習DB）")
        for lb in brief["legal_basis_hints"]:
            print(f"- {lb}")
        print()
    if brief["exam_points_from_practice"]:
        print("## 試験ポイント（演習解説より）")
        for p in brief["exam_points_from_practice"]:
            print(f"- {p}")
        print()
    if brief["practice_ids"]:
        print("## 参照演習 ID")
        print(", ".join(brief["practice_ids"]))
        print()
    if brief["example_candidates"]:
        print("## 例題候補（一問一答）")
        for ex in brief["example_candidates"][:3]:
            print(f"- [{ex['id']}] {ex['question']}")
            if ex.get("answer_preview"):
                print(f"  → {ex['answer_preview'][:100]}")
        print()
    if brief["past_questions"]:
        print("## 過去問")
        for pq in brief["past_questions"]:
            print(f"- {pq['label']}: {pq.get('preview', '')[:80]}")
        print()
    print("## 執筆ルール")
    for rule in brief["writing_rules"]:
        print(f"- {rule}")


def main() -> int:
    ap = argparse.ArgumentParser(description="用語書き直しの一次ソース・ブリーフ")
    ap.add_argument("--term", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    brief = build_brief(args.term)
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    else:
        print_brief(brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
