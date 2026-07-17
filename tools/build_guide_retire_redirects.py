#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archived ガイド記事の articles/{slug}/ へ noindex リダイレクト HTML を書く。"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.editorial_quality import norm  # noqa: E402

RETIRED_JSON = ROOT / "data" / "guide_retired.json"

# 統合先の実タイトルが取れないときのフォールバック（プレースホルダは使わない）。
FALLBACK_TITLE = "乙4マスター｜危険物取扱者乙4試験ガイド"

# noindex リダイレクトでも、削除反映までは検索結果に旧 URL が残る。
# その間のスニペットが「記事移動中…」だと CTR を落とすため、
# 統合先ページの実タイトル・説明文を埋め込んでおく。
REDIRECT_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={url}">
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex, follow">
<title>{title}</title>{desc_meta}
<script>location.replace({url_js});</script>
</head>
<body>
<p>この記事は<a href="{url}">{link_text}</a>に統合されました。自動で移動します。</p>
</body>
</html>
"""

_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_DESC_RE = re.compile(r'<meta\s+name="description"\s+content="(.*?)"', re.S)
_PLACEHOLDER_TITLES = {"記事移動中…", "用語解説へ移動中…"}


def read_target_meta(stub_dir: Path, rel: str) -> tuple[str, str]:
    """統合先 HTML から title と description を読む。取れなければ空文字。"""
    if rel.startswith(("http://", "https://")):
        return "", ""
    target = (stub_dir / rel).resolve()
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file():
        return "", ""
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return "", ""
    title = ""
    m = _TITLE_RE.search(text)
    if m:
        title = html.unescape(m.group(1)).strip()
    if title in _PLACEHOLDER_TITLES:  # 統合先自体がリダイレクト stub の場合は使わない
        title = ""
    desc = ""
    m = _DESC_RE.search(text)
    if m:
        desc = html.unescape(m.group(1)).strip()
    return title, desc


def load_retired_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if RETIRED_JSON.is_file():
        data = json.loads(RETIRED_JSON.read_text(encoding="utf-8"))
        for slug, target in (data.get("redirects") or {}).items():
            mapping[norm(slug)] = norm(target)
    csv_path = ROOT / "data" / "guide_articles.csv"
    if csv_path.is_file():
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if norm(row.get("content_status")) != "archived":
                    continue
                slug = norm(row.get("slug"))
                note = norm(row.get("original_note"))
                target = ""
                for part in note.split(";"):
                    if part.startswith("retire_redirect:"):
                        target = part.split(":", 1)[1].strip()
                        break
                if slug and target:
                    mapping.setdefault(slug, target)
    return mapping


def article_redirect_href(target: str) -> str:
    """articles/{slug}/index.html からの相対 URL を組み立てる。"""
    t = norm(target)
    if t.startswith(("http://", "https://")):
        return t
    if t.startswith("../"):
        base = t.rstrip("/")
        if base.endswith(".html"):
            return base
        return f"{base}/index.html"
    slug = t.rstrip("/")
    return f"../{slug}/index.html"


def write_redirect(articles_dir: Path, slug: str, target_slug: str) -> None:
    out_dir = articles_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    rel = article_redirect_href(target_slug)
    esc = html.escape(rel, quote=True)

    title, desc = read_target_meta(out_dir, rel)
    title_out = html.escape(title or FALLBACK_TITLE, quote=True)
    # リンク文言は統合先タイトルのサイト名を除いた見出し部分を使う。
    link_text = html.escape((title.split("｜")[0].strip() if title else "統合先の記事"), quote=True)
    desc_meta = ""
    if desc:
        desc_meta = f'\n<meta name="description" content="{html.escape(desc, quote=True)}">'

    (out_dir / "index.html").write_text(
        REDIRECT_HTML.format(
            url=esc,
            url_js=repr(rel),
            title=title_out,
            desc_meta=desc_meta,
            link_text=link_text,
        ),
        encoding="utf-8",
    )
    marker = out_dir / ".generated-by-exam-site"
    if marker.is_file():
        marker.unlink()


def main() -> int:
    mapping = load_retired_map()
    articles_dir = ROOT / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for slug, target in sorted(mapping.items()):
        if not target:
            continue
        write_redirect(articles_dir, slug, target)
        count += 1
    print(f"Wrote {count} retired guide redirect(s) under articles/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
