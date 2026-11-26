#!/usr/bin/env python3
"""data/free_questions.json（無料公開する問題の一覧）を読む。

ファイルが無ければ絞り込みなし（全問公開）として扱う。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREE_JSON = ROOT / "data" / "free_questions.json"


def _load() -> dict:
    if not FREE_JSON.is_file():
        return {}
    data = json.loads(FREE_JSON.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def free_practice_nos() -> set[int] | None:
    raw = _load().get("practice")
    return {int(x) for x in raw} if isinstance(raw, list) else None


def free_ichimon_ids() -> set[str] | None:
    raw = _load().get("ichimon")
    return {str(x).strip() for x in raw} if isinstance(raw, list) else None
