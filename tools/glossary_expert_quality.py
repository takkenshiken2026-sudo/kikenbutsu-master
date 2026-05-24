#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用語詳細記事を専門家・プロライター水準に引き上げる（全件後処理）。"""

from __future__ import annotations

import re

from tools.glossary_reader_quality import plainize, split_semicolon_field
from tools.site_config import exam_name

EXAM = exam_name()
PATTERN_MARKER = "【試験で問われる型】"
FIELD_MARKER = "【現場・実務のイメージ】"


def norm(s: str | None) -> str:
    return (s or "").strip()


def split_paras(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", norm(text)) if p.strip()]


CATEGORY_FIELD_NOTE: dict[str, str] = {
    "法令・制度": (
        "製造所・貯蔵所・取扱所の区分や、許可・届出・選任など「誰が・いつまでに・何をするか」"
        "が条文の言い換えとして問われます。"
    ),
    "物性・化学": (
        "引火点・沸点・蒸気濃度など、数値と単位・品名がセットの設問が多く、"
        "計算より「条件の当てはめ」で勝負が決まることがあります。"
    ),
    "火災・消火・漏えい": (
        "危険物の性質（水溶性・揮発性・蒸気の蓄積）に合った消火・漏えい対策かどうか、"
        "「適切／不適切」の判断が中心です。"
    ),
}


def build_exam_pattern_paragraph(
    term: str,
    category: str,
    exam_points: list[str],
    traps: list[str],
) -> str:
    points = "。".join(p.rstrip("。") for p in exam_points[:2] if p)
    trap = traps[0].rstrip("。") if traps else "似た用語・数値と混同しやすい"
    core = points or f"{category}の定義と適用場面の理解"
    return plainize(
        f"{PATTERN_MARKER}"
        f"五肢択一では「正しいもの／誤っているもの」の問い方に加え、"
        f"「{term}」を含む肢の言い換え（{core}）が頻出です。"
        f"特に「{trap}」という誤答パターンは、演習で×になったら用語ページへ戻って定義を声に出して確認してください。"
    )


def build_field_paragraph(term: str, category: str) -> str:
    note = CATEGORY_FIELD_NOTE.get(category, CATEGORY_FIELD_NOTE["法令・制度"])
    return plainize(
        f"{FIELD_MARKER}"
        f"現場では、{term}は保安体制・設備基準・取扱手順のどこに効いてくるかを意識すると記憶が定着します。"
        f"{note}"
    )


def build_expert_article_lead(
    term: str,
    category: str,
    lead_sentence: str,
) -> str:
    core = lead_sentence.rstrip("。") if lead_sentence else f"{category}で押さえる重要語"
    return plainize(
        f"このページは、{EXAM}（乙種第4類）の受験者が「{term}」を試験本番で得点源にするための用語解説です。"
        f"ひとことで言うと、{core}。"
        f"定義のあと、具体例・試験ポイント・演習の正誤解説とあわせて読み進めてください。"
    )


def append_expert_body_blocks(
    body: str,
    term: str,
    category: str,
    exam_points: list[str],
    traps: list[str],
) -> str:
    parts = split_paras(body)
    extras: list[str] = []
    if not any(PATTERN_MARKER in p for p in parts):
        extras.append(build_exam_pattern_paragraph(term, category, exam_points, traps))
    if not any(FIELD_MARKER in p for p in parts):
        extras.append(build_field_paragraph(term, category))
    if not extras:
        return body
    return body + "\n\n" + "\n\n".join(extras)


def build_expert_memory_tip(
    term: str,
    category: str,
    peers: list[str],
    exam_points: list[str],
    traps: list[str],
) -> str:
    peer_line = ""
    if peers:
        peer_line = (
            f"関連語「{'」「'.join(peers[:3])}」とは、"
            f"同じ点・違う点を表に1行ずつ書き、{term}だけの特徴を声に出せるまで確認します。"
        )
    point = exam_points[0].rstrip("。") if exam_points else "定義と数値・主体の区別"
    trap = traps[0].rstrip("。") if traps else "類似語との混同"
    return plainize(
        f"【覚え方】{point}を付箋に書き、演習で出たら即このページへ戻る。\n\n"
        f"【整理のコツ】{peer_line or '分野ハブから同カテゴリの用語を5語だけセットで読む。'}\n\n"
        f"【ひっかけ対策】「{trap}」のパターンかを確認し、誤った選択肢の理由を1行メモする。\n\n"
        f"【復習】丸暗記ではなく、選択肢の正誤解説を読み上げて説明できるかを合格ラインにする。"
    )[:520]


def deepen_faq_answer(answer: str, term: str) -> str:
    a = plainize(answer)
    if len(a) >= 120:
        return a
    return (
        f"{a} "
        f"あわせて{EXAM}の実践演習で「{term}」を含む問題を1問解き、"
        f"正誤解説と照らし合わせると定着が早くなります。"
    )


def apply_glossary_expert_quality(row: dict[str, str]) -> None:
    term = norm(row.get("term"))
    if not term:
        return
    category = norm(row.get("category")) or "法令・制度"
    exam_points = split_semicolon_field(norm(row.get("exam_points")))
    traps = split_semicolon_field(norm(row.get("common_mistakes")))
    peers = split_semicolon_field(norm(row.get("related_terms")))

    lead_sentence = norm(row.get("definition"))
    if lead_sentence.startswith(f"まず「{term}」は、"):
        lead_sentence = lead_sentence.split("、", 1)[-1].rstrip("。")

    row["article_lead"] = build_expert_article_lead(term, category, lead_sentence)
    row["term_detail_body"] = append_expert_body_blocks(
        norm(row.get("term_detail_body")),
        term,
        category,
        exam_points,
        traps,
    )
    row["memory_tip"] = build_expert_memory_tip(
        term, category, peers, exam_points, traps
    )
    for i in range(1, 5):
        q = norm(row.get(f"faq_{i}_question"))
        a = norm(row.get(f"faq_{i}_answer"))
        if q and a:
            row[f"faq_{i}_answer"] = deepen_faq_answer(a, term)
