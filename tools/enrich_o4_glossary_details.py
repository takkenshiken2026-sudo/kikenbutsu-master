#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
実践演習・一問一答DBの解説を集約し、glossary_terms.csv の用語詳細記事列を充実させる。

  python3 tools/enrich_o4_glossary_details.py
  python3 tools/enrich_o4_glossary_details.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.site_config import brand_name, exam_name  # noqa: E402

CSV_PATH = ROOT / "data" / "glossary_terms.csv"
PRACTICE = ROOT / "data" / "imported" / "o4_practice_500_source.csv"
ICHIMON = ROOT / "data" / "imported" / "o4_ichimon_500_source.csv"

EXAM = exam_name()
BRAND = brand_name()

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

# 学習メタ用語（詳細記事の自動生成対象外・ガイド的な短い説明のみ）
META_STUDY_TERMS = frozenset({"ひっかけ対策", "よくある混同論点"})

META_PEER_TERMS = KEEP_TERMS | META_STUDY_TERMS | frozenset({"ひっかけ問題"})

# 用語名と問題DBの topic/unit/本文キーワードの対応
TERM_SEARCH_ALIASES: dict[str, list[str]] = {
    "バックドラフト": ["バックドラフト", "密閉空間", "爆燃"],
    "フラッシュオーバー": ["フラッシュオーバー", "全焼", "急激"],
    "丙種危険物取扱者": ["丙種危険物取扱者", "丙種"],
    "乙種危険物取扱者": ["乙種危険物取扱者", "乙種"],
    "乙種第4類": ["乙種第4類", "乙4", "第4類"],
    "危険物の規制に関する政令": ["危険物の規制に関する政令", "政令", "別表第三"],
    "引火性液体": ["引火性液体", "第4類危険物"],
    "引火性蒸気": ["引火性蒸気", "可燃性蒸気", "蒸気"],
    "消防法別表第二": ["別表第二", "品名", "性状"],
    "消防法施行令": ["消防法施行令", "施行令"],
    "消防署長": ["消防署長"],
    "消防長": ["消防長"],
    "漏えい対策": ["漏えい", "漏洩", "流出"],
    "漏えい防止堤": ["漏えい防止堤", "防止堤"],
    "移動式貯蔵タンク": ["移動タンク貯蔵所", "移動タンク", "タンクローリー"],
    "移動タンク貯蔵所": ["移動タンク貯蔵所", "移動タンク", "タンクローリー"],
    "第2類危険物": ["第2類危険物", "第2類", "酸化性固体"],
    "第3類危険物": ["第3類危険物", "第3類", "自然発火", "禁水性"],
    "第5類危険物": ["第5類危険物", "第5類", "自己反応"],
    "指定数量の倍数": ["指定数量倍数", "倍数", "指定数量"],
    "泡消火": ["泡消火", "泡消火剤", "泡沫"],
    "粉末消火": ["粉末消火", "粉末消火剤"],
    "屋内貯蔵所": ["屋内貯蔵所"],
    "給油取扱所": ["給油取扱所", "ガソリンスタンド"],
    "沸点": ["沸点", "沸騰", "外圧"],
    "注水消火": ["注水", "注水消火", "非水溶性"],
    "水上泡消火": ["水上泡", "泡消火", "泡沫"],
    "密閉空間火災": ["密閉空間", "閉鎖空間", "バックドラフト"],
    "接地": ["接地", "静電気", "アース"],
    "標識": ["標識", "表示板", "危険物の表示"],
    "表示": ["表示", "表示板", "危険物の表示"],
    "消防法別表第二": ["別表第二", "品名", "性状"],
    "消防法施行令": ["施行令", "技術上の基準"],
    "消防署長": ["消防署長", "市町村"],
    "消防長": ["消防長"],
    "漏えい防止堤": ["防止堤", "漏えい防止"],
}

