#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extra HTML for affiliate-online-course-compare (A8 online course comparison)."""

from __future__ import annotations

import html

AFFILIATE_REL = "nofollow sponsored noopener noreferrer"

ONSUKU_A8 = (
    "https://px.a8.net/svt/ejp?a8mat=4B3TF0+DUXECI+408S+BW0YB"
    "&a8ejpredirect=https%3A%2F%2Fonsuku.jp%2Ftraining%2Fotu4"
)
JOHO_A8 = (
    "https://px.a8.net/svt/ejp?a8mat=4B3TF0+DUBYQQ+4LOQ+BW0YB"
    "&a8ejpredirect=https%3A%2F%2Fwww.joho-gakushu.or.jp%2Fkikenbutu-otu4%2F"
    "%3Futm_source%3DAffi%26utm_medium%3Dlist%26utm_campaign%3D01"
)


def _cta(href: str, label: str) -> str:
    return (
        f'<p class="affiliate-course-cta">'
        f'<a class="related-link affiliate-course-link" href="{html.escape(href)}" target="_blank" '
        f'rel="{AFFILIATE_REL}">{html.escape(label)}</a></p>'
    )


def build_extra_html() -> str:
    rows = [
        ("料金の考え方", "単講座＋定額受け放題（ウケホーダイ）も選択可※", "7,700円（税込）一括・申込から3年間視聴"),
        ("講義動画", "全66回・約7.5時間", "約7時間（SMARTビデオ）"),
        ("演習", "オリジナル356問（動画と連動）", "一問一答の答練＋解説（約2時間）"),
        ("学習支援", "進捗管理・キーワード検索・復習・教材DL", "進捗・復習チェック・メモ・音声DL"),
        ("体験・導線", "無料体験あり（公式で要確認）", "低価格・長期視聴で再学習しやすい"),
        ("向いている人", "問題量で固めたい／他資格もまとめて受講したい", "まず安く始めたい／初学者向けの丁寧な解説重視"),
    ]
    table_rows = "".join(
        "<tr>"
        f"<th scope=\"row\">{html.escape(k)}</th>"
        f"<td>{html.escape(a)}</td>"
        f"<td>{html.escape(b)}</td>"
        "</tr>"
        for k, a, b in rows
    )
    return (
        '<section class="seo-article-section affiliate-course-block" '
        'aria-labelledby="affiliate-course-compare-title">'
        '<h2 id="affiliate-course-compare-title">乙4オンライン講座2社の比較</h2>'
        '<p class="affiliate-course-note">'
        "価格・プラン・返品条件は各公式サイトの最新表示を優先してください。"
        "本表は2026年5月時点の公開情報に基づく整理です。</p>"
        '<div class="affiliate-course-hero" role="list">'
        '<article class="affiliate-course-card" role="listitem">'
        '<p class="affiliate-course-rank">講座A</p>'
        "<h3>オンスク.JP<br>危険物乙4オンライン通信講座</h3>"
        "<p>動画・演習・進捗管理をスマホ中心に回したい方向け。</p>"
        + _cta(ONSUKU_A8, "公式サイトで詳細を見る（無料体験）")
        + "</article>"
        '<article class="affiliate-course-card" role="listitem">'
        '<p class="affiliate-course-rank">講座B</p>'
        "<h3>情報学習院<br>SMART合格講座（乙種4類）</h3>"
        "<p>一括7,700円・3年視聴でコストを抑えたい方向け。</p>"
        + _cta(JOHO_A8, "公式サイトで詳細を見る")
        + "</article>"
        "</div>"
        '<div class="affiliate-course-table-wrap">'
        '<table class="seo-compare-table">'
        "<caption>オンスク.JPと情報学習院 SMART合格講座の比較</caption>"
        "<thead><tr>"
        '<th scope="col">比較項目</th>'
        '<th scope="col">オンスク.JP</th>'
        '<th scope="col">情報学習院 SMART</th>'
        "</tr></thead>"
        f"<tbody>{table_rows}</tbody>"
        "</table></div>"
        '<p class="affiliate-course-note">※ウケホーダイは複数講座の定額プランです。乙4単体の料金は公式でご確認ください。</p>'
        "</section>"
    )
