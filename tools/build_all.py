#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kikenbutsu-master 用ビルド（静的 SEO + 実践・一問一答一覧）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    py = sys.executable
    run([py, "tools/validate_csv.py"])
    run([py, "tools/apply_site_config.py"])
    run([py, "tools/csv_to_exam_site_past_js.py"])
    run([py, "tools/csv_to_exam_site_ichimondou_js.py"])
    run([py, "tools/build_past_question_pages.py"])
    run([py, "tools/build_practice_ichimon_pages.py"])
    run([py, "tools/build_article_pages.py"])
    run([py, "tools/build_glossary_pages.py"])
    run([py, "tools/build_compare_pages.py"])
    run([py, "tools/build_numbers_mistakes_pages.py"])
    run([py, "tools/build_sitemap.py"])
    run([py, "tools/validate_generated_seo.py"])
    run([py, "tools/validate_site_integration.py"])
    run([py, "tools/validate_internal_links.py"])
    run([py, "tools/validate_public_content.py"])
    run(["bash", "tools/prepare_public_site.sh"])
    run(["bash", "tools/sync_gh_pages_branch.sh"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
