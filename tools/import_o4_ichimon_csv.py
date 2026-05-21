#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危険物取扱者乙4 一問一答（○×）CSV → data/ichimon_questions.csv

  python3 tools/import_o4_ichimon_csv.py
  python3 tools/import_o4_ichimon_csv.py --source /path/to/危険物取扱者乙4_....csv
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    Path.home() / "Downloads" / "危険物取扱者乙4_一問一答_○×問題500問_DB.csv"
)
ARCHIVE = ROOT / "data" / "imported" / "o4_ichimon_500_source.csv"
OUT = ROOT / "data" / "ichimon_questions.csv"

ICHIMON_HEADER = [
    "id",
    "question",
    "answer",
    "explanation",
    "category",
    "tags",
    "source",
    "note",
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
        norm(row.get("source_question_id")),
        norm(row.get("topic_id")),
        norm(row.get("unit")),
        norm(row.get("topic")),
        norm(row.get("difficulty")),
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
    return "\n\n".join(parts) if parts else "（解説は未入力です。）"


def parse_answer(row: dict[str, str]) -> str:
    text = norm(row.get("answer_text"))
    if text in ("○", "〇", "×", "✕", "╳"):
        return "○" if text in ("○", "〇") else "×"
    raw = norm(row.get("answer")).lower()
    if raw in ("true", "1", "yes"):
        return "○"
    if raw in ("false", "0", "no"):
        return "×"
    raise ValueError(f"answer を判定できません: id={row.get('id')} answer={row.get('answer')!r}")


def row_to_ichimon(row: dict[str, str]) -> dict[str, str]:
    rid = norm(row.get("id"))
    if not rid:
        raise ValueError("id が空の行があります")

    subject = norm(row.get("subject"))
    category = SUBJECT_TO_CATEGORY.get(subject)
    if not category:
        raise ValueError(f"未対応の subject: {subject!r} (id={rid})")

    question = norm(row.get("statement"))
    if not question:
        raise ValueError(f"問題文なし: id={rid}")

    return {
        "id": rid,
        "question": question,
        "answer": parse_answer(row),
        "explanation": build_explanation(row),
        "category": category,
        "tags": build_tags(row),
        "source": norm(row.get("source_note")) or "乙4一問一答DB",
        "note": norm(row.get("review_status")),
    }


def load_source(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def main() -> int:
    ap = argparse.ArgumentParser(description="乙4一問一答CSVを ichimon_questions.csv に変換")
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
    seen: set[str] = set()
    for row in rows:
        out = row_to_ichimon(row)
        if out["id"] in seen:
            raise ValueError(f"id が重複: {out['id']}")
        seen.add(out["id"])
        out_rows.append(out)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ICHIMON_HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)

    if not args.no_archive:
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, ARCHIVE)

    print(f"Wrote {OUT} ({len(out_rows)} 問)")
    if not args.no_archive:
        print(f"Archived source → {ARCHIVE}")
    by_cat: dict[str, int] = {}
    for r in out_rows:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
