#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""乙4試験日特設ページ exam-dates/index.html を生成する。"""

from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.exam_schedule_page_content import (  # noqa: E402
    META_DESCRIPTION,
    PAGE_LEAD,
    PAGE_SLUG,
    PAGE_TITLE,
    faq_items,
    page_sections,
)
from tools.exam_schedule_table import exam_schedule_table_html, latest_fetched_at, load_schedule_rows  # noqa: E402
from tools.html_footer import (  # noqa: E402
    ROBOTS_INDEX_FOLLOW,
    breadcrumb_html,
    shell_body_class,
    site_page_footer,
    site_page_header,
    site_page_wrap_close,
    site_page_wrap_open,
    site_scroll_top_html,
)
from tools.knowledge_hub_seo import faq_section_html  # noqa: E402
from tools.seo_body_markup import seo_section_body_html  # noqa: E402
from tools.seo_editorial_chrome import (  # noqa: E402
    SEO_EDITORIAL_CSS_VER,
    seo_brand_asset_tags,
    seo_editorial_article_class,
    seo_editorial_head_fonts,
    seo_editorial_stylesheet_links,
)
from tools.site_config import brand_name, exam_name, public_url  # noqa: E402

OUTPUT_DIR = ROOT / PAGE_SLUG
REL_PATH = Path(PAGE_SLUG) / "index.html"
EXAM_DATES_CSS_VER = SEO_EDITORIAL_CSS_VER

AUTHOR_NAME = "乙4マスター編集部"
AUTHOR_PROFILE = (
    "危険物取扱者試験（乙種第4類）の筆記試験に向けた学習設計・演習運用を専門とする編集チーム。"
    "法令・物性・火災予防の三領域を横断し、受験者が迷わない導線づくりを担当しています。"
)
REVIEWER_NAME = "公式情報確認担当"
REVIEWER_PROFILE = (
    "消防試験研究センター・消防庁の公開情報と照合し、"
    "出題傾向とサイト内リンクの整合を確認した担当者です。"
)
PRIMARY_SOURCES = [
    {
        "label": "消防試験研究センター 危険物取扱者",
        "url": "https://www.shoubo-shiken.or.jp/kikenbutsu/",
    },
    {
        "label": "試験情報検索",
        "url": "https://shinsei.shoubo-shiken.or.jp/shoubou_ia/iajs9001.do?shibu_cd=38&menjo_kbn=1",
    },
]


def quality_panel_html(fact_checked_at: str) -> str:
    rows = [
        f"<tr><th>執筆</th><td>{html.escape(AUTHOR_NAME)}（{html.escape(AUTHOR_PROFILE)}）</td></tr>",
        f"<tr><th>確認</th><td>{html.escape(REVIEWER_NAME)}（{html.escape(REVIEWER_PROFILE)}）</td></tr>",
        f"<tr><th>事実確認日</th><td>{html.escape(fact_checked_at)}</td></tr>",
        (
            "<tr><th>主な参照元</th><td><ul class=\"quality-source-list\">"
            + "".join(
                f'<li><a href="{html.escape(s["url"])}" target="_blank" rel="noopener noreferrer">'
                f'{html.escape(s["label"])}</a></li>'
                for s in PRIMARY_SOURCES
            )
            + "</ul></td></tr>"
        ),
    ]
    return (
        '<section class="seo-quality-panel" aria-labelledby="quality-panel-title">'
        '<h2 id="quality-panel-title">このページの信頼性について</h2>'
        '<table class="seo-info-table"><tbody>'
        + "".join(rows)
        + "</tbody></table></section>"
    )


def section_html(heading: str, body: str, section_num: int, section_id: str) -> str:
    body_html = seo_section_body_html(body)
    return (
        f'<section class="seo-article-section" aria-labelledby="{section_id}">'
        f'<h2 id="{section_id}"><span class="section-heading-num">{section_num}</span>'
        f"{html.escape(heading)}</h2>{body_html}</section>"
    )


