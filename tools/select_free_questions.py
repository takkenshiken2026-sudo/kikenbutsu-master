#!/usr/bin/env python3
"""無料公開する問題（実践演習・一問一答）を選び data/free_questions.json に書き出す。

- 乙4の問題だけが対象（丙種・甲種の関連試験は別CSVで、絞り込まない）。
- 分野（category）×難易度（tags 5列目：標準/応用/難関）の比率を保って間引く。
- 各グループ内では問題番号順に等間隔で選ぶ（偏りを避ける・再実行しても同じ結果）。
- 一度作った JSON は手で編集してよい。生成側（csv_to_exam_site_*）は JSON だけを見る。

使い方:
  python3 tools/select_free_questions.py --practice 300 --ichimon 300
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRACTICE_CSV = ROOT / "data" / "practice_questions.csv"
ICHIMON_CSV = ROOT / "data" / "ichimon_questions.csv"
OUT_JSON = ROOT / "data" / "free_questions.json"

DIFF_TIERS = ("標準", "応用", "難関")


def norm(s: str | None) -> str:
    return (s or "").strip()


def diff_tier(tags: str) -> str:
    parts = [p.strip() for p in norm(tags).split(";")]
    if len(parts) >= 5 and parts[4] in DIFF_TIERS:
        return parts[4]
    return ""


def allocate(sizes: dict[str, int], total: int) -> dict[str, int]:
    """最大剰余法で total を sizes の比率に配分する。"""
    whole = sum(sizes.values())
    if total >= whole:
        return dict(sizes)
    raw = {k: v * total / whole for k, v in sizes.items()}
    out = {k: int(x) for k, x in raw.items()}
    rest = total - sum(out.values())
    for k in sorted(raw, key=lambda k: (raw[k] - out[k], sizes[k]), reverse=True)[:rest]:
        out[k] += 1
    return out


def spread(items: list, n: int) -> list:
    """items から n 件を等間隔で選ぶ。"""
    if n <= 0:
        return []
    if n >= len(items):
        return list(items)
    step = len(items) / n
    return [items[int(i * step + step / 2)] for i in range(n)]


def select(rows: list[dict], key_fn, total: int) -> list:
    groups: "OrderedDict[str, list[dict]]" = OrderedDict()
    by_cat: "OrderedDict[str, list[dict]]" = OrderedDict()
    for r in rows:
        by_cat.setdefault(norm(r.get("category")), []).append(r)
    picked: list[dict] = []
    cat_quota = allocate({c: len(v) for c, v in by_cat.items()}, total)
    for cat, cat_rows in by_cat.items():
        groups = OrderedDict()
        for r in cat_rows:
            groups.setdefault(diff_tier(r.get("tags", "")), []).append(r)
        tier_quota = allocate({t: len(v) for t, v in groups.items()}, cat_quota[cat])
        for tier, tier_rows in groups.items():
            picked.extend(spread(tier_rows, tier_quota[tier]))
    return sorted(key_fn(r) for r in picked)


def load(path: Path) -> list[dict]:
    return list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--practice", type=int, required=True)
    ap.add_argument("--ichimon", type=int, required=True)
    args = ap.parse_args()

    practice = [
        r for r in load(PRACTICE_CSV) if norm(r.get("is_invalidated")).upper() != "TRUE"
    ]
    ichimon = load(ICHIMON_CSV)
    data = {
        "_note": "無料公開する問題。ここに無い乙4の問題は公開データ（exam-site-data-*.js）に出力しない。"
        " 再選定は tools/select_free_questions.py。",
        "practice": select(practice, lambda r: int(r["question_no"]), args.practice),
        "ichimon": select(ichimon, lambda r: norm(r["id"]), args.ichimon),
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON}: practice {len(data['practice'])}/{len(practice)}, ichimon {len(data['ichimon'])}/{len(ichimon)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
