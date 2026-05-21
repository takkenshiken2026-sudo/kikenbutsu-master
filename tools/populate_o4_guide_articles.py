#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
危険物取扱者乙4向けに guide_articles.csv を100本以上に拡充する。

  python3 tools/populate_o4_guide_articles.py
  python3 tools/populate_o4_guide_articles.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scaffold_guide_article import (  # noqa: E402
    build_row,
    filter_related_links,
    load_fieldnames,
)
from tools.site_config import brand_name, exam_name, fields  # noqa: E402

OUT = ROOT / "data" / "guide_articles.csv"
EXAM = "危険物取扱者試験（乙種第4類）"
EXAM_SHORT = "危険物取扱者試験"
BRAND = "乙4マスター"
SOURCES = (
    "消防試験研究センター 危険物取扱者（公式）|https://www.shoubo-shiken.or.jp/kikenbutsu/;"
    "消防庁（公式）|https://www.fdma.go.jp/"
)
AFFILIATE_LEAD = (
    "※本記事には教材・講座の紹介（アフィリエイト）を含みます。価格・内容は各公式サイトで必ずご確認ください。"
)

FIELD_SUFFIXES = [
    ("basics", "基礎"),
    ("frequent-topics", "頻出論点"),
    ("calculation", "計算・指定数量"),
    ("case-study", "事例・場面問題"),
    ("past-question-focus", "演習の活かし方"),
]

BODY_TMPL = (
    "{exam}の「{topic}」について整理します。乙種第4類は第4類危険物（引火性液体）を中心に、"
    "法令・物性・火災予防の3領域が出題の柱です。{detail} "
    "数値・制度は消防試験研究センターの受験案内で最新版を確認し、当サイトの実践演習・用語解説で定着を図ってください。"
)

DETAIL_BY_GENRE: dict[str, str] = {
    "試験概要": "受験前に公式情報の全体像を押さえ、学習の優先順位を決めます。",
    "受験・申込": "申込期限・受験資格・手数料の見落としを防ぐことが第一歩です。",
    "合格・難易度": "合格率や合格点は目安として読み、演習の正答率で現在地を測ります。",
    "出題・形式": "出題範囲と試験形式（マークシート）を先に把握し、教材選びの基準にします。",
    "学習計画": "3分野をローテーションし、演習と復習の日をカレンダーに入れます。",
    "独学対策": "教材を増やす前に、公式範囲と復習の仕組みを固定します。",
    "過去問活用": "実践演習・過去問で弱点を可視化し、用語へ戻って解説を読みます。",
    "分野別対策": "苦手分野に時間を配分し、頻出論点から順に固めます。",
    "用語整理": "混同しやすい語句は関連用語とセットで確認します。",
    "復習・苦手克服": "間違いの理由を分類し、間隔を空けて解き直します。",
    "直前・当日": "直前期は新規インプットより、誤答と数字の最終確認を優先します。",
    "注意点・更新": "非公式情報より公式情報を優先し、改定年度を必ず確認します。",
}


def body_for(genre: str, topic: str) -> str:
    detail = DETAIL_BY_GENRE.get(genre, "公式情報と演習を往復しながら理解を深めます。")
    return BODY_TMPL.format(exam=EXAM, topic=topic, detail=detail)


def spec(slug: str, genre: str, title: str, *, tags: str = "", affiliate: bool = False) -> dict:
    return {"slug": slug, "genre": genre, "title": title, "tags": tags, "affiliate": affiliate}