def related_links_html() -> str:
    links = [
        ("../articles/exam-schedule/", "試験日程·逆算12週"),
        ("../articles/exam-application-flow/", "申込みの流れ"),
        ("../articles/exam-venue-and-region/", "会場·受験地確認"),
        ("../articles/study-plan/", "学習計画の立て方"),
        ("../terms/index.html", "用語解説一覧"),
    ]
    items = "".join(
        f'<a class="related-link" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        for href, label in links
    )
    return (
        '<div class="related-box"><div class="related-box-title">関連コンテンツ</div>'
        f'<div class="related-links">{items}</div></div>'
    )


def build_page_html() -> str:
    schedule_rows = load_schedule_rows()
    fact_checked = (latest_fetched_at(schedule_rows) or date.today().isoformat())[:10]
    canonical = public_url(f"{PAGE_SLUG}/")
    title = f"{PAGE_TITLE}｜{brand_name()}"
    desc = META_DESCRIPTION

    faq_list = [{"question": q, "answer": a} for q, a in faq_items()]
    body_parts: list[str] = [
        exam_schedule_table_html(schedule_rows, section_num=None, show_heading=False, show_note=False),
        quality_panel_html(fact_checked),
    ]
    section_num = 1
    for idx, (heading, body) in enumerate(page_sections()):
        body_parts.append(section_html(heading, body, section_num, f"exam-dates-sec-{idx + 1}"))
        section_num += 1
    body_parts.append(
        faq_section_html(faq_list, heading_id="exam-dates-faq", section_num=section_num)
    )
    body_parts.append(related_links_html())

    graph: list[dict] = [
        {
            "@type": "WebPage",
            "@id": canonical + "#webpage",
            "url": canonical,
            "name": PAGE_TITLE,
            "description": desc,
            "inLanguage": "ja-JP",
            "isPartOf": {"@type": "WebSite", "name": brand_name(), "url": public_url("index.html")},
            "about": exam_name(),
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "トップ", "item": public_url("index.html")},
                {"@type": "ListItem", "position": 2, "name": PAGE_TITLE, "item": canonical},
            ],
        },
    ]
    if faq_list:
        graph.append(
            {
                "@type": "FAQPage",
                "@id": canonical + "#faq",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["question"],
                        "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
                    }
                    for item in faq_list
                ],
            }
        )

    json_ld = {"@context": "https://schema.org", "@graph": graph}

    header = site_page_header(REL_PATH, current="articles")
    footer = site_page_footer(REL_PATH, current=None)
    scroll_top = site_scroll_top_html(REL_PATH)
    crumb = breadcrumb_html(
        REL_PATH,
        [
            ("トップ", "../index.html"),
            ("試験日一覧（都道府県別）", None),
        ],
    )

    article_class = seo_editorial_article_class(extra="exam-dates-page")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
{seo_brand_asset_tags(REL_PATH)}
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{ROBOTS_INDEX_FOLLOW}
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(PAGE_TITLE)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{html.escape(canonical)}">
<meta name="twitter:card" content="summary_large_image">
{seo_editorial_head_fonts()}
{seo_editorial_stylesheet_links(REL_PATH, site_pages_ver=EXAM_DATES_CSS_VER)}
<script type="application/ld+json">
{json.dumps(json_ld, ensure_ascii=False, indent=2)}
</script>
</head>
<body class="{shell_body_class('exam-dates-page')}">
{site_page_wrap_open()}
{header}
<main class="seo-article-main">
{crumb}
<article class="{article_class}">
<div class="article-meta">
<span class="meta-category">試験日一覧</span>
<span class="meta-updated">更新日：{html.escape(fact_checked)}</span>
</div>
<h1 class="article-title">{html.escape(PAGE_TITLE)}</h1>
<p class="article-lead" id="exam-dates-lead">{html.escape(PAGE_LEAD)}</p>
{"".join(body_parts)}
</article>
</main>
{footer}
{scroll_top}
{site_page_wrap_close()}
</body>
</html>
"""


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "index.html"
    out.write_text(build_page_html(), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
