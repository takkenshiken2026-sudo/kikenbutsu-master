#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公開 HTML と CSV 本文の誤字・重複・プレースホルダをスキャンする。

  python3 tools/audit_content_typos.py
  python3 tools/audit_content_typos.py --json report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CSV_SOURCES = [
    ROOT / "data" / "guide_articles.csv",
    ROOT / "data" / "glossary_terms.csv",
]

HTML_GLOBS = [
    "index.html",
    "about.html",
    "privacy.html",
    "related-sites.html",
    "articles/index.html",
    "articles/*/index.html",
    "terms/index.html",
    "terms/field-*/index.html",
    "terms/g-*.html",
    "q/index.html",
    "q/past/**/index.html",
    "q/practice/**/index.html",
    "q/ichimon/**/index.html",
]

# 3連続以上を許容する文字（長音・促音・省略記号・ダッシュ類）
CHAR_REPEAT_ALLOW = frozenset("ーッ…─－—―・.．")

PLACEHOLDER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("placeholder_todo", re.compile(r"\bTODO\b|TODO[:：]", re.I)),
    ("placeholder_fixme", re.compile(r"\bFIXME\b", re.I)),
    ("placeholder_lorem", re.compile(r"\blorem ipsum\b", re.I)),
    ("placeholder_tbd", re.compile(r"\bTBD\b|要確認|未記入|ダミー", re.I)),
    ("placeholder_bracket", re.compile(r"\[(?:要|未)[^\]]{0,20}\]|＜(?:要|未)[^＞]{0,20}＞")),
]

TYPO_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("dup_qualification_paren", re.compile(r"（乙種第4類）（乙種第4類）")),
    ("dup_polite", re.compile(r"(?:ですです|ますます|であるである)")),
    ("dup_subject", re.compile(r"([\u3040-\u9fffA-Za-z0-9・]{2,20})は、\1は")),
    ("triple_period", re.compile(r"。{3,}|\.{4,}")),
    ("space_before_punct", re.compile(r" [、。！？]")),
    ("fullwidth_latin_mix", re.compile(r"[Ａ-Ｚａ-ｚ]{6,}")),  # 長い全角英字列
]

# 同一文字3連続（許容文字を除く）
CHAR_TRIPLE_RE = re.compile(r"(.)\1{2,}")

# 同一語句の直後連続のみ（空白・読点なし）
WORD_REPEAT_RE = re.compile(r"([\u3040-\u9fffァ-ヶー]{3,12})\1")

# フレーズ重複（8文字以上の塊が文中で2回以上）
PHRASE_DUP_RE = re.compile(
    r"([\u3040-\u9fffA-Za-z0-9・（）()、]{8,60}?)(?=.*\1)"
)

