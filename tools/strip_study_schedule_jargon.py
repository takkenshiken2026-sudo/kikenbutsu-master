#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガイド CSV / batch から学習運用テンプレ jargon を除去（乙4）。

field-* は fix batch で対応。三領域の「三列表」→「分野別正答率表」へ統一。

  python3 tools/strip_study_schedule_jargon.py --dry-run
  python3 tools/strip_study_schedule_jargon.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.guide_prose_patterns import PROSE_COLUMNS  # noqa: E402

GUIDE_CSV = ROOT / "data" / "guide_articles.csv"
BATCH_GLOBS = ("kiken_rewrite_batch*.py", "kiken_rewrite_fix_batch*.py")

JARGON_REPLACEMENTS: list[tuple[str, str]] = [
    (r"三列表「法令」行", "分野別正答率表の法令行"),
    (r"三列表「物性」行", "分野別正答率表の物性行"),
    (r"三列表「火災」行", "分野別正答率表の火災行"),
    (r"三列表3回分", "分野別正答率表3回分"),
    (r"三列表固定", "分野別正答率表固定"),
    (r"三列表更新", "分野別正答率表の更新"),
    (r"三列表記入", "分野別正答率1行記入"),
    (r"三列表へ", "分野別正答率表へ"),
    (r"三列表を", "分野別正答率表を"),
    (r"三列表の", "分野別正答率表の"),
    (r"三列表と", "分野別正答率表と"),
    (r"三列表で", "分野別正答率表で"),
    (r"三列表", "分野別正答率表"),
    (r"5行表", "分野別正答率表"),
    (r"7行表", "分野別正答率表"),
    (r"5列表", "分野別正答率表"),
    (r"9/6 三列表", "9月通し50問の正答率表"),
    (r"9/6通し", "9月通し50問120分"),
    (r"/terms/15分", "用語解説15分"),
    (r"/terms/", "用語解説"),
    (r"Day0→3→7", "当日・3日後・7日後の復習"),
    (r"Day3解き直し", "3日後の解き直し"),
    (r"Day3", "3日後"),
]

JARGON_REGEX_REPLACEMENTS: list[tuple[str, str]] = [
    (r"9/\d+通し\d+/\d+", "9月通し50問120分"),
]

JARGON_CHECK_RE = re.compile(
    r"5行表|7行表|5列表|三列表|/terms/|Day3解き直し|Day0→3→7|9/\d+通し"
)


def strip_jargon(text: str) -> str:
    if not text:
        return text
    out = text
    for pattern, repl in JARGON_REPLACEMENTS:
        out = out.replace(pattern, repl)
    for pattern, repl in JARGON_REGEX_REPLACEMENTS:
        out = re.sub(pattern, repl, out)
    return out


def should_skip_slug(slug: str) -> bool:
    return slug.startswith("field-")


def patch_text_columns(row: dict[str, str]) -> int:
    slug = (row.get("slug") or "").strip()
    if should_skip_slug(slug):
        return 0
    changed = 0
    cols = set(PROSE_COLUMNS) | {
        "title",
        "meta_description",
        "lead",
        "user_intent",
        "action_items",
        "key_points",
        *(f"section_{n}_heading" for n in range(1, 8)),
        *(f"faq_{n}_question" for n in range(1, 5)),
    }
    for col in cols:
        if col not in row:
            continue
        before = row.get(col) or ""
        after = strip_jargon(before)
        if after != before:
            row[col] = after
            changed += 1
    return changed


def patch_csv(*, dry_run: bool = False) -> tuple[int, int]:
    with GUIDE_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    row_count = 0
    col_count = 0
    for row in rows:
        n = patch_text_columns(row)
        if n:
            row_count += 1
            col_count += n

    if not dry_run and row_count:
        with GUIDE_CSV.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    return row_count, col_count


def patch_batch_files(*, dry_run: bool = False) -> tuple[int, int]:
    file_count = 0
    hit_count = 0
    seen: set[Path] = set()
    for pattern in BATCH_GLOBS:
        for path in sorted((ROOT / "tools").glob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8")
            if not JARGON_CHECK_RE.search(text):
                continue
            after = strip_jargon(text)
            if after != text:
                file_count += 1
                hit_count += len(JARGON_CHECK_RE.findall(text))
                if not dry_run:
                    path.write_text(after, encoding="utf-8")
    return file_count, hit_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--csv-only", action="store_true", help="CSV のみ")
    args = parser.parse_args()

    rows, cols = patch_csv(dry_run=args.dry_run)
    print(f"CSV: {rows} rows, {cols} columns {'(dry-run)' if args.dry_run else 'updated'}")

    if not args.csv_only:
        files, hits = patch_batch_files(dry_run=args.dry_run)
        print(f"batches: {files} files, ~{hits} jargon hits {'(dry-run)' if args.dry_run else 'updated'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
