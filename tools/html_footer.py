# -*- coding: utf-8 -*-
"""静的 HTML 用フッター（相対パス付き）と GA4 共通タグ。

- 測定IDを変えるときは GA4_MEASUREMENT_ID と site-analytics.js 内の DEFAULT_MID を揃える。
- 新規の手書き HTML では </body> 直前に analytics_snippet(Path('相対パス')) と同等の2行を置くか、
  生成ページでは site_page_footer の直後に analytics が付くので head に GA を書かない。
- ヘッダー・フッターは index.html の topnav / site-footer と同型（site-pages.css の site-shell）。
"""

from __future__ import annotations

import html
from pathlib import Path

from tools.site_config import (
    brand_mark,
    brand_name,
    contact_url,
    copyright_text,
    exam_name,
    footer_disclaimer,
    ga4_measurement_id,
    learning_nav_label,
    navigation_items,
)

FORM_URL = contact_url()

# GA4 測定ID（site-analytics.js の DEFAULT_MID と揃えること）
GA4_MEASUREMENT_ID = ga4_measurement_id()

# フッター注記・著作権（共通フッター・静的ガイドの表記揃え）
FOOTER_DISCLAIMER = footer_disclaimer()
SITE_COPYRIGHT = copyright_text()

# 静的ページ・生成 HTML 共通（Search Console / クローラ向け）
ROBOTS_INDEX_FOLLOW = '<meta name="robots" content="index, follow">'

SITE_FOOTER_NAV = navigation_items("footer")

# index.html topnav と同じ学習ナビ（用語解説のみ静的一覧、他は SPA ハッシュへ）
LEARNING_NAV_ITEMS: list[tuple[str, str, str, str]] = [
    (
        "tnav-ichimondou",
        "一問一答",
        "#ichimondou",
        '<svg viewBox="0 0 16 16"><path d="M8 2v12M4 4h8M4 8h8M4 12h8"/></svg>',
    ),
    (
        "tnav-past",
        "過去問",
        "#past",
        '<svg viewBox="0 0 16 16"><path d="M3 2h10v12H3z"/><path d="M5 5h6M5 8h6M5 11h4"/></svg>',
    ),
    (
        "tnav-orig",
        "実践演習",
        "#orig",
        '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6"/><path d="M8 5v3l2 1"/></svg>',
    ),
    (
        "tnav-dash",
        "記録・分析",
        "#dash",
        '<svg viewBox="0 0 16 16"><path d="M2 13L5 8l3 2 3-5 3 2"/></svg>',
    ),
    (
        "tnav-review",
        "復習",
        "#review",
        '<svg viewBox="0 0 16 16"><path d="M2 4h12M2 8h8M2 12h10"/></svg>',
    ),
    (
        "tnav-glossary",
        "用語解説",
        "terms/index.html",
        '<svg viewBox="0 0 16 16"><rect x="2.5" y="2" width="11" height="12" rx="1.5"/><path d="M5 6h6M5 9h4"/></svg>',
    ),
]

# site_page_header(current=...) で学習ナビの active を付ける
# 過去問一覧（q）はフッター「過去問一覧」と対応。ヘッダー「過去問」は SPA 演習用のため active にしない。
LEARNING_NAV_ACTIVE_BY_PAGE: dict[str, str] = {
    "terms": "tnav-glossary",
}


def _in_q_section(rel_path: Path) -> bool:
    return bool(rel_path.parts) and rel_path.parts[0] == "q"