# 問題DBに紐づかない核心語の手書き詳細（乙4向け）
CURATED_ARTICLES: dict[str, dict[str, str]] = {
    "移送": {
        "definition": "まず「移送」は、貯蔵所等から配管・ポンプ等により危険物を他の設備や場所へ移すことをいう。",
        "term_detail_body": "移動タンク貯蔵所による移送や移送取扱所など、設備の種類ごとに基準が異なります。漏えい・火気・静電気対策が試験の定番です。",
        "exam_points": "配管・ポンプ等による危険物の移動;移動タンク貯蔵所・移送取扱所との区別;漏えい・火気・静電気の注意",
        "common_mistakes": "運搬と混同する;移送取扱所と移動タンク貯蔵所を同一視する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "指定数量": {
        "definition": "まず「指定数量」は、危険物の危険性に応じて政令で定められる基準数量であり、品名・性状ごとに異なる。",
        "term_detail_body": "指定数量は、製造・貯蔵・取扱いの規制区分を決めるための基準値です。ガソリン（第1石油類・非水溶性200 L）やアセトン（水溶性400 L）のように、同じ類でも性状で数量が変わります。\n\n指定数量の倍数は、貯蔵量÷指定数量を品名ごとに求めて合算します。単純にリットル数を足し合わせるのではなく、倍数計算が試験の定番です。",
        "exam_points": "品名・性状ごとに数量が異なる;倍数は貯蔵量÷指定数量の合算;第1石油類は水溶性・非水溶性で数量が違う",
        "common_mistakes": "数量を単純合計する;指定数量と倍数の計算を混同する;水溶性・非水溶性の区分を誤る",
        "legal_basis": "危険物の規制に関する政令",
    },
    "運搬": {
        "definition": "まず「運搬」は、危険物を事業所外へ車両等で運び送ることをいう。",
        "term_detail_body": "運搬では表示・混載制限・容器・積載方法などの基準が問われます。移送（設備間の移動）や譲渡・引渡しとの違いを整理してください。",
        "exam_points": "車両等による事業所外の運搬;表示・混載・容器・積載の基準;移送・譲渡との区別",
        "common_mistakes": "移送と混同する;表示と標識を同一視する",
        "legal_basis": "危険物の規制に関する政令",
    },
    "バックドラフト": {
        "definition": "まず「バックドラフト」は、密閉空間で発生した火災に大量の酸素が一気に供給されたとき、可燃性ガスが急激に燃焼・爆発的に燃え上がる現象をいう。",
        "term_detail_body": "バックドラフトは室内火災の急激な延焼現象です。閉鎖空間では燃焼が不完全になり可燃性ガスが蓄積し、開口部から酸素が流入すると一気に燃焼が進む。\n\n消火活動では、開放前の内部状況確認、換気の段階的実施、自衛消防組織との連携が重要です。",
        "exam_points": "密閉空間＋酸素流入で急燃;開放前の内部確認;換気は段階的に行う",
        "common_mistakes": "通常の延焼と混同する;開口部を一気に全開にする;内部状況未確認で進入する",
        "legal_basis": "消防法",
    },
    "フラッシュオーバー": {
        "definition": "まず「フラッシュオーバー」は、閉鎖空間火災で天井付近の高温ガス層が一気に下方へ伝播し、室内全体が一瞬で燃焼に至る現象をいう。",
        "term_detail_body": "フラッシュオーバーは、火災の成長過程で発生しうる危険な現象です。輻射熱により可燃物表面が一斉に着火し、避難・消火活動の時間的余裕が大きく減ります。\n\n試験ではバックドラフトとの違い（酸素流入型か、輻射熱による一斉着火か）が問われやすいです。",
        "exam_points": "天井付近の高温ガス層が下方へ伝播;室内一斉着火;バックドラフトと区別する",
        "common_mistakes": "バックドラフトと同一視する;単なる延焼とみなす",
        "legal_basis": "消防法",
    },
    "丙種危険物取扱者": {
        "definition": "まず「丙種危険物取扱者」は、丙種の危険物を取り扱う資格者で、乙種・甲種とは対象となる危険物の範囲と試験内容が異なる。",
        "term_detail_body": "乙種第4類の学習では、甲種・乙種・丙種の違いを混同しないことが重要です。丙種は比較的範囲が限定された危険物取扱資格として位置づけられます。",
        "exam_points": "乙種・丙種・甲種の対象範囲の違い;免状の種類と取扱可能な危険物;試験の受験資格の違い",
        "common_mistakes": "乙種第4類と丙種の出題範囲を同一視する;全類を扱えると誤解する",
        "legal_basis": "消防法",
    },
    "消防法別表第二": {
        "definition": "まず「消防法別表第二」は、危険物の品名と性状を定める表で、別表第一と組み合わせて危険物かどうかを判断する。",
        "term_detail_body": "別表第一の品名に該当し、かつ別表第二の区分に応じた性状を有する物品が危険物となります。試験では品名と性状の対応を問う設問が出ます。",
        "exam_points": "別表第一の品名＋別表第二の性状;危険物該当性の二段階判断",
        "common_mistakes": "別表第一だけで危険物と決めつける;性状区分を品名と混同する",
        "legal_basis": "消防法",
    },
    "消防法施行令": {
        "definition": "まず「消防法施行令」は、消防法の委任に基づき、製造所等の構造設備や技術上の基準などを定める命令である。",
        "term_detail_body": "危険物の規制に関する政令とあわせて、施設基準・保安距離・貯蔵方法などの具体基準を確認する場面で登場します。",
        "exam_points": "消防法・政令・施行令の役割分担;施設の構造設備基準",
        "common_mistakes": "政令と施行令の内容を取り違える;消防法本則と施行令を混同する",
        "legal_basis": "消防法;消防法施行令",
    },
    "消防長": {
        "definition": "まず「消防長」は、消防本部を置く市町村の消防委員会が選任する消防職員で、消防法上の権限・職務の主体の一つである。",
        "term_detail_body": "消防署長（消防署を置く市町村）との違い、命令権・監督権の主体としての整理が試験で問われます。",
        "exam_points": "消防長と消防署長の設置主体の違い;消防組織と権限の主体",
        "common_mistakes": "消防署長と同一とみなす;都道府県知事の権限と混同する",
        "legal_basis": "消防法",
    },
}

