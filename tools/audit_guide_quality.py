#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
試験ガイド（guide_articles.csv）の読み手向け品質を監査する。

  python3 tools/audit_guide_quality.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "guide_articles.csv"

BOILERPLATE = (
    "乙種第4類は第4類危険物（引火性液体）を中心に、法令・物性・火災予防の3領域が出題の柱です",
    "公式情報の確認ポイントと乙4マスターでの学習の進め方を整理します",
    "【本文を記入】",
)

GENERIC_LEAD = "受験・学習を検討している人向けの記事です"


@dataclass
class Issue:
    level: str
    slug: str
    check: str
    message: str


@dataclass
class Report:
    total: int = 0
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def add(self, level: str, slug: str, check: str, message: str) -> None:
        item = Issue(level, slug, check, message)
        if level == "error":
            self.errors.append(item)
        else:
            self.warnings.append(item)


def norm(s: str | None) -> str:
    return (s or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-section-chars", type=int, default=70)
    args = ap.parse_args()

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    rep = Report(total=len(rows))
    dup_phrase_counter: Counter[str] = Counter()

    for row in rows:
        slug = norm(row.get("slug"))
        bodies = []
        for i in range(1, 8):
            h = norm(row.get(f"section_{i}_heading"))
            b = norm(row.get(f"section_{i}_body"))
            if not h:
                continue
            bodies.append(b)
            if any(p in b for p in BOILERPLATE):
                rep.add("error", slug, "boilerplate", f"section_{i} に定型文が残っています")
            if len(b) < args.min_section_chars:
                rep.add("warn", slug, "short_section", f"section_{i} が短すぎます（{len(b)}字）")
            if len(b) >= 80 and b.count("。") < 2:
                rep.add("warn", slug, "thin_section", f"section_{i} の文量が少なめです")
            dup_phrase_counter[b[:60]] += 1

        if len(bodies) >= 2 and len(set(bodies)) < len(bodies):
            rep.add("error", slug, "duplicate_sections", "同一記事内でセクション本文が重複しています")

        lead = norm(row.get("lead"))
        if GENERIC_LEAD in lead and "アフィリエイト" not in lead:
            rep.add("warn", slug, "generic_lead", "リード文が汎用テンプレのままです")

        meta = norm(row.get("meta_description"))
        if meta == norm(row.get("title")) or "公式情報の確認ポイントと" in meta:
            rep.add("warn", slug, "generic_meta", "meta_description が単調です")

        if not norm(row.get("faq_1_question")) or not norm(row.get("faq_2_question")):
            rep.add("warn", slug, "faq", "FAQが未設定です")

        if not norm(row.get("related_links")) or norm(row.get("related_links")).count(";") < 1:
            rep.add("warn", slug, "related_links", "関連リンクが2件未満です")

    # 全記事で同一先頭60字が多い = まだ均一
    for prefix, count in dup_phrase_counter.items():
        if count >= 12 and len(prefix) >= 28 and prefix:
            rep.add(
                "warn",
                "(複数)",
                "mass_duplicate",
                f"同型本文の先頭が {count} 記事で一致: {prefix[:40]}…",
            )

    print(f"Guide articles: {rep.total}")
    print(f"ERROR: {len(rep.errors)}  WARN: {len(rep.warnings)}")
    for item in rep.errors[:20]:
        print(f"  [E] {item.slug} {item.check}: {item.message}")
    for item in rep.warnings[:25]:
        print(f"  [W] {item.slug} {item.check}: {item.message}")
    if len(rep.errors) > 20:
        print(f"  … errors truncated ({len(rep.errors)} total)")
    if len(rep.warnings) > 25:
        print(f"  … warnings truncated ({len(rep.warnings)} total)")

    return 1 if rep.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
