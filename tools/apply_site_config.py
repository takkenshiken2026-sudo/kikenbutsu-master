#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply site-config.json to hand-written HTML/JS placeholders."""

from __future__ import annotations

import hashlib
import re
import sys
import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import (
    brand_mark,
    brand_name,
    category_to_field_map,
    clean_origin,
    contact_url,
    copyright_text,
    exam_name,
    ga4_measurement_id,
    learning_nav_label,
    official_organization,
    primary_external_link,
    sync_config_files,
    fields,
)
from tools.html_footer import site_page_footer, site_page_header, site_shell_footer


TEXT_TARGETS = [
    ROOT / "index.html",
    ROOT / "about.html",
    ROOT / "privacy.html",
    ROOT / "related-sites.html",
    ROOT / "articles" / "index.html",
    ROOT / "site-analytics.js",
]

STATIC_PAGE_CURRENTS = {
    ROOT / "about.html": "about",
    ROOT / "privacy.html": "privacy",
    ROOT / "related-sites.html": "related",
    ROOT / "articles" / "index.html": "articles",
}


def replace_all(text: str) -> str:
    origin = clean_origin()
    host = origin.replace("https://", "").replace("http://", "").strip("/")
    official = primary_external_link()
    orig_nav_label = learning_nav_label("tnav-orig", "実践演習")
    replacements = [
        ("© 2026 Sampleマスター学習支援・YOUR-DOMAIN.example", copyright_text()),
        ("Sampleマスター", brand_name()),
        ("◯◯試験（プレースホルダー）", exam_name()),
        ("YOUR-DOMAIN.example", host),
        ("https://YOUR-DOMAIN.example", origin),
        ("https://example.com/contact", contact_url()),
        ("window.__GA4_MEASUREMENT_ID__=\"\"", f'window.__GA4_MEASUREMENT_ID__="{ga4_measurement_id()}"'),
        ('var DEFAULT_MID = "";', f'var DEFAULT_MID = "{ga4_measurement_id()}";'),
        ("一般社団法人 試験実施団体", official_organization()),
        ("試験実施団体（試験・登録の公式）", official.get("label", official_organization())),
        ("https://example.com/", official.get("url", "https://example.com/")),
    ]
    if orig_nav_label == "実践演習":
        replacements.extend(
            [
                ("オリジナル問題", "実践演習"),
                ("オリジナル演習", "実践演習"),
                ("単元別問題データ", "実践演習データ"),
            ]
        )
    if exam_name() != "◯◯試験（プレースホルダー）":
        replacements.append(("◯◯試験", exam_name()))
    for src, dst in replacements:
        text = text.replace(src, dst)

    marker = '<script src="./site-config.js"></script>'
    if "site-config.js" not in text and "site-analytics.js" in text:
        for old, new_block in (
            (
                '<script defer src="./site-analytics.js"></script>',
                marker + '\n<script defer src="./site-analytics.js"></script>',
            ),
            (
                '<script defer src="site-analytics.js"></script>',
                '<script src="site-config.js"></script>\n<script defer src="site-analytics.js"></script>',
            ),
        ):
            if old in text:
                text = text.replace(old, new_block, 1)
                break
    return text


def ensure_theme_link(text: str, rel_path: Path) -> str:
    if "site-theme.css" in text:
        return text
    href = "site-theme.css" if rel_path.parent == Path(".") else "../site-theme.css"
    text = text.replace(
        '<link rel="stylesheet" href="./site-pages.css">',
        '<link rel="stylesheet" href="./site-pages.css">\n  <link rel="stylesheet" href="./site-theme.css">',
    )
    text = text.replace(
        '<link rel="stylesheet" href="../site-pages.css">',
        '<link rel="stylesheet" href="../site-pages.css">\n  <link rel="stylesheet" href="../site-theme.css">',
    )
    if "site-theme.css" not in text and "site-pages.css" in text:
        text = re.sub(
            r'(<link rel="stylesheet" href="[^"]*site-pages\.css[^"]*">)',
            rf'\1\n  <link rel="stylesheet" href="{href}">',
            text,
            count=1,
        )
    return text