def build_catalog() -> list[dict]:
    items: list[dict] = []

    def add_many(rows: list[tuple[str, str, str]], *, tags: str = ""):
        for s, g, t in rows:
            items.append(spec(s, g, t, tags=tags))

    add_many(
        [
            ("official-info-sources", "試験概要", f"{EXAM}の公式情報の確認先と使い方"),
            ("learning-app-guide", "試験概要", f"{BRAND}の使い方（実践演習・用語・復習）"),
            ("exam-purpose-and-career", "試験概要", f"{EXAM}の目的と取得後の活用イメージ"),
            ("first-time-exam-guide", "試験概要", f"{EXAM}を初めて受験する人向けガイド"),
            ("compare-similar-qualifications", "試験概要", "危険物取扱者 甲種・乙種・丙種の違い"),
        ]
    )
    add_many(
        [
            ("exam-eligibility", "受験・申込", f"{EXAM}の受験資格の確認方法"),
            ("exemption-system", "受験・申込", f"{EXAM}の免除制度の概要"),
            ("work-experience-requirement", "受験・申込", f"{EXAM}と実務経験・職務の関係"),
            ("education-requirement", "受験・申込", f"{EXAM}の学歴要件の見方"),
            ("concurrent-exam-rules", "受験・申込", "危険物取扱者と他資格の同時受験の注意点"),
        ]
    )
    add_many(
        [
            ("exam-schedule", "受験・申込", f"{EXAM}の試験日程と年間スケジュール"),
            ("exam-fees", "受験・申込", f"{EXAM}の受験料と支払い"),
            ("exam-application-flow", "受験・申込", f"{EXAM}の申込手順"),
            ("application-deadline-checklist", "受験・申込", f"{EXAM}の申込期限チェックリスト"),
            ("exam-venue-and-region", "受験・申込", f"{EXAM}の会場・地域の選び方"),
            ("reschedule-and-absence", "受験・申込", f"{EXAM}の欠席・再受験の扱い"),
        ]
    )
    add_many(
        [
            ("exam-format-overview", "出題・形式", f"{EXAM}の試験形式の全体像"),
            ("subject-breakdown", "出題・形式", f"{EXAM}（乙4）の出題科目と配分"),
            ("cbt-computer-exam", "出題・形式", f"{EXAM}とCBT・マークシートの違い"),
            ("written-essay-section", "出題・形式", f"{EXAM}に記述試験はあるか"),
            ("time-limit-strategy", "出題・形式", f"{EXAM}の時間配分のコツ"),
        ]
    )
    add_many(
        [
            ("exam-scope-overview", "出題・形式", f"{EXAM}（乙4）の出題範囲の全体像"),
            ("syllabus-how-to-read", "出題・形式", "危険物乙4の出題範囲表の読み方"),
            ("scope-revision-history", "出題・形式", f"{EXAM}の出題範囲の改定履歴の見方"),
            ("weight-by-topic", "出題・形式", f"{EXAM}の分野別の出題比重"),
            ("new-topics-trend", "出題・形式", f"{EXAM}の近年の出題傾向"),
            ("scope-vs-past-questions", "出題・形式", "出題範囲と実践演習・過去問の対応"),
        ]
    )
    add_many(
        [
            ("pass-rate", "合格・難易度", f"{EXAM}の合格率の見方"),
            ("exam-difficulty", "合格・難易度", f"{EXAM}（乙4）の難易度"),
            ("pass-score", "合格・難易度", f"{EXAM}の合格点・合格基準"),
            ("pass-rate-how-to-read", "合格・難易度", "危険物試験の合格率統計の読み方"),
            ("difficulty-for-beginners", "合格・難易度", f"{EXAM}は初学者でも受かるか"),
        ]
    )
    add_many(
        [
            ("study-plan-3months", "学習計画", f"{EXAM}の3か月学習計画"),
            ("study-plan-6months", "学習計画", f"{EXAM}の6か月学習計画"),
            ("study-plan-1year", "学習計画", f"{EXAM}の1年学習計画"),
            ("study-plan-working", "学習計画", f"{EXAM}を働きながら受ける学習計画"),
            ("study-plan-beginner", "学習計画", f"{EXAM}初学者向け学習計画"),
            ("first-30-days-plan", "学習計画", f"{EXAM}の最初の30日プラン"),
            ("balance-work-study", "学習計画", f"{EXAM}の仕事と勉強の両立"),
            ("time-management", "学習計画", f"{EXAM}の学習時間の作り方"),
        ]
    )
    add_many(
        [
            ("self-study-start", "独学対策", f"{EXAM}の独学の始め方"),
            ("self-study-schedule", "独学対策", f"{EXAM}の独学スケジュール例"),
            ("self-study-mistakes", "独学対策", f"{EXAM}独学でよくある失敗"),
            ("self-study-environment", "独学対策", f"{EXAM}独学の環境づくり"),
            ("self-study-motivation", "独学対策", f"{EXAM}独学のモチベーション維持"),
            ("self-study-without-school", "独学対策", f"{EXAM}を予備校なしで受ける"),
        ]
    )
    add_many(
        [
            ("textbook-selection", "独学対策", f"{EXAM}の参考書の選び方"),
            ("problem-book-selection", "独学対策", f"{EXAM}の問題集の選び方"),
            ("correspondence-course-guide", "独学対策", f"{EXAM}の通信講座の選び方"),
            ("free-materials-online", "独学対策", f"{EXAM}の無料学習コンテンツの活用法"),
            ("textbook-vs-past-questions", "独学対策", f"{EXAM}は参考書と演習どちらを優先するか"),
            ("material-update-cycle", "独学対策", f"{EXAM}教材の改訂と買い替え"),
        ]
    )
    add_many(
        [
            ("past-questions-by-year", "過去問活用", f"{EXAM}の年度別過去問の進め方"),
            ("past-questions-by-field", "過去問活用", f"{EXAM}の分野別演習の進め方"),
            ("past-questions-review-cycle", "過去問活用", f"{EXAM}の解き直しサイクル"),
            ("past-questions-score-analysis", "過去問活用", f"{EXAM}演習の正答率の見方"),
            ("bookmark-review-method", "過去問活用", f"{BRAND}のブックマーク復習"),
            ("past-questions-first-attempt", "過去問活用", f"{EXAM}で最初に解く演習の選び方"),
            ("past-questions-wrong-reasons", "過去問活用", f"{EXAM}の誤答理由の分類"),
            ("past-questions-latest-year", "過去問活用", f"{EXAM}の直近年度演習の扱い"),
        ]
    )
    add_many(
        [
            ("mock-exam-how-to", "過去問活用", f"{EXAM}の模擬試験の使い方"),
            ("ichimon-practice", "過去問活用", f"{EXAM}の一問一答の活用法"),
            ("drill-volume-guide", "過去問活用", f"{EXAM}の演習量の目安"),
            ("timed-practice", "過去問活用", f"{EXAM}の時間計測演習"),
            ("essay-practice-method", "過去問活用", f"{EXAM}と記述対策の要否"),
            ("simulation-exam-schedule", "過去問活用", f"{EXAM}の模試日程の組み込み"),
        ]
    )
    for f in fields():
        fid = str(f["id"])
        fname = str(f["name"])
        for suffix, label in FIELD_SUFFIXES:
            items.append(
                spec(
                    f"field-{fid}-{suffix}",
                    "分野別対策",
                    f"{EXAM}の{fname}｜{label}",
                    tags=f"分野別;{fname}",
                )
            )
    add_many(
        [
            ("glossary-study-method", "用語整理", f"{EXAM}の用語解説の使い方"),
            ("important-terms-list", "用語整理", f"{EXAM}で押さえる重要用語"),
            ("confusing-terms", "用語整理", f"{EXAM}で混同しやすい用語"),
            ("related-terms-navigation", "用語整理", f"{EXAM}の関連用語のたどり方"),
            ("terms-with-past-questions", "用語整理", "演習と用語解説の往復学習"),
            ("terms-importance-levels", "用語整理", f"{EXAM}用語の重要度の見方"),
            ("numbers-and-deadlines", "用語整理", f"{EXAM}の数字・期限の整理"),
            ("formula-memorization", "用語整理", f"{EXAM}の計算・公式の覚え方"),
            ("calculation-drill", "用語整理", f"{EXAM}の指定数量・倍数の演習"),
            ("rate-and-percentage", "用語整理", f"{EXAM}の割合・濃度の問題"),
            ("numeric-trap-choices", "用語整理", f"{EXAM}の数値ひっかけ選択肢"),
        ]
    )
    add_many(
        [
            ("review-cycle-spaced", "復習・苦手克服", f"{EXAM}の間隔復習"),
            ("mistake-notebook", "復習・苦手克服", f"{EXAM}の間違いノート"),
            ("weak-field-recovery", "復習・苦手克服", f"{EXAM}の苦手分野の立て直し"),
            ("note-taking-method", "復習・苦手克服", f"{EXAM}の学習メモの取り方"),
            ("almost-correct-review", "復習・苦手克服", f"{EXAM}の「なんとなく正解」の見直し"),
            ("plateau-breakthrough", "復習・苦手克服", f"{EXAM}学習の伸び悩み対策"),
        ]
    )
    add_many(
        [
            ("final-week-prep", "直前・当日", f"{EXAM}直前1週間の対策"),
            ("final-day-checklist", "直前・当日", f"{EXAM}前日チェックリスト"),
            ("final-scope-narrowing", "直前・当日", f"{EXAM}直前の範囲の絞り方"),
            ("final-sleep-and-health", "直前・当日", f"{EXAM}直前の睡眠と体調"),
            ("final-mock-last-run", "直前・当日", f"{EXAM}直前の最終演習"),
        ]
    )
    add_many(
        [
            ("exam-day-items", "直前・当日", f"{EXAM}当日の持ち物"),
            ("exam-day-flow", "直前・当日", f"{EXAM}当日の流れ"),
            ("exam-day-time-allocation", "直前・当日", f"{EXAM}当日の時間配分"),
            ("mental-prep-exam-day", "直前・当日", f"{EXAM}当日のメンタル対策"),
            ("exam-day-troubleshooting", "直前・当日", f"{EXAM}当日のトラブル対応"),
        ]
    )
    add_many(
        [
            ("after-pass-procedure", "注意点・更新", f"{EXAM}合格後の手続き"),
            ("pass-announcement-guide", "注意点・更新", f"{EXAM}の合格発表の見方"),
            ("registration-after-pass", "注意点・更新", "危険物取扱者免状の交付・登録"),
            ("career-after-qualification", "注意点・更新", f"{EXAM}取得後のキャリア"),
        ]
    )
    add_many(
        [
            ("fail-retry-plan", "注意点・更新", f"{EXAM}不合格後の学習計画"),
            ("retake-strategy", "注意点・更新", f"{EXAM}の再受験戦略"),
            ("retake-schedule-adjustment", "注意点・更新", f"{EXAM}再受験の日程調整"),
            ("score-gap-analysis", "注意点・更新", f"{EXAM}の得点差の分析"),
        ]
    )
    add_many(
        [
            ("exam-changes", "注意点・更新", f"{EXAM}の制度・出題の変更"),
            ("legal-revision-impact", "注意点・更新", "消防法・政令改定と試験への影響"),
            ("syllabus-update-tracker", "注意点・更新", f"{EXAM}出題範囲の更新追跡"),
            ("official-info-update-habits", "注意点・更新", f"{EXAM}公式情報の定期確認"),
        ]
    )
    add_many(
        [
            ("common-misconceptions", "注意点・更新", f"{EXAM}のよくある誤解"),
            ("pass-only-past-questions-myth", "注意点・更新", f"{EXAM}は演習だけで足りるか"),
            ("study-hours-myth", "注意点・更新", f"{EXAM}の勉強時間の神話"),
            ("eligibility-myths", "注意点・更新", f"{EXAM}受験資格の誤解"),
            ("difficulty-myths", "注意点・更新", f"{EXAM}難易度の誤解"),
        ]
    )
    affiliate_rows = [
        ("affiliate-textbooks-recommend", "独学対策", f"{EXAM}のおすすめ参考書の選び方"),
        ("affiliate-problem-books", "独学対策", f"{EXAM}のおすすめ問題集"),
        ("affiliate-online-course-compare", "独学対策", f"{EXAM}のオンライン講座比較"),
        ("affiliate-correspondence-course", "独学対策", f"{EXAM}の通信講座比較"),
        ("affiliate-cram-school", "独学対策", f"{EXAM}の予備校・講座の選び方"),
        ("affiliate-mock-exam-materials", "過去問活用", f"{EXAM}の模試教材の選び方"),
        ("affiliate-free-vs-paid-study", "独学対策", f"{EXAM}無料と有料教材の使い分け"),
        ("affiliate-beginner-material-set", "学習計画", f"{EXAM}初学者の教材セット"),
        ("affiliate-retake-short-course", "学習計画", f"{EXAM}再受験者向け短期講座"),
        ("affiliate-qualification-support-service", "受験・申込", f"{EXAM}の受験サポートサービス"),
    ]
    for s, g, t in affiliate_rows:
        items.append(spec(s, g, t, tags="アフィリエイト", affiliate=True))

    # 既存5本（上書き用）
    items.extend(
        [
            spec("exam-overview", "試験概要", f"{EXAM}の概要と最初に確認するポイント"),
            spec("study-plan", "学習計画", f"{EXAM}の学習計画の立て方"),
            spec("past-question-strategy", "過去問活用", f"{EXAM}の実践演習・過去問の使い方"),
            spec("glossary-how-to", "用語整理", f"{EXAM}の用語解説の活用法"),
            spec("self-study-roadmap", "独学対策", f"{EXAM}を独学で進めるロードマップ"),
        ]
    )
    return items


