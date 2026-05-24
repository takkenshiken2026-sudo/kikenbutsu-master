#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
試験ガイド・用語詳細を「資格の専門家＋プロライター」水準に引き上げる共通ロジック。

演習DB・既存 enrich の上に、具体例・試験の問われ方・読者行動を厚くする。
"""

from __future__ import annotations

import re

from tools.glossary_reader_quality import (  # noqa: E402
    FAQ_EXTRA_COLUMNS as GLOSSARY_FAQ_EXTRA,
    apply_reader_quality,
    plainize,
    split_semicolon_field,
)
from tools.o4_guide_slug_sections import slug_faq_pairs  # noqa: E402
from tools.site_config import brand_name, exam_name  # noqa: E402

EXAM = exam_name()
BRAND = brand_name()

GUIDE_FAQ_EXTRA_COLUMNS = (
    "faq_3_question",
    "faq_3_answer",
    "faq_4_question",
    "faq_4_answer",
)

SECTION_DEPTH_MARKERS = ("具体例", "たとえば", "試験では", "演習では", "正しい。", "誤り。")

GENRE_SECTION_EXAMPLE: dict[str, str] = {
    "試験概要": (
        "たとえば、受験前に「資格要件・申込期限・出題範囲の年度」をセットで確認できているかだけでも、"
        "直前の慌て方が大きく減ります。"
    ),
    "受験・申込": (
        "たとえば、申込書の不備や受験料の名義違いは不受理につながりやすいため、"
        "提出前に公式の記入例と照合する時間を必ず取ってください。"
    ),
    "合格・難易度": (
        "たとえば、合格率は全体統計、演習の正答率はあなた個人の指標です。"
        "数字を混ぜて判断しないことが、計画を崩さないコツになります。"
    ),
    "出題・形式": (
        "たとえば、出題範囲表の章立てと演習の分野チップ（法令・物性・火災）を対応づけると、"
        "「どこが弱いか」が一目で分かります。"
    ),
    "学習計画": (
        "たとえば、平日20分の一問一答と、週末60分の演習まとめを分けるだけでも、"
        "継続率と定着率が上がりやすくなります。"
    ),
    "独学対策": (
        "たとえば、テキストは1冊に絞り、足りない分野だけ問題集を追加する方が、"
        "乙4の広い範囲では挫折しにくいです。"
    ),
    "過去問活用": (
        "たとえば、最新年度の過去問で形式に慣れたあと、実践演習500問で弱点分野の量を確保する"
        "二段構えが効率的です。"
    ),
    "分野別対策": (
        "たとえば、法令で指定数量と倍数、物性で引火点と沸点、火災で消火の適否は、"
        "それぞれ別の用語セットで整理すると混同が減ります。"
    ),
    "用語整理": (
        "たとえば、ガソリン（第1石油類）と灯油（第2石油類）は名称が似ていても指定数量が異なり、"
        "用語解説で「同じ・違う」を表にすると記憶に残ります。"
    ),
    "復習・苦手克服": (
        "たとえば、誤答を「知識不足／用語混同／計算ミス／読み飛ばし」に分類すると、"
        "次の1週間でやるべきことが明確になります。"
    ),
    "直前・当日": (
        "たとえば、直前週は新しい教材を増やさず、誤答ノートと数字一覧だけを毎日15分見る"
        "運用に切り替えるのが安全です。"
    ),
    "注意点・更新": (
        "たとえば、法改正で変わりやすいのは数値・手続・施設基準の条文表現です。"
        "受験年度の公式テキストを最終確認の基準にしてください。"
    ),
}

GENRE_FAQ_EXTRA: dict[str, list[tuple[str, str]]] = {
    "試験概要": [
        (
            "{topic}の学習は何から始めるとよいですか？",
            "公式の出題範囲を確認したうえで、学習計画記事→実践演習で現在地を測る流れがおすすめです。",
        ),
        (
            "{topic}と予備校・通信講座の関係は？",
            "必須ではありません。公式範囲と復習の仕組みが回るかで判断し、購入前は目次とサンプルで確認してください。",
        ),
    ],
    "独学対策": [
        (
            "{topic}で挫折しやすい人の共通点は？",
            "教材を増やしすぎて復習日がないパターンです。演習と解き直しの時間を先に確保してください。",
        ),
        (
            "{topic}のおすすめの1日の流れは？",
            "短時間の一問一答→演習→誤答の用語確認の3ステップを基本に、週末にまとめて解き直します。",
        ),
    ],
}

DEFAULT_FAQ_EXTRA = [
    (
        "{topic}は独学でも対応できますか？",
        "可能な受験者も多いです。公式範囲の把握と、演習・用語・復習の仕組みを先に決めてください。",
    ),
    (
        "{topic}の次にやることは？",
        f"この記事のチェックリストを終えたら、{BRAND}の実践演習で10問解き、誤答語を用語解説で確認してください。",
    ),
]


def norm(s: str | None) -> str:
    return (s or "").strip()


def _short_topic(title: str, slug: str) -> str:
    t = title.replace(EXAM, "").strip("の・ ")
    return t or slug.replace("-", " ")


def section_has_depth(body: str) -> bool:
    hits = sum(1 for m in SECTION_DEPTH_MARKERS if m in body)
    return hits >= 2 and len(body) >= 160


def enhance_guide_section(
    body: str,
    heading: str,
    genre: str,
    slug: str,
    section_index: int,
) -> str:
    text = plainize(body)
    if not text:
        return text
    extras: list[str] = []
    if not section_has_depth(text):
        ex = GENRE_SECTION_EXAMPLE.get(genre)
        if ex and ex not in text:
            extras.append(ex)
        if "試験では" not in text:
            extras.append(
                f"試験では、「{heading}」に関する設問は、言い換え・数値・主体（誰が・いつ・何を）の"
                f"どれかがひっかけになる形で出ることが多いです。"
            )
    if section_index >= 4 and BRAND not in text:
        extras.append(
            f"ここまで整理できたら、{BRAND}の実践演習で分野チップを固定し、"
            f"10問解いて正答率をメモしてください。誤った語は用語解説で定義を一言で確認します。"
        )
    if not extras:
        return text
    return text + "\n\n" + "\n\n".join(extras)


def enhance_guide_lead(lead: str, genre: str, title: str) -> str:
    lead = plainize(lead)
    if len(lead) >= 100 and "この記事では" in lead:
        return lead
    topic = _short_topic(title, "")
    opener = (
        f"この記事は、{EXAM}を受験・学習する方が「{topic}」を迷わず進められるよう、"
        f"公式情報の確認手順と{BRAND}での学習のつなぎ方まで整理したガイドです。"
    )
    if lead:
        return f"{opener}\n\n{lead}"
    return opener


def build_guide_faqs_four(slug: str, genre: str, title: str) -> list[tuple[str, str]]:
    topic = _short_topic(title, slug)
    base = [(q.replace("◯◯試験", EXAM), a.replace("◯◯試験", EXAM)) for q, a in slug_faq_pairs(slug, genre, title)]
    seen = {norm(q) for q, _ in base}
    for q, a in GENRE_FAQ_EXTRA.get(genre, DEFAULT_FAQ_EXTRA):
        fq = q.format(topic=topic)
        if fq in seen:
            continue
        seen.add(fq)
        base.append((fq, a.format(topic=topic) if "{topic}" in a else a))
        if len(base) >= 4:
            break
    while len(base) < 4:
        for q, a in DEFAULT_FAQ_EXTRA:
            fq = q.format(topic=topic)
            if fq in seen:
                continue
            seen.add(fq)
            base.append((fq, a))
            if len(base) >= 4:
                break
        break
    return base[:4]


def apply_guide_pro_row(row: dict[str, str]) -> None:
    slug = norm(row.get("slug"))
    genre = norm(row.get("genre"))
    title = norm(row.get("title"))
    if not slug:
        return

    row["lead"] = enhance_guide_lead(norm(row.get("lead")), genre, title)

    meta = norm(row.get("meta_description"))
    if meta and len(meta) < 90:
        row["meta_description"] = (
            f"{title}。{EXAM}受験者向けに、公式確認の手順と{BRAND}での演習・用語の活用法を専門家視点で整理しました。"
        )[:160]

    intent = norm(row.get("user_intent"))
    if "演習・用語" not in intent:
        topic = _short_topic(title, slug)
        row["user_intent"] = (
            f"「{topic}」を実務と試験の両面で理解し、"
            f"公式情報→演習→用語解説の順で学習を進めたい。"
        )

    sec_idx = 0
    for i in range(1, 8):
        heading = norm(row.get(f"section_{i}_heading"))
        body = norm(row.get(f"section_{i}_body"))
        if not heading or not body:
            continue
        sec_idx += 1
        row[f"section_{i}_body"] = enhance_guide_section(
            body, heading, genre, slug, sec_idx
        )

    for i, (q, a) in enumerate(build_guide_faqs_four(slug, genre, title), start=1):
        row[f"faq_{i}_question"] = q
        row[f"faq_{i}_answer"] = plainize(a)


def build_glossary_expert_block(
    term: str,
    category: str,
    exam_points: list[str],
    traps: list[str],
) -> str:
    parts: list[str] = []
    if exam_points:
        ep = plainize(exam_points[0].rstrip("。"))
        parts.append(
            f"専門家視点では、{term}は「{ep}」が得点の分かれ目になります。"
            f"定義を暗記するだけでなく、選択肢の言い換えに耐える一言説明を目標にしてください。"
        )
    if traps:
        tr = plainize(traps[0].rstrip("。"))
        parts.append(
            f"受験者がつまずきやすいのは、{tr}パターンです。"
            f"演習で×になった選択肢をそのままメモし、関連用語と対比表で整理すると改善しやすくなります。"
        )
    if not parts:
        parts.append(
            f"{category}では、{term}が他の用語とセットで問われることが多いです。"
            f"単独の暗記より、演習2問→用語解説→関連語1件の小さなサイクルが効率的です。"
        )
    parts.append(
        "数値・手続・条文表現は年度で整理が変わるため、"
        "最終確認は消防試験研究センターのテキストと公式サイトを基準にしてください。"
    )
    return "\n\n".join(parts)


def apply_glossary_pro_row(row: dict[str, str]) -> None:
    term = norm(row.get("term"))
    if not term:
        return
    category = norm(row.get("category")) or "法令・制度"
    exam_points = split_semicolon_field(norm(row.get("exam_points")))
    traps = split_semicolon_field(norm(row.get("common_mistakes")))

    apply_reader_quality(row)

    body = norm(row.get("term_detail_body"))
    expert = build_glossary_expert_block(term, category, exam_points, traps)
    if expert and "専門家視点" not in body:
        row["term_detail_body"] = (body + "\n\n" + expert) if body else expert

    expl = norm(row.get("explanation"))
    if expl and len(expl) < 120:
        traps_line = traps[0] if traps else "類似語や数値の取り違え"
        row["explanation"] = plainize(
            f"{expl} 演習では、{traps_line}に注意しながら、正誤解説を読み返して判断基準を言語化してください。"
        )



def ensure_guide_csv_columns(fieldnames: list[str]) -> list[str]:
    for col in GUIDE_FAQ_EXTRA_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)
    return fieldnames


def ensure_glossary_csv_columns(fieldnames: list[str]) -> list[str]:
    for col in GLOSSARY_FAQ_EXTRA:
        if col not in fieldnames:
            fieldnames.append(col)
    return fieldnames
