#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate write_kikenbutsu_hub_s35-s39_content.py."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
from _hub_content_emit import emit_cmp, emit_mis, emit_num, fix_entry  # noqa: E402

with (ROOT / "data/glossary_terms.csv").open(encoding="utf-8-sig") as _f:
    GLOSS = {r["term"] for r in csv.DictReader(_f)}

_TAIL = "乙4試験では用語集と消防法・政令の対応づけが得点の鍵になります。最新の試験要項もあわせて確認してください。"


def _rel(*terms: str) -> str:
    ok = [t for t in terms if t in GLOSS]
    for d in ("指定数量", "第4類危険物", "消防法", "危険物取扱者", "予防規程", "消火設備"):
        if len(ok) >= 2:
            break
        if d in GLOSS and d not in ok:
            ok.append(d)
    return ";".join(ok[:3])


def _t(title: str, batch: str) -> str:
    return title


def _faq(qa):
    return [(q, a if len(a) >= 100 else a + _TAIL) for q, a in qa]


THEMES = [
    ("kiken-toriatsukai", "危険物取扱", "L", ("危険物取扱者", "危険物保安監督者"), "危険物取扱者;選任", "選任・解任時届出", ("危険物取扱者", "危険物保安監督者")),
    ("shobou-hou", "消防法", "L", ("消防法", "火災予防"), "消防法;火災予防", "消防法・政令で定める", ("消防法", "火災予防")),
    ("shitei-suryo", "指定数量", "L", ("指定数量", "指定数量の倍数"), "指定数量;第4類危険物", "品名別（政令・品名表）", ("指定数量", "指定数量の倍数")),
    ("chozo-sho", "貯蔵所", "L", ("タンク貯蔵所", "屋外タンク貯蔵所"), "タンク貯蔵所;指定数量", "容量・倍数（政令確認）", ("屋外タンク貯蔵所", "屋内タンク貯蔵所の基準")),
    ("ido-ukewatashi", "移動", "L", ("移送", "譲渡・引渡し"), "移送;譲渡・引渡し", "政令・品名表で確認", ("移送", "譲渡・引渡し")),
    ("hoan-kitei", "保安規程", "L", ("予防規程", "火災予防"), "予防規程;予防規程の作成", "作成・変更時（条文）", ("予防規程", "火災予防")),
    ("shoka", "消火", "F", ("消火設備", "消火活動"), "消火設備;消火設備の区分", "規模・用途で変動", ("消火設備", "消火活動")),
    ("tank", "タンク", "L", ("タンクローリー", "移動タンク貯蔵所"), "タンクローリー;移動タンク貯蔵所", "政令・品名表で確認", ("タンクローリー", "移動タンク貯蔵所")),
    ("tensou-kiroku", "転送記録", "L", ("譲渡・引渡しの届出", "移送"), "譲渡・引渡し;譲渡・引渡しの届出", "政令・品名表確認", ("譲渡・引渡し", "移送")),
    ("ot4-shiken", "乙4試験", "L", ("危険物取扱者", "乙種危険物取扱者"), "危険物取扱者;試験要項", "要項で確認（年度により変動）", ("乙種危険物取扱者", "丙種危険物取扱者")),
]

BATCH_ANGLE = {
    "S35": "基礎整理", "S36": "実務連動", "S37": "試験頻出", "S38": "判例・ガイド", "S39": "横断総合",
}


def _cmp(slug, title, cat, t1, t2, summary):
    return fix_entry({
        "slug": slug, "title": title, "cat": cat, "tags": f"{t1};{t2}",
        "summary": summary, "labels": f"{t1};{t2}",
        "axes": [
            ("区分", [f"{t1}の基準", f"{t2}の基準"]),
            ("数量", ["指定数量", "倍数"]),
            ("設備", ["消火設備", "保安設備"]),
            ("試験", [f"「{t1}＝{t2}」", "「基準同一」"]),
            ("混同", ["届出不要", "設備不要"]),
        ],
        "article_title": f"{title}｜乙4",
        "lead": summary + "消防法・政令・品名表をセットで整理してください。",
        "points": f"{t1}と{t2}を分離;指定数量;設備基準;試験の正誤肢に注意",
        "mistakes": f"{t1}＝{t2};基準同一;倍数無視;試験の正誤肢に注意",
        "tip": f"「{t1}と{t2}を分ける」。", "related": _rel(t1, t2),
        "qa": _faq([
            (f"{t1}の要点は？", f"{summary}{t1}の定義・基準を用語集で確認してください。"),
            (f"{t2}との違いは？", f"{t2}は別枠です。比較表を作成してください。"),
            ("試験対策の進め方は？", "区分表・倍数表を作成し、過去問を反復してください。"),
            ("確認先はどこですか？", "消防法・政令・品名表・用語集を参照してください。"),
        ]),
    })


