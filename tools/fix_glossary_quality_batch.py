#!/usr/bin/env python3
"""One-off batch fixes for glossary quality audit findings."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "glossary_terms.csv"


def norm(s: str | None) -> str:
    return (s or "").strip()


def sentence_key(s: str) -> str:
    return re.sub(r"\s+", "", s)[:100]


def dedupe_body_paragraphs(body: str) -> str:
    """Remove duplicate sentences within each paragraph; drop duplicate-only paragraphs."""
    paras_out: list[str] = []
    for para in re.split(r"\n{2,}", norm(body)):
        sents = re.split(r"(?<=[。！？])", para)
        seen: set[str] = set()
        kept: list[str] = []
        for s in sents:
            if not norm(s):
                continue
            k = sentence_key(s)
            if len(k) <= 30:
                kept.append(s)
                continue
            if k in seen:
                continue
            seen.add(k)
            kept.append(s)
        new_para = "".join(kept).strip()
        if new_para:
            paras_out.append(new_para)
    # Drop consecutive duplicate paragraphs
    final: list[str] = []
    prev_key = ""
    for p in paras_out:
        pk = sentence_key(p)
        if pk == prev_key and len(pk) > 30:
            continue
        final.append(p)
        prev_key = pk
    return "\n\n".join(final)


def add_practice_tags(tags: str) -> str:
    parts = [x.strip() for x in tags.split(";") if x.strip()]
    for need in ("実践演習連動", "一問一答連動"):
        if need not in parts:
            parts.append(need)
    return ";".join(parts)


def main() -> int:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig")))
    fieldnames = rows[0].keys()

    fixes = {
        "グリセリン": lambda r: _fix_glycerin(r),
        "消防法施行令": lambda r: _fix_enforcement_order(r),
        "消防長": lambda r: _fix_fire_chief(r),
        "第1類危険物": lambda r: _fix_class1(r),
        "類別": lambda r: _fix_classification(r),
    }

    for row in rows:
        term = norm(row.get("term"))
        if term in fixes:
            fixes[term](row)

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print("Updated", ", ".join(fixes))
    return 0


def _fix_glycerin(row: dict[str, str]) -> None:
    row["term_detail_body"] = dedupe_body_paragraphs(
        """グリセリンは第4類危険物の第三石油類に属する水溶性液体で、指定数量は4,000 Lです。ガソリン（第一石油類）や特殊引火物、動植物油類、第6類危険物とは分類が異なります。

試験では「第三石油類のうち水溶性」「指定数量4,000 L」「アルコール類・動植物油類と混同しない」の三点がセットで問われます。

誤り。酸化性固体ではない。

誤り。ガソリンは第一石油類であり、グリセリンとは分類が異なる。

誤り。特殊引火物ではない。

誤り。禁水性物質ではない。

第三石油類は非水溶性液体と水溶性液体で指定数量が異なる。グリセリンは水溶性側の代表例です。

よくある誤りは、非水溶性・水溶性の指定数量差を見落とすことと、アルコール類や動植物油類と混同することです。

火災・消火・漏えいでは「アセトアルデヒド」「アセトン」など近い用語とセットで出題されます。定義・数値・主体の違いを表で対比し、グリセリンだけの特徴を一言で言えるようにしてください。

【試験で問われる型】五肢択一では「正しいもの／誤っているもの」に加え、グリセリンを含む肢の言い換え（第三石油類・水溶性・4,000 L）が頻出です。×になったら本ページで分類と指定数量を声に出して確認してください。

【現場・実務のイメージ】水溶性液体としての取扱い・消火・漏えい対策が適切かどうかを、品名ごとの性質と照らして判断する場面で使われます。"""
    )
    row["short_def"] = (
        "グリセリンは第4類・第三石油類の水溶性液体で、指定数量は4,000 L。"
        "非水溶性の石油類と指定数量が異なる点が試験の定番です。"
    )
    lead = norm(row.get("article_lead"))
    if "（乙種第4類）（乙種第4類）" in lead:
        row["article_lead"] = lead.replace("（乙種第4類）（乙種第4類）", "（乙種第4類）")


def _fix_enforcement_order(row: dict[str, str]) -> None:
    row["tags"] = add_practice_tags(norm(row.get("tags")))
    row["explanation"] = (
        "試験では、消防法・危険物の規制に関する政令・消防法施行令の三層と、"
        "「政令で定める」「施行令で定める」の条文文言の正誤が問われます。"
        "実践演習で施設基準や手続の根拠法令が問われたら、このページで役割分担を整理してから解き直してください。"
    )


def _fix_fire_chief(row: dict[str, str]) -> None:
    row["tags"] = add_practice_tags(norm(row.get("tags")))
    row["explanation"] = (
        "試験では、消防長・消防署長・都道府県知事など、消防行政の主体と権限の所在が問われます。"
        "任命主体や命令・監督の範囲を混同しやすいため、実践演習で主体名が出たら本ページの比較表で確認してください。"
    )


def _fix_class1(row: dict[str, str]) -> None:
    row["tags"] = add_practice_tags(norm(row.get("tags")))
    row["explanation"] = (
        "第1類は酸化性固体の類別です。乙4は第4類が中心ですが、"
        "「第○類に属するものはどれか」で他類の代表例と混同しないよう、"
        "実践演習・一問一答で類別を含む問題は各類のキーワードを声に出して確認してください。"
    )


def _fix_classification(row: dict[str, str]) -> None:
    row["explanation"] = (
        "危険物は第1類（酸化性固体）から第6類（酸化性液体）まで六つの類に分かれます。"
        "乙4では第4類（引火性液体）が中心ですが、正誤の肢で他類の性質説明が混ざる問題が頻出です。"
        "実践演習で「第○類」の組合せが出たら、固体／液体／自然発火性などのキーワードで区別してください。"
    )


if __name__ == "__main__":
    raise SystemExit(main())
