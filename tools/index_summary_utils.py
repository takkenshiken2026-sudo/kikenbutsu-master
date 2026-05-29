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
