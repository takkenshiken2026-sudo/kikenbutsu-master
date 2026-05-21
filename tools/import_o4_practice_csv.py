#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危険物取扱者乙4 想定問題 CSV → data/practice_questions.csv（実践演習）

  python3 tools/import_o4_practice_csv.py
  python3 tools/import_o4_practice_csv.py --source /path/to/危険物取扱者乙4_....csv
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / "Downloads" / "危険物取扱者乙4_五肢択一_想定問題500問_DB.csv"
ARCHIVE = ROOT / "data" / "imported" / "o4_practice_500_source.csv"
OUT = ROOT / "data" / "practice_questions.csv"

PRACTICE_HEADER = [
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
    "explanation",
]

SUBJECT_TO_CATEGORY = {
    "危険物に関する法令": "法令・制度",
    "基礎的な物理学及び基礎的な化学": "物性・化学",
    "危険物の性質並びにその火災予防及び消火の方法": "火災・消火・漏えい",
}


def norm(s: str | None) -> str:
    return (s or "").strip()


def build_tags(row: dict[str, str]) -> str:
    parts = [
        norm(row.get("id")),
        norm(row.get("topic_id")),
        norm(row.get("unit")),
        norm(row.get("topic")),
        norm(row.get("difficulty")),
        norm(row.get("question_type")),
    ]
    return ";".join(p for p in parts if p)


def build_explanation(row: dict[str, str]) -> str:
    parts: list[str] = []
    main = norm(row.get("explanation"))
    if main:
        parts.append(main)
    exam_point = norm(row.get("exam_point"))
    if exam_point:
        parts.append(f"【試験ポイント】{exam_point}")
    trap = norm(row.get("trap_point"))
    if trap:
        parts.append(f"【ひっかけ】{trap}")
    labels = ("ア", "イ", "ウ", "エ", "オ")
    for i in range(1, 6):
        ce = norm(row.get(f"choice_{i}_explanation"))
        if not ce:
            continue
        label = labels[i - 1]
        parts.append(f"【選択肢{label}】{ce}")
    return "\n\n".join(parts) if parts else "（解説は未入力です。）"


def row_to_practice(row: dict[str, str], question_no: int) -> dict[str, str]:
    subject = norm(row.get("subject"))
    category = SUBJECT_TO_CATEGORY.get(subject)
    if not category:
        raise ValueError(f"未対応の subject: {subject!r} (id={row.get('id')})")

    answer_raw = norm(row.get("answer"))
    try:
        answer = int(answer_raw)
    except ValueError as e:
        raise ValueError(f"answer が整数ではありません: id={row.get('id')} answer={answer_raw!r}") from e
    if not 1 <= answer <= 5:
        raise ValueError(f"answer は 1〜5: id={row.get('id')} answer={answer}")

    choices = [norm(row.get(f"choice_{i}")) for i in range(1, 6)]
    if not all(choices):
        raise ValueError(f"選択肢欠け: id={row.get('id')}")

    stem = norm(row.get("question"))
    if not stem:
        raise ValueError(f"問題文なし: id={row.get('id')}")

    return {
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
        "correct": str(answer),
        "explanation": build_explanation(row),
    }


def load_source(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def main() -> int:
    ap = argparse.ArgumentParser(description="乙4想定問題CSVを practice_questions.csv に変換")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="入力CSV")
    ap.add_argument("--no-archive", action="store_true", help="data/imported/ へ原本をコピーしない")
    args = ap.parse_args()
    src: Path = args.source.expanduser().resolve()
    if not src.is_file():
        print(f"入力がありません: {src}", file=sys.stderr)
        return 1

    rows = load_source(src)
    if not rows:
        print("入力CSVに行がありません", file=sys.stderr)
        return 1

    out_rows: list[dict[str, str]] = []
    for i, row in enumerate(rows, start=1):
        out_rows.append(row_to_practice(row, i))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRACTICE_HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)

    if not args.no_archive:
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, ARCHIVE)

    print(f"Wrote {OUT} ({len(out_rows)} 問)")
    if not args.no_archive:
        print(f"Archived source → {ARCHIVE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
