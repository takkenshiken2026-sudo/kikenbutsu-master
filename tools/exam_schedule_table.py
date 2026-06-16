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

from tools.exam_schedule_regions import SHIBU_REGIONS, region_blocks  # noqa: E402


def region_block_names() -> list[str]:
    return [block for block, _ in region_blocks()]


def region_chips_html() -> str:
    chips = [
        '<button type="button" class="exam-schedule-region-chip on" data-region="" aria-pressed="true">'
        "すべて</button>"
    ]
    for block in region_block_names():
        esc = html.escape(block, quote=True)
        chips.append(
            f'<button type="button" class="exam-schedule-region-chip" data-region="{esc}" '
            f'aria-pressed="false">{html.escape(block)}</button>'
        )
    return (
        '<div class="exam-schedule-region-chips" role="group" aria-label="地方で絞り込み">'
        f"{''.join(chips)}</div>"
    )


def row_search_text(row: dict[str, str]) -> str:
    parts = [
        row.get("prefecture", ""),
        row.get("region_block", ""),
        row.get("venue", ""),
        row.get("exam_date_raw", ""),
        row.get("application_period", ""),
        row.get("result_date_raw", ""),
    ]
    return " ".join(p.strip() for p in parts if p.strip())


def prefecture_combobox_html(options: list[str]) -> str:
    items = [
        '<li role="option" class="exam-schedule-pref-option on" data-value="" tabindex="-1">'
        "すべての都道府県</li>"
    ]
    for pref in options:
        esc = html.escape(pref, quote=True)
        items.append(
            f'<li role="option" class="exam-schedule-pref-option" data-value="{esc}" tabindex="-1">'
            f"{html.escape(pref)}</li>"
        )
    return (
        '<div class="exam-schedule-pref-combobox" id="exam-schedule-pref-combobox">'
        '<span class="exam-schedule-pref-label" id="exam-schedule-pref-label">都道府県</span>'
        '<div class="exam-schedule-pref-combobox-field">'
        '<input type="text" id="exam-schedule-pref-input" class="exam-schedule-pref-input" '
        'role="combobox" aria-expanded="false" aria-controls="exam-schedule-pref-listbox" '
        'aria-autocomplete="list" aria-labelledby="exam-schedule-pref-label" '
        'placeholder="都道府県を検索・選択" autocomplete="off" value="すべての都道府県">'
        '<input type="hidden" id="exam-schedule-pref-value" value="">'
        '<button type="button" class="exam-schedule-pref-clear hide" id="exam-schedule-pref-clear" '
        'aria-label="都道府県の選択をクリア">×</button>'
        '<button type="button" class="exam-schedule-pref-toggle" id="exam-schedule-pref-toggle" '
        'aria-label="都道府県一覧を開く" aria-expanded="false"></button>'
        f'<ul id="exam-schedule-pref-listbox" class="exam-schedule-pref-listbox" role="listbox" '
        f'aria-labelledby="exam-schedule-pref-label" hidden>{"".join(items)}</ul>'
        "</div></div>"
    )


