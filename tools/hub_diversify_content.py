#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replace generic S35–S44 hub templates with topic- and batch-specific copy."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

BATCH_RE = re.compile(r"-s(\d+)$")
GENERIC_CONFUSION = frozenset(
    {
        "手順と主体の混同。",
        "手順と主体の混同",
        "再発防止計画・休復職支援は名称が似るため、主語と時点の読み飛ばしが起きやすい。",
    }
)
GENERIC_MISTAKE_PATTERNS = (
    ("手順", "誤った対応", "典型誤答"),
    ("主体", "誤った対応", "典型誤答"),
    ("記録", "誤った対応", "典型誤答"),
    ("報告", "誤った対応", "典型誤答"),
)
GENERIC_CMP_AXES = (
    ("定義", ["主語・目的の確認", "手順・対象の確認"]),
    ("頻出", ["類似語の入替", "数値・条件付き出題"]),
)

ANGLE_BY_BATCH: dict[int, str] = {
    35: "基礎整理",
    36: "実務連動",
    37: "試験頻出",
    38: "判例・ガイド",
    39: "横断総合",
    40: "基礎整理",
    41: "実務連動",
    42: "試験頻出",
    43: "判例・ガイド",
    44: "横断総合",
}

CONFUSION_BY_ANGLE: dict[str, str] = {
    "基礎整理": "{topic}の目的・対象・主体の定義を取り違えやすい。",
    "実務連動": "{topic}の実施主体と手続順序（誰が・いつ・何を）を混同しやすい。",
    "試験頻出": "{topic}の過去問で主語・数値・条件文が入れ替わる肢に注意。",
    "判例・ガイド": "{topic}のガイドライン・通知と法令条文の関係を誤解しやすい。",
    "横断総合": "{topic}と類似制度の境界が曖昧になり、総合問題で誤答しやすい。",
}

LEAD_BY_ANGLE: dict[str, str] = {
    "基礎整理": "{topic}は用語の定義と義務主体を先に固定し、比較表で整理してください。",
    "実務連動": "{topic}は職場フロー（事前確認→実施→記録→報告）に沿って復習すると定着します。",
    "試験頻出": "{topic}は過去問の逆転肢・数値混同を型別に分類し、条件文を最後まで読んでください。",
    "判例・ガイド": "{topic}は法令条文とガイドライン・通知の対応表を作成し、優先関係を確認してください。",
    "横断総合": "{topic}は関連制度との違いを横断マップにまとめ、直前総仕上げに使ってください。",
}

TITLE_SUFFIXES = (
    "の典型誤答",
    "の混同",
    "の誤認",
    "の逆転",
    "の省略",
    "の盲信",
    "の過剰",
    "の未確認",
    "の未使用",
    "の放置",
    "のゼロ",
    "の比較",
    "の違い",
    "の整理",
    "の要点",
    "の対比",
    "の区分",
    "の手順",
    "の制度",
    "の運用",
    "の判定",
    "の数値",
    "の周期",
    "の目安",
    "の頻度",
    "の時間",
    "の回数",
    "の基準",
    "の比率",
    "の配分",
    "の確認",
    "の数値整理",
    "の比較整理",
)


def _batch_num(slug: str) -> int | None:
    m = BATCH_RE.search(slug or "")
    return int(m.group(1)) if m else None


def _core_topic(title: str) -> str:
    t = (title or "").strip()
    for suffix in TITLE_SUFFIXES:
        if t.endswith(suffix):
            t = t[: -len(suffix)]
            break
    return t.strip() or title.strip()


def _topic_terms(row: dict[str, str]) -> list[str]:
    tags = [x.strip() for x in (row.get("tags") or "").split(";") if x.strip()]
    generic = {
        "比較",
        "数値",
        "誤答",
        "整理",
        "メンタルヘルスII種",
        "宅建",
        "第一種",
        "第二種",
        "2級ボイラー技士",
        "試験対策",
    }
    out = [t for t in tags if t not in generic and not re.fullmatch(r"S\d+", t)]
    if not out:
        out = [_core_topic(row.get("title", ""))]
    return out[:4]


def _variant_index(slug: str, n: int) -> int:
    if n <= 0:
        return 0
    h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    return h % n


