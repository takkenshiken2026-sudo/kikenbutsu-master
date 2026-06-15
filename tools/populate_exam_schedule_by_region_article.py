#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exam-schedule-by-region は廃止。特設ページは tools/build_exam_schedule_page.py を使用。"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.exam_schedule_regions import official_schedule_url, region_blocks  # noqa: E402

CSV_PATH = ROOT / "data" / "guide_articles.csv"
SLUG = "exam-schedule-by-region"
TODAY = date.today().isoformat()


def prefecture_links_table() -> str:
    lines = [
        "| 地方 | 都道府県 | 公式の試験日程 |",
        "| --- | --- | --- |",
    ]
    for block, items in region_blocks():
        for idx, (code, name, _) in enumerate(items):
            region_cell = block if idx == 0 else ""
            url = official_schedule_url(code)
            lines.append(f"| {region_cell} | {name} | [試験日程一覧]({url}) |")
    return "\n".join(lines)


def article_row() -> dict[str, str]:
    links = prefecture_links_table()
    return {
        "slug": SLUG,
        "genre": "受験・申込",
        "title": "危険物取扱者試験（乙4）の試験日一覧【都道府県別】",
        "meta_description": (
            "危険物取扱者試験（乙4）の試験日を都道府県別に整理。"
            "消防試験研究センター公式の試験日程一覧へのリンクと、"
            "乙4行の見方・支部選びの注意を解説します。"
        ),
        "lead": (
            "危険物取扱者試験（乙種第4類）の試験日は、都道府県（支部）ごとに異なります。"
            "正本は一般財団法人 消防試験研究センターの試験日程一覧です。"
            "本記事では47都道府県への公式リンク、乙4の行の見方、"
            "サイト内の自動集計一覧の使い方をまとめます。"
            "支部を決めたあとの逆算学習は試験日程記事で確認してください。"
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
        "original_note": "exam-schedule-by-region — populate_exam_schedule_by_region_article.py で生成。",
        "user_intent": (
            "本記事を読むと、受験したい都道府県の公式試験日程ページを開き、"
            "乙4の試験日・申込期間を自分の行だけ転記できるようになります。"
            "全国一覧表で近い日程も比較できます。"
        ),
        "action_items": (
            "受験したい都道府県の公式リンクを開く;"
            "乙4の行から試験日・申込期間・合格発表予定日をメモする;"
            "支部を決めたら試験日程記事で4点カレンダーを登録する;"
            "申込前に要項PDFで手数料・方式を再確認する"
        ),
        "update_policy": "試験要項・支部日程の更新時に本文・公式リンク・自動集計CSVを見直します。",
        "last_reviewed_at": TODAY,
        "next_review_at": TODAY,
        "source_checked_at": TODAY,
        "content_status": "published",
        "revision_note": f"{TODAY}: 都道府県別試験日ハブ新規公開",
        "section_1_heading": "試験日の正本は消防試験研究センター",
        "section_1_body": (
            "危険物取扱者試験（乙種第4類）の試験日・申込期間・合格発表予定日は、"
            "一般財団法人 消防試験研究センターの試験日程一覧が正本です。\n\n"
            "| 確認項目 | 公式での場所 |\n"
            "| --- | --- |\n"
            "| 試験日 | 各都道府県ページの「試験日」列 |\n"
            "| 申込期間 | 「申請受付期間」列 |\n"
            "| 受験地 | 「受験地」列（市区町村名） |\n"
            "| 合格発表 | 「合格発表予定日」列 |\n\n"
            "現住所・勤務地にかかわらず、希望する都道府県で受験できます。"
            "非公式まとめサイトの日程は、必ず公式ページと照合してから使ってください。"
        ),
        "section_2_heading": "都道府県別の公式リンク一覧",
        "section_2_body": (
            "下表から受験したい都道府県の公式ページを開いてください。"
            "各リンクは消防試験研究センター試験情報検索（危険物取扱者）です。\n\n"
            f"{links}"
        ),
        "section_3_heading": "公式ページで乙4の行を見つける",
        "section_3_body": (
            "都道府県ページを開いたら、次の手順で乙4の日程を確認します。\n\n"
            "1. 表の「乙種」欄に「乙４」とある行だけを見る\n"
            "2. 同じ行の「受験地」「試験日」「申請受付期間」をメモする\n"
            "3. 「合格発表予定日」もカレンダーに登録する\n"
            "4. 受験地注意事項・試験注意事項のリンクがあれば開く\n\n"
            "| 列名 | 乙4受験者が見るポイント |\n"
            "| --- | --- |\n"
            "| 受験地 | 会場の割当は受験票が正本。申込時に支部・回を確定 |\n"
            "| 試験日 | 令和表記（例：R08.09.15(日)）を西暦に直してカレンダー登録 |\n"
            "| 申請受付期間 | 締切日の数日前までに書類・手数料を揃える |\n"
            "| 試験種類 | 乙４の文字がある行が対象 |\n\n"
            "1つの都道府県に複数の受験地があり、試験日が同じ日でも会場が分かれている場合があります。"
            "申込時に受験地を選べる支部は、要項・申込画面の案内どおりに確認してください（要項で再確認）。"
        ),
        "section_4_heading": "支部（都道府県）を選ぶときの注意",
        "section_4_body": (
            "支部選びで迷いやすい点を整理します。\n\n"
            "| 論点 | ポイント |\n"
            "| --- | --- |\n"
            "| 居住地以外 | 全国どの支部でも受験可能 |\n"
            "| 日程の違い | 同じ月でも都道府県によって試験日が異なる |\n"
            "| 申込締切 | 支部・回ごとに異なる。愛媛例では試験日の約2週間前 |\n"
            "| 統一試験とCBT | 支部案内・要項で方式を確認 |\n"
            "| 手数料 | 乙種は5,300円（要項で再確認） |\n\n"
            "遠方支部を選ぶ場合は、会場アクセスは受験票と公式案内で確認します。"
            "会場名・交通の詳細は exam-venue-and-region 記事を参照してください。"
        ),
        "section_5_heading": "試験日程記事との使い分け",
        "section_5_body": (
            "都道府県の探索と、決定後の学習逆算は記事を分けます。\n\n"
            "| 論点 | 本記事（都道府県別） | 試験日程記事 |\n"
            "| --- | --- | --- |\n"
            "| 焦点 | どの支部・いつ受験できるか | 4点カレンダー・12週逆算 |\n"
            "| 使うタイミング | 申込前の支部比較 | 支部決定後の学習計画 |\n"
            "| 成果物 | 公式行の転記 | 週次演習表 |\n"
            "| 出口 | 申込の流れへ | 学習計画へ |\n\n"
            "例えば愛媛支部で9/15（日）試験を選んだら、"
            "本記事で日程を転記したあと、試験日程記事で申込締切・合格発表を4点カレンダー登録し、"
            "学習計画記事で残り週数から三領域の配分を決める流れが定番です。"
        ),
        "section_6_heading": "",
        "section_6_body": "",
        "section_7_heading": "",
        "section_7_body": "",
        "faq_1_question": "乙4はどの都道府県で受験できますか？",
        "faq_1_answer": (
            "全国47都道府県の支部（東京都は中央試験センター含む日程）で受験できます。"
            "本記事の都道府県リンクから公式の試験日程一覧を開き、"
            "乙４の行がある日程を確認してください。"
            "現住所・勤務地にかかわらず希望する都道府県を選べます（要項で再確認）。"
        ),
        "faq_2_question": "サイト内の自動集計一覧は公式と違ったらどうしますか？",
        "faq_2_answer": (
            "必ず公式ページを正本としてください。"
            "自動集計は公式データの取得時点のキャッシュであり、"
            "直前の変更や支部独自の注意事項は反映されない場合があります。"
            "申込前には都道府県リンクから公式を開き直し、"
            "試験日・申込期間・受験地を再確認してください（要項で再確認）。"
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
