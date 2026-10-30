#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/past_questions.csv と data/practice_questions.csv（任意）→ exam-site-data-past.js（CSV_IMPORTED_*）。"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.correct_answer_format import collect_choice_texts, is_valid_correct, parse_correct_js_index
from tools.site_config import category_to_field_map, default_exam_id, extended_correct_answers
from tools.build_past_question_pages import page_dict as past_page_dict
from tools.build_practice_ichimon_pages import practice_page_dict
from tools.q_explanation import _o4_explanation_lead, build_explanation_html

DATA_CSV = ROOT / "data" / "past_questions.csv"
PRACTICE_CSV = ROOT / "data" / "practice_questions.csv"
# 関連試験（丙種・甲種…）の問題。SPA 専用（乙4 の静的ページ生成器には読ませない）。
RELATED_CSV = ROOT / "data" / "related_exam_questions.csv"
OUT_JS = ROOT / "exam-site-data-past.js"
OUT_PRACTICE_JS = ROOT / "exam-site-data-practice.js"

# 実践演習プール（index.html の isCsvPracticePoolQuestion / applyCsvImportedQuestions と対応）
PRACTICE_POOL_YEAR = "orig"
PRACTICE_ID_BASE = 900_000
# 関連試験の id 基点（乙4 の過去問 ≤~999999・実践演習 900000台 と衝突しないよう十分離す）。
RELATED_ID_BASE = 13_000_000
RELATED_EXAM_ORDER = ["heishu", "kou"]

LABELS = [("ア", "statement_a"), ("イ", "statement_b"), ("ウ", "statement_c"), ("エ", "statement_d")]

# site-config.json の fields[].aliases / name に対応
CATEGORY_TO_FIELD: dict[str, str] = category_to_field_map()

# 試験軸。CSV の任意列 exam（空＝既定試験）。既定試験の問題には exam キーを出力しない
# （乙4 の生成物を不変に保つため）。関連試験の問題だけ "exam" を付与する。
DEFAULT_EXAM: str = default_exam_id()


def norm(s: str | None) -> str:
    return (s or "").strip()


def row_exam(row: dict) -> str:
    """行の試験 id。未指定・空は既定試験に正規化。"""
    return norm(row.get("exam")) or DEFAULT_EXAM


def with_exam(obj: dict, exam: str) -> dict:
    """既定以外の試験のみ exam キーを付与（既定試験は出力不変）。"""
    if exam and exam != DEFAULT_EXAM:
        obj["exam"] = exam
    return obj


def build_plain_text(row: dict) -> str:
    parts: list[str] = []
    stem = norm(row.get("stem"))
    preamble = norm(row.get("preamble"))
    if stem:
        parts.append(stem)
    if preamble:
        parts.append(preamble)
    for lab, key in LABELS:
        t = norm(row.get(key))
        if t:
            parts.append(f"{lab}　{t}")
    return "\n\n".join(parts) if parts else "（問題文なし）"


def parse_correct(raw: str, *, max_choice: int) -> int | None:
    return parse_correct_js_index(
        raw, extended=extended_correct_answers(), max_choice=max_choice
    )


def row_to_obj(row: dict, line_no: int) -> dict | None:
    if norm(row.get("is_invalidated", "")).upper() == "TRUE":
        return None
    year = int(row["exam_year"])
    qno = int(row["question_no"])
    cat = norm(row.get("category"))
    field = CATEGORY_TO_FIELD.get(cat)
    if not field:
        raise ValueError(f"line {line_no}: 未対応の category={cat!r}")

    opts = collect_choice_texts(row)
    min_choices = 2 if extended_correct_answers() else 4
    if len(opts) < min_choices:
        raise ValueError(f"line {line_no}: 選択肢欠け year={year} no={qno}")
    max_choice = len(opts)

    inv = norm(row.get("is_invalidated", "")).upper() == "TRUE"
    cor_raw = norm(row.get("correct"))
    cor = parse_correct(cor_raw, max_choice=max_choice)
    if cor is None and not inv:
        if extended_correct_answers() and is_valid_correct(cor_raw, max_choice=max_choice):
            return None
        raise ValueError(f"line {line_no}: 正答なし year={year} no={qno}")

    text = build_plain_text(row)
    exp = norm(row.get("explanation")) or "（解説は未入力です。）"
    page = past_page_dict(row, line_no)
    exp_html = build_explanation_html(page, row)

    qid = year * 100 + qno
    return with_exam({
        "id": qid,
        "year": year,
        "num": qno,
        "field": field,
        "text": text,
        "opts": opts,
        "ans": 0 if cor is None else cor,
        "exp": exp,
        "expHtml": exp_html,
    }, row_exam(row))