def replace_static_chrome(text: str, path: Path) -> str:
    current = STATIC_PAGE_CURRENTS.get(path)
    if not current:
        return text
    rel_path = path.relative_to(ROOT)
    text = re.sub(
        r'\s*<header class="(?:site-page-header(?: site-page-header--wide)?|topnav site-shell-header(?: site-shell-header--wide)?)">.*?</header>',
        "\n" + site_page_header(rel_path, current=current),
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r'\s*<footer class="(?:site-page-footer(?: site-page-footer--wide)?|site-footer)[^"]*".*?</footer>\s*(?:<!-- GA4:.*?-->\s*)?(?:<script>window\.__GA4_MEASUREMENT_ID__="[^"]*";</script>\s*)?(?:<script defer src="[^"]*site-analytics\.js"></script>\s*)?',
        "\n" + site_page_footer(rel_path, current=current),
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace("</script></div>", "</script>\n  </div>")
    text = re.sub(
        r'(</div>)\s*<!-- GA4:.*?site-analytics\.js"></script>\s*(?=</body>)',
        r"\1\n",
        text,
        count=1,
        flags=re.S,
    )
    return ensure_theme_link(text, rel_path)


def ensure_index_theme(text: str) -> str:
    """index.html は optimize_index_asset_loading で theme を head にインライン化する。"""
    return text


def _asset_version(path: Path) -> str:
    if not path.is_file():
        return "0"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _versioned_href(filename: str, version: str) -> str:
    return f"{filename}?v={version}"


def optimize_index_asset_loading(text: str) -> str:
    """LCP/FCP 向け: theme/config を head インライン化し、演習データ JS は defer + preload。"""
    theme_path = ROOT / "site-theme.css"
    config_path = ROOT / "site-config.js"
    data_files = (
        "exam-site-data-practice.js",
        "exam-site-data-past.js",
        "exam-site-data-ichimondou.js",
    )

    theme_block = ""
    if theme_path.is_file():
        css = theme_path.read_text(encoding="utf-8").strip()
        theme_block = f'<style id="site-theme-vars">\n{css}\n</style>'

    config_block = ""
    if config_path.is_file():
        js = config_path.read_text(encoding="utf-8").strip()
        config_block = f"<script>\n{js}\n</script>"

    if "<!--SITE_THEME_INLINE-->" in text:
        text = text.replace("<!--SITE_THEME_INLINE-->", theme_block, 1)
    elif theme_block and 'id="site-theme-vars"' not in text:
        text = text.replace("</head>", f"  {theme_block}\n</head>", 1)

    if "<!--SITE_CONFIG_INLINE-->" in text:
        text = text.replace("<!--SITE_CONFIG_INLINE-->", config_block, 1)
    elif config_block and "window.SITE_CONFIG" not in text.split("</head>", 1)[0]:
        text = text.replace("</head>", f"  {config_block}\n</head>", 1)

    for filename in data_files:
        version = _asset_version(ROOT / filename)
        href = _versioned_href(filename, version)
        text = re.sub(
            rf'(<link rel="preload" href="){re.escape(filename)}(?:\?v=[^"]*)?(" as="script">)',
            rf"\1{href}\2",
            text,
        )
        text = re.sub(
            rf'(<script defer src="){re.escape(filename)}(?:\?v=[^"]*)?("></script>)',
            rf"\1{href}\2",
            text,
        )

    analytics_version = _asset_version(ROOT / "site-analytics.js")
    text = re.sub(
        r'(<script defer src=")site-analytics\.js(?:\?v=[^"]*)?("></script>)',
        rf"\1{_versioned_href('site-analytics.js', analytics_version)}\2",
        text,
    )

    # 旧来の同期読み込み（レンダーブロック）を除去
    text = re.sub(r'\n<link rel="stylesheet" href="site-theme\.css">', "", text)
    text = re.sub(r'\n<script src="site-config\.js"></script>', "", text)
    text = re.sub(
        r'\n<script src="exam-site-data-(?:practice|past|ichimondou)\.js(?:\?v=[^"]*)?"></script>',
        "",
        text,
    )

    defer_block = "\n".join(
        f'<script defer src="{_versioned_href(name, _asset_version(ROOT / name))}"></script>'
        for name in data_files
    )
    marker = "<!-- 演習データ（defer:"
    if marker not in text and defer_block:
        text = text.replace(
            "<!-- GA4: tools/html_footer.analytics_snippet と同内容（トップ SPA） -->",
            defer_block + "\n<!-- GA4: tools/html_footer.analytics_snippet と同内容（トップ SPA） -->",
            1,
        )

    # preload 行が無ければ fonts の直後に追加
    if 'rel="preload" href="exam-site-data-practice.js' not in text:
        preload_lines = "\n".join(
            f'<link rel="preload" href="{_versioned_href(name, _asset_version(ROOT / name))}" as="script">'
            for name in data_files
        )
        text = text.replace(
            '<link rel="preload" as="style" href="https://fonts.googleapis.com/css2',
            preload_lines + '\n<link rel="preload" as="style" href="https://fonts.googleapis.com/css2',
            1,
        )

    if "years:[...YEARS]" in text:
        text = text.replace(
            "years:[...YEARS]",
            "years:[]",
        )
    if "quizState.years = YEARS.slice();" not in text:
        text = text.replace(
            "  YEARS = Array.from(yset).sort(function (a, b) { return b - a; });\n}",
            "  YEARS = Array.from(yset).sort(function (a, b) { return b - a; });\n"
            "  if (typeof quizState !== 'undefined' && quizState) quizState.years = YEARS.slice();\n}",
        )

    return text


def update_index_shell_footer(text: str) -> str:
    """SPA フッターを site-config の navigation.footer と同型に揃える。"""
    block = site_shell_footer(Path("index.html"), fixed=True, include_analytics=False)
    indented = "\n".join(("  " + line) if line else line for line in block.splitlines())
    return re.sub(
        r'\n  <footer class="site-footer[^"]*" role="contentinfo">.*?</footer>',
        "\n" + indented,
        text,
        count=1,
        flags=re.S,
    )


def update_index_brand_mark(text: str) -> str:
    mark = html.escape(brand_mark())

    def _inject_mark(m: re.Match[str]) -> str:
        return f"{m.group(1)}{mark}{m.group(3)}"

    text = re.sub(
        r'(<div class="topnav-logo-mark"[^>]*>)(.*?)(</div>)',
        _inject_mark,
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r'(<span class="site-footer-logo-mark"[^>]*>)(.*?)(</span>)',
        _inject_mark,
        text,
        count=1,
        flags=re.S,
    )
    return text


def update_index_glossary_excerpt(text: str) -> str:
    csv_path = ROOT / "data" / "glossary_terms.csv"
    if not csv_path.is_file() or '<section class="glos-static-section"' not in text:
        return text
    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8-sig").splitlines()))
    cat_map = category_to_field_map()
    by_field: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        fid = cat_map.get(str(row.get("category") or "").strip())
        if not fid:
            continue
        by_field.setdefault(fid, []).append(row)

    blocks: list[str] = []
    for f in fields():
        fid = str(f["id"])
        items = by_field.get(fid, [])[:2]
        if not items:
            continue
        legacy = str(f.get("legacyGlossaryCat") or fid)
        articles = []
        for item in items:
            term = html.escape(str(item.get("term") or "").strip())
            desc = html.escape(str(item.get("short_def") or item.get("definition") or "").strip())
            articles.append(
                '<article class="glos-static-card" itemscope itemtype="https://schema.org/DefinedTerm">\n'
                f'  <h4 class="glos-static-term" itemprop="name">{term}</h4>\n'
                f'  <p class="glos-static-desc" itemprop="description">{desc}</p>\n'
                "</article>"
            )
        blocks.append(
            f'<div class="glos-cat-section" data-cat="{html.escape(legacy)}">\n'
            f'<h3 class="glos-cat-heading">{html.escape(str(f.get("name") or fid))}</h3>\n'
            + "\n".join(articles)
            + "\n</div>"
        )
    if not blocks:
        return text

    start = text.find('<section class="glos-static-section"')
    first_block = text.find('<div class="glos-cat-section"', start)
    end = text.find("</section>", first_block)
    if start < 0 or first_block < 0 or end < 0:
        return text
    intro = text[start:first_block]
    replacement = intro + "\n".join(blocks) + "\n</section>"
    return text[:start] + replacement + text[end + len("</section>") :]


def main() -> int:
    sync_config_files()
    for path in TEXT_TARGETS:
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8")
        new = replace_static_chrome(replace_all(old), path)
        if path == ROOT / "index.html":
            new = ensure_index_theme(new)
            new = optimize_index_asset_loading(new)
            new = update_index_shell_footer(new)
            new = update_index_brand_mark(new)
            new = update_index_glossary_excerpt(new)
        if new != old:
            path.write_text(new, encoding="utf-8")
            print(f"Updated {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