def footer_href(rel_path: Path, site_rel: str) -> str:
    """rel_path: ROOT からの相対パス（例 q/past/y2025/q01/index.html）。site_rel: index.html / q/index.html 等。"""
    site_rel = site_rel.lstrip("/")
    parent = rel_path.parent
    parts = parent.parts
    if parent.as_posix() == "q" and site_rel == "q/index.html":
        return "index.html"
    if site_rel == "terms/index.html" and parts and parts[0] == "terms":
        if len(parts) == 1:
            return "index.html"
        return "/".join([".."] * (len(parts) - 1)) + "/index.html"
    if parts and parts[0] == "terms" and len(parts) == 1 and site_rel.startswith("field-") and site_rel.endswith("/index.html"):
        return site_rel
    if len(parts) >= 3 and parts[0] == "q" and parts[1] == "past" and site_rel == "q/index.html":
        prefix = "/".join([".."] * (len(parts) - 1))
        return prefix + "/index.html"
    if (
        len(parts) >= 4
        and parts[0] == "q"
        and parts[1] == "past"
        and site_rel.startswith("past/y")
        and site_rel.endswith("/index.html")
    ):
        up = len(parts) - 3
        return ("/".join([".."] * up) + "/index.html") if up else "index.html"
    up = len(parts)
    if len(parts) >= 3 and parts[0] == "q" and parts[1] == "past" and site_rel.startswith("q/") and site_rel.count("/") == 1:
        up = len(parts) - 1
    prefix = "/".join([".."] * up)
    if not prefix:
        return site_rel
    return prefix + "/" + site_rel


def analytics_snippet(rel_path: Path) -> str:
    """全静的ページ共通: フッター直後（</body> 直前想定）に置く GA4 タグ。相対パスで site-analytics.js を読む。"""
    src = html.escape(footer_href(rel_path, "site-analytics.js"))
    mid = html.escape(GA4_MEASUREMENT_ID)
    return (
        "<!-- GA4: tools/html_footer.analytics_snippet（測定IDは GA4_MEASUREMENT_ID） -->\n"
        f'<script>window.__GA4_MEASUREMENT_ID__="{mid}";</script>\n'
        f'<script defer src="{src}"></script>'
    )


def _breadcrumb_ol(rel_path: Path, items: list[tuple[str, str | None]]) -> str:
    lis: list[str] = []
    for text, href in items:
        if href:
            h = footer_href(rel_path, href) if not href.startswith("http") else href
            lis.append(f'<li><a href="{html.escape(h)}">{html.escape(text)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{html.escape(text)}</li>')
    crumbs = "\n        ".join(lis)
    return f"""<nav class="site-page-header-crumb" aria-label="パンくず">
      <ol class="q-breadcrumb">
        {crumbs}
      </ol>
    </nav>"""


def _topnav_logo(rel_path: Path) -> str:
    root = html.escape(footer_href(rel_path, "index.html"))
    mark = html.escape(brand_mark())
    name = html.escape(brand_name())
    exam = html.escape(exam_name())
    return f"""<a class="topnav-logo" href="{root}" aria-label="{name}、{exam}対策のトップへ">
          <div class="topnav-logo-mark" title="サービス略称（差し替え）">{mark}</div>
          <span class="topnav-logo-stack">
            <span class="topnav-logo-text">{name}</span>
            <span class="topnav-logo-sub">{exam}</span>
          </span>
        </a>"""


def _learning_nav_href(rel_path: Path, dest: str) -> str:
    """学習ナビのリンク先（#hash は index.html 基準、それ以外は site 相対パス）。"""
    if dest.startswith("#"):
        return footer_href(rel_path, "index.html") + dest
    return footer_href(rel_path, dest)


def _learning_nav_links(rel_path: Path, *, current: str | None = None) -> str:
    """静的ページ用: SPA 学習ナビ（用語解説は terms/index.html）。"""
    active_id = LEARNING_NAV_ACTIVE_BY_PAGE.get(current or "")
    links: list[str] = []
    for nav_id, label, dest, icon in LEARNING_NAV_ITEMS:
        link_dest = dest
        if nav_id == "tnav-past" and _in_q_section(rel_path):
            link_dest = "q/index.html"
        href = html.escape(_learning_nav_href(rel_path, link_dest))
        active = nav_id == active_id
        cls = "topnav-link active" if active else "topnav-link"
        cur = ' aria-current="page"' if active else ""
        display_label = learning_nav_label(nav_id, label)
        links.append(
            f'<a class="{cls}" id="{nav_id}" href="{href}"{cur}>{icon}{html.escape(display_label)}</a>'
        )
    return "\n          ".join(links)


