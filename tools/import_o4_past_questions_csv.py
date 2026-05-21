#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乙4 過去問 CSV（PDF抽出）→ data/past_questions.csv

  python3 tools/import_o4_past_questions_csv.py \\
    --source /path/to/kikenbutsu_otsu4_questions.csv

  python3 tools/import_o4_past_questions_csv.py --source ... --exam-year 2026
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    Path.home()
    / "Documents/Codex/2026-05-21/4/kikenbutsu_otsu4_questions.csv"
)
ARCHIVE = ROOT / "data" / "imported" / "o4_past_otsu4_source.csv"
OUT = ROOT / "data" / "past_questions.csv"

PAST_HEADER = [
    "exam_year",
    "exam_wareki",
    "question_no",
    "type",
    "category",
    "tags",
    "stem",
    "preamble",
    "statement_a",
    "statement_b",
    "statement_c",
    "statement_d",
    "choice_1",
    "choice_2",
    "choice_3",
    "choice_4",
    "choice_5",
    "correct",
    "is_exempt",
    "is_invalidated",
    "note",
    "explanation",
    "explanation_summary",
    "explanation_correct",
    "explanation_choices",
    "explanation_point",
    "related_links",
]

SECTION_TO_CATEGORY = {
    "危険物に関する法令": "法令・制度",
    "基礎的な物理学及び基礎的な化学": "物性・化学",
    "危険物の性質並びにその火災予防及び消火の方法": "火災・消火・漏えい",
}


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def load_source(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def build_tags(row: dict[str, str]) -> str:
    parts = [
        norm(row.get("id")),
        norm(row.get("section")),
        norm(row.get("source_file")),
        f"p{norm(row.get('page'))}" if norm(row.get("page")) else "",
        "過去問",
        "乙4",
    ]
    if norm(row.get("needs_review")).upper() == "TRUE":
        parts.append("要確認")
    return ";".join(p for p in parts if p)


def build_explanations(row: dict[str, str], correct: int) -> dict[str, str]:
    answer_text = norm(row.get("answer_text"))
    section = norm(row.get("section"))
    stem = norm(row.get("question_text"))

    summary = (
        f"本問は「{section}」分野の過去問形式（五肢択一）です。"
        "正解の根拠を確認し、誤り選択肢との違いを整理してください。"
    )
    explanation = f"正解は選択肢（{correct}）です。{answer_text}"
    correct_detail = answer_text or "（正解文の詳細は未入力です。）"

    wrong_bits: list[str] = []
    for i in range(1, 6):
        if i == correct:
            continue
        text = norm(row.get(f"choice_{i}"))
        if not text:
            continue
        preview = text if len(text) <= 72 else text[:69] + "…"
        wrong_bits.append(f"{i}:（{i}）は正解ではありません。{preview}")

    point = (
        f"「{section}」では、条文の言い回しと数値・条件の違いが問われやすいです。"
        "関連する用語解説と実践演習で定着を確認してください。"
    )

    return {
        "explanation": explanation,
        "explanation_summary": summary,
        "explanation_correct": correct_detail,
        "explanation_choices": ";".join(wrong_bits),
        "explanation_point": point,
    }


def row_to_past(
    row: dict[str, str],
    *,
    exam_year: int,
    exam_wareki: str,
) -> dict[str, str]:
    section = norm(row.get("section"))
    category = SECTION_TO_CATEGORY.get(section)
    if not category:
        raise ValueError(f"未対応の section: {section!r} (id={row.get('id')})")

    qno_raw = norm(row.get("question_number"))
    try:
        question_no = int(qno_raw)
    except ValueError as e:
        raise ValueError(f"question_number が整数ではありません: id={row.get('id')}") from e

    answer_raw = norm(row.get("answer"))
    try:
        correct = int(answer_raw)
    except ValueError as e:
        raise ValueError(f"answer が整数ではありません: id={row.get('id')}") from e
    if not 1 <= correct <= 5:
        raise ValueError(f"answer は 1〜5: id={row.get('id')} answer={correct}")

    choices = [norm(row.get(f"choice_{i}")) for i in range(1, 6)]
    if not all(choices):
        raise ValueError(f"選択肢欠け: id={row.get('id')}")

    stem = norm(row.get("question_text"))
    if not stem:
        raise ValueError(f"問題文なし: id={row.get('id')}")

    exp_parts = build_explanations(row, correct)
    note = ""
    if norm(row.get("needs_review")).upper() == "TRUE":
        note = "要確認（抽出データ）"

    return {
        "exam_year": str(exam_year),
        "exam_wareki": exam_wareki,
        "question_no": str(question_no),
        "type": "single",
        "category": category,
        "tags": build_tags(row),
        "stem": stem,
        "preamble": "",
        "statement_a": "",
        "statement_b": "",
        "statement_c": "",
        "statement_d": "",
        "choice_1": choices[0],
        "choice_2": choices[1],
        "choice_3": choices[2],
        "choice_4": choices[3],
        "choice_5": choices[4],
        "correct": str(correct),
        "is_exempt": "FALSE",
        "is_invalidated": "FALSE",
        "note": note,
        "related_links": f"field:{category};terms:用語解説一覧",
        **exp_parts,
    }


def merge_existing(
    existing: list[dict[str, str]],
    imported: list[dict[str, str]],
    exam_year: int,
) -> list[dict[str, str]]:
    kept = [r for r in existing if int(r["exam_year"]) != exam_year]
    seen = {(int(r["exam_year"]), int(r["question_no"])) for r in kept}
    for row in imported:
        key = (int(row["exam_year"]), int(row["question_no"]))
        if key in seen:
            raise ValueError(f"重複: exam_year={key[0]} question_no={key[1]}")
        seen.add(key)
    return kept + imported


def main() -> int:
    ap = argparse.ArgumentParser(description="乙4過去問CSVを past_questions.csv に取り込む")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--exam-year", type=int, default=2026)
    ap.add_argument(
        "--exam-wareki",
        default="",
        help="年度表示ラベル（未指定時は「{exam_year}年」）",
    )
    ap.add_argument(
        "--replace-year",
        action="store_true",
        default=True,
        help="同一 exam_year の既存行を差し替える（既定: 有効）",
    )
    ap.add_argument(
        "--append-only",
        action="store_true",
        help="既存を残して追加のみ（--replace-year を無効化）",
    )
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    if args.append_only:
        args.replace_year = False

    src = args.source.expanduser().resolve()
    if not src.is_file():
        print(f"入力がありません: {src}", file=sys.stderr)
        return 1

    rows = load_source(src)
    if not rows:
        print("入力CSVに行がありません", file=sys.stderr)
        return 1

    wareki_label = norm(args.exam_wareki) or f"{args.exam_year}年"

    imported: list[dict[str, str]] = []
    for row in rows:
        imported.append(
            row_to_past(
                row,
                exam_year=args.exam_year,
                exam_wareki=wareki_label,
            )
        )

    existing: list[dict[str, str]] = []
    if OUT.is_file() and not args.replace_year:
        existing = load_source(OUT)
    elif OUT.is_file() and args.replace_year:
        existing = [
            r
            for r in load_source(OUT)
            if int(r["exam_year"]) != args.exam_year
        ]

    out_rows = merge_existing(existing, imported, args.exam_year)
    out_rows.sort(key=lambda r: (int(r["exam_year"]), int(r["question_no"])))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PAST_HEADER, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    if not args.no_archive:
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, ARCHIVE)

    print(
        f"Wrote {OUT} — 取り込み {len(imported)} 問"
        f"（exam_year={args.exam_year}、合計 {len(out_rows)} 問）"
    )
    if not args.no_archive:
        print(f"Archived source → {ARCHIVE}")
    print("Next: python3 tools/build_all.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
