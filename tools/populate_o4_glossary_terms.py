#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危険物取扱者乙4向けに glossary_terms.csv を300件以上に拡充する。

  python3 tools/populate_o4_glossary_terms.py
  python3 tools/populate_o4_glossary_terms.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import brand_name, exam_name  # noqa: E402

OUT = ROOT / "data" / "glossary_terms.csv"
PRACTICE = ROOT / "data" / "imported" / "o4_practice_500_source.csv"
EXAM = exam_name()
BRAND = brand_name()

SUBJECT_TO_CATEGORY = {
    "危険物に関する法令": "法令・制度",
    "基礎的な物理学及び基礎的な化学": "物性・化学",
    "危険物の性質並びにその火災予防及び消火の方法": "火災・消火・漏えい",
}

SKIP_TERMS = {
    "その他",
    "基本",
    "演習",
    "学習法",
    "整理",
    "用語集",
    "制度",
    "得点",
    "公式情報",
    "学習計画",
}

# 既存12件は本文を維持
KEEP_SLUG_TERMS = {
    "公式情報",
    "復習",
    "比較表",
    "試験要項",
    "受験資格",
    "合格基準",
    "出題範囲",
    "過去問",
    "一問一答",
    "模擬試験",
    "用語解説",
    "学習記録",
}

CORE_TERMS: list[tuple[str, str]] = [
    ("消防法", "法令・制度"),
    ("危険物の規制に関する政令", "法令・制度"),
    ("消防法施行令", "法令・制度"),
    ("危険物", "法令・制度"),
    ("第4類危険物", "法令・制度"),
    ("引火性液体", "法令・制度"),
    ("指定数量", "法令・制度"),
    ("指定数量の倍数", "法令・制度"),
    ("製造所", "法令・制度"),
    ("貯蔵所", "法令・制度"),
    ("取扱所", "法令・制度"),
    ("移動式貯蔵タンク", "法令・制度"),
    ("危険物取扱者", "法令・制度"),
    ("乙種危険物取扱者", "法令・制度"),
    ("乙種第4類", "法令・制度"),
    ("丙種危険物取扱者", "法令・制度"),
    ("甲種危険物取扱者", "法令・制度"),
    ("危険物保安監督者", "法令・制度"),
    ("危険物保安統括管理者", "法令・制度"),
    ("予防規程", "法令・制度"),
    ("保安距離", "法令・制度"),
    ("保有空地", "法令・制度"),
    ("消防署長", "法令・制度"),
    ("消防長", "法令・制度"),
    ("第一石油類", "火災・消火・漏えい"),
    ("第二石油類", "火災・消火・漏えい"),
    ("第三石油類", "火災・消火・漏えい"),
    ("特殊引火物", "火災・消火・漏えい"),
    ("アルコール類", "火災・消火・漏えい"),
    ("動植物油類", "火災・消火・漏えい"),
    ("ガソリン", "火災・消火・漏えい"),
    ("灯油", "火災・消火・漏えい"),
    ("軽油", "火災・消火・漏えい"),
    ("重油", "火災・消火・漏えい"),
    ("アセトン", "火災・消火・漏えい"),
    ("メタノール", "火災・消火・漏えい"),
    ("エタノール", "火災・消火・漏えい"),
    ("ジエチルエーテル", "火災・消火・漏えい"),
    ("二硫化炭素", "火災・消火・漏えい"),
    ("引火点", "物性・化学"),
    ("発火点", "物性・化学"),
    ("燃焼", "物性・化学"),
    ("燃焼の三要素", "物性・化学"),
    ("完全燃焼", "物性・化学"),
    ("不完全燃焼", "物性・化学"),
    ("蒸気圧", "物性・化学"),
    ("蒸気比重", "物性・化学"),
    ("比重", "物性・化学"),
    ("密度", "物性・化学"),
    ("フラッシュオーバー", "火災・消火・漏えい"),
    ("バックドラフト", "火災・消火・漏えい"),
    ("窒息消火", "火災・消火・漏えい"),
    ("冷却消火", "火災・消火・漏えい"),
    ("除去消火", "火災・消火・漏えい"),
    ("泡消火", "火災・消火・漏えい"),
    ("粉末消火", "火災・消火・漏えい"),
    ("二酸化炭素消火", "火災・消火・漏えい"),
    ("泡消火剤", "火災・消火・漏えい"),
    ("耐アルコール泡", "火災・消火・漏えい"),
    ("静電気", "物性・化学"),
    ("接地", "物性・化学"),
    ("酸化", "物性・化学"),
    ("還元", "物性・化学"),
    ("pH", "物性・化学"),
    ("引火性蒸気", "物性・化学"),
    ("可燃性蒸気", "物性・化学"),
    ("漏えい", "火災・消火・漏えい"),
    ("漏えい対策", "火災・消火・漏えい"),
    ("漏えい防止堤", "火災・消火・漏えい"),
    ("第1類危険物", "法令・制度"),
    ("第2類危険物", "法令・制度"),
    ("第3類危険物", "法令・制度"),
    ("第5類危険物", "法令・制度"),
    ("第6類危険物", "法令・制度"),
    ("酸化性固体", "物性・化学"),
    ("可燃性固体", "物性・化学"),
    ("自然発火性物質", "物性・化学"),
    ("禁水性物質", "物性・化学"),
    ("自己反応性物質", "物性・化学"),
    ("運搬容器", "法令・制度"),
    ("表示", "法令・制度"),
    ("標識", "法令・制度"),
    ("消火活動", "火災・消火・漏えい"),
    ("消防法別表第一", "法令・制度"),
    ("消防法別表第二", "法令・制度"),
]

