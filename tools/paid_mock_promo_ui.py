#!/usr/bin/env python3
"""静的ページ（過去問一覧・試験日一覧・試験ガイド記事）に置く有料予想模試の案内ボックス。

- 商品情報は site-config.json の paidMockExam から取る（URL・価格・画像を一元管理）。
- 文面はページごとに書き分ける。同じ文を全ページに貼らない（CLAUDE.md の定型文禁止）。
- 価格は設定の priceLabel の文字で出す（価格改定時に画像を作り直さずに済むよう、バナー画像は使わない）。
- 商品の中身について書いてよいのは設定にある事実だけ
  （35問・2時間・PDF・2回分・価格・note販売）。解説の有無などは未確認のため書かない。
"""

from __future__ import annotations

import html
from pathlib import Path

from tools.site_config import paid_mock_exam

# 試験ガイド記事：試験前の読者が読む記事に限定する（合格後の手続き・仕事系には出さない）。
ARTICLE_LEADS: dict[str, str] = {
    "study-plan": (
        "計画の最後の1〜2週間には、35問を2時間で通して解く日を入れておくと仕上がりを測れます。"
        "サイトの演習を一通り終えた段階で使える予想模試を用意しています。"
    ),
    "past-question-strategy": (
        "このサイトで解ける過去問は1年分の35問です。"
        "同じ問題を2周目に解くと答えを覚えてしまうため、初見の35問で本番形式を測りたい人向けに予想模試を用意しています。"
    ),
    "exam-schedule": (
        "受験日が決まったら、その2週間前を目安に本番と同じ35問・2時間で一度通してみてください。"
        "時間配分と科目ごとの取りこぼしが本番前に見えます。"
    ),
    "pass-rate": (
        "乙4は合計点ではなく、3科目それぞれで60%以上が必要です。"
        "本番前に35問を通しで解き、どの科目が危ないかを数字で確かめておくと対策の優先順位が決まります。"
    ),
    "exam-difficulty": (
        "難易度の感じ方は、時間を計って35問を解いたときに初めて実感できます。"
        "本番前の実力確認に使える予想模試を用意しています。"
    ),
    "pass-score": (
        "法令9問・物理化学6問・性質消火6問のどれか1つでも欠けると不合格です。"
        "35問を通しで解いて、自分の点数が各科目のラインを越えているかを試験前に確認できます。"
    ),
    "final-day-checklist": (
        "前日に新しい範囲へ手を広げるより、2時間を通して解く体力と時間配分を確かめておく方が当日に効きます。"
        "直前の通し練習用に予想模試を用意しています。"
    ),
    "law-study-method": (
        "法令は3科目で最も問題数が多く、15問中9問が必要です。"
        "他の2科目と混ぜた35問の中で法令に何分かかるかを、本番形式で一度測っておくと安心です。"
    ),
    "physchem-study-method": (
        "物理・化学は10問中6問が合格ラインです。"
        "35問・2時間の中で計算問題に時間をかけすぎないかを、本番形式で確かめておけます。"
    ),
    "properties-study-method": (
        "性質・消火は品名ごとの数字や例外を正確に覚えているかが問われる科目です。"
        "3科目を混ぜた本番形式の35問で、知識が定着しているかを確かめられます。"
    ),
    "prep-course": (
        "講習会のあとに自宅で本番形式を試したい人向けに、35問・2時間の予想模試を用意しています。"
        "講習で押さえた範囲がどこまで得点につながるかを測れます。"
    ),
}

Q_INDEX_LEAD = (
    "掲載している過去問は1年分の35問です。"
    "解き終えたら、別の35問で本番と同じ2時間の通し練習ができる予想模試も用意しています。"
)

EXAM_DATES_LEAD = (
    "受験日が決まったら、試験の2週間前を目安に35問・2時間の通し練習を一度入れておくと、"
    "時間配分と苦手科目を本番前に確認できます。"
)


def paid_mock_callout_html(rel_path: Path, lead: str) -> str:
    """有料予想模試の案内ボックス。設定が無い・文面が空なら空文字。"""
    cfg = paid_mock_exam()
    if not cfg or not lead:
        return ""
    url = cfg["url"]
    price = cfg.get("priceLabel", "")
    meta = cfg.get("scoreMeta", "")
    title = cfg.get("cardTitle") or cfg.get("modeTitle", "予想模試")
    foot = cfg.get("footnote", "")
    link_attrs = f'href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer"'

    spec = "・".join(x for x in (meta, price) if x)
    return (
        '<aside class="paid-mock-callout" aria-label="有料の予想模試の案内">'
        f'<p class="paid-mock-callout__label">有料・{html.escape(title)}</p>'
        f'<p class="paid-mock-callout__lead">{html.escape(lead)}</p>'
        f'<a class="paid-mock-callout__cta" {link_attrs}>'
        f"noteで模試を見る{('（' + html.escape(spec) + '）') if spec else ''} ↗</a>"
        + (f'<p class="paid-mock-callout__foot">{html.escape(foot)}</p>' if foot else "")
        + "</aside>"
    )


def article_paid_mock_callout_html(slug: str, rel_path: Path) -> str:
    return paid_mock_callout_html(rel_path, ARTICLE_LEADS.get(slug, ""))


def q_index_paid_mock_callout_html(rel_path: Path) -> str:
    return paid_mock_callout_html(rel_path, Q_INDEX_LEAD)


def exam_dates_paid_mock_callout_html(rel_path: Path) -> str:
    return paid_mock_callout_html(rel_path, EXAM_DATES_LEAD)
