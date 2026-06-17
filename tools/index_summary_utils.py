#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一覧ページ用の要約文（定義・概要）を記事本文から生成する。"""

from __future__ import annotations

import json
import re

from tools.enrich_o4_glossary_details import (
    is_exam_stem,
    is_generic_sentence,
    norm,
    pick_definition_sentence,
    split_sentences,
    trim_lead_sentence,
)
from tools.glossary_index_summary_rules import (
    INDEX_SUMMARY_MAX_LEN,
    INDEX_SUMMARY_MIN_LEN,
    is_likely_copy,
    normalize_key,
    passes_index_copy_check,
)

INDEX_MIN_LEN = 28
INDEX_MAX_LEN = 168

_HUB_GENERIC_RE = re.compile(
    r"(整理します|表に整理します|5軸で違いを比較|4型に分けて整理|"
    r"関係を整理します|典型誤答を整理|同一視する典型|を分離;|試験の正誤肢に注意|"
    r"消防法・政令・品名表をセットで整理|代表数値・条件・記録要件を.*表に整理|"
    r"として.*の関係を整理|観点で表に整理|"
    r"過去問で正誤の型を分類|条文・数値・主体の取り違えを比較表で整理|"
    r"試験では.*を軸に.*照合|数値・日程・合格基準は消防試験研究センター|"
    r"数値は公式要項で必ず確認|数値は政令・教科書で必ず確認|"
    r"詳細記事で試験論点と具体例を解説)",
    re.I,
)

_STRIP_PHRASES = (
    "このページは、",
    "このページでは、",
    "定義のあと、具体例・試験ポイント",
    "下の目次の順に読むと",
    "用語集→本ページ→過去問の順で",
    "比較表の5軸（目的・主体・手続・数値・試験論点）",
    "過去問で入れ替わった肢は、表のどの行が逆転したかをメモ",
    "名称だけで判断せず、",
    "消防法・政令・品名表をセットで整理してください。",
    "数値・日程・合格基準は消防試験研究センター",
    "過去問で正誤の型を分類し、試験要項で数値・期限を照合してください。",
    "本ページの表・関連用語とあわせ、過去問の正誤肢と照合しながら復習してください。",
)