# --add-terms で追記する用語（問題DB・既存CSVにない短語）
EXTRA_TERMS: list[tuple[str, str]] = [
    ("沸点", "物性・化学"),
    ("質量パーセント濃度", "物性・化学"),
    ("注水消火", "火災・消火・漏えい"),
    ("水上泡消火", "火災・消火・漏えい"),
    ("密閉空間火災", "火災・消火・漏えい"),
    ("タンクローリー", "法令・制度"),
    ("酢酸エチル", "火災・消火・漏えい"),
    ("アセトアルデヒド", "火災・消火・漏えい"),
    ("第4石油類", "火災・消火・漏えい"),
    ("譲渡・引渡し", "法令・制度"),
]

BLOB_FIELDS = (
    "question",
    "statement",
    "explanation",
    "unit",
    "topic",
    "exam_point",
    "trap_point",
    "source_note",
)

GENERIC_PHRASES = (
    "危険物取扱者試験の出題範囲において重要な概念",
    "選択肢の言い換えや数字のひっかけ",
    "実践演習で誤答した選択肢",
    "公式の定義・試験テキスト",
    "関連用語へ進んでください",
    "繰り返し登場します",
    "混同を防げます",
)


def norm(s: str | None) -> str:
    return (s or "").strip()


def norm_term(s: str | None) -> str:
    return re.sub(r"\s+", "", norm(s))


def split_sentences(text: str, limit: int = 6) -> list[str]:
    text = re.sub(r"\s+", " ", norm(text))
    if not text:
        return []
    parts = [p.strip() for p in re.findall(r"[^。！？]+[。！？]?", text) if p.strip()]
    return parts[:limit]


def is_generic_sentence(s: str) -> bool:
    if len(s) < 18:
        return True
    return any(p in s for p in GENERIC_PHRASES)


def trim_lead_sentence(term: str, sentence: str) -> str:
    s = norm(sentence)
    m = re.search(rf"まず「{re.escape(term)}」は、(.+)", s)
    if m:
        return m.group(1).strip().rstrip("。")
    for prefix in (f"{term}は、", f"{term}とは、", f"{term}は", f"{term}とは"):
        if s.startswith(prefix):
            return s[len(prefix) :].lstrip().rstrip("。")
    return s.rstrip("。")


_EXAM_STEM_MARKERS = (
    "は正しい",
    "は誤",
    "どれか",
    "次の記述",
    "次のうち",
    "正解は選択肢",
    "正しい説明は",
)


def is_exam_stem(sentence: str) -> bool:
    s = norm(sentence)
    if not s:
        return True
    if s.startswith(("誤り", "正しい", "×", "○", "実践演習", "正解は")):
        return True
    return any(m in s for m in _EXAM_STEM_MARKERS)


def _definition_sentence_score(term: str, body: str) -> int:
    score = 0
    if body.startswith(term) or body.startswith(f"{term}は"):
        score += 14
    m = re.match(r"^([^、。]{1,40})は[、]", body)
    if m:
        subj = m.group(1).strip()
        if subj == term or subj.endswith(term):
            score += 10
        elif term in subj and len(subj) > len(term) + 1:
            score -= 12
        elif term in subj:
            score += 4
        else:
            score -= 9
    elif term in body[: min(len(body), 50)]:
        score += 2
    else:
        score -= 5
    return score


def pick_definition_sentence(
    term: str,
    explanations: list[str],
    exam_points: list[str],
) -> str:
    """一覧・リード用に、定義らしい一文を選ぶ（用語名が主語の文を優先）。"""
    best: tuple[int, str] | None = None
    for expl in explanations:
        for sent in split_sentences(expl, 12):
            body = trim_lead_sentence(term, sent)
            if len(body) < 22 or is_exam_stem(body) or is_generic_sentence(body):
                continue
            sc = _definition_sentence_score(term, body)
            if term not in body[:70] and not body.startswith(term):
                sc -= 15
            if best is None or sc > best[0]:
                best = (sc, body)
    if best and best[0] >= 0:
        return best[1]

    for ep in exam_points:
        ep = norm(ep)
        if len(ep) >= 18 and not is_generic_sentence(ep) and not is_exam_stem(ep):
            sc = _definition_sentence_score(term, ep)
            if sc >= 0:
                return ep
    if explanations:
        fallback = trim_lead_sentence(term, explanations[0])
        if len(fallback) >= 18 and not is_exam_stem(fallback):
            return fallback
    return ""


def build_short_def(term: str, lead: str, category: str) -> str:
    if lead:
        line = lead if lead.startswith(term) else f"{term}は、{lead.rstrip('。')}。"
        return line if line.endswith("。") else f"{line}。"
    return (
        f"{term}は、{EXAM}の{category}分野で頻出の用語です。"
        "定義と数値・条件の違いを押さえます。"
    )[:200]


