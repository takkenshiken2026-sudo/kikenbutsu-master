#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一問一答の解説を簡潔な一文に整える（【試験ポイント】【ひっかけ】を除去して統合）。"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICHIMON_CSV = ROOT / "data" / "ichimon_questions.csv"
SOURCE_CSV = ROOT / "data" / "imported" / "o4_ichimon_500_source.csv"

_TAG_SPLIT = re.compile(r"\n\n*【試験ポイント】|\n\n*【ひっかけ】|【試験ポイント】|【ひっかけ】")


def norm(s: str | None) -> str:
    return (s or "").strip()


def split_verdict(text: str) -> tuple[str, str]:
    text = norm(text)
    for v in ("正しい", "誤り"):
        if text.startswith(v):
            return v, text[len(v) :].lstrip("。． ").strip()
    return "", text


def split_sentences(body: str) -> list[str]:
    body = re.sub(r"\s+", " ", body)
    parts = re.split(r"(?<=[。．])\s*", body)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not p.endswith("。"):
            p += "。"
        out.append(p)
    return out


def dedupe_sentences(sents: list[str]) -> list[str]:
    kept: list[str] = []
    for s in sents:
        sc = s.rstrip("。")
        replaced = False
        for i, k in enumerate(kept):
            kc = k.rstrip("。")
            if sc == kc:
                replaced = True
                break
            if sc in kc or kc in sc:
                if len(sc) > len(kc):
                    kept[i] = s
                replaced = True
                break
        if not replaced:
            kept.append(s)
    return kept


def drop_short_opening(sents: list[str], verdict: str) -> list[str]:
    if verdict == "誤り" or len(sents) < 2:
        return sents
    first_len = len(sents[0].rstrip("。"))
    second_len = len(sents[1].rstrip("。"))
    if first_len < second_len * 0.72:
        return sents[1:]
    return sents


def compress_parts(parts: list[str], verdict: str) -> list[str]:
    if len(parts) <= 2:
        return parts
    if verdict == "誤り":
        return [parts[0], "、".join(parts[1:])]
    return [max(parts, key=len)]


def is_contained(text: str, corpus: list[str]) -> bool:
    t = text.rstrip("。")
    if not t:
        return True
    for c in corpus:
        cc = c.rstrip("。")
        if t in cc or cc in t:
            return True
    return False


def join_body_parts(parts: list[str], verdict: str) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]

    first, *rest = parts
    if verdict == "誤り":
        tail = "、".join(rest) if len(rest) > 1 else (rest[0] if rest else "")
        if not tail:
            return first
        if first.endswith("ない") or "ではない" in first:
            return f"{first}、{tail}"
        return f"{first}、{tail}"

    if len(parts) == 2:
        second = rest[0]
        if "とは異なる" in second and first.rstrip("。").endswith("である"):
            return f"{first.rstrip('。')[:-3]}で、{second}"
        return f"{first}、{second}"

    merged = first.rstrip("。")
    for p in rest:
        p = p.rstrip("。")
        if "とは異なる" in p or re.search(
            r"^(移動|給油|屋外|屋内|販売|一般|移送)", p
        ):
            if merged.endswith("である"):
                merged = merged[:-3] + "で、" + p
            else:
                merged = merged + "、" + p
        else:
            merged = merged + "。" + p
    return merged


def polish_phrasing(text: str) -> str:
    text = re.sub(
        r"である、(?=移動|給油|屋外|屋内|一般|移送|販売|第|アルコール|灯油|ガソリン|エタノール|アセトン|特殊|動植物)",
        "で、",
        text,
    )
    text = text.replace("。、", "、")
    text = re.sub(r"。{2,}", "。", text)
    return text


def simplify(main: str, exam_point: str = "", trap_point: str = "") -> str:
    """解説本文を簡潔な一文に整える（試験ポイント・ひっかけは統合しない）。"""
    del exam_point, trap_point  # 旧形式の重複を避け、本文のみで構成
    main = norm(main)
    if _TAG_SPLIT.search(main):
        chunks = _TAG_SPLIT.split(main)
        main = norm(chunks[0])

    verdict, body = split_verdict(main)
    sents = dedupe_sentences(split_sentences(body))
    sents = drop_short_opening(sents, verdict)
    parts = compress_parts([s.rstrip("。") for s in sents], verdict)
    core = join_body_parts(parts, verdict).rstrip("。") + "。"
    out = f"{verdict}。{core}" if verdict else core
    return polish_phrasing(out)


def load_source_map() -> dict[str, dict[str, str]]:
    if not SOURCE_CSV.is_file():
        return {}
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as f:
        return {norm(r["id"]): r for r in csv.DictReader(f) if norm(r.get("id"))}


def main() -> int:
    if not ICHIMON_CSV.is_file():
        print(f"missing: {ICHIMON_CSV}", file=sys.stderr)
        return 1

    src_map = load_source_map()
    text = ICHIMON_CSV.read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    fieldnames = rows[0].keys() if rows else []

    changed = 0
    for row in rows:
        rid = norm(row.get("id"))
        src = src_map.get(rid, {})
        if src:
            new_exp = simplify(
                src.get("explanation", ""),
                src.get("exam_point", ""),
                src.get("trap_point", ""),
            )
        else:
            new_exp = simplify(row.get("explanation", ""))
        if norm(row.get("explanation")) != new_exp:
            changed += 1
        row["explanation"] = new_exp

    with ICHIMON_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    bad = [r["id"] for r in rows if "【試験ポイント】" in r["explanation"] or "【ひっかけ】" in r["explanation"]]
    print(f"updated {changed}/{len(rows)} explanations in {ICHIMON_CSV}")
    if bad:
        print(f"still tagged: {bad[:10]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
