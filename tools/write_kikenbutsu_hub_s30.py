#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write kikenbutsu (乙4) knowledge hub S30 — 10 compare + 10 numbers + 10 mistakes."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

HEADER_COMPARE = [
    "slug", "title", "category", "tags", "summary", "col_labels", "compare_rows",
    "article_title", "article_lead", "exam_points", "common_mistakes", "memory_tip",
    "related_terms", "faq_1_question", "faq_1_answer", "faq_2_question", "faq_2_answer",
    "faq_3_question", "faq_3_answer", "faq_4_question", "faq_4_answer",
]
HEADER_NUMBERS = [
    "slug", "title", "category", "tags", "summary", "highlight", "item_rows",
    "article_title", "article_lead", "exam_points", "common_mistakes", "memory_tip",
    "related_terms", "faq_1_question", "faq_1_answer", "faq_2_question", "faq_2_answer",
    "faq_3_question", "faq_3_answer", "faq_4_question", "faq_4_answer",
]
HEADER_MISTAKES = [
    "slug", "title", "category", "tags", "summary", "confusion_point", "pattern_rows",
    "article_title", "article_lead", "exam_points", "common_mistakes", "memory_tip",
    "related_terms", "faq_1_question", "faq_1_answer", "faq_2_question", "faq_2_answer",
    "faq_3_question", "faq_3_answer", "faq_4_question", "faq_4_answer",
]


