#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared technical SEO helpers (sitemap, content dates, robots)."""

from __future__ import annotations

import re
from pathlib import Path

from tools.knowledge_hub_writing_samples import WRITING_SAMPLE_SLUGS
from tools.sitemap_utils import iso_date

CONTENT_DATE_COLUMNS: tuple[str, ...] = (
    "fact_checked_at",
    "last_reviewed_at",
    "source_checked_at",
)

SITEMAP_EXCLUDED_REL_PREFIXES: tuple[str, ...] = (
    "terms/samples/",
    "terms/diagram-samples/",
)

SITEMAP_EXCLUDED_BASENAMES: frozenset[str] = frozenset(
    {
        *WRITING_SAMPLE_SLUGS.values(),
        "g-diagram-demo.html",
    }
)

NOINDEX_ROBOTS_META = '<meta name="robots" content="noindex, follow">'
INDEX_ROBOTS_META = '<meta name="robots" content="index, follow">'

DEFAULT_OG_IMAGE_PATH = "/og-image.png"


def default_og_image_url() -> str:
    from tools.site_config import clean_origin

    return f"{clean_origin()}{DEFAULT_OG_IMAGE_PATH}"


def social_share_meta_html(*, image_alt: str | None = None) -> str:
    """Open Graph / Twitter Card 用の共有画像メタ（全ページ共通デフォルト）。"""
    from tools.site_config import brand_name, exam_name
    from xml.sax.saxutils import escape as xml_escape

    image_url = default_og_image_url()
    alt = image_alt or f"{brand_name()}｜{exam_name()}の無料学習サイト"
    alt_esc = xml_escape(alt)
    url_esc = xml_escape(image_url)
    return (
        f'<meta property="og:image" content="{url_esc}">\n'
        f'<meta property="og:image:secure_url" content="{url_esc}">\n'
        '<meta property="og:image:type" content="image/png">\n'
        '<meta property="og:image:width" content="1200">\n'
        '<meta property="og:image:height" content="630">\n'
        f'<meta property="og:image:alt" content="{alt_esc}">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:image" content="{url_esc}">\n'
        f'<meta name="twitter:image:alt" content="{alt_esc}">'
    )


_TWITTER_CARD_SUMMARY_RE = re.compile(
    r'<meta name="twitter:card" content="summary">\s*',
    re.I,
)


def page_social_meta_html(
    *,
    title: str,
    description: str,
    canonical: str,
    og_type: str = "website",
    image_alt: str | None = None,
) -> str:
    from xml.sax.saxutils import escape as xml_escape

    t = xml_escape(title)
    d = xml_escape(description)
    u = xml_escape(canonical)
    ogt = xml_escape(og_type)
    share = social_share_meta_html(image_alt=image_alt)
    return (
        f'<meta property="og:type" content="{ogt}">\n'
        f'<meta property="og:title" content="{t}">\n'
        f'<meta property="og:description" content="{d}">\n'
        f'<meta property="og:url" content="{u}">\n'
        '<meta property="og:locale" content="ja_JP">\n'
        f"{share}\n"
        f'<meta name="twitter:title" content="{t}">\n'
        f'<meta name="twitter:description" content="{d}">'
    )


def _insert_after_tag(html: str, m: re.Match[str], block: str) -> str:
    line_end = html.find("\n", m.end())
    if line_end < 0:
        line_end = m.end()
    else:
        line_end += 1
    return html[:line_end] + block + "\n" + html[line_end:]


def _insert_after_meta_block(html: str, block: str) -> str:
    for pattern in (
        r'<meta property="og:url" content="[^"]*">',
        r'<link rel="canonical" href="[^"]*">',
    ):
        m = re.search(pattern, html)
        if m:
            return _insert_after_tag(html, m, block)
    return html.replace("</head>", block + "\n</head>", 1)


def ensure_page_social_meta(html: str) -> str:
    """og:image / twitter 大画像カードが無い HTML に付与する。"""
    if 'property="og:image"' in html:
        if 'name="twitter:image"' not in html:
            html = _TWITTER_CARD_SUMMARY_RE.sub("", html)
            return _insert_after_meta_block(html, social_share_meta_html())
        return _TWITTER_CARD_SUMMARY_RE.sub(
            '<meta name="twitter:card" content="summary_large_image">\n',
            html,
        )

    title_m = re.search(r"<title>([^<]+)</title>", html)
    desc_m = re.search(r'<meta name="description" content="([^"]*)"', html)
    canon_m = re.search(r'<link rel="canonical" href="([^"]*)"', html)
    og_url_m = re.search(r'<meta property="og:url" content="([^"]*)"', html)

    if re.search(r'<meta property="og:title"', html) and og_url_m:
        html = _TWITTER_CARD_SUMMARY_RE.sub("", html)
        block = social_share_meta_html()
        if title_m and "twitter:title" not in html:
            from xml.sax.saxutils import escape as xml_escape

            t = xml_escape(title_m.group(1).strip())
            desc = desc_m.group(1).strip() if desc_m else ""
            block += (
                f'\n<meta name="twitter:title" content="{t}">'
                + (f'\n<meta name="twitter:description" content="{xml_escape(desc)}">' if desc else "")
            )
        return _insert_after_meta_block(html, block)

    if title_m and desc_m and canon_m:
        block = page_social_meta_html(
            title=title_m.group(1).strip(),
            description=desc_m.group(1).strip(),
            canonical=canon_m.group(1).strip(),
        )
        return _insert_after_tag(html, canon_m, block)

    return html

_NOINDEX_RE = re.compile(r"""name\s*=\s*["']robots["'][^>]*content\s*=\s*["'][^"']*noindex""", re.I)
_NOINDEX_RE_ALT = re.compile(r"""content\s*=\s*["'][^"']*noindex[^"']*["'][^>]*name\s*=\s*["']robots["']""", re.I)


def content_date_from_row(row: dict[str, str] | None) -> str | None:
    if not row:
        return None
    for col in CONTENT_DATE_COLUMNS:
        d = iso_date(row.get(col))
        if d:
            return d
    return None


def is_sitemap_excluded_rel(rel: str) -> bool:
    normalized = rel.replace("\\", "/").lstrip("/")
    for prefix in SITEMAP_EXCLUDED_REL_PREFIXES:
        if normalized.startswith(prefix):
            return True
    return Path(normalized).name in SITEMAP_EXCLUDED_BASENAMES


def is_noindex_html_text(text: str) -> bool:
    return bool(_NOINDEX_RE.search(text) or _NOINDEX_RE_ALT.search(text))


def is_noindex_html(path: Path) -> bool:
    if not path.is_file():
        return False
    return is_noindex_html_text(path.read_text(encoding="utf-8"))


def robots_meta_for_slug(slug_file: str) -> str:
    name = Path(slug_file).name
    if name in SITEMAP_EXCLUDED_BASENAMES:
        return NOINDEX_ROBOTS_META
    return INDEX_ROBOTS_META


def meta_updated_html(updated: str | None) -> str:
    if not updated:
        return ""
    from xml.sax.saxutils import escape as xml_escape

    return f'<span class="meta-updated">更新日：{xml_escape(updated)}</span>'


def json_ld_date_modified(updated: str | None) -> dict[str, str]:
    if not updated:
        return {}
    return {"dateModified": updated}


def latest_content_date(rows: list[dict[str, str]]) -> str | None:
    dates = [d for row in rows if (d := content_date_from_row(row))]
    return max(dates) if dates else None