def sentence_key(s: str) -> str:
    return re.sub(r"\s+", "", s)[:120]


def ends_sentence(s: str) -> str:
    t = norm(s)
    if not t:
        return ""
    return t if t.endswith("。") else f"{t}。"


def unique_sentences(sentences: list[str], *, limit: int = 5) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in sentences:
        s = norm(raw)
        if len(s) < 16 or is_generic_sentence(s) or is_exam_stem(s):
            continue
        key = sentence_key(s)
        if key in seen:
            continue
        if any(len(key) > 24 and (key in o or o in key) for o in seen):
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= limit:
            break
    return out


CATEGORY_STUDY_NOTES: dict[str, str] = {
    "法令・制度": (
        "乙種第4類の法令分野では、条文の言い換えと「誤っているものはどれか」の問いが多く、"
        "数値・義務の主体・手続の区別が試験の焦点になります。"
    ),
    "物性・化学": (
        "物性・化学分野では、性質の数値（沸点・引火点・濃度など）と危険物分類の対応が問われます。"
        "似た物質名は表で比較すると整理しやすくなります。"
    ),
    "火災・消火・漏えい": (
        "火災・消火分野では、第4類の性質・消火方法・漏えい対策の組み合わせが頻出です。"
        "水溶性・非水溶性の違いをセットで押さえてください。"
    ),
}


def build_term_detail_body(
    term: str,
    category: str,
    lead_sentence: str,
    explanations: list[str],
    exam_points: list[str],
    traps: list[str],
    unit: str,
    topic: str,
    q_count: int,
    peers: list[str],
    legal: str,
    practice_rows: list[dict[str, str]],
    *,
    skip_definition: bool = False,
) -> str:
    parts: list[str] = []

    def_sents: list[str] = []
    if lead_sentence:
        lead = lead_sentence.rstrip("。")
        if lead.startswith(f"{term}は"):
            def_sents.append(ends_sentence(lead))
        else:
            def_sents.append(ends_sentence(f"{term}は、{lead}"))
    for sent in unique_sentences(
        [trim_lead_sentence(term, e) for e in explanations if e],
        limit=4,
    ):
        if sentence_key(sent) == sentence_key(lead_sentence):
            continue
        if sent.startswith(f"{term}は"):
            def_sents.append(ends_sentence(sent.rstrip("。")))
        elif re.match(rf"^{re.escape(term)}", sent):
            def_sents.append(ends_sentence(sent.rstrip("。")))
        else:
            def_sents.append(ends_sentence(sent.rstrip("。")))
    if def_sents and not skip_definition:
        for sent in def_sents[:4]:
            parts.append(sent)

    cat_note = CATEGORY_STUDY_NOTES.get(category)
    if cat_note:
        parts.append(cat_note)
    elif unit:
        parts.append(
            f"単元「{unit}」では、{term}の定義に加え、条件の言い換えや数値のひっかけが問われます。"
        )

    if q_count or practice_rows:
        ctx: list[str] = []
        if unit or topic:
            label = unit or topic
            sub = f"（{topic}）" if topic and topic != unit else ""
            ctx.append(f"出題文脈は主に「{label}」{sub}で、{term}がキーワードとして繰り返し登場します。")
        if q_count >= 2:
            ctx.append(
                f"{BRAND}では実践演習・一問一答に合わせた復習問題を{q_count}問前後掲載しています。"
            )
        qtypes = unique_lines(
            [norm(r.get("question_type")) for r in practice_rows if norm(r.get("question_type"))],
            limit=2,
        )
        if qtypes:
            ctx.append(f"想定される出題形式の例: {'・'.join(qtypes)}。")
        if ctx:
            parts.append(" ".join(ctx))

    if peers:
        parts.append(
            f"理解を深めるには、「{'」「'.join(peers[:3])}」との違いを並べて覚えると、"
            f"本番で{term}を含む選択肢を判別しやすくなります。"
        )

    if legal:
        basis = legal.replace(";", "・")
        parts.append(
            f"根拠法令は主に{basis}です。改正や数値の更新は、消防試験研究センターの公式テキストで確認してください。"
        )

    return "\n\n".join(p for p in parts if p)


def build_explanation_text(
    term: str,
    category: str,
    traps: list[str],
    exam_questions: list[str],
    ichimon_rows: list[dict[str, str]],
) -> str:
    parts: list[str] = []
    if category == "法令・制度":
        parts.append(
            f"法令分野の{term}は、正しい説明・誤っている説明の判別と、数値・主体・手続の区別が問われやすいです。"
        )
    elif category == "物性・化学":
        parts.append(
            f"{term}は物性・化学の文脈で、数値や性質の組み合わせ（引火点・沸点・濃度など）とセットで問われます。"
        )
    else:
        parts.append(
            f"{term}は火災・消火・漏えいの文脈で、性質と対策（消火方法・漏えい防止）の対応が問われやすいです。"
        )

    if traps:
        parts.append(f"誤答の典型は「{traps[0][:72]}{'…' if len(traps[0]) > 72 else ''}」のように、似た制度や数値と混同することです。")
    if exam_questions:
        preview = exam_questions[0][:88]
        parts.append(f"実践演習では「{preview}…」のように、一文で正誤を判断する設問もあります。")
    if ichimon_rows:
        parts.append("一問一答では○×形式で素早く定着を確認できます。")
    return " ".join(parts)


