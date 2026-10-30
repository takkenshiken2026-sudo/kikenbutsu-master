#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/ichimon_questions.csv → exam-site-data-ichimondou.js（window.ICHIMONDOU_ROWS）。

CSV 列: id, question, answer, explanation, explanation_summary, explanation_correct,
explanation_opposite, explanation_point, category, tags, source, note
（静的 HTML の詳細解説用。SPA 用 JS は従来どおり explanation を要約表示）
- answer: ○＝記述が正しい / ×＝記述が誤り（index.html の correctAnswer と一致）
- category: tools/csv_to_exam_site_past_js.py の CATEGORY_TO_FIELD と揃える
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.ichimon_paths import ichimon_rel_path
from tools.build_practice_ichimon_pages import ichimon_page_dict
from tools.q_explanation import (
    _o4_explanation_lead,
    build_ichimon_explanation_html,
)
from tools.site_config import category_to_field_map, default_exam_id

DATA_CSV = ROOT / "data" / "ichimon_questions.csv"
# 関連試験（丙種・甲種…）の一問一答。SPA 専用（乙4 の静的ページ生成器には読ませない）。
RELATED_CSV = ROOT / "data" / "related_exam_ichimon.csv"
OUT_JS = ROOT / "exam-site-data-ichimondou.js"

DEFAULT_EXAM: str = default_exam_id()

# site-config.json の fields[].aliases / name に対応
CATEGORY_TO_FIELD: dict[str, str] = category_to_field_map()


def norm(s: str | None) -> str:
    return (s or "").strip()


def category_to_field(cat: str) -> str:
    c = norm(cat)
    f = CATEGORY_TO_FIELD.get(c)
    if not f:
        raise ValueError(f"未対応の category={c!r}")
    return f


def parse_marubatsu_answer(raw: str) -> bool:
    """True = 記述は正しい（ユーザー正解は○） / False = 記述は誤り（正解は×）"""
    s = norm(raw)
    if s in ("○", "〇"):
        return True
    if s in ("×", "✕", "╳"):
        return False
    raise ValueError(f"想定外の answer 列: {raw!r}")


def public_path_from_id(row_id: str) -> str:
    return ichimon_rel_path(row_id)


def normalize_statement(text: str) -> str:
    s = norm(text).replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\s+", " ", s)
    return s


def ichimon_exp_fields(row: dict, line_no: int) -> tuple[str, str]:
    page = ichimon_page_dict(row, line_no)
    exp_html = build_ichimon_explanation_html(page, row)
    exp_plain = (
        norm(row.get("explanation_summary"))
        or _o4_explanation_lead(norm(row.get("explanation")))
        or "（解説は未入力です。）"
    )
    return exp_plain, exp_html


def row_to_obj(row: dict, line_no: int) -> dict:
    rid = norm(row.get("id"))
    if not rid:
        raise ValueError(f"line {line_no}: id が空です")
    cat = norm(row.get("category"))
    exp, exp_html = ichimon_exp_fields(row, line_no)
    return {
        "id": rid,
        "field": category_to_field(cat),
        "statement": normalize_statement(norm(row.get("question"))),
        "correctAnswer": parse_marubatsu_answer(norm(row.get("answer"))),
        "exp": exp,
        "expHtml": exp_html,
        "publicPath": public_path_from_id(rid),
    }


def related_row_to_obj(row: dict, line_no: int) -> dict:
    """関連試験（exam 列で丙種/甲種…）の一問一答。静的ページは作らないので publicPath は付けない。"""
    rid = norm(row.get("id"))
    if not rid:
        raise ValueError(f"related_exam_ichimon.csv line {line_no}: id が空です")
    exam = norm(row.get("exam"))
    if not exam or exam == DEFAULT_EXAM:
        raise ValueError(
            f"related_exam_ichimon.csv line {line_no}: exam 列は関連試験（既定={DEFAULT_EXAM!r} 以外）にしてください"
        )
    cat = norm(row.get("category"))
    statement = normalize_statement(norm(row.get("question")))
    correct = parse_marubatsu_answer(norm(row.get("answer")))
    # 静的ページ用の ichimon_page_dict は id の形式に依存するため使わず、
    # 解説 HTML に必要な最小限の page を自前で組む。
    page = {"statement": statement, "correct_answer": correct}
    exp_html = build_ichimon_explanation_html(page, row)
    exp_plain = (
        norm(row.get("explanation_summary"))
        or _o4_explanation_lead(norm(row.get("explanation")))
        or "（解説は未入力です。）"
    )
    return {
        "id": rid,
        "exam": exam,
        "field": category_to_field(cat),
        "statement": statement,
        "correctAnswer": correct,
        "exp": exp_plain,
        "expHtml": exp_html,
    }


def load_related_rows() -> list[dict]:
    if not RELATED_CSV.is_file():
        return []
    text = RELATED_CSV.read_text(encoding="utf-8-sig")
    rows_in = list(csv.DictReader(text.splitlines()))
    out: list[dict] = []
    seen: set[str] = set()
    for i, row in enumerate(rows_in, start=2):
        obj = related_row_to_obj(row, i)
        if obj["id"] in seen:
            raise ValueError(f"related_exam_ichimon.csv line {i}: id 重複 {obj['id']!r}")
        seen.add(obj["id"])
        out.append(obj)
    return out


def main() -> int:
    if not DATA_CSV.is_file():
        print(f"入力がありません: {DATA_CSV}", file=sys.stderr)
        return 1
    text = DATA_CSV.read_text(encoding="utf-8-sig")
    rows_in = list(csv.DictReader(text.splitlines()))
    objs: list[dict] = []
    for i, row in enumerate(rows_in, start=2):
        objs.append(row_to_obj(row, i))
    related = load_related_rows()
    objs.extend(related)

    payload = json.dumps(objs, ensure_ascii=False, indent=2)
    js = (
        "/* AUTO-GENERATED by tools/csv_to_exam_site_ichimondou_js.py — data/ichimon_questions.csv を編集して再実行 */\n"
        f"window.ICHIMONDOU_ROWS = {payload};\n"
    )
    OUT_JS.write_text(js, encoding="utf-8")
    print(f"Wrote {OUT_JS} ({len(objs)} rows, うち関連試験 {len(related)} 問)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
