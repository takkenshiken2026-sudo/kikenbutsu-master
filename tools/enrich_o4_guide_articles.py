#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
試験ガイド（guide_articles.csv）の定型文を乙4向け固有本文に差し替える。

  python3 tools/enrich_o4_guide_articles.py
  python3 tools/enrich_o4_guide_articles.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.o4_guide_content import (  # noqa: E402
    AFFILIATE_LEAD,
    AFFILIATE_SECTION_EXTRA,
    BRAND,
    EXAM,
    FIELD_SUFFIX_HINTS,
    FIELDS,
    GENRE_BODIES,
    SLUG_PATCHES,
)
from tools.o4_guide_slug_sections import (  # noqa: E402
    SLUG_SECTION_EXTRA,
    slug_faq_pairs,
    slug_lead_text,
    slug_section_bodies,
)
from tools.scaffold_guide_article import GENRE_OUTLINES  # noqa: E402
from tools.site_config import brand_name, exam_name  # noqa: E402

CSV_PATH = ROOT / "data" / "guide_articles.csv"
BOILERPLATE_MARKERS = (
    "乙種第4類は第4類危険物（引火性液体）を中心に、法令・物性・火災予防の3領域が出題の柱です",
    "数値・制度は消防試験研究センターの受験案内で最新版を確認し、当サイトの実践演習・用語解説で定着を図ってください",
)

FIELD_SLUG_RE = re.compile(r"^field-(law|rights|limit)-([a-z0-9-]+)$")


def norm(s: str | None) -> str:
    return (s or "").strip()


def is_boilerplate(text: str) -> bool:
    return any(m in text for m in BOILERPLATE_MARKERS)


def field_templates(field_id: str, suffix: str) -> dict[str, str]:
    info = FIELDS[field_id]
    hints = FIELD_SUFFIX_HINTS.get(suffix, FIELD_SUFFIX_HINTS["basics"])
    name = info["name"]
    return {
        "field_scope": (
            f"「{name}」は乙4筆記の主要分野のひとつです。{info['scope']}が中心です。"
            f"実践演習では約{info['practice']}問、2026年度過去問では{info['past_2026']}問がこの分野に分類されています（学習用集計）。"
        ),
        "field_basics": (
            f"{name}の{hints['focus']}として、{hints['basics']} "
            f"用語解説の分野ハブ（{name}）から一覧に入り、演習の分野チップを固定して学習してください。"
        ),
        "field_frequent": (
            f"{name}の頻出論点では、{hints['frequent']} "
            "出題範囲表の該当章と演習の誤答タグを突き合わせ、優先順位をつけます。"
        ),
        "field_past": (
            f"{name}の演習では、{hints['past']} "
            f"{BRAND}の過去問・実践演習で分野フィルタを使い、解説を読んだら同型を続けて解きます。"
        ),
        "field_cross": (
            f"{name}と他分野のつながり：{hints['cross']} "
            "例えば指定数量（法令）と引火点（物性）、消火方法（火災）のように、用語の関連リンクで横断します。"
        ),
    }


def body_for_genre(genre: str, heading: str, slug: str) -> str:
    bodies = GENRE_BODIES.get(genre, {})
    raw = bodies.get(heading, "")
    m = FIELD_SLUG_RE.match(slug)
    if m and genre == "分野別対策":
        tpl = field_templates(m.group(1), m.group(2))
        raw = raw.format(**tpl) if raw else ""
    if not raw:
        raw = (
            f"{exam_name()}の「{heading}」について、{genre}の観点で整理します。"
            f"公式の出題範囲と{BRAND}の演習・用語解説を併用し、理解と定着を両立させてください。"
        )
    return raw


def enrich_lead(row: dict[str, str], slug: str) -> str:
    patch = SLUG_PATCHES.get(slug, {})
    title = norm(row.get("title"))
    genre = norm(row.get("genre"))
    custom = slug_lead_text(slug, genre, title)
    if patch.get("lead"):
        lead = patch["lead"]
    elif custom:
        lead = custom
    else:
        outline = GENRE_OUTLINES.get(genre, {})
        lead = norm(outline.get("lead")) or f"{EXAM}の学習・受験を検討している人向けの記事です。"
        lead = lead.replace("◯◯試験", EXAM)
    tags = norm(row.get("tags"))
    if "アフィリエイト" in tags and AFFILIATE_LEAD not in lead:
        lead = AFFILIATE_LEAD + lead
    return lead


def enrich_meta(row: dict[str, str], slug: str) -> str:
    title = norm(row.get("title"))
    genre = norm(row.get("genre"))
    hook = {
        "試験概要": "公式情報の確認と学習の入口",
        "受験・申込": "資格・日程・申込の実務ポイント",
        "合格・難易度": "合格率・合格点の読み方",
        "出題・形式": "出題範囲と試験形式",
        "学習計画": "期間別の学習設計",
        "独学対策": "独学の教材と進め方",
        "過去問活用": "演習・解き直しの手順",
        "分野別対策": "分野別の演習と用語",
        "用語整理": "用語解説の活用法",
        "復習・苦手克服": "復習サイクルと誤答管理",
        "直前・当日": "直前・当日のチェック",
        "注意点・更新": "誤解防止と制度更新",
    }.get(genre, "学習の進め方")
    return f"{title}。{hook}を、{exam_name()}受験者向けに{BRAND}が整理しました。"