def build_article_lead(term: str, category: str, unit: str) -> str:
    if unit:
        return (
            f"{category}分野の「{unit}」でよく出る用語です。"
            f"下の目次から定義・試験ポイント・例題の順に確認し、演習と往復してください。"
        )
    return (
        f"{category}分野で押さえる用語です。"
        f"定義と試験ポイントを確認したら、関連用語と演習で定着を確認してください。"
    )


def build_memory_tip(term: str, peers: list[str]) -> str:
    tips: list[str] = []
    if peers:
        tips.append(f"「{peers[0]}」と違いを比較表にまとめる。")
    tips.append(
        f"演習で{term}を含む問題を解き、間違えたら"
        "試験ポイント→関連用語→定義の順に見直す。"
    )
    return " ".join(tips)[:300]


def filter_related_peers(
    term: str,
    category: str,
    by_cat: dict[str, list[str]],
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]],
) -> list[str]:
    """同分野の実義ある用語を関連リンクに選ぶ（メタ用語を除外）。"""
    scores: Counter[str] = Counter()
    for row in practice_rows + ichimon_rows:
        for field in ("topic", "unit"):
            val = norm(row.get(field))
            if not val or val == term or val in META_PEER_TERMS or len(val) > 28:
                continue
            if val != term:
                scores[val] += 3
            for part in re.split(r"[・／/]", val):
                p = norm(part)
                if len(p) >= 3 and p not in META_PEER_TERMS and p != term:
                    scores[p] += 1

    ranked = [t for t, _ in scores.most_common(20) if t not in META_PEER_TERMS]
    if len(ranked) < 2:
        ranked = [
            p
            for p in by_cat.get(category, [])
            if p != term and p not in META_PEER_TERMS and len(p) <= 24
        ]
    return ranked[:3]


META_STUDY_ARTICLES: dict[str, dict[str, str]] = {
    "ひっかけ対策": {
        "short_def": "試験の問い方（正しいもの／誤っているもの）や言い換え、数値の取り違えに注意する学習の視点。",
        "definition": "まず「ひっかけ対策」とは、選択肢の言い換えや「誤っているものはどれか」といった問い方の癖を把握し、定義と条文を照らして判別する学習の仕方を指す。",
        "term_detail_body": (
            "乙4では、正しい説明だけでなく「誤っているものはどれか」が頻出します。"
            "問い方を先に確認し、数字・主体・品名の取り違えを意識して解くことが重要です。\n\n"
            "具体例として、ガソリン（第1石油類）・灯油（第2石油類）・重油（第3石油類）の分類や、"
            "水溶性と非水溶性の違いは、同じような語句で混同されやすいテーマです。\n\n"
            "詳しい学習の進め方は試験ガイド「過去問の使い方」もあわせて確認してください。"
        ),
        "exam_points": "問い方（正しい／誤り）を先に確認;数値・主体・品名の取り違え;類似分類の比較",
        "common_mistakes": "誤り選択肢を正しいと決めつける;数量を単純合計する;水溶性＝安全とみなす",
        "related_terms": "ガソリン;灯油;第4類危険物",
        "explanation": "設問文の冒頭（正しい／誤っている）を線引きし、各選択肢を定義・数値と照合して判断します。",
        "article_lead": "試験特有の問い方と、数値・分類のひっかけに備える学習の視点を整理します。",
    },
    "よくある混同論点": {
        "short_def": "試験で混同されやすい分類・数値・制度を、対比して整理するための論点集。",
        "definition": "まず「よくある混同論点」とは、似た用語や数値の組み合わせを取り違えやすいテーマをまとめ、比較しながら覚えるための整理枠を指す。",
        "term_detail_body": (
            "法令・物性・火災の各分野で、「似ているが違う」組み合わせが繰り返し問われます。"
            "例として、危険物の類と品名、指定数量と倍数、消火方法と危険物の性質などです。\n\n"
            "1つの論点を押さえたら、関連する用語ページと実践演習でセット復習すると定着しやすくなります。"
        ),
        "exam_points": "類似語の対比;指定数量と倍数;消火方法と危険物分類",
        "common_mistakes": "名称だけで分類を判断する;単位や主体を読み飛ばす;例外規定を一般化する",
        "related_terms": "指定数量;第4類危険物;泡消火",
        "explanation": "比較表や一覧で「同じ点・違う点」だけを書き出し、選択肢ごとに当てはめて確認します。",
        "article_lead": "混同しやすいテーマを対比表で整理する考え方を説明します。",
    },
}