FIELDNAMES: list[str] | None = None


def load_fieldnames() -> list[str]:
    global FIELDNAMES
    if FIELDNAMES is None:
        with OUT.open(encoding="utf-8-sig", newline="") as f:
            FIELDNAMES = list(csv.DictReader(f).fieldnames or [])
    return FIELDNAMES


def to_hiragana(text: str) -> str:
    try:
        import pykakasi  # type: ignore

        kks = pykakasi.kakasi()
        parts = kks.convert(text)
        hira = "".join(p.get("hira", "") for p in parts).strip()
        return hira or text
    except Exception:
        if re.fullmatch(r"[A-Za-z0-9・\-\.]+", text):
            return text
        return text


def norm_term(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "", s)
    return s


def collect_candidates() -> dict[str, str]:
    """term -> category"""
    out: dict[str, str] = {}
    for term, cat in CORE_TERMS:
        t = norm_term(term)
        if t and t not in SKIP_TERMS:
            out[t] = cat

    if PRACTICE.is_file():
        with PRACTICE.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                subj = row.get("subject", "").strip()
                cat = SUBJECT_TO_CATEGORY.get(subj, "法令・制度")
                for key in ("topic", "unit"):
                    t = norm_term(row.get(key, ""))
                    if len(t) >= 2 and t not in SKIP_TERMS:
                        out.setdefault(t, cat)
                topic = norm_term(row.get("topic", ""))
                for part in re.split(r"[・／/]", topic):
                    p = norm_term(part)
                    if len(p) >= 3 and p not in SKIP_TERMS:
                        out.setdefault(p, cat)
    return out


def pick_related(term: str, category: str, by_cat: dict[str, list[str]], limit: int = 3) -> str:
    pool = [t for t in by_cat.get(category, []) if t != term]
    if not pool:
        return ""
    picked = pool[:limit]
    return ";".join(picked)


