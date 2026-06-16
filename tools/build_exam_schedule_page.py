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
)
from tools.seo_body_markup import seo_section_body_html  # noqa: E402
from tools.seo_editorial_chrome import (  # noqa: E402
    seo_brand_asset_tags,
    seo_editorial_article_class,
    seo_editorial_head_fonts,
    seo_editorial_stylesheet_links,
)
from tools.site_config import brand_name, exam_name, public_url  # noqa: E402

OUTPUT_DIR = ROOT / PAGE_SLUG
REL_PATH = Path(PAGE_SLUG) / "index.html"


def section_html(heading: str, body: str, section_num: int, section_id: str) -> str:
    body_html = seo_section_body_html(body)
    return (
        f'<section class="seo-article-section" aria-labelledby="{section_id}">'
        f'<h2 id="{section_id}"><span class="section-heading-num">{section_num}</span>'
        f"{html.escape(heading)}</h2>{body_html}</section>"
    )


def faq_html(items: list[tuple[str, str]], section_num: int) -> str:
    blocks = []
    for q, a in items:
        blocks.append(
            f'<details class="term-faq-item" open><summary>{html.escape(q)}</summary>'
            f"<div>{html.escape(a)}</div></details>"
        )
    return (
        f'<section class="seo-article-section" aria-labelledby="exam-dates-faq">'
        f'<h2 id="exam-dates-faq"><span class="section-heading-num">{section_num}</span>よくある質問</h2>'
        f"{''.join(blocks)}</section>"
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

    body_parts: list[str] = [
        exam_schedule_table_html(schedule_rows, show_heading=False),
    ]
    section_num = 1
    for idx, (heading, body) in enumerate(page_sections()):
        body_parts.append(section_html(heading, body, section_num, f"exam-dates-sec-{idx + 1}"))
        section_num += 1
    body_parts.append(faq_html(faq_items(), section_num))
    body_parts.append(related_links_html())

    json_ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": PAGE_TITLE,
        "description": desc,
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": brand_name(), "url": public_url("index.html")},
        "about": exam_name(),
    }

    header = site_page_header(REL_PATH, current="articles")
    footer = site_page_footer(REL_PATH, current=None)
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
{seo_editorial_stylesheet_links(REL_PATH)}
<script type="application/ld+json">
{json.dumps(json_ld, ensure_ascii=False, indent=2)}
</script>
</head>
<body class="{shell_body_class('exam-dates-page')}">
{site_page_wrap_open()}
{header}
<main class="seo-article-main">
{crumb}
<article class="seo-article-card article-body {article_class}">
<div class="article-meta">
<span class="meta-category">特設ページ</span>
<span class="meta-updated">更新日：{html.escape(fact_checked)}</span>
</div>
<h1 class="article-title">{html.escape(PAGE_TITLE)}</h1>
<p class="article-lead" id="exam-dates-lead">{html.escape(PAGE_LEAD)}</p>
{"".join(body_parts)}
</article>
</main>
{footer}
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
