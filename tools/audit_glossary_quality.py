#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用語詳細記事（glossary_terms.csv）の読み手向け品質・ファクト整合を監査する。

  python3 tools/audit_glossary_quality.py
  python3 tools/audit_glossary_quality.py --json report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CSV_PATH = ROOT / "data" / "glossary_terms.csv"
PRACTICE = ROOT / "data" / "imported" / "o4_practice_500_source.csv"
ICHIMON = ROOT / "data" / "imported" / "o4_ichimon_500_source.csv"

KEEP_TERMS = {
    "公式情報",
    "復習",
    "比較表",
    "試験要項",
    "受験資格",
    "合格基準",
    "出題範囲",
    "過去問",
    "一問一答",
    "模擬試験",
    "用語解説",
    "学習記録",
}

GENERIC_PHRASES = (
    "で頻出する",
    "出題範囲において重要な概念",
    "選択肢の言い換え",
    "実践演習で誤答した",
    "繰り返し登場します",
)

META_PEER_TERMS = (
    KEEP_TERMS
    | {"ひっかけ対策", "よくある混同論点", "ひっかけ問題"}
)


@dataclass
class Issue:
    level: str  # error | warn | info
    term: str
    check: str
    message: str


@dataclass
class AuditReport:
    total: int = 0
    enriched: int = 0
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    infos: list[Issue] = field(default_factory=list)

    def add(self, level: str, term: str, check: str, message: str) -> None:
        item = Issue(level, term, check, message)
        if level == "error":
            self.errors.append(item)
        elif level == "warn":
            self.warnings.append(item)
        else:
            self.infos.append(item)


def norm(s: str | None) -> str:
    return (s or "").strip()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sentence_key(s: str) -> str:
    return re.sub(r"\s+", "", s)[:100]


def has_duplicate_subject(term: str, text: str) -> bool:
    t = norm(text)
    return f"{term}は、{term}は" in t or t.startswith(f"{term}は{term}")


def body_paragraph_count(body: str) -> int:
    return len([p for p in body.split("\n\n") if norm(p)])


def related_terms_list(raw: str) -> list[str]:
    return [x.strip() for x in re.split(r"[;,、]", raw) if x.strip()]


def build_practice_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    idx: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        blob = " ".join(
            norm(row.get(k))
            for k in ("question", "explanation", "unit", "topic", "exam_point")
        )
        for m in re.findall(r"[\u3040-\u9fff\u30a0-\u9fffA-Za-z0-9・（）()]{2,30}", blob):
            if len(m) >= 2:
                idx[m].append(row)
    return idx


def source_supports_lead(term: str, lead: str, practice_idx: dict[str, list[dict[str, str]]]) -> bool:
    """リード文の主要キーワードが問題DB解説に含まれるか（緩いファクトチェック）。"""
    lead_n = norm(lead)
    if not lead_n or len(lead_n) < 20:
        return False
    # 用語名以外の名詞っぽい断片
    chunks = re.findall(r"[\u3040-\u9fff]{4,}", lead_n.replace(term, ""))
    if not chunks:
        return True
    key = max(chunks, key=len)[:12]
    hits = practice_idx.get(term, []) + practice_idx.get(key, [])
    if not hits:
        return True
    for row in hits[:20]:
        expl = norm(row.get("explanation"))
        if key in expl or lead_n[:40] in expl:
            return True
    return False