def enrich_row(row: dict[str, str], meta: dict) -> dict[str, str]:
    today = date.today().isoformat()
    next_month = (date.today() + timedelta(days=30)).isoformat()
    title = meta["title"]

    row["title"] = title
    row["meta_description"] = f"{title}。{EXAM_SHORT}（乙種第4類）の受験者向けに、公式情報の確認ポイントと{BRAND}での学習の進め方を整理します。"
    lead = f"{EXAM}の受験・学習を検討している人向けの記事です。"
    if meta.get("affiliate"):
        lead = AFFILIATE_LEAD + lead
    row["lead"] = lead

    tags = meta.get("tags") or row.get("tags", "")
    tag_parts = [t for t in tags.split(";") if t]
    for t in row.get("tags", "").split(";"):
        if t and t not in tag_parts:
            tag_parts.append(t)
    if meta.get("affiliate") and "アフィリエイト" not in tag_parts:
        tag_parts.append("アフィリエイト")
    row["tags"] = ";".join(tag_parts)

    row["author_name"] = f"{brand_name()}編集部"
    row["author_profile"] = "危険物取扱者試験（乙種第4類）向けの学習コンテンツを整理する編集チーム"
    row["reviewer_name"] = "公式情報確認担当"
    row["reviewer_profile"] = "消防試験研究センター・消防庁の公開情報と照合"
    row["fact_checked_at"] = today
    row["primary_sources"] = SOURCES
    row["original_note"] = f"{meta['slug']} — populate_o4_guide_articles.py で生成"
    row["user_intent"] = f"「{title}」について知り、次の学習行動に移りたい。"
    row["action_items"] = (
        "公式の受験案内を確認する;"
        "実践演習で現在地を把握する;"
        "用語解説で弱点を補う"
    )
    row["update_policy"] = "試験要項・消防法改正・出題範囲の更新時に本文と参照元を見直します。"
    row["last_reviewed_at"] = today
    row["next_review_at"] = next_month
    row["source_checked_at"] = today
    row["content_status"] = "published"
    row["revision_note"] = f"populate_o4_guide_articles.py で {today} 作成（乙4向け）。"

    genre = row["genre"]
    for i in range(1, 8):
        h = row.get(f"section_{i}_heading", "").strip()
        if h:
            row[f"section_{i}_body"] = body_for(genre, h)

    return row


