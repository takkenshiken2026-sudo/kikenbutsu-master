#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quality gate for knowledge hub CSVs after rebuild."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

BATCH_SUFFIX_RE = re.compile(r"（S\d+）")
BATCH_SLUG_RE = re.compile(r"-s(\d+)$")
FORBIDDEN_PHRASES = (
    "手順と主体の混同。",
    "（S35）",
    "（S40）",
)

GENERIC_FAQ = "試験論点・条文・数値の対応を比較表に整理し、過去問で正誤の型を分類してください。"


def _read(name: str) -> list[dict[str, str]]:
    path = DATA / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _batch(slug: str) -> int | None:
    m = BATCH_SLUG_RE.search(slug or "")
    return int(m.group(1)) if m else None


def run_gate() -> tuple[int, dict[str, int]]:
    errors: list[str] = []
    metrics: dict[str, int] = {}

    for name in ("comparisons.csv", "numbers.csv", "mistakes.csv"):
        rows = _read(name)
        metrics[f"{name}_rows"] = len(rows)

        batch_hits = 0
        forbidden = 0
        for row in rows:
            for key, val in row.items():
                if not isinstance(val, str):
                    continue
                if BATCH_SUFFIX_RE.search(val):
                    batch_hits += 1
                for ph in FORBIDDEN_PHRASES:
                    if ph in val:
                        forbidden += 1
        metrics[f"{name}_batch_suffix_fields"] = batch_hits
        metrics[f"{name}_forbidden_phrase_hits"] = forbidden
        if batch_hits:
            errors.append(f"{name}: batch suffix in {batch_hits} fields")
        if forbidden:
            errors.append(f"{name}: forbidden phrase in {forbidden} fields")

    mistakes = _read("mistakes.csv")
    cp_by_batch: dict[int, Counter[str]] = defaultdict(Counter)
    for row in mistakes:
        b = _batch(row.get("slug", ""))
        if b is None or b < 35:
            continue
        cp_by_batch[b][row.get("confusion_point", "")] += 1
    dup_cp = sum(1 for c in cp_by_batch.values() for _, n in c.items() if n > 1)
    metrics["mistakes_duplicate_confusion_in_batch"] = dup_cp
    if dup_cp:
        errors.append(f"mistakes: {dup_cp} duplicate confusion_point values within S35+ batches")

    generic_cp = sum(1 for r in mistakes if r.get("confusion_point") == "手順と主体の混同。")
    metrics["mistakes_generic_confusion"] = generic_cp
    if generic_cp:
        errors.append(f"mistakes: {generic_cp} rows still use generic confusion_point")

    faq_generic = 0
    for name in ("comparisons.csv", "numbers.csv", "mistakes.csv"):
        for row in _read(name):
            for i in range(1, 5):
                ans = row.get(f"faq_{i}_answer", "")
                if GENERIC_FAQ in ans:
                    faq_generic += 1
    metrics["faq_boilerplate_answers"] = faq_generic

    # pattern_rows identical within batch (S35+ mistakes)
    pat_by_batch: dict[int, Counter[str]] = defaultdict(Counter)
    for row in mistakes:
        b = _batch(row.get("slug", ""))
        if b is None or b < 35:
            continue
        pat_by_batch[b][row.get("pattern_rows", "")] += 1
    dup_pat = sum(1 for c in pat_by_batch.values() for _, n in c.items() if n > 1)
    metrics["mistakes_duplicate_patterns_in_batch"] = dup_pat
    if dup_pat:
        errors.append(f"mistakes: {dup_pat} duplicate pattern_rows within S35+ batches")

    if errors:
        print("QUALITY GATE FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1, metrics
    print("QUALITY GATE OK", json.dumps(metrics, ensure_ascii=False))
    return 0, metrics


if __name__ == "__main__":
    code, _ = run_gate()
    raise SystemExit(code)
