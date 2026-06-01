#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同一ハブ CSV 内の類似タイトルを slug/highlight で一意化する。"""

from __future__ import annotations

import argparse
import csv
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.hub_strip_batch_suffix import strip_batch_suffix  # noqa: E402

HUB_FILES = ("comparisons.csv", "numbers.csv", "mistakes.csv")
HUB_TAG = {
    "comparisons.csv": "比較",
    "numbers.csv": "数値",
    "mistakes.csv": "誤答",
}


def _title_key(title: str) -> str:
    return strip_batch_suffix(title.strip())


def _similar(t1: str, t2: str) -> bool:
    if not t1 or not t2:
        return False
    if t1 == t2:
        return True
    k1, k2 = _title_key(t1), _title_key(t2)
    if k1 == k2:
        return True
    return SequenceMatcher(None, k1, k2).ratio() >= 0.88


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _tweak_title(row: dict[str, str], hub_file: str, *, level: int) -> str | None:
    title = (row.get("title") or "").strip()
    if not title:
        return None
    highlight = (row.get("highlight") or "").strip()
    category = (row.get("category") or "").strip()
    slug = (row.get("slug") or "").strip()
    if level == 0:
        tag = highlight[:16] if highlight else slug.split("-")[-1] if slug else HUB_TAG.get(hub_file, "論点")
        if tag and tag not in title:
            return f"{title}｜{tag}"
    if level == 1 and highlight:
        label = highlight[:8]
        if label and not title.startswith(f"【{label}】"):
            return f"【{label}】{title}"
    if level == 2 and slug:
        tail = "-".join(slug.split("-")[-2:]) if "-" in slug else slug[-14:]
        if tail and tail not in title:
            return f"{title}｜{tail}"
    if level == 3 and category:
        label = category[:8]
        if label and not title.startswith(f"【{label}】"):
            return f"【{label}】{title}"
    if level >= 4 and slug:
        if slug not in title:
            return f"{title}｜{slug[-18:]}"
    return None


def fix_file(path: Path) -> int:
    header, rows = _read(path)
    if not rows:
        return 0
    changed = 0
    for _ in range(16):
        round_changed = 0
        active = [i for i, row in enumerate(rows) if (row.get("title") or "").strip()]
        for ai, i in enumerate(active):
            t1 = (rows[i].get("title") or "").strip()
            for j in active[ai + 1 :]:
                t2 = (rows[j].get("title") or "").strip()
                if not _similar(t1, t2):
                    continue
                for idx in (i, j):
                    row = rows[idx]
                    title = (row.get("title") or "").strip()
                    for level in range(6):
                        new_title = _tweak_title(row, path.name, level=level)
                        if new_title and new_title != title:
                            row["title"] = new_title
                            round_changed += 1
                            break
        if round_changed == 0:
            break
        changed += round_changed
    if changed:
        _write(path, header, rows)
    return changed


def fix_site(root: Path) -> int:
    data = root / "data"
    total = 0
    for name in HUB_FILES:
        path = data / name
        if not path.is_file():
            continue
        n = fix_file(path)
        if n:
            print(f"  {name}: {n} title tweaks")
        total += n
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    n = fix_site(args.root.resolve())
    print(f"done: {n} title tweaks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
