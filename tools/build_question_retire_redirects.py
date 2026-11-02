#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""廃止した単問静的ページ（q/practice/p*/）へ noindex リダイレクト stub を書く。

AdSense の低価値/Scaled content 対策で実践演習の単問静的ページ（1,000本）を廃止したが、
これらは長期間 sitemap に載って Google にインデックス済みのため、削除直後は 404 が大量発生する。
GitHub Pages では本物の 301 を返せないので、プロジェクト既存の作法（build_guide_retire_redirects.py と
同じ meta refresh + canonical + noindex の stub）に合わせ、過去問ハブ（/q/index.html）へ寄せる。

対象 URL は data/question_retired_urls.json（削除前 sitemap から凍結）で管理する。
build_practice_ichimon_pages.py が q/practice を rmtree するため、本スクリプトは build_all.py 内で
その後に実行すること。
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RETIRED_JSON = ROOT / "data" / "question_retired_urls.json"

# 統合先（過去問ハブ）の実タイトル・説明を埋め、検索結果に旧 URL が残る間の
# スニペット品質を保つ。取得できないときのフォールバック。
FALLBACK_TITLE = "危険物取扱者試験（乙種第4類）の過去問・問題演習｜乙4マスター"

REDIRECT_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={url}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="noindex, follow">
<title>{title}</title>{desc_meta}
<script>location.replace({url_js});</script>
</head>
<body>
<p>この問題ページは<a href="{url}">過去問・問題演習</a>に統合されました。自動で移動します。</p>
</body>
</html>
"""

_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_DESC_RE = re.compile(r'<meta\s+name="description"\s+content="(.*?)"', re.S)


def load_config() -> tuple[list[str], str]:
    data = json.loads(RETIRED_JSON.read_text(encoding="utf-8"))
    retired = [str(p).strip().lstrip("/") for p in (data.get("retired") or []) if str(p).strip()]
    target = str(data.get("redirect_target") or "q/index.html").strip().lstrip("/")
    return retired, target


def rel_to_target(src_rel: str, target_rel: str) -> str:
    """src（旧ページ）から target（ハブ）への相対 URL を作る。"""
    src_dir = Path(src_rel).parent
    depth = len(src_dir.parts)
    return "../" * depth + target_rel


def read_target_meta(target_rel: str) -> tuple[str, str]:
    target = (ROOT / target_rel).resolve()
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
    desc = ""
    m = _DESC_RE.search(text)
    if m:
        desc = html.unescape(m.group(1)).strip()
    return title, desc


def main() -> int:
    if not RETIRED_JSON.is_file():
        print(f"skip: {RETIRED_JSON} がありません")
        return 0
    retired, target_rel = load_config()
    canonical = f"https://kikenbutsu-master.jp/{target_rel}"
    title, desc = read_target_meta(target_rel)
    title_out = html.escape(title or FALLBACK_TITLE, quote=True)
    desc_meta = ""
    if desc:
        desc_meta = f'\n<meta name="description" content="{html.escape(desc, quote=True)}">'

    count = 0
    for rel in retired:
        out = ROOT / rel
        rel_url = rel_to_target(rel, target_rel)
        esc = html.escape(rel_url, quote=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            REDIRECT_HTML.format(
                url=esc,
                url_js=repr(rel_url),
                canonical=html.escape(canonical, quote=True),
                title=title_out,
                desc_meta=desc_meta,
            ),
            encoding="utf-8",
        )
        count += 1
    print(f"Wrote {count} retired question redirect(s) -> {target_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
