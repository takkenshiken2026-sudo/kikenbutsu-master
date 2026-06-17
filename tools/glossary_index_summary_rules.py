#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語一覧（terms/index）向け index_summary 列の品質・オリジナル性ルール."""

from __future__ import annotations

import re
from dataclasses import dataclass

from tools.editorial_quality import (
    EDITORIAL_BOILERPLATE_PHRASES,
    EDITORIAL_GENERIC_PHRASES,
    concreteness_issues,
    placeholder_issues,
)

INDEX_SUMMARY_MIN_LEN = 100
INDEX_SUMMARY_MAX_LEN = 150
INDEX_SUMMARY_COPY_RATIO = 0.70
INDEX_SUMMARY_CROSS_SIMILARITY = 0.87
INDEX_SUMMARY_BUILD_SIMILARITY = 0.72
INDEX_SUMMARY_PREFIX_DUP_LEN = 50
INDEX_SUMMARY_MIN_CONTIGUOUS_COPY = 20

COPY_SOURCE_COLUMNS: tuple[str, ...] = (
    "definition",
    "faq_1_answer",
    "article_lead",
)

INDEX_SUMMARY_FORBIDDEN_FRAGMENTS: tuple[str, ...] = (
    "付箋に書き",
    "演習で出たら即このページへ",
    "【覚え方】",
    "【記入】",
    "差し替えてください",
)

_INDEX_SUMMARY_CROSS_STRIP: tuple[str, ...] = (
    "試験では",
    "根拠法令は",
    "乙4では",
    "が論点になります",
    "論点になります",
    "一覧では",
    "の定義確認が定番です",
    "定義の言い換えと例外条件の確認が定番です",
    "分野で押さえる用語です",
    "試験に出やすい重要語です",
    "試験での確認ポイント",
    "が重要です",
    "との違いも確認します",
    "過去問では正しい説明",
)


def norm(value: object) -> str:
    return str(value or "").strip()


def normalize_key(text: str) -> str:
    return re.sub(r"\s+", "", norm(text))


def substantive_key(text: str) -> str:
    key = normalize_key(text)
    for phrase in _INDEX_SUMMARY_CROSS_STRIP:
        key = key.replace(phrase, "")
    return key


def similar_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    common = sum(1 for ch in a if ch in b)
    return common / max(len(a), len(b))


def cross_similar_ratio(a: str, b: str) -> float:
    """語間重複判定用（一覧定型句を除いた類似度）。"""
    return similar_ratio(substantive_key(a), substantive_key(b))


def longest_contiguous_copy(summary: str, source: str) -> int:
    s = normalize_key(summary)
    src = normalize_key(source)
    if not s or not src:
        return 0
    best = 0
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            chunk = s[i:j]
            if len(chunk) <= best:
                continue
            if chunk in src:
                best = len(chunk)
    return best


def is_likely_copy(summary: str, source: str) -> bool:
    s = normalize_key(summary)
    src = normalize_key(source)
    if not s or not src:
        return False
    if s == src:
        return True
    if len(s) <= len(src) and s in src:
        return True
    if len(src) >= len(s) and src in s and len(src) / len(s) > 0.55:
        return True
    contiguous = longest_contiguous_copy(summary, source)
    if contiguous >= 40 and contiguous / len(s) > 0.45:
        return True
    if contiguous >= INDEX_SUMMARY_MIN_CONTIGUOUS_COPY and similar_ratio(s, src) > INDEX_SUMMARY_COPY_RATIO:
        return True
    return similar_ratio(s, src) > 0.85


def copy_sources(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        norm(row.get(col))
        for col in (*COPY_SOURCE_COLUMNS, "short_def")
        if norm(row.get(col))
    )


def passes_index_copy_check(text: str, row: dict[str, str]) -> bool:
    summary = norm(text)
    if not summary:
        return False
    return not any(is_likely_copy(summary, src) for src in copy_sources(row))


@dataclass(frozen=True)
class IndexSummaryIssue:
    level: str  # ERROR | WARN
    message: str
    term: str = ""
    column: str = "index_summary"


def check_index_summary_row(row: dict[str, str]) -> list[IndexSummaryIssue]:
    """1行分。未記入は WARN（移行期）。記入済みは長さ・コピー・定型を検査。"""
    term = norm(row.get("term"))
    text = norm(row.get("index_summary"))
    issues: list[IndexSummaryIssue] = []

    if not text:
        issues.append(
            IndexSummaryIssue(
                "WARN",
                "index_summary 未記入（一覧はレガシー抜粋にフォールバック）",
                term=term,
            )
        )
        return issues

    n = len(text)
    if n < INDEX_SUMMARY_MIN_LEN:
        issues.append(
            IndexSummaryIssue(
                "ERROR",
                f"index_summary は {INDEX_SUMMARY_MIN_LEN} 文字以上にしてください"
                f"（現在 {n} 文字）",
                term=term,
            )
        )
    elif n > INDEX_SUMMARY_MAX_LEN:
        issues.append(
            IndexSummaryIssue(
                "ERROR",
                f"index_summary は {INDEX_SUMMARY_MAX_LEN} 文字以下にしてください"
                f"（現在 {n} 文字）",
                term=term,
            )
        )

    if term and term not in text:
        issues.append(
            IndexSummaryIssue(
                "WARN",
                f"index_summary に用語名 {term!r} を含めると一覧で意味が伝わりやすくなります",
                term=term,
            )
        )

    for issue in placeholder_issues(text, "index_summary"):
        issues.append(IndexSummaryIssue(issue.level, issue.message, term=term))

    for phrase in EDITORIAL_BOILERPLATE_PHRASES:
        if phrase in text:
            issues.append(
                IndexSummaryIssue(
                    "ERROR",
                    f"index_summary に機械的な共通文が含まれています: {phrase[:40]}…",
                    term=term,
                )
            )
            break

    for phrase in INDEX_SUMMARY_FORBIDDEN_FRAGMENTS:
        if phrase in text:
            issues.append(
                IndexSummaryIssue(
                    "ERROR",
                    f"index_summary に一覧向けでない定型が含まれています: {phrase}",
                    term=term,
                )
            )

    for phrase in EDITORIAL_GENERIC_PHRASES:
        if phrase in text:
            issues.append(
                IndexSummaryIssue(
                    "WARN",
                    f"index_summary が汎用的すぎる可能性があります: {phrase[:32]}…",
                    term=term,
                )
            )

    for col in COPY_SOURCE_COLUMNS:
        source = norm(row.get(col))
        if source and is_likely_copy(text, source):
            issues.append(
                IndexSummaryIssue(
                    "ERROR",
                    f"index_summary が {col} の抜粋・言い換え不足に見えます。"
                    "一覧専用のオリジナル文（100〜150字）に書き直してください",
                    term=term,
                )
            )
            break

    importance = norm(row.get("importance"))
    if importance in {"A", "S"}:
        for issue in concreteness_issues(text, "index_summary"):
            issues.append(IndexSummaryIssue(issue.level, issue.message, term=term))

    return issues


