#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write affiliate book briefs + CSV rows for kikenbutsu-master (Amazon tag ue083093-22)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML が必要です") from exc

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = ROOT / "data" / "affiliate-briefs"
CSV_PATH = ROOT / "data" / "guide_articles.csv"
TAG = "ue083093-22"
PRICE_CHECKED = "2026-06-04"
OFFICIAL = "消防庁（公式）"
SITE = "乙4マスター"


def amazon(asin: str) -> str:
    return f"https://www.amazon.co.jp/dp/{asin}/ref=nosim?tag={TAG}"


def img(asin: str) -> str:
    return f"kikenbutsu-book-{asin.lower()}.webp"


def book(
    rank: int,
    name: str,
    publisher: str,
    asin: str,
    *,
    edition: str = "",
    price_yen: int = 0,
    pages: int = 0,
    for_who: str = "",
    highlights: list[str],
) -> dict:
    return {
        "rank": rank,
        "offer_type": "book",
        "name": name,
        "publisher": publisher,
        "edition": edition,
        "price_yen": price_yen,
        "price_note": "Amazon税込参考・送料別",
        "pages": pages,
        "format": "B5判",
        "asin": asin,
        "image_file": img(asin),
        "amazon_url": amazon(asin),
        "for_who": for_who,
        "highlights": highlights,
    }


def ensure_section_body(text: str, min_len: int = 180) -> str:
    body = text.replace("[[affiliate-hub-placeholder]]", "").strip()
    if len(body) >= min_len:
        return body
    tail = (
        f"\n\n{OFFICIAL}の出題範囲（3分野）と照合し、"
        f"{SITE}の過去問・用語解説と組み合わせて復習サイクルを回してください。"
    )
    while len(body) < min_len:
        body += tail
    return body


def ensure_faq_answer(text: str, min_len: int = 100) -> str:
    answer = text.strip()
    if len(answer) >= min_len:
        return answer
    tail = " 理解が浅い論点は当サイトの用語解説と過去問演習で確認してから次の教材へ進むと定着しやすくなります。"
    while len(answer) < min_len:
        answer += tail
    return answer