def exam_schedule_filter_script() -> str:
    return """<script>
(function(){
  var section=document.querySelector(".exam-schedule-table-section");
  if(!section){return;}
  var prefValue=document.getElementById("exam-schedule-pref-value");
  var prefInput=document.getElementById("exam-schedule-pref-input");
  var prefList=document.getElementById("exam-schedule-pref-listbox");
  var prefCombo=document.getElementById("exam-schedule-pref-combobox");
  var prefClear=document.getElementById("exam-schedule-pref-clear");
  var prefToggle=document.getElementById("exam-schedule-pref-toggle");
  var search=document.getElementById("exam-schedule-text-filter");
  var sortSel=document.getElementById("exam-schedule-sort");
  var table=document.getElementById("exam-schedule-table");
  var count=document.getElementById("exam-schedule-table-count");
  var empty=document.getElementById("exam-schedule-table-empty");
  var chips=section.querySelectorAll(".exam-schedule-region-chip");
  if(!prefValue||!prefInput||!prefList||!search||!sortSel||!table||!count){return;}
  var prefOptions=Array.prototype.slice.call(prefList.querySelectorAll(".exam-schedule-pref-option"));
  var tbody=table.tBodies[0];
  var allRows=Array.prototype.slice.call(tbody.rows);
  var activeRegion="";
  var activeOptionIndex=-1;
  function norm(s){return (s||"").toLowerCase();}
  function getPref(){return prefValue.value||"";}
  function optionLabel(opt){return (opt.textContent||"").trim();}
  function closePrefList(){
    prefList.hidden=true;
    prefInput.setAttribute("aria-expanded","false");
    if(prefToggle){prefToggle.setAttribute("aria-expanded","false");}
    if(prefCombo){prefCombo.classList.remove("open");}
    activeOptionIndex=-1;
  }
  function visiblePrefOptions(){
    return prefOptions.filter(function(opt){return !opt.hidden;});
  }
  function highlightPrefOption(index){
    var visible=visiblePrefOptions();
    for(var i=0;i<visible.length;i++){
      visible[i].classList.toggle("is-active",i===index);
    }
    activeOptionIndex=index;
    if(index>=0&&visible[index]){
      visible[index].scrollIntoView({block:"nearest"});
    }
  }
  function filterPrefOptions(query){
    var q=norm(query.replace(/すべての都道府県/g,"").trim());
    for(var i=0;i<prefOptions.length;i++){
      var opt=prefOptions[i];
      var label=optionLabel(opt);
      var show=!q||norm(label).indexOf(q)!==-1||label.indexOf(query.trim())!==-1;
      opt.hidden=!show;
    }
    highlightPrefOption(visiblePrefOptions().length?0:-1);
  }
  function openPrefList(){
    filterPrefOptions(prefInput.value);
    prefList.hidden=false;
    prefInput.setAttribute("aria-expanded","true");
    if(prefToggle){prefToggle.setAttribute("aria-expanded","true");}
    if(prefCombo){prefCombo.classList.add("open");}
  }
  function setPref(value,label){
    prefValue.value=value||"";
    var text=label||(value||"すべての都道府県");
    prefInput.value=text;
    for(var i=0;i<prefOptions.length;i++){
      var on=prefOptions[i].getAttribute("data-value")===prefValue.value;
      prefOptions[i].classList.toggle("on",on);
      prefOptions[i].setAttribute("aria-selected",on?"true":"false");
    }
    if(prefClear){prefClear.classList.toggle("hide",!prefValue.value);}
    closePrefList();
    apply();
  }
  function rowMatches(row){
    var pref=getPref();
    var q=search.value.trim();
    if(pref&&row.getAttribute("data-prefecture")!==pref){return false;}
    if(activeRegion&&row.getAttribute("data-region-block")!==activeRegion){return false;}
    if(q){
      var hay=row.getAttribute("data-search-text")||"";
      if(hay.indexOf(q)===-1&&norm(hay).indexOf(norm(q))===-1){return false;}
    }
    return true;
  }
  function sortRows(rows){
    var mode=sortSel.value;
    var sorted=rows.slice();
    if(mode==="exam-asc"){
      sorted.sort(function(a,b){
        var ai=a.getAttribute("data-exam-iso")||"9999-99-99";
        var bi=b.getAttribute("data-exam-iso")||"9999-99-99";
        return ai.localeCompare(bi);
      });
    }else if(mode==="exam-desc"){
      sorted.sort(function(a,b){
        var ai=a.getAttribute("data-exam-iso")||"";
        var bi=b.getAttribute("data-exam-iso")||"";
        return bi.localeCompare(ai);
      });
    }else if(mode==="prefecture"){
      sorted.sort(function(a,b){
        var ap=a.getAttribute("data-prefecture")||"";
        var bp=b.getAttribute("data-prefecture")||"";
        return ap.localeCompare(bp,"ja");
      });
    }else{
      sorted.sort(function(a,b){
        return Number(a.getAttribute("data-original-index"))-Number(b.getAttribute("data-original-index"));
      });
    }
    return sorted;
  }
  function apply(){
    var sorted=sortRows(allRows);
    for(var i=0;i<sorted.length;i++){tbody.appendChild(sorted[i]);}
    var visible=0;
    for(var j=0;j<allRows.length;j++){
      var show=rowMatches(allRows[j]);
      allRows[j].style.display=show?"":"none";
      if(show){visible++;}
    }
    count.textContent=visible+"件";
    if(empty){empty.classList.toggle("hide",visible>0);}
  }
  prefInput.addEventListener("focus",function(){openPrefList();});
  prefInput.addEventListener("input",function(){openPrefList();});
  prefInput.addEventListener("keydown",function(ev){
    var visible=visiblePrefOptions();
    if(ev.key==="ArrowDown"){
      ev.preventDefault();
      if(prefList.hidden){openPrefList();return;}
      var next=activeOptionIndex<0?0:Math.min(activeOptionIndex+1,visible.length-1);
      highlightPrefOption(next);
    }else if(ev.key==="ArrowUp"){
      ev.preventDefault();
      var prev=activeOptionIndex<=0?0:activeOptionIndex-1;
      highlightPrefOption(prev);
    }else if(ev.key==="Enter"){
      if(!prefList.hidden&&activeOptionIndex>=0&&visible[activeOptionIndex]){
        ev.preventDefault();
        var opt=visible[activeOptionIndex];
        setPref(opt.getAttribute("data-value")||"",optionLabel(opt));
      }
    }else if(ev.key==="Escape"){
      closePrefList();
      prefInput.blur();
    }
  });
  if(prefToggle){
    prefToggle.addEventListener("click",function(){
      if(prefList.hidden){openPrefList();prefInput.focus();}
      else{closePrefList();}
    });
  }
  if(prefClear){
    prefClear.addEventListener("click",function(){setPref("", "すべての都道府県");});
  }
  for(var p=0;p<prefOptions.length;p++){
    prefOptions[p].addEventListener("mousedown",function(ev){
      ev.preventDefault();
      setPref(this.getAttribute("data-value")||"",optionLabel(this));
    });
  }
  document.addEventListener("click",function(ev){
    if(!prefCombo||prefCombo.contains(ev.target)){return;}
    var current=getPref();
    for(var i=0;i<prefOptions.length;i++){
      if(prefOptions[i].getAttribute("data-value")===current){
        prefInput.value=optionLabel(prefOptions[i]);
        break;
      }
    }
    closePrefList();
  });
  search.addEventListener("input",apply);
  sortSel.addEventListener("change",apply);
  for(var k=0;k<chips.length;k++){
    chips[k].addEventListener("click",function(){
      var btn=this;
      activeRegion=btn.getAttribute("data-region")||"";
      for(var c=0;c<chips.length;c++){
        var on=chips[c]===btn;
        chips[c].classList.toggle("on",on);
        chips[c].setAttribute("aria-pressed",on?"true":"false");
      }
      apply();
    });
  }
  var params=new URLSearchParams(window.location.search);
  var prefParam=params.get("pref");
  if(prefParam){
    for(var o=0;o<prefOptions.length;o++){
      if(prefOptions[o].getAttribute("data-value")===prefParam){
        setPref(prefParam,optionLabel(prefOptions[o]));
        break;
      }
    }
  }
  apply();
})();
</script>"""


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
    show_note: bool = True,
    heading_title: str = "都道府県別の試験日一覧",
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
            f"{num_markup}{html.escape(heading_title)}</h2>"
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

    body_rows = []
    for idx, row in enumerate(display_rows):
        pref = row.get("prefecture", "")
        region_block = row.get("region_block", "").strip()
        search_text = html.escape(row_search_text(row), quote=True)
        body_rows.append(
            "<tr"
            f' data-original-index="{idx}"'
            f' data-prefecture="{html.escape(pref, quote=True)}"'
            f' data-region-block="{html.escape(region_block, quote=True)}"'
            f' data-exam-iso="{html.escape(row.get("exam_date_iso", ""), quote=True)}"'
            f' data-search-text="{search_text}"'
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

    note_html = ""
    if show_note:
        note_html = (
            f'<p class="exam-schedule-table-note">データ取得日：{html.escape(fetched_label)}。'
            "申込期間・試験日・合格発表は支部・受験地ごとに異なります。"
            "申込前には必ず各行の公式リンクで最新情報を確認してください（要項で再確認）。</p>"
        )

    return (
        f'<section class="seo-article-section exam-schedule-table-section" {aria}>'
        f"{heading_html}"
        f"{note_html}"
        '<div class="exam-schedule-table-tools">'
        '<div class="exam-schedule-table-tools-primary">'
        '<label class="exam-schedule-text-search" for="exam-schedule-text-filter">'
        '<span class="u-visually-hidden">キーワード検索</span>'
        '<input id="exam-schedule-text-filter" type="search" inputmode="search" '
        'autocomplete="off" placeholder="都道府県・受験地・試験日…" aria-label="試験日一覧を検索">'
        "</label>"
        '<label class="exam-schedule-sort-label" for="exam-schedule-sort">並び替え</label>'
        '<select id="exam-schedule-sort" class="exam-schedule-sort-select" aria-label="並び替え">'
        '<option value="exam-asc" selected>試験日が近い順</option>'
        '<option value="exam-desc">試験日が遠い順</option>'
        '<option value="prefecture">都道府県順</option>'
        '<option value="default">取得順</option>'
        "</select>"
        f'<span class="exam-schedule-table-count" id="exam-schedule-table-count">{len(display_rows)}件</span>'
        "</div>"
        '<div class="exam-schedule-table-tools-secondary">'
        f"{prefecture_combobox_html(options)}"
        "</div>"
        "</div>"
        f"{region_chips_html()}"
        '<p class="exam-schedule-table-empty hide" id="exam-schedule-table-empty" role="status">'
        "条件に一致する日程がありません。キーワードや地方を変えるか、都道府県を「すべて」に戻してください。</p>"
        '<div class="exam-schedule-table-wrap">'
        '<table class="seo-info-table exam-schedule-table" id="exam-schedule-table">'
        "<thead><tr>"
        "<th>都道府県</th><th>受験地</th><th>試験日</th>"
        "<th>申込期間</th><th>合格発表予定</th><th>公式</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
        f"{exam_schedule_filter_script()}"
        "</section>"
    )
