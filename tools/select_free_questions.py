#!/usr/bin/env python3
"""無料公開する問題（実践演習・一問一答）を選び data/free_questions.json に書き出す。

- 乙4の問題だけが対象（丙種・甲種の関連試験は別CSVで、絞り込まない）。
- 分野（category）ごとの問題数は元データの比率を保つ。
- 難易度（tags 5列目：標準/応用/難関）は、--practice-standard-ratio を指定すると
  難関は元の比率のまま・標準はその割合だけ・残りを応用に回す（応用を厚くする）。
  指定しなければ難易度も元データの比率どおり。
- 各グループ内では問題番号順に等間隔で選ぶ（偏りを避ける・再実行しても同じ結果）。
- 一度作った JSON は手で編集してよい。生成側（csv_to_exam_site_*）は JSON だけを見る。

使い方:
  python3 tools/select_free_questions.py --practice 300 --ichimon 300 --practice-standard-ratio 0.1
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


def tier_quota_weighted(groups: dict[str, list], quota: int, standard_ratio: float) -> dict[str, int]:
    """難関は元の比率・標準は quota×standard_ratio・残りを応用に配分する。"""
    base = allocate({t: len(v) for t, v in groups.items()}, quota)
    out = {t: 0 for t in groups}
    out["難関"] = base.get("難関", 0) if "難関" in groups else 0
    if "標準" in groups:
        out["標準"] = min(len(groups["標準"]), round(quota * standard_ratio))
    rest = quota - sum(out.values())
    if "応用" in groups:
        out["応用"] = min(len(groups["応用"]), rest)
        rest -= out["応用"]
    # 応用が足りない分は標準 → 難関の順で埋める
    for t in ("標準", "難関"):
        if rest > 0 and t in groups:
            add = min(len(groups[t]) - out[t], rest)
            out[t] += add
            rest -= add
    return out


def select(rows: list[dict], key_fn, total: int, standard_ratio: float | None = None) -> list:
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
        if standard_ratio is None:
            tier_quota = allocate({t: len(v) for t, v in groups.items()}, cat_quota[cat])
        else:
            tier_quota = tier_quota_weighted(groups, cat_quota[cat], standard_ratio)
        for tier, tier_rows in groups.items():
            picked.extend(spread(tier_rows, tier_quota[tier]))
    return sorted(key_fn(r) for r in picked)


def load(path: Path) -> list[dict]:
    return list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--practice", type=int, required=True)
    ap.add_argument("--ichimon", type=int, required=True)
    ap.add_argument(
        "--practice-standard-ratio",
        type=float,
        default=None,
        help="実践演習で標準問題に割く割合（例 0.1）。残りは難関（元比率）と応用。",
    )
    args = ap.parse_args()

    practice = [
        r for r in load(PRACTICE_CSV) if norm(r.get("is_invalidated")).upper() != "TRUE"
    ]
    ichimon = load(ICHIMON_CSV)
    data = {
        "_note": "無料公開する問題。ここに無い乙4の問題は公開データ（exam-site-data-*.js）に出力しない。"
        " 再選定は tools/select_free_questions.py。",
        "practice": select(
            practice, lambda r: int(r["question_no"]), args.practice, args.practice_standard_ratio
        ),
        "ichimon": select(ichimon, lambda r: norm(r["id"]), args.ichimon),
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON}: practice {len(data['practice'])}/{len(practice)}, ichimon {len(data['ichimon'])}/{len(ichimon)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