def site_page_header(
    rel_path: Path,
    *,
    current: str | None = None,
    breadcrumb_items: list[tuple[str, str | None]] | None = None,
    wide: bool = False,
) -> str:
    """index.html の topnav と同型・同じ学習ナビ（静的ページから SPA へ戻る）。"""
    _ = breadcrumb_items
    nav_html = _learning_nav_links(rel_path, current=current)
    wide_cls = " site-shell-header--wide" if wide else ""
    return f"""<header class="topnav site-shell-header{wide_cls}">
      <div class="topnav-inner">
        {_topnav_logo(rel_path)}
        <nav class="topnav-links" aria-label="メインナビゲーション">
          {nav_html}
        </nav>
      </div>
    </header>"""


def site_shell_footer(
    rel_path: Path,
    *,
    fixed: bool = True,
    include_analytics: bool = True,
    current: str | None = None,
) -> str:
    """index.html の site-footer と同型（画面下固定。site-pages.css で position:fixed）。"""
    _ = fixed
    root = html.escape(footer_href(rel_path, "index.html"))
    mark = html.escape(brand_mark())
    name = html.escape(brand_name())
    title = html.escape(f"{brand_name()}（{exam_name()}対策）トップへ")
    links: list[str] = []
    for label, dest, key in SITE_FOOTER_NAV:
        is_current = bool(current and key == current)
        cur = ' aria-current="page"' if is_current else ""
        if dest.startswith("http"):
            href = dest
            links.append(
                f'<a href="{html.escape(href)}" target="_blank" rel="noopener noreferrer"{cur}>'
                f"{html.escape(label)}</a>"
            )
        else:
            href = footer_href(rel_path, dest)
            links.append(
                f'<a href="{html.escape(href)}"{cur}>{html.escape(label)}</a>'
            )
    links_html = "\n          ".join(links)
    footer = f"""<footer class="site-footer" role="contentinfo">
    <div class="site-footer-scroll">
      <div class="site-footer-inner">
        <a class="site-footer-brand" href="{root}" title="{title}">
          <span class="site-footer-logo-mark" title="サービス略称（差し替え）">{mark}</span>
          <span class="site-footer-site-name">{name}</span>
        </a>
        <span class="site-footer-sep" aria-hidden="true"></span>
        <nav class="site-footer-legal" aria-label="サイト情報・ポリシー">
          {links_html}
        </nav>
        <span class="site-footer-sep" aria-hidden="true"></span>
        <span class="site-footer-copy">{html.escape(SITE_COPYRIGHT)}</span>
      </div>
    </div>
  </footer>"""
    if include_analytics:
        return footer + "\n" + analytics_snippet(rel_path)
    return footer


def site_page_footer(rel_path: Path, *, current: str | None = None, wide: bool = False) -> str:
    """静的ページ用フッター + GA4（site-config の navigation.footer）。"""
    _ = wide
    return site_shell_footer(rel_path, include_analytics=True, current=current)


def site_page_wrap_open() -> str:
    return '<div class="site-page-wrap">'


def site_page_wrap_close() -> str:
    return "</div>"


def breadcrumb_html(rel_path: Path, items: list[tuple[str, str | None]]) -> str:
    """後方互換。新規は site_page_header(..., breadcrumb_items=...) を使用。"""
    return _breadcrumb_ol(rel_path, items)


def static_site_header(*, root_href: str, breadcrumb_items: list[tuple[str, str | None]]) -> str:
    """過去問など従来の q-static ヘッダー（パンくず付き）。"""
    lis: list[str] = []
    for text, href in breadcrumb_items:
        if href:
            lis.append(f'<li><a href="{html.escape(href)}">{html.escape(text)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{html.escape(text)}</li>')
    crumbs = "\n      ".join(lis)
    return f"""<header class="q-static-header">
  <p class="q-static-brand"><a href="{html.escape(root_href)}">{html.escape(brand_name())}</a>（{html.escape(exam_name())}）</p>
  <nav aria-label="パンくず">
    <ol class="q-breadcrumb">
      {crumbs}
    </ol>
  </nav>
</header>"""


def static_footer_block(rel_path: Path) -> str:
    """過去問など従来の q-static フッター + GA4。"""
    return site_shell_footer(rel_path, include_analytics=True)