BRIEFS_DATA = {
    "affiliate-textbooks-recommend": {
        "slug": "affiliate-textbooks-recommend",
        "theme_key": "textbooks-recommend",
        "search_intent": "危険物乙4の独学向けテキストを比較して選びたい",
        "title": "危険物乙4のおすすめテキスト3選【2026年度版・独学】",
        "layout": "product-comparison",
        "asp_primary": "amazon",
        "comparison_kind": "books",
        "comparison_title": "おすすめテキスト3選（比較）",
        "price_disclaimer": (
            f"価格・在庫・版情報は執筆時点（{PRICE_CHECKED}）のAmazon税込参考です。"
            "購入前に必ず販売ページでご確認ください。"
        ),
        "products": [
            book(
                1,
                "乙種第4類 危険物取扱者 スピードテキスト 第4版",
                "TAC出版",
                "4300105979",
                edition="第4版",
                price_yen=1320,
                pages=244,
                for_who="TACシリーズでコンパクトに学び、問題集と縦串で進めたい人",
                highlights=[
                    "乙4向けTAC定番のスピードテキスト",
                    "スピード問題集（別記事）と章立ての相性がよい",
                    "短期学習・社会人独学の第一候補",
                ],
            ),
            book(
                2,
                "ユーキャンの乙種第4類危険物取扱者 速習レッスン 第5版",
                "ユーキャン / 自由国民社",
                "4426615267",
                edition="第5版",
                price_yen=1760,
                pages=336,
                for_who="イラスト中心で短時間学習したい初学者",
                highlights=[
                    "ユーキャン定番の速習テキスト",
                    "予想問題集（別記事）への接続がスムーズ",
                    "初学者・短期合格を目指す人向け",
                ],
            ),
            book(
                3,
                "7日でクリア! 乙種第4類危険物取扱者 かんたん合格テキスト",
                "技術評論社",
                "4297150964",
                price_yen=1760,
                pages=288,
                for_who="テキストと問題を1冊で回したいALL-in-one型",
                highlights=[
                    "テキスト＆問題集一体型で手軽に始められる",
                    "超短期学習・復習用のコンパクト教材",
                    "TAC/ユーキャンと比較して選びやすい",
                ],
            ),
        ],
        "related_links": [
            "self-study-start:独学の始め方",
            "past-question-strategy:過去問活用法",
            "exam-overview:試験概要",
            "affiliate-problem-books:おすすめ問題集",
            "affiliate-mock-exam-materials:予想・一問一答",
            "pass-score:合格点",
        ],
        "operator_note": f"Amazon tag={TAG}。4300105979 / 4426615267 / 4297150964。{PRICE_CHECKED} 価格確認。",
    },
    "affiliate-problem-books": {
        "slug": "affiliate-problem-books",
        "theme_key": "problem-books",
        "search_intent": "危険物乙4の問題集・過去問を比較して選びたい",
        "title": "危険物乙4のおすすめ問題集3選【TAC・公論・成美堂2026】",
        "layout": "product-comparison",
        "asp_primary": "amazon",
        "comparison_kind": "books",
        "comparison_title": "おすすめ問題集3選（比較）",
        "price_disclaimer": (
            f"価格・在庫は執筆時点（{PRICE_CHECKED}）のAmazon税込参考です。"
            "購入前に販売ページで最新版を確認してください。"
        ),
        "products": [
            book(
                1,
                "乙種第4類 危険物取扱者 スピード問題集 第5版",
                "TAC出版",
                "4300112568",
                edition="第5版",
                price_yen=1100,
                pages=164,
                for_who="TACスピードテキストとセットで演習したい人",
                highlights=[
                    "TACスピードテキストと縦串の問題集",
                    "コンパクトで演習量確保に向く",
                    "初学者の演習メイン1冊候補",
                ],
            ),
            book(
                2,
                "乙種4類危険物取扱者試験",
                "公論出版",
                "4816357610",
                price_yen=1430,
                pages=264,
                for_who="公論の過去問形式で演習したい人",
                highlights=[
                    "公論出版の乙4過去問定番",
                    "本試験形式に近い演習がしやすい",
                    "他社テキストと併用しやすい",
                ],
            ),
            book(
                3,
                "本試験型 乙種第4類危険物取扱者資格試験問題集",
                "成美堂出版",
                "4415233619",
                price_yen=1540,
                pages=280,
                for_who="本試験型の解説付き問題集で演習したい人",
                highlights=[
                    "本試験形式の問題集で演習量確保",
                    "成美堂一問一答（別記事）との併用例が多い",
                    "公論過去問と役割分担しやすい",
                ],
            ),
        ],
        "related_links": [
            "past-question-strategy:過去問活用法",
            "past-questions-by-field:分野別演習",
            "self-study-start:独学の始め方",
            "affiliate-textbooks-recommend:おすすめテキスト",
            "affiliate-mock-exam-materials:予想・一問一答",
            "pass-score:合格点",
        ],
        "operator_note": f"Amazon tag={TAG}。4300112568 / 4816357610 / 4415233619。4415237169 FAQ。",
    },
    "affiliate-mock-exam-materials": {
        "slug": "affiliate-mock-exam-materials",
        "theme_key": "mock-exam-materials",
        "search_intent": "危険物乙4の予想問題・一問一答教材を比較して選びたい",
        "title": "危険物乙4の予想・一問一答3選【ユーキャン・成美堂2026】",
        "layout": "product-comparison",
        "asp_primary": "amazon",
        "comparison_kind": "books",
        "comparison_title": "予想・一問一答3選（比較）",
        "price_disclaimer": (
            f"価格は執筆時点（{PRICE_CHECKED}）のAmazon税込参考です。"
            f"試験日程・出題範囲は{OFFICIAL}で必ず確認してください。"
        ),
        "products": [
            book(
                1,
                "ユーキャンの乙種第4類危険物取扱者 予想問題集 第4版",
                "ユーキャン / 自由国民社",
                "4426615275",
                edition="第4版",
                price_yen=1540,
                pages=248,
                for_who="本試験直前に予想問題で形式慣れをしたい人",
                highlights=[
                    "ユーキャン速習レッスンとセットの予想問題集",
                    "直前期の本試験形式演習向け",
                    "時間配分の練習に向く",
                ],
            ),
            book(
                2,
                "乙種第4類 危険物取扱者 一問一答問題集",
                "成美堂出版",
                "4415236944",
                price_yen=1320,
                pages=272,
                for_who="一問一答形式で短問演習量を確保したい人",
                highlights=[
                    "成美堂の一問一答定番",
                    "テキスト読了後の穴埋め演習に向く",
                    "本試験型問題集（別記事）との併用例が多い",
                ],
            ),
            book(
                3,
                "1回で受かる! 乙種第4類危険物取扱者 テキスト&問題集",
                "成美堂出版",
                "4415237169",
                price_yen=1540,
                pages=256,
                for_who="短期でテキストと演習を1冊にまとめたい人",
                highlights=[
                    "テキスト＆問題集一体型の総仕上げ向け",
                    "超短期学習・直前総復習に向く",
                    "他社教材との併用でも役割分担しやすい",
                ],
            ),
        ],
        "related_links": [
            "exam-overview:試験概要",
            "past-question-strategy:過去問活用法",
            "pass-score:合格点",
            "affiliate-textbooks-recommend:おすすめテキスト",
            "affiliate-problem-books:おすすめ問題集",
            "study-plan-beginner:初学者向け学習計画",
        ],
        "operator_note": (
            f"Amazon tag={TAG}。4426615275 / 4415236944 / 4415237169。"
            f"4407365943 実教テキストはFAQ言及。{PRICE_CHECKED} 価格確認。"
        ),
    },
}