def audit(rows: list[dict[str, str]], practice_rows: list[dict[str, str]]) -> AuditReport:
    rep = AuditReport()
    rep.total = len(rows)
    practice_idx = build_practice_index(practice_rows)

    body_openings: Counter[str] = Counter()
    lead_openings: Counter[str] = Counter()

    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue
        tags = norm(row.get("tags"))
        is_enriched = "詳細記事" in tags
        if is_enriched:
            rep.enriched += 1

        if term in KEEP_TERMS:
            continue

        short = norm(row.get("short_def"))
        body = norm(row.get("term_detail_body"))
        definition = norm(row.get("definition"))
        exam_points = norm(row.get("exam_points"))
        mistakes = norm(row.get("common_mistakes"))
        related = related_terms_list(norm(row.get("related_terms")))

        # --- 品質 ---
        if is_enriched:
            if len(short) < 18 or short in (term, f"{term}。"):
                rep.add("error", term, "short_def", f"一覧用定義が短すぎる: {short!r}")
            elif any(g in short for g in GENERIC_PHRASES) and len(short) < 80:
                rep.add("warn", term, "short_def", "汎用テンプレ文が残っている")

            if has_duplicate_subject(term, body) or has_duplicate_subject(term, short):
                rep.add("warn", term, "duplicate_subject", "「用語は、用語は…」型の重複がある")

            if body_paragraph_count(body) < 2 and len(body) < 200:
                rep.add("warn", term, "thin_body", f"詳細本文が薄い（{len(body)}字・{body_paragraph_count(body)}段落）")

            if not exam_points:
                rep.add("warn", term, "exam_points", "試験ポイント列が空")

            if not mistakes:
                rep.add("info", term, "mistakes", "よくある誤りが未設定")

            meta_peers = [p for p in related if p in META_PEER_TERMS]
            if meta_peers:
                rep.add("warn", term, "related_terms", f"メタ用語が関連に混入: {meta_peers}")

            if body:
                body_openings[body.split("\n\n")[0][:55]] += 1

            lead = norm(row.get("article_lead"))
            if lead:
                lead_openings[lead[:45]] += 1
                if "を中心に整理します" in lead and lead.count("、") < 2:
                    pass  # 新テンプレ — OK

            # 同一文の繰り返し
            sents = re.split(r"(?<=[。！？])", body.replace("\n\n", " "))
            keys = [sentence_key(s) for s in sents if len(sentence_key(s)) > 30]
            if len(keys) != len(set(keys)) and len(keys) >= 3:
                rep.add("warn", term, "duplicate_sentence", "本文内に同一・類似文が重複")

        # --- ファクト（緩い照合）---
        if is_enriched and term not in KEEP_TERMS:
            lead_core = short or definition
            if lead_core and not source_supports_lead(term, lead_core, practice_idx):
                if "詳細記事" in tags and ("実践演習連動" in tags or "一問一答連動" in tags):
                    rep.add(
                        "info",
                        term,
                        "source_alignment",
                        "リードのキーワードが問題DB解説で未確認（手書き・要目視）",
                    )

            # 正答番号・数値の孤立チェック（本文に数字があるが根拠列が空）
            nums = re.findall(r"\d+\s*L|\d+倍|\d+℃", body + short)
            if nums and not norm(row.get("legal_basis")):
                rep.add("info", term, "numeric_claim", f"数値記述あり・法令根拠列なし: {nums[:3]}")

    # テンプレ単調さ（全体）
    if rep.enriched:
        top_body, top_count = body_openings.most_common(1)[0]
        if top_count > rep.enriched * 0.15:
            rep.add(
                "warn",
                "(全体)",
                "monotone_body",
                f"同じ本文冒頭が {top_count}/{rep.enriched} 件: {top_body!r}",
            )

    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="用語詳細記事の品質・ファクト監査")
    ap.add_argument("--json", type=Path, help="JSONレポート出力先")
    args = ap.parse_args()

    if not CSV_PATH.is_file():
        print(f"CSV がありません: {CSV_PATH}", file=sys.stderr)
        return 1

    rows = load_rows(CSV_PATH)
    practice = load_rows(PRACTICE) if PRACTICE.is_file() else []
    ichimon = load_rows(ICHIMON) if ICHIMON.is_file() else []
    report = audit(rows, practice + ichimon)

    print(f"用語 {report.total} 件（詳細記事 {report.enriched} 件）")
    print(f"ERROR {len(report.errors)} / WARN {len(report.warnings)} / INFO {len(report.infos)}")

    for label, items in (
        ("ERROR", report.errors[:30]),
        ("WARN", report.warnings[:40]),
        ("INFO", report.infos[:15]),
    ):
        if not items:
            continue
        print(f"\n--- {label} ---")
        for it in items:
            print(f"  [{it.check}] {it.term}: {it.message}")

    if len(report.errors) > 30:
        print(f"  … ERROR は他 {len(report.errors) - 30} 件")
    if len(report.warnings) > 40:
        print(f"  … WARN は他 {len(report.warnings) - 40} 件")

    if args.json:
        payload = {
            "summary": {
                "total": report.total,
                "enriched": report.enriched,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "infos": len(report.infos),
            },
            "errors": [asdict(x) for x in report.errors],
            "warnings": [asdict(x) for x in report.warnings],
            "infos": [asdict(x) for x in report.infos],
        }
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")

    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
