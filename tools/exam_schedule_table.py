#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/exam_schedule_otsu4.csv から試験ガイド用の乙4日程一覧 HTML を生成する。"""

from __future__ import annotations

import csv
import html
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_CSV = ROOT / "data" / "exam_schedule_otsu4.csv"

from tools.exam_schedule_regions import SHIBU_REGIONS  # noqa: E402


def load_schedule_rows(path: Path = SCHEDULE_CSV) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def latest_fetched_at(rows: list[dict[str, str]]) -> str:
    values = [r.get("fetched_at", "").strip() for r in rows if r.get("fetched_at", "").strip()]
    return max(values) if values else ""


def upcoming_rows(rows: list[dict[str, str]], *, today: date | None = None) -> list[dict[str, str]]:
    today = today or date.today()
    upcoming: list[dict[str, str]] = []
    for row in rows:
        iso = row.get("exam_date_iso", "").strip()
        if not iso:
            upcoming.append(row)
            continue
        try:
            exam_day = date.fromisoformat(iso)
        except ValueError:
            upcoming.append(row)
            continue
        if exam_day >= today:
            upcoming.append(row)
    return upcoming


def prefecture_options(rows: list[dict[str, str]]) -> list[str]:
    present = {row.get("prefecture", "").strip() for row in rows}
    ordered = [name for _, name, _ in SHIBU_REGIONS if name in present]
    extras = sorted(present - set(ordered))
    return ordered + extras


def exam_schedule_table_html(
    rows: list[dict[str, str]] | None = None,
    *,
    section_num: int | None = None,
    show_heading: bool = True,
) -> str:
    rows = rows if rows is not None else load_schedule_rows()
    display_rows = upcoming_rows(rows)
    fetched_at = latest_fetched_at(rows)
    fetched_label = fetched_at[:10] if fetched_at else "未取得"

    num_markup = (
        f'<span class="section-heading-num">{section_num}</span>'
        if section_num is not None
        else ""
    )
    heading_html = ""
    if show_heading:
        heading_html = (
            '<h2 id="exam-schedule-table-title">'
            f"{num_markup}"
            "乙4の試験日一覧（公式データから自動集計）</h2>"
        )
    aria = 'aria-labelledby="exam-schedule-table-title"' if show_heading else 'aria-label="乙4の試験日一覧"'
    if not display_rows:
        return (
            f'<section class="seo-article-section exam-schedule-table-section" {aria}>'
            f"{heading_html}"
            "<p>公式ページからの日程データはまだ取得されていません。"
            "`python3 tools/fetch_exam_schedule.py` を実行してから "
            "`python3 tools/build_all.py` を再実行してください。</p></section>"
        )

    options = prefecture_options(display_rows)
    option_html = '<option value="">すべての都道府県</option>' + "".join(
        f'<option value="{html.escape(pref)}">{html.escape(pref)}</option>' for pref in options
    )

    body_rows = []
    for row in display_rows:
        pref = row.get("prefecture", "")
        body_rows.append(
            "<tr"
            f' data-prefecture="{html.escape(pref, quote=True)}"'
            f' data-exam-iso="{html.escape(row.get("exam_date_iso", ""), quote=True)}"'
            ">"
            f"<td>{html.escape(pref)}</td>"
            f"<td>{html.escape(row.get('venue', ''))}</td>"
            f"<td>{html.escape(row.get('exam_date_raw', ''))}</td>"
            f"<td>{html.escape(row.get('application_period', ''))}</td>"
            f"<td>{html.escape(row.get('result_date_raw', ''))}</td>"
            f'<td><a href="{html.escape(row.get("official_url", ""), quote=True)}"'
            ' target="_blank" rel="noopener noreferrer">公式</a></td>'
            "</tr>"
        )

    return (
        f'<section class="seo-article-section exam-schedule-table-section" {aria}>'
        f"{heading_html}"
        f'<p class="exam-schedule-table-note">データ取得日：{html.escape(fetched_label)}。'
        "申込期間・試験日・合格発表は支部・受験地ごとに異なります。"
        "申込前には必ず各行の公式リンクで最新情報を確認してください（要項で再確認）。</p>"
        '<div class="exam-schedule-table-tools">'
        '<label for="exam-schedule-pref-filter">都道府県で絞り込み</label>'
        f'<select id="exam-schedule-pref-filter" class="exam-schedule-pref-filter">{option_html}</select>'
        f'<span class="exam-schedule-table-count" id="exam-schedule-table-count">{len(display_rows)}件</span>'
        "</div>"
        '<div class="exam-schedule-table-wrap">'
        '<table class="seo-info-table exam-schedule-table" id="exam-schedule-table">'
        "<thead><tr>"
        "<th>都道府県</th><th>受験地</th><th>試験日</th>"
        "<th>申込期間</th><th>合格発表予定</th><th>公式</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
        "<script>"
        "(function(){"
        'var sel=document.getElementById("exam-schedule-pref-filter");'
        'var table=document.getElementById("exam-schedule-table");'
        'var count=document.getElementById("exam-schedule-table-count");'
        "if(!sel||!table||!count){return;}"
        "function apply(){"
        'var pref=sel.value;var rows=table.tBodies[0].rows;var visible=0;'
        "for(var i=0;i<rows.length;i++){"
        'var show=!pref||rows[i].getAttribute("data-prefecture")===pref;'
        "rows[i].style.display=show?\"\":\"none\";"
        "if(show){visible++;}"
        "}"
        'count.textContent=visible+"件";'
        "}"
        'sel.addEventListener("change",apply);'
        "})();"
        "</script>"
        "</section>"
    )