def enrich_user_intent(row: dict[str, str], slug: str) -> str:
    title = norm(row.get("title"))
    topic = title.replace(EXAM, "").strip("の") or slug.replace("-", " ")
    return f"「{topic}」を理解し、{BRAND}の演習・用語・関連ガイドへ進みたい。"


def enrich_faqs(row: dict[str, str], slug: str) -> None:
    title = norm(row.get("title"))
    genre = row["genre"]
    faqs = slug_faq_pairs(slug, genre, title)
    if slug == "past-questions-latest-year":
        faqs = [
            (
                "最新年度の過去問はどこで解けますか？",
                f"{BRAND}の過去問一覧（2026年度35問など）から解説付きで確認できます。",
            ),
            (
                "実践演習と過去問はどう使い分けますか？",
                "過去問で本番形式に慣れ、実践演習500問で分野別の量と弱点補強を行ってください。",
            ),
        ]
    for i, (q, a) in enumerate(faqs[:2], start=1):
        a = a.replace("◯◯試験", EXAM)
        row[f"faq_{i}_question"] = q
        row[f"faq_{i}_answer"] = a


def enrich_action_items(row: dict[str, str], slug: str) -> str:
    genre = row["genre"]
    base = {
        "試験概要": "公式受験案内を保存する;出題範囲表を確認する;学習計画記事へ進む",
        "受験・申込": "受験資格を公式表で確認する;申込期限をカレンダー登録する;会場・持ち物をメモする",
        "学習計画": "3分野の週間ローテを決める;実践演習で現在地を測る;復習日を先に確保する",
        "過去問活用": "最新年度過去問を時間計測で解く;誤答理由を分類する;用語解説で混同を解消する",
        "分野別対策": "分野チップ固定で演習する;用語ハブから関連語を読む;正答率80%まで深掘りする",
        "用語整理": "演習で出た語を用語解説で確認する;数字・期限を一覧化する;関連用語を5語セットで読む",
    }.get(genre, "公式情報を確認する;演習で現在地を把握する;用語解説で弱点を補う")
    if slug.startswith("affiliate-"):
        base = "公式出題範囲を確認する;無料コンテンツで不足を把握する;購入前に目次・サンプルを確認する"
    return base


def enrich_row(row: dict[str, str], *, force: bool) -> bool:
    slug = norm(row.get("slug"))
    genre = norm(row.get("genre"))
    if not slug or not genre:
        return False
    changed = False

    new_lead = enrich_lead(row, slug)
    if force or row.get("lead") != new_lead:
        row["lead"] = new_lead
        changed = True

    new_meta = enrich_meta(row, slug)
    if force or is_boilerplate(norm(row.get("meta_description", ""))) or "公式情報の確認ポイントと" in norm(
        row.get("meta_description")
    ):
        row["meta_description"] = new_meta
        changed = True

    patch = SLUG_PATCHES.get(slug, {})
    section_extra = SLUG_SECTION_EXTRA.get(slug, {})
    title = norm(row.get("title"))
    slug_bodies = slug_section_bodies(slug, genre, title)
    for i in range(1, 8):
        heading = norm(row.get(f"section_{i}_heading"))
        if not heading:
            continue
        old = norm(row.get(f"section_{i}_body"))
        if patch.get(heading):
            new_body = patch[heading]
            if heading in section_extra:
                new_body = new_body + "\n\n" + section_extra[heading]
        elif heading in slug_bodies:
            new_body = slug_bodies[heading]
        else:
            new_body = body_for_genre(genre, heading, slug)
        if "アフィリエイト" in norm(row.get("tags")) and AFFILIATE_SECTION_EXTRA not in new_body:
            new_body = new_body + "\n\n" + AFFILIATE_SECTION_EXTRA
        if force or is_boilerplate(old) or old != new_body:
            if old != new_body:
                row[f"section_{i}_body"] = new_body
                changed = True

    old_ai = norm(row.get("action_items"))
    new_ai = enrich_action_items(row, slug)
    if force or old_ai == "公式の受験案内を確認する;実践演習で現在地を把握する;用語解説で弱点を補う":
        if old_ai != new_ai:
            row["action_items"] = new_ai
            changed = True

    new_intent = enrich_user_intent(row, slug)
    if force or "次の学習行動に移りたい" in norm(row.get("user_intent")):
        if row.get("user_intent") != new_intent:
            row["user_intent"] = new_intent
            changed = True

    enrich_faqs(row, slug)

    today = date.today().isoformat()
    note = f"enrich_o4_guide_articles.py で {today} 品質更新（スラッグ別本文・FAQ）。"
    if norm(row.get("revision_note")) != note:
        row["revision_note"] = note
        changed = True

    row["author_profile"] = f"{exam_name()}向けの学習コンテンツ（演習・用語・試験ガイド）を整理する編集チーム"
    row["reviewer_profile"] = "消防試験研究センター・消防庁の公開情報と照合し、サイト内リンクの整合を確認"

    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="定型文以外も上書き")
    args = ap.parse_args()

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        print("guide_articles.csv: no header", file=sys.stderr)
        return 1

    n_changed = 0
    n_boiler = 0
    for row in rows:
        for i in range(1, 8):
            if is_boilerplate(norm(row.get(f"section_{i}_body", ""))):
                n_boiler += 1
        if enrich_row(row, force=args.force):
            n_changed += 1

    print(f"articles: {len(rows)}, boilerplate sections before: {n_boiler}, rows updated: {n_changed}")

    if args.dry_run:
        print("(dry-run: CSV not written)")
        return 0

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
