#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旧特設URL /exam-dates/ から試験ガイド記事へリダイレクトする。"""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "exam-dates"
REL_PATH = Path("exam-dates") / "index.html"
TARGET = "../articles/exam-schedule-by-region/index.html"

REDIRECT_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={url}">
<link rel="canonical" href="{url}">
<meta name="robots" content="noindex, follow">
<title>記事移動中…</title>
<script>location.replace({url_js});</script>
</head>
<body>
<p>試験ガイド記事へ移動します。<a href="{url}">こちら</a></p>
</body>
</html>
"""


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "index.html"
    esc = html.escape(TARGET, quote=True)
    out.write_text(REDIRECT_HTML.format(url=esc, url_js=repr(TARGET)), encoding="utf-8")
    print(f"Wrote redirect {out.relative_to(ROOT)} -> {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