HTML_TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S
)
JSON_LD_RE = re.compile(r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>.*?</script>", re.I | re.S)
URL_RE = re.compile(r"https?://\S+")


@dataclass
class Finding:
    check: str
    path: str
    line: int
    context: str
    message: str


def strip_html(html: str) -> str:
    t = SCRIPT_STYLE_RE.sub(" ", html)
    t = HTML_TAG_RE.sub(" ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def line_number_at(text: str, index: int) -> int:
    return text[:index].count("\n") + 1


def context_around(text: str, index: int, width: int = 50) -> str:
    start = max(0, index - width)
    end = min(len(text), index + width)
    snippet = text[start:end].replace("\n", " ")
    return snippet.strip()


def check_char_repetition(path: str, text: str, findings: list[Finding]) -> None:
    # URL 内の www 等を除外
    scrubbed = URL_RE.sub(" ", text)
    for m in CHAR_TRIPLE_RE.finditer(scrubbed):
        ch = m.group(1)
        if ch in CHAR_REPEAT_ALLOW or ch.isspace():
            continue
        if ch.isascii() and ch.isalnum():
            # 英数字3連続は英単語・略語の誤検知が多い
            continue
        if ch in "-_=" and len(m.group(0)) >= 5:
            continue
        if ch in "-_" and m.group(0).count(ch) <= 4:
            continue
        findings.append(
            Finding(
                "char_repeat",
                path,
                line_number_at(text, m.start()),
                context_around(text, m.start()),
                f"文字 '{ch}' が {len(m.group(0))} 回連続",
            )
        )


def check_patterns(
    path: str, text: str, patterns: list[tuple[str, re.Pattern[str]]], findings: list[Finding]
) -> None:
    for name, pat in patterns:
        for m in pat.finditer(text):
            findings.append(
                Finding(
                    name,
                    path,
                    line_number_at(text, m.start()),
                    context_around(text, m.start()),
                    m.group(0)[:80],
                )
            )


def check_word_repeat(path: str, text: str, findings: list[Finding]) -> None:
    for m in WORD_REPEAT_RE.finditer(text):
        word = m.group(1)
        if len(word) < 4:
            continue
        findings.append(
            Finding(
                "duplicate_word",
                path,
                line_number_at(text, m.start()),
                context_around(text, m.start()),
                f"連続重複: 「{word}」",
            )
        )


def check_phrase_dup(path: str, text: str, findings: list[Finding]) -> None:
    """長いフレーズが同一テキスト内に2回以上出る場合（CSV段落向け）。"""
    if len(text) < 80:
        return
    seen: dict[str, int] = {}
    for m in re.finditer(r"[\u3040-\u9fff][\u3040-\u9fffA-Za-z0-9・（）、。]{7,55}[。]?", text):
        frag = re.sub(r"\s+", "", m.group(0))
        if len(frag) < 12:
            continue
        seen[frag] = seen.get(frag, 0) + 1
    for frag, count in seen.items():
        if count >= 2 and len(frag) >= 18:
            idx = text.find(frag)
            findings.append(
                Finding(
                    "duplicate_phrase",
                    path,
                    line_number_at(text, idx),
                    frag[:60],
                    f"同一フレーズが {count} 回（{frag[:40]}…）",
                )
            )


def scan_text(path: str, text: str, findings: list[Finding], phrase_dup: bool = True) -> None:
    if not text.strip():
        findings.append(
            Finding("empty_content", path, 1, "", "空のテキスト")
        )
        return
    check_char_repetition(path, text, findings)
    check_patterns(path, text, TYPO_PATTERNS, findings)
    check_patterns(path, text, PLACEHOLDER_PATTERNS, findings)
    check_word_repeat(path, text, findings)
    if phrase_dup:
        check_phrase_dup(path, text, findings)


def scan_csv(path: Path, findings: list[Finding]) -> None:
    rel = str(path.relative_to(ROOT))
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            for col, val in row.items():
                if not val or col in ("slug", "reading", "importance", "priority"):
                    continue
                if len(val) < 4:
                    continue
                loc = f"{rel}:{row_num}:{col}"
                scan_text(loc, val, findings, phrase_dup=len(val) > 120)


def scan_html(path: Path, findings: list[Finding]) -> None:
    rel = str(path.relative_to(ROOT))
    raw = path.read_text(encoding="utf-8", errors="replace")
    body = JSON_LD_RE.sub(" ", SCRIPT_STYLE_RE.sub(" ", raw))
    # プレースホルダのみ生 HTML も見る
    check_patterns(rel, body, PLACEHOLDER_PATTERNS, findings)
    check_patterns(rel, body, TYPO_PATTERNS, findings)
    visible = strip_html(body)
    if len(visible) > 20:
        check_char_repetition(f"{rel}#text", visible, findings)
        check_word_repeat(f"{rel}#text", visible, findings)


def collect_html() -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for pattern in HTML_GLOBS:
        for p in sorted(ROOT.glob(pattern)):
            r = p.resolve()
            if r not in seen and p.is_file():
                seen.add(r)
                out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="公開コンテンツの誤字・重複監査")
    ap.add_argument("--json", type=Path, help="JSON 出力")
    ap.add_argument("--max", type=int, default=500, help="表示件数上限")
    args = ap.parse_args()

    findings: list[Finding] = []
    for csv_path in CSV_SOURCES:
        if csv_path.is_file():
            scan_csv(csv_path, findings)
    for html_path in collect_html():
        scan_html(html_path, findings)

    # 重複 finding を簡易統合
    uniq: list[Finding] = []
    keys: set[tuple[str, str, int, str]] = set()
    for f in findings:
        k = (f.check, f.path, f.line, f.message[:60])
        if k in keys:
            continue
        keys.add(k)
        uniq.append(f)

    uniq.sort(key=lambda x: (x.check, x.path, x.line))
    print(f"audit_content_typos: {len(uniq)} finding(s)")
    by_check: dict[str, int] = {}
    for f in uniq:
        by_check[f.check] = by_check.get(f.check, 0) + 1
    for check, n in sorted(by_check.items()):
        print(f"  {check}: {n}")

    shown = uniq[: args.max]
    for f in shown:
        print(f"\n[{f.check}] {f.path}:{f.line}")
        print(f"  {f.message}")
        if f.context:
            print(f"  … {f.context[:120]}")

    if len(uniq) > len(shown):
        print(f"\n… 他 {len(uniq) - len(shown)} 件")

    if args.json:
        args.json.write_text(
            json.dumps([asdict(f) for f in uniq], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nWrote {args.json}")

    # 重大なプレースホルダ・明らかな誤字のみ exit 1
    fatal_checks = {
        "placeholder_todo",
        "placeholder_fixme",
        "placeholder_lorem",
        "dup_qualification_paren",
        "dup_subject",
    }
    fatal = [f for f in uniq if f.check in fatal_checks]
    return 1 if fatal else 0


if __name__ == "__main__":
    raise SystemExit(main())