def _num(slug, title, cat, tag, summary, highlight, rel):
    return fix_entry({
        "slug": slug, "title": title, "cat": cat, "tags": tag, "summary": summary,
        "highlight": highlight,
        "items": [
            ("数値", highlight.split("（")[0], "試験頻出"),
            ("根拠", "政令・品名表", "条文確認"),
            ("倍数", "2倍・4倍等", "設備基準"),
            ("試験", "混同肢", "正誤確認"),
            ("確認", "用語集", "最新政令"),
        ],
        "article_title": f"{title}｜乙4",
        "lead": summary + "数値は政令・品名表で確認してください。",
        "points": f"{highlight};倍数計算;品名別;試験の正誤肢に注意",
        "mistakes": "数値固定暗記;倍数無視;品名混同;試験の正誤肢に注意",
        "tip": f"「{highlight.split('（')[0]}を確認」。", "related": rel,
        "qa": _faq([
            ("数値の要点は？", f"{summary}政令・品名表で最新を確認してください。"),
            ("試験の引っかけは？", "類似品名・類似設備の数量を混同しないでください。"),
            ("試験対策の進め方は？", "数量・倍数一覧表を作成し、過去問を反復してください。"),
            ("確認先はどこですか？", "消防法・政令・品名表を参照してください。"),
        ]),
    })


def _mis(slug, title, cat, t1, t2, summary):
    return fix_entry({
        "slug": slug, "title": title, "cat": cat, "tags": f"{t1};{t2}",
        "summary": summary, "confusion": f"{t1}と{t2}の混同。",
        "patterns": [
            ("基準", "同一", "別基準", "基準誤"),
            ("数量", "無視", "指定数量", "数量誤"),
            ("設備", "不要", "政令基準", "設備誤"),
            ("届出", "不要", "必要", "届出誤"),
        ],
        "article_title": f"{title}｜乙4",
        "lead": summary + "正しい整理を表にまとめてください。",
        "points": f"{t1}≠{t2};倍数・設備;品名表;試験の正誤肢に注意",
        "mistakes": "同一視;倍数無視;設備不要;試験の正誤肢に注意",
        "tip": f"「{t1}と{t2}は別」。", "related": _rel(t1, t2),
        "qa": _faq([
            ("誤りの内容は何ですか？", f"{summary}典型誤答として頻出です。"),
            ("正しい理解は何ですか？", f"{t1}と{t2}を基準・数量・設備で分けてください。"),
            ("試験対策の進め方は？", "誤答パターン表を作成し、過去問を反復してください。"),
            ("確認先はどこですか？", "消防法・政令・用語集を参照してください。"),
        ]),
    })


def _build(batch: str) -> None:
    sfx = f"-{batch.lower()}"
    angle = BATCH_ANGLE[batch]
    cmps, nums, miss = [], [], []
    for slug_base, theme, cat, (t1, t2), tag, highlight, (m1, m2) in THEMES:
        cmps.append(_cmp(
            f"{slug_base}-cmp{sfx}", _t(f"{theme}：{t1}と{t2}の比較", batch), cat, t1, t2,
            f"{theme}（{angle}）として{t1}と{t2}の関係を整理します。",
        ))
        nums.append(_num(
            f"{slug_base}-num{sfx}", _t(f"{theme}：{highlight.split('（')[0]}の数値", batch), cat, tag,
            f"{theme}（{angle}）の数量・基準を整理します。", highlight, _rel(*tag.split(";")),
        ))
        miss.append(_mis(
            f"{slug_base}-mis{sfx}", _t(f"{theme}：{m1}と{m2}の混同誤り", batch), cat, m1, m2,
            f"{theme}（{angle}）で{m1}と{m2}を同一視する典型誤り。",
        ))
    header = f'''# -*- coding: utf-8 -*-
"""危険物取扱者乙4 知識ハブ {batch} 追加分（各10件）."""

from tools.write_kikenbutsu_hub_s30_content import _OFFICIAL, cmp, mis, num

L, M, F = "法令・制度", "物性・化学", "火災・消火・漏えい"

'''
    out = TOOLS / f"write_kikenbutsu_hub_{batch.lower()}_content.py"
    parts = [header, "COMPARISONS_ADD = [\n"] + [emit_cmp(c) for c in cmps]
    parts += ["]\n\nNUMBERS_ADD = [\n"] + [emit_num(n) for n in nums]
    parts += ["]\n\nMISTAKES_ADD = [\n"] + [emit_mis(m) for m in miss]
    parts.append("]\n")
    out.write_text("".join(parts), encoding="utf-8")
    print("wrote", out)


def main() -> None:
    for batch in ("S35", "S36", "S37", "S38", "S39"):
        _build(batch)


if __name__ == "__main__":
    main()
