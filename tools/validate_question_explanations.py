#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""過去問・実践・一問一答 CSV の解説品質監査（矛盾・重複・デモ行・実践HTML）。"""

from __future__ import annotations

import csv
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.q_content_quality import (  # noqa: E402
    build_ichimon_primary_ids,
    dedupe_prose,
    is_demo_past_question_row,
    is_demo_practice_question_row,
)
from tools.q_explanation import (  # noqa: E402
    _CHOICE_NOTE_MAX_LEN,
    _CHOICE_NOTE_MIN_LEN,
    _CORRECT_REASON_MAX_LEN,
    _CORRECT_REASON_MIN_LEN,
    build_explanation_html,
    build_ichimon_explanation_html,
    norm,
    parse_explanation_choices,
    question_ask_mode,
    _parrots_stem,
)
from tools.site_config import is_template_site, excluded_past_exam_years  # noqa: E402

DATA = ROOT / "data"

_PRACTICE_EXP_FORBIDDEN = (
    "他肢では",
    "本問の正答は",
    "免状の効力・取扱範囲の説明として誤り",
    "分類として誤り",
)


def _strip_exp_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(text)).replace("\n", "").strip()


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _error(msg: str) -> None:
    print(f"[ERROR] {msg}")


def audit_past() -> tuple[int, int]:
    path = DATA / "past_questions.csv"
    if not path.is_file():
        return 0, 0
    errs = warns = 0
    skip_years = excluded_past_exam_years()
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for idx, row in enumerate(rows, start=2):
        if is_demo_past_question_row(row, excluded_exam_years=skip_years):
            warns += 1
            _warn(f"{path.name}:{idx} デモ・サンプル過去問（静的ページ生成対象外）")
            continue
        summary = norm(row.get("explanation_summary"))
        correct = norm(row.get("explanation_correct"))
        if summary and correct and dedupe_prose(summary) == dedupe_prose(correct):
            warns += 1
            _warn(f"{path.name}:{idx} explanation_summary と explanation_correct が同一")
        stem = norm(row.get("stem"))
        if stem and correct and _parrots_stem(stem, correct):
            warns += 1
            _warn(f"{path.name}:{idx} explanation_correct が設問文の言い換え")
        choices = parse_explanation_choices(norm(row.get("explanation_choices")))
        notes = [v for k, v in choices.items() if k != int(row.get("correct") or 0)]
        if len(notes) >= 2 and len(set(notes)) == 1:
            if is_template_site():
                warns += 1
                _warn(f"{path.name}:{idx} 他肢解説が全肢同一")
            else:
                errs += 1
                _error(f"{path.name}:{idx} 他肢解説が全肢同一")
        body = f"{summary} {correct}"
        mode = question_ask_mode(stem)
        if mode == "most_correct" and re.search(r"誤っている|不適切", body):
            warns += 1
            _warn(f"{path.name}:{idx} 正しいもの問題なのに解説に「誤り」表現")
        if mode == "least_appropriate" and re.search(r"正しいものは", body) and "正答" not in body:
            warns += 1
            _warn(f"{path.name}:{idx} 最も不適切問題の解説表現を要確認")
    return errs, warns


def audit_practice() -> tuple[int, int]:
    from tools.build_practice_ichimon_pages import practice_page_dict

    path = DATA / "practice_questions.csv"
    if not path.is_file():
        return 0, 0
    errs = warns = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for idx, row in enumerate(rows, start=2):
        if is_demo_practice_question_row(row):
            warns += 1
            _warn(f"{path.name}:{idx} デモ・テンプレ実践演習（静的ページ生成対象外）")
            continue
        qno = int(row.get("question_no") or idx - 1)
        page = practice_page_dict(row, qno)
        exp_html = build_explanation_html({**page, "year": 0}, row)
        cor_m = re.search(
            r'id="q-exp-correct-h"[^>]*>.*?</h3>\s*<p>(.*?)</p>',
            exp_html,
            re.S,
        )
        if not cor_m:
            errs += 1
            _error(f"{path.name}:{idx} Q{qno} 正解の理由セクションなし")
            continue
        cor = _strip_exp_html(cor_m.group(1))
        wrongs = [
            _strip_exp_html(w)
            for w in re.findall(
                r'class="q-exp-choice-note"[^>]*>(.*?)</',
                exp_html,
                re.S,
            )
        ]
        if not (_CORRECT_REASON_MIN_LEN <= len(cor) <= _CORRECT_REASON_MAX_LEN):
            errs += 1
            _error(
                f"{path.name}:{idx} Q{qno} 正解の理由 {len(cor)}字 "
                f"（{_CORRECT_REASON_MIN_LEN}〜{_CORRECT_REASON_MAX_LEN}字）"
            )
        for wi, note in enumerate(wrongs, start=1):
            if not (_CHOICE_NOTE_MIN_LEN <= len(note) <= _CHOICE_NOTE_MAX_LEN):
                errs += 1
                _error(
                    f"{path.name}:{idx} Q{qno} 他肢{wi} {len(note)}字 "
                    f"（{_CHOICE_NOTE_MIN_LEN}〜{_CHOICE_NOTE_MAX_LEN}字）"
                )
        for phrase in _PRACTICE_EXP_FORBIDDEN:
            if phrase in cor or any(phrase in w for w in wrongs):
                errs += 1
                _error(f"{path.name}:{idx} Q{qno} 禁止句「{phrase}」")
    return errs, warns


