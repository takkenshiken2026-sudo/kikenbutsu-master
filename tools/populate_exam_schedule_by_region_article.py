#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験日一覧ガイド記事（exam-schedule-by-region）を guide_articles.csv に登録する。"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CSV_PATH = ROOT / "data" / "guide_articles.csv"
SLUG = "exam-schedule-by-region"
TODAY = date.today().isoformat()


def article_row() -> dict[str, str]:
    return {
        "slug": SLUG,
        "genre": "受験・申込",
        "title": "危険物取扱者試験（乙4）の試験日一覧【都道府県別】",
        "meta_description": (
            "危険物取扱者試験（乙4）の試験日を都道府県別に一覧表示。"
            "受験地・申込期間・合格発表予定日を比較できます。"
        ),
        "lead": (
            "危険物取扱者試験（乙種第4類）の試験日・申込期間を、都道府県（支部）別に一覧で確認できます。"
            "申込前は各行の公式リンクで最新情報を必ず確認してください。"
            "支部を決めたあとの逆算学習は試験日程記事で進めてください。"
        ),
        "priority": "14",
        "tags": "受験資格;申込;公式情報",
        "author_name": "乙4マスター編集部",
        "author_profile": (
            "危険物取扱者試験（乙種第4類）の筆記試験に向けた学習設計・演習運用を専門とする編集チーム。"
            "法令・物性・火災予防の三領域を横断し、受験者が迷わない導線づくりを担当しています。"
        ),
        "reviewer_name": "公式情報確認担当",
        "reviewer_profile": (
            "消防試験研究センター・消防庁の公開情報と照合し、"
            "出題傾向とサイト内リンクの整合を確認した担当者です。"
        ),
        "fact_checked_at": TODAY,
        "primary_sources": (
            "消防試験研究センター 危険物取扱者|https://www.shoubo-shiken.or.jp/kikenbutsu/;"
            "試験情報検索|https://shinsei.shoubo-shiken.or.jp/shoubou_ia/iajs9001.do?shibu_cd=38&menjo_kbn=1"
        ),
        "original_note": "exam-schedule-by-region — 試験ガイド配置·日程表は build_article_pages で注入。",
        "user_intent": (
            "本記事を読むと、受験したい都道府県の乙4試験日・申込期間を一覧で比較でき、"
            "公式ページで最新日程を確認する手順が分かります。"
        ),
        "action_items": (
            "都道府県フィルタで受験地を絞り込む;"
            "試験日・申込期間をメモする;"
            "各行の公式リンクで最新情報を確認する;"
            "支部決定後は試験日程記事で4点カレンダーを登録する"
        ),
        "key_points": (
            "都道府県で絞り込み可能;"
            "申込前は公式リンクで再確認;"
            "支部決定後は試験日程記事へ"
        ),
        "update_policy": "試験要項・支部日程の更新時に本文と日程CSVを見直します。",
        "last_reviewed_at": TODAY,
        "next_review_at": TODAY,
        "source_checked_at": TODAY,
        "content_status": "published",
        "revision_note": f"{TODAY}: 試験ガイド配置に変更（一覧中心）",
        "section_1_heading": "一覧の使い方",
        "section_1_body": (
            "下の表は消防試験研究センター公式データをもとに、乙4の試験日を都道府県別に表示しています。"
            "都道府県フィルタで絞り込み、試験日・申込期間・合格発表予定日を確認してください。"
            "表の数値は取得時点の情報です。申込前には必ず「公式」列のリンク先で上書き確認してください（要項で再確認）。"
            "複数の受験地がある都道府県では、同じ試験日でも会場が分かれる場合があります。"
            "申込時に受験地を選べる支部は、要項・申込画面の案内どおりに確認してください。"
        ),
        "section_2_heading": "試験日程記事との使い分け",
        "section_2_body": (
            "都道府県の比較と、決定後の学習逆算は記事を分けます。\n\n"
            "| 論点 | 本記事（試験日一覧） | 試験日程記事 |\n"
            "| --- | --- | --- |\n"
            "| 焦点 | どの支部・いつ受験できるか | 4点カレンダー・12週逆算 |\n"
            "| 使うタイミング | 申込前の支部比較 | 支部決定後の学習計画 |\n"
            "| 出口 | 申込の流れへ | 学習計画へ |\n\n"
            "支部日程を決めたら、exam-schedule記事で申込締切・合格発表を4点カレンダー登録してください。"
        ),
        "section_3_heading": "",
        "section_3_body": "",
        "section_4_heading": "",
        "section_4_body": "",
        "section_5_heading": "",
        "section_5_body": "",
        "section_6_heading": "",
        "section_6_body": "",
        "section_7_heading": "",
        "section_7_body": "",
        "faq_1_question": "乙4はどの都道府県で受験できますか？",
        "faq_1_answer": (
            "全国47都道府県の支部で受験できます。"
            "一覧の都道府県フィルタで絞り込み、各行の公式リンクから最新日程を確認してください。"
            "現住所・勤務地にかかわらず希望する都道府県を選べます。"
            "東京都は中央試験センター含む日程も支部ページに掲載されます（要項で再確認）。"
        ),
        "faq_2_question": "一覧と公式で日程が違う場合は？",
        "faq_2_answer": (
            "必ず公式ページを正本としてください。"
            "本記事の表は取得時点のキャッシュです。支部独自の注意事項や直前の変更は反映されない場合があります。"
            "申込前に各行の公式リンクを開き直し、試験日・申込期間・受験地を再確認してください（要項で再確認）。"
        ),
        "related_links": (
            "exam-schedule:試験日程·逆算12週;"
            "exam-application-flow:申込みの流れ;"
            "exam-venue-and-region:会場·受験地確認;"
            "study-plan:学習計画の立て方"
        ),
    }


def upsert() -> None:
    row = article_row()
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if not fieldnames:
        raise SystemExit(f"missing header: {CSV_PATH}")

    replaced = False
    for idx, existing in enumerate(rows):
        if existing.get("slug") == SLUG:
            rows[idx] = {key: row.get(key, "") for key in fieldnames}
            replaced = True
            break
    if not replaced:
        rows.append({key: row.get(key, "") for key in fieldnames})

    with CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'updated' if replaced else 'added'} {SLUG}")


def main() -> int:
    upsert()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