def level_from_tags(tags: str) -> int:
    m = re.search(r"level(\d)", norm(tags))
    if m:
        lv = int(m.group(1))
        if lv in (1, 2, 3):
            return lv
    return 1


# tags 5列目に入る難易度ラベル（標準/応用/難関）。UI の★段階へも対応させる。
DIFF_TIERS = ("標準", "応用", "難関")


def diff_tier_from_tags(tags: str) -> str:
    parts = [p.strip() for p in norm(tags).split(";")]
    if len(parts) >= 5 and parts[4] in DIFF_TIERS:
        return parts[4]
    return ""


def practice_exp_fields(row: dict, line_no: int) -> tuple[str, str]:
    """SPA 用: プレーンテキスト（短い要約）と構造化 HTML 解説。"""
    page = practice_page_dict(row, line_no)
    page_ext = {**page, "year": 0, "is_invalidated": False, "is_exempt": False}
    exp_html = build_explanation_html(page_ext, row)
    exp_plain = (
        norm(row.get("explanation_summary"))
        or _o4_explanation_lead(norm(row.get("explanation")))
        or "（解説は未入力です。）"
    )
    return exp_plain, exp_html


def practice_row_to_obj(row: dict, line_no: int) -> dict | None:
    """実践演習 CSV（exam_year なし）。year は常に PRACTICE_POOL_YEAR。"""
    if norm(row.get("is_invalidated", "")).upper() == "TRUE":
        return None
    qno = int(row["question_no"])
    cat = norm(row.get("category"))
    field = CATEGORY_TO_FIELD.get(cat)
    if not field:
        raise ValueError(f"practice_questions.csv line {line_no}: 未対応の category={cat!r}")

    opts = collect_choice_texts(row)
    min_choices = 2 if extended_correct_answers() else 4
    if len(opts) < min_choices:
        raise ValueError(f"practice_questions.csv line {line_no}: 選択肢欠け no={qno}")
    max_choice = len(opts)

    cor_raw = norm(row.get("correct"))
    cor = parse_correct(cor_raw, max_choice=max_choice)
    if cor is None:
        if extended_correct_answers() and is_valid_correct(cor_raw, max_choice=max_choice):
            return None
        raise ValueError(f"practice_questions.csv line {line_no}: 正答なし no={qno}")

    text = build_plain_text(row)
    exp, exp_html = practice_exp_fields(row, line_no)
    qid = PRACTICE_ID_BASE + qno
    return with_exam({
        "id": qid,
        "year": PRACTICE_POOL_YEAR,
        "num": qno,
        "field": field,
        "text": text,
        "opts": opts,
        "ans": 0 if cor is None else cor,
        "exp": exp,
        "expHtml": exp_html,
        "level": level_from_tags(row.get("tags", "")),
        "diff": diff_tier_from_tags(row.get("tags", "")),
        "publicPath": f"q/practice/p{qno:03d}/index.html",
    }, row_exam(row))


def load_practice_questions() -> list[dict]:
    if not PRACTICE_CSV.is_file():
        return []
    text = PRACTICE_CSV.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    out: list[dict] = []
    for i, row in enumerate(rows, start=2):
        o = practice_row_to_obj(row, i)
        if o is None:
            continue
        out.append(o)
    return out


