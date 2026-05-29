#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove internal batch labels like （S33） from public hub CSV fields."""

from __future__ import annotations

import re

BATCH_SUFFIX_RE = re.compile(r"（S\d+）|\(S\d+\)")

# slug は内部識別子として -s35 等を残す
_SKIP_KEYS = frozenset({"slug"})


def strip_batch_suffix(text: str) -> str:
    if not text or not BATCH_SUFFIX_RE.search(text):
        return text
    cleaned = BATCH_SUFFIX_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def strip_hub_row(row: dict[str, str]) -> dict[str, str]:
    for key, val in row.items():
        if key in _SKIP_KEYS or not isinstance(val, str):
            continue
        row[key] = strip_batch_suffix(val)
    return row


def strip_hub_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    for row in rows:
        strip_hub_row(row)
    return rows
