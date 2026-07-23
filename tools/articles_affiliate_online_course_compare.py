#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extra HTML for affiliate-online-course-compare (A8 online course comparison)."""

from __future__ import annotations

import html

AFFILIATE_REL = "nofollow sponsored noopener noreferrer"

ONSUKU_A8 = (
    "https://onsuku.jp/training/otu4"
    "?a8=MISVmIytjWpCKupI2Uf3uapuoPPNfsoVSUf.yszQv.BtjsSw6sc02WKMT-Pbcbof2._WQXS72ISVGs00000018694001"
)
STUDYING_AFB = "https://t.afi-b.com/visit.php?a=y7404W-O2449818&p=P984775K"
JOHO_A8 = (
    "https://px.a8.net/svt/ejp?a8mat=4B3TF0+DUBYQQ+4LOQ+BW0YB"
    "&a8ejpredirect=https%3A%2F%2Fwww.joho-gakushu.jp%2Fsmartinfo%2Fsmart_lineup.php"
)

# 各講座LP掲載の画像（公式サイトのURL）
ONSUKU_IMAGE = "https://s3.ap-northeast-1.amazonaws.com/onsuku.jp/img/parts/training/top/thumb_otu4_top.jpg"
JOHO_IMAGE = "https://www.joho-gakushu.or.jp/kikenbutu-otu4/img/newtop_img_009.jpg"


def _cta(href: str, label: str) -> str:
    return (
        f'<p class="affiliate-course-cta">'
        f'<a class="related-link affiliate-course-link" href="{html.escape(href)}" target="_blank" '
        f'rel="{AFFILIATE_REL}">{html.escape(label)}</a></p>'
    )


def _card(
    *,
    rank: str,
    href: str,
    image_src: str,
    image_alt: str,
    title_html: str,
    summary: str,
    cta_label: str,
) -> str:
    return (
        '<article class="affiliate-course-card" role="listitem">'
        f'<a class="affiliate-course-thumb" href="{html.escape(href)}" target="_blank" rel="{AFFILIATE_REL}">'
        f'<img src="{html.escape(image_src)}" alt="{html.escape(image_alt)}" width="640" height="360" '
        'loading="lazy" decoding="async">'
        "</a>"
        f'<div class="affiliate-course-card-body">'
        f'<p class="affiliate-course-rank">{html.escape(rank)}</p>'
        f"<h3>{title_html}</h3>"
        f"<p>{html.escape(summary)}</p>"
        + _cta(href, cta_label)
        + "</div></article>"
    )


def build_extra_html() -> str:
    rows = [
        ("料金の考え方", "単講座＋定額受け放題（ウケホーダイ）も選択可※", "7,700円（税込）一括・申込から3年間視聴"),
        ("講義動画", "全66回・約7.5時間", "約7時間（SMARTビデオ）"),
        ("演習", "オリジナル356問（動画と連動）", "一問一答の答練＋解説（約2時間）"),
        ("学習支援", "進捗管理・キーワード検索・復習・教材DL", "進捗・復習チェック・メモ・音声DL"),
        ("体験・導線", "無料体験あり（各公式サイトでご確認ください）", "低価格・長期視聴で再学習しやすい"),
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
    card_a = _card(
        rank="講座A",
        href=ONSUKU_A8,
        image_src=ONSUKU_IMAGE,
        image_alt="オンスク.JP 危険物乙4オンライン通信講座のイメージ",
        title_html="オンスク.JP<br>危険物乙4オンライン通信講座",
        summary="動画・演習・進捗管理をスマホ中心に回したい方向け。",
        cta_label="公式サイトで詳細を見る（無料体験）",
    )
    card_b = _card(
        rank="講座B",
        href=JOHO_A8,
        image_src=JOHO_IMAGE,
        image_alt="情報学習院 危険物取扱者(乙種4類) SMART合格講座のイメージ",
        title_html="情報学習院<br>SMART合格講座（乙種4類）",
        summary="一括7,700円・3年視聴でコストを抑えたい方向け。",
        cta_label="公式サイトで詳細を見る",
    )
    return (
        '<section class="seo-article-section affiliate-course-block" '
        'aria-labelledby="affiliate-course-compare-title">'
        '<h2 id="affiliate-course-compare-title">乙4オンライン講座2社の比較</h2>'
        '<p class="affiliate-course-note">'
        "価格・プラン・返品条件は各公式サイトの最新表示を優先してください。"
        "本表は2026年5月時点の公開情報に基づく整理です。"
        "カード画像は各講座公式ページの掲載素材です。</p>"
        '<div class="affiliate-course-hero" role="list">'
        f"{card_a}{card_b}"
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