def load_related_questions() -> list[dict]:
    """関連試験（exam 列で丙種/甲種…）の問題を実践演習形式で読み込む。
    乙4 の静的ページは生成せず、SPA のプールにだけ載せる（id は衝突回避のため基点でずらす）。"""
    if not RELATED_CSV.is_file():
        return []
    text = RELATED_CSV.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    out: list[dict] = []
    seen_ids: set[int] = set()
    for i, row in enumerate(rows, start=2):
        exam = row_exam(row)
        if exam == DEFAULT_EXAM:
            raise ValueError(
                f"related_exam_questions.csv line {i}: exam 列は関連試験（既定={DEFAULT_EXAM!r} 以外）にしてください"
            )
        obj = practice_row_to_obj(row, i)
        if obj is None:
            continue
        # 実践演習の静的ページには載せないので publicPath は付けない。
        obj.pop("publicPath", None)
        # id を関連試験用の基点でずらし、乙4 プールと絶対に衝突させない。
        base = RELATED_ID_BASE + RELATED_EXAM_ORDER.index(exam) * 1_000_000 \
            if exam in RELATED_EXAM_ORDER else RELATED_ID_BASE + 900_000
        qno = int(row["question_no"])
        qid = base + qno
        if qid in seen_ids:
            raise ValueError(f"related_exam_questions.csv line {i}: id 衝突 exam={exam} no={qno}")
        seen_ids.add(qid)
        obj["id"] = qid
        obj["exam"] = exam
        out.append(obj)
    return out


def write_practice_js(practice_objs: list[dict], related_objs: list[dict] | None = None) -> None:
    """index.html の実践演習 UI 用データを出力する。
    related_objs（関連試験）はプールには載せるが、乙4 向けの掲載数カウントには含めない。"""
    related_objs = related_objs or []
    by_level: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    for obj in list(practice_objs) + list(related_objs):
        q = dict(obj)
        lv = int(q.pop("level", 1))
        if lv not in by_level:
            lv = 1
        by_level[lv].append(q)
    lines = [
        "/* AUTO-GENERATED by tools/csv_to_exam_site_past_js.py — data/practice_questions.csv / data/related_exam_questions.csv を編集し再生成 */",
        f"const CSV_IMPORTED_PRACTICE_QUESTION_COUNT = {len(practice_objs)};",
        "const PRACTICE_QUESTIONS = " + json.dumps(by_level, ensure_ascii=False, indent=2) + ";",
    ]
    payload = "\n".join(lines) + "\n"
    OUT_PRACTICE_JS.write_text(payload, encoding="utf-8")


def main() -> int:
    if not DATA_CSV.is_file():
        print(f"入力がありません: {DATA_CSV}", file=sys.stderr)
        return 1
    text = DATA_CSV.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    objs: list[dict] = []
    year_labels: dict[int, str] = {}
    for i, row in enumerate(rows, start=2):
        o = row_to_obj(row, i)
        if o is None:
            continue
        objs.append(o)
        y = o["year"]
        wl = norm(row.get("exam_wareki"))
        if y not in year_labels:
            year_labels[y] = f"{y}年"

    practice_objs = load_practice_questions()
    related_objs = load_related_questions()
    write_practice_js(practice_objs, related_objs)
    practice_years = [PRACTICE_POOL_YEAR] if practice_objs else []

    lines = [
        "// AUTO-GENERATED by tools/csv_to_exam_site_past_js.py — "
        "data/past_questions.csv を編集し再生成（実践演習は exam-site-data-practice.js）",
        f"const CSV_IMPORTED_PAST_YEAR_COUNT = {len(year_labels)};",
        "const CSV_IMPORTED_YEAR_LABELS = " + json.dumps(year_labels, ensure_ascii=False) + ";",
        "const CSV_IMPORTED_PRACTICE_POOL_YEARS = " + json.dumps(practice_years, ensure_ascii=False) + ";",
        "const CSV_IMPORTED_QUESTIONS = [",
    ]
    for o in objs:
        lines.append("  " + json.dumps(o, ensure_ascii=False) + ",")
    lines.append("];")
    lines.append("")
    lines.append("if (typeof applyCsvImportedQuestions === 'function') {")
    lines.append("  applyCsvImportedQuestions();")
    lines.append("}")
    lines.append("")

    payload = "\n".join(lines)
    OUT_JS.write_text(payload, encoding="utf-8")
    print(
        f"Wrote {OUT_JS} (過去問 {len(objs)} 問, 実践演習 {len(practice_objs)} 問, "
        f"関連試験 {len(related_objs)} 問, 年度ラベル {len(year_labels)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