def audit_index_summary_cross_rows(rows: list[dict[str, str]]) -> list[IndexSummaryIssue]:
    """語間の完全一致・先頭一致・高類似を検出（記入済み行のみ）。"""
    filled: list[tuple[str, str]] = []
    for row in rows:
        term = norm(row.get("term"))
        text = norm(row.get("index_summary"))
        if term and text:
            filled.append((term, text))

    issues: list[IndexSummaryIssue] = []

    by_exact: dict[str, list[str]] = {}
    for term, text in filled:
        by_exact.setdefault(normalize_key(text), []).append(term)
    for key, terms in by_exact.items():
        if len(terms) < 2 or len(key) < INDEX_SUMMARY_MIN_LEN:
            continue
        issues.append(
            IndexSummaryIssue(
                "ERROR",
                f"index_summary が {len(terms)} 語で完全一致しています"
                f"（{', '.join(terms[:5])}{'…' if len(terms) > 5 else ''}）。"
                "各用語ごとにオリジナル文を書き分けてください",
                term=terms[0],
            )
        )

    by_prefix: dict[str, list[str]] = {}
    for term, text in filled:
        prefix = normalize_key(text)[:INDEX_SUMMARY_PREFIX_DUP_LEN]
        if len(prefix) >= INDEX_SUMMARY_PREFIX_DUP_LEN:
            by_prefix.setdefault(prefix, []).append(term)
    for prefix, terms in by_prefix.items():
        if len(terms) < 2:
            continue
        issues.append(
            IndexSummaryIssue(
                "ERROR",
                f"index_summary の先頭 {INDEX_SUMMARY_PREFIX_DUP_LEN} 字が"
                f" {len(terms)} 語で同一です（{', '.join(terms[:4])}…）",
                term=terms[0],
            )
        )

    for i, (term_a, text_a) in enumerate(filled):
        key_a = normalize_key(text_a)
        for term_b, text_b in filled[i + 1 :]:
            if term_a == term_b:
                continue
            key_b = normalize_key(text_b)
            if key_a == key_b:
                continue
            if cross_similar_ratio(key_a, key_b) > INDEX_SUMMARY_CROSS_SIMILARITY:
                issues.append(
                    IndexSummaryIssue(
                        "ERROR",
                        f"index_summary が {term_b!r} と高類似です（>{INDEX_SUMMARY_CROSS_SIMILARITY:.0%}）。"
                        "語ごとに独自の論点を入れて書き分けてください",
                        term=term_a,
                    )
                )
                break

    return issues


def index_summary_fill_stats(rows: list[dict[str, str]]) -> tuple[int, int]:
    total = sum(1 for row in rows if norm(row.get("term")))
    filled = sum(
        1
        for row in rows
        if norm(row.get("term")) and norm(row.get("index_summary"))
    )
    return filled, total


def cross_conflicts_incremental(
    term: str,
    summary: str,
    applied: list[tuple[str, str]],
    *,
    max_ratio: float | None = None,
) -> bool:
    """採用済み概要との語間重複（増分 apply 用・O(n)）。"""
    limit = INDEX_SUMMARY_CROSS_SIMILARITY if max_ratio is None else max_ratio
    key = normalize_key(summary)
    if not key:
        return False
    prefix = (
        key[:INDEX_SUMMARY_PREFIX_DUP_LEN]
        if len(key) >= INDEX_SUMMARY_PREFIX_DUP_LEN
        else ""
    )
    for _other_term, other_summary in applied:
        other_key = normalize_key(other_summary)
        if not other_key:
            continue
        if key == other_key and len(key) >= INDEX_SUMMARY_MIN_LEN:
            return True
        if prefix and len(other_key) >= INDEX_SUMMARY_PREFIX_DUP_LEN:
            if other_key[:INDEX_SUMMARY_PREFIX_DUP_LEN] == prefix:
                return True
        if cross_similar_ratio(key, other_key) > limit:
            return True
    return False


def cross_conflicts_with(
    term: str,
    summary: str,
    applied: list[tuple[str, str]],
) -> bool:
    """既に採用済みの概要と語間重複するか（増分 apply 用）。"""
    if not summary:
        return False
    return cross_conflicts_incremental(term, summary, applied)