def apply_meta_study_term(row: dict[str, str]) -> None:
    term = norm(row.get("term"))
    curated = META_STUDY_ARTICLES.get(term, {})
    if curated:
        apply_curated(row, curated)
    tags = [t for t in parse_tags(norm(row.get("tags"))) if t != "詳細記事"]
    for drop in ("実践演習連動", "一問一答連動"):
        if drop in tags:
            tags.remove(drop)
    if "学習法" not in tags:
        tags.append("学習法")
    row["tags"] = ";".join(dict.fromkeys(tags))
    row["article_title"] = f"{term}とは？{EXAM}の学習で押さえる整理の仕方"
    row["memory_tip"] = (
        f"混同しやすいテーマは比較表にし、演習で間違えた論点だけを表に追記する。"
    )[:300]


def unique_lines(items: list[str], limit: int = 5) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        s = norm(raw)
        if not s or s in seen or is_generic_sentence(s):
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_question_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_term: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_ids: dict[str, set[str]] = defaultdict(set)

    def attach(term_key: str, row: dict[str, str]) -> None:
        rid = norm(row.get("id"))
        if rid and rid in seen_ids[term_key]:
            return
        if rid:
            seen_ids[term_key].add(rid)
        by_term[term_key].append(row)

    for row in rows:
        keys: set[str] = set()
        for field in ("topic", "unit"):
            t = norm_term(row.get(field))
            if len(t) >= 2:
                keys.add(t)
        topic = norm_term(row.get("topic"))
        for part in re.split(r"[・／/]", topic):
            p = norm_term(part)
            if len(p) >= 3:
                keys.add(p)
        for key in keys:
            attach(key, row)
    return by_term


def search_keys_for(term: str) -> list[str]:
    keys = [norm_term(term)]
    keys.extend(norm_term(a) for a in TERM_SEARCH_ALIASES.get(term, []) if norm(a))
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        if len(k) >= 2 and k not in seen:
            seen.add(k)
            out.append(k)
    return sorted(out, key=len, reverse=True)


def row_blob(row: dict[str, str]) -> str:
    return norm_term("".join(row.get(f, "") for f in BLOB_FIELDS))


def row_score(term: str, key: str, row: dict[str, str]) -> int:
    score = 0
    nt = norm_term(term)
    nk = norm_term(key)
    for field in ("topic", "unit"):
        val = norm_term(row.get(field))
        if nt and nt in val:
            score += 12
        elif nk and nk in val:
            score += 8
    if nk and nk in row_blob(row):
        score += 2
    return score


def is_ichimon_row(row: dict[str, str]) -> bool:
    rid = norm(row.get("id"))
    return rid.startswith("TF-") or (norm(row.get("statement")) and not norm(row.get("question")))


