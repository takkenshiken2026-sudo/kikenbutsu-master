#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語詳細記事の手直し優先度チェック（8段階）。"""

from __future__ import annotations

import re
from dataclasses import dataclass

FAQ_HUB_RE = re.compile(
    r"【[1-4]】|compare|numbersページ|numbers|観点[A-D]|補足\d+-\d+|"
    r"試験要項の最新版も確認|関連ハブページ|過去問形式を記録|"
    r"compare表|弱点論点は比較表"
)

GRAMMAR_GLITCH_RE = re.compile(
    r"。{2,}|です。です|である。である|がが|をを|のの|てて|"
    r"試験では、試験では|また、また、|誤り。誤り。"
)

GENERIC_HEADING_RE = re.compile(
    r"【試験で問われる型】|【現場・実務のイメージ】|【整理のコツ】|"
    r"【ひっかけ対策】|【復習】|【覚え方】|【記入】"
)

PAST_EXAM_VAGUE_RE = re.compile(r"（過去問で要注意）|過去問で要注意")

LEGAL_SPECIFIC_RE = re.compile(r"第\d+条|別表第?\d+|施行令|政令第?\d+")

CLASS_TABLE_TERMS = frozenset(
    {
        "第1類危険物",
        "第2類危険物",
        "第3類危険物",
        "第4類危険物",
        "第5類危険物",
        "第6類危険物",
        "危険物の分類",
        "危険物の分類表",
        "特殊引火物",
        "第一石油類",
        "第二石油類",
        "第三石油類",
        "第四石油類",
    }
)

CHECK_LABELS: tuple[str, ...] = (
    "faq_hub_remnants",
    "grammar_broken",
    "legal_vague",
    "needs_class_table",
    "duplicate_text",
    "generic_headings",
    "example_unnatural",
    "past_exam_vague",
)


def norm(value: object) -> str:
    return str(value or "").strip()


def faq_blob(row: dict[str, str]) -> str:
    parts: list[str] = []
    for n in range(1, 5):
        parts.append(norm(row.get(f"faq_{n}_question")))
        parts.append(norm(row.get(f"faq_{n}_answer")))
    return "\n".join(parts)


def combined_text(row: dict[str, str]) -> str:
    cols = (
        "short_def",
        "definition",
        "article_lead",
        "term_detail_body",
        "explanation",
        "common_mistakes",
        "memory_tip",
        "example_question",
        "example_answer",
        "legal_basis",
    )
    return "\n".join(norm(row.get(c)) for c in cols) + "\n" + faq_blob(row)


@dataclass
class RemediationChecks:
    faq_hub_remnants: bool = False
    grammar_broken: bool = False
    legal_vague: bool = False
    needs_class_table: bool = False
    duplicate_text: bool = False
    generic_headings: bool = False
    example_unnatural: bool = False
    past_exam_vague: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {label: getattr(self, label) for label in CHECK_LABELS}

    def priority_score(self) -> int:
        weights = (8, 7, 6, 5, 4, 3, 2, 1)
        return sum(w for w, label in zip(weights, CHECK_LABELS) if getattr(self, label))

    def failing_labels(self) -> list[str]:
        return [label for label in CHECK_LABELS if getattr(self, label)]


def _duplicate_paragraphs(text: str) -> bool:
    paras = [p.strip() for p in re.split(r"\n{2,}", norm(text)) if p.strip()]
    if len(paras) < 2:
        return False
    keys = [re.sub(r"\s+", "", p) for p in paras]
    return len(keys) != len(set(keys))


def _example_unnatural(row: dict[str, str]) -> bool:
    q = norm(row.get("example_question"))
    if not q:
        return True
    if "について、「" in q and ("正しい" in q or "適切" in q):
        return False
    return not re.search(r"[。?？]$", q)


def _needs_class_table(term: str, row: dict[str, str]) -> bool:
    if term in CLASS_TABLE_TERMS or "第" in term and "類" in term:
        body = norm(row.get("term_detail_body"))
        if "|" in body and "第" in body:
            return False
        if "正式名称" in body and "代表" in body:
            return False
        return True
    return False


def _legal_vague(row: dict[str, str]) -> bool:
    legal = norm(row.get("legal_basis"))
    if not legal:
        return False
    if LEGAL_SPECIFIC_RE.search(legal):
        return False
    if legal in {"消防法", "危険物の規制に関する政令", "危険物の規制に関する政令;消防法"}:
        return True
    return len(legal) < 20 and "第" not in legal


def audit_remediation_row(row: dict[str, str]) -> RemediationChecks:
    term = norm(row.get("term"))
    text = combined_text(row)
    faq = faq_blob(row)
    body = norm(row.get("term_detail_body"))

    return RemediationChecks(
        faq_hub_remnants=bool(FAQ_HUB_RE.search(faq)),
        grammar_broken=bool(GRAMMAR_GLITCH_RE.search(text)),
        legal_vague=_legal_vague(row),
        needs_class_table=_needs_class_table(term, row),
        duplicate_text=_duplicate_paragraphs(body) or _duplicate_paragraphs(faq),
        generic_headings=bool(GENERIC_HEADING_RE.search(text)),
        example_unnatural=_example_unnatural(row),
        past_exam_vague=bool(PAST_EXAM_VAGUE_RE.search(text)),
    )