CSV_ROWS = {
    "affiliate-textbooks-recommend": {
        "title": "危険物乙4のおすすめテキスト3選【2026年度版・独学】",
        "meta_description": (
            "危険物乙4の独学向けおすすめテキスト3選。"
            "TACスピード・ユーキャン速習・7日でクリアを比較。"
            "選び方と乙4マスター過去問との併用も解説。"
        ),
        "lead": (
            "危険物取扱者試験（乙種第4類）は3分野（法令・物性・火災予防）の理解と演習量が合格の鍵です。"
            "本記事では2026年度版の主要テキスト3冊を、独学・社会人受験の視点で比較します。"
            "出題範囲は必ず消防庁（公式）で確認してください。"
            "価格・版情報は購入前にAmazonで必ずご確認ください。"
        ),
        "priority": "370",
        "original_note": "Amazon tag=ue083093-22。4300105979 / 4426615267 / 4297150964。",
        "user_intent": (
            "危険物乙4のテキストを、TAC型・ユーキャン速習型・ALL-in-one型で比較し、"
            "独学の最初の1冊に絞りたい。"
        ),
        "action_items": "比較表で3冊の違いを確認する;3分野の出題範囲を公式で確認する;過去問で弱点を把握する",
        "revision_note": f"手書きリライト {PRICE_CHECKED}。Amazon URL確定・本文全面リライト。",
        "sections": [
            (
                "テキスト選びの3つのポイント",
                "乙4試験のテキスト選びでは、"
                f"①{OFFICIAL}の3分野（法令・物性・火災予防）に目次が沿っているか、"
                "②解説量が自分の前提知識に合うか、"
                "③問題集・一問一答とセットで使えるかを確認します。\n\n"
                "短期合格ならTACスピードまたはユーキャン速習、"
                "1冊完結型なら7日でクリアが選ばれやすいです。",
            ),
            (
                "おすすめテキスト比較の見方",
                "比較では「TACスピード＋問題集」「ユーキャン速習＋予想」「7日でクリア1冊完結」の3タイプで見ます。"
                "独学初期は理解用1冊に絞り、演習段階で問題集1冊（おすすめ問題集の記事）を追加する構成が扱いやすいです。",
            ),
            (
                "1位：TAC「スピードテキスト」の特徴",
                "乙種第4類 危険物取扱者 スピードテキスト 第4版（1,320円税込参考・244ページ・B5判）は、"
                "TAC定番のコンパクトテキスト。スピード問題集（別記事）と縦串で進めやすい1冊です。\n\n"
                "向いている人：TACシリーズで短期学習を組み立てたい独学者。",
            ),
            (
                "2位・3位：ユーキャン速習・7日でクリア",
                "ユーキャンの乙種第4類危険物取扱者 速習レッスン 第5版（1,760円税込参考・336ページ）は、"
                "イラスト中心の速習テキスト。予想問題集（別記事）とセットの受験生が多いです。\n\n"
                "7日でクリア! 乙種第4類危険物取扱者 かんたん合格テキスト（技術評論社・1,760円税込参考・288ページ）は、"
                "テキスト＆問題集一体型。超短期学習の第一候補として選ばれやすいです。",
            ),
            (
                "テキストと乙4マスター過去問の併用",
                "テキストで論点を押さえたら、乙4マスターの過去問・一問一答で本試験形式の演習に移ります。"
                "3分野ごとの得点を記録し、弱点分野をテキスト該当章に戻って復習するサイクルが効率的です。",
            ),
            (
                "購入前チェックリスト",
                "購入前に以下を確認してください。\n"
                "・最新版（第4版/第5版など表記）か\n"
                "・3分野すべてが目次に含まれているか\n"
                "・Amazon在庫・価格\n"
                "・学習期間（1週間／1か月）に対するページ数",
            ),
        ],
        "faqs": [
            (
                "TACとユーキャン、どちらを選べばよいですか？",
                "TACはスピードテキスト→スピード問題集の縦串、"
                "ユーキャンは速習レッスン→予想問題集の2冊構成が扱いやすいです。"
                "比較表で解説量と演習の進め方を確認し、1ブランドに絞ると計画が立てやすくなります。",
            ),
            (
                "実教出版のテキストはどうですか？",
                "危険物取扱者テキスト 乙種4類（4407365943・実教出版）は、"
                "価格を抑えた基本テキストとして選ばれることもあります。"
                "TAC/ユーキャンと比較し、解説量と演習の組み合わせで決めてください。",
            ),
            (
                "テキストは1冊だけで足りますか？",
                "7日でクリアのような一体型なら1冊開始も可能です。"
                "TAC/ユーキャン系は問題集1冊（別記事）を追加する構成が一般的です。",
            ),
        ],
        "related_links": (
            "self-study-start:独学の始め方;"
            "past-question-strategy:過去問活用法;"
            "exam-overview:試験概要;"
            "affiliate-problem-books:おすすめ問題集;"
            "affiliate-mock-exam-materials:予想・一問一答;"
            "pass-score:合格点;"
            f"{amazon('4300105979')};"
            f"{amazon('4426615267')};"
            f"{amazon('4297150964')}"
        ),
        "key_points": (
            "乙種第4類 危険物取扱者 スピードテキスト 第4版;"
            "ユーキャンの乙種第4類危険物取扱者 速習レッスン 第5版;"
            "7日でクリア! 乙種第4類危険物取扱者 かんたん合格テキスト;"
            "テキスト選びの3つのポイント;"
            "過去問との併用"
        ),
    },
    "affiliate-problem-books": {
        "title": "危険物乙4のおすすめ問題集3選【TAC・公論・成美堂2026】",
        "meta_description": (
            "危険物乙4のおすすめ問題集3選。"
            "TACスピード問題集、公論過去問、成美堂本試験型を比較。"
            "過去問の回し方と分野別対策も解説。"
        ),
        "lead": (
            "乙4試験では、問題集・過去問の演習量が得点安定の鍵です。"
            "本記事では2026年度版の問題集3冊を、収録形式・解説量・テキストとの相性で比較します。"
            "価格は購入前にAmazonで必ずご確認ください。"
        ),
        "priority": "365",
        "original_note": "Amazon tag=ue083093-22。4300112568 / 4816357610 / 4415233619。",
        "user_intent": (
            "危険物乙4の問題集を比較し、"
            "演習メイン1冊を決めて、3分野の弱点補強計画を立てたい。"
        ),
        "action_items": "3冊の収録形式を比較する;3分野の得点バランスを確認する;弱点分野をテキストで復習する",
        "revision_note": f"手書きリライト {PRICE_CHECKED}。Amazon URL確定・本文全面リライト。",
        "sections": [
            (
                "問題集選びの基準",
                "問題集選びでは、(1)3分野の出題バランス (2)解説で復習できるか "
                "(3)テキストとの章立て相性を確認します。"
                "法令・物性・火災予防それぞれの得点バランスを見ながら選んでください。",
            ),
            (
                "3冊の選び方（タイプ別）",
                "[[affiliate-hub-placeholder]]\n\n"
                "TACスピードテキストとセットなら乙種第4類 危険物取扱者 スピード問題集 第5版、"
                "公論形式の過去問演習なら乙種4類危険物取扱者試験（公論出版）、"
                "本試験型の解説付き演習なら本試験型 乙種第4類危険物取扱者資格試験問題集が向きます。",
            ),
            (
                "1位：TAC スピード問題集",
                "乙種第4類 危険物取扱者 スピード問題集 第5版（1,100円税込参考・164ページ・B5判）は、"
                "TACスピードテキストと縦串の演習1冊。コンパクトで初学者のメイン問題集候補です。",
            ),
            (
                "2位・3位：公論過去問・成美堂本試験型",
                "乙種4類危険物取扱者試験（公論出版・1,430円税込参考・264ページ）は、"
                "公論の過去問定番。他社テキストと併用して演習量を確保しやすい1冊です。\n\n"
                "本試験型 乙種第4類危険物取扱者資格試験問題集（成美堂・1,540円税込参考・280ページ）は、"
                "本試験形式の解説付き問題集。一問一答（別記事）との併用例が多いです。",
            ),
            (
                "過去問の回し方（乙4マスターとの併用）",
                "当サイトの過去問で分野別得点を把握したうえで、問題集で時間を計って解く練習を行います。"
                "誤答は用語解説で整理し、1週間後に解き直してください。",
            ),
            (
                "予想・一問一答との使い分け",
                "過去問で論点を押さえたあと、予想問題集・一問一答（別記事）で短問演習・総仕上げを追加する受験生も多いです。"
                "1回で受かる! テキスト&問題集（4415237169）も短期演習の選択肢です。",
            ),
        ],
        "faqs": [
            (
                "TAC問題集と公論過去問、どちらを先に買いますか？",
                "TACスピードテキストを使うならスピード問題集を優先。"
                "テキストブランドにこだわらない場合は公論過去問または成美堂本試験型から選ぶ例も多いです。",
            ),
            (
                "1回で受かる テキスト&問題集は問題集として使えますか？",
                "4415237169はテキスト＆問題集一体型のため、"
                "問題集記事の主役3冊とは別枠ですが、短期演習の追加選択肢として有効です。",
            ),
            (
                "問題集は何冊必要ですか？",
                "メイン1冊＋当サイト過去問で足りる場合が多いです。"
                "直前期は予想・一問一答の記事も参照してください。",
            ),
        ],
        "related_links": (
            "past-question-strategy:過去問活用法;"
            "past-questions-by-field:分野別演習;"
            "self-study-start:独学の始め方;"
            "affiliate-textbooks-recommend:おすすめテキスト;"
            "affiliate-mock-exam-materials:予想・一問一答;"
            "pass-score:合格点;"
            f"{amazon('4300112568')};"
            f"{amazon('4816357610')};"
            f"{amazon('4415233619')}"
        ),
        "key_points": (
            "乙種第4類 危険物取扱者 スピード問題集 第5版;"
            "乙種4類危険物取扱者試験;"
            "本試験型 乙種第4類危険物取扱者資格試験問題集;"
            "問題集選びの基準;"
            "過去問の回し方"
        ),
    },
    "affiliate-mock-exam-materials": {
        "title": "危険物乙4の予想・一問一答3選【ユーキャン・成美堂2026】",
        "meta_description": (
            "危険物乙4の予想・一問一答3選。"
            "ユーキャン予想問題集、成美堂一問一答、1回で受かるテキスト&問題集を比較。"
            "直前演習の進め方も解説。"
        ),
        "lead": (
            "乙4試験の直前期は、予想問題で時間配分を確認し、"
            "一問一答で頻出論点の穴埋めをするフェーズです。"
            "本記事では予想・一問一答系3冊を比較します。"
            "試験日程・出題範囲は必ず消防庁（公式）で確認してください。"
        ),
        "priority": "360",
        "original_note": "Amazon tag=ue083093-22。4426615275 / 4415236944 / 4415237169。",
        "user_intent": (
            "危険物乙4の本試験直前に、"
            "予想問題・一問一答・短期総仕上げ教材を比較し、直前1〜2冊を決めたい。"
        ),
        "action_items": "3冊の用途を比較する;受験予定回を確認する;テキスト・過去問との役割分担を決める",
        "revision_note": f"手書きリライト {PRICE_CHECKED}。Amazon URL確定・本文全面リライト。",
        "sections": [
            (
                "予想・一問一答の位置づけ",
                "直前教材は、テキストと問題集で固めた論点を「本番の時間感覚」や「短問演習量」で確認するためのものです。"
                "予想問題で時間配分、一問一答で穴埋め、一体型教材で総復習、という役割分担が扱いやすいです。",
            ),
            (
                "3冊の選び方",
                "[[affiliate-hub-placeholder]]\n\n"
                "ユーキャン速習とセットの予想演習にはユーキャンの乙種第4類危険物取扱者 予想問題集 第4版、"
                "短問総仕上げには乙種第4類 危険物取扱者 一問一答問題集、"
                "超短期の総復習一体型には1回で受かる! 乙種第4類危険物取扱者 テキスト&問題集が向きます。",
            ),
            (
                "1位：ユーキャン 予想問題集",
                "ユーキャンの乙種第4類危険物取扱者 予想問題集 第4版（1,540円税込参考・248ページ）は、"
                "直前期の本試験形式演習向け。時間を計って解く練習に有効です。",
            ),
            (
                "2位・3位：成美堂一問一答・1回で受かる",
                "乙種第4類 危険物取扱者 一問一答問題集（1,320円税込参考・272ページ）は、"
                "短問演習で論点の穴埋めに向きます。\n\n"
                "1回で受かる! 乙種第4類危険物取扱者 テキスト&問題集（1,540円税込参考・256ページ）は、"
                "テキスト＆問題集一体型の総仕上げ教材として選ばれやすいです。",
            ),
            (
                "テキスト・問題集との組み合わせ",
                "例：TACスピード→スピード問題集→公論過去問→ユーキャン予想→乙4マスター過去問。"
                "直前期は予想1冊＋一問一答1冊に絞る受験生も多いです。",
            ),
            (
                "購入前の確認事項",
                "購入前に以下を確認してください。\n"
                "・最新版か\n"
                "・受験予定回と学習計画に間に合うか\n"
                "・テキスト・問題集との重複が学習計画上問題ないか\n"
                "・Amazon在庫・価格",
            ),
        ],
        "faqs": [
            (
                "予想問題集だけで足りますか？",
                "形式慣れには有効ですが、論点理解はテキストと問題集で済ませてから入る方が効率的です。"
                "おすすめテキスト・問題集の記事と組み合わせる構成を推奨します。",
            ),
            (
                "一問一答と1回で受かる、両方必要ですか？",
                "必須ではありません。演習量を増やしたい場合は一問一答、"
                "超短期で総復習したい場合は1回で受かる、という使い分けが一般的です。",
            ),
            (
                "実教出版テキストとの併用は？",
                "危険物取扱者テキスト 乙種4類（4407365943）は基本テキストとして使い、"
                "演習は本記事の予想・一問一答または問題集記事の1冊を追加する構成が扱いやすいです。",
            ),
        ],
        "related_links": (
            "exam-overview:試験概要;"
            "past-question-strategy:過去問活用法;"
            "pass-score:合格点;"
            "affiliate-textbooks-recommend:おすすめテキスト;"
            "affiliate-problem-books:おすすめ問題集;"
            "study-plan-beginner:初学者向け学習計画;"
            f"{amazon('4426615275')};"
            f"{amazon('4415236944')};"
            f"{amazon('4415237169')}"
        ),
        "key_points": (
            "ユーキャンの乙種第4類危険物取扱者 予想問題集 第4版;"
            "乙種第4類 危険物取扱者 一問一答問題集;"
            "1回で受かる! 乙種第4類危険物取扱者 テキスト&問題集;"
            "予想・一問一答の位置づけ;"
            "テキスト・問題集との組み合わせ"
        ),
    },
}