def build_row(term: str, category: str, *, importance: str = "B") -> dict[str, str]:
    reading = to_hiragana(term)
    short = (
        f"{term}は、{EXAM}（乙種第4類）で頻出する{category}分野の用語です。"
        f"定義と試験での問われ方をセットで押さえると、実践演習の解説理解が速くなります。"
    )
    definition = (
        f"{term}は、危険物取扱者試験の出題範囲において重要な概念です。"
        f"法令・物性・火災予防のいずれかの文脈で使われ、選択肢の言い換えや数字のひっかけと結びつくことがあります。"
    )
    explanation = (
        f"試験では{term}の意味、適用場面、関連法令を問う問題が出ます。"
        f"実践演習で誤答した選択肢に出てきたら、この用語ページで定義を確認し、関連用語へ進んでください。"
    )
    article_title = f"{term}とは？{EXAM}で押さえる意味とポイント"
    article_lead = (
        f"{term}の基本理解と、試験で問われやすいポイントを整理します。"
        f"公式情報（消防試験研究センター・消防庁）と照合しながら学習してください。"
    )
    body = (
        f"{term}は{category}の学習で繰り返し登場します。"
        f"類似語との違い、数字・条件の例外は比較しながら覚えると混同を防げます。"
    )
    exam_points = (
        f"定義を一文で説明できる;適用する場面（製造・貯蔵・取扱・消火）を挙げられる;"
        f"関連する法令名を意識できる"
    )
    mistakes = (
        f"類似語と混同する;数字や条件を取り違える;すべての危険物に当てはめる"
    )
    memory = f"過去問・実践演習で出たら即このページへ戻る。関連用語を2語だけセットで覚える。"

    row = {k: "" for k in load_fieldnames()}
    row.update(
        {
            "term": term,
            "reading": reading,
            "category": category,
            "tags": f"{category};乙4;頻出",
            "short_def": short[:200],
            "definition": definition,
            "related_terms": "",
            "legal_basis": "消防法" if category == "法令・制度" else "",
            "importance": importance,
            "explanation": explanation,
            "article_title": article_title,
            "article_lead": article_lead,
            "term_detail_body": body,
            "exam_points": exam_points,
            "common_mistakes": mistakes,
            "memory_tip": memory,
            "example_question": f"{term}について正しい説明はどれか。",
            "example_answer": "公式の定義・試験テキストの説明と一致する選択肢を選ぶ。",
            "faq_1_question": f"{term}はどこで確認できますか？",
            "faq_1_answer": "消防試験研究センターの公式テキスト・受験案内、関連する法令（消防法等）で確認します。",
            "faq_2_question": f"{term}と似た用語の違いは？",
            "faq_2_answer": "用語解説の関連用語リンクからセットで読み、定義の差を比較してください。",
        }
    )
    return row


def load_keep_rows() -> dict[str, dict[str, str]]:
    if not OUT.is_file():
        return {}
    with OUT.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["term"].strip(): r for r in rows if r.get("term", "").strip() in KEEP_SLUG_TERMS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min-count", type=int, default=300)
    args = ap.parse_args()

    keep = load_keep_rows()
    candidates = collect_candidates()

    # 重要語は importance A
    important = {
        "指定数量",
        "第4類危険物",
        "引火性液体",
        "危険物取扱者",
        "乙種第4類",
        "ガソリン",
        "灯油",
        "引火点",
        "燃焼の三要素",
        "泡消火",
        "消防法",
    }

    new_terms = [t for t in sorted(candidates) if t not in keep]
    rows: list[dict[str, str]] = []

    for term in sorted(keep):
        rows.append(keep[term])

    by_cat: dict[str, list[str]] = defaultdict(list)
    for term in new_terms:
        by_cat[candidates[term]].append(term)

    for term in new_terms:
        cat = candidates[term]
        imp = "A" if term in important else "B"
        rows.append(build_row(term, cat, importance=imp))

    # related_terms をカテゴリ内で付与
    all_by_cat: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        all_by_cat[r["category"]].append(r["term"])
    for r in rows:
        if r["term"] in keep:
            continue
        rel = pick_related(r["term"], r["category"], all_by_cat)
        if rel:
            r["related_terms"] = rel

    if len(rows) < args.min_count:
        print(f"warn: {len(rows)} 件（目標 {args.min_count}）", file=sys.stderr)

    if args.dry_run:
        print(f"would write {len(rows)} terms")
        return 0

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=load_fieldnames(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {OUT} — {len(rows)} 件（既存維持 {len(keep)} 件、新規 {len(rows) - len(keep)} 件）")
    print("Next: python3 tools/build_all.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
