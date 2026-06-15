#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消防試験研究センター公式ページから乙4試験日程を収集し data/exam_schedule_otsu4.csv に保存する。

正本は公式サイト。本 CSV はサイト内一覧の生成用キャッシュ。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.exam_schedule_regions import (  # noqa: E402
    SHIBU_REGIONS,
    official_schedule_url,
)

OUTPUT_CSV = ROOT / "data" / "exam_schedule_otsu4.csv"
CSV_FIELDS = [
    "shibu_cd",
    "prefecture",
    "region_block",
    "venue",
    "exam_date_raw",
    "exam_date_iso",
    "application_period",
    "result_date_raw",
    "result_date_iso",
    "official_url",
    "fetched_at",
]

ROW_RE = re.compile(r'<TR><TD class="td_shibuname"[^>]*>.*?</TR>', re.IGNORECASE | re.DOTALL)
CELL_RE = re.compile(r'<TD class="td_([^"]+)"[^>]*>(.*?)</TD>', re.IGNORECASE | re.DOTALL)
REIWA_DATE_RE = re.compile(r"R(\d{2})\.(\d{2})\.(\d{2})")


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def reiwa_to_iso(raw: str) -> str:
    m = REIWA_DATE_RE.search(raw or "")
    if not m:
        return ""
    reiwa_year, month, day = (int(m.group(i)) for i in range(1, 4))
    year = 2018 + reiwa_year
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def parse_schedule_rows(html: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row_html in ROW_RE.findall(html):
        cells = [(cls, strip_html(content)) for cls, content in CELL_RE.findall(row_html)]
        if not cells:
            continue
        values = [text for _, text in cells]
        if "乙４" not in values:
            continue
        by_class = {cls: text for cls, text in cells}
        rows.append(
            {
                "venue": by_class.get("jukenti", ""),
                "exam_date_raw": by_class.get("shikenbi", ""),
                "application_period": by_class.get("shinsei_u", ""),
                "result_date_raw": by_class.get("goukaku", ""),
            }
        )
    return rows


def fetch_html(shibu_cd: str, *, timeout: float = 25.0) -> str:
    url = official_schedule_url(shibu_cd)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "kikenbutsu-master-schedule-fetch/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def collect_rows(*, delay_sec: float = 0.25) -> list[dict[str, str]]:
    fetched_at = datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()
    collected: list[dict[str, str]] = []
    for code, prefecture, block in SHIBU_REGIONS:
        official_url = official_schedule_url(code)
        try:
            html = fetch_html(code)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"WARN {prefecture} ({code}): {exc}", file=sys.stderr)
            continue
        parsed = parse_schedule_rows(html)
        for item in parsed:
            collected.append(
                {
                    "shibu_cd": code,
                    "prefecture": prefecture,
                    "region_block": block,
                    "venue": item["venue"],
                    "exam_date_raw": item["exam_date_raw"],
                    "exam_date_iso": reiwa_to_iso(item["exam_date_raw"]),
                    "application_period": item["application_period"],
                    "result_date_raw": item["result_date_raw"],
                    "result_date_iso": reiwa_to_iso(item["result_date_raw"]),
                    "official_url": official_url,
                    "fetched_at": fetched_at,
                }
            )
        print(f"{prefecture}: {len(parsed)} 行")
        if delay_sec:
            time.sleep(delay_sec)
    collected.sort(key=lambda r: (r.get("exam_date_iso") or "9999", r["prefecture"], r["venue"]))
    return collected


def write_csv(rows: list[dict[str, str]], path: Path = OUTPUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch 乙4 exam schedules from official site.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not write CSV")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV)
    args = parser.parse_args()

    rows = collect_rows()
    print(f"total rows: {len(rows)}")
    if args.dry_run:
        return 0
    if not rows:
        print("ERROR: no rows fetched; CSV not updated", file=sys.stderr)
        return 1
    write_csv(rows, args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