def _is_generic_mistake(row: dict[str, str]) -> bool:
    cp = (row.get("confusion_point") or "").strip()
    if cp in GENERIC_CONFUSION or "手順と主体" in cp or "主語と時点" in cp:
        return True
    try:
        patterns = json.loads(row.get("pattern_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if len(patterns) != 4:
        return False
    traps = [p.get("trap") for p in patterns]
    wrongs = [p.get("wrong") for p in patterns]
    if traps == ["主体誤", "手続誤", "数値誤", "効果誤"] and wrongs == [
        "逆転",
        "省略",
        "固定誤",
        "同一",
    ]:
        return True
    if any(p.get("wrong") == "名称だけで判断" for p in patterns):
        return True
    for p, (axis, wrong, trap) in zip(patterns, GENERIC_MISTAKE_PATTERNS):
        if p.get("topic") != axis or p.get("wrong") != wrong or p.get("trap") != trap:
            break
    else:
        return True
    return traps.count("典型誤答") >= 3


def _mistake_patterns(topic: str, terms: list[str], angle: str, slug: str) -> list[dict[str, str]]:
    axes = [
        ("主体", "義務主体の取り違え", "条文の主語を先に確定", "主体誤り"),
        ("手順", "実施順序の逆転", "確認→実施→記録の順", "手順誤り"),
        ("数値", "数値・条件の単独暗記", "数値と条件をセット確認", "数値誤り"),
        ("記録", "記録・報告の省略", "記録保存まで追跡", "記録誤り"),
    ]
    angle_twist = {
        "基礎整理": "定義確認",
        "実務連動": "フロー確認",
        "試験頻出": "逆転肢対策",
        "判例・ガイド": "条文照合",
        "横断総合": "類似制度と区別",
    }.get(angle, "要点確認")
    shift = _variant_index(slug, len(axes))
    rotated = axes[shift:] + axes[:shift]
    out: list[dict[str, str]] = []
    for i, (axis, wrong, correct_base, trap) in enumerate(rotated):
        term = terms[(i + shift) % len(terms)] if terms else topic
        out.append(
            {
                "topic": axis,
                "wrong": f"{term}を{wrong}",
                "correct": f"{term}の{correct_base}（{angle_twist}）",
                "trap": trap,
            }
        )
    return out


def _mistake_exam_points(topic: str, angle: str, slug: str) -> str:
    pools = {
        "基礎整理": [
            f"{topic}の定義と主体を固定",
            "用語の境界を表で整理",
            "類似語の入替肢に注意",
        ],
        "実務連動": [
            f"{topic}の実施フローを順序固定",
            "記録・報告まで一体確認",
            "担当者分担を明確化",
        ],
        "試験頻出": [
            f"{topic}の逆転肢パターンを分類",
            "条件文の主語を下線",
            "数値+条件のセット暗記",
        ],
        "判例・ガイド": [
            f"{topic}のガイドと条文の対応",
            "通知・通達の位置づけ確認",
            "優先順位を表で整理",
        ],
        "横断総合": [
            f"{topic}と関連制度の違い",
            "横断マップで弱点可視化",
            "直前は誤答型の反復",
        ],
    }
    pts = pools.get(angle, pools["試験頻出"])
    start = _variant_index(slug, len(pts))
    return ";".join(pts[start:] + pts[:start])


def _mistake_common(topic: str, terms: list[str], slug: str) -> str:
    opts = [
        f"{topic}の主体を固定せずに暗記",
        f"{terms[0] if terms else topic}と類似制度を混同",
        "手順を省略したまま正解と判断",
        "記録・報告義務を見落とす",
        "旧要項・旧数値をそのまま適用",
    ]
    i = _variant_index(slug, len(opts))
    return ";".join([opts[i], opts[(i + 1) % len(opts)], opts[(i + 2) % len(opts)]])


def _memory_tip(topic: str, angle: str) -> str:
    tips = {
        "基礎整理": f"「{topic}＝定義→主体→対象」",
        "実務連動": f"「{topic}＝確認→実施→記録」",
        "試験頻出": f"「{topic}＝主語→条件→数値」",
        "判例・ガイド": f"「{topic}＝条文→ガイド→事例」",
        "横断総合": f"「{topic}＝関連制度と境界線」",
    }
    return tips.get(angle, f"「{topic}を表で整理」")


def _faq_mistake(row: dict[str, str], topic: str, angle: str) -> None:
    terms = _topic_terms(row)
    t0 = terms[0] if terms else topic
    row["faq_1_question"] = f"「{row.get('title', topic)}」で最初に確認すべき点は？"
    row["faq_1_answer"] = (
        f"{topic}では{t0}の義務主体と実施タイミングを先に固定してください。"
        f"{angle}の観点では、比較表の1行目に「誰が・いつ・何を」を書くと誤答が減ります。"
    )
    row["faq_2_question"] = f"「{topic}」の典型誤答パターンは？"
    row["faq_2_answer"] = (
        f"{row.get('confusion_point', '')} "
        f"過去問では{t0}に関する逆転肢や、類似制度の数値流用に注意してください。"
    )
    row["faq_3_question"] = f"「{topic}」の復習の進め方（{angle}）は？"
    row["faq_3_answer"] = (
        LEAD_BY_ANGLE.get(angle, LEAD_BY_ANGLE["試験頻出"]).format(topic=topic)
        + " 誤答した設問は原因（主体・手順・数値・記録）をタグ付けして再演習してください。"
    )
    row["faq_4_question"] = f"「{topic}」の関連条文・資料は？"
    row["faq_4_answer"] = (
        f"用語集の「{t0}」と関連法令・試験要項を照合してください。"
        " 直前は誤答ノートと本ページを往復し、同型の引っかけを連続で解いてください。"
    )


def _diversify_mistake(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    if not _is_generic_mistake(row):
        return
    topic = _core_topic(row.get("title", ""))
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    terms = _topic_terms(row)
    slug = row.get("slug", "")

    row["confusion_point"] = CONFUSION_BY_ANGLE[angle].format(topic=topic)
    row["summary"] = f"{topic}（{angle}）で頻出する誤答パターンを、主体・手順・数値・記録の4型で整理します。"
    row["pattern_rows"] = json.dumps(_mistake_patterns(topic, terms, angle, slug), ensure_ascii=False)
    row["article_lead"] = LEAD_BY_ANGLE[angle].format(topic=topic)
    row["exam_points"] = _mistake_exam_points(topic, angle, slug)
    row["common_mistakes"] = _mistake_common(topic, terms, slug)
    row["memory_tip"] = _memory_tip(topic, angle)
    if not row.get("article_title"):
        row["article_title"] = f"{row.get('title', topic)}｜誤答パターン"
    _faq_mistake(row, topic, angle)


def _is_generic_compare(row: dict[str, str]) -> bool:
    lead = (row.get("article_lead") or "").strip()
    if "義務主体・実施手順・記録保存" in lead:
        return True
    if lead.startswith("比較表で") and "整理" in lead and len(lead) < 80:
        return True
    try:
        axes = json.loads(row.get("compare_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if len(axes) < 2:
        return False
    labels = {(a.get("axis"), tuple(a.get("cols") or [])) for a in axes}
    for generic in GENERIC_CMP_AXES:
        if (generic[0], tuple(generic[1])) in labels:
            return True
    return "観点A" in (row.get("col_labels") or "")


def _faq_compare(row: dict[str, str], topic: str, angle: str) -> None:
    terms = _topic_terms(row)
    t1, t2 = (terms + [topic])[:2]
    row["faq_1_question"] = f"「{t1}」と「{t2}」の違いは何ですか？"
    row["faq_1_answer"] = (
        f"{topic}（{angle}）では、比較表の5軸（目的・主体・手続・数値・試験論点）で"
        f"{t1}と{t2}を並べ、主語と条件文の差を確認してください。"
    )
    row["faq_2_question"] = f"「{topic}」の比較表の使い方は？"
    row["faq_2_answer"] = (
        LEAD_BY_ANGLE.get(angle, LEAD_BY_ANGLE["試験頻出"]).format(topic=topic)
        + " 過去問で入れ替わった肢は、表のどの行が逆転したかをメモしてください。"
    )
    row["faq_3_question"] = f"「{topic}」で試験に出やすい混同は？"
    row["faq_3_answer"] = (
        f"{row.get('common_mistakes', '')} "
        f"名称だけで判断せず、{t1}と{t2}それぞれの義務主体を条文で確認してください。"
    )
    row["faq_4_question"] = f"「{topic}」の直前復習（{angle}）は？"
    row["faq_4_answer"] = (
        f"比較表を見ずに{t1}と{t2}の違いを口述し、"
        " 誤答した設問は逆転した軸（主体・手順・数値）をタグ付けして再演習してください。"
    )


def _compare_rows(topic: str, terms: list[str], angle: str) -> list[dict[str, Any]]:
    t1, t2 = (terms + [topic, topic])[:2]
    pools: dict[str, list[tuple[str, list[str]]]] = {
        "基礎整理": [
            ("目的", [f"{t1}の目的", f"{t2}の目的"]),
            ("主体", [f"{t1}の義務者", f"{t2}の義務者"]),
            ("対象", [f"{t1}の適用範囲", f"{t2}の適用範囲"]),
            ("手続", [f"{t1}の手続", f"{t2}の手続"]),
            ("試験", [f"{t1}の頻出論点", f"{t2}との混同点"]),
        ],
        "実務連動": [
            ("フロー", [f"{t1}の実施順", f"{t2}の実施順"]),
            ("記録", [f"{t1}の記録", f"{t2}の記録"]),
            ("連携", [f"{t1}の関係者", f"{t2}の関係者"]),
            ("異常時", [f"{t1}の対応", f"{t2}の対応"]),
            ("試験", [f"実務→試験の変換", f"手順省略肢"]),
        ],
        "試験頻出": [
            ("論点", [f"{t1}の条文", f"{t2}の条文"]),
            ("数値", [f"{t1}の数値", f"{t2}の数値"]),
            ("条件", [f"{t1}の要件", f"{t2}の要件"]),
            ("逆転", [f"{t1}の正答型", f"逆転肢の例"]),
            ("混同", [f"{t1}と{t2}の境界", "名称だけの判断"]),
        ],
        "判例・ガイド": [
            ("根拠", [f"{t1}の法令", f"{t2}の法令"]),
            ("ガイド", [f"{t1}の指針", f"{t2}の指針"]),
            ("運用", [f"{t1}の実務解釈", f"{t2}の実務解釈"]),
            ("更新", [f"{t1}の改定点", f"{t2}の改定点"]),
            ("試験", [f"条文×ガイド", "旧通知の流用"]),
        ],
        "横断総合": [
            ("制度", [f"{t1}の位置づけ", f"{t2}の位置づけ"]),
            ("関係", [f"{t1}との連携", f"{t2}との連携"]),
            ("リスク", [f"{t1}の違反リスク", f"{t2}の違反リスク"]),
            ("総合", [f"横断マップ上の{t1}", f"横断マップ上の{t2}"]),
            ("直前", [f"弱点チェック", "同型誤答の再確認"]),
        ],
    }
    return [{"axis": a, "cols": c} for a, c in pools.get(angle, pools["試験頻出"])]


def _diversify_compare(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    if not _is_generic_compare(row):
        return
    topic = _core_topic(row.get("title", ""))
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    terms = _topic_terms(row)
    t1, t2 = (terms + [topic])[:2]
    row["col_labels"] = f"{t1};{t2}"
    row["compare_rows"] = json.dumps(_compare_rows(topic, terms, angle), ensure_ascii=False)
    row["summary"] = f"{topic}（{angle}）について、{t1}と{t2}の違いを5軸で整理します。"
    row["article_lead"] = LEAD_BY_ANGLE[angle].format(topic=topic)
    row["exam_points"] = _mistake_exam_points(topic, angle, row.get("slug", ""))
    row["common_mistakes"] = _mistake_common(topic, terms, row.get("slug", ""))
    row["memory_tip"] = _memory_tip(topic, angle)
    _faq_compare(row, topic, angle)


def _is_generic_numbers(row: dict[str, str]) -> bool:
    hl = (row.get("highlight") or "").strip()
    if hl in ("代表値は要項・法令で確認", "要項・法令で確認"):
        return True
    cm = (row.get("common_mistakes") or "").strip()
    if cm == "数値だけ暗記;手順省略;主体混同":
        return True
    try:
        items = json.loads(row.get("item_rows") or "[]")
    except json.JSONDecodeError:
        return False
    if not items:
        return False
    notes = [i.get("note", "") for i in items]
    if notes.count("試験要点を確認") >= 3:
        return True
    if notes.count("試験頻出") >= 3 and len(set(i.get("item") for i in items)) <= 2:
        return True
    return False


def _faq_numbers(row: dict[str, str], topic: str, angle: str) -> None:
    terms = _topic_terms(row)
    t0 = terms[0] if terms else topic
    row["faq_1_question"] = f"「{topic}」で確認すべき数値・条件は？"
    row["faq_1_answer"] = (
        f"{topic}（{angle}）では{t0}に関する数値だけでなく、"
        "義務主体・実施条件・記録保存までセットで確認してください。"
    )
    row["faq_2_question"] = f"「{topic}」の数値暗記のコツは？"
    row["faq_2_answer"] = (
        f"{row.get('memory_tip', '')} "
        "数値は条文・試験要項の表と照合し、旧要項との差分は更新日付で管理してください。"
    )
    row["faq_3_question"] = f"「{topic}」の典型誤答は？"
    row["faq_3_answer"] = (
        f"{row.get('common_mistakes', '')} "
        f"{angle}では条件文の主語と数値が入れ替わる肢に注意してください。"
    )
    row["faq_4_question"] = f"「{topic}」の関連資料は？"
    row["faq_4_answer"] = (
        f"用語集の「{t0}」、関連法令・試験要項、直近の通知・ガイドラインを照合してください。"
        " 直前は本ページの確認表と過去問を往復してください。"
    )


def _number_items(topic: str, terms: list[str], angle: str) -> list[dict[str, str]]:
    labels = ["義務主体", "実施・頻度", "記録・保存", "試験の確認点", "関連制度"]
    out: list[dict[str, str]] = []
    for i, label in enumerate(labels):
        term = terms[i % len(terms)] if terms else topic
        note_by_angle = {
            "基礎整理": "定義・主体を確認",
            "実務連動": "フロー上の位置づけ",
            "試験頻出": "数値・条件のセット",
            "判例・ガイド": "条文・通知を照合",
            "横断総合": "関連制度とセット",
        }
        out.append(
            {
                "item": label,
                "value": term,
                "note": note_by_angle.get(angle, "試験要点を確認"),
            }
        )
    return out


def _diversify_numbers(row: dict[str, str]) -> None:
    batch = _batch_num(row.get("slug", ""))
    if batch is None or batch < 35:
        return
    if not _is_generic_numbers(row):
        return
    topic = _core_topic(row.get("title", ""))
    angle = ANGLE_BY_BATCH.get(batch, "試験頻出")
    terms = _topic_terms(row)
    row["item_rows"] = json.dumps(_number_items(topic, terms, angle), ensure_ascii=False)
    row["highlight"] = f"{terms[0] if terms else topic}（{angle}で確認）"
    row["summary"] = f"{topic}（{angle}）の数値・手続・記録の確認ポイントを整理します。"
    row["article_lead"] = (
        f"{topic}では数値だけでなく、義務主体・実施条件・記録保存まで一体で確認してください。"
        + LEAD_BY_ANGLE[angle].format(topic=topic)
    )
    row["exam_points"] = _mistake_exam_points(topic, angle, row.get("slug", ""))
    row["common_mistakes"] = _mistake_common(topic, terms, row.get("slug", ""))
    row["memory_tip"] = _memory_tip(topic, angle)
    _faq_numbers(row, topic, angle)


def diversify_hub_row(row: dict[str, str]) -> dict[str, str]:
    if "confusion_point" in row:
        _diversify_mistake(row)
    elif "compare_rows" in row:
        _diversify_compare(row)
    elif "highlight" in row and "item_rows" in row:
        _diversify_numbers(row)
    return row


def _differentiate_duplicate_patterns(row: dict[str, str]) -> None:
    try:
        patterns = json.loads(row.get("pattern_rows") or "[]")
    except json.JSONDecodeError:
        return
    if not patterns:
        return
    title = (row.get("title") or "").strip()
    topic = _core_topic(title)
    label = title.split("：")[0].strip() if "：" in title else topic
    terms = _topic_terms(row)
    shift = _variant_index(row.get("slug", ""), max(len(patterns), 1))
    for j, p in enumerate(patterns):
        term = terms[(j + shift) % len(terms)] if terms else topic
        anchor = label if label not in (term, topic) else term
        wrong = (p.get("wrong") or "").strip()
        correct = (p.get("correct") or "").strip()
        if anchor not in wrong:
            p["wrong"] = f"【{anchor}】{wrong}" if wrong else anchor
        if anchor not in correct:
            p["correct"] = f"【{anchor}】→{correct}" if correct else anchor
    row["pattern_rows"] = json.dumps(patterns, ensure_ascii=False)


def _dedupe_mistake_patterns(rows: list[dict[str, str]]) -> None:
    by_batch: dict[int, dict[str, list[dict[str, str]]]] = {}
    for row in rows:
        if "confusion_point" not in row:
            continue
        batch = _batch_num(row.get("slug", ""))
        if batch is None or batch < 35:
            continue
        pat = row.get("pattern_rows", "")
        by_batch.setdefault(batch, {}).setdefault(pat, []).append(row)
    for batch_rows in by_batch.values():
        for group in batch_rows.values():
            if len(group) < 2:
                continue
            for row in group:
                _differentiate_duplicate_patterns(row)


def diversify_hub_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    for row in rows:
        diversify_hub_row(row)
    _dedupe_mistake_patterns(rows)
    return rows
