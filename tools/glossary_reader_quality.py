#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用語詳細記事の読みやすさ（平易な文体・具体例・覚え方・FAQ）を整える。

enrich_o4_glossary_details.py の最終段階から呼び出す。
"""

from __future__ import annotations

import re
from typing import Any

FAQ_EXTRA_COLUMNS = (
    "faq_3_question",
    "faq_3_answer",
    "faq_4_question",
    "faq_4_answer",
)

# 頻出語は試験でイメージしやすい具体例を固定（それ以外はカテゴリ・キーワードで生成）
TERM_EXAMPLES: dict[str, str] = {
    "指定数量": "ガソリン（非水溶性）は200 L、アセトン（水溶性）は400 Lのように、品名ごとに数値が決まります。",
    "指定数量の倍数": "貯蔵量を指定数量で割った値（倍数）を品名ごとに足し合わせ、施設の区分を決めます。",
    "倍数計算": "例えば、ガソリン200 Lと灯油400 Lを同じ屋内に置くとき、それぞれ÷指定数量してから合算します（リットル数の単純合計ではありません）。",
    "ガソリン": "第1石油類の非水溶性として扱われ、指定数量は200 Lです。",
    "灯油": "第2石油類に分類され、引火点の範囲で第1石油類と区別されます。",
    "アセトン": "水溶性液体で指定数量は400 L。水に溶けても引火の危険がある点が試験の定番です。",
    "第4類危険物": "引火性液体が該当し、乙4の主な対象です（例：ガソリン・灯油・エーテルなど）。",
    "引火点": "ガソリンの引火点は−20 ℃前後、灯油は30 ℃以上など、品名とセットで覚えます。",
    "消防法": "危険物かどうかは、別表第一の品名と別表第二の性状の両方で判断します。",
    "危険物の規制に関する政令": "指定数量や品名一覧（別表第三）は、この政令で具体化されています。",
    "別表第三": "ガソリン・灯油など、品名ごとの指定数量を調べる表です。",
    "類別": "第4類は引火性液体、第2類は可燃性固体など、6つの類に分けられます。",
    "泡消火": "非水溶性の石油類の火災で有効なことが多く、水溶性液体だけに使えるわけではありません。",
    "移送": "配管・ポンプで設備間を移すことで、タンクローリーでの運搬とは別です。",
    "運搬": "事業所の外へ車両で運ぶ行為で、表示・混載・容器の基準が問われます。",
    "バックドラフト": "密閉した室内火災で、開口部から酸素が一気に入ると可燃性ガスが急燃する現象です。",
    "フラッシュオーバー": "天井付近の高温ガスが下へ伝わり、室内が一斉に燃え広がる現象です。",
    "燃焼の三要素": "可燃物・酸素（空気）・着火源の3つがそろうと燃焼が続きます。",
    "爆発下限界": "空気中の可燃性蒸気濃度がこの値を下回ると、火花があっても燃えにくくなります。",
}

CATEGORY_EXAMPLES: dict[str, str] = {
    "法令・制度": (
        "条文では「消防法で定める」「政令で定める」「施行令で定める」のように、"
        "どの法令に書かれているかを選ぶ問題がよく出ます。"
    ),
    "物性・化学": (
        "引火点・沸点・密度など、数字と単位をセットで覚えると、"
        "選択肢の数値の当たり外れを見分けやすくなります。"
    ),
    "火災・消火・漏えい": (
        "危険物の性質（水溶性か、蒸気がたまりやすいか）に合った消火・漏えい対策かどうかが、"
        "正誤の判断ポイントになります。"
    ),
}

PLAIN_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("において", "では"),
    ("こととなる", "ことになります"),
    ("こととなる。", "ことになります。"),
    ("といえる", "と言えます"),
    ("が挙げられる", "があります"),
    ("が挙げられます", "があります"),
    ("が求められる", "が必要です"),
    ("が必要となる", "が必要になります"),
    ("に留意する", "に注意する"),
    ("に留意が", "に注意が"),
    ("を要する", "が必要です"),
    ("に該当するもの", "に当てはまるもの"),
    ("に該当する", "に当てはまる"),
    ("をいう", "を指します"),
    ("をいい、", "を指し、"),
    ("をいい", "を指し"),
)


def norm(s: str | None) -> str:
    return (s or "").strip()


def split_semicolon_field(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def plainize(text: str) -> str:
    """堅い表現をやわらかい言い回しに寄せる（法令用語は残す）。"""
    t = norm(text)
    if not t:
        return ""
    for old, new in PLAIN_REPLACEMENTS:
        t = t.replace(old, new)
    t = re.sub(r"(\d)（", r"\1（", t)
    return t


def pick_concrete_example(
    term: str,
    category: str,
    exam_points: list[str],
) -> str:
    if term in TERM_EXAMPLES:
        return TERM_EXAMPLES[term]
    joined = " ".join(exam_points)
    if "指定数量" in joined or "倍数" in term:
        return TERM_EXAMPLES["指定数量"]
    if "第" in term and "類" in term:
        return (
            f"{term}は危険物の類別のひとつです。"
            "乙4では第4類（引火性液体）が中心ですが、誤り選択肢では他の類の例も出ます。"
        )
    if "消火" in term or "漏えい" in term:
        return CATEGORY_EXAMPLES["火災・消火・漏えい"]
    if "引火" in term or "蒸気" in term or "燃焼" in term:
        return (
            "密閉空間では蒸気がたまりやすく、換気と火気厳禁が重要です。"
            "数値（引火点・爆発下限界など）は品名とセットで確認してください。"
        )
    return CATEGORY_EXAMPLES.get(category, CATEGORY_EXAMPLES["法令・制度"])


def first_clause(s: str) -> str:
    t = norm(s)
    if not t:
        return ""
    if "。" in t:
        return t.split("。")[0].strip()
    return t


def build_key_summary(
    term: str,
    category: str,
    lead_sentence: str,
    exam_points: list[str],
) -> str:
    """「まず押さえる要点」用（short_def）— 定義＋具体例＋試験の一言。"""
    core = plainize(first_clause(lead_sentence)) if lead_sentence else f"{category}で押さえる重要語"
    if core.startswith(f"{term}は"):
        line1 = ends_sentence(core)
    else:
        line1 = ends_sentence(f"{term}は、{core}")
    example = plainize(pick_concrete_example(term, category, exam_points))
    line2 = ends_sentence(f"たとえば、{example.rstrip('。')}") if example else ""
    exam_line = ""
    if exam_points:
        first = plainize(exam_points[0].rstrip("。"))
        exam_line = ends_sentence(f"試験では、{first}点を押さえると得点源になります")
    parts = [p for p in (line1, line2, exam_line) if p]
    return "\n\n".join(parts)


def ends_sentence(s: str) -> str:
    t = norm(s)
    if not t:
        return ""
    return t if t.endswith("。") else f"{t}。"


def build_reader_lead(
    term: str,
    category: str,
    unit: str,
    lead_sentence: str = "",
) -> str:
    if lead_sentence:
        core = plainize(lead_sentence.rstrip("。"))
        return (
            f"このページでは、{category}分野の「{term}」を、試験に出る形で整理します。"
            f"ひとことで言うと、{core}。"
            f"下の目次の順に読むと、定義から演習のポイントまでつながって理解できます。"
        )
    if unit:
        return (
            f"「{unit}」の単元でよく出る用語です。"
            f"意味を確認したら、試験ポイントと例題で定着を確認してください。"
        )
    return (
        f"{category}で押さえる用語です。"
        f"意味と試験のポイントを確認し、関連用語・演習とあわせて復習してください。"
    )


def build_detailed_memory_tip(
    term: str,
    category: str,
    peers: list[str],
    exam_points: list[str],
    traps: list[str],
    unit: str = "",
) -> str:
    """覚え方・整理のコツ（複数段落・セミコロン区切りも可）。"""
    blocks: list[str] = []

    hook = f"「{term}」は、"
    if unit:
        hook += f"単元「{unit}」とセットで出ることが多い語です。"
    else:
        hook += f"{category}の頻出語です。"
    blocks.append(plainize(hook))

    if peers:
        peer_str = "」「".join(peers[:3])
        blocks.append(
            plainize(
                f"整理のコツ：関連する「{peer_str}」と、"
                f"「同じ点・違う点」を表に書き出し、{term}だけの特徴を一行で言えるようにします。"
            )
        )
    elif exam_points:
        blocks.append(
            plainize(
                f"整理のコツ：試験ポイント（{exam_points[0].rstrip('。')}など）を"
                f"付箋に書き、演習の正誤解説と照らし合わせます。"
            )
        )

    if traps:
        blocks.append(
            plainize(
                f"覚え方：間違えたら「{traps[0].rstrip('。')}」のパターンか確認し、"
                f"同じ型の誤りが出た問題を2問だけ繰り返します。"
            )
        )
    else:
        blocks.append(
            plainize(
                "覚え方：実践演習でこの語が出たら、定義→試験ポイント→関連用語の順に"
                "このページへ戻ると、短時間で復習できます。"
            )
        )

    blocks.append(
        plainize(
            "復習のしかた：丸暗記より、選択肢の「誤り。」の理由を声に出して説明できるかを目標にします。"
        )
    )
    return "\n\n".join(blocks)[:480]


def build_faq_set(
    term: str,
    category: str,
    short_def: str,
    exam_points: list[str],
    traps: list[str],
    legal: str,
    peers: list[str],
) -> list[tuple[str, str]]:
    """よくある質問 3〜4 件（質問, 回答）。"""
    definition_answer = plainize(short_def.replace("\n\n", " ").replace("\n", " "))
    if not definition_answer:
        definition_answer = f"{term}は、{category}で学ぶ重要な用語です。"

    exam_bits = [plainize(p.rstrip("。")) for p in exam_points[:3] if p]
    if exam_bits:
        exam_answer = "。".join(exam_bits) + "。"
    else:
        exam_answer = (
            f"{category}では、定義の言い換えや数値・主体の区別がセットで問われます。"
            "実践演習の解説と照らし合わせて確認してください。"
        )

    if traps:
        mistake_answer = "。".join(
            plainize(ensure_sentence(t).rstrip("。")) for t in traps[:2]
        ) + "。"
    else:
        mistake_answer = (
            "似た用語や数値と混同しやすいです。"
            "演習で×になった選択肢をメモし、関連用語と対比して復習してください。"
        )

    items: list[tuple[str, str]] = [
        (f"{term}とは何ですか？", definition_answer),
        (f"{term}は試験でどんなふうに問われますか？", exam_answer),
        (f"{term}で間違えやすい点は？", mistake_answer),
    ]

    if peers and len(peers) >= 2:
        a, b = peers[0], peers[1]
        items.append(
            (
                f"{term}と「{a}」「{b}」の違いは？",
                plainize(
                    f"「{a}」「{b}」は意味や数値・適用場面が異なります。"
                    f"用語ページの比較表と演習で、{term}だけのポイントを確認してください。"
                ),
            )
        )
    elif legal:
        basis = legal.replace(";", "・")
        items.append(
            (
                f"{term}の根拠や数値はどこで確認しますか？",
                plainize(
                    f"主な根拠は{basis}です。"
                    "最新の数値・手続は消防試験研究センターのテキストと公式サイトで確認してください。"
                ),
            )
        )
    else:
        items.append(
            (
                f"{term}はどう復習するとよいですか？",
                plainize(
                    "意味を一言で言えるようにしたあと、実践演習で出た正誤解説を読み返し、"
                    "関連用語へ1つだけリンクして広げると定着しやすくなります。"
                ),
            )
        )
    return items[:4]


def ensure_sentence(s: str) -> str:
    t = norm(s)
    if not t:
        return ""
    return t if t.endswith("。") else f"{t}。"


def apply_faqs_to_row(row: dict[str, str], faqs: list[tuple[str, str]]) -> None:
    for idx, (q, a) in enumerate(faqs, start=1):
        row[f"faq_{idx}_question"] = q
        row[f"faq_{idx}_answer"] = plainize(a)
    for idx in range(len(faqs) + 1, 5):
        row.pop(f"faq_{idx}_question", None)
        row.pop(f"faq_{idx}_answer", None)


def apply_reader_quality(
    row: dict[str, str],
    *,
    lead_sentence: str = "",
    exam_points: list[str] | None = None,
    traps: list[str] | None = None,
    peers: list[str] | None = None,
    unit: str = "",
    skip_short_def: bool = False,
) -> None:
    """CSV 行に読みやすさ改善を反映する。"""
    term = norm(row.get("term"))
    if not term:
        return
    category = norm(row.get("category")) or "法令・制度"
    exam_points = exam_points if exam_points is not None else split_semicolon_field(
        norm(row.get("exam_points"))
    )
    traps = traps if traps is not None else split_semicolon_field(
        norm(row.get("common_mistakes"))
    )
    peers = peers if peers is not None else split_semicolon_field(norm(row.get("related_terms")))

    if not lead_sentence:
        lead_sentence = norm(row.get("definition"))
        if lead_sentence.startswith(f"まず「{term}」は、"):
            lead_sentence = lead_sentence.split("、", 1)[-1].rstrip("。")

    if not skip_short_def:
        row["short_def"] = build_key_summary(term, category, lead_sentence, exam_points)

    lead_raw = norm(row.get("article_lead"))
    if lead_raw and "このページでは" not in lead_raw:
        row["article_lead"] = plainize(lead_raw)
    elif not lead_raw or len(lead_raw) < 40:
        row["article_lead"] = build_reader_lead(term, category, unit, lead_sentence)

    row["memory_tip"] = build_detailed_memory_tip(
        term, category, peers, exam_points, traps, unit
    )

    body = norm(row.get("term_detail_body"))
    if body:
        row["term_detail_body"] = plainize(body)

    definition = norm(row.get("definition"))
    if definition:
        row["definition"] = plainize(definition)

    explanation = norm(row.get("explanation"))
    if explanation:
        row["explanation"] = plainize(explanation)

    faqs = build_faq_set(
        term,
        category,
        row["short_def"],
        exam_points,
        traps,
        norm(row.get("legal_basis")),
        peers,
    )
    apply_faqs_to_row(row, faqs)


def ensure_glossary_csv_columns(fieldnames: list[str]) -> list[str]:
    for col in FAQ_EXTRA_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)
    return fieldnames