def _faq(qa: list[tuple[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i, (q, a) in enumerate(qa, start=1):
        out[f"faq_{i}_question"] = q
        out[f"faq_{i}_answer"] = a
    return out


def _rows(*items: dict) -> str:
    return json.dumps(list(items), ensure_ascii=False)


COMPARISONS = [
    {
        "slug": "koshu-otsu-hei-hikaku",
        "title": "甲種・乙種・丙種の取扱範囲の違い",
        "category": "法令・制度",
        "tags": "甲種;乙種;丙種;免状",
        "summary": "危険物取扱者免状3種類の取扱できる危険物の範囲と受験資格の違いを、乙4試験で問われる観点で整理します。",
        "col_labels": "甲種;乙種;丙種",
        "compare_rows": _rows(
            {"axis": "取扱範囲", "cols": [
                "すべての種類の危険物（第1〜6類等）",
                "第1〜6類のうち受験した類（乙4は第4類引火性液体）",
                "乙種第4類のうち指定された危険物（引火性液体の一部）のみ",
            ]},
            {"axis": "受験資格", "cols": [
                "実務経験等の受験資格が必要",
                "受験資格不要（どなたでも受験可）",
                "受験資格不要",
            ]},
            {"axis": "試験手数料（目安）", "cols": [
                "7,200円（消費税非課税・公式要項で確認）",
                "5,300円（乙種共通・公式要項で確認）",
                "4,200円（公式要項で確認）",
            ]},
            {"axis": "乙4受験者の位置づけ", "cols": [
                "上位資格。乙4だけでは取得しない",
                "ガソリン等の第4類を扱う現場資格として最多",
                "指定品目に限定。乙4より狭い",
            ]},
            {"axis": "試験での見分け", "cols": [
                "「全類」「実務経験」「7,200円」のキーワード",
                "「第4類ガソリン」「受験資格なし」「5,300円」",
                "「指定危険物のみ」「丙種指定品目」のキーワード",
            ]},
        ),
        "article_title": "甲種・乙種・丙種の違い｜危険物取扱者乙4",
        "article_lead": "危険物取扱者免状は甲・乙・丙の3種類があり、取扱できる危険物の範囲と受験要件が異なります。乙4は第4類引火性液体（ガソリン等）向けの乙種免状で、受験者数が最も多い試験です。丙種はさらに指定品目に限定されます。",
        "exam_points": "甲種は全類・受験資格あり;乙種は類ごとに試験（乙4は第4類）;丙種は指定品目のみ;手数料は甲>乙>丙の順（公式要項で確認）",
        "common_mistakes": "丙種で第4類すべてを扱えると誤解する;甲種も受験資格不要とする;乙種1類取得で乙4も自動取得とする",
        "memory_tip": "「甲＝全部・資格要」「乙＝類別・乙4が主流」「丙＝指定のみ」と段階で覚える。",
        "related_terms": "甲種・乙種・丙種の違い;乙種第4類;丙種危険物取扱者",
        **_faq([
            ("甲種と乙種の最大の違いは？", "甲種はすべての危険物を取り扱えますが受験資格が必要です。乙種は類ごとの試験で、乙4は第4類引火性液体が対象です。受験資格は不要です。取扱範囲と受験要件の両方で区別してください。"),
            ("丙種は乙4と何が違いますか？", "丙種は乙種第4類のうち指定された危険物に限り取扱作業ができます。乙4（乙種第4類）は第4類の引火性液体全般が対象です。丙種の方が取扱範囲が狭い点に注意してください。"),
            ("試験で問われやすい数値は？", "試験手数料（甲7,200円・乙5,300円・丙4,200円等）は消防試験研究センターの公式要項で確認してください。年度・改正で変わる場合があるため、数値早見表利用時も直前に再確認を。"),
            ("乙4取得後に他類は？", "乙種は類ごとに試験が分かれています。他類（第1類等）を扱うには別途その類の試験に合格する必要があります。ただし乙種免状保有者は法令・物化科目の免除があります。"),
        ]),
    },
    {
        "slug": "inka-ten-hakka-ten",
        "title": "引火点と発火点の違い",
        "category": "物性・化学",
        "tags": "引火点;発火点;第4類;液体",
        "summary": "引火性液体の分類・試験方法に関わる引火点と発火点の定義・測定条件の違いを整理します。",
        "col_labels": "引火点;発火点",
        "compare_rows": _rows(
            {"axis": "定義のイメージ", "cols": [
                "可燃性蒸気が外部火源（小火炎）に接触して一時的に着火する最低温度",
                "外部火源なしで自然に着火する温度（物質が自己発火する温度）",
            ]},
            {"axis": "第4類との関係", "cols": [
                "引火点による分類（特殊・第1〜4類等）の基準",
                "自然発火性の判断や第3類等との関連で出題",
            ]},
            {"axis": "試験での典型問題", "cols": [
                "ガソリンの引火点（特殊引火点）や灯油・軽油の区分",
                "「引火点＝発火点」と同一視する誤答肢",
            ]},
            {"axis": "関連する危険性", "cols": [
                "蒸気の着火性・換気・火気厳禁の判断",
                "蓄熱・自然発火性物質（第3類等）の管理",
            ]},
            {"axis": "覚え方", "cols": [
                "「外から火を近づけたら着く温度」",
                "「火を使わなくても自分で燃え始める温度」",
            ]},
        ),
        "article_title": "引火点と発火点の違い｜危険物取扱者乙4",
        "article_lead": "引火点は外部火源により蒸気が着火する温度、発火点は外部火源なしで自然発火する温度です。乙4では引火点による第4類の分類が最重要ですが、発火点・自然発火との混同も頻出です。",
        "exam_points": "引火点は第4類分類の基準;発火点は自然発火の判断に関連;両者を同一視しない;ガソリンは特殊引火点として扱う",
        "common_mistakes": "引火点と発火点を同じ数値・同じ概念とする;引火点が高いほど危険と逆に覚える;自然発火性物質の引火点問題と混同する",
        "memory_tip": "「引火＝外の火」「発火＝自分で発火」と火源の有無で切り分ける。",
        "related_terms": "引火点;発火点;引火・発火・自然発火の違い",
        **_faq([
            ("引火点と発火点の違いは？", "引火点は可燃性蒸気が外部の火源に接触して着火する最低温度です。発火点は外部火源なしで物質自体が自然発火する温度です。乙4では引火点による液体の分類が特に重要です。"),
            ("ガソリンの引火点は？", "ガソリンは特殊引火点として扱われ、引火点による分類表で別枠です。具体的数値は消防法別表・教科書の一次情報で確認し、暗記表と照合してください。"),
            ("試験の引っかけは？", "引火点と発火点の数値や定義を入れ替える肢、引火点が高い液体ほど引火性が高いとする誤りなどが典型です。引火点による分類の用語解説も参照してください。"),
            ("関連する第4類の論点は？", "第4類共通性質、アルコール類・灯油・軽油の引火点区分とセットで整理すると得点しやすくなります。"),
        ]),
    },
]

# Part 2 appended below in same file via exec from part2 module - actually I'll add rest inline in next edit
