#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用語詳細のゼロ書き直し品質ゲート（CSV + 生成HTML）。

  python3 tools/verify_glossary_rewrite.py --term アセトン
  python3 tools/verify_glossary_rewrite.py --term アセトン --term 特殊引火物
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_glossary_pages import load_glossary_entries, norm  # noqa: E402
from tools.glossary_remediation_rules import audit_remediation_row  # noqa: E402

CSV_PATH = ROOT / "data" / "glossary_terms.csv"
TERMS_DIR = ROOT / "terms"

HTML_FORBIDDEN = (
    (re.compile(r"根拠法令です"), "html_forbidden_legal_phrase"),
    (re.compile(r"別表第1上的"), "html_forbidden_beppyo_jo"),
    (re.compile(r"【[1-4]】"), "html_faq_hub_remnant"),
    (re.compile(r"compare表|numbersページ|観点[A-D]"), "html_hub_operator_text"),
    (re.compile(r"このページは、危険物取扱者試験"), "html_boilerplate_lead"),
    (re.compile(r"【試験で問われる型】|【現場・実務のイメージ】|【整理のコツ】"), "html_generic_heading"),
    (re.compile(r"誤り。第1類ではない"), "html_scattered_wrong_answers"),
)

# 「アニリンは、エチレングリコールは第4類…」型（別物質名の連結崩れ）
CROSS_TERM_GLITCH = re.compile(
    r"([\u4e00-\u9fffァ-ヶー・]{2,20})は、([\u4e00-\u9fffァ-ヶー・]{2,20})は第\d+類"
)


def _has_cross_term_glitch(text: str) -> bool:
    for m in CROSS_TERM_GLITCH.finditer(text or ""):
        if m.group(1) != m.group(2):
            return True
    return False

LEAD_BOILERPLATE = re.compile(
    r"このページは、危険物取扱者試験|ひとことで言うと、|定義のあと、具体例・試験ポイント"
)


@dataclass
class VerifyResult:
    term: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_csv_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _row_for_term(rows: list[dict[str, str]], term: str) -> dict[str, str] | None:
    for row in rows:
        if norm(row.get("term")) == term:
            return row
    return None


def _html_path_for_term(term: str) -> Path | None:
    for entry in load_glossary_entries():
        if entry["term"] == term:
            return TERMS_DIR / entry["slug_file"]
    return None


def _strip_tags(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _section_text(html: str, section_id: str) -> str:
    m = re.search(
        rf'<section[^>]*aria-labelledby="{re.escape(section_id)}"[^>]*>(.*?)</section>',
        html,
        flags=re.S,
    )
    if m:
        return _strip_tags(m.group(1))
    m = re.search(
        rf'id="{re.escape(section_id)}"[^>]*>(.*?)</div>\s*</div>',
        html,
        flags=re.S,
    )
    return _strip_tags(m.group(1)) if m else ""


def verify_csv_row(row: dict[str, str], result: VerifyResult) -> None:
    term = norm(row.get("term"))
    checks = audit_remediation_row(row)
    if checks.priority_score():
        for label in checks.failing_labels():
            result.errors.append(f"csv_remediation:{label}")

    short = norm(row.get("short_def"))
    lead = norm(row.get("article_lead"))
    if LEAD_BOILERPLATE.search(lead):
        result.errors.append("csv_boilerplate_lead")

    if short and lead and short[:40] in lead[:80]:
        result.warnings.append("csv_short_def_overlaps_lead")

    body = norm(row.get("term_detail_body"))
    if body and not body.startswith("###"):
        result.warnings.append("csv_body_missing_h3")

    for n in range(1, 5):
        ans = norm(row.get(f"faq_{n}_answer"))
        if len(ans) < 100:
            result.errors.append(f"csv_faq_{n}_too_short")

    related = [t.strip() for t in norm(row.get("related_terms")).split(";") if t.strip()]
    rows = _load_csv_rows()
    by_term = {norm(r.get("term")): r for r in rows}
    for rel in related:
        rel_row = by_term.get(rel)
        if not rel_row:
            result.warnings.append(f"csv_related_missing:{rel}")
            continue
        rel_short = norm(rel_row.get("short_def"))
        if _has_cross_term_glitch(rel_short):
            result.errors.append(f"csv_related_glitch:{rel}")


def verify_html(term: str, row: dict[str, str], result: VerifyResult) -> None:
    path = _html_path_for_term(term)
    if not path or not path.is_file():
        result.errors.append("html_missing")
        return

    html = path.read_text(encoding="utf-8")
    plain = _strip_tags(html)

    for pattern, code in HTML_FORBIDDEN:
        if pattern.search(html) or pattern.search(plain):
            result.errors.append(code)

    short = norm(row.get("short_def"))
    summary_text = _section_text(html, "term-sec-summary")
    if short and summary_text == short:
        pass  # expected for summary section
    def_text = _section_text(html, "term-sec-definition")
    if short and short in def_text and len(def_text) < len(short) + 40:
        result.errors.append("html_definition_only_short_def")

    if short and short in _section_text(html, "term-sec-faq"):
        result.warnings.append("html_short_def_in_faq")

    related_block = _section_text(html, "term-related-title")
    if _has_cross_term_glitch(related_block):
        result.errors.append("html_related_glitch")


def verify_term(term: str) -> VerifyResult:
    result = VerifyResult(term=term)
    rows = _load_csv_rows()
    row = _row_for_term(rows, term)
    if not row:
        result.errors.append("csv_term_not_found")
        return result
    verify_csv_row(row, result)
    verify_html(term, row, result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="用語ゼロ書き直しの品質ゲート")
    ap.add_argument("--term", action="append", required=True, help="検証する用語名")
    args = ap.parse_args()

    failed = 0
    for term in args.term:
        result = verify_term(term)
        status = "OK" if result.ok else "FAIL"
        print(f"=== {term} [{status}] ===")
        for err in result.errors:
            print(f"  ERROR: {err}")
        for warn in result.warnings:
            print(f"  WARN:  {warn}")
        if not result.errors and not result.warnings:
            print("  (no issues)")
        print()
        if not result.ok:
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
