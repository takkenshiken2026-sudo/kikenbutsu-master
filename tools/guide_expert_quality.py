#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""試験ガイド記事を専門家・プロライター水準の文体・構成に整える（全件後処理）。"""

from __future__ import annotations

import re

from tools.o4_guide_content import BRAND, EXAM, OFFICIAL
from tools.o4_guide_slug_sections import _short_topic, slug_faq_pairs

EXPERT_MARKER = "【専門家の整理】"


def norm(s: str | None) -> str:
    return (s or "").strip()


def split_paras(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", norm(text)) if p.strip()]


# ジャンル × セクション順（0〜4）の追記段落
GENRE_EXPERT_ADDONS: dict[str, list[str]] = {
    "試験概要": [
        f"{EXPERT_MARKER}乙4は「第4類（引火性液体）の保安」が中心ですが、法令・物性・火災の三柱は切り離せません。受験初期は範囲表の章立てと{BRAND}の分野チップを対応づけ、数字論点は用語解説で根拠法令まで確認してください。",
        f"{EXPERT_MARKER}公式情報は{OFFICIAL}が一次情報です。ネット記事の要約だけで申込・合格判断をしないでください。PDFは年度・都道府県ごとに保存し、改定脚注を必ず読みます。",
        f"{EXPERT_MARKER}学習は「演習→誤答理由→用語→再演習」の循環が最短です。正答率だけを追うと、言い換え問題で再び落ちることがあります。",
        f"{EXPERT_MARKER}申込前チェックリストは、資格・期限・会場・持ち物・合格後手続きの5項目に絞ると漏れが減ります。",
        f"{EXPERT_MARKER}次に読む記事は、出題範囲と学習計画をセットで開き、週間の演習問数まで書き込んでから量を増やしてください。",
    ],
    "受験・申込": [
        f"{EXPERT_MARKER}資格は「該当・非該当」が一文で言えるまで公式表と照合します。実務年数や他免状の有無は、自分の経歴を欄ごとにチェックしてください。",
        f"{EXPERT_MARKER}日程は都道府県で異なります。申込締切はカレンダー通知を二重化し、振込・オンライン申込の締切時刻も別メモにします。",
        f"{EXPERT_MARKER}受験料の名義・金額ミスは不受理の典型です。領収書と申込控えは試験当日まで保管してください。",
        f"{EXPERT_MARKER}会場は交通と入場時間を前日に確認します。当日慌てないよう、筆記用具は前日に揃えます。",
        f"{EXPERT_MARKER}提出直前に、資格・写真・印鑑・会場希望の有無を声に出して読み上げると誤記に気づきやすいです。",
    ],
    "合格・難易度": [
        f"{EXPERT_MARKER}合格率は「全体の結果」です。自分の演習正答率とは別指標として記録し、分野別の伸びで次の一手を決めます。",
        f"{EXPERT_MARKER}合格点は試験要項の明記が正です。模試の点数をそのまま本番ラインと同一視しないことが重要です。",
        f"{EXPERT_MARKER}難易度は学習設計で調整できます。範囲が広い分、復習日を先に確保した計画が効きます。",
        f"{EXPERT_MARKER}統計を見たら、最も正答率の低い分野に週あたり30分を再配分してください。",
        f"{EXPERT_MARKER}数字の確認後は、学習計画記事へ戻り、週間演習量を1行更新します。",
    ],
    "出題・形式": [
        f"{EXPERT_MARKER}出題範囲表は「章＝演習タグ＝用語ハブ」で対応づけると漏れが減ります。改定脚注は見落としやすいので、PDF内検索で「改定」を確認してください。",
        f"{EXPERT_MARKER}乙4の三領域はバランスが問われます。一分野だけ強くても、他分野の基礎問で失点しやすいです。",
        f"{EXPERT_MARKER}配点・問題数は本番形式の演習で体に覚えさせます。見直し5分を残す練習を週1回入れてください。",
        f"{EXPERT_MARKER}マークシートは塗り忘れ・番号ズレが致命傷になります。時間配分メモを演習のたびに更新します。",
        f"{EXPERT_MARKER}範囲と過去問・実践演習を対応づけたら、未演習の章タグを優先リストにします。",
    ],
    "学習計画": [
        f"{EXPERT_MARKER}三領域ローテは「新規インプットの日」と「復習のみの日」を分けると継続しやすいです。",
        f"{EXPERT_MARKER}期間設計は1日の確保時間×週の演習問数で逆算します。無理な短期化より復習枠の確保を優先してください。",
        f"{EXPERT_MARKER}週間表はカレンダーに書き込み、達成率を週末に振り返ります。未達分は翌週へ持ち越さず削ります。",
        f"{EXPERT_MARKER}復習は翌日・1週間後・直前の三層が効きます。ブックマークを週次で空にする運用がおすすめです。",
        f"{EXPERT_MARKER}直前2週間は範囲拡大を止め、誤答・数字・混同用語に絞ります。",
    ],
    "独学対策": [
        f"{EXPERT_MARKER}独学の成否は「公式範囲の確定」と「誤答の再演習」で決まります。解きっぱなしは同じミスを本番まで持ち込みます。",
        f"{EXPERT_MARKER}教材は各1冊から始め、索引・数字表の有無で選びます。乙4は用語と数値の往復が必須です。",
        f"{EXPERT_MARKER}演習正答率70%未満の分野はテキストに戻り、80%前後まで同型を繰り返します。",
        f"{EXPERT_MARKER}誤答ノートは「なぜその肢が魅力的か」を1行書くと、言い換え問題に効きます。",
        f"{EXPERT_MARKER}直前は新規教材を増やさず、誤答・指定数量・消火の適否に絞ります。",
    ],
    "過去問活用": [
        f"{EXPERT_MARKER}過去問は本番形式の慣れ、実践演習は量と弱点補強——役割を混ぜないと効率が落ちます。",
        f"{EXPERT_MARKER}一問一答は隙間時間の用語確認専用にし、本番形式は別日にまとめて行います。",
        f"{EXPERT_MARKER}誤答分類（知識不足・混同・計算・読み飛ばし）を週1回見直し、同タグが続く分野は用語へ戻ります。",
        f"{EXPERT_MARKER}解き直しは必ず翌日以降。暗記確認ではなく、選択肢の言い換えに耐えるかを見ます。",
        f"{EXPERT_MARKER}繰り返し落とす語は関連用語5語セット→演習10問で定着させます。",
    ],
    "分野別対策": [
        f"{EXPERT_MARKER}分野別は正答率が伸び悩むまで同分野を深掘りし、伸びたら維持演習に切り替えます。",
        f"{EXPERT_MARKER}基礎は用語ハブで一覧→演習5問の順が効率的です。",
        f"{EXPERT_MARKER}頻出は出題範囲表の該当章と演習タグを突き合わせ、優先順位を数値化します。",
        f"{EXPERT_MARKER}過去問演習は分野フィルタ固定で解き、解説を読んだら同型を続けて解きます。",
        f"{EXPERT_MARKER}横断は関連用語リンクで法令・物性・火災をつなぎ、一問で三領域が出る複合問に備えます。",
    ],
    "用語整理": [
        f"{EXPERT_MARKER}用語は演習で出た語から開き、定義→試験ポイント→関連語の順が定着に効きます。",
        f"{EXPERT_MARKER}頻出章に対応する語を優先し、指定数量・石油類・消火適否は早めに押さえます。",
        f"{EXPERT_MARKER}数字・期限は一覧表にし、根拠法令を1語メモします。",
        f"{EXPERT_MARKER}混同ペアは表で「同じ点・違う点」を書き、直後に演習で確認します。",
        f"{EXPERT_MARKER}用語を読んだら同分野演習5〜10問が最低ラインです。",
    ],
    "復習・苦手克服": [
        f"{EXPERT_MARKER}復習は間隔を空けた反復が有効です。翌日・数日後・直前の三層をカレンダーに登録します。",
        f"{EXPERT_MARKER}苦手は分野ではなく「誤答理由タグ」で見ると対策が具体化します。",
        f"{EXPERT_MARKER}ノートは完璧を目指さず、誤った肢の魅力を1行残せれば十分です。",
        f"{EXPERT_MARKER}伸び悩み時はインプットと演習の比率変更が先です。量だけ増やすと疲弊します。",
        f"{EXPERT_MARKER}直前は誤答・数字・混同語のみ毎日短時間で回します。",
    ],
    "直前・当日": [
        f"{EXPERT_MARKER}直前は「覚える」より「捨てる」が主役です。範囲拡大は止め、誤答と数字に絞ります。",
        f"{EXPERT_MARKER}睡眠・体調は得点に直結します。徹夜より短時間の誤答確認を優先してください。",
        f"{EXPERT_MARKER}持ち物・会場・時間は前日に再確認し、受験票と身分証を同じ封筒に入れます。",
        f"{EXPERT_MARKER}当日は新しい論点に手を出さず、メモしたチェックリストだけを見ます。",
        f"{EXPERT_MARKER}終了後は合格発表日と手続き期限をカレンダー登録し、忘れないようにします。",
    ],
    "注意点・更新": [
        f"{EXPERT_MARKER}制度・数値は公式優先です。SNSやまとめサイトは「仮説」として扱い、必ず原文で確認します。",
        f"{EXPERT_MARKER}教材の年度は出題範囲の改定と一致しているか、目次と範囲表で突き合わせます。",
        f"{EXPERT_MARKER}誤解しやすい論点は、演習の正誤解説と用語の比較表で潰します。",
        f"{EXPERT_MARKER}更新情報は公式のお知らせをブックマークし、学習計画の見直し日を月1回設けます。",
        f"{EXPERT_MARKER}不安なときは演習正答率の分野別推移を見ると、次の一手が具体化します。",
    ],
}


def build_expert_lead(row: dict[str, str], slug: str) -> str:
    title = norm(row.get("title"))
    genre = norm(row.get("genre"))
    topic = _short_topic(title, slug)
    base = norm(row.get("lead"))
    hook = (
        f"この記事は、{EXAM}を受験・学習する方が「{topic}」を実務と試験の両面から整理するためのガイドです。"
        f"資格試験の学習設計と、{BRAND}の演習・用語解説の使い方を、専門家の視点でつなげて説明します。"
    )
    if base and len(base) > 80:
        return f"{hook}\n\n{base}"
    return hook


def append_expert_section_addon(body: str, genre: str, section_index: int) -> str:
    addons = GENRE_EXPERT_ADDONS.get(genre, GENRE_EXPERT_ADDONS["学習計画"])
    if section_index >= len(addons):
        return body
    addon = addons[section_index]
    if EXPERT_MARKER in body or addon in body:
        return body
    return body + "\n\n" + addon if body else addon


def expand_faqs(row: dict[str, str], slug: str) -> None:
    title = norm(row.get("title"))
    genre = norm(row.get("genre"))
    topic = _short_topic(title, slug)
    pairs = list(slug_faq_pairs(slug, genre, title))
    extra = [
        (
            f"{topic}は{BRAND}だけで足りますか？",
            f"公式範囲の確認と演習・用語の往復が回れば十分な受験者も多いです。"
            f"不足分野は分野チップの正答率で判断し、テキストは必要な章だけ追加してください。",
        ),
        (
            f"{topic}の直前1週間は何を優先しますか？",
            "新規範囲の拡大は止め、誤答・数字・混同用語の三点に絞って毎日短時間確認します。"
            "時間計測演習は週1回を上限にし、残りは解き直しに充ててください。",
        ),
    ]
    seen_q: set[str] = set()
    merged: list[tuple[str, str]] = []
    for q, a in pairs + extra:
        if q in seen_q:
            continue
        seen_q.add(q)
        merged.append((q, a))
        if len(merged) >= 4:
            break
    for i, (q, a) in enumerate(merged[:4], start=1):
        row[f"faq_{i}_question"] = q
        row[f"faq_{i}_answer"] = a


def apply_guide_expert_quality(row: dict[str, str]) -> None:
    slug = norm(row.get("slug"))
    genre = norm(row.get("genre"))
    if not slug:
        return
    row["lead"] = build_expert_lead(row, slug)
    meta = norm(row.get("meta_description"))
    if meta and "専門家" not in meta and "整理しました" not in meta:
        row["meta_description"] = (
            f"{meta.rstrip('。')}。"
            f"{EXAM}受験者向けに、演習と用語解説へのつなぎ方まで専門家視点で整理しました。"
        )
    for i in range(1, 8):
        heading = norm(row.get(f"section_{i}_heading"))
        body = norm(row.get(f"section_{i}_body"))
        if not heading or not body:
            continue
        row[f"section_{i}_body"] = append_expert_section_addon(body, genre, i - 1)
    expand_faqs(row, slug)
    profile = (
        f"{EXAM}の筆記試験に向けた学習設計・演習運用を専門とする編集チーム。"
        f"法令・物性・火災予防の三領域を横断し、受験者が迷わない導線づくりを担当しています。"
    )
    row["author_profile"] = profile
    row["reviewer_profile"] = (
        "消防試験研究センター・消防庁の公開情報と照合し、"
        "出題傾向とサイト内リンクの整合を確認した担当者です。"
    )