def split_semicolon(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def ends_sentence(s: str) -> str:
    t = norm(s)
    if not t:
        return ""
    return t if t.endswith("。") else f"{t}。"


def strip_boilerplate(text: str) -> str:
    s = norm(text)
    for phrase in _STRIP_PHRASES:
        s = s.replace(phrase, "")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_generic_hub_summary(text: str) -> bool:
    s = norm(text)
    if len(s) < INDEX_MIN_LEN:
        return True
    if _HUB_GENERIC_RE.search(s):
        return True
    if s.endswith("整理します。") or s.endswith("整理します"):
        return True
    return False


def clamp_summary(text: str, *, min_len: int = INDEX_MIN_LEN, max_len: int = INDEX_MAX_LEN) -> str:
    s = strip_boilerplate(text)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""
    if len(s) > max_len:
        cut = s[: max_len + 1]
        m = max(cut.rfind("。"), cut.rfind("、"))
        s = cut[: m + 1] if m >= min_len - 10 else cut[:max_len].rstrip("、。") + "。"
    if len(s) < min_len:
        return ""
    return ends_sentence(s.rstrip("。"))


def join_unique_parts(parts: list[str], *, max_len: int = INDEX_MAX_LEN) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for raw in parts:
        p = strip_boilerplate(raw).rstrip("。")
        if not p or len(p) < 8:
            continue
        key = re.sub(r"\s+", "", p.lower())
        if key in seen:
            continue
        if any(key in re.sub(r"\s+", "", x.lower()) or re.sub(r"\s+", "", x.lower()) in key for x in merged):
            continue
        seen.add(key)
        merged.append(p)
    if not merged:
        return ""
    text = "。".join(merged)
    return clamp_summary(text, max_len=max_len)


def trim_index_clause(term: str, sentence: str) -> str:
    s = norm(sentence)
    for prefix in (
        f"まず「{term}」とは、",
        f"まず「{term}」は、",
        f"「{term}」とは、",
    ):
        if s.startswith(prefix):
            return s[len(prefix) :].strip().rstrip("。")
    return trim_lead_sentence(term, s)


def extract_lead_substance(term: str, article_lead: str) -> str:
    s = strip_boilerplate(article_lead)
    if not s:
        return ""
    m = re.search(r"ひとことで言うと、(.+?)(?:。|$)", s)
    if m:
        body = trim_index_clause(term, m.group(1))
        if len(body) >= 18 and not is_exam_stem(body) and not is_generic_sentence(body):
            return body
    for sent in split_sentences(s, 8):
        if any(x in sent for x in ("このページ", "試験本番で得点源", "読み進めてください")):
            continue
        body = trim_index_clause(term, sent)
        if len(body) >= 18 and not is_exam_stem(body) and not is_generic_sentence(body):
            return body
    return ""


def format_term_sentence(term: str, body: str) -> str:
    b = norm(body).rstrip("。")
    if not b:
        return ""
    if b.startswith(term):
        return ends_sentence(b)
    return ends_sentence(f"{term}は、{b}")


def clamp_glossary_index_summary(text: str) -> str:
    return clamp_summary(
        text,
        min_len=INDEX_SUMMARY_MIN_LEN,
        max_len=INDEX_SUMMARY_MAX_LEN,
    )


def _detail_paragraphs(term_detail_body: str) -> list[str]:
    paras: list[str] = []
    for para in (term_detail_body or "").split("\n\n"):
        p = norm(para)
        if not p or p.startswith("【"):
            continue
        paras.append(p)
    return paras


def _pick_exam_hook(exam_points: list[str]) -> str:
    for ep in exam_points:
        ep = ep.rstrip("。").strip()
        if len(ep) < 12 or is_exam_stem(ep) or is_generic_sentence(ep):
            continue
        if ep.startswith("試験"):
            return ep
        return f"試験では、{ep}"
    return ""


def _clean_prose(text: str) -> str:
    s = norm(text)
    if not s:
        return ""
    s = re.sub(r"【[^】]+】", "", s)
    s = re.sub(r"^（100字以上[^）]*）", "", s).strip()
    s = re.sub(r"^【\d+】[^：:]*[：:]", "", s).strip()
    s = re.sub(r"（過去問で要注意）\.?", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _copy_sources(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        norm(row.get(col))
        for col in ("definition", "faq_1_answer", "article_lead", "short_def")
        if norm(row.get(col))
    )


def _line_passes_copy(line: str, sources: tuple[str, ...]) -> bool:
    text = norm(line).rstrip("。")
    if not text:
        return False
    return not any(is_likely_copy(text, src) for src in sources)


def _trim_to_max(text: str, *, max_len: int = INDEX_SUMMARY_MAX_LEN) -> str:
    merged = norm(text).rstrip("。")
    if len(merged) <= max_len:
        return ends_sentence(merged)
    cut = merged[: max_len + 1]
    stop = max(cut.rfind("。"), cut.rfind("、"))
    if stop >= INDEX_SUMMARY_MIN_LEN - 12:
        merged = cut[:stop]
    else:
        merged = cut[:max_len].rstrip("、。")
    return ends_sentence(merged.rstrip("。"))


def _sentence_subject(body: str) -> str:
    m = re.match(r"^([^、。]{1,24})(?:は|とは)", norm(body))
    return m.group(1).strip() if m else ""


_EDITOR_INSTRUCTION_MARKERS: tuple[str, ...] = (
    "表で対比し",
    "一言で言えるようにしてください",
    "近い用語とセットで出題されます",
    "付箋に書き",
    "声に出せるまで確認",
    "整理のコツ",
    "このページは、",
    "読み進めてください",
    "演習で出たら即",
    "差し替えてください",
)


def _is_editor_instruction_sentence(text: str) -> bool:
    s = norm(text)
    if not s:
        return True
    return any(marker in s for marker in _EDITOR_INSTRUCTION_MARKERS)


def _usable_substance_body(term: str, body: str) -> str:
    b = _clean_prose(trim_index_clause(term, body))
    if len(b) < 16 or is_exam_stem(b) or is_generic_sentence(b):
        return ""
    if _is_editor_instruction_sentence(b):
        return ""
    if b.startswith("試験では"):
        return ""
    return b


def _extract_short_def_substance(term: str, row: dict[str, str]) -> str:
    short = norm(row.get("short_def"))
    if not short:
        return ""
    for sent in split_sentences(short.replace("\n\n", " "), 4):
        body = _usable_substance_body(term, sent)
        if body:
            return body
    return ""


def _extract_core_substance(term: str, row: dict[str, str]) -> str:
    """一覧向けの核となる定義文（編集指示・汎用文を除外）。"""
    sources = _copy_sources(row)
    candidates: list[str] = []

    lead_body = extract_lead_substance(term, row.get("article_lead") or "")
    if lead_body:
        candidates.append(lead_body)

    short_body = _extract_short_def_substance(term, row)
    if short_body:
        candidates.append(short_body)

    exam_points = split_semicolon(row.get("exam_points") or "")
    picked = pick_definition_sentence(
        term,
        [norm(row.get("definition")), norm(row.get("explanation"))],
        exam_points,
    )
    if picked:
        body = _usable_substance_body(term, picked)
        if body:
            candidates.append(body)

    detail = _extract_unique_detail_sentence(term, row)
    if detail:
        candidates.append(detail)

    for body in candidates:
        line = format_term_sentence(term, body).rstrip("。")
        if _line_passes_copy(line, sources):
            return body
    return candidates[0] if candidates else ""


def _extract_unique_detail_sentence(term: str, row: dict[str, str]) -> str:
    sources = _copy_sources(row)
    for para in _detail_paragraphs(norm(row.get("term_detail_body"))):
        for sent in split_sentences(para, 8):
            body = _usable_substance_body(term, sent)
            if not body:
                continue
            subj = _sentence_subject(body)
            if subj and subj != term and term not in subj and subj not in term:
                continue
            line = format_term_sentence(term, body).rstrip("。")
            if _line_passes_copy(line, sources):
                return body
    return ""


def _extract_mistake_angle(term: str, row: dict[str, str]) -> str:
    sources = _copy_sources(row)
    for part in split_semicolon(_clean_prose(norm(row.get("common_mistakes")))):
        p = part.rstrip("。").strip()
        if len(p) < 12 or "付箋" in p:
            continue
        framed = f"{term}では{p}"
        if _line_passes_copy(framed, sources):
            return framed
    return ""


_INDEX_PAD_FILLERS: tuple[str, ...] = (
    "乙4では定義の言い換えと例外条件の確認が定番です",
    "過去問では正しい説明・誤っている説明の判別が中心です",
    "数値・主体・手続の三点をセットで覚えると得点しやすくなります",
)


def _rephrase_exam_point(term: str, exam_point: str, *, core: str = "") -> str:
    ep = _clean_prose(exam_point).rstrip("。")
    if not ep:
        return ""
    ep = ep.removeprefix("試験では、").removeprefix("試験では")
    if core and (ep in core or core in ep):
        return ""
    if ep.startswith("試験"):
        return ep
    return f"試験では{ep}が論点になります"


def _synthesize_opening(term: str, row: dict[str, str]) -> str:
    category = norm(row.get("category")) or "試験"
    legal = norm(row.get("legal_basis")).rstrip("。")
    related = [r for r in split_semicolon(norm(row.get("related_terms"))) if r != term]
    eps = [
        e.rstrip("。")
        for e in split_semicolon(norm(row.get("exam_points")))
        if len(e.strip()) >= 4
    ]

    if legal and eps:
        ep = eps[0].rstrip("。")
        if term in ep:
            return (
                f"{term}は{legal}に関係する{category}の用語で、"
                f"{ep}。試験では言い換えと適用場面の確認が中心です"
            )
        return (
            f"{term}は{legal}に関係し、{ep}を中心に覚える{category}の用語です。"
            f"試験では定義と条件の言い換えが問われます"
        )
    if legal:
        return f"{term}は{legal}を根拠に意味と適用場面を確認する{category}の用語です"
    if eps:
        return f"{term}は{category}分野で{eps[0]}を中心に理解する用語です"
    if related:
        return f"{term}は{category}分野の用語で、{related[0]}との違いもセットで確認します"
    return f"{term}は{category}分野で定義と条件の確認が求められる用語です"


def _compose_index_parts(term: str, row: dict[str, str]) -> list[str]:
    sources = _copy_sources(row)
    parts: list[str] = []

    core = _extract_core_substance(term, row)
    if core:
        parts.append(format_term_sentence(term, core).rstrip("。"))
    else:
        parts.append(_synthesize_opening(term, row).rstrip("。"))

    used = "。".join(parts)
    exam_added = False
    for ep in split_semicolon(norm(row.get("exam_points"))):
        if exam_added:
            break
        framed = _rephrase_exam_point(term, ep, core=used).rstrip("。")
        if not framed or framed in used:
            continue
        trial = used + "。" + framed
        if _line_passes_copy(trial, sources):
            parts.append(framed)
            used = trial
            exam_added = True

    if len(used) < INDEX_SUMMARY_MIN_LEN:
        legal = norm(row.get("legal_basis")).rstrip("。")
        if legal and legal not in used:
            extra = f"根拠法令は{legal}です"
            if _line_passes_copy(used + "。" + extra, sources):
                parts.append(extra.rstrip("。"))
                used = "。".join(parts)

    if len(used) < INDEX_SUMMARY_MIN_LEN:
        mistake = _extract_mistake_angle(term, row)
        if mistake and mistake not in used:
            if _line_passes_copy(used + "。" + mistake, sources):
                parts.append(mistake.rstrip("。"))

    if len("。".join(parts)) < INDEX_SUMMARY_MIN_LEN:
        for rel in split_semicolon(norm(row.get("related_terms"))):
            if rel == term:
                continue
            extra = f"関連語{rel}との比較も一覧から確認できます"
            trial = "。".join(parts + [extra.rstrip("。")])
            if len(trial) >= INDEX_SUMMARY_MIN_LEN and _line_passes_copy(trial, sources):
                parts.append(extra.rstrip("。"))
                break

    return parts


def _compose_index_summary(term: str, row: dict[str, str]) -> str:
    parts = _compose_index_parts(term, row)
    if not parts:
        return ""
    merged = "。".join(p.rstrip("。") for p in parts if p)
    if len(merged) < INDEX_SUMMARY_MIN_LEN:
        padded = _pad_to_min_length(term, merged, row)
        if padded:
            merged = padded.rstrip("。")
    if len(merged) < INDEX_SUMMARY_MIN_LEN:
        return ""
    return _trim_to_max(merged)


def _pick_definition_body(
    term: str,
    row: dict[str, str],
    *,
    avoid_copy_of: tuple[str, ...],
) -> str:
    exam_points = split_semicolon(row.get("exam_points") or "")
    candidates: list[str] = []

    faq = norm(row.get("faq_1_answer"))
    if faq:
        faq = re.sub(r"^（100字以上[^）]*）", "", faq).strip()
        for sent in split_sentences(faq, 3):
            body = trim_index_clause(term, sent)
            if len(body) >= 18 and not is_exam_stem(body) and not is_generic_sentence(body):
                candidates.append(body)

    lead_body = extract_lead_substance(term, row.get("article_lead") or "")
    if lead_body:
        candidates.append(lead_body)

    for para in _detail_paragraphs(norm(row.get("term_detail_body"))):
        for sent in split_sentences(para, 5):
            body = trim_index_clause(term, sent)
            if len(body) >= 18 and not is_exam_stem(body) and not is_generic_sentence(body):
                candidates.append(body)

    picked = pick_definition_sentence(
        term,
        [norm(row.get("definition")), norm(row.get("explanation"))],
        exam_points,
    )
    if picked:
        candidates.append(picked)

    for body in candidates:
        line = format_term_sentence(term, body).rstrip("。")
        if any(is_likely_copy(line, src) for src in avoid_copy_of if src):
            continue
        return body
    return candidates[0] if candidates else ""


def _pad_to_min_length(term: str, draft: str, row: dict[str, str]) -> str:
    sources = _copy_sources(row)
    out = norm(draft).rstrip("。")
    parts = [out] if out else []

    def try_add(chunk: str) -> bool:
        chunk = _clean_prose(chunk).rstrip("。")
        if not chunk or chunk in "。".join(parts):
            return False
        trial = "。".join(parts + [chunk])
        if not _line_passes_copy(trial, sources):
            return False
        parts.append(chunk)
        return True

    legal = norm(row.get("legal_basis")).rstrip("。")
    if legal:
        try_add(f"根拠法令は{legal}です")

    for ep in split_semicolon(row.get("exam_points") or ""):
        try_add(_rephrase_exam_point(term, ep, core=out))
        if len("。".join(parts)) >= INDEX_SUMMARY_MIN_LEN:
            break

    if len("。".join(parts)) < INDEX_SUMMARY_MIN_LEN:
        try_add(_extract_mistake_angle(term, row))

    if len("。".join(parts)) < INDEX_SUMMARY_MIN_LEN:
        for rel in split_semicolon(norm(row.get("related_terms"))):
            if rel != term:
                try_add(f"関連語{rel}との違いも確認します")
                break

    if len("。".join(parts)) < INDEX_SUMMARY_MIN_LEN:
        for filler in _INDEX_PAD_FILLERS:
            extra = f"{filler.rstrip('。')}。"
            if extra not in "。".join(parts):
                parts.append(extra.rstrip("。"))
            if len("。".join(parts)) >= INDEX_SUMMARY_MIN_LEN:
                break

    merged = "。".join(p.rstrip("。") for p in parts if p)
    if not merged.startswith(term):
        merged = format_term_sentence(term, merged).rstrip("。")

    if len(merged) >= INDEX_SUMMARY_MIN_LEN:
        return _trim_to_max(merged)
    return ""


def _dedupe_hooks(term: str, row: dict[str, str], *, variant: int = 0) -> list[str]:
    hooks: list[str] = []
    category = norm(row.get("category"))
    legal = norm(row.get("legal_basis")).rstrip("。")
    importance = norm(row.get("importance"))

    core = _extract_core_substance(term, row)
    if core and core not in hooks:
        hooks.append(format_term_sentence(term, core).rstrip("。"))

    for ep in split_semicolon(row.get("exam_points") or ""):
        framed = _rephrase_exam_point(term, ep, core=core or "").rstrip("。")
        if framed and framed not in hooks:
            hooks.append(framed)

    mistake = _extract_mistake_angle(term, row)
    if mistake:
        hooks.append(mistake.rstrip("。"))

    if legal:
        hooks.append(f"根拠法令は{legal}です")
    for rel in split_semicolon(row.get("related_terms") or "")[:3]:
        if rel and rel != term:
            hooks.append(f"関連語{rel}との違いも確認します")
    if category:
        hooks.append(f"{category}分野で{term}の定義と条件を押さえる用語です")
    if importance in {"A", "S"}:
        hooks.append(f"{term}は重要度{importance}で頻出しやすい語です")

    for filler in _INDEX_PAD_FILLERS:
        hooks.append(filler.rstrip("。"))

    if variant:
        hooks.append(f"一覧では{term}の試験論点を短く確認できます")
        hooks.append(f"乙4では{term}の言い換えと例外条件の確認が定番です")

    seen_local: set[str] = set()
    unique: list[str] = []
    for hook in hooks:
        key = normalize_key(hook)
        if not key or key in seen_local:
            continue
        seen_local.add(key)
        unique.append(hook)
    if variant:
        start = variant % max(1, len(unique))
        unique = unique[start:] + unique[:start]
    return unique


def _dedupe_draft(
    term: str,
    draft: str,
    row: dict[str, str],
    seen: set[str],
    *,
    variant: int = 0,
) -> str:
    out = norm(draft)
    key = normalize_key(out)
    prefix = key[:50]
    if key not in seen and prefix not in seen:
        return out

    for hook in _dedupe_hooks(term, row, variant=variant):
        trial = out.rstrip("。") + "。" + hook.rstrip("。") + "。"
        trial_key = normalize_key(trial)
        trial_prefix = trial_key[:50]
        if trial_key in seen or trial_prefix in seen:
            continue
        trimmed = clamp_glossary_index_summary(trial) or _trim_to_max(trial)
        trimmed_key = normalize_key(trimmed)
        trimmed_prefix = trimmed_key[:50]
        if trimmed_key not in seen and trimmed_prefix not in seen:
            return trimmed
    return out


def _fallback_index_summary(term: str, row: dict[str, str]) -> str:
    """素材が足りない行向けの最低限の下書き。"""
    category = norm(row.get("category")) or "試験"
    seed = f"{term}は{category}分野で試験に出やすい重要語です"
    return _pad_to_min_length(term, format_term_sentence(term, seed), row)


def _register_index_summary(
    term: str,
    summary: str,
    applied_pairs: list[tuple[str, str]],
    seen_keys: set[str],
) -> None:
    applied_pairs.append((term, summary))
    key = normalize_key(summary)
    seen_keys.add(key)
    if len(key) >= 50:
        seen_keys.add(key[:50])


def _worst_cross_match(
    term: str,
    summary: str,
    applied_pairs: list[tuple[str, str]],
) -> tuple[str, float]:
    from tools.glossary_index_summary_rules import cross_similar_ratio

    key = normalize_key(summary)
    worst_term = ""
    worst_ratio = 0.0
    for other_term, other_summary in applied_pairs:
        if other_term == term:
            continue
        ratio = cross_similar_ratio(key, normalize_key(other_summary))
        if ratio > worst_ratio:
            worst_ratio = ratio
            worst_term = other_term
    return worst_term, worst_ratio


def _variant_suffix(term: str, row: dict[str, str], *, variant: int) -> str:
    category = norm(row.get("category"))
    legal = norm(row.get("legal_basis")).rstrip("。")
    related = [r for r in split_semicolon(norm(row.get("related_terms"))) if r != term]
    importance = norm(row.get("importance"))
    rel = related[variant % len(related)] if related else ""
    options = [
        f"乙4の{category}では{term}の定義確認が定番です" if category else "",
        f"{term}は{legal}に関わる試験頻出語です" if legal else "",
        f"一覧では{rel}と{term}の違いをセットで押さえます" if rel else "",
        f"重要度{importance}の{term}は条件の言い換えが問われます"
        if importance in {"A", "S"}
        else "",
        f"{term}は{category}分野で手続と要件を整理する語です" if category else "",
        f"過去問では{term}の正誤肢で定義の取り違えが出やすいです",
    ]
    options = [o for o in options if o]
    return options[variant % len(options)] if options else f"{term}の試験論点を一覧で短く確認できます"


def _build_substance_summary(
    term: str,
    row: dict[str, str],
    *,
    variant: int = 0,
    contrast_term: str = "",
) -> str:
    parts: list[str] = []
    core = _extract_core_substance(term, row)
    if core:
        parts.append(format_term_sentence(term, core).rstrip("。"))

    eps = split_semicolon(norm(row.get("exam_points")))
    if eps:
        ep = eps[variant % len(eps)]
        framed = _rephrase_exam_point(term, ep, core=core or "。".join(parts)).rstrip("。")
        if framed and framed not in "。".join(parts):
            parts.append(framed)

    if contrast_term:
        parts.append(f"一覧では{contrast_term}との定義の違いを押さえる必要があります")

    mistake = _extract_mistake_angle(term, row)
    if mistake and variant % 2 == 1 and mistake not in "。".join(parts):
        parts.append(mistake.rstrip("。"))

    legal = norm(row.get("legal_basis")).rstrip("。")
    if legal and variant % 3 == 0 and legal not in "。".join(parts):
        parts.append(f"根拠法令は{legal}です")

    suffix = _variant_suffix(term, row, variant=variant)
    if suffix and suffix not in "。".join(parts):
        parts.append(suffix.rstrip("。"))

    merged = "。".join(p.rstrip("。") for p in parts if p)
    if not merged:
        return ""
    padded = _pad_to_min_length(term, merged, row)
    if padded:
        return padded
    return _trim_to_max(merged)


def _exam_point_summary_candidates(term: str, row: dict[str, str]) -> list[str]:
    candidates: list[str] = []
    core = _extract_core_substance(term, row)
    if core:
        padded = _pad_to_min_length(
            term, format_term_sentence(term, core).rstrip("。"), row
        )
        if padded:
            candidates.append(padded)

    eps = split_semicolon(norm(row.get("exam_points")))
    for idx, ep in enumerate(eps):
        framed = _rephrase_exam_point(term, ep, core=core or "")
        if not framed:
            continue
        base = format_term_sentence(term, framed.rstrip("。"))
        padded = _pad_to_min_length(term, base.rstrip("。"), row)
        if padded and padded not in candidates:
            candidates.append(padded)
        if idx >= 4:
            break

    mistake = _extract_mistake_angle(term, row)
    if mistake:
        padded = _pad_to_min_length(term, mistake.rstrip("。"), row)
        if padded and padded not in candidates:
            candidates.append(padded)

    composed = _compose_index_summary(term, row)
    if composed and composed not in candidates:
        candidates.append(composed)

    return candidates


def _passes_row_errors(row: dict[str, str], summary: str) -> bool:
    from tools.glossary_index_summary_rules import check_index_summary_row

    trial = dict(row)
    trial["index_summary"] = summary
    return not any(i.level == "ERROR" for i in check_index_summary_row(trial))


def _accept_candidate(
    term: str,
    row: dict[str, str],
    candidate: str,
    applied_pairs: list[tuple[str, str]],
    *,
    build_mode: bool = True,
) -> str:
    from tools.glossary_index_summary_rules import (
        INDEX_SUMMARY_BUILD_SIMILARITY,
        INDEX_SUMMARY_CROSS_SIMILARITY,
        cross_conflicts_incremental,
    )

    if not candidate:
        return ""
    final = clamp_glossary_index_summary(candidate) or _trim_to_max(candidate)
    if not final:
        return ""
    if not _passes_row_errors(row, final):
        return ""
    limit = (
        INDEX_SUMMARY_BUILD_SIMILARITY
        if build_mode
        else INDEX_SUMMARY_CROSS_SIMILARITY
    )
    if cross_conflicts_incremental(term, final, applied_pairs, max_ratio=limit):
        return ""
    return final


def _minimal_exam_summary(
    term: str,
    row: dict[str, str],
    applied_pairs: list[tuple[str, str]],
    *,
    contrast_term: str = "",
) -> str:
    from tools.glossary_index_summary_rules import (
        INDEX_SUMMARY_CROSS_SIMILARITY,
        cross_conflicts_incremental,
    )

    core = _extract_core_substance(term, row)
    eps = split_semicolon(norm(row.get("exam_points")))
    legal = norm(row.get("legal_basis")).rstrip("。")
    trials: list[str] = []

    if core:
        trials.append(format_term_sentence(term, core).rstrip("。"))
    for ep in eps:
        framed = _rephrase_exam_point(term, ep, core=core or "")
        if framed:
            trials.append(format_term_sentence(term, framed.rstrip("。")).rstrip("。"))

    for base in trials:
        parts = [base.rstrip("。")]
        if contrast_term:
            parts.append(f"一覧では{contrast_term}と{term}の定義の違いが試験の焦点です")
        if legal:
            parts.append(f"根拠法令は{legal}です")
        merged = "。".join(p for p in parts if p)
        final = _pad_to_min_length(term, merged, row) or _trim_to_max(merged)
        if not final or not _passes_row_errors(row, final):
            continue
        if not cross_conflicts_incremental(
            term, final, applied_pairs, max_ratio=INDEX_SUMMARY_CROSS_SIMILARITY
        ):
            return final
        pushed = _push_below_cross_threshold(term, row, final, applied_pairs)
        if pushed:
            return pushed
    return ""


def _push_below_cross_threshold(
    term: str,
    row: dict[str, str],
    summary: str,
    applied_pairs: list[tuple[str, str]],
) -> str:
    from tools.glossary_index_summary_rules import (
        INDEX_SUMMARY_BUILD_SIMILARITY,
        INDEX_SUMMARY_CROSS_SIMILARITY,
        cross_conflicts_incremental,
        cross_similar_ratio,
    )

    if not summary:
        return ""
    if not cross_conflicts_incremental(
        term, summary, applied_pairs, max_ratio=INDEX_SUMMARY_CROSS_SIMILARITY
    ):
        return summary

    base = summary.rstrip("。")
    suffixes: list[str] = []
    for hook in _dedupe_hooks(term, row):
        suffixes.append(hook.rstrip("。"))
    for variant in range(20):
        suffixes.append(_variant_suffix(term, row, variant=variant))

    key = normalize_key(summary)
    for other_term, other_summary in applied_pairs:
        ratio = cross_similar_ratio(key, normalize_key(other_summary))
        if ratio > INDEX_SUMMARY_BUILD_SIMILARITY:
            suffixes.append(f"一覧では{other_term}と{term}の条文上の区別を忘れない")
            suffixes.append(f"{term}は{other_term}と語句が近いが適用要件が異なります")

    seen_suffix: set[str] = set()
    for suffix in suffixes:
        suffix = suffix.rstrip("。")
        if not suffix or suffix in seen_suffix:
            continue
        seen_suffix.add(suffix)
        trial = base + "。" + suffix
        final = clamp_glossary_index_summary(trial) or _trim_to_max(trial)
        if not final or not _passes_row_errors(row, final):
            continue
        if not cross_conflicts_incremental(
            term,
            final,
            applied_pairs,
            max_ratio=INDEX_SUMMARY_CROSS_SIMILARITY,
        ):
            return final
    return ""


def _break_cross_similarity(
    term: str,
    row: dict[str, str],
    applied_pairs: list[tuple[str, str]],
) -> str:
    from tools.glossary_index_summary_rules import (
        INDEX_SUMMARY_CROSS_SIMILARITY,
        cross_conflicts_incremental,
    )

    for variant in range(32):
        candidate = _build_substance_summary(term, row, variant=variant)
        accepted = _accept_candidate(term, row, candidate, applied_pairs)
        if accepted:
            return accepted
        pushed = _push_below_cross_threshold(term, row, candidate, applied_pairs)
        if pushed:
            return pushed

        worst_term, ratio = _worst_cross_match(term, candidate or "", applied_pairs)
        if ratio <= INDEX_SUMMARY_CROSS_SIMILARITY:
            continue
        contrast = _build_substance_summary(
            term, row, variant=variant, contrast_term=worst_term
        )
        accepted = _accept_candidate(term, row, contrast, applied_pairs)
        if accepted:
            return accepted
        pushed = _push_below_cross_threshold(term, row, contrast, applied_pairs)
        if pushed:
            return pushed

    return ""


def force_unique_index_summary(
    term: str,
    row: dict[str, str],
    *,
    variant: int = 0,
) -> str:
    """語間重複を避ける一覧専用文（定義素材を優先し term で差別化）。"""
    core = _extract_core_substance(term, row)
    if core:
        merged = format_term_sentence(term, core).rstrip("。")
    else:
        merged = _synthesize_opening(term, row).rstrip("。")

    hooks = _dedupe_hooks(term, row, variant=variant)
    start = variant % max(1, len(hooks)) if hooks else 0
    for hook in hooks[start:] + hooks[:start]:
        trial = merged.rstrip("。") + "。" + hook.rstrip("。")
        padded = _pad_to_min_length(term, trial, row)
        if padded and len(padded.rstrip("。")) >= INDEX_SUMMARY_MIN_LEN:
            return padded

    padded = _pad_to_min_length(term, merged, row)
    if padded:
        return padded
    return _trim_to_max(merged)


def resolve_unique_index_summary(
    term: str,
    row: dict[str, str],
    applied_pairs: list[tuple[str, str]],
    seen_keys: set[str],
) -> str:
    """試験論点ベース→合成→差別化の順で語間重複のない概要を返す。"""
    candidates: list[str] = []

    for item in _exam_point_summary_candidates(term, row):
        if item not in candidates:
            candidates.append(item)

    for variant in range(6):
        built = _build_substance_summary(term, row, variant=variant)
        if built and built not in candidates:
            candidates.append(built)

    draft = draft_glossary_index_summary(row, seen_keys=seen_keys)
    if draft and draft not in candidates:
        candidates.append(draft)

    if draft:
        for variant in range(4):
            alt = _dedupe_draft(term, draft, row, seen_keys, variant=variant)
            if alt and alt not in candidates:
                candidates.append(alt)

    synth = _trim_to_max(_synthesize_opening(term, row).rstrip("。"))
    if synth and synth not in candidates:
        candidates.append(synth)

    for variant in range(4):
        forced = force_unique_index_summary(term, row, variant=variant)
        if forced and forced not in candidates:
            candidates.append(forced)

    for candidate in candidates:
        accepted = _accept_candidate(term, row, candidate, applied_pairs)
        if accepted:
            return accepted
        pushed = _push_below_cross_threshold(term, row, candidate, applied_pairs)
        if pushed:
            return pushed

    return _break_cross_similarity(term, row, applied_pairs)


def draft_glossary_index_summary(
    row: dict[str, str],
    *,
    seen_keys: set[str] | None = None,
) -> str:
    """一覧用 index_summary の下書き（100〜150字・コピー回避・語間 dedupe）。"""
    term = norm(row.get("term"))
    if not term:
        return ""

    candidates: list[str] = []
    composed = _compose_index_summary(term, row)
    if composed:
        candidates.append(composed)

    fallback = _fallback_index_summary(term, row)
    if fallback:
        candidates.append(fallback)

    merged = ""
    for candidate in candidates:
        if passes_index_copy_check(candidate, row):
            merged = candidate
            break
    if not merged and candidates:
        merged = candidates[0]

    if not merged:
        return ""

    if seen_keys is not None:
        merged = _dedupe_draft(term, merged, row, seen_keys)
        seen_keys.add(normalize_key(merged))
        if len(normalize_key(merged)) >= 50:
            seen_keys.add(normalize_key(merged)[:50])

    final = clamp_glossary_index_summary(merged)
    if not final:
        final = _trim_to_max(merged)
    if final and len(final.rstrip("。")) < INDEX_SUMMARY_MIN_LEN:
        final = _pad_to_min_length(term, final.rstrip("。"), row) or final
    if final and not passes_index_copy_check(final, row):
        synth = _pad_to_min_length(term, _synthesize_opening(term, row).rstrip("。"), row)
        if synth and passes_index_copy_check(synth, row):
            final = synth
    if final and len(final.rstrip("。")) < INDEX_SUMMARY_MIN_LEN:
        final = ""
    return final


def build_glossary_index_summary(entry: dict) -> str:
    term = norm(entry.get("term"))
    if not term:
        return ""

    exam_points = split_semicolon(entry.get("exam_points") or "")
    sources = [
        norm(entry.get("definition")),
        norm(entry.get("explanation")),
        norm(entry.get("term_detail_body")),
    ]

    lead_body = extract_lead_substance(term, entry.get("article_lead") or "")
    if lead_body:
        out = format_term_sentence(term, lead_body)
        if out:
            return clamp_summary(out)

    picked = pick_definition_sentence(term, [s for s in sources if s], exam_points)
    if picked:
        out = format_term_sentence(term, picked)
        if out:
            return clamp_summary(out)

    short = norm(entry.get("short_def") or "")
    if short:
        first = split_sentences(short.replace("\n\n", " "), 1)
        if first:
            body = trim_lead_sentence(term, first[0])
            if body and not is_generic_sentence(body):
                out = format_term_sentence(term, body)
                if out:
                    return clamp_summary(out)
    return ""


def _first_compare_axis(row: dict) -> str:
    try:
        rows = json.loads(row.get("compare_rows") or "[]")
    except json.JSONDecodeError:
        return ""
    if not rows:
        return ""
    axis = norm(rows[0].get("axis"))
    cols = rows[0].get("cols") or []
    if not axis or not cols:
        return ""
    c0, c1 = norm(cols[0]), norm(cols[1]) if len(cols) > 1 else ""
    if c0 and c1:
        return f"{axis}では、{c0}と{c1}の違いが試験の焦点になります"
    return ""


def _first_number_highlight(row: dict) -> str:
    h = norm(row.get("highlight"))
    if h and len(h) >= 10 and not is_generic_hub_summary(h):
        return h.rstrip("。")
    try:
        items = json.loads(row.get("item_rows") or "[]")
    except json.JSONDecodeError:
        items = []
    if items:
        it = items[0]
        item = norm(it.get("item"))
        value = norm(it.get("value"))
        note = norm(it.get("note"))
        if item and value:
            bit = f"{item}は{value}"
            if note:
                bit += f"（{note}）"
            return bit
    return ""


def _first_mistake_hook(row: dict) -> str:
    cp = norm(row.get("confusion_point"))
    if cp and len(cp) >= 12:
        return cp.rstrip("。")
    try:
        patterns = json.loads(row.get("pattern_rows") or "[]")
    except json.JSONDecodeError:
        patterns = []
    if patterns:
        p = patterns[0]
        wrong = norm(p.get("wrong"))
        correct = norm(p.get("correct"))
        if wrong and correct:
            return f"誤答例「{wrong}」と正解「{correct}」の差を押さえます"
    return ""


def _usable_exam_point(row: dict) -> str:
    for ep in split_semicolon(row.get("exam_points") or ""):
        ep = ep.rstrip("。")
        if len(ep) >= 12 and not is_generic_sentence(ep) and "試験の正誤肢" not in ep:
            return ep
    return ""


def _usable_memory_tip(row: dict) -> str:
    tip = norm(row.get("memory_tip") or "")
    if not tip:
        return ""
    first = split_sentences(tip.replace("\n", " "), 1)
    if not first:
        return ""
    t = first[0].rstrip("。")
    t = re.sub(r"^【覚え方】", "", t).strip()
    if len(t) >= 12 and not is_generic_sentence(t):
        return t
    return ""


def build_hub_index_summary(row: dict, *, kind: str) -> str:
    title = norm(row.get("title"))
    parts: list[str] = []

    lead = strip_boilerplate(row.get("article_lead") or "")
    if lead:
        sents = split_sentences(lead, 3)
        for sent in sents:
            s = sent.rstrip("。")
            if len(s) >= 16 and not is_generic_sentence(s) and "整理します" not in s:
                parts.append(s)
                if len("。".join(parts)) >= INDEX_MIN_LEN:
                    break

    if kind == "compare":
        axis = _first_compare_axis(row)
        if axis:
            parts.append(axis)
    elif kind == "numbers":
        num = _first_number_highlight(row)
        if num:
            parts.append(num)
    elif kind == "mistakes":
        hook = _first_mistake_hook(row)
        if hook:
            parts.append(hook)

    ep = _usable_exam_point(row)
    if ep:
        parts.append(ep)

    if len("。".join(parts)) < INDEX_MIN_LEN:
        tip = _usable_memory_tip(row)
        if tip:
            parts.append(tip)

    out = join_unique_parts(parts, max_len=INDEX_MAX_LEN)
    if out and title and title not in out:
        out = clamp_summary(f"{title}：{out.rstrip('。')}。", min_len=24)
    if out and not is_generic_hub_summary(out):
        return out

    if title:
        highlight = norm(row.get("highlight") or "")
        if highlight and len(highlight) >= 12 and not is_generic_hub_summary(highlight):
            return clamp_summary(f"{title}。{highlight}", min_len=24)
        return clamp_summary(f"{title}の試験論点と数値・条文の確認ポイントを解説します。", min_len=24)
    return ""
