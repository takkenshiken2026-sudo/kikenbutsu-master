#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
執筆済み CSV 行が一次ソース・ブリーフと矛盾しないか検証。

  python3 tools/glossary_rewrite_validate.py --term ジエチルエーテル
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.glossary_rewrite_brief import build_brief, norm  # noqa: E402
from tools.verify_glossary_rewrite import verify_term  # noqa: E402

CSV_PATH = ROOT / "data" / "glossary_terms.csv"
REWRITE_TAG = "rewrite:2026-06"

# 分類キーワード → 行内に含めるべき表現（特殊引火物クラスタ）
CLASSIFICATION_ASSERTIONS: dict[str, list[tuple[str, str]]] = {
    "ジエチルエーテル": [
        ("must_contain", "特殊引火物"),
        ("must_not_contain", "第二石油類"),
        ("must_not_contain", "アルコール類"),
        ("must_not_contain", "動植物油類"),
    ],
    "二硫化炭素": [
        ("must_contain", "特殊引火物"),
        ("must_not_contain", "第二石油類"),
        ("must_not_contain", "不燃性"),
        ("must_not_contain", "動植物油類"),
    ],
    "特殊引火物": [("must_contain", "50 L")],
    "アセトン": [("must_contain", "第一石油類"), ("must_contain", "400 L")],
    "アニリン": [("must_contain", "第三石油類")],
    "アセトアルデヒド": [("must_contain", "特殊引火物"), ("must_contain", "50 L")],
    "ガソリン": [
        ("must_contain", "第一石油類"),
        ("must_contain", "200 L"),
        ("must_not_contain", "第二石油類"),
    ],
    "灯油": [
        ("must_contain", "第二石油類"),
        ("must_contain", "1,000 L"),
        ("must_not_contain", "第一石油類"),
    ],
    "軽油": [
        ("must_contain", "第二石油類"),
        ("must_contain", "1,000 L"),
        ("must_not_contain", "第三石油類"),
    ],
    "重油": [
        ("must_contain", "第三石油類"),
        ("must_contain", "2,000 L"),
        ("must_not_contain", "第二石油類"),
    ],
    "メタノール": [
        ("must_contain", "アルコール類"),
        ("must_contain", "400 L"),
        ("must_not_contain", "第一石油類"),
        ("must_not_contain", "第二石油類"),
    ],
    "エタノール": [
        ("must_contain", "アルコール類"),
        ("must_contain", "400 L"),
        ("must_not_contain", "第一石油類"),
    ],
    "動植物油類": [
        ("must_contain", "10,000 L"),
        ("must_not_contain", "6,000 L"),
    ],
    "動植物油": [
        ("must_contain", "動植物油類"),
        ("must_not_contain", "第四石油類"),
    ],
    "第四石油類": [
        ("must_contain", "6,000 L"),
        ("must_not_contain", "10,000 L"),
    ],
    "潤滑油類": [
        ("must_contain", "第四石油類"),
        ("must_contain", "6,000 L"),
        ("must_not_contain", "第三石油類"),
    ],
    "ベンゼン": [
        ("must_contain", "第一石油類"),
        ("must_not_contain", "第二石油類"),
    ],
    "トルエン": [
        ("must_contain", "第一石油類"),
        ("must_not_contain", "第二石油類"),
        ("must_not_contain", "動植物油類"),
    ],
    "キシレン": [
        ("must_contain", "第二石油類"),
        ("must_not_contain", "特殊引火物"),
    ],
    "酢酸": [
        ("must_contain", "第二石油類"),
        ("must_contain", "2,000 L"),
        ("must_not_contain", "第一石油類"),
    ],
    "酢酸エチル": [
        ("must_contain", "第一石油類"),
        ("must_not_contain", "第二石油類"),
    ],
    "エチレングリコール": [
        ("must_contain", "第三石油類"),
        ("must_not_contain", "アルコール類"),
    ],
    "クレオソート油": [
        ("must_contain", "第三石油類"),
        ("must_not_contain", "第二石油類"),
    ],
    "グリセリン": [
        ("must_contain", "第三石油類"),
        ("must_contain", "4,000 L"),
        ("must_not_contain", "第一石油類"),
    ],
    "引火点": [
        ("must_contain", "火源"),
        ("must_not_contain", "火源がなく"),
    ],
    "発火点": [
        ("must_contain", "火源がなく"),
        ("must_not_contain", "火源を近づけ"),
    ],
    "沸点": [
        ("must_contain", "沸騰"),
        ("must_not_contain", "火源を近づけ"),
    ],
    "比熱": [
        ("must_contain", "1 g"),
        ("must_not_contain", "色の濃さ"),
    ],
    "液比重": [
        ("must_contain", "水を基準"),
        ("must_not_contain", "空気を基準"),
    ],
    "蒸気比重": [
        ("must_contain", "空気を基準"),
        ("must_not_contain", "水を基準"),
    ],
    "融点・沸点": [
        ("must_contain", "固体"),
        ("must_contain", "沸騰"),
        ("must_not_contain", "火源を近づけ"),
    ],
    "熱容量": [
        ("must_contain", "物体全体"),
        ("must_not_contain", "火源で引火"),
    ],
    "温度と熱量": [
        ("must_contain", "熱量"),
        ("must_not_contain", "引火点"),
    ],
    "潜熱・顕熱": [
        ("must_contain", "状態変化"),
        ("must_contain", "顕熱"),
        ("must_not_contain", "色を変える"),
    ],
    "熱伝導": [
        ("must_contain", "物質内"),
        ("must_not_contain", "無関係"),
    ],
    "熱膨張": [
        ("must_contain", "温度上昇"),
        ("must_not_contain", "免状"),
    ],
    "熱伝導・対流・放射": [
        ("must_contain", "対流"),
        ("must_contain", "放射"),
        ("must_not_contain", "無関係"),
    ],
    "熱量の計算": [
        ("must_contain", "質量"),
        ("must_contain", "温度"),
        ("must_not_contain", "免状"),
    ],
    "密度・質量・体積の計算": [
        ("must_contain", "質量÷体積"),
        ("must_contain", "密度×体積"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "比重の計算": [
        ("must_contain", "質量÷体積"),
        ("must_contain", "0.8"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "体積の計算": [
        ("must_contain", "密度×体積"),
        ("must_contain", "400 g"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "計算問題": [
        ("must_contain", "質量÷体積"),
        ("must_contain", "溶質÷溶液"),
        ("must_contain", "温度上昇"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "濃度の計算": [
        ("must_contain", "溶質÷溶液"),
        ("must_contain", "10 %"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "密度": [
        ("must_contain", "質量÷体積"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "比重": [
        ("must_contain", "水を基準"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "密度・比重": [
        ("must_contain", "密度と比重を混同しない"),
        ("must_contain", "液比重"),
        ("must_contain", "蒸気比重"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "液体の比重と水への浮沈": [
        ("must_contain", "水に浮き"),
        ("must_contain", "溶けること"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "燃焼範囲": [
        ("must_contain", "混合"),
        ("must_contain", "薄すぎ"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "下限界・上限界": [
        ("must_contain", "下限界"),
        ("must_contain", "上限界"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "燃焼範囲・爆発範囲": [
        ("must_contain", "燃焼範囲"),
        ("must_contain", "爆発"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "爆発範囲": [
        ("must_contain", "爆発"),
        ("must_contain", "混合"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "下限界": [
        ("must_contain", "下限界"),
        ("must_contain", "薄すぎ"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "上限界": [
        ("must_contain", "上限界"),
        ("must_contain", "濃すぎ"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "可燃性蒸気と空気の混合危険": [
        ("must_contain", "燃焼範囲"),
        ("must_contain", "引火"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "可燃性蒸気と空気の混合": [
        ("must_contain", "混合"),
        ("must_contain", "燃焼範囲"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "可燃性蒸気": [
        ("must_contain", "低所"),
        ("must_contain", "第4類"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "燃焼": [
        ("must_contain", "酸化"),
        ("must_contain", "可燃物"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "燃焼の三要素": [
        ("must_contain", "可燃物"),
        ("must_contain", "点火源"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "引火・発火・自然発火の違い": [
        ("must_contain", "引火"),
        ("must_contain", "火源"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "燃焼の継続": [
        ("must_contain", "連鎖"),
        ("must_contain", "抑制"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "燃焼の継続・連鎖反応の考え方": [
        ("must_contain", "連鎖"),
        ("must_contain", "抑制"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "完全燃焼・不完全燃焼": [
        ("must_contain", "完全"),
        ("must_contain", "一酸化炭素"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "完全燃焼": [
        ("must_contain", "酸素"),
        ("must_contain", "二酸化炭素"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "不完全燃焼": [
        ("must_contain", "一酸化炭素"),
        ("must_contain", "酸素"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "完全燃焼と不完全燃焼": [
        ("must_contain", "完全"),
        ("must_contain", "一酸化炭素"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "窒息消火": [
        ("must_contain", "酸素"),
        ("must_contain", "断"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "除去消火": [
        ("must_contain", "可燃物"),
        ("must_contain", "取り除"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "冷却消火": [
        ("must_contain", "温度"),
        ("must_contain", "下げ"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "抑制消火": [
        ("must_contain", "連鎖"),
        ("must_contain", "抑制"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "抑制消火・負触媒効果": [
        ("must_contain", "負触媒"),
        ("must_contain", "連鎖"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "負触媒効果": [
        ("must_contain", "負触媒"),
        ("must_contain", "抑制"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "粉末消火剤": [
        ("must_contain", "粉末"),
        ("must_contain", "連鎖"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "粉末消火": [
        ("must_contain", "粉末"),
        ("must_contain", "連鎖"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "泡消火": [
        ("must_contain", "泡"),
        ("must_contain", "液面"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "泡消火剤": [
        ("must_contain", "泡"),
        ("must_contain", "液面"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "二酸化炭素消火": [
        ("must_contain", "二酸化炭素"),
        ("must_contain", "窒息"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "粉末消火剤の基本作用": [
        ("must_contain", "連鎖"),
        ("must_contain", "粉末"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "粉末消火剤の適用": [
        ("must_contain", "第4類"),
        ("must_contain", "粉末"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "水による消火の特徴": [
        ("must_contain", "冷却"),
        ("must_contain", "温度"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "水による消火が不適切な場合": [
        ("must_contain", "棒状"),
        ("must_contain", "非水溶性"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "泡・二酸化炭素・粉末消火剤の基本作用": [
        ("must_contain", "泡"),
        ("must_contain", "連鎖"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "泡・二酸化炭素・粉末消火剤の適用": [
        ("must_contain", "第4類"),
        ("must_contain", "泡"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "消火剤": [
        ("must_contain", "消火剤"),
        ("must_contain", "第4類"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "消火方法": [
        ("must_contain", "除去"),
        ("must_contain", "窒息"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "消火": [
        ("must_contain", "三要素"),
        ("must_contain", "除去"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "漏えい": [
        ("must_contain", "漏えい"),
        ("must_contain", "通報"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "漏えい・流出時の危険": [
        ("must_contain", "火気"),
        ("must_contain", "回収"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "漏えい防止": [
        ("must_contain", "漏えい"),
        ("must_contain", "裸火"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "漏えい対策": [
        ("must_contain", "火気"),
        ("must_contain", "回収"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "火災予防": [
        ("must_contain", "換気"),
        ("must_contain", "可燃性蒸気"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "火気・静電気・漏えい防止": [
        ("must_contain", "静電気"),
        ("must_contain", "火気"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "換気": [
        ("must_contain", "換気"),
        ("must_contain", "滞留"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "静電気": [
        ("must_contain", "静電気"),
        ("must_contain", "接地"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "火気管理": [
        ("must_contain", "火気"),
        ("must_contain", "換気"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "接地": [
        ("must_contain", "接地"),
        ("must_contain", "静電気"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "静電気対策": [
        ("must_contain", "静電気"),
        ("must_contain", "接地"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "予防規程": [
        ("must_contain", "予防規程"),
        ("must_contain", "保安"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "自然発火": [
        ("must_contain", "自然発火"),
        ("must_contain", "酸化"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "危険物施設保安員": [
        ("must_contain", "保安"),
        ("must_contain", "施設"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "標識・掲示板": [
        ("must_contain", "標識"),
        ("must_contain", "掲示"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "危険物取扱者": [
        ("must_contain", "危険物取扱者"),
        ("must_contain", "乙種"),
        ("must_not_contain", "pH"),
    ],
    "設置許可": [
        ("must_contain", "許可"),
        ("must_contain", "指定数量"),
        ("must_not_contain", "pH"),
    ],
    "完成検査": [
        ("must_contain", "完成検査"),
        ("must_contain", "検査"),
        ("must_not_contain", "pH"),
    ],
    "危険物保安監督者": [
        ("must_contain", "保安監督"),
        ("must_contain", "届出"),
        ("must_not_contain", "pH"),
    ],
    "保安距離": [
        ("must_contain", "保安距離"),
        ("must_contain", "周囲"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "保有空地": [
        ("must_contain", "保有空地"),
        ("must_contain", "空地"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "定期点検": [
        ("must_contain", "定期点検"),
        ("must_contain", "点検"),
        ("must_not_contain", "pH"),
    ],
    "完成検査前検査": [
        ("must_contain", "完成検査"),
        ("must_contain", "検査"),
        ("must_not_contain", "pH"),
    ],
    "製造所等": [
        ("must_contain", "製造所等"),
        ("must_contain", "貯蔵所"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "貯蔵所": [
        ("must_contain", "貯蔵"),
        ("must_contain", "取扱"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "取扱所": [
        ("must_contain", "取扱"),
        ("must_contain", "貯蔵"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "変更許可": [
        ("must_contain", "変更"),
        ("must_contain", "許可"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "屋内貯蔵所": [
        ("must_contain", "屋内"),
        ("must_contain", "貯蔵"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "屋外タンク貯蔵所": [
        ("must_contain", "屋外"),
        ("must_contain", "タンク"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "移動タンク貯蔵所": [
        ("must_contain", "移動"),
        ("must_contain", "貯蔵"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "給油取扱所": [
        ("must_contain", "給油"),
        ("must_contain", "取扱"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "一般取扱所": [
        ("must_contain", "一般"),
        ("must_contain", "取扱"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "販売取扱所": [
        ("must_contain", "販売"),
        ("must_contain", "取扱"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "移送取扱所": [
        ("must_contain", "移送"),
        ("must_contain", "取扱"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "製造所": [
        ("must_contain", "製造"),
        ("must_contain", "製造所"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "消火設備": [
        ("must_contain", "消火"),
        ("must_contain", "設備"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "警報設備": [
        ("must_contain", "警報"),
        ("must_contain", "設備"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "避難設備": [
        ("must_contain", "避難"),
        ("must_contain", "設備"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "標識": [
        ("must_contain", "標識"),
        ("must_contain", "火気"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "指定数量": [
        ("must_contain", "指定数量"),
        ("must_contain", "危険性"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "指定数量の倍数": [
        ("must_contain", "倍数"),
        ("must_contain", "指定数量"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "複数危険物を扱う場合の倍数合算": [
        ("must_contain", "倍数"),
        ("must_contain", "合算"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "第4類危険物の指定数量": [
        ("must_contain", "第4類"),
        ("must_contain", "指定数量"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "水溶性・非水溶性による指定数量差": [
        ("must_contain", "水溶性"),
        ("must_contain", "指定数量"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "指定数量の意味": [
        ("must_contain", "指定数量"),
        ("must_contain", "基準"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "品名・数量・指定数量倍数の変更届出": [
        ("must_contain", "届出"),
        ("must_contain", "数量"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "指定数量未満": [
        ("must_contain", "指定数量"),
        ("must_contain", "未満"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "指定数量の倍数計算": [
        ("must_contain", "倍数"),
        ("must_contain", "指定数量"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "指定数量未満の危険物の扱い": [
        ("must_contain", "指定数量"),
        ("must_contain", "未満"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "仮貯蔵": [
        ("must_contain", "仮"),
        ("must_contain", "貯蔵"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "仮取扱い": [
        ("must_contain", "仮"),
        ("must_contain", "取扱"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "仮使用": [
        ("must_contain", "仮"),
        ("must_contain", "使用"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "仮貯蔵・仮取扱い": [
        ("must_contain", "仮"),
        ("must_contain", "承認"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "保安検査": [
        ("must_contain", "保安"),
        ("must_contain", "検査"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "保安講習": [
        ("must_contain", "保安"),
        ("must_contain", "講習"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "使用停止": [
        ("must_contain", "使用停止"),
        ("must_contain", "行政"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "行政措置": [
        ("must_contain", "行政"),
        ("must_contain", "措置"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "事故時対応": [
        ("must_contain", "事故"),
        ("must_contain", "通報"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "指定数量倍数の変更届出": [
        ("must_contain", "届出"),
        ("must_contain", "倍数"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "倍数計算": [
        ("must_contain", "倍数"),
        ("must_contain", "指定数量"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "非水溶性による指定数量差": [
        ("must_contain", "非水溶性"),
        ("must_contain", "指定数量"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "保安講習の対象": [
        ("must_contain", "保安講習"),
        ("must_contain", "対象"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "位置の基準": [
        ("must_contain", "位置"),
        ("must_contain", "保安"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "タンク貯蔵所": [
        ("must_contain", "タンク"),
        ("must_contain", "貯蔵"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "危険物保安監督者選任・解任届出": [
        ("must_contain", "保安監督者"),
        ("must_contain", "届出"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "保安検査の対象": [
        ("must_contain", "保安検査"),
        ("must_contain", "施設"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
    "仮使用の承認": [
        ("must_contain", "仮"),
        ("must_contain", "承認"),
        ("must_not_contain", "免状"),
        ("must_not_contain", "pH"),
    ],
}

PF_REF_RE = re.compile(
    r"PF-\d{3}|TF-PF-\d{3}|PC-\d{3}|TF-PC-\d{3}|L-\d{3}|TF-L-\d{3}|第\d+問"
)


def _row_for_term(term: str) -> dict[str, str] | None:
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if norm(row.get("term")) == term:
                return row
    return None


def _combined(row: dict[str, str]) -> str:
    cols = (
        "short_def",
        "definition",
        "article_lead",
        "term_detail_body",
        "exam_points",
        "explanation",
        "example_question",
        "example_answer",
        "faq_1_answer",
        "faq_2_answer",
        "faq_3_answer",
        "faq_4_answer",
    )
    return "\n".join(norm(row.get(c)) for c in cols)


def validate_sources(term: str, row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    text = _combined(row)
    core = norm(row.get("short_def")) + "\n" + norm(row.get("definition"))
    brief = build_brief(term)

    for kind, phrase in CLASSIFICATION_ASSERTIONS.get(term, []):
        if kind == "must_contain" and phrase not in text:
            errors.append(f"source_assertion_missing:{phrase}")
        if kind == "must_not_contain" and phrase in core:
            errors.append(f"source_assertion_forbidden_in_def:{phrase}")

    if brief["practice_count"] > 0 and not PF_REF_RE.search(text):
        errors.append("source_missing_practice_id")

    if brief["example_candidates"] and norm(row.get("example_question")):
        ex_q = norm(row.get("example_question"))
        if "正しいか、誤りか" not in ex_q and "正しい。" not in ex_q and "誤り" not in ex_q:
            errors.append("source_example_not_exam_format")

    related = [t.strip() for t in norm(row.get("related_terms")).split(";") if t.strip()]
    by_term = {
        norm(r.get("term")): r
        for r in csv.DictReader(CSV_PATH.open(encoding="utf-8-sig"))
    }
    for rel in related:
        rel_row = by_term.get(rel)
        if not rel_row:
            errors.append(f"source_related_missing:{rel}")
            continue
        tags = norm(rel_row.get("tags"))
        rel_ok = REWRITE_TAG in tags or verify_term(rel).ok
        if not rel_ok and rel != term:
            errors.append(f"source_related_not_rewritten:{rel}")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="用語書き直しのソース整合検証")
    ap.add_argument("--term", action="append", required=True)
    args = ap.parse_args()

    failed = 0
    for term in args.term:
        row = _row_for_term(term)
        print(f"=== {term} ===")
        if not row:
            print("  ERROR: csv_term_not_found")
            failed += 1
            continue

        source_errors = validate_sources(term, row)
        verify = verify_term(term)

        for err in source_errors:
            print(f"  ERROR: {err}")
        for err in verify.errors:
            print(f"  ERROR: {err}")
        for warn in verify.warnings:
            print(f"  WARN:  {warn}")

        if not source_errors and verify.ok:
            print("  OK")
        else:
            failed += 1
        print()

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
