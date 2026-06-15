#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""消防試験研究センター試験情報検索の支部コード（shibu_cd）定義。"""

from __future__ import annotations

OFFICIAL_SCHEDULE_BASE = (
    "https://shinsei.shoubo-shiken.or.jp/shoubou_ia/iajs9001.do"
)
MENJO_KBN_KIKENBUTSU = "1"


def official_schedule_url(shibu_cd: str) -> str:
    return f"{OFFICIAL_SCHEDULE_BASE}?shibu_cd={shibu_cd}&menjo_kbn={MENJO_KBN_KIKENBUTSU}"


# (shibu_cd, 都道府県名, 地方ブロック)
SHIBU_REGIONS: list[tuple[str, str, str]] = [
    ("01", "北海道", "北海道・東北"),
    ("02", "青森県", "北海道・東北"),
    ("03", "岩手県", "北海道・東北"),
    ("04", "宮城県", "北海道・東北"),
    ("05", "秋田県", "北海道・東北"),
    ("06", "山形県", "北海道・東北"),
    ("07", "福島県", "北海道・東北"),
    ("08", "茨城県", "関東"),
    ("09", "栃木県", "関東"),
    ("10", "群馬県", "関東"),
    ("11", "埼玉県", "関東"),
    ("12", "千葉県", "関東"),
    ("13", "東京都", "関東"),
    ("14", "神奈川県", "関東"),
    ("15", "新潟県", "甲信越・北陸"),
    ("16", "富山県", "甲信越・北陸"),
    ("17", "石川県", "甲信越・北陸"),
    ("18", "福井県", "甲信越・北陸"),
    ("19", "山梨県", "甲信越・北陸"),
    ("20", "長野県", "甲信越・北陸"),
    ("21", "岐阜県", "東海"),
    ("22", "静岡県", "東海"),
    ("23", "愛知県", "東海"),
    ("24", "三重県", "東海"),
    ("25", "滋賀県", "近畿"),
    ("26", "京都府", "近畿"),
    ("27", "大阪府", "近畿"),
    ("28", "兵庫県", "近畿"),
    ("29", "奈良県", "近畿"),
    ("30", "和歌山県", "近畿"),
    ("31", "鳥取県", "中国"),
    ("32", "島根県", "中国"),
    ("33", "岡山県", "中国"),
    ("34", "広島県", "中国"),
    ("35", "山口県", "中国"),
    ("36", "徳島県", "四国"),
    ("37", "香川県", "四国"),
    ("38", "愛媛県", "四国"),
    ("39", "高知県", "四国"),
    ("40", "福岡県", "九州・沖縄"),
    ("41", "佐賀県", "九州・沖縄"),
    ("42", "長崎県", "九州・沖縄"),
    ("43", "熊本県", "九州・沖縄"),
    ("44", "大分県", "九州・沖縄"),
    ("45", "宮崎県", "九州・沖縄"),
    ("46", "鹿児島県", "九州・沖縄"),
    ("47", "沖縄県", "九州・沖縄"),
]


def region_blocks() -> list[tuple[str, list[tuple[str, str, str]]]]:
    order: list[str] = []
    groups: dict[str, list[tuple[str, str, str]]] = {}
    for code, name, block in SHIBU_REGIONS:
        if block not in groups:
            order.append(block)
            groups[block] = []
        groups[block].append((code, name, block))
    return [(block, groups[block]) for block in order]
