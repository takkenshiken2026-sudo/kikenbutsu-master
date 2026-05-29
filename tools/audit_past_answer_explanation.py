#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""past_questions.csv の正答と解説の整合性を検証する。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_past_question_pages import page_dict
from tools.q_explanation import (
    build_explanation_html,
    is_find_false_question,
    norm,
    parse_explanation_choices,
    question_ask_mode,
    resolve_wrong_choice_note,
)

DATA_CSV = ROOT / "data" / "past_questions.csv"


def _wrong_number_in_text(text: str, correct: int) -> list[str]:
    issues: list[str] = []
    if not text:
        return issues
    for m in re.finditer(r"正解(?:は|の)?\s*[（(](\d+)[）)]", text):
        n = int(m.group(1))
        if n != correct:
            issues.append(f"解説が正解=（{n}）と記述（CSV正答={correct}）")
    for m in re.finditer(r"正答(?:は|の)?\s*[（(](\d+)[）)]", text):
        n = int(m.group(1))
        if n != correct and not is_find_false_question(text):
            issues.append(f"解説が正答=（{n}）と記述（CSV正答={correct}）")
    return issues


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def _wrong_note_from_html(html: str, choice_num: int) -> str:
    wrong_part = html.split("他の選択肢", 1)[-1] if "他の選択肢" in html else ""
    marker = f'q-exp-choice-num">（{choice_num}）'
    pos = wrong_part.find(marker)
    if pos < 0:
        return ""
    block = wrong_part[pos : pos + 800]
    m = re.search(r'q-exp-choice-note">(.*?)</p>', block, re.DOTALL)
    if not m:
        return ""
    return _strip_html(m.group(1))


def audit_row(row: dict, line_no: int) -> list[str]:
    try:
        page = page_dict(row, line_no)
    except ValueError as exc:
        return [str(exc)]

    correct = page.get("correct")
    if page.get("is_invalidated") or correct is None:
        return []

    qid = f"{page['year']}-{page['qno']:02d}"
    stem = page["stem_plain"]
    issues: list[str] = []

    for field in ("explanation", "explanation_summary", "explanation_correct"):
        for msg in _wrong_number_in_text(norm(row.get(field)), correct):
            issues.append(f"{qid}: {field}: {msg}")

    parsed = parse_explanation_choices(norm(row.get("explanation_choices")))
    if correct in parsed:
        note = parsed[correct]
        if re.search(r"誤り|正しくない|不正解|不適切|該当しない", note):
            if not re.search(r"正答ではありません|正解ではありません|本問の正答では", note):
                issues.append(
                    f"{qid}: explanation_choices: 正答肢（{correct}）を誤りと記述"
                )

    html = build_explanation_html(page, row)
    wrong_nums = [
        int(n)
        for n in re.findall(r'q-exp-choice-num">（(\d+)）', html.split("他の選択肢", 1)[-1])
    ]
    if correct in wrong_nums:
        issues.append(f"{qid}: rendered: 正答（{correct}）が「他の選択肢」に表示")

    if not is_find_false_question(stem):
        m = re.search(
            r"正解の理由</h3>\s*(?:<p class=\"q-exp-mode-note\">.*?</p>\s*)?"
            r"<p>(.*?)</p>\s*<p class=\"q-exp-correct-opt\"",
            html,
            re.DOTALL,
        )
        if m:
            reason = re.sub(r"<[^>]+>", "", m.group(1))
            if re.search(rf"[（(]{correct}[）)]\s*(?:は|も)?誤り", reason):
                issues.append(
                    f"{qid}: rendered: 正答（{correct}）を誤りと記述（誤り選択問題以外）"
                )

    if is_find_false_question(stem):
        if "q-exp-mode-note" not in html:
            issues.append(f"{qid}: rendered: 誤り選択問題なのに設問形式の注記がない")
    elif question_ask_mode(stem) == "least_appropriate" and "最も適切でない" in html:
        issues.append(f"{qid}: rendered: 「最も適切でない」テンプレが誤用")

    for num, csv_note in parsed.items():
        if num == correct or not csv_note:
            continue
        rendered_note = _wrong_note_from_html(html, num)
        if not rendered_note:
            issues.append(f"{qid}: explanation_choices: （{num}）の解説が HTML にない")
            continue
        resolved = resolve_wrong_choice_note(
            page,
            num,
            page["opts"][num - 1],
            row,
            csv_note=csv_note,
        )
        if resolved != csv_note:
            issues.append(
                f"{qid}: explanation_choices: （{num}）の CSV 解説が resolve で上書き"
            )

    return issues


def main() -> int:
    csv_path = DATA_CSV
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])

    all_issues: list[str] = []
    with csv_path.open(encoding="utf-8") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            all_issues.extend(audit_row(row, line_no))

    if all_issues:
        print(f"audit_past_answer_explanation: {len(all_issues)} 件の不整合", file=sys.stderr)
        for item in all_issues:
            print(item, file=sys.stderr)
        return 1

    print("audit_past_answer_explanation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
