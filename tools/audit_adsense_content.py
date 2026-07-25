#!/usr/bin/env python3
"""AdSense「低価値コンテンツ」リスクの監査（読み取り専用）。

広告タグ（adsbygoogle）を出しているページを対象に、次の2つを定量化する。

  1. 本文（<main>）の可視テキスト量 … 薄いページの検出
  2. 定型文率 … そのページの文のうち、多数の他ページにも出現する
     「使い回し文」が占める割合（スケール生成・低付加価値の主指標）

出力（reports/adsense_content/）:
  - thin_pages.csv        本文が閾値未満のページ
  - boilerplate_pages.csv 定型文率が閾値以上のページ
  - repeated_sentences.csv 全体で最も使い回されている文
  - summary.json          エリア別の集計

破壊的変更はしない。CI ゲートではなく現状把握・改善対象の抽出に使う。

使い方:
  python3 tools/audit_adsense_content.py
  python3 tools/audit_adsense_content.py --min-chars 500 --boiler 0.5
"""
from __future__ import annotations

import argparse
import collections
import csv
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "adsense_content"

# 監査対象エリア（広告を出す静的ページ群）。
AREAS = {
    "q_ichimon": "q/ichimon",
    "q_practice": "q/practice",
    "q_past": "q/past",
    "terms": "terms",
    "articles": "articles",
}

_SCRIPT_RE = re.compile(r"<script.*?</script>", re.S)
_STYLE_RE = re.compile(r"<style.*?</style>", re.S)
_MAIN_RE = re.compile(r"<main\b.*?</main>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def has_ads(text: str) -> bool:
    return "adsbygoogle" in text


def main_text(raw: str) -> str:
    """<main> 内の可視テキストを返す（無ければ body 相当）。"""
    body = _SCRIPT_RE.sub("", raw)
    body = _STYLE_RE.sub("", body)
    m = _MAIN_RE.search(body)
    if m:
        body = m.group(0)
    body = _TAG_RE.sub(" ", body)
    return _WS_RE.sub(" ", html.unescape(body)).strip()


def sentences(text: str) -> list[str]:
    out = []
    for s in re.split(r"[。\n・]", text):
        s = s.strip()
        if len(s) >= 12:
            out.append(s)
    return out


def iter_pages():
    for area, rel in AREAS.items():
        base = ROOT / rel
        if not base.exists():
            continue
        for f in sorted(base.rglob("*.html")):
            try:
                raw = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not has_ads(raw):
                continue
            yield area, f, raw


def run(min_chars: int, boiler: float, repeat_min: int) -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    pages = []  # (area, path, text, sentence_list, char_len)
    sent_doc_count: collections.Counter[str] = collections.Counter()

    for area, f, raw in iter_pages():
        txt = main_text(raw)
        sents = sentences(txt)
        pages.append((area, f, txt, sents, len(txt)))
        for s in set(sents):  # ページ単位の出現（同一ページ内重複は1回）
            sent_doc_count[s] += 1

    if not pages:
        print("対象ページが見つかりません。")
        return 0

    # 定型文＝repeat_min ページ以上に出現する文。
    def boiler_ratio(sents: list[str]) -> float:
        if not sents:
            return 0.0
        boiler_hits = sum(1 for s in sents if sent_doc_count[s] >= repeat_min)
        return boiler_hits / len(sents)

    thin = []
    boilerplate = []
    per_area = collections.defaultdict(
        lambda: {"pages": 0, "chars_sum": 0, "thin": 0, "boiler": 0}
    )

    for area, f, txt, sents, clen in pages:
        rel = f.relative_to(ROOT).as_posix()
        br = boiler_ratio(sents)
        a = per_area[area]
        a["pages"] += 1
        a["chars_sum"] += clen
        if clen < min_chars:
            a["thin"] += 1
            thin.append((clen, rel, area))
        if br >= boiler:
            a["boiler"] += 1
            boilerplate.append((round(br, 3), clen, rel, area))

    thin.sort()
    boilerplate.sort(reverse=True)

    with (OUT / "thin_pages.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["main_chars", "path", "area"])
        w.writerows(thin)

    with (OUT / "boilerplate_pages.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["boilerplate_ratio", "main_chars", "path", "area"])
        w.writerows(boilerplate)

    with (OUT / "repeated_sentences.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["doc_count", "sentence"])
        for s, c in sent_doc_count.most_common(200):
            if c >= repeat_min:
                w.writerow([c, s])

    summary = {
        "params": {
            "min_chars": min_chars,
            "boiler_ratio_threshold": boiler,
            "repeat_min_docs": repeat_min,
        },
        "total_monetized_pages": len(pages),
        "thin_pages": len(thin),
        "boilerplate_pages": len(boilerplate),
        "by_area": {
            area: {
                "pages": a["pages"],
                "avg_main_chars": (a["chars_sum"] // a["pages"]) if a["pages"] else 0,
                "thin_pages": a["thin"],
                "boilerplate_pages": a["boiler"],
            }
            for area, a in sorted(per_area.items())
        },
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 標準出力サマリ
    print("== AdSense 低価値コンテンツ監査 ==")
    print(
        f"広告掲載ページ: {len(pages)} / "
        f"薄い(<{min_chars}字): {len(thin)} / "
        f"定型文率≥{boiler:.0%}: {len(boilerplate)}"
    )
    print("エリア別（ページ数 / 平均本文字数 / 薄い / 定型文多）:")
    for area, a in summary["by_area"].items():
        print(
            f"  {area:10s}: {a['pages']:5d} / {a['avg_main_chars']:5d}字 / "
            f"{a['thin_pages']:5d} / {a['boilerplate_pages']:5d}"
        )
    print(f"詳細CSV: {OUT.relative_to(ROOT)}/")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="AdSense 低価値コンテンツ監査")
    ap.add_argument(
        "--min-chars",
        type=int,
        default=600,
        help="本文がこの文字数未満なら『薄い』（既定600）",
    )
    ap.add_argument(
        "--boiler",
        type=float,
        default=0.5,
        help="定型文率がこの値以上なら『定型文多』（既定0.5）",
    )
    ap.add_argument(
        "--repeat-min",
        type=int,
        default=20,
        help="この数以上のページに出る文を『定型文』とみなす（既定20）",
    )
    args = ap.parse_args()
    return run(args.min_chars, args.boiler, args.repeat_min)


if __name__ == "__main__":
    raise SystemExit(main())
