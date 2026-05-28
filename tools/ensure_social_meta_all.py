#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全公開 HTML に OGP 共有画像メタを付与する。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.seo_utils import ensure_page_social_meta  # noqa: E402

SKIP_DIR_NAMES = frozenset({"public_site", ".git", "node_modules", ".cursor"})


def main() -> int:
    updated = 0
    for path in sorted(ROOT.rglob("*.html")):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        old = path.read_text(encoding="utf-8")
        new = ensure_page_social_meta(old)
        if new == old:
            continue
        path.write_text(new, encoding="utf-8")
        print(f"ensure_social_meta_all: {path.relative_to(ROOT)}")
        updated += 1
    print(f"ensure_social_meta_all: updated {updated} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