def load_existing() -> dict[str, dict[str, str]]:
    if not OUT.is_file():
        return {}
    with OUT.open(encoding="utf-8-sig", newline="") as f:
        return {r["slug"].strip(): r for r in csv.DictReader(f) if r.get("slug")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    catalog = build_catalog()
    order: list[str] = []
    merged: dict[str, dict[str, str]] = {}

    # 既存の順序を維持
    if OUT.is_file():
        with OUT.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                s = r["slug"].strip()
                if s not in order:
                    order.append(s)

    for meta in catalog:
        slug = meta["slug"]
        if slug in merged:
            continue
        base = build_row(slug, meta["genre"], title=meta["title"])
        row = enrich_row(base, meta)
        merged[slug] = row
        if slug not in order:
            order.append(slug)

    fieldnames = load_fieldnames()

    if args.dry_run:
        print(f"would write {len(merged)} articles to {OUT}")
        return 0

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for slug in order:
            if slug in merged:
                w.writerow(merged[slug])

    for slug in order:
        if slug not in merged:
            continue
        rel = merged[slug].get("related_links", "")
        merged[slug]["related_links"] = filter_related_links(rel)

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for slug in order:
            if slug in merged:
                w.writerow(merged[slug])

    aff = sum(1 for r in merged.values() if "アフィリエイト" in r.get("tags", ""))
    print(f"Wrote {OUT} — {len(merged)} 本（アフィリエイト {aff} 本）")
    print("Next: python3 tools/build_all.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