def _ichimon_judges_statement_wrong(question: str) -> bool:
    """一問一答で「この記述は誤っている」形式（○＝誤りあり、と判定する設問）。"""
    q = norm(question)
    return bool(re.search(r"誤っている|誤りの記述|誤った記述|誤りのある", q))


def audit_ichimon() -> tuple[int, int]:
    path = DATA / "ichimon_questions.csv"
    if not path.is_file():
        return 0, 0
    errs = warns = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    primary = build_ichimon_primary_ids(rows)
    thin_branches = sum(1 for r in rows if norm(r.get("id")) not in primary)
    if thin_branches:
        _warn(
            f"{path.name}: 選択肢枝番の一問一答 {thin_branches} 行は noindex（元問あたり最小枝番のみ index）"
        )
        warns += thin_branches
    for idx, row in enumerate(rows, start=2):
        ans = norm(row.get("answer"))
        summary = norm(row.get("explanation_summary"))
        correct = norm(row.get("explanation_correct"))
        exp = norm(row.get("explanation"))
        is_true = ans in {"○", "O", "o", "true", "TRUE", "1"}
        is_false = ans in {"×", "x", "X", "false", "FALSE", "0"}
        combined = f"{summary} {correct} {exp}"
        if is_true and re.search(r"誤りです|誤った記述|×\s*が正答", combined):
            if not _ichimon_judges_statement_wrong(norm(row.get("question"))):
                errs += 1
                _error(f"{path.name}:{idx} 正答○なのに解説が誤り扱い")
        if is_false and re.search(r"正しい内容です|正当である|○\s*が正答", combined) and "誤" not in summary[:20]:
            errs += 1
            _error(f"{path.name}:{idx} 正答×なのに解説が正しい扱い")
        if summary and correct and dedupe_prose(summary) == dedupe_prose(correct):
            warns += 1
            _warn(f"{path.name}:{idx} explanation_summary と explanation_correct が同一")
    return errs, warns


def audit_ichimon_rendered() -> tuple[int, int]:
    from tools.build_practice_ichimon_pages import ichimon_page_dict

    path = DATA / "ichimon_questions.csv"
    if not path.is_file():
        return 0, 0
    errs = warns = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for idx, row in enumerate(rows, start=2):
        rid = norm(row.get("id"))
        page = ichimon_page_dict(row, idx - 1)
        exp_html = build_ichimon_explanation_html(page, row)
        cor_m = re.search(
            r'id="q-exp-correct-h"[^>]*>.*?</h3>\s*<p>(.*?)</p>',
            exp_html,
            re.S,
        )
        opp_m = re.search(
            r'id="q-exp-opposite-h"[^>]*>.*?</section>',
            exp_html,
            re.S,
        )
        if not cor_m:
            errs += 1
            _error(f"{path.name}:{idx} {rid} 正解の理由なし")
            continue
        cor = _strip_exp_html(cor_m.group(1))
        opp = ""
        if opp_m:
            opp_p = re.search(r"<p>(.*?)</p>", opp_m.group(0), re.S)
            if opp_p:
                opp = _strip_exp_html(opp_p.group(1))
        if not (_CORRECT_REASON_MIN_LEN <= len(cor) <= _CORRECT_REASON_MAX_LEN):
            errs += 1
            _error(
                f"{path.name}:{idx} {rid} 正解の理由 {len(cor)}字 "
                f"（{_CORRECT_REASON_MIN_LEN}〜{_CORRECT_REASON_MAX_LEN}字）"
            )
        if not opp:
            errs += 1
            _error(f"{path.name}:{idx} {rid} 反対側解説なし")
        elif not (_CHOICE_NOTE_MIN_LEN <= len(opp) <= _CHOICE_NOTE_MAX_LEN):
            errs += 1
            _error(
                f"{path.name}:{idx} {rid} 反対側 {len(opp)}字 "
                f"（{_CHOICE_NOTE_MIN_LEN}〜{_CHOICE_NOTE_MAX_LEN}字）"
            )
        ans = norm(row.get("answer"))
        if ans in {"×", "x", "X"} and cor.startswith("正しい"):
            errs += 1
            _error(f"{path.name}:{idx} {rid} 正答×なのに正解理由が「正しい」始まり")
        if ans in {"○", "O", "o"} and cor.startswith("誤り"):
            errs += 1
            _error(f"{path.name}:{idx} {rid} 正答○なのに正解理由が「誤り」始まり")
        for phrase in _PRACTICE_EXP_FORBIDDEN:
            if phrase in cor or phrase in opp:
                errs += 1
                _error(f"{path.name}:{idx} {rid} 禁止句「{phrase}」")
    return errs, warns


def main() -> int:
    total_err = total_warn = 0
    for fn in (audit_past, audit_practice, audit_ichimon, audit_ichimon_rendered):
        e, w = fn()
        total_err += e
        total_warn += w
    print(f"Question explanation audit: {total_err} error(s), {total_warn} warning(s)")
    return 1 if total_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