def find_question_rows(
    term: str,
    exact_idx: dict[str, list[dict[str, str]]],
    all_rows: list[dict[str, str]],
    *,
    max_rows: int = 48,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    keys = search_keys_for(term)
    seen_ids: set[str] = set()
    scored: list[tuple[int, dict[str, str]]] = []

    def add_row(row: dict[str, str], base: int) -> None:
        rid = norm(row.get("id"))
        if rid and rid in seen_ids:
            return
        if rid:
            seen_ids.add(rid)
        best = max((row_score(term, k, row) for k in keys), default=0)
        scored.append((base + best, row))

    for key in keys:
        for row in exact_idx.get(key, []):
            add_row(row, 20)

    if len(scored) < 4:
        for row in all_rows:
            blob = row_blob(row)
            for key in keys:
                nk = norm_term(key)
                if len(nk) >= 2 and nk in blob:
                    add_row(row, 5)
                    break

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [row for _, row in scored[:max_rows]]
    practice = [r for r in picked if not is_ichimon_row(r)]
    ichimon = [r for r in picked if is_ichimon_row(r)]
    return practice, ichimon


def most_common_unit(rows: list[dict[str, str]]) -> str:
    units = [norm(r.get("unit")) for r in rows if norm(r.get("unit"))]
    if not units:
        return ""
    return Counter(units).most_common(1)[0][0]


def extract_legal_basis(rows: list[dict[str, str]]) -> str:
    found: list[str] = []
    for row in rows:
        note = norm(row.get("source_note"))
        if not note:
            continue
        for label in ("消防法", "危険物の規制に関する政令", "消防法施行令", "保安規程"):
            if label in note and label not in found:
                found.append(label)
    return ";".join(found[:4])


def pick_example(
    term: str, practice_rows: list[dict[str, str]], ichimon_rows: list[dict[str, str]]
) -> tuple[str, str]:
    if ichimon_rows:
        row = ichimon_rows[0]
        q = norm(row.get("statement"))
        if len(q) > 220:
            q = q[:217] + "…"
        ans = norm(row.get("answer_text")) or ("○" if norm(row.get("answer")).lower() == "true" else "×")
        expl = split_sentences(norm(row.get("explanation")), 1)
        detail = expl[0] if expl else ""
        return q, f"{ans}。{detail}" if detail else ans
    if practice_rows:
        row = practice_rows[0]
        q = norm(row.get("question"))
        if len(q) > 220:
            q = q[:217] + "…"
        ans_num = norm(row.get("answer"))
        labels = ("ア", "イ", "ウ", "エ", "オ")
        try:
            idx = int(ans_num) - 1
            label = labels[idx] if 0 <= idx < 5 else ans_num
        except ValueError:
            label = ans_num
        expl = split_sentences(norm(row.get("explanation")), 1)
        detail = expl[0] if expl else ""
        return q, f"正解は選択肢{label}。{detail}" if detail else f"正解は選択肢{label}。"
    return (
        f"{term}について正しい説明はどれか。",
        "公式の定義・試験テキストの説明と一致する選択肢を選ぶ。",
    )


def apply_curated(row: dict[str, str], curated: dict[str, str]) -> None:
    for key, value in curated.items():
        if norm(value):
            row[key] = value


def enrich_row(
    row: dict[str, str],
    practice_rows: list[dict[str, str]],
    ichimon_rows: list[dict[str, str]],
    by_cat: dict[str, list[str]],
    *,
    curated: dict[str, str] | None = None,
) -> bool:
    term = norm(row.get("term"))
    category = norm(row.get("category"))
    if curated:
        apply_curated(row, curated)
    if not practice_rows and not ichimon_rows:
        return bool(curated)

    all_rows = (practice_rows + ichimon_rows) or []
    unit = most_common_unit(all_rows)
    topic = norm(all_rows[0].get("topic")) if all_rows else ""

    explanations = unique_lines(
        [norm(r.get("explanation")) for r in practice_rows + ichimon_rows],
        limit=5,
    )
    if not explanations and curated:
        explanations = unique_lines(
            [curated.get("definition", ""), curated.get("term_detail_body", "")],
            limit=3,
        )
    exam_points = unique_lines(
        [norm(r.get("exam_point")) for r in practice_rows + ichimon_rows],
        limit=8,
    )
    if not exam_points and curated:
        exam_points = [p.strip() for p in curated.get("exam_points", "").split(";") if p.strip()]
    traps = unique_lines(
        [norm(r.get("trap_point")) for r in practice_rows + ichimon_rows],
        limit=5,
    )
    if not traps and curated:
        traps = split_sentences(curated.get("common_mistakes", ""), 3)

    lead_sentence = ""
    if curated and norm(curated.get("definition")):
        curated_def = split_sentences(curated.get("definition", ""), 1)
        if curated_def:
            lead_sentence = trim_lead_sentence(term, curated_def[0])
    if not lead_sentence:
        lead_sentence = pick_definition_sentence(term, explanations, exam_points)
    if not lead_sentence:
        lead_sentence = trim_lead_sentence(term, norm(row.get("short_def")))

    if lead_sentence and _definition_sentence_score(term, lead_sentence) < 8:
        best_alt: tuple[int, str] | None = None
        for alt in unique_sentences(
            [trim_lead_sentence(term, e) for e in explanations if e],
            limit=8,
        ):
            sc = _definition_sentence_score(term, alt)
            if term not in alt[:70] and not alt.startswith(term):
                sc -= 15
            if best_alt is None or sc > best_alt[0]:
                best_alt = (sc, alt)
        if best_alt and best_alt[0] >= 8:
            lead_sentence = best_alt[1]

    short_def = build_short_def(term, lead_sentence, category)

    if lead_sentence:
        definition = f"まず「{term}」は、{lead_sentence.rstrip('。')}。"
    else:
        definition = norm(row.get("definition"))
    if len(explanations) > 1:
        second = trim_lead_sentence(term, explanations[1])
        if second and second != lead_sentence:
            definition += f" {second}" + ("" if second.endswith("。") else "。")
    if unit:
        definition += f" {category}では「{unit}」の文脈で繰り返し問われます。"

    q_count = len(practice_rows) + len(ichimon_rows)
    ex_q, ex_a = pick_example(term, practice_rows, ichimon_rows)
    legal = extract_legal_basis(all_rows) or norm(row.get("legal_basis"))
    peers = filter_related_peers(term, category, by_cat, practice_rows, ichimon_rows)

    if curated and norm(curated.get("term_detail_body")):
        term_detail_body = norm(curated["term_detail_body"])
        supplement = build_term_detail_body(
            term,
            category,
            lead_sentence,
            explanations,
            exam_points,
            traps,
            unit,
            topic,
            q_count,
            peers,
            legal,
            practice_rows,
            skip_definition=True,
        )
        for para in supplement.split("\n\n"):
            p = norm(para)
            if p and p not in term_detail_body:
                term_detail_body = f"{term_detail_body}\n\n{p}"
    else:
        term_detail_body = build_term_detail_body(
            term,
            category,
            lead_sentence,
            explanations,
            exam_points,
            traps,
            unit,
            topic,
            q_count,
            peers,
            legal,
            practice_rows,
        )

    exam_section = unique_lines(
        [norm(r.get("question")) for r in practice_rows[:3]],
        limit=2,
    )
    explanation = build_explanation_text(
        term, category, traps, exam_section, ichimon_rows
    )

    mistakes = (
        ";".join(traps[:5])
        if traps
        else norm(row.get("common_mistakes"))
    )
    memory = build_memory_tip(term, peers)

    tags = parse_tags(norm(row.get("tags")))
    if "詳細記事" not in tags:
        tags.append("詳細記事")
    if practice_rows:
        tags.append("実践演習連動")
    if ichimon_rows:
        tags.append("一問一答連動")

    row.update(
        {
            "short_def": short_def,
            "definition": definition,
            "explanation": explanation,
            "article_title": f"{term}とは？{EXAM}で押さえる意味・試験ポイント",
            "article_lead": build_article_lead(term, category, unit),
            "term_detail_body": term_detail_body,
            "exam_points": ";".join(exam_points) if exam_points else norm(row.get("exam_points")),
            "common_mistakes": mistakes,
            "memory_tip": memory[:300],
            "example_question": ex_q,
            "example_answer": ex_a,
            "legal_basis": legal,
            "faq_1_question": f"{term}の試験での意味は？",
            "faq_1_answer": (
                short_def
                if short_def
                else (explanations[0] if explanations else norm(row.get("faq_1_answer")))
            ),
            "faq_2_question": f"{term}でよくある誤りは？",
            "faq_2_answer": (
                traps[0]
                if traps
                else (
                    f"{category}分野では似た用語や数値と混同しやすいです。"
                    "演習で誤った選択肢をメモし、関連用語と対比して復習してください。"
                )
            ),
            "tags": ";".join(dict.fromkeys(tags)),
        }
    )
    if peers:
        row["related_terms"] = ";".join(peers)
    return True


def parse_tags(raw: str) -> list[str]:
    return [t.strip() for t in re.split(r"[;,、]", raw) if t.strip()]


def append_extra_terms(rows: list[dict[str, str]], fieldnames: list[str]) -> int:
    from tools.populate_o4_glossary_terms import build_row  # noqa: E402

    existing = {norm(r.get("term")) for r in rows}
    added = 0
    for term, category in EXTRA_TERMS:
        if term in existing:
            continue
        row = build_row(term, category)
        for col in fieldnames:
            row.setdefault(col, "")
        rows.append(row)
        existing.add(term)
        added += 1
    return added


def main() -> int:
    ap = argparse.ArgumentParser(description="乙4用語詳細記事の本文を問題DBから充実")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--add-terms",
        action="store_true",
        help="頻出の短語用語を glossary_terms.csv に追記してから充実する",
    )
    args = ap.parse_args()

    if not CSV_PATH.is_file():
        print(f"入力がありません: {CSV_PATH}", file=sys.stderr)
        return 1

    practice_rows_src = load_csv_rows(PRACTICE)
    ichimon_rows_src = load_csv_rows(ICHIMON)
    all_q_rows = practice_rows_src + ichimon_rows_src
    exact_idx = build_question_index(all_q_rows)

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    added_terms = 0
    if args.add_terms and not args.dry_run:
        added_terms = append_extra_terms(rows, fieldnames)
        if added_terms:
            print(f"新規用語を {added_terms} 件追加しました")
    elif args.add_terms and args.dry_run:
        existing = {norm(r.get("term")) for r in rows}
        added_terms = sum(1 for t, _ in EXTRA_TERMS if t not in existing)
        if added_terms:
            print(f"（dry-run）新規用語を {added_terms} 件追加予定")

    by_cat: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        t = norm(row.get("term"))
        if t:
            by_cat[norm(row.get("category"))].append(t)

    enriched = 0
    skipped_keep = 0
    meta_study = 0
    curated_only = 0
    no_source = 0

    for row in rows:
        term = norm(row.get("term"))
        if not term:
            continue
        if term in KEEP_TERMS:
            skipped_keep += 1
            continue
        if term in META_STUDY_TERMS:
            apply_meta_study_term(row)
            meta_study += 1
            continue

        practice_rows, ichimon_rows = find_question_rows(term, exact_idx, all_q_rows)
        curated = CURATED_ARTICLES.get(term)
        if not practice_rows and not ichimon_rows and not curated:
            no_source += 1
            continue

        if enrich_row(row, practice_rows, ichimon_rows, by_cat, curated=curated):
            enriched += 1
            if curated and not practice_rows and not ichimon_rows:
                curated_only += 1

    print(
        f"用語 {len(rows)} 件 — 詳細充実 {enriched} 件"
        f"（手書きテンプレ {curated_only} 件）、学習メタ {meta_study} 件、"
        f"手書き維持 {skipped_keep} 件、未対応 {no_source} 件"
    )

    if args.dry_run:
        return 0

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {CSV_PATH}")
    print("Next: python3 tools/build_all.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