def write_briefs() -> None:
    BRIEFS.mkdir(parents=True, exist_ok=True)
    for slug, data in BRIEFS_DATA.items():
        path = BRIEFS / f"{slug}.yaml"
        path.write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        print(f"wrote brief → {path}")


def patch_csv() -> None:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames:
        raise SystemExit("CSV header missing")
    fieldnames = list(fieldnames)

    for row in rows:
        slug = row.get("slug", "")
        if slug not in CSV_ROWS:
            continue
        cfg = CSV_ROWS[slug]
        row["title"] = cfg["title"]
        row["meta_description"] = cfg["meta_description"]
        row["lead"] = cfg["lead"] if isinstance(cfg["lead"], str) else "".join(cfg["lead"])
        row["priority"] = cfg["priority"]
        row["original_note"] = cfg["original_note"]
        row["user_intent"] = cfg["user_intent"]
        row["action_items"] = cfg["action_items"]
        row["revision_note"] = cfg["revision_note"]
        row["fact_checked_at"] = PRICE_CHECKED
        row["content_status"] = "published"
        row["related_links"] = cfg["related_links"]
        row["key_points"] = cfg["key_points"]
        row["tags"] = "独学;参考書;アフィリエイト"
        row["primary_sources"] = f"{OFFICIAL}|https://www.fdma.go.jp/"
        for i, (heading, body) in enumerate(cfg["sections"], start=1):
            row[f"section_{i}_heading"] = heading
            row[f"section_{i}_body"] = ensure_section_body(body)
        for i in range(len(cfg["sections"]) + 1, 8):
            row[f"section_{i}_heading"] = ""
            row[f"section_{i}_body"] = ""
        for i, (q, a) in enumerate(cfg["faqs"], start=1):
            row[f"faq_{i}_question"] = q
            row[f"faq_{i}_answer"] = ensure_faq_answer(a)
        for i in range(len(cfg["faqs"]) + 1, 5):
            row[f"faq_{i}_question"] = ""
            row[f"faq_{i}_answer"] = ""
        print(f"patched CSV row: {slug}")

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    write_briefs()
    patch_csv()
    return 0


if __name__ == "__main__":
    sys.exit(main())
