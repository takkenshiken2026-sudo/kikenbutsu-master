# -*- coding: utf-8 -*-
"""過去問・実践演習・一問一答の解説 HTML（正解の理由・他肢コメント）。"""

from __future__ import annotations

import html
import re

from tools.q_content_quality import (
    clean_ichimon_correct_body,
    dedupe_prose,
    ichimon_body_already_states_truth,
    strip_four_choice_leak,
)


def norm(value: object) -> str:
    return (value or "").strip() if value is not None else ""


_FW_DIGIT_TRANS = str.maketrans("０１２３４５６７８９", "0123456789")


def _parse_choice_num(raw: str) -> int | None:
    s = norm(raw).translate(_FW_DIGIT_TRANS)
    return int(s) if s.isdigit() else None


def correct_choice_indices(correct: object) -> set[int]:
    """page['correct'] から正答肢番号の集合（multi は 1,4 → {1,4}）。"""
    if correct is None:
        return set()
    if isinstance(correct, int):
        return {correct}
    raw = norm(correct)
    if not raw:
        return set()
    if raw.isdigit():
        return {int(raw)}
    if "," in raw and all(part.strip().isdigit() for part in raw.split(",") if part.strip()):
        return {int(part.strip()) for part in raw.split(",") if part.strip()}
    return set()


def _correct_choice_index(correct: object) -> int | None:
    """page['correct'] が int または multi の '1,3' 等のとき、先頭肢番号を返す。"""
    indices = correct_choice_indices(correct)
    return min(indices) if indices else None


def parse_numbered_choice_notes(text: str) -> dict[int, str]:
    """「１．…２．…」形式（運管過去問解説など）の肢別メモを抽出。"""
    out: dict[int, str] = {}
    if not text:
        return out
    section_re = (
        r"(?:^|(?<=[。．\n]))"
        r"(?:([０-９]+)[．.]|(\d{1,2})[．.](?![0-9]))\s*"
        r"(.+?)"
        r"(?=(?:^|(?<=[。．\n]))(?:[０-９]+[．.]|\d{1,2}[．.](?![0-9]))|$)"
    )
    for m in re.finditer(section_re, text, flags=re.DOTALL):
        num = _parse_choice_num(m.group(1) or m.group(2))
        note = norm(m.group(3))
        if num is not None and note:
            out[num] = note
    return out


_KANA_CHOICE_TO_NUM: dict[str, int] = {
    "ア": 1,
    "イ": 2,
    "ウ": 3,
    "エ": 4,
    "オ": 5,
}


def parse_kana_bracket_choice_notes(text: str) -> dict[int, str]:
    """O4 実践演習など: 【選択肢ア】誤り。… / 【選択肢1】… 形式の肢別解説。"""
    out: dict[int, str] = {}
    if not text:
        return out
    for m in re.finditer(r"【選択肢([アイウエオ])】([^【]+)", text):
        n = _KANA_CHOICE_TO_NUM.get(m.group(1))
        note = norm(m.group(2))
        if n and note:
            out[n] = note
    for m in re.finditer(r"【選択肢(\d)】([^【]+)", text):
        n = _parse_choice_num(m.group(1))
        note = norm(m.group(2))
        if n and note:
            out[n] = note
    return out


def parse_all_inline_choice_notes(text: str) -> dict[int, str]:
    """番号付き・括弧・カナ括弧の肢別解説を統合（同一肢は長い方を採用）。"""
    out: dict[int, str] = {}
    for parser in (
        parse_numbered_choice_notes,
        parse_inline_paren_choice_reasons,
        parse_kana_bracket_choice_notes,
    ):
        for n, note in parser(text).items():
            prev = out.get(n, "")
            if len(note) > len(prev):
                out[n] = note
    return out


_CORRECT_REASON_MIN_LEN = 50
_CORRECT_REASON_MAX_LEN = 220
_CHOICE_NOTE_MIN_LEN = 40
_CHOICE_NOTE_MAX_LEN = 220


def _o4_explanation_lead(exp: str) -> str:
    """【試験ポイント】【ひっかけ】【選択肢X】より前の解説本文。"""
    return norm(re.split(r"【(?:試験ポイント|ひっかけ|選択肢)", exp or "", maxsplit=1)[0])


def _strip_choice_verdict_prefix(note: str) -> str:
    return norm(re.sub(r"^(正しい|誤り|適切でない|適切|妥当)[。．、]\s*", "", note))


def _truncate_prose_at_sentence(text: str, max_len: int) -> str:
    t = dedupe_prose(text)
    if len(t) <= max_len:
        return t if not t or t.endswith("。") else t + "。"
    chunk = t[:max_len]
    m = re.search(r".+[。！？!?]", chunk)
    if m and len(m.group(0)) >= 60:
        return m.group(0)
    return chunk.rstrip("、。 ") + "…"


def _split_explanation_sentences(text: str) -> list[str]:
    out: list[str] = []
    t = norm(text)
    if not t:
        return out
    buf: list[str] = []
    quote_depth = 0
    for ch in t:
        buf.append(ch)
        if ch in "「『":
            quote_depth += 1
        elif ch in "」』" and quote_depth > 0:
            quote_depth -= 1
        elif ch in "。！？!?" and quote_depth == 0:
            sent = "".join(buf).strip()
            if len(sent) >= 8:
                out.append(sent if sent.endswith("。") else sent + "。")
            buf = []
    tail = "".join(buf).strip()
    if len(tail) >= 8:
        out.append(tail if tail.endswith("。") else tail + "。")
    return out


def _sentence_is_redundant(sent: str, existing: str) -> bool:
    sn = _normalize_for_compare(sent)
    ex = _normalize_for_compare(existing)
    if not sn or not ex:
        return False
    if len(sn) >= 12 and (sn in ex or ex in sn):
        return True
    if len(sn) >= 20 and len(ex) >= 20:
        shorter, longer = (sn, ex) if len(sn) <= len(ex) else (ex, sn)
        if shorter in longer:
            return True
    return _keyword_overlap_ratio(sent, existing) >= 0.72


def _append_unique_sentences(parts: list[str], text: str) -> None:
    joined = "".join(parts)
    for sent in _split_explanation_sentences(text):
        if _sentence_is_redundant(sent, joined):
            continue
        parts.append(sent)
        joined = "".join(parts)


def _o4_tagged_block(exp: str, tag: str) -> str:
    m = re.search(rf"【{re.escape(tag)}】([^【]+)", exp or "")
    return norm(m.group(1)) if m else ""


def _normalize_exam_formula_sentence(sent: str) -> str:
    s = sent.strip()
    if not s:
        return s
    core = s.rstrip("。")
    if "＝" in core and len(core) <= 24:
        left, _, right = core.partition("＝")
        left = left.strip()
        right = right.strip()
        if left and right:
            return f"{left}は{right}で表される。"
    return s if s.endswith("。") else s + "。"


def _expand_cor_note_to_sentence(cor_idx: int, opt_text: str, note: str) -> str:
    """正答肢メモを主語のある1文に整える。"""
    note = re.sub(r"^正しい[。．]\s*", "", _strip_choice_verdict_prefix(note))
    note = note.rstrip("。").strip()
    if not note:
        return ""
    opt_sn = _snippet(opt_text.rstrip("。．"), 40).rstrip("。．")
    if len(note) <= 22 or not re.search(r"[はがをに]", note):
        return f"選択肢（{cor_idx}）「{opt_sn}」は、{note}。"
    return note + "。" if not note.endswith("。") else note


def _append_if_fresh(body: str, sent: str, *, max_overlap: float = 0.72) -> str:
    if not sent:
        return body
    s = sent if sent.endswith("。") else sent + "。"
    if _sentence_is_redundant(s, body):
        return body
    if _keyword_overlap_ratio(s, body) >= max_overlap:
        return body
    return body + s


def _dedupe_body_sentences(body: str, *, strict: bool = True) -> str:
    """段落内の重複文を除去する。strict=False は他肢解説向け（短い補足文を残す）。"""
    kept: list[str] = []
    joined = ""
    for sent in _split_explanation_sentences(body):
        if kept and _keyword_overlap_ratio(sent, kept[-1]) >= 0.8:
            continue
        sn = _normalize_for_compare(sent)
        pn = _normalize_for_compare(kept[-1]) if kept else ""
        if kept and len(sn) >= 14 and len(pn) >= 14 and sn[:14] == pn[:14]:
            continue
        if strict:
            if (
                kept
                and len(sn) >= 8
                and len(pn) >= 8
                and sn[:8] == pn[:8]
                and _keyword_overlap_ratio(sent, kept[-1]) >= 0.55
            ):
                continue
            if kept and len(sn) >= 10 and len(pn) >= 10:
                prefix_len = 0
                for a, b in zip(sn, pn):
                    if a == b:
                        prefix_len += 1
                    else:
                        break
                if prefix_len >= 6 and _keyword_overlap_ratio(sent, kept[-1]) >= 0.35:
                    continue
            if kept and len(sn) <= 36:
                if any(_keyword_overlap_ratio(sent, k) >= 0.72 for k in kept):
                    continue
        if strict:
            if _sentence_is_redundant(sent, joined):
                continue
        elif _keyword_overlap_ratio(sent, joined) >= 0.88:
            continue
        kept.append(sent)
        joined += sent
    return joined


def _dedupe_wrong_note_sentences(body: str) -> str:
    """他肢解説向け。完全一致の文だけ除去（語句が一部重なる補足は残す）。"""
    kept: list[str] = []
    for sent in _split_explanation_sentences(body):
        sn = _normalize_for_compare(sent)
        if sn and any(sn == _normalize_for_compare(k) for k in kept):
            continue
        kept.append(sent)
    return "".join(kept)


def _pad_correct_reason_body(
    page: dict,
    row: dict,
    body: str,
    notes: dict[int, str],
    cor_idx: int | None,
) -> str:
    """正解の理由が短いとき、O4原文（試験ポイント・正答肢メモ等）のみで補う。"""
    if len(body) >= _CORRECT_REASON_MIN_LEN:
        return body

    exp = norm(row.get("explanation"))
    exam = _o4_tagged_block(exp, "試験ポイント")
    if exam:
        for sent in _split_explanation_sentences(exam):
            body = _append_if_fresh(
                body, _normalize_exam_formula_sentence(sent), max_overlap=0.95
            )
            if len(body) >= _CORRECT_REASON_MIN_LEN:
                return body

    if cor_idx:
        opts = page.get("opts") or []
        if 1 <= cor_idx <= len(opts):
            sent = _expand_cor_note_to_sentence(
                cor_idx, norm(opts[cor_idx - 1]), notes.get(cor_idx, "")
            )
            if sent and _keyword_overlap_ratio(sent, body) < 0.55:
                body = _append_if_fresh(body, sent, max_overlap=0.85)
            if len(body) >= _CORRECT_REASON_MIN_LEN:
                return body

    lead = _o4_explanation_lead(exp)
    for sent in _split_explanation_sentences(lead)[1:]:
        body = _append_if_fresh(body, sent)
        if len(body) >= _CORRECT_REASON_MIN_LEN:
            return body

    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    if "液体" in stem and "特徴" in stem and len(body) < _CORRECT_REASON_MIN_LEN:
        body = _append_if_fresh(
            body,
            "試験では三状態の性質比較として問われやすい。",
            max_overlap=0.5,
        )

    if "化学変化" in stem and len(body) < _CORRECT_REASON_MIN_LEN:
        body = _append_if_fresh(
            body,
            "試験では物理変化との区別として問われやすい。",
            max_overlap=0.5,
        )

    if "元素" in stem and "説明" in stem and len(body) < _CORRECT_REASON_MIN_LEN:
        body = _append_if_fresh(
            body,
            "単体・化合物・混合物の理解の前提となる概念である。",
            max_overlap=0.5,
        )

    if "第一石油類" in stem and "代表" in stem and len(body) < _CORRECT_REASON_MIN_LEN:
        body = _append_if_fresh(
            body,
            "組合せ問題では各類の代表例をセットで覚える。",
            max_overlap=0.95,
        )

    if "指定数量未満" in stem and len(body) < _CORRECT_REASON_MIN_LEN:
        body = _append_if_fresh(
            body,
            "条例等の規制対象となり得る点も押さえる。",
            max_overlap=0.95,
        )

    if "熱量" in stem and "単位" in stem and len(body) < _CORRECT_REASON_MIN_LEN:
        body = _append_if_fresh(
            body,
            "J（ジュール）やcal（カロリー）を押さえる。",
            max_overlap=0.5,
        )

    if ("液比重" in stem or ("水" in stem and "重さ" in stem and "比" in stem)) and len(body) < _CORRECT_REASON_MIN_LEN:
        body = _append_if_fresh(
            body,
            "比較の基準が水である点が液比重の特徴である。",
            max_overlap=0.95,
        )

    return body


def _stem_topic_for_bridge(stem: str) -> str:
    s = norm(stem).rstrip("。．.?？!！")
    m = re.match(r"^(.+?)について[、,]", s)
    if m:
        return m.group(1).strip()
    for pat in (
        r"について[、,]?正しいものはどれか\.?$",
        r"について[、,]?適切なものはどれか\.?$",
        r"について[、,]?[^。]+はどうなるか\.?$",
        r"として[、,]?正しいものはどれか\.?$",
        r"として[、,]?適切なものはどれか\.?$",
        r"は一般に何と呼ばれるか\.?$",
        r"はどれか\.?$",
        r"を選び(?:なさい)?\.?$",
    ):
        s = re.sub(pat, "", s)
    return s.rstrip("、，。．")


def _dedupe_after_intro(body: str, intro: str) -> str:
    if not intro or not body.startswith(intro):
        return body
    rest = body[len(intro) :]
    sents = _split_explanation_sentences(rest)
    if not sents:
        return body
    m = re.match(r"^正答は（\d+）「([^」]+)」です。", intro)
    opt_word = m.group(1).rstrip("。") if m else ""
    kept: list[str] = []
    for i, sent in enumerate(sents):
        if i == 0 and opt_word and len(opt_word) <= 16:
            if sent.startswith(f"{opt_word}は") or sent.startswith(f"{opt_word}が"):
                continue
        if i == 0 and _sentence_is_redundant(sent, intro):
            continue
        kept.append(sent)
    return intro + "".join(kept) if kept else body


def _format_wrong_choice_padding(page: dict, idx: int, note: str) -> str:
    """誤答肢の選択肢文＋解説メモから、自然な補足文を1文生成する。"""
    note = _strip_choice_verdict_prefix(note).rstrip("。")
    if not note:
        return ""
    opts = page.get("opts") or []
    opt = norm(opts[idx - 1]).rstrip("。") if 1 <= idx <= len(opts) else ""
    opt_sn = _snippet(opt, 40) if opt else ""

    note_out = note
    if re.search(r"(?:ではない|でない)$", note):
        note_out = re.sub(r"ではない$", "ではありません", note)
        note_out = re.sub(r"でない$", "ではありません", note_out)

    if opt_sn:
        opt_core = opt_sn.rstrip("。")
        note_core = note_out.rstrip("。")
        if note_core == opt_core or note_core.startswith(opt_core):
            return ""
        return f"（{idx}）は「{opt_sn}」とありますが、{note_out}。"
    return f"（{idx}）については、{note_out}。"


def _pick_wrong_choice_for_padding(
    notes: dict[int, str],
    cor_idx: int | None,
    page: dict | None = None,
) -> tuple[int, str] | None:
    """補完用に最も情報量のある誤答肢解説を1つ選ぶ。"""
    ranked: list[tuple[int, int, str]] = []
    for i, raw in notes.items():
        if cor_idx and i == cor_idx:
            continue
        note = _strip_choice_verdict_prefix(raw)
        if len(note) < 4:
            continue
        ranked.append((i, len(note), note))
    ranked.sort(key=lambda x: x[1], reverse=True)
    if ranked:
        return ranked[0][0], ranked[0][2]
    return None


def _expand_correct_reason_if_short(
    page: dict,
    row: dict,
    body: str,
    notes: dict[int, str],
    cor_idx: int | None,
) -> str:
    if len(body) >= _CORRECT_REASON_MIN_LEN:
        return body

    parts = _split_explanation_sentences(body)
    joined = body

    for extra in (
        norm(row.get("explanation_summary")),
        norm(row.get("explanation_correct")),
    ):
        if not extra:
            continue
        for block in re.split(r"\n\n+", extra):
            _append_unique_sentences(parts, _strip_choice_verdict_prefix(block))
        joined = "".join(parts)
        if len(joined) >= _CORRECT_REASON_MIN_LEN:
            return joined

    exam = _o4_tagged_block(norm(row.get("explanation")), "試験ポイント")
    if exam:
        for sent in _split_explanation_sentences(exam):
            expanded = _normalize_exam_formula_sentence(sent)
            if not _sentence_is_redundant(expanded, joined):
                parts.append(expanded)
                joined = "".join(parts)
        if len(joined) >= _CORRECT_REASON_MIN_LEN:
            return joined

    trap = _o4_tagged_block(norm(row.get("explanation")), "ひっかけ")
    if trap and not _sentence_is_redundant(trap, joined):
        parts.append(trap if trap.endswith("。") else trap + "。")
        joined = "".join(parts)

    return joined


def _strip_notes_overlapping_reference(text: str, reference: str) -> str:
    if not text or not reference:
        return text
    parts = _split_explanation_sentences(text)
    kept = [s for s in parts if not _sentence_is_redundant(s, reference)]
    return "".join(kept) if kept else text


def _wrong_stem_exam_bridge(stem: str, exam: str, core: str) -> str:
    """試験ポイントと誤答coreをstem文脈でつなぐ1文（O4原文ベース）。"""
    if not exam or not core:
        return ""
    exam = exam.rstrip("。")
    core = core.rstrip("。")
    core_subj = core.split("は")[0] if "は" in core else core

    if ("代表例" in stem or "代表的な" in stem) and exam:
        topic = ""
        if "特殊引火物" in stem:
            topic = "特殊引火物"
        elif "の代表例" in stem:
            topic = stem.split("の代表例")[0].split("として")[0]
        elif "として" in stem:
            topic = stem.split("として")[0].strip()
        exam_refs = exam
        m = re.search(r"代表例は(.+?)(?:など|$)", exam)
        if m:
            exam_refs = m.group(1).split("、")[0]
        elif "は" in exam:
            exam_refs = exam.split("は")[0]
        if (
            topic
            and _normalize_for_compare(core_subj) not in _normalize_for_compare(exam_refs)
        ):
            return (
                f"本問が問う{topic}の代表例は{exam_refs}などであり、"
                f"{core_subj}は該当しない。"
            )

    if "分類" in stem and "ではない" in core:
        m_subj = re.match(r"^(.+?)の分類", stem)
        if m_subj and "は" in exam:
            subj = m_subj.group(1).strip()
            exam_subj = exam.split("は")[0].strip()
            exam_cat = exam.split("は", 1)[1].strip().rstrip("。．")
            if subj == exam_subj:
                return f"{subj}は{exam_cat}に該当する。"

    if "組合せ" in stem and "分類" in stem and "は" in core:
        if "重油" in core and "第三石油類" in core:
            return "重油は第三石油類であり、アルコール類ではない。"
        if "灯油" in core and "第二石油類" in core:
            return "灯油は第二石油類であり、特殊引火物ではない。"
        if "メタノール" in core and "アルコール" in core:
            return "メタノールはアルコール類であり、第二石油類ではない。"
        if "ジエチル" in core:
            return "ジエチルエーテルは特殊引火物である。"

    if "該当" in stem and "は" in exam:
        exam_subj = exam.split("は")[0]
        if exam_subj != core_subj:
            return f"{exam}。{core}。"
    return ""


def _elaborate_wrong_classification(stem: str, core: str) -> str:
    """類別・消火・数量など、coreの内容から追加1文を生成。"""
    core = core.rstrip("。")
    m = re.match(r"^(.+?)は(.+?)である$", core)
    if not m:
        return ""
    _subj, cat = m.group(1), m.group(2)

    if re.search(r"第\d類", cat) and ("第4類" in stem or "引火性液体" in stem):
        return "第4類（引火性液体）とは別の類別である。"
    if "類別" in stem and "組合せ" in stem and re.search(r"第\d類", cat):
        return f"{cat}という組合せは、消防法上の類別と一致しない。"
    if "消火" in stem:
        if "冷却" in core or "温度" in core:
            return "温度を下げる冷却消火の説明であり、設問の消火方法とは異なる。"
        if "除去" in core or "取り除" in core:
            return "可燃物を取り除く除去消火の説明であり、設問の消火方法とは異なる。"
    if "指定数量" in stem and ("L" in core or "リットル" in core or "数量" in core):
        return "政令で定める指定数量の値として誤りである。"
    if "倍数" in stem:
        return "指定数量の倍数の算定方法として誤りである。"
    if "組合せ" in stem and ("製造所" in stem or "施設" in stem):
        if "分類ではない" in core:
            return "法令上の製造所等は、製造所・貯蔵所・取扱所を指す。"
    if ("取扱者" in stem and "区分" in stem and ("甲種" in core or "乙種" in core or "丙種" in core)):
        return "危険物取扱者の区分と取扱範囲の説明として誤りである。"
    if "特殊引火物" in stem and m:
        subj, cat = m.group(1), m.group(2)
        if "石油類" in cat or "動植物油" in cat:
            return f"{subj}は{cat}であり、特殊引火物ではない。"
    if "分類" in stem and "軽油" in stem and "ではない" in core:
        return "軽油は第二石油類に該当する。"
    return ""


def _wrong_note_opening(choice_num: int, opt_sn: str, core: str) -> str:
    """O4の誤答メモから1文目を作る（肢番号は q-exp-choice-head で表示）。"""
    del choice_num
    core = core.rstrip("。").strip()
    return f"「{opt_sn}」について、{core}。"


def _strip_wrong_note_head_num(note: str) -> str:
    """他肢リスト見出しと重複する先頭の肢番号を除去。"""
    return re.sub(r"^（[０-９0-9]+）\s*", "", norm(note)).lstrip()


def _wrong_note_context_sentence(page: dict, core: str, choice_text: str = "") -> str:
    """肢ごとの2文目。stem と選択肢・注記から生成（正答引用なし）。"""
    stem = norm(page.get("stem_plain") or page.get("stem"))
    core = core.rstrip("。")
    choice = norm(choice_text).rstrip("。") if choice_text else ""
    blob = f"{choice}{core}"
    if question_ask_mode(stem) == "least_appropriate":
        return ""

    if re.search(r"第\d類", core) or "類危険物" in core:
        if "乙種第4" in stem or ("第4類" in stem and "性質" in stem):
            if "第4類" not in core and "引火性液体" not in core:
                return "第4類（引火性液体）とは別の区分である。"
        if "類別" in stem and "組合せ" in stem:
            return "危険物の類別と性質の組合せとして誤りである。"

    if "消火" in stem:
        if "冷却" in core or "温度" in core:
            return "冷却消火の説明であり、設問の消火方法としては該当しない。"
        if "除去" in core or "取り除" in core:
            return "除去消火の説明であり、設問の消火方法としては該当しない。"
        if "窒息" in stem and ("着火" in core or "蒸気" in core):
            return "窒息消火の説明としては該当しない。"
        if "酸素" in stem and ("供給" in stem or "断" in stem):
            if "加熱" in blob:
                return "加熱は燃焼を助けるため、酸素供給を断つ消火法ではない。"
            if "冷却" in blob:
                return "冷却消火は温度を下げる方法であり、酸素供給を断つ方法ではない。"
            if "除去" in blob:
                return "除去消火は可燃物を取り除く方法である。"
            if "発火" in blob and "消火" in blob:
                return "発火消火という消火方法は存在しない。"
        if ("温度を下げる" in stem or "冷却" in stem) and "消火" in stem:
            if "混触" in blob:
                return "危険物の混触は火災原因となり得るが、冷却消火の方法ではない。"
            if "除去" in blob:
                return "除去消火は可燃物を取り除く方法であり、温度低下が主目的ではない。"
            if "窒息" in blob:
                return "窒息消火は酸素供給を断つ方法であり、温度低下が主目的ではない。"
            if "抑制" in blob:
                return "抑制消火は連鎖反応を抑える方法であり、温度低下が主目的ではない。"

    if "可燃性蒸気" in stem and ("燃え" in stem or "引火" in stem or "現象" in stem):
        if "凝固" in blob:
            return "凝固は液体が固体になる変化であり、燃焼開始の現象ではない。"
        if "中和" in blob:
            return "中和は酸とアルカリの化学反応であり、燃焼現象ではない。"
        if "書換" in blob:
            return "免状の書換えは行政手続きであり、燃焼現象ではない。"
        if "沈殿" in blob:
            return "沈殿は溶液から固体が析出する現象であり、燃焼現象ではない。"

    if "固体内部" in stem and "熱" in stem:
        if "還元" in blob:
            return "還元は化学反応の種類であり、固体内部への熱移動の現象ではない。"
        if "放射" in blob:
            return "放射は電磁波による熱移動であり、固体内部の主たる伝熱方式ではない。"
        if "対流" in blob:
            return "対流は流体の移動による熱移動であり、固体内部では主に起こらない。"
        if "中和" in blob:
            return "中和は酸とアルカリの反応であり、熱移動の現象ではない。"

    if "液体" in stem and ("特徴" in stem or "正しいもの" in stem):
        if "燃えない" in blob or ("燃え" in blob and "ない" in blob):
            return "ガソリンなど燃える液体もあり、必ず不燃ではない。"
        if "全体" in blob and "広が" in blob:
            return "気体は容器全体に広がる性質があり、液体とは異なる。"
        if "溶ける" in blob:
            return "水に溶けない液体も多く、必ず水溶液になるわけではない。"
        if "一定" in blob and "形" in blob:
            return "形と体積が一定に近いのは固体の特徴である。"

    if "気体になり始める" in stem or ("液体" in stem and "温度" in stem and "何" in stem):
        if "発火点" in blob:
            return "発火点は火源なしで自然発火する最低温度である。"
        if "引火点" in blob:
            return "引火点は火源で可燃性蒸気が引火する最低温度である。"
        if "凝固点" in blob:
            return "凝固点は液体が固体になる温度である。"
        if "融点" in blob:
            return "融点は固体が液体になる温度である。"
        if "沸点" in blob:
            return "沸点は液体が気体になり始める温度である。"

    if "固体になり始める" in stem or ("液体" in stem and "固体" in stem and "何" in stem):
        if "燃焼範囲" in blob:
            return "燃焼範囲は可燃性蒸気の濃度範囲であり、温度の名称ではない。"
        if "発火点" in blob:
            return "発火点は火源なしで自然発火する最低温度である。"
        if "引火点" in blob:
            return "引火点は火源で可燃性蒸気が引火する最低温度である。"
        if "沸点" in blob:
            return "沸点は液体が気体になり始める温度である。"
        if "凝固点" in blob:
            return "凝固点は液体が固体になり始める温度である。"

    if ("液体" in stem and "気体" in stem and "移動" in stem) or "熱が運ばれる" in stem:
        if "放射" in blob:
            return "放射は電磁波による熱移動であり、流体の移動とは別である。"
        if "熱伝導" in blob or ("伝導" in blob and "熱" in blob):
            return "熱伝導は固体内部などで熱が伝わる現象である。"
        if "酸化" in blob:
            return "酸化は化学反応の名称であり、熱移動の現象ではない。"
        if "中和" in blob:
            return "中和は酸とアルカリの反応であり、熱移動の現象ではない。"

    if "水" in stem and "重さ" in stem and "比" in stem:
        if "燃焼範囲" in blob:
            return "燃焼範囲は濃度の概念であり、液体の比重とは別である。"
        if "発火点" in blob:
            return "発火点は温度の概念であり、液体の比重とは別である。"
        if "蒸気比重" in blob:
            return "蒸気比重は空気を基準とし、液比重は水を基準とする。"
        if "指定数量" in blob:
            return "指定数量は危険物の数量基準であり、比重とは別である。"

    if "熱量" in stem and "単位" in stem:
        if "秒" in blob:
            return "秒は時間の単位であり、熱量の単位（J等）とは別である。"
        if "kg" in blob:
            return "kgは質量の単位であり、熱量の単位とは別である。"
        if "L" in blob or "リットル" in blob:
            return "Lは体積の単位であり、熱量の単位とは別である。"
        if blob.strip().startswith("m") or choice == "m":
            return "mは長さの単位であり、熱量の単位とは別である。"

    if "三要素" in stem or ("燃焼" in stem and "要素" in stem):
        return "可燃物・酸素供給源・点火源がそろった組合せではない。"

    if "蒸気圧" in stem:
        if "灰" in core:
            return "飽和蒸気圧は液体と蒸気が平衡のときの蒸気の圧力である。"
        if "免状" in core:
            return "飽和蒸気圧は物理化学の概念であり、免状番号ではない。"
        if "溶け" in core or "溶解" in core:
            return "溶解速度は別の概念である。"
        if "pH" in blob:
            return "pHは水溶液の酸性・アルカリ性の尺度であり、蒸気圧とは別である。"
        if "不燃" in blob:
            return "蒸気圧の大小と燃焼性は別の問題である。"
        if "指定数量" in blob:
            return "指定数量は政令の数量基準であり、蒸気圧とは無関係である。"
        if "沈" in blob or ("水" in blob and "沈" in blob):
            return "液体の浮沈は比重の問題であり、蒸気圧とは別である。"
        if "酸素" in blob and "放出" in blob:
            return "蒸気圧と酸素放出性は別である。"
        if "重い" in blob or ("比重" in blob and "水" in blob) or "水より" in blob:
            return "液体の比重は蒸気圧の大小とは別の物理量である。"
        if "逆" in blob or ("蒸発" in blob and "にくい" in blob):
            return "蒸気圧が高いほど蒸発しやすい傾向がある。"
        if "同じ" in blob or "色" in blob or "引火しない" in blob or "にくい" in blob:
            return "蒸気圧と蒸発の関係として誤った理解である。"

    if "発熱反応" in stem:
        if "凝固" in core or "固体になる" in core:
            return "凝固点は状態変化の温度であり、発熱反応の説明ではない。"
        if "伴わない" in core:
            return "熱をまったく伴わない反応は発熱反応ではない。"
        if "熱を" in core and "放出" in core:
            return "発熱反応は反応に伴って熱を放出する反応である。"
        if "溶け" in core or "溶解" in core:
            return "溶解は物理現象であり、発熱反応の定義ではない。"
        if "水だけ" in core:
            return "発熱反応は熱を放出する反応の概念である。"

    if "還元" in stem and "説明" in stem:
        if "指定数量" in core or "手続" in core:
            return "還元は化学反応の概念であり、法令手続きではない。"
        if "器具" in core or "比重" in core:
            return "液体の比重計などの器具の名称ではない。"
        if "溶け" in core or "溶解" in core:
            return "還元は酸素を失う反応などであり、溶解とは別である。"
        if "温度" in core or "燃え" in core:
            return "引火点などの温度概念とは別である。"

    if "酸素" in stem and "結びつ" in stem:
        if "中和" in blob:
            return "中和は酸とアルカリの反応であり、酸素結合の名称ではない。"
        if "還元" in blob:
            return "還元は酸素を失う方向の反応として説明され、本問の反応とは逆である。"
        if "蒸発" in blob:
            return "蒸発は液体が気体になる状態変化であり、化学反応の名称ではない。"
        if "凝固" in blob:
            return "凝固は液体が固体になる状態変化であり、化学反応の名称ではない。"

    if ("酸性" in stem or "アルカリ" in stem) and "指標" in stem:
        if "蒸気比重" in blob:
            return "蒸気比重は蒸気と空気の重さの比であり、酸性度の指標ではない。"
        if "免状" in blob:
            return "免状番号は資格証の番号であり、酸性度の指標ではない。"
        if "保有空地" in blob:
            return "保有空地は施設配置の空地であり、酸性度の指標ではない。"
        if "指定数量" in blob:
            return "指定数量は危険物の数量基準であり、酸性度の指標ではない。"

    if "酸化" in stem and "説明" in stem:
        if "蒸発" in core:
            return "蒸発は状態変化であり、酸化反応の説明ではない。"
        if "5個" in core or ("電子" in core and "得" in core):
            return "酸化は電子を失う反応としても説明される。"
        if "浮" in core:
            return "比重や浮沈の問題であり、酸化の概念ではない。"
        if "温度" in core:
            return "温度変化そのものを酸化というわけではない。"

    if "有機化合物" in stem:
        if "免状" in core:
            return "有機化合物は炭素を含む化合物であり、免状の名称ではない。"
        if "酸素" in core and "放出" in core:
            return "酸素放出性と有機化合物の定義は別である。"
        if "金属" in core:
            return "有機化合物は一般に炭素を主成分とする。"
        if "禁水" in core or "水素" in core:
            return "すべてが禁水性とは限らない。"

    if "炭化水素" in stem:
        if "鉄" in blob or "銅" in blob:
            return "炭化水素は炭素と水素からなる有機化合物である。"
        if "ナトリウム" in blob or ("塩素" in blob and "だけ" in blob):
            return "ナトリウムと塩素は別化合物の元素で、炭化水素ではない。"
        if "酸素" in blob and "窒素" in blob:
            return "炭化水素は炭素と水素からなる化合物である。"
        if "ヘリウム" in blob:
            return "ヘリウムは希ガスであり、炭化水素の構成元素ではない。"
        if "金属" in blob:
            return "炭化水素は有機化合物の一種であり、金属ではない。"
        if "水" in blob and ("だけ" in blob or "ではない" in blob):
            return "水（H₂O）とは組成が異なる。"
        if "施設" in blob:
            return "危険物施設の名称ではない。"

    if "軽油" in stem and "分類" in stem:
        if "特殊引火物" in blob:
            return "軽油は灯油とともに第二石油類に分類される。"
        if "動植物油" in blob:
            return "動植物油類は菜種油・大豆油などであり、軽油とは別である。"
        if "第一石油類" in blob:
            return "ガソリンなどが第一石油類であり、軽油は第二石油類である。"

    if "ガソリン" in stem and "性質" in stem:
        if "不燃" in blob:
            return "ガソリンは引火性液体であり、揮発性・可燃性がある。"
        if "水溶性" in blob and "安全" in blob:
            return "水に溶けにくくても可燃性蒸気に引火する危険がある。"

    if "ガソリン" in stem and "指定数量" in stem:
        if "100" in blob:
            return "ガソリン（第一石油類）は200 Lが指定数量である。"
        if "50" in blob:
            return "50 Lは特殊引火物などの指定数量である。"
        if "動植物油" in blob or "10,000" in blob or "10000" in blob:
            return "動植物油類の指定数量は10,000 Lであり、ガソリンとは異なる。"
        if "2,000" in blob or "2000" in blob:
            return "2,000 Lは第3石油類水溶性等の指定数量であり、ガソリンの整理ではない。"
        if "400" in blob and "水溶性" in blob:
            return "400 L水溶性はアセトン等の指定数量であり、ガソリンではない。"
        if "1,000" in blob or "1000" in blob:
            return "1,000 Lは灯油・軽油など第二石油類非水溶性の指定数量である。"

    if "不飽和炭化水素" in stem:
        if "水" in core:
            return "不飽和炭化水素は炭素と水素からなる有機化合物である。"
        if "金属" in core:
            return "有機化合物であり、金属元素だけではない。"
        if "酸素" in core and "放出" in core:
            return "酸素を放出する液体の定義ではない。"
        if "指定数量" in core or "単位" in core:
            return "危険物の指定数量の単位ではない。"

    if "アルコール類" in stem:
        if "不燃" in core or "引火" in core:
            return "メタノールやエタノールなど引火性液体がある。"
        if "標識" in core:
            return "危険物標識の種類名ではない。"
        if "金属" in core and "ナトリウム" in core:
            return "アルコール類はヒドロキシ基をもつ有機化合物である。"

    if "水溶性" in stem and "正しい" in stem:
        if "酸素" in core:
            return "酸素を放出する性質（酸素系第3類）とは別である。"
        if "重い" in core:
            return "水より重いことは液体の比重の問題である。"
        if "燃え" in core or "引火" in core:
            return "エタノールなど水に溶けても引火性がある。"
        if "蒸気" in core:
            return "蒸気比重は別の概念である。"

    if "静電気" in stem and "第4類" in stem:
        if "溶け" in core or "水溶性" in core:
            return "静電気火花は可燃性蒸気への着火源となり得る。"
        if "指定数量" in core:
            return "静電気は指定数量を変えるものではない。"
        if "蒸気比重" in core or "ゼロ" in core:
            return "蒸気比重とは別の火災予防論点である。"
        if "不燃" in core:
            return "静電気は可燃性を変えるものではない。"

    if "静電気" in stem:
        if "火花" in blob:
            return "火花は着火源となり得るため、静電気対策としては不適切である。"
        if "溶" in blob and "水" in blob:
            return "静電気火花は可燃性蒸気等への着火源となり得る。"
        if "酸素" in blob and "なく" in blob:
            return "静電気火花は点火源となり、酸素を除去するものではない。"
        if "流速" in blob and "速" in blob:
            return "高速流動は帯電の原因となり得るため、抑制する対策が必要である。"
        if "摩擦" in blob or ("乾燥" in blob and "激し" in blob):
            return "乾燥状態での激しい摩擦は帯電を助長するため、対策としては不適切である。"
        if "絶縁" in blob or ("電荷" in blob and "逃が" in blob and "ない" in blob):
            return "電荷を逃がすため接地が重要であり、絶縁だけでは不十分である。"
        if "標識" in core:
            return "静電気は摩擦・流動・乾燥などで発生しやすい。"
        if "免状" in core or "交付" in core:
            return "静電気発生と免状交付は無関係である。"
        if "指定数量" in core:
            return "指定数量の計算とは無関係である。"
        if "静止" in core and "だけ" in core:
            return "摩擦や流動も静電気発生に関係する。"
        if "接地" in core:
            return "接地は静電気を逃がす対策であり、発生条件ではない。"
        if "湿度" in core and ("管理" in core or "適切" in core):
            return "湿度管理は帯電防止の対策であり、発生条件そのものではない。"
        if ("抑える" in core or "防止" in core) and ("流動" in core or "摩擦" in core):
            return "流動や摩擦を抑えるのは帯電防止の対策である。"
        if "換気" in core:
            return "換気は可燃性蒸気対策であり、静電気の発生条件ではない。"
        if any(k in core for k in ("絶縁", "かき混", "高速", "ためる", "流動")):
            return "静電気の発生や着火リスクを下げる方法ではない。"

    if "不完全燃焼" in stem:
        if "存在しない" in blob and "可燃物" in blob:
            return "不完全燃焼も燃焼の一種であり、可燃物が存在する状態で起こる。"
        if "十分" in blob and "酸素" in blob:
            return "酸素が十分にある条件では完全燃焼に近くなりやすい。"
        if "二酸化炭素だけ" in blob:
            return "一酸化炭素やすすを生じる点で不完全燃焼の説明と異なる。"

    if "完全燃焼" in stem:
        if "一酸化炭素" in blob or ("酸素" in blob and "不足" in blob):
            return "酸素不足では不完全燃焼に近く、一酸化炭素だけを必ず生じるわけではない。"
        if "火源" in blob and "なし" in blob:
            return "自然発火の温度は発火点の概念であり、完全燃焼の条件とは別である。"
        if "固体" in blob and ("液体" in blob or "なる" in blob):
            return "状態変化の現象であり、燃焼の状態とは別である。"
        if "溶け" in blob or "溶解" in blob:
            return "溶解は物理現象であり、燃焼状態の説明ではない。"

    if "蒸気比重" in stem or "蒸気" in stem and "空気" in core:
        if "上昇" in core or "引火しない" in core:
            return "空気より重い可燃性蒸気は低所に滞留しやすい。"

    if "熱の伝わり方" in stem or "熱伝導" in stem:
        if "無関係" in core:
            return "熱伝導・対流・放射はいずれも熱の移動に関わる。"

    if "密度" in stem:
        if "750" in blob:
            return "750 gは密度0.75の値そのものであり、質量＝密度×体積で300 gとなる。"
        if "533" in blob:
            return "400÷0.75のように密度で割る計算は誤りである。"
        if "400 g" in blob and ("体積" in core or "そのまま" in core):
            return "質量は密度×体積で求め、体積をそのまま質量にしてはならない。"
        if "計算の向き" in core or "不適切" in core:
            return "質量＝密度×体積の式を正しく適用して求める。"
        if "体積" in core and "質量" in core:
            return "密度は質量÷体積で求める。"

    if "分類" in stem and "軽油" in stem:
        if "ではない" in core:
            return "軽油は第二石油類に該当する。"

    if "特殊引火物" in stem and "石油類" in core:
        return "特殊引火物ではなく石油類に分類される。"

    if "指定数量" in stem:
        if "指定数量以上" in stem and ("設置" in stem or "貯蔵" in stem):
            if "免状" in blob:
                return "施設の設置許可と免状の再交付は別の手続きである。"
            if "販売" in blob or "価格" in blob:
                return "設置許可は施設に関する手続きであり、販売価格の届出ではない。"
            if "受験" in blob:
                return "試験申込と施設の設置許可は無関係である。"
            if "消火器" in blob:
                return "消火器の購入と施設の設置許可は別の手続きである。"
        if "説明" in stem:
            if "販売" in blob or "価格" in blob:
                return "指定数量は危険物の数量基準であり、販売価格ではない。"
            if "年齢" in blob:
                return "指定数量は数量の基準であり、取扱者の年齢制限ではない。"
            if "消火器" in blob:
                return "指定数量は危険物の数量基準であり、消火器の重さではない。"
            if "試験" in blob and "時間" in blob:
                return "指定数量は数量の単位基準であり、試験時間の単位ではない。"
        if "倍数" not in stem:
            if "ガソリン" in stem and "灯油" in stem and "組合せ" in stem:
                if "1,000" in blob and "ガソリン" in blob:
                    return "ガソリン200 L、灯油1,000 Lが正しい組合せである。"
                if "10,000" in blob or "6,000" in blob:
                    return "10,000 Lは動植物油類、6,000 Lは第4石油類の指定数量である。"
                if "50" in blob and "400" in blob:
                    return "50 Lは特殊引火物、400 Lはアルコール類の指定数量である。"
                if "400" in blob and "200" in blob and "ガソリン" in blob:
                    return "ガソリン200 L、灯油1,000 Lが正しい組合せである。"
            if "灯油" in stem or "軽油" in stem:
                if "400 L" in core:
                    return "灯油の指定数量は1,000 Lである。"
                if "200 L" in core:
                    return "灯油は第二石油類で、指定数量は1,000 Lである。"
                if "50 L" in core:
                    return "50 Lは特殊引火物の指定数量である。"
            if "動植物油" in stem:
                if "400 L" in core:
                    return "動植物油類の指定数量は10,000 Lである。"
                if "6,000 L" in core or "6000" in core:
                    return "6,000 Lは第4石油類の指定数量である。"
                if "1,000 L" in core:
                    return "1,000 Lは第二石油類非水溶性の指定数量である。"
            if "特殊引火物" in stem:
                pass
            elif "アルコール" in stem:
                pass
            elif "400 L" in core and "アルコール" in core:
                return "本問が問う危険物の指定数量とは異なる。"
            if "400 L" in core:
                return "400 Lはアルコール類の指定数量である。"
            if "200 L" in core:
                return "200 Lは第1石油類非水溶性の指定数量である。"
            if "1,000 L" in core or "1000 L" in core:
                return "1,000 Lは第二石油類非水溶性の指定数量である。"
            if "50 L" in core:
                return "50 Lは特殊引火物の指定数量である。"
            if "10,000 L" in core or "10000" in core:
                return "10,000 Lは動植物油類の指定数量である。"
            if "6,000 L" in core or "6000" in core:
                return "6,000 Lは第4石油類の指定数量である。"
            if "2,000 L" in core:
                return "2,000 Lは第3石油類非水溶性の指定数量である。"
            if "4,000 L" in core:
                return "4,000 Lは第3石油類水溶性の指定数量である。"
        else:
            if "考え方" in stem and "倍数" in stem:
                if "指定数量を" in blob and "貯蔵" in blob:
                    return "倍数は数量÷指定数量であり、分母と分子を逆にしない。"
                if "消火器" in blob or "受験" in blob:
                    return "指定数量倍数は危険物の数量基準であり、消火器や受験者数とは無関係である。"
                if "販売" in blob or "価格" in blob:
                    return "指定数量倍数は数量の基準であり、販売価格とは無関係である。"
                if "免状" in blob and "番号" in blob:
                    return "指定数量倍数は数量の基準であり、免状番号とは無関係である。"
            if "動植物油" in stem and ("10,000" in stem or "10000" in stem):
                if "1.0倍" in blob:
                    return "10,000 L貯蔵なら1.0倍である。"
                if "2.0倍" in blob:
                    return "20,000 Lなら2.0倍である。"
                if "0.25倍" in blob:
                    return "2,500 Lなら0.25倍である。"
            if "50" in stem and "200 L" in stem:
                if "なら" in core and "倍" in core:
                    return "本問は50 L÷200 L＝0.25倍を求める。"
            if "ガソリン分だけ" in core:
                return "エタノール分0.5倍も合算して1.0倍となる。"
            if "単純" in core and "合計" in core:
                return "数量を足して割るのではなく、倍数を合算する。"
            if "足して" in core or "指定数量を足" in core:
                return "各危険物の指定数量倍数を個別に求める。"
            if "800 L" in core:
                return "本問の貯蔵量50 Lとは数量が異なる。"
            if "100 L" in core and "0.5倍" in core:
                return "本問の貯蔵量50 Lとは数量が異なる。"
            if "200 L" in core and "1.0倍" in core:
                return "本問の貯蔵量50 Lとは数量が異なる。"
            if "400 L" in core and "2.0倍" in core:
                return "本問の貯蔵量50 Lとは数量が異なる。"
            if "灯油" in stem and "軽油" in stem:
                if "計算結果" in core:
                    return "灯油500÷1000＝0.5倍、軽油500÷1000＝0.5倍、合計1.0倍である。"
                if "片方" in core:
                    return "灯油・軽油それぞれ0.5倍として合算する。"
            if "アセトン" in stem and "灯油" in stem:
                if "片方" in core or "0.5倍" in blob:
                    return "0.5倍は片方のみの計算であり、灯油分も合算して1.0倍となる。"
            if "ガソリン" in stem and "200 L" in stem:
                if "2.0倍" in blob:
                    return "2.0倍は400 L÷200 Lの場合であり、120 Lでは0.6倍である。"
                if "1.2倍" in blob:
                    return "120÷200＝0.6倍であり、指定数量で割る計算が必要である。"
                if "0.8" in blob and "潤滑油" in stem:
                    return "ガソリン・軽油・潤滑油それぞれの倍数を合算する必要がある。"
            if "計算結果" in core:
                return "指定数量倍数は数量÷指定数量で個別に求め合算する。"
            if "特殊引火物" in stem:
                if "1.0倍" in blob or "1.0倍" in core:
                    return "25 L÷50 L＝0.5倍であり、1.0倍ではない。"
                if "2.0倍" in blob or "2.0倍" in core:
                    return "50 Lなら1.0倍、100 Lなら2.0倍となる。"
                if "5.0倍" in blob:
                    return "250 Lなら5.0倍となる計算であり、25 Lではない。"
        if "特殊引火物" in stem and "動植物油" in stem and "組合せ" in stem:
            if "400" in blob and "特殊引火物" in blob:
                return "特殊引火物の指定数量は50 Lである。"
            if "50" in blob and "動植物油" in blob and "400" not in blob.split("動植物油")[0][-10:]:
                pass
            if ("400" in blob and "動植物油" in blob) or ("50" in blob and "特殊引火物" in blob and "400" in blob):
                return "動植物油類の指定数量は10,000 Lである。"
            if "逆" in core or "数値" in core:
                return "特殊引火物50 L、動植物油類10,000 Lが正しい。"
        if "特殊引火物" in stem and "理由" in stem:
            if "免状" in blob and "不要" in blob:
                return "指定数量の大小と免状制度の要否は別の問題である。"
            if "不燃" in blob:
                return "特殊引火物は引火危険が高いため、指定数量が小さい。"
            if "販売" in blob or "価格" in blob:
                return "指定数量は数量基準であり、販売価格とは無関係である。"
            if "沈" in blob or ("水" in blob and "浮" in blob):
                return "指定数量の大小は引火危険の程度に関係し、浮沈とは直接無関係である。"
        return ""

    if "設置許可" in stem and "免状" in stem:
        if "消火剤" in blob:
            return "設置許可と免状は法令上の制度であり、消火剤の種類ではない。"
        if "指定数量" in blob:
            return "指定数量の数量基準と、許可・免状の制度は別である。"
        if "常に" in blob and "不要" in blob:
            return "設置許可と取扱者免状は別の手続きである。"

    if "変更許可" in stem or (
        "製造所" in stem and "変更" in stem and "関係" in stem
    ):
        if "広告" in blob or ("色" in blob and "変更" in blob):
            return "変更許可は位置・構造・設備の変更に関する手続きである。"
        if "昼食" in blob:
            return "取扱者の私的な事柄は法令上の施設変更ではない。"
        if "ロゴ" in blob or "社名" in blob:
            return "メーカーの商標変更は施設変更許可の対象ではない。"
        if "受験票" in blob:
            return "試験の受験票と施設の変更許可は無関係である。"

    if "完成検査前検査" in stem:
        if "味" in blob:
            return "完成検査前検査はタンク等の設備確認に関係する。"
        if "答案" in blob or ("試験" in blob and "答案" in blob):
            return "試験答案と完成検査前検査は無関係である。"
        if "価格" in blob:
            return "販売価格表と設備検査は別である。"
        if "広告" in blob or "宣伝" in blob:
            return "宣伝広告と完成検査前検査は無関係である。"

    if "数量変更" in stem or (
        "数量" in stem and "変更" in stem and "製造所" in stem
    ):
        if "答案" in blob or ("試験" in blob and "答案" in blob):
            return "数量変更届は施設管理の手続きであり、試験答案ではない。"
        if "手続" in blob and "不要" in blob:
            return "法令上、届出が必要となる場合がある。"
        if "なくなる" in blob or ("危険物" in blob and "なく" in blob):
            return "数量を変えても危険物の性質は変わらない。"
        if "第4類" in blob and "不要" in blob:
            return "第4類施設でも数量変更の管理が関係する場合がある。"

    if "甲種" in stem and "取扱範囲" in stem:
        if "単位" in blob and "指定数量" in blob:
            return "指定数量の数量基準と、免状の取扱範囲は別である。"
        if "消火設備" in blob:
            return "甲種免状は取扱者の資格であり、消火設備の名称ではない。"
        if "第4類" in blob and "だけ" in blob:
            return "甲種はすべての種類の危険物を取り扱える資格である。"
        if "一切" in blob and "取扱" in blob:
            return "甲種は最も広い取扱範囲をもつ免状である。"

    if "製造所等" in stem and "設置許可" in stem:
        if "乙" in core and "関係" in core:
            return "第4類危険物を扱う施設でも設置許可が関係する場合がある。"
        if "分類" in core:
            return "製造所等は施設の総称であり、危険物の分類名ではない。"
        if "未満" in core or "条例" in core:
            return "指定数量未満でも市町村条例等が関係する場合がある。"
        if "写真" in core or ("免状" in core and "変更" in core):
            return "設置許可と取扱者免状の手続きは別である。"
        if "年齢" in blob:
            return "設置許可は施設の位置・構造・設備の適合を確認する制度であり、年齢確認だけが目的ではない。"
        if "試験" in blob or "採点" in blob:
            return "設置許可は施設に関する行政手続きであり、試験採点とは無関係である。"
        if "受験料" in blob or ("受験" in blob and "料" in blob):
            return "設置許可は施設に関する行政手続きであり、試験受験料とは無関係である。"
        if "販売" in blob or "価格" in blob:
            return "設置許可は施設に関する手続きであり、危険物の販売価格を決める制度ではない。"
        if "写真" in blob:
            return "設置許可と取扱者免状の交付手続きは別の制度である。"

    if "保安検査" in stem and "保安講習" in stem:
        if "指定数量" in blob and ("なく" in blob or "消" in blob):
            return "いずれも指定数量をなくす制度ではない。"
        if "販売" in blob or "価格" in blob:
            return "保安検査は施設・設備の点検、保安講習は安全教育であり、販売価格とは無関係である。"
        if "試験" in blob and "科目" in blob:
            return "試験科目名ではなく、保安検査と保安講習は別の制度である。"
        if "味" in blob:
            return "危険物の官能確認を行う制度ではない。"

    if "保安講習" in stem:
        if "指定数量" in blob or ("指定数量" in core and "別名" in core):
            return "保安講習は安全教育の制度であり、指定数量とは別である。"
        if "品名" in blob or "品名" in core:
            return "保安講習は安全教育制度であり、危険物の品名ではない。"
        if "写真" in blob or ("写真" in core and "撮影" in core):
            return "免状交付時の写真撮影と保安講習は別の手続きである。"
        if "消滅" in blob or ("取得" in blob and "制度" in blob):
            return "免状取得後も取扱作業者の安全教育が必要となる場合がある。"
        if "設置許可" in core or ("許可" in core and "別名" in core):
            return "保安講習は取扱作業従事者の安全教育制度である。"
        if "一般消費者" in core or "歩行者" in core:
            return "対象は危険物の取扱作業に従事する者である。"
        if "消火器" in core:
            return "消火器を購入した者だけが対象になる制度ではない。"
        if "甲種" in core and "関係しない" in core:
            return "甲種危険物取扱者であっても保安講習が関係する場合がある。"
        if "免状" in core and "存在しない" in core:
            return "免状取得後も取扱作業者の安全教育が必要となる。"
        if "単位" in core:
            return "保安講習は安全教育の制度であり、数量の単位ではない。"
        return ""

    if "完成検査" in stem and "定期点検" in stem:
        if "レシート" in blob:
            return "完成検査・定期点検は施設の検査制度であり、購入証明ではない。"
        if "指定数量" in blob and "変" in blob:
            return "指定数量の変更手続きと、施設検査は別である。"
        if "採点" in blob or ("試験" in blob and "制度" in blob):
            return "試験採点制度と施設の完成検査・定期点検は別である。"
        if "味" in blob:
            return "危険物の官能検査は行ってはならない。"

    if "保安距離" in stem and "保有空地" in stem:
        if "消火剤" in blob:
            return "いずれも施設配置の距離・空地に関する概念であり、消火剤ではない。"
        if "指定数量" in blob and "単位" in blob:
            return "指定数量の数量基準と、距離・空地の概念は別である。"
        if "免状" in blob:
            return "取扱者免状の区分と、施設配置の概念は別である。"
        if "価格" in blob:
            return "販売価格と施設配置の距離・空地は無関係である。"

    if "免状" in stem and ("亡失" in stem or "再交付" in stem):
        if "再交付" in core or "一切" in core:
            return "免状を亡失した場合には再交付の手続きがある。"
        if "設置許可" in core:
            return "免状手続きと施設の設置許可は別である。"
        if "廃棄" in core:
            return "免状亡失時に危険物をすべて廃棄する制度ではない。"
        if "範囲" in core and "超" in core:
            return "再交付しても免状の取扱範囲が拡大するわけではない。"

    if "施設保安員" in stem:
        if "味" in blob:
            return "危険物は官能で確認せず、施設の構造・設備の保安が主な業務である。"
        if "価格" in blob or "販売" in blob:
            return "施設保安員は施設の保安業務に関与し、販売価格決定とは無関係である。"
        if "分類" in blob:
            return "危険物施設保安員は施設保安に関与する者の名称である。"
        if "指定数量" in blob or "単位" in blob:
            return "指定数量は危険物の数量基準である。"
        if "試験" in blob and ("科目" in blob or "採点" in blob):
            return "試験科目名ではなく、施設保安に関与する者の名称である。"
        if "受験" in blob:
            return "試験の受験票ではなく、施設保安の役割である。"
        if "消火剤" in blob or "商品" in blob:
            return "消火剤の商品名ではなく、施設保安の役割である。"
        if "消防器具" in blob or "家庭用" in blob:
            return "施設の保安業務に関与する者の名称である。"

    if "保安統括管理者" in stem and "保安監督者" in stem:
        if "品名" in blob:
            return "いずれも人の役割・名称であり、危険物の品名ではない。"
        if "消火器" in blob and "型式" in blob:
            return "保安管理体制の担い手であり、消火器の型式名称ではない。"
        if "単位" in blob or ("指定数量" in blob and "単位" in blob):
            return "指定数量の数量基準と、保安管理者の役割は別である。"
        if "同じ" in blob or "一方" in blob:
            return "名称は似ているが、統括管理と現場監督は制度上区別される。"

    if "保安監督者" in stem:
        if "住宅" in blob:
            return "一定規模以上の製造所等で選任が必要となる場合がある。"
        if "誰でも" in blob or "無関係" in blob:
            return "法令上の資格・要件を満たした者が選任される。"
        if "容器" in blob and "製造" in blob:
            return "施設全体の保安管理を担う役割である。"
        if "味見" in blob or ("味" in blob and "確認" in blob):
            return "危険物の官能検査は行ってはならない。"
        if "価格" in blob:
            return "保安監督者は取扱作業の保安監督が主な役割である。"
        if "広告" in blob:
            return "施設の保安管理と広告制作は無関係である。"
        if "試験" in blob and "問題" in blob:
            return "試験問題作成者ではなく、現場の保安監督に関係する。"
        if "分類" in blob:
            return "選任届出は法令上の手続きであり、危険物の分類名ではない。"
        if "数式" in blob or "計算" in blob:
            return "選任届出は法令上の手続きであり、数量計算の数式ではない。"
        return ""

    if "免状" in stem and "記載" in stem:
        if "設置許可" in blob or "施設許可" in core:
            return "免状書換えと施設の設置許可は別の手続きである。"
        if "倍数" in blob or "合算" in blob:
            return "指定数量倍数の計算と免状書換えは別である。"
        if "保有空地" in blob:
            return "保有空地の確保と免状書換えは別の制度である。"
        if "完成検査" in blob:
            return "完成検査は施設の検査であり、免状書換えではない。"

    if "書換え" in stem or ("免状" in stem and "書換" in stem):
        if "見学" in blob:
            return "見学だけでは免状の記載事項変更には当たらない。"
        if "暗記" in blob:
            return "指定数量の暗記は免状書換えの事由ではない。"
        if "消火器" in blob and "購入" in blob:
            return "消火器の購入だけでは免状書換えは不要である。"
        if "毎日" in blob or ("扱わ" in blob and "ない" in blob):
            return "免状書換えは記載事項に変更があった場合などに必要となる。"

    if "予防規程" in stem:
        if "広告" in blob:
            return "予防規程は火災予防・保安管理の運用ルールであり、広告配色ではない。"
        if "食品" in blob:
            return "予防規程は火災予防・保安管理の運用ルールであり、食品取扱いのためではない。"
        if "指定数量" in blob and ("増" in blob or "減" in blob or "自由" in blob):
            return "指定数量を自由に変更する制度ではない。"
        if "合格" in blob or ("試験" in blob and "決" in blob):
            return "試験合格者を決める制度ではない。"
        if "装飾" in blob or "デザイン" in blob:
            return "予防規程は火災予防・保安管理の運用ルールである。"
        if "味見" in blob or ("味" in blob and "方法" in blob):
            return "危険物の官能検査は行ってはならない。"
        if "受験" in blob or "番号" in blob:
            return "試験制度とは無関係である。"
        if "価格" in blob:
            return "予防規程は施設の保安管理に関する規程である。"
        if "写真" in blob or ("免状" in blob and "管理" in blob):
            return "免状交付手続きとは無関係であり、施設の保安管理規程である。"
        if "指定数量" in blob and ("なく" in blob or "消" in blob):
            return "指定数量は法令上の基準であり、予防規程でなくなるわけではない。"
        if "分類表" in blob:
            return "危険物の類別一覧ではなく、施設の運用ルールである。"
        if "刻印" in blob:
            return "容器の材質刻印とは別の規程である。"
        if "第4類" in blob and "不要" in blob:
            return "第4類危険物を扱う施設でも必要となる場合がある。"
        return ""

    if "完成検査" in stem:
        if "書換" in blob or ("免状" in blob and "書" in blob):
            return "完成検査は施設の基準適合確認であり、免状書換えではない。"
        if "価格" in blob and ("確認" in blob or "販売" in blob):
            return "完成検査は施設の検査であり、販売価格の確認ではない。"
        if "自由" in blob or ("常に" in blob and "使用" in blob):
            return "原則として完成検査後に使用する必要がある。"
        if "試験" in core or "合格" in core:
            return "完成検査は施設が法令基準に適合するか確認する検査である。"
        if "味" in core:
            return "危険物の官能検査は行ってはならない。"
        if "写真" in core or ("免状" in core and "確認" in core):
            return "免状写真の確認手続きではない。"
        if "指定数量" in core and "変更" in core:
            return "指定数量変更の手続きではない。"
        if "自主" in core or "取扱者" in core:
            return "消防法上の完成検査と自主確認は別である。"
        if "運搬" in core or "車両" in core:
            return "製造所等の設置・変更後の施設が対象である。"
        if "不要" in core:
            return "設置・変更後には完成検査が必要となる場合がある。"
        return ""

    if "譲渡" in stem or "引渡" in stem:
        if "受験" in core:
            return "譲渡届出は施設の管理変更に関する手続きである。"
        if "味" in core:
            return "危険物の官能検査は行ってはならない。"
        if "第4類" in core and "ない" in core:
            return "第4類施設でも譲渡・引渡しはあり得る。"

    if "定期点検" in stem:
        if "飲" in blob:
            return "定期点検は施設の維持管理状態を確認するための点検である。"
        if "価格" in blob or "販売" in blob:
            return "販売価格決定とは無関係である。"
        if "色" in blob and ("標識" in blob or "変え" in blob):
            return "標識色を自由に変えるための制度ではない。"
        if "試験" in blob or "点数" in blob or "答案" in blob or "受験" in blob:
            return "試験制度とは無関係である。"
        if "味" in blob:
            return "定期点検は施設の維持管理状態を確認するための点検である。"
        if "免状" in blob and "写真" in blob:
            return "免状交付手続きとは無関係である。"
        if "味" in core and "記録" in core:
            return "点検記録は施設点検の結果を記載するものである。"
        if "指定数量" in blob and "変更" in blob:
            return "指定数量を変更する帳票ではない。"
        if "破棄" in blob:
            return "点検記録は一定期間保存することが求められる場合がある。"
        if "同じ" in blob or "完全" in blob:
            return "保安検査と定期点検は別の制度として区別される。"

    if "変更" in stem and "製造所" in stem:
        if "価格" in core:
            return "変更許可は位置・構造・設備の変更に関する手続きである。"
        if "住所" in core:
            return "危険物取扱者の住所変更とは別の手続きである。"
        if "立会" in core:
            return "施設変更の法令手続きと取扱者の立会いは別である。"
        if "標識" in core or "掲示" in core:
            return "標識の更新だけで変更許可が不要になるわけではない。"
        if "第4類" in core and "関係" in core:
            return "第4類危険物を扱う施設でも変更許可が関係する場合がある。"

    if "製造所" in stem and "設置" in stem:
        if "免状" in core:
            return "施設の設置許可と取扱者免状は別の制度である。"
        if "表示" in core:
            return "表示板の設置だけで設置許可が不要になるわけではない。"

    if "仮貯蔵" in stem or "仮取扱" in stem or "仮使用" in stem:
        if "免状" in blob and "別名" in blob:
            return "仮貯蔵・仮取扱いは一時的な取扱いの制度であり、免状の別名ではない。"
        if "試験" in blob or "受験" in blob:
            return "例外的な使用・取扱いの手続きであり、試験の受験制度ではない。"
        if "指定数量" in blob and ("なく" in blob or "不要" in blob):
            return "指定数量の制度をなくすものではない。"
        if "同じ" in blob or "違いはない" in blob or "名称以外" in blob:
            return "仮使用と仮貯蔵・仮取扱いは制度上区別される。"
        if "措置" in blob and "不要" in blob:
            return "火災予防上の措置を不要にする制度ではない。"
        if "第4類" in blob and "対象" in blob and "ない" in blob:
            return "第4類危険物も仮貯蔵・仮取扱いの対象となり得る。"
        if "屋外" in blob and "火気" in blob:
            return "屋外であっても火気管理などの保安措置は必要である。"
        if "自由" in blob or ("常に" in blob and "扱" in blob):
            return "指定数量以上の仮貯蔵・仮取扱いでも、法令上の手続きが必要となる場合がある。"
        if "屋外" in blob or "一時的" in blob or "取扱者" in blob:
            return "指定数量以上の仮貯蔵・仮取扱いでも、法令上の手続きが必要となる場合がある。"

    if "標識" in stem or "掲示板" in stem:
        if "役割" in stem or "目的" in stem:
            if "不燃" in blob or "不燃性" in blob:
                return "標識は注意喚起のための表示であり、危険物を不燃性に変える効果はない。"
            if "指定数量" in blob and ("減" in blob or "変" in blob or "自動" in blob):
                return "指定数量は政令で定められ、標識で変わるものではない。"
            if "許可" in blob and "不要" in blob:
                return "標識設置があっても、施設の設置許可が不要になるわけではない。"
            if "合格証" in blob or ("試験" in blob and "合格" in blob):
                return "試験合格証と標識・掲示板は別のものである。"
            if "免状" in core and "写真" in core:
                return "標識は危険物の性質・注意事項を明示するためのものである。"
            if "不燃" in core:
                return "危険物を不燃性にする設備ではない。"
            if "味" in core:
                return "味を知らせるための掲示ではない。"
            if "指定数量" in core:
                return "指定数量を変更するものではない。"
        if "同じ内容" in core or "同じ" in core:
            return "施設や危険物の種類に応じた表示内容が必要である。"
        if "設置してはならない" in core:
            return "危険物施設では標識・掲示板の設置が求められる場合がある。"
        if "装飾" in core or "飾る" in core:
            return "危険物施設の識別と注意喚起が主な目的である。"
        if "喫煙" in core:
            return "第4類危険物施設では火気厳禁の掲示が重要である。"
        if "投棄" in core:
            return "危険物は適正な方法で管理・処理しなければならない。"
        if "飲食" in core:
            return "危険物施設では火気・引火源の管理が必要である。"
        if "換気" in core and "禁止" in core:
            return "可燃性蒸気の滞留を防ぐため、換気は重要である。"
        if "換気" in core and ("重要" in core or "滞留" in core):
            return "換気禁止と掲示するのは、火災予防上適切ではない。"
        return ""

    if "自衛消防組織" in stem:
        if "不燃" in blob:
            return "自衛消防組織は火災等の初動対応体制であり、物質を不燃性に変えるものではない。"
        if "味" in blob:
            return "危険物の官能検査は行ってはならない。"
        if "印刷" in blob and "免状" in blob:
            return "免状の印刷機関ではなく、事業所の消防体制である。"
        if "化学式" in blob:
            return "自衛消防組織は火災等の初動対応体制に関する組織である。"
        if "指定数量" in blob and "決" in blob:
            return "指定数量は政令で定められ、組織が決めるものではない。"
        if "指定数量" in blob:
            return "指定数量は危険物の数量基準であり、組織の名称ではない。"
        if "免状" in blob or "交付" in blob:
            return "免状の交付機関ではなく、事業所等の消防体制である。"
        if "火災" in blob and "関係" in blob:
            return "火災時の対応に関係するが、本肢の定義としては誤った表現である。"

    if stem.startswith("販売取扱所") or (
        "販売取扱所" in stem and ("正しい" in stem or "説明" in stem)
    ):
        if "計算" in blob or ("方法" in blob and "指定数量" in blob):
            return "指定数量の計算方法ではなく、販売を行う取扱所の名称である。"
        if "免状" in blob:
            return "危険物取扱者免状とは別の施設名称である。"
        if "試験" in blob:
            return "販売取扱所は容器入り危険物を販売する取扱所である。"
        if "自衛消防" in blob:
            return "自衛消防組織は火災対応体制であり、施設の種類名ではない。"
        if "移動タンク" in blob:
            return "移動タンク貯蔵所は貯蔵所に分類される。"
        if "屋外タンク" in blob:
            return "屋外タンク貯蔵所は貯蔵所に分類される。"
        if "地下タンク" in blob:
            return "地下タンク貯蔵所は貯蔵所に分類される。"

    if stem.startswith("移送取扱所") or (
        "移送取扱所" in stem and "正しい" in stem
    ):
        if "免状" in core or "書換" in core or "窓口" in core:
            return "移送取扱所は配管等で危険物を移送する取扱所である。"
        if "移動タンク" in core:
            return "移動タンク貯蔵所は貯蔵所に分類される。"
        if "販売" in core:
            return "販売取扱所は取扱所の一種である。"
        if "屋内" in core:
            return "屋内貯蔵所は貯蔵所に分類される。"

    if "行政" in stem and ("措置" in stem or "違反" in stem):
        if "試験" in core and "問題" in core:
            return "行政措置は施設の法令遵守を確保するためのものである。"
        if "賞金" in core:
            return "使用停止命令などが行政措置の例である。"
        if "名称" in core or "施設名" in core:
            return "法令違反に対する行政措置とは無関係である。"
        if "行政措置" in core and "行われ" in core:
            return "本問が問う行政措置の具体例とは異なる。"

    if ("適合しない" in stem or "基準" in stem) and "措置" in stem:
        if "下水" in core:
            return "法令不適合時の行政措置とは無関係である。"
        if "試験" in core and ("免除" in core or "問題" in core):
            return "使用停止命令などが行政措置の例である。"
        if "指定数量" in core and "増加" in core:
            return "指定数量は政令で定められ、自動増加しない。"
        if "分類" in core and "自由" in core:
            return "危険物の分類を施設側で変更できるわけではない。"

    if "運搬" in stem and "適切" in stem:
        if "容器" in core or "収納" in core:
            return "運搬では表示だけでなく容器・積載方法も重要である。"
        if "混載" in core or "食品" in core:
            return "危険物の性質に応じた混載制限がある。"
        if "火気" in core:
            return "運搬中の火気使用は引火の危険がある。"
        if "漏えい" in core and "不要" in core:
            return "漏えい時は適切な応急措置が必要である。"

    if stem.startswith("屋内貯蔵所") or (
        "屋内貯蔵所" in stem and ("正しい" in stem or "説明" in stem)
    ):
        if "給油" in blob:
            return "給油取扱所は取扱所に分類される。"
        if "販売" in blob:
            return "販売取扱所は取扱所に分類される。"
        if "移動タンク" in blob:
            return "移動タンク貯蔵所は貯蔵所の一種である。"
        if "移送" in blob:
            return "移送取扱所は取扱所に分類される。"
        if "免状" in blob or "書換" in blob:
            return "免状手続きの窓口ではなく、建物内で危険物を貯蔵する施設である。"
        if "計算" in blob or "計算式" in blob:
            return "指定数量の計算式ではなく、施設の種類名である。"

    if stem.startswith("移動タンク貯蔵所") or (
        "移動タンク貯蔵所" in stem and "正しい" in stem
    ):
        if "販売" in core:
            return "販売取扱所は取扱所に分類される。"
        if "屋内" in core:
            return "屋内貯蔵所は建物内で貯蔵する施設である。"
        if "給油" in core:
            return "給油取扱所は取扱所に分類される。"
        if "試験" in core:
            return "移動タンク貯蔵所は貯蔵所の一種である。"

    if "移動タンク貯蔵所" in stem and "移送" in stem:
        if "漏えい" in core or "漏" in core:
            return "移送中の漏えいは火災・環境汚染の危険がある。"
        if "火気" in core:
            return "移送時の火気使用は引火の危険がある。"
        if "屋内" in core:
            return "移動タンク貯蔵所は屋内貯蔵所ではない。"
        if "表示" in core or "書類" in core:
            return "移送には表示や書類等が関係する場合がある。"

    if stem.startswith("製造所") and "正しい" in stem and "製造所等" not in stem:
        if "販売" in core or "取扱所" in core:
            return "製造所は危険物を製造する施設である。"
        if "試験" in core or "会場" in core:
            return "製造所は施設の種類名であり、試験会場ではない。"
        if "消火器" in core or "型式" in core:
            return "消火器の型式名ではなく、危険物施設の名称である。"
        if "分類" in core:
            return "危険物の分類表ではなく、施設の種類名である。"

    if "製造所等" in stem and "説明" in stem:
        if "第4類" in core and "別名" in core:
            return "製造所等は施設の総称であり、危険物の類別名ではない。"
        if "免状" in core:
            return "製造所等は施設の総称であり、取扱者免状ではない。"
        if "消火剤" in core:
            return "製造所等は施設の名称であり、消火剤ではない。"
        if "指定数量" in core:
            return "指定数量表ではなく、製造所・貯蔵所・取扱所の総称である。"

    if "給油取扱所" in stem and ("注意" in stem or "適切" in stem or "危険" in stem):
        if "換気" in blob and ("避" in blob or "ため" in blob):
            return "可燃性蒸気の滞留を防ぐため、換気は怠ってはならない。"
        if "下水" in blob or "排水" in blob:
            return "漏えいした燃料を下水へ流してはならない。"
        if "裸火" in blob:
            return "蒸気確認に裸火を用いると引火・爆燃の危険がある。"
        if "喫煙" in blob and ("推奨" in blob or "危険" in stem):
            return "喫煙は火気となり引火の危険がある。"
        if "第6類" in blob or ("類" in blob and "変" in blob):
            return "喫煙は火気となり引火の危険があるが、危険物の類別は変わらない。"
        if "指定数量" in blob and "増" in blob:
            return "指定数量は物質ごとの基準であり、喫煙で増えるわけではない。"
        if "水溶性" in blob:
            return "水溶性の有無は物質の性質であり、喫煙とは無関係である。"
        if "免状" in blob and "失効" in blob:
            return "免状の失効と火気管理は別の論点である。"

    if stem.startswith("給油取扱所") or (
        "給油取扱所" in stem and "正しい" in stem
    ):
        if "免状" in core or "交付" in core:
            return "給油取扱所は危険物を給油する取扱所である。"
        if "屋内貯蔵" in core:
            return "屋内貯蔵所は貯蔵所に分類される。"
        if "移動タンク" in core:
            return "移動タンク貯蔵所は貯蔵所に分類される。"
        if "移送" in core:
            return "移送取扱所は取扱所の一種である。"

    if stem.startswith("一般取扱所") or (
        "一般取扱所" in stem and "正しい" in stem
    ):
        if "免状" in core:
            return "一般取扱所は危険物を取り扱う施設の名称である。"
        if "住宅" in core:
            return "一般取扱所は取扱所の一種である。"
        if "屋外タンク" in core:
            return "屋外タンク貯蔵所は貯蔵所に分類される。"
        if "計算" in core:
            return "指定数量の計算式ではなく、施設の種類名である。"

    if "貯蔵所" in stem and "正しい" in stem and "について" in stem:
        facility = stem.split("について")[0].strip()
        if "移送取扱所" in core or ("配管" in core and "移送" in core):
            return f"{facility}は貯蔵所であり、移送取扱所ではない。"
        if "給油取扱所" in core or ("給油" in core and "自動車" in core):
            return f"{facility}は貯蔵所であり、給油取扱所ではない。"
        if "免状" in core:
            return f"{facility}は危険物施設の名称であり、免状ではない。"
        if "受験" in core or "会場" in core:
            return f"{facility}は施設の種類名であり、試験会場ではない。"
        if "試験" in core and ("科目" in core or "区分" in core):
            return f"{facility}は施設の種類名である。"
        if "燃焼範囲" in core:
            return f"{facility}は危険物を貯蔵する施設である。"
        if "単位" in core or "計算式" in core:
            return f"{facility}は施設の種類名である。"
        if "交付" in core or "窓口" in core:
            return f"{facility}は施設名称であり、免状交付窓口ではない。"
        if "販売" in core and "取扱所" in core:
            return f"{facility}は貯蔵所であり、販売取扱所ではない。"

    if "火災予防" in stem and "第4類" in stem:
        if "排水" in core or "下水" in core:
            return "漏えい物を排水溝へ流すと火災・環境汚染の危険がある。"
        if "裸火" in core:
            return "裸火による蒸気確認は引火の危険がある。"
        if "接地" in core and "不要" in core:
            return "接地は静電気対策として重要である。"
        if "加熱" in core or "開放" in core:
            return "加熱や開放は可燃性蒸気を増やす危険がある。"

    if "セルフ" in stem or "自ら給油" in stem:
        if "第4類" in core and "関係" in core and "ない" in core:
            return "セルフ式でもガソリン等の第4類危険物を扱う。"
        if "火気" in core or "裸火" in core:
            return "給油時の火気使用は引火の危険がある。"
        if "免状" in core and "関係" in core and "ない" in core:
            return "危険物取扱者制度と関係する場合がある。"
        if "安全" in core and "不要" in core:
            return "セルフ式でも監視・安全確保が必要である。"

    if "保安距離" in stem:
        if "試験" in blob or "会場" in blob:
            return "保安距離は周囲の保安対象物との距離であり、試験会場までの距離ではない。"
        if "通勤" in blob:
            return "取扱者の通勤距離と保安距離は別である。"
        if "色" in blob and "容器" in blob:
            return "容器の色と保安距離は無関係である。"
        if "販売" in blob or "店" in blob:
            return "販売店までの距離と保安距離は別である。"
        if "製造会社" in core or ("消火器" in core and "会社" in core):
            return "保安距離は火災・爆発時の周囲影響を抑える位置基準である。"
        if "価格" in core:
            return "保安距離は施設配置の位置基準であり、価格決定とは無関係である。"
        if "年齢" in core:
            return "取扱者の年齢確認とは無関係である。"
        if "味" in core:
            return "危険物の性質確認は試験や官能検査では行わない。"
        if "色" in core or "文字" in core:
            return "保安距離は周囲施設への影響を抑えるための距離である。"
        if "受験" in core:
            return "試験制度とは無関係である。"

    if "保有空地" in stem:
        if "捨て" in core or "投棄" in core:
            return "保有空地は延焼防止・消火活動のために確保する空地である。"
        if "器具" in core or "発火点" in core:
            return "発火点を測る器具の名称ではない。"
        if "指定数量" in core:
            return "指定数量は危険物の数量基準である。"
        if "試験" in core:
            return "保有空地は施設周囲に確保する空地である。"
        if "におい" in core or "臭" in core:
            return "施設周囲の安全確保が目的である。"
        if "名称" in core:
            return "施設の名称変更とは無関係である。"

    if "漏えい" in stem or ("火災" in stem and "対応" in stem) or "流出" in stem:
        if "ためる" in blob or "滞留" in blob:
            return "可燃性蒸気をためると引火の危険が高まる。"
        if "放置" in blob:
            return "漏えいや火災は放置せず、応急措置と通報が必要である。"
        if "知らせず" in blob or ("周囲" in blob and "作業" in blob):
            return "漏えい・流出時は周囲への周知や関係機関への通報が必要である。"
        if "下水" in blob or "排水" in blob or ("流" in blob and "なら" in blob):
            return "流出物を下水へ流すと火災・環境汚染の危険がある。"
        if "火気" in blob or "裸火" in blob:
            return "火気を近づけると引火・爆燃の危険がある。"

    if "避難設備" in stem:
        if "指定数量" in core:
            return "避難設備は火災時の安全な避難を助ける設備である。"
        if "免状" in core or "印刷" in core:
            return "免状の交付・印刷とは無関係である。"
        if "販売" in core or "レジ" in core:
            return "危険物販売のための設備ではない。"
        if "蒸気" in core:
            return "可燃性蒸気を発生させる設備ではない。"

    if "消火設備" in stem and "警報設備" in stem:
        if "レジ" in blob or ("販売" in blob and "レジ" in blob):
            return "消火・警報の設備であり、販売用のレジではない。"
        if "免状" in blob and "種類" in blob:
            return "施設設備の名称であり、免状の種類ではない。"
        if "味" in blob and "確認" in blob:
            return "火災対応の設備であり、官能確認の設備ではない。"
        if "単位" in blob and "指定数量" in blob:
            return "指定数量の数量基準と、設備の名称は別である。"

    if "消火設備" in stem:
        if "免状" in blob:
            return "消火設備は火災時の消火のための設備である。"
        if "指定数量" in blob or "装置" in blob:
            return "指定数量を変える装置ではない。"
        if "取扱基準" in blob:
            return "消火設備があっても取扱いの基準が不要になるわけではない。"
        if "設置してはならない" in blob:
            return "火災時の初期消火のために消火設備が必要となる。"
        if "水" in blob and ("だけ" in blob or "必ず" in blob):
            return "第4類危険物でも水消火だけで足りるとは限らない。"
        return ""

    if "警報設備" in stem or ("火災" in stem and "知らせ" in stem and "設備" in stem):
        if "避難" in blob:
            return "避難設備は火災時の避難を助ける設備であり、火災知らせ設備ではない。"
        if "指定数量" in blob:
            return "指定数量は数量基準であり、火災を知らせる設備の名称ではない。"
        if "販売" in blob:
            return "販売設備は法令上の設備区分ではない。"
        if "価格" in blob:
            return "警報設備は火災等の異常を知らせる設備である。"
        if "飲用" in blob:
            return "危険物を飲用可能にする設備ではない。"
        if "免状" in blob or "印刷" in blob:
            return "免状の交付・印刷とは無関係である。"

    if "貯蔵所" in stem and "違い" in stem:
        if "免状" in blob and "種類" in blob:
            return "いずれも施設の種類であり、免状の種類ではない。"
        if "計算" in blob or ("式" in blob and "指定数量" in blob):
            return "指定数量の計算方法ではなく、貯蔵施設の区分である。"
        if "給油" in blob and "別名" in blob:
            return "給油取扱所は取扱所の一種であり、貯蔵所の別名ではない。"
        if "消火器" in blob and "種類" in blob:
            return "貯蔵施設の名称であり、消火器の種類ではない。"
        if "試験" in blob and "会場" in blob:
            return "危険物施設の名称であり、試験会場ではない。"
        if "販売" in blob and "別名" in blob:
            return "販売取扱所は取扱所の一種であり、貯蔵所の別名ではない。"
        if "単位" in blob and "指定数量" in blob:
            return "指定数量の数量基準と、施設区分は別である。"
        if "第6類" in blob and "だけ" in blob:
            return "第4類など多くの危険物を扱う貯蔵施設もある。"

    if "地下タンク" in stem:
        if "放出" in blob or ("地中" in blob and "自由" in blob):
            return "危険物を地中へ放出してはならない。"
        if "裸火" in blob and ("漏" in blob or "確認" in blob):
            return "漏えい確認に裸火を用いると引火・爆燃の危険がある。"
        if "飲" in blob:
            return "危険物を飲んではならない。"
        if "標識" in blob and "漏" in blob and "不要" in blob:
            return "標識があっても漏えい対策は必要である。"
        if "不燃" in blob:
            return "地下タンク貯蔵所でも引火性液体等の漏えい対策が重要である。"
        if "免状" in blob and "不要" in blob:
            return "漏えい管理と免状制度は別の論点である。"
        if "指定数量" in blob and ("存在" in blob or "ない" in blob):
            return "指定数量は施設管理の基準であり、漏えい管理の理由とは別である。"

    if "危険物法令" in stem and "区別" in stem:
        if "食品" in blob:
            return "危険物標識の表示と、食品表示は別の制度である。"
        if "水溶性" in blob and "免状" in blob:
            return "物質の水溶性と、免状番号は別の概念である。"
        if "消火器" in blob and "受験" in blob:
            return "消火器の表示色と、受験番号は別である。"
        if "味" in blob and "価格" in blob:
            return "危険物の官能確認や価格決定は、法令学習の区別点ではない。"

    if "第4類" in stem and ("注意" in stem or "自然" in stem):
        if "歓迎" in blob or ("火気" in blob and "歓迎" in blob):
            return "第4類施設では火気厳禁が原則であり、火気歓迎は不適切である。"
        if "下水" in blob or "放流" in blob:
            return "危険物を下水へ流してはならない。"
        if "滞留" in blob and "推奨" in blob:
            return "可燃性蒸気の滞留は火災予防上避けるべきである。"
        if "喫煙" in blob and "推奨" in blob:
            return "第4類施設では喫煙・火気は危険である。"

    if "第4類" in stem and "開放" in stem and "放置" in stem:
        if "免状" in blob and ("書換" in blob or "自動" in blob):
            return "容器開放と免状書換えは無関係である。"
        if "酸素" in blob and ("なく" in blob or "完全" in blob):
            return "開放放置は可燃性蒸気の滞留を助長するが、酸素を完全になくすわけではない。"
        if "不燃" in blob:
            return "引火性液体が不燃性になるわけではない。"
        if "指定数量" in blob and "減" in blob:
            return "指定数量は物質ごとの基準であり、放置で減るわけではない。"

    if "掲示" in stem and "第4類" in stem:
        if "裸火" in core:
            return "第4類危険物施設では裸火使用は危険である。"
        if "喫煙" in core:
            return "喫煙は火気となり引火の危険がある。"
        if "水中" in core:
            return "第4類は引火性液体であり、すべて水中保管するものではない。"
        if "滞留" in core or "蒸気" in core:
            return "可燃性蒸気の滞留を防ぐ換気が重要である。"

    if "貯蔵" in stem and "適切" in stem:
        if "放置" in blob or ("漏" in blob and "放置" in blob):
            return "漏えいは放置せず適切に処理しなければならない。"
        if "開放" in blob:
            return "容器を開放して保管するのは火災・漏えいの危険がある。"
        if "ためる" in blob or ("蒸気" in blob and "ため" in blob):
            return "可燃性蒸気をためると引火の危険が高まる。"
        if "加熱" in blob or "日光" in blob:
            return "直射日光での加熱は引火・爆燃の危険がある。"

    if "貯蔵" in stem and "取扱" in stem and question_ask_mode(stem) == "most_correct":
        if "同一" in core or "火気" in core or "直射日光" in core:
            return "危険物は性質に応じた貯蔵・取扱いが必要である。"

    if "貯蔵所" in stem and "種類" in stem:
        if "取扱所" in core:
            if "一般取扱所" in core:
                return "一般取扱所は危険物の取扱いを行う施設であり、貯蔵所ではない。"
            if "移送取扱所" in core:
                return "移送取扱所は移送に伴う取扱いを行う施設である。"
            if "販売取扱所" in core:
                return "販売取扱所は販売に伴う取扱いを行う施設である。"
            if "給油取扱所" in core:
                return "給油取扱所は給油に伴う取扱いを行う施設であり、貯蔵所ではない。"
            return "本問が問う貯蔵所の種類には該当しない。"

    if "取扱所" in stem and "種類" in stem:
        if "貯蔵所" in core:
            if "屋内貯蔵所" in core:
                return "屋内貯蔵所は建物内で危険物を貯蔵する施設である。"
            if "屋外タンク" in core:
                return "屋外タンク貯蔵所はタンクによる屋外貯蔵を行う施設である。"
            if "移動タンク" in core:
                return "名称に『貯蔵所』とあるが、取扱所ではなく貯蔵所に分類される。"
            if "地下タンク" in core:
                return "地下タンク貯蔵所は地下タンクによる貯蔵施設である。"
            return "本問が問う取扱所の種類には該当しない。"

    if "引火点" in stem:
        if "免状" in blob:
            return "引火点は液体の引火に関する温度の概念である。"
        if "浮" in blob or "沈" in blob:
            return "液体の比重により浮沈が決まり、引火点とは別である。"
        if "蒸気比重" in blob or ("蒸気" in blob and "空気" in blob):
            return "蒸気比重は蒸気と空気の重さの比である。"
        if "凝固点" in blob or "沸騰" in blob or "沸点" in blob:
            return "沸点は液体が気体になる温度であり、引火点とは別である。"
        if ("火源" in blob and "ない" in blob) or "発火点" in blob:
            return "火源なしで燃え始める温度は発火点の概念である。"
        if "密度" in blob or "ゼロ" in blob:
            return "引火点は温度の概念であり、密度がゼロになる温度ではない。"
        if "溶解" in blob or "pH" in blob or "酸性" in blob:
            return "pHは水溶液の酸性度の指標であり、引火点とは別である。"
        if "固体" in blob and ("液体" in blob or "融" in blob):
            return "融点は固体が液体になる温度であり、引火点とは別である。"

    if "発火点" in stem:
        if "運搬" in core or "距離" in core:
            return "発火点は火源なしで自然発火する最低温度である。"
        if "引火点" in core or ("火源" in core and "引火" in core):
            return "火源を要する引火の最低温度は引火点である。"
        if "溶け" in core or "溶解" in core:
            return "溶解温度は別の概念である。"
        if "浮" in core:
            return "浮沈は比重の問題であり、発火点とは無関係である。"

    if "引火" in stem and "発火" in stem and "違い" in stem:
        if "同じ" in blob or "完全" in blob:
            return "引火は火源を要し、発火は火源なしで燃え始める点で区別される。"
        if "消火設備" in blob:
            return "引火・発火は燃焼現象の概念であり、消火設備の種類ではない。"
        if "指定数量" in blob or "免状" in blob:
            return "引火・発火は燃焼開始の概念であり、数量基準や免状ではない。"
        if "溶け" in blob or ("浮" in blob and "水" in blob):
            return "引火・発火は燃焼現象の概念であり、溶解や浮力ではない。"

    if "自然発火" in stem:
        if "免状" in blob:
            return "自然発火は外部火源なしで発火する現象であり、免状取得ではない。"
        if "指定数量" in blob and "超" in blob:
            return "指定数量超過だけで必ず自然発火するわけではない。"
        if "溶解" in blob or "溶け" in blob or "水溶性" in blob:
            return "自然発火は酸化熱の蓄積による現象であり、水溶性とは別である。"
        if "蒸気比重" in blob:
            return "自然発火と蒸気比重は別の概念である。"

    if "酸化熱" in stem or ("外部火源" in stem and "燃え" in stem):
        if "中和" in blob:
            return "中和は酸とアルカリの化学反応であり、自然発火の現象ではない。"
        if "沸騰" in blob:
            return "沸騰は液体が気体になる現象であり、自然発火とは別である。"
        if "融解" in blob:
            return "融解は固体が液体になる物理変化であり、自然発火とは別である。"

    if "対流" in stem:
        if "免状" in blob:
            return "対流は液体や気体の移動による熱伝達であり、免状とは無関係である。"
        if "指定数量" in blob:
            return "対流は熱の伝わり方の概念であり、指定数量とは無関係である。"
        if "固体内部" in blob or ("固体" in blob and "内部" in blob):
            return "固体内部での伝達は主に熱伝導の説明に近い。"
        if "真空中" in blob or ("電磁波" in blob and "だけ" in blob):
            return "真空中の電磁波による伝達は放射の説明に近い。"

    if "放射" in stem and ("熱" in stem or "伝" in stem):
        if "指定数量" in blob:
            return "放射は電磁波による熱伝達であり、指定数量とは無関係である。"
        if "流れ" in blob or ("液体" in blob and "流" in blob):
            return "液体の流れによる伝達は対流の説明に近い。"
        if "溶け" in blob or "溶解" in blob:
            return "放射は熱の伝わり方の概念であり、溶解とは別である。"
        if "固体内部" in blob or ("固体" in blob and "内部" in blob):
            return "固体内部での伝達は主に熱伝導の説明に近い。"

    if "融点" in stem:
        if "発火" in blob and "火源" in blob:
            return "火源なしで発火する温度は発火点の説明に近い。"
        if "蒸気比重" in blob:
            return "融点は固体が液体になる温度であり、蒸気比重とは別である。"
        if "沸騰" in blob or "沸点" in blob:
            return "融点は固体→液体、沸点は液体→気体の境界温度である。"
        if "引火" in blob:
            return "可燃性蒸気が引火する温度は引火点の概念である。"

    if "気体" in stem and ("特徴" in stem or "正しい" in stem):
        if "形" in blob and "体積" in blob and "保" in blob:
            return "一定の形と体積を保つのは主に固体の特徴である。"
        if "沈" in blob or ("水" in blob and "沈" in blob):
            return "気体の特徴は状態の話であり、水への浮沈ではない。"
        if "第4類" in blob:
            return "気体は物質の状態であり、第4類危険物に限られない。"
        if "不燃" in blob:
            return "気体にも可燃性のあるものがある。"

    if "窒息消火" in stem:
        if "加熱" in blob:
            return "加熱は可燃性蒸気を増やし、窒息消火の例ではない。"
        if "酸素" in blob and ("送" in blob or "供給" in blob or "大量" in blob):
            return "酸素供給は燃焼を助けるため、窒息消火の例ではない。"
        if "火花" in blob:
            return "火花は着火源となり、窒息消火の例ではない。"
        if "追加" in blob or ("可燃物" in blob and "追加" in blob):
            return "可燃物を増やすと燃焼が拡大し、窒息消火の例ではない。"

    if "燃焼範囲" in stem:
        if "沈" in blob or ("水" in blob and ("沈" in blob or "比重" in blob)):
            return "上限界は可燃性蒸気濃度の概念であり、液体の浮沈とは別である。"
        if "沸騰" in blob or ("沸点" in blob and "温度" in blob):
            return "上限界は混合濃度の限界であり、沸点とは別である。"
        if "免状" in blob:
            return "燃焼範囲は混合濃度の概念であり、免状番号ではない。"
        if "自然発火" in blob:
            return "濃度が下限より低いときは燃焼しにくく、自然発火とは別の問題である。"
        if "指定数量" in blob:
            return "指定数量は施設管理の数量基準であり、混合濃度とは別である。"
        if "最大" in blob or "爆発" in blob:
            return "最大爆発力は適当な濃度付近であり、下限より低いときは該当しない。"
        if "液体" in blob and "なる" in blob:
            return "気化など状態変化の問題であり、可燃性蒸気の混合濃度とは別である。"
        if "固体" in blob and "なる" in blob:
            return "混合状態の話であり、必ず固体になるわけではない。"
        if "薄" in blob or "爆発" in blob:
            return "混合気が薄すぎれば燃焼しにくく、爆発力が常に最大になるわけではない。"
        if "濃" in stem and "不燃" in blob:
            return "濃度が上限より高いときも、不燃性になるわけではない。"
        if "高い" in stem and "自然発火" in blob:
            return "濃度が高い場合でも、自然発火とは別の問題である。"
        if "重さ" in blob or "単位" in blob:
            return "燃焼範囲は可燃性蒸気と空気の混合濃度の範囲を表す。"
        if "0％" in blob or "100％" in blob or "常に" in blob:
            return "物質ごとに燃焼範囲の上下限は異なる。"
        if "色" in blob:
            return "燃焼範囲は物質の色では決まらない。"
        if "溶解" in blob or ("溶け" in blob and "水" in blob):
            return "上限界は混合濃度の限界であり、溶解とは別である。"
        if "蒸気比重" in blob:
            return "燃焼範囲は混合濃度の概念であり、蒸気比重とは別である。"
        if "凝固" in blob or "凍り" in blob:
            return "凝固点は温度の概念であり、燃焼範囲の限界とは異なる。"

    if "沸点" in stem and ("標高" in stem or "外圧" in stem or "下が" in stem):
        if "不燃" in blob:
            return "沸点の変化は外圧の影響であり、不燃性の問題ではない。"
        if "第4類" in blob:
            return "沸点と危険物の類別は別の問題である。"
        if "指定数量" in blob:
            return "沸点の変化と指定数量は無関係である。"
        if "色" in blob:
            return "沸点は温度の概念であり、色の変化とは別である。"

    if "沸点" in stem:
        if "密度" in blob or "ゼロ" in blob:
            return "沸点は液体が沸騰し始める温度である。"
        if "引火" in blob:
            return "引火点は火源による引火の最低温度である。"
        if "色" in blob:
            return "沸点は温度の概念であり、色の変化だけを示すものではない。"
        if "発火" in blob or "固体" in blob or ("燃焼" in blob and "始" in blob):
            return "発火点は火源なしで自然発火する温度に近い概念である。"

    if "圧力" in stem and "沸点" in stem:
        if "関係" in core:
            return "外圧が低いと沸点は下がる傾向があり、圧力と沸点は関係する。"
        if "固体" in core:
            return "沸点は液体が沸騰する温度であり、凝固点とは別である。"
        if "0 ℃" in core or "0℃" in core:
            return "沸点は物質・外圧により異なり、必ず0 ℃ではない。"
        if "無限" in core:
            return "沸点が無限大になるわけではない。"

    if "蒸発" in stem:
        if "酸性" in core:
            return "蒸発は液体表面から気体になる現象である。"
        if "密度" in core:
            return "蒸発は状態変化であり、密度変化だけを指すものではない。"
        if "酸素" in core and "放出" in core:
            return "蒸発は液体から気体への変化であり、酸素放出とは別である。"
        if "燃焼" in core or ("燃え" in core and "固体" in core):
            return "蒸発は液体が気体になる現象であり、燃焼とは別である。"

    if "液体の比重" in stem or ("比重" in stem and "液体" in stem):
        if "不燃" in blob or "不燃" in core:
            return "比重の大小と燃焼性は別の問題である。"
        if "蒸気" in blob and "空気" in blob:
            return "液体の比重と蒸気比重は別の概念として覚える。"
        if "発火" in blob:
            return "比重が小さくても引火性液体は燃えるおそれがある。"
        if "溶け" in blob or "溶け" in core:
            return "比重と水溶性は同じ意味ではない。"
        if "反応" in core or "速度" in core:
            return "液体の比重は水を基準とした重さの比である。"
        if "酸素" in core:
            return "比重は物質の重さの比であり、酸素濃度ではない。"
        if "燃え" in core or "温度" in core:
            return "燃え始める温度は引火点などの概念である。"

    if "水より" in stem and "比重" in stem:
        if "蒸気比重" in core or ("液比重" in core and "蒸気" in core):
            return "液体の比重と蒸気比重は別の概念として扱う。"
        if "溶け" in core or "水溶性" in core:
            return "水に浮くことと水に溶けることは別である。"
        if "燃え" in core and "ない" in core:
            return "比重が小さくても引火性液体は燃えるおそれがある。"
        if "酸素" in core:
            return "比重と酸素放出の性質は無関係である。"

    if "水溶性" in stem and "第4類" in stem:
        if "非水溶性" in core or "軽油" in core or "ガソリン" in core or "灯油" in core or "潤滑油" in core:
            return "アセトンは水溶性の第一石油類として整理される。"
        if "引火" in core:
            return "アルコール類のように水に溶けやすくても引火危険がある。"
        if "浮く" in core or "沈む" in core:
            return "液体の比重により、水に浮く第4類危険物もある。"
        if "すべて" in core and "溶け" in core:
            return "水溶性と非水溶性の両方がある。"
        if "酸素" in core:
            return "水溶性と酸素放出の性質は別である。"

    if "分子" in stem and "正しい" in stem:
        if "免状" in core:
            return "分子は原子が結びついてできた粒子である。"
        if "比重" in core:
            return "分子は物質を構成する粒子であり、比重の単位ではない。"
        if "光" in core:
            return "分子は物質の粒子であり、光ではない。"
        if "音" in core:
            return "分子は物質の粒子であり、音ではない。"

    if "化学反応式" in stem:
        if "避難" in core:
            return "化学反応式は化学反応を化学式で表したものである。"
        if "色" in core:
            return "反応前後の物質関係を示すものである。"
        if "器具" in core or "体積" in core:
            return "化学反応式は計算や記述のための表現である。"
        if "住所" in core:
            return "施設の表示とは別の化学の概念である。"

    if "熱量" in stem and ("cal" in stem or "温度" in stem):
        if "質量" in core and "考慮" in core:
            return "熱量は質量×温度上昇で求める。"
        if "温度" in core and "掛け" in core:
            return "100 gを10 ℃上げるには100×10が必要である。"
        if "計算結果" in core:
            return "正しくは100×10＝1,000 calである。"
        if "水1 g" in core or "1 cal" in core:
            return "1 calは水1 gを1 ℃上げるときの熱量である。"

    if ("第4類" in stem and "消火" in stem) or "第4類危険物火災" in stem:
        if "下水" in blob or "排水" in blob:
            return "下水への流出は火災・環境汚染の危険がある。"
        if "加熱" in blob:
            return "加熱は可燃性蒸気を増やし危険を拡大する。"
        if "かくはん" in blob or "攪拌" in blob or "かき混" in blob:
            return "かき混ぜは燃焼面積を増やし、火災拡大のおそれがある。"
        if "酸素" in blob and ("供給" in blob or "送" in blob or "大量" in blob):
            return "酸素を供給すると燃焼が助長され、消火の考え方に反する。"
        if "火気" in blob or "裸火" in blob:
            return "火気を近づけると引火・爆燃の危険がある。"

    if "除去消火" in stem:
        if "火花" in blob:
            return "火花は着火源となり、除去消火の方法ではない。"
        if "酸素" in blob and ("送" in blob or "供給" in blob or "大量" in blob):
            return "酸素を送り込むと燃焼が助長される。"
        if "ためる" in blob or ("蒸気" in blob and "ため" in blob):
            return "可燃性蒸気をためると引火の危険がある。"
        if "加熱" in blob:
            return "加熱は燃焼を助けるため、除去消火の方法ではない。"
        if "促進" in core:
            return "除去消火は可燃物を取り除いて燃焼を止める方法である。"
        if "冷却" in core or "温度" in core:
            return "温度を下げるのは冷却消火である。"
        if "窒息" in core or "酸素" in core:
            return "酸素を断つのは窒息消火である。"
        if "蒸気" in core and "増" in core:
            return "可燃性蒸気を増やすのは火災を拡大させる。"

    if "取り除" in stem and "燃焼" in stem:
        if "窒息" in blob:
            return "窒息消火は酸素供給を断つ方法であり、可燃物除去とは異なる。"
        if "冷却" in blob:
            return "冷却消火は温度を下げる方法であり、可燃物除去とは異なる。"
        if "自然発火" in blob:
            return "自然発火は現象の名称であり、消火方法ではない。"

    if "連鎖反応" in stem and ("抑" in stem or "消火" in stem):
        if "除去" in blob or "取り除" in blob:
            return "除去消火は可燃物を取り除く方法である。"
        if "冷却" in blob:
            return "冷却消火は温度を下げる方法である。"
        if "混触" in blob:
            return "危険物の混触は火災原因となり得るが、抑制消火ではない。"
        if "加熱" in blob:
            return "加熱消火という消火方法は存在しない。"
        if "販売" in blob or "希釈" in blob:
            return "危険物の販売方法であり、消火の考え方とは無関係である。"
        if "指定数量" in blob and "計算" in blob:
            return "指定数量の計算方法であり、消火の原理とは無関係である。"

    if "比熱" in stem and "小さい" in stem:
        if "無限" in blob:
            return "必要な熱量が無限大になるわけではない。"
        if "浮" in blob:
            return "比重の大小と比熱は別の物理量である。"
        if "不燃" in blob:
            return "比熱の大小と燃焼性は別の問題である。"
        if "酸素" in blob and "放出" in blob:
            return "比熱と酸素放出性は別の性質である。"

    if "冷却消火" in stem:
        if "ためる" in blob or ("蒸気" in blob and "ため" in blob):
            return "可燃性蒸気をためると引火の危険が高まり、冷却消火の例ではない。"
        if "火花" in blob:
            return "火花は着火源となり、冷却消火の例ではない。"
        if "下水" in blob or "排水" in blob:
            return "下水への流出は火災・環境汚染の危険がある。"
        if "酸素" in blob and ("送" in blob or "供給" in blob or "大量" in blob):
            return "酸素供給は燃焼を助けるため、冷却消火の例ではない。"
        if "可燃物" in blob and "増" in blob:
            return "冷却消火は燃焼物の温度を下げる方法である。"
        if "静電気" in blob:
            return "静電気は着火源となり得るが、冷却消火の説明ではない。"
        if "酸素" in blob:
            return "酸素濃度を高めるのは窒息消火・除去消火とは別の論点である。"

    if "抑制消火" in stem:
        if "密度" in core:
            return "抑制消火は燃焼の連鎖反応を抑える方法である。"
        if "燃焼範囲" in core:
            return "燃焼範囲を広げる方法ではなく、連鎖反応を抑える。"
        if "温度計" in core:
            return "抑制消火は消火の原理の一つである。"
        if "可燃物" in core and "増" in core:
            return "可燃物を増やすと燃焼が拡大する。"

    if "比熱" in stem:
        if "溶解" in core:
            return "比熱は温度を上げる熱量の指標であり、水への溶解度ではない。"
        if "色" in core:
            return "比熱は色の濃さとは無関係である。"
        if "燃え" in core or "温度を表す" in core:
            return "比熱は引火点・発火点のような燃焼開始温度ではない。"
        if "蒸気" in core or "空気より" in core:
            return "比熱は1 gを1 ℃上げる熱量の指標であり、蒸気比重とは別である。"

    if "化学変化" in stem:
        if "物理変化" in blob or "形が変わる" in blob:
            return "物質の性質が変わらない変化は物理変化である。"
        if "形が変わる" in blob or "割れ" in blob:
            return "割れて形状だけが変わる変化は、化学成分が変わらない物理変化である。"
        if "状態変化" in blob:
            return "固液気の状態が変わるだけでは通常、物理変化である。"
        if "溶解" in blob:
            return "溶解は通常、物理変化として扱う。"
        if "比重" in blob or "浮" in blob:
            return "比重は液体の浮沈に関する値であり、化学変化の特徴ではない。"
        if "指定数量" in blob:
            return "指定数量の変更は法令手続きの話であり、化学変化の特徴ではない。"
        if "免状" in blob:
            return "免状の再交付は行政手続きであり、化学変化の特徴ではない。"

    if "物理変化" in stem:
        if "燃焼" in blob or "さび" in blob or "灰" in blob:
            return "燃焼やさびは化学成分が変わる化学変化である。"

    if "燃焼" in stem and "酸化" in stem:
        if "関係" in blob and "ない" in blob:
            return "燃焼は酸素と結びつく急激な酸化反応と考えられる。"
        if "免状" in blob or "書換" in blob:
            return "燃焼は化学反応の概念であり、免状書換えではない。"
        if "溶け" in blob or "水溶性" in blob:
            return "燃焼と溶解は別の現象である。"
        if "指定数量" in blob or "計算" in blob:
            return "指定数量の計算方法ではない。"

    if "密度" in stem and "説明" in stem:
        if "色" in blob:
            return "密度は単位体積あたりの質量であり、色を表す値ではない。"
        if "温度" in blob and "だけ" in blob:
            return "密度は質量÷体積で表す物理量である。"

    if "密度" in stem:
        if "750" in blob:
            return "750 gは密度0.75の値そのものであり、質量＝密度×体積で300 gとなる。"
        if "533" in blob:
            return "400÷0.75のように密度で割る計算は誤りである。"
        if "400 g" in blob and ("体積" in core or "そのまま" in core):
            return "質量は密度×体積で求め、体積をそのまま質量にしてはならない。"
        if "温度" in blob:
            return "密度は質量÷体積で求め、温度だけでは決まらない。"
        if "時間" in blob:
            return "密度は質量÷体積で求め、時間は関係しない。"
        if "体積÷" in blob or ("÷質量" in blob and "体積" in blob):
            return "密度は質量÷体積で求める。分母分子を逆にしない。"
        if "＋" in blob or "質量＋" in blob or "＋体積" in blob:
            return "密度は質量と体積の商であり、両者を足す計算ではない。"
        if "500÷400" in core or "400÷500" in core:
            return "密度は質量÷体積で求める。分母分子を逆にしない。"
        if "計算結果" in core:
            return "正しくは400 g÷500 cm³＝0.8 g/cm³である。"
        if "足" in core:
            return "密度は質量と体積の商であり、両者を足す計算ではない。"
        if "割っていない" in core:
            return "密度は質量÷体積で求める。"
        if "1,000÷800" in core or "800÷" in core or "÷400" in core:
            return "密度は体積で質量を割る。分子と分母を逆にしない。"
        if "密度の数値" in core or "誤って" in core:
            return "質量＝密度×体積の式を正しく適用して求める。"
        if "近似" in core or "÷0.75" in core:
            return "400÷0.75のように密度で割る計算は誤りである。"

    if "パーセント濃度" in stem or "質量パーセント" in stem:
        if "計算結果" in core:
            return "正しくは20 g÷200 g×100＝10 %である。"
        if "10 %" in core or "10％" in core:
            return "溶質20 g÷溶液200 g×100で10 %となる。"
        if "比が違" in core or "溶質" in core:
            return "濃度は溶質の質量を溶液全体の質量で割って求める。"

    if "三態" in stem:
        if "pH" in core or "酸性" in core or "アルカリ" in core:
            return "物質の三態は固体・液体・気体の状態である。"
        if "甲種" in core or "乙種" in core or "丙種" in core or (
            "取扱者" in core and "区分" in core
        ):
            return "甲種・乙種・丙種は危険物取扱者免状の区分である。"
        if "製造所" in core or "貯蔵所" in core or "取扱所" in core or (
            "施設" in core and "区分" in core
        ):
            return "製造所・貯蔵所・取扱所は危険物施設の区分である。"
        if "可燃物" in core or "火気" in core or "燃焼" in core or "消火" in core:
            return "可燃物・火気・水は燃焼三要素や消火に関係する語句である。"

    if "酸" in stem and "性質" in stem:
        if "第4類" in core:
            return "酢酸など第4類に該当する酸もあるが、すべてが第4類ではない。"
        if "不燃" in core or ("性質" in core and "異なる" in core):
            return "酸の性質は物質により異なり、引火性のあるものもある。"
        if "金属" in core:
            return "酸は水溶液中で水素イオンを生じる化合物の概念である。"
        if "アルカリ" in core or ("pH" in core and "大" in core):
            return "pH7より大きいのは一般にアルカリ性である。"

    if "アルカリ性" in stem:
        if "pH" in core and ("0" in core or "限ら" in core):
            return "アルカリ性は一般にpH7より大きい水溶液である。"
        if "第4類" in core:
            return "アルカリ性と危険物の類別は別の概念である。"
        if "酸素" in core and "放出" in core:
            return "酸素放出性（酸素系第3類）とは別である。"
        if "可燃性蒸気" in core or "蒸気" in core:
            return "アルカリ性はpHの概念であり、必ず可燃性蒸気を発生するわけではない。"

    if "中和反応" in stem or ("打ち消" in stem and "反応" in stem):
        if "破砕" in blob or "粉々" in blob:
            return "中和は酸とアルカリが互いの性質を打ち消す反応である。"
        if "融解" in blob:
            return "融解は固体が液体になる物理変化であり、中和反応ではない。"
        if "酸化" in blob and "還元" not in blob:
            return "酸化は酸素との結合などの反応であり、中和とは別である。"
        if "還元" in blob:
            return "還元は酸素を失うなどの反応であり、中和とは別である。"
        if "蒸発" in blob or "蒸発" in core:
            return "蒸発は状態変化であり、中和反応ではない。"
        if "指定数量" in blob or "指定数量" in core:
            return "指定数量の計算方法ではない。"
        if "浮" in blob or "浮" in core:
            return "浮沈は比重の問題であり、中和とは別である。"

    if "温度" in stem and "熱量" in stem:
        if "免状" in core:
            return "温度は熱さ冷たさの程度を表す物理量である。"
        if "密度" in core or ("体積" in core and "割" in core):
            return "質量÷体積は密度の説明である。"
        if "色" in core:
            return "熱量は移動・蓄積される熱エネルギーの量である。"
        if "単位" in core:
            return "温度と熱量は単位も意味も異なる。"

    if "熱容量" in stem:
        if "比熱" in blob and "説明" in blob:
            return "物質1 gあたりの場合は比熱、物体全体なら熱容量である。"
        if "蒸気比重" in blob or ("蒸気" in blob and "空気" in blob):
            return "蒸気比重は蒸気と空気の重さの比である。"
        if "引火" in blob:
            return "引火点は火源による引火の最低温度である。"
        if "面積" in blob or "貯蔵" in blob:
            return "熱容量は温度を1 ℃上げるのに必要な熱量である。"
        if "浮" in blob:
            return "浮力・比重の問題であり、熱容量とは別の物理量である。"
        if "不燃" in blob:
            return "熱容量の大小と不燃性は別の問題である。"
        if "爆発" in blob:
            return "熱容量と爆発性は別の概念である。"
        if "酸化" in blob:
            return "酸化性と熱容量は別の物理量である。"

    if "熱膨張" in stem or ("体積" in stem and "増" in stem and "温度" in stem):
        if "酸素" in blob and "放出" in blob:
            return "熱膨張は温度上昇による体積の増大現象である。"
        if "溶け" in blob or "溶解" in blob:
            return "溶解は別の現象である。"
        if "免状" in blob:
            return "温度上昇で物体が膨張する物理現象である。"
        if "燃焼" in blob:
            return "熱膨張は必ず燃焼を伴うわけではない。"
        if "還元" in blob:
            return "還元は化学反応の種類であり、体積膨張の物理現象ではない。"
        if "凝固" in blob:
            return "凝固は液体が固体になる現象であり、熱膨張とは別の変化である。"
        if "中和" in blob:
            return "中和は酸とアルカリの化学反応であり、熱膨張とは別である。"
        if "沈殿" in blob:
            return "沈殿は固体の析出現象であり、温度上昇による体積増大とは別である。"

    if "化合物" in stem and "有機" not in stem and "炭化" not in stem:
        if "標識" in core:
            return "化合物は2種類以上の元素が結びついた物質である。"
        if "単体" in core or "1種類" in core:
            return "1種類の元素だけからなるものは単体である。"
        if "避難" in core:
            return "避難設備の名称ではない。"
        if "比重" in core or "単位" in core:
            return "液体の比重を表す単位ではない。"

    if "混合物" in stem:
        if "免状" in core:
            return "混合物は複数の物質が混じったものである。"
        if "発火点" in core or "温度単位" in core:
            return "発火点や温度単位の名称ではない。"
        if "単体" in core or "1種類" in core:
            return "1種類の元素だけからなるものは単体である。"

    if "イオン" in stem or ("電気を帯び" in stem and "粒子" in stem):
        if "引火" in blob or "発火" in blob or ("温度" in blob and "燃え" in blob):
            return "イオンは電気を帯びた原子または原子団である。"
        if "分子量" in blob:
            return "分子量は分子の質量に関する値であり、イオンとは別である。"
        if "指定数量" in blob:
            return "指定数量は危険物の数量基準であり、イオンとは別である。"
        if "比重" in blob:
            return "比重は重さの比であり、イオンとは別である。"
        if "沸点" in blob:
            return "沸点は温度の概念であり、イオンとは別である。"
        if "色" in blob:
            return "イオンは電気を帯びた粒子であり、色の値ではない。"
        if "消火" in blob:
            return "消火薬剤の名称ではない。"
        if "指定数量" in core:
            return "指定数量とは別の化学概念である。"

    if "燃焼" in stem and ("化学" in stem or "説明" in stem):
        if "免状" in core:
            return "燃焼は熱や光を伴う急激な酸化反応である。"
        if "凝固" in core or "固体になる" in core:
            return "凝固は状態変化であり、燃焼ではない。"
        if "溶け" in core or "溶解" in core:
            return "溶解は別の現象である。"
        if "消滅" in core or "質量" in core:
            return "燃焼しても質量保存の法則は成り立つ。"

    if "燃焼" in stem and "酸素" in stem:
        if "関係" in core and "深" in core:
            return "酸素供給源は燃焼三要素の一つである。"
        if "関係" in core and "ない" in core:
            return "燃焼には酸素供給源が必要である。"
        if "単位" in core:
            return "指定数量の単位ではない。"
        if "不要" in core or "常に不要" in core:
            return "通常の燃焼には酸素が必要である。"

    if ("水" in stem and "消火" in stem) or "水による消火" in stem:
        if "酸素" in core and ("発生" in core or "放出" in core):
            return "水の主な消火効果は冷却である。"
        if "指定数量" in core:
            return "指定数量を変えるものではない。"
        if "引火" in core and "やす" in core:
            return "水は冷却効果により燃焼物の温度を下げる。"
        if "蒸気" in core and "増" in core:
            return "可燃性蒸気を増やすことが消火の目的ではない。"

    if "乾性油" in stem:
        if "第6類" in blob or ("酸素" in blob and "放出" in blob):
            return "乾性油を含んだ布は酸化熱の蓄積で自然発火するおそれがある。"
        if "火気" in blob and "近" in blob:
            return "自然発火の危険があるため、火気の近くで乾燥させない。"
        if "積み重" in blob or "一切" in blob or ("袋" in blob and "詰" in blob):
            return "密閉・積み重ねは酸化熱の蓄積を助長し、自然発火のおそれがある。"
        if "下水" in blob or "排水" in blob:
            return "油を含む布等を下水へ流すと火災・環境汚染の危険がある。"
        if "喫煙" in blob or ("火気" in blob and "蒸気" in blob):
            return "火気は着火源となり、自然発火リスクとあわせて重大な危険がある。"

    if "非水溶性" in stem and ("火災" in stem or "消火" in stem):
        if "溶け" in blob and ("管理不要" in blob or "不要" in blob):
            return "非水溶性液体でも引火危険があり、適切な管理が必要である。"
        if "棒状" in blob:
            return "非水溶性で水より軽い液体は棒状注水で燃焼液面を広げるおそれがある。"
        if "第6類" in blob:
            return "非水溶性引火性液体は第4類危険物として扱う。"
        if "火気" in blob and ("近" in blob or "確認" in blob):
            return "火気を近づけると引火・爆燃の危険がある。"

    if "非水溶性" in stem and ("棒状" in stem or "放射" in stem):
        if "指定数量" in blob:
            return "棒状注水でも指定数量は変わらない。"
        if "固体" in blob:
            return "水をかけても必ず固体になるわけではない。"
        if "不燃" in blob:
            return "第4類危険物が不燃性になるわけではない。"
        if ("消" in blob or "止" in blob) and "火" in blob:
            return "非水溶性で水より軽い液体は棒状注水で拡散しやすい。"
        if "必ず" in blob and "消" in blob:
            return "棒状注水は火を拡散させるおそれがあり、必ず消えるとは限らない。"
        if "蒸気比重" in blob and "ゼロ" in blob:
            return "蒸気比重は物質の性質であり、注水でゼロになるわけではない。"

    if "二酸化炭素" in stem and "消火" in stem:
        if "水溶性" in core:
            return "二酸化炭素は酸素濃度を下げる窒息効果で消火する。"
        if "火花" in core:
            return "二酸化炭素消火剤は火花を発生させるためのものではない。"
        if "指定数量" in core:
            return "指定数量を変える消火剤ではない。"
        if "可燃物" in core and "増" in core:
            return "窒息効果により燃焼を抑える消火剤である。"

    if "特殊引火物" in stem and ("特徴" in stem or "危険性" in stem or "適切" in stem):
        if "動植物油" in blob or "動植物油" in core:
            return "特殊引火物は動植物油類ではなく、別の区分に分類される。"
        if "不燃" in blob or "燃えない" in core or "不燃性" in blob:
            return "特殊引火物は引火危険が高い可燃性液体である。"
        if "10,000" in blob or "10000" in blob:
            return "特殊引火物の指定数量は50 Lである。"
        if "酸化性固体" in blob or ("酸化" in blob and "固体" in blob):
            return "酸化性固体は第1類危険物であり、特殊引火物ではない。"
        if "第1類" in core:
            return "特殊引火物は第4類危険物の中で引火危険が特に高いものである。"
        if "沈" in core or "絶対" in core:
            return "引火危険が高いが、水に沈む・燃えないとは限らない。"

    if "ジエチルエーテル" in stem:
        if "火災予防" in stem:
            if "溶け" in blob and "危険" in blob and "ない" in blob:
                return "水に溶けにくくても引火危険がある特殊引火物である。"
            if "放置" in blob:
                return "漏えいは換気・回収など適切に処理する。"
            if "加熱" in blob or ("火気" in blob and "近" in blob):
                return "火気や加熱は引火・爆燃の危険がある。"
            if "開放" in blob or ("蒸気" in blob and "発生" in blob):
                return "容器開放は可燃性蒸気を増やし危険である。"
        if "不燃" in blob or "不燃性" in blob:
            return "特殊引火物は引火危険が高い可燃性液体であり、不燃性ではない。"
        if "第二石油類" in blob or "灯油" in blob:
            return "ジエチルエーテルは特殊引火物である。"
        if "第6類" in blob:
            return "第6類ではなく第4類の特殊引火物である。"
        if "動植物油" in blob:
            return "特殊引火物は動植物油類とは別の区分に分類される。"
        if "アルコール" in blob:
            return "アルコール類ではない。"

    if "酢酸エチル" in stem:
        if "動植物油" in blob:
            return "動植物油類ではなく第一石油類に分類される。"
        if "第6類" in blob:
            return "第4類の第一石油類であり、第6類ではない。"
        if "第三石油類" in blob:
            return "第三石油類ではなく第一石油類である。"
        if "第二石油類" in blob:
            return "酢酸は第二石油類だが、酢酸エチルは第一石油類である。"

    if "アセトン" in stem and "ガソリン" in stem:
        if "10,000" in blob or "10000" in blob:
            return "アセトンは水溶性、ガソリンは非水溶性で指定数量も異なる。"
        if "不燃" in blob or "酸化性固体" in blob:
            return "どちらも第4類の引火性液体であり、不燃性や酸化性固体ではない。"
        if "第6類" in blob:
            return "どちらも第4類危険物の第一石油類に分類される。"
        if "動植物油" in blob:
            return "石油類に属し、動植物油類ではない。"

    if stem.startswith("アセトン") or (
        "アセトン" in stem and ("正しい" in stem or "分類" in stem)
    ):
        if "動植物油" in blob:
            return "アセトンは第一石油類の水溶性液体である。"
        if "第3類" in blob or "第6類" in blob:
            return "第4類危険物の第一石油類である。"
        if "第三石油類" in blob:
            return "第三石油類ではなく第一石油類である。"
        if "第二石油類" in blob:
            return "アセトンは第一石油類の水溶性液体であり、第二石油類ではない。"
        if "燃え" in blob and "ない" in blob:
            return "水に溶けても引火危険がある引火性液体である。"

    if "第二石油類" in stem and "正しい" in stem:
        if "動植物油" in blob or "大豆油" in blob or "菜種油" in blob:
            return "動植物油類は菜種油・大豆油など別の区分である。"
        if "メタノール" in blob:
            return "メタノールはアルコール類であり、第二石油類ではない。"
        if "ガソリン" in blob:
            return "ガソリンは第一石油類であり、第二石油類ではない。"
        if "ジエチル" in blob or "エーテル" in blob:
            return "ジエチルエーテルは特殊引火物である。"

    if "特殊引火物" in stem and ("組合せ" in stem or "該当" in stem):
        if "メタノール" in blob or "エタノール" in blob:
            return "メタノール・エタノールはアルコール類に分類される。"
        if "重油" in blob or "潤滑油" in blob:
            return "重油・潤滑油は第三石油類など石油類に該当する。"
        if "大豆油" in blob or "菜種油" in blob:
            return "大豆油・菜種油は動植物油類に該当する。"
        if "灯油" in blob or "軽油" in blob:
            return "灯油・軽油は第二石油類に該当する。"

    if "第4類危険物" in stem and "換気" in stem:
        if "指定数量" in blob:
            return "換気は可燃性蒸気の滞留を防ぐためであり、指定数量を変えるものではない。"
        if "免状" in blob or "発行" in blob:
            return "換気は火災予防のための措置であり、免状発行とは無関係である。"
        if "蒸気比重" in blob and "ゼロ" in blob:
            return "換気は蒸気比重の値そのものを変えるものではない。"
        if "不燃" in blob:
            return "換気は可燃性蒸気を排出するもので、物質を不燃性に変えるものではない。"

    if ("泡消火" in stem or ("泡" in stem and "消火" in stem)) and "第4類" in stem:
        if "かき混" in blob or "攪拌" in blob:
            return "第4類火災でかき混ぜると燃焼拡大のおそれがある。"
        if "酸素" in blob and ("送" in blob or "供給" in blob):
            return "酸素供給は燃焼を助けるため、泡消火の作用ではない。"
        if "下水" in blob or "排水" in blob:
            return "漏えいした危険物を下水へ流してはならない。"
        if "火気" in blob and ("近" in blob or "燃え尽" in blob):
            return "火気を近づけると引火・爆燃の危険がある。"

    if "第4類危険物" in stem and ("火災予防" in stem or "消火" in stem):
        if "酸素" in blob and "放出" in blob:
            return "第4類の引火性液体がすべて酸素を放出するわけではない。"
        if "火気" in blob and ("近" in blob or "安全" in blob):
            return "火気を近づけると引火の危険が高まる。"
        if "溶け" in blob and ("火災" in blob or "危険" in blob):
            return "水に溶けても引火危険がある第4類がある。"
        if "泡" in blob and ("促進" in blob or "助" in blob):
            return "泡消火剤は液面被覆により可燃性蒸気の発生を抑える。"

    if "動植物油類" in stem and "適切" in stem:
        if "第二石油類" in core or "軽油" in core or "灯油" in core:
            return "菜種油・大豆油などが動植物油類の代表例である。"
        if "第一石油類" in core or "ガソリン" in core or "アセトン" in core:
            return "石油類・アルコール類とは分類が異なる。"

    if re.search(r"第[一二三四]石油類", stem) or "石油類" in stem:
        if "第一石油類" in core or "ガソリン" in core or "ベンゼン" in core:
            if "第二石油類" in stem or "第三石油類" in stem or "第四石油類" in stem:
                return "ガソリン・ベンゼンは第一石油類である。"
        if "第二石油類" in core or "灯油" in core or "軽油" in core:
            if "第三石油類" in stem or "第四石油類" in stem:
                return "灯油・軽油は第二石油類である。"
        if "第三石油類" in core or "重油" in core:
            if "第四石油類" in stem:
                return "重油は第三石油類である。"
        if "アルコール" in core or "特殊引火物" in core:
            return "石油類とアルコール類・特殊引火物は別に整理する。"

    if "危険物法令" in stem:
        if "第4類" in blob and "酸化" in blob:
            return "第4類危険物は引火性液体であり、酸化性固体は第1類である。"
        if "価格" in blob:
            return "指定数量は販売価格ではない。"

    if "連鎖反応" in stem:
        if "指定数量" in core or "単位" in core:
            return "燃焼の連鎖反応は燃焼が継続する過程の考え方である。"
        if "溶け" in core or "溶解" in core:
            return "溶解速度とは別の概念である。"
        if "免状" in core:
            return "免状の交付手続きではない。"
        if "装置" in core or "比重" in core:
            return "液体比重を測る装置の名称ではない。"

    if "点火源" in stem:
        if "水" in blob and ("ない" in core or "通常" in core or blob == "水"):
            return "水は冷却に用いるが、通常は点火源ではない。"
        if "氷" in blob:
            return "氷は低温の水であり、着火のきっかけにはならない。"
        if "窒素" in blob:
            return "窒素は不活性ガスであり、通常は着火のきっかけにならない。"
        if "二酸化炭素" in blob or ("二酸化" in blob and "炭素" in blob):
            return "二酸化炭素は窒息消火に用いることがある。"

    if "可燃性蒸気" in stem and "空気" in stem:
        if "溶け" in blob or "水溶性" in blob:
            return "水溶性と可燃性蒸気の引火は別の性質である。"
        if "絶対" in blob and "燃焼" in blob:
            return "混合濃度が燃焼下限〜上限の範囲に入れば燃焼し得る。"
        if "不燃" in blob:
            return "空気と混ざっても燃焼範囲内では危険がある。"
        if "指定数量" in blob and "ゼロ" in blob:
            return "指定数量は混合濃度とは別の数量基準である。"
        if "指定数量" in blob and ("なく" in blob or "減" in blob):
            return "混合気の性質と指定数量の基準は別である。"
        if "第6類" in blob:
            return "水溶性と危険物の類別は別の問題である。"

    if "比熱" in stem:
        if "指定数量" in blob:
            return "比熱と危険物の指定数量は別の概念である。"
        if "可燃性蒸気" in blob or ("蒸気" in blob and "出" in blob):
            return "比熱の大小と可燃性蒸気の発生は直接結びつかない。"
        if "浮" in blob or ("水" in blob and "浮" in blob):
            return "比熱と液体の浮力・比重は別の物理量である。"
        if "爆発" in blob:
            return "比熱の大小と爆発性は別の性質である。"

    if "密度" in stem:
        if "ゼロ" in blob:
            return "質量がある限り密度はゼロにならない。"
        if "水溶性" in blob or ("溶け" in blob and "性" in blob):
            return "密度と水溶性は別の性質である。"
        if "発火" in blob:
            return "密度の大小と引火性は別の問題である。"
        if "小さく" in blob:
            return "同じ体積で質量が大きいほど密度は大きくなる。"
        if "質量" in stem:
            if "割" in core or "向き" in core or "0.0016" in blob:
                return "質量＝密度×体積であり、体積÷密度は逆の計算である。"
            if "625" in blob:
                return "500÷0.8は体積÷密度であり、質量の式ではない。"
            if "500 g" in blob and "400" not in blob:
                return "質量は0.8×500＝400 gで求める。"

    if "粉末消火" in stem:
        if "指定数量" in blob:
            return "消火剤は指定数量を変えるものではない。"
        if "火花" in blob:
            return "火花は着火源となり得るが、粉末消火剤の消火効果ではない。"
        if "酸素" in blob and ("供給" in blob or "大量" in blob):
            return "酸素供給は燃焼を助けるため、消火効果とは逆である。"
        if "可燃物" in blob and "増" in blob:
            return "可燃物を増やすと燃焼が拡大し、消火効果とは逆である。"

    if "温度" in stem and "説明" in stem:
        if "pH" in blob or "酸性" in blob:
            return "温度は熱さ冷たさの程度を表す物理量であり、pHとは別である。"
        if "体積" in blob and "質量" in blob:
            return "質量÷体積は密度の説明であり、温度とは別である。"
        if "指定数量" in blob or "倍数" in blob:
            return "指定数量倍数は数量基準であり、温度の説明ではない。"
        if "熱エネルギー" in blob or ("熱量" in blob and "総量" in blob):
            return "熱エネルギーの総量は熱量の概念であり、温度とは別である。"

    if "氷" in stem and ("水" in stem or "変わ" in stem):
        if "指定数量" in blob:
            return "状態変化に伴う熱は潜熱の概念であり、指定数量とは無関係である。"
        if "蒸気比重" in blob:
            return "融解に関わるのは潜熱であり、蒸気比重とは別の物理量である。"
        if "pH" in blob:
            return "pHは水溶液の概念であり、融解に関する熱とは別である。"
        if "免状" in blob:
            return "氷の融解に関わる熱量の話であり、免状交付制度とは無関係である。"

    if "液比重" in stem and ("1より" in stem or "大きい" in stem):
        if "軽" in blob and "浮" in blob:
            return "液比重が1より大きいとき、水より重く沈みやすい。"
        if "酸素" in blob and "放出" in blob:
            return "液比重と酸素放出性は別の性質である。"
        if "不燃" in blob:
            return "液比重の大小と不燃性は別の問題である。"
        if "空気" in blob and "軽" in blob:
            return "液比重と蒸気比重は別の物理量である。"

    if "蒸気比重" in stem:
        if "小さい" in stem or ("1より" in stem and "小" in stem):
            if "沈" in blob and "水" in blob:
                return "蒸気比重は空気との比較であり、水への浮沈とは直接関係ない。"
            if "重" in blob and "空気" in blob:
                return "蒸気比重が1より小さいとき、蒸気は空気より軽い。"
            if "溶け" in blob or "水溶性" in blob:
                return "蒸気比重と水溶性は別の性質である。"
            if "不燃" in blob:
                return "蒸気比重の大小と不燃性は別の問題である。"
        if "第1類" in blob or "第１類" in blob:
            return "蒸気比重と危険物の類別は別の概念である。"
        if "不燃" in blob:
            return "蒸気比重が1より大きくても燃焼性のある蒸気はある。"
        if "軽い" in blob or ("空気" in blob and "軽" in blob):
            return "蒸気比重が1より大きいとき、蒸気は空気より重い。"
        if "溶け" in blob or "水溶性" in blob:
            return "蒸気比重と水溶性は別の性質である。"

    if "pH" in stem or ("酸性" in stem and "水溶液" in stem):
        if "蒸気比重" in blob:
            return "酸性と蒸気比重は別の概念である。"
        if "不燃" in blob:
            return "酸性水溶液でも可燃性のあるものがある。"
        if "第4類" in blob:
            return "pHの大小と危険物の類別は別である。"
        if "pH" in blob and "大" in blob:
            return "一般にpH7より大きい水溶液がアルカリ性である。"
        if "中性" in blob:
            return "一般にpH7付近が中性で、7未満は酸性である。"
        if "酸性" in blob or "強酸" in blob:
            return "一般にpH7付近が中性で、7未満が酸性である。"
        if "アルカリ" in blob:
            return "一般にpH7より大きい水溶液がアルカリ性である。"

    if "引火性液体" in stem:
        if "不燃" in blob:
            return "引火性液体は可燃性があり、不燃性ではない。"
        if "水素" in blob or ("水" in blob and "反応" in blob):
            return "禁水性物質の説明であり、引火性液体の一般性質ではない。"
        if "酸素" in blob and "放出" in blob:
            return "酸素放出性と引火性液体の危険性は別である。"
        if "固体" in blob:
            return "引火性液体は液体であり、固体ではない。"

    if "水溶性" in stem and "第4類" in stem:
        if "第1類" in blob:
            return "水溶性があっても第4類に属するものがある。"
        if "10,000" in blob or "10000" in blob:
            return "水溶性と指定数量の値は別に定められる。"
        if "不燃" in blob:
            return "水に溶けても引火危険がある第4類がある。"
        if "絶対" in blob and "蒸気" in blob:
            return "水溶性があっても可燃性蒸気を出すものがある。"

    if "泡消火剤" in stem:
        if "溶か" in core or "水溶性" in core:
            return "泡は液面を覆い可燃性蒸気の発生を抑える。"
        if "かき混" in core or "攪拌" in core:
            return "第4類火災でかき混ぜると燃焼拡大のおそれがある。"
        if "酸素" in core and ("供給" in core or "促進" in core):
            return "酸素供給は燃焼を助けるため、消火作用ではない。"
        if "指定数量" in core:
            return "指定数量を変える消火剤ではない。"

    if "ガソリン蒸気" in stem or (
        "ガソリン" in stem and "蒸気" in stem and "危険" in stem
    ):
        if "酸素" in core and "放出" in core:
            return "ガソリン蒸気は第4類の可燃性蒸気であり、酸素系第3類ではない。"
        if "不燃" in core or "安全" in core or "引火" in core:
            return "ガソリン蒸気は空気より重く、火気で引火しやすい。"
        if "溶け" in core or "換気" in core:
            return "可燃性蒸気の滞留を防ぐ換気が重要である。"

    if "ガソリン" in stem and ("火災予防" in stem or "取扱" in stem):
        if "下水" in core or "排水" in core:
            return "漏えいしたガソリンを下水へ流すと火災・環境汚染の危険がある。"
        if "加熱" in core or "開放" in core or "直射日光" in core:
            return "容器開放や加熱は可燃性蒸気を増やし引火の危険がある。"
        if "裸火" in core or ("火気" in core and "確認" in core):
            return "蒸気確認に裸火を用いると引火・爆燃の危険がある。"
        if "火気" in core and ("近" in core or "移" in core):
            return "引火危険が高いため、火気の近くで取り扱わない。"

    if "第4類危険物" in stem and "説明" in stem:
        if "第3類" in core or "自然発火" in core or "禁水" in core:
            return "自然発火性物質・禁水性物質は第3類危険物の説明である。"
        if "第2類" in core or "可燃性固体" in core:
            return "可燃性固体は第2類危険物の性状である。"
        if "第6類" in core or "酸化性液体" in core:
            return "酸化性液体は第6類危険物の性状である。"
        if "第1類" in core or "酸化性固体" in core:
            return "酸化性固体は第1類危険物の性状である。"

    if "第4類危険物" in stem and ("該当" in stem or "性状" in stem):
        if "酸化性液体" in blob:
            return "酸化性液体は第6類危険物の性状であり、第4類ではない。"
        if "自然発火" in blob or "禁水" in blob:
            return "自然発火性物質・禁水性物質は第3類危険物の性状である。"
        if "酸化性固体" in blob:
            return "酸化性固体は第1類危険物の性状であり、第4類ではない。"
        if "可燃性固体" in blob:
            return "可燃性固体は第2類危険物の性状であり、第4類ではない。"

    if "消火剤" in stem and "第4類" in stem:
        if "酸素" in core:
            return "酸素は燃焼を助けるため、消火剤としては不適切である。"
        if "ガソリン" in core or "燃料" in core:
            return "ガソリンは可燃物であり、消火剤ではない。"
        if "火花" in core or "着火源" in core:
            return "火花は着火源であり、消火剤ではない。"
        if "可燃性蒸気" in core or ("蒸気" in core and "引火" in core):
            return "可燃性蒸気は引火危険を高めるため、消火剤ではない。"

    if ("第4類" in stem or "可燃性蒸気" in stem) and (
        "性質" in stem or "蒸気" in stem
    ):
        if "酸素" in core:
            return "第4類の可燃性蒸気が水で酸素を放出するわけではない。"
        if "無害" in core or ("換気" in core and "不要" in core):
            return "可燃性蒸気の滞留を防ぐ換気は火災予防上重要である。"
        if "引火" in core:
            return "第4類の可燃性蒸気は火源により引火するおそれがある。"
        if "軽く" in core or "天井" in core:
            return "第4類の蒸気は空気より重いものが多い。"

    if "エタノール" in stem:
        if "第1類" in core:
            return "エタノールは第4類危険物のアルコール類である。"
        if "第一石油類" in core or "ガソリン" in core:
            return "エタノールはアルコール類であり、第一石油類ではない。"
        if "禁水" in core:
            return "エタノールは禁水性物質ではない。"
        if "不燃" in core:
            return "エタノールは引火の危険がある可燃性液体である。"

    if "乙種" in stem and "取扱者" in stem:
        if "一切" in blob and "取扱" in blob:
            return "乙種は第4類の指定数量倍数ごとに取扱える危険物の種類が定められている。"
        if "すべて" in blob and ("無条件" in blob or "類" in blob):
            return "甲種と異なり、すべての類を無条件で取り扱えるわけではない。"
        if "消火設備" in blob:
            return "乙種免状は取扱者の資格であり、消火設備の名称ではない。"
        if "設置許可" in blob:
            return "施設の設置許可と取扱者免状は別の制度である。"

    if "重油" in stem and "分類" in stem:
        if "動植物油" in core:
            return "重油は第4類の第三石油類に該当する。"
        if "特殊引火物" in core:
            return "重油は特殊引火物ではなく石油類に分類される。"
        if "第一石油類" in core:
            return "第一石油類はガソリンなどに該当し、重油とは異なる。"
        if "アルコール" in core:
            return "アルコール類はメタノール・エタノールなどに該当する。"

    if "重油" in stem and "火災予防" in stem:
        if "第1類" in blob or ("酸素" in blob and "放出" in blob):
            return "重油は第4類の第三石油類であり、第1類ではない。"
        if "裸火" in blob:
            return "温度確認に裸火を用いると引火の危険がある。"
        if "放置" in blob:
            return "漏えいは換気・回収など適切に処理する。"
        if "溶け" in blob and ("管理不要" in blob or "完全" in blob):
            return "非水溶性でも引火危険があり管理が必要である。"

    if "キシレン" in stem and "トルエン" in stem:
        if "アルコール" in blob:
            return "キシレン・トルエンは石油類に分類される。"
        if "特殊引火物" in blob:
            return "どちらも特殊引火物ではなく石油類である。"
        if "動植物油" in blob:
            return "動植物油類とは別の石油類に分類される。"
        if ("第一石油類" in blob and "キシレン" in blob) or "逆" in core:
            return "トルエンは第一石油類、キシレンは第二石油類である。"

    if "潤滑油" in stem:
        if "特殊引火物" in blob:
            return "潤滑油は第四石油類に該当し、特殊引火物ではない。"
        if "アルコール" in blob:
            return "潤滑油は石油類であり、アルコール類ではない。"
        if "第3類" in blob:
            return "潤滑油は第4類の第四石油類である。"
        if "動植物油" in blob:
            return "潤滑油は石油類であり、動植物油類ではない。"

    if "酢酸" in stem and "酢酸エチル" in stem:
        if "動植物油" in blob:
            return "酢酸・酢酸エチルは動植物油類ではない。"
        if "アルコール" in blob:
            return "どちらもアルコール類ではなく石油類に分類される。"
        if "第6類" in blob:
            return "第4類の引火性液体であり、第6類ではない。"
        if "第一石油類" in blob and "酢酸" in blob and "酢酸エチル" in blob:
            return "酢酸は第二石油類、酢酸エチルは第一石油類である。"

    if "二硫化炭素" in stem:
        if "第6類" in blob or "第６類" in blob:
            return "第4類の特殊引火物であり、第6類ではない。"
        if "酸素" in blob and "放出" in blob:
            return "酸素放出性（第3類性状）とは別である。"
        if "第1類" in blob:
            return "二硫化炭素は特殊引火物に該当する。"
        if "不燃" in blob or ("引火" in blob and "ない" in blob):
            return "引火危険が高い特殊引火物である。"
        if "引火" in blob and "ある" in blob:
            return "二硫化炭素は引火危険が高い特殊引火物である。"
        if "第二石油類" in blob:
            return "第二石油類ではなく特殊引火物である。"
        if "動植物油" in blob:
            return "動植物油類ではなく特殊引火物である。"

    if stem.startswith("メタノール") or (
        "メタノール" in stem
        and ("適切" in stem or "性質" in stem or "火災" in stem or "危険" in stem)
    ):
        if "第1類" in blob or ("酸化" in blob and "固体" in blob):
            return "メタノールは第4類のアルコール類であり、第1類ではない。"
        if "第6類" in blob:
            return "メタノールは第4類危険物のアルコール類であり、第6類ではない。"
        if "酸素" in blob and "放出" in blob:
            return "酸素放出性とアルコール類の性質は別である。"
        if "第一石油類" in blob or "石油類" in blob or "第三石油類" in blob:
            return "メタノールは第4類危険物のアルコール類である。"
        if "特殊引火物" in blob:
            return "メタノールはアルコール類であり、特殊引火物ではない。"
        if "動植物油" in blob:
            return "メタノールはアルコール類であり、動植物油類ではない。"
        if "溶け" in blob and ("引火" in blob or "燃え" in blob or "絶対" in blob):
            return "水に溶けても引火危険がある第4類の典型例である。"

    if "アセトアルデヒド" in stem:
        if "禁水" in core:
            return "アセトアルデヒドは特殊引火物である。"
        if "重油" in core or "第三石油類" in core:
            return "石油類ではなく特殊引火物に該当する。"
        if "第6類" in core:
            return "第4類の特殊引火物に該当する。"
        if "蒸気" in core and "ない" in core:
            return "引火危険があり、可燃性蒸気を発生する。"
        if "引火" in core and "ある" in core:
            return "アセトアルデヒドは引火危険が高い特殊引火物である。"

    if "の分類" in stem and "ではない" in core:
        m = re.match(r"^(.+?)の分類", stem)
        if m:
            subj = m.group(1).strip()
            class_hints = {
                "ベンゼン": "ベンゼンは第一石油類に該当する。",
                "トルエン": "トルエンは第一石油類に該当する。",
                "酢酸エチル": "酢酸エチルは第一石油類に該当する。",
                "キシレン": "キシレンは第二石油類に該当する。",
                "酢酸": "酢酸は第二石油類に該当し、第一石油類ではない。",
                "エチレングリコール": "エチレングリコールは第三石油類に該当する。",
            }
            for name, hint in class_hints.items():
                if name in subj:
                    return hint

    if "組合せ" in stem and "分類" in stem:
        if "重油" in core and "第三石油類" in core:
            return "重油は第三石油類であり、アルコール類ではない。"
        if "灯油" in core and "第二石油類" in core:
            return "灯油は第二石油類であり、特殊引火物ではない。"
        if "メタノール" in core and "アルコール" in core:
            return "メタノールはアルコール類であり、第二石油類ではない。"
        if "ジエチル" in core:
            return "ジエチルエーテルは特殊引火物である。"

    if ("グリセリン" in stem or "エチレングリコール" in stem) and "分類" in stem:
        if "第一石油類" in blob:
            return "エチレングリコール・グリセリンは第三石油類に該当する。"
        if "第二石油類" in blob:
            return "エチレングリコール・グリセリンは第三石油類に該当する。"
        if "アルコール" in blob:
            return "第三石油類であり、アルコール類ではない。"
        if "特殊引火物" in blob:
            return "第三石油類であり、特殊引火物ではない。"
        if "動植物油" in blob:
            return "第三石油類であり、動植物油類ではない。"

    if "布" in stem and "油" in stem:
        if "指定数量" in blob:
            return "指定数量は放置しても自動的に減るものではない。"
        if "第6類" in blob:
            return "危険物の類別が変わるわけではなく、自然発火のリスクがある。"
        if "不燃" in blob:
            return "不燃性に変化するわけではなく、酸化熱が蓄積する。"
        if "溶け" in blob and "消火" in blob:
            return "水に溶けて消火されるとは限らない。"

    if "水溶性" in stem and ("組合せ" in stem or "第4類" in stem):
        if "重油" in blob or "潤滑油" in blob or "大豆油" in blob:
            return "重油・潤滑油・大豆油は非水溶性として整理される。"
        if "ジエチル" in blob or "二硫化" in blob:
            return "特殊引火物等の非水溶性液体の組合せである。"
        if ("灯油" in blob or "軽油" in blob) and "組合せ" in stem:
            return "灯油・軽油・重油は非水溶性として整理される。"

    if ("泡消火" in stem or ("泡" in stem and "消火" in stem)) and (
        "注意" in stem or "火災" in stem
    ):
        if "促進" in blob:
            return "泡消火剤は液面被覆により消火に用いられる。"
        if "危険がない" in blob or ("火災" in blob and "ない" in blob):
            return "水溶性でも引火危険がある引火性液体がある。"
        if "第1類" in blob:
            return "水溶性液体も第4類引火性液体に該当するものがある。"
        if "火気" in blob and ("近" in blob or "確認" in blob or "燃え尽" in blob):
            return "火気を近づけると引火・爆燃の危険がある。"
        if "下水" in blob or "排水" in blob or "放流" in blob:
            return "漏えいや火災時の流出物を下水へ流してはならない。"
        if "酸素" in blob and ("供給" in blob or "大量" in blob):
            return "酸素供給は燃焼を助けるため、消火の考え方に反する。"
        if "開放" in blob or ("容器" in blob and "開" in blob):
            return "容器開放は可燃性蒸気を増やし危険である。"

    if "性質" in stem and "消火" in stem and (
        "組合せ" in stem or "総合" in stem or "理解" in stem
    ):
        if "会社" in blob or "ロゴ" in blob:
            return "会社名や商標は危険物の性質・消火の論点ではない。"
        if "免状" in blob and "受験" in blob:
            return "免状番号と受験番号は試験運営情報であり、性消の本質ではない。"
        if "販売" in blob or "広告" in blob:
            return "販売価格や広告文は性質・消火の論点ではない。"
        if "試験会場" in blob or "座席" in blob:
            return "試験会場や座席番号は試験運営に関する情報である。"
        if "液比重" in blob and "空気" in blob:
            return "液比重の基準は水であり、空気を基準とするのは蒸気比重である。"
        if "水溶性" in blob and "不燃" in blob:
            return "水溶性でも引火危険がある第4類があり、すべて不燃性とは限らない。"
        if "蒸気比重" in blob and "水" in blob:
            return "蒸気比重の基準は空気であり、水を基準とするのは液比重である。"
        if "分類" in blob and "消火" in blob and "不要" in blob:
            return "第4類では分類と消火方法をセットで整理して覚える必要がある。"

    if "配管" in stem and "移送" in stem:
        if "屋内貯蔵" in blob:
            return "屋内貯蔵所は建物内で貯蔵する施設であり、移送取扱所ではない。"
        if "簡易タンク" in blob or "移動タンク" in blob:
            return "貯蔵所に分類される施設であり、配管移送の取扱所ではない。"
        if "販売" in blob and "取扱" in blob:
            return "販売取扱所は販売に伴う取扱所であり、配管移送の施設ではない。"

    if "配管" in stem and ("流" in stem or "高速" in stem):
        if "免状" in blob:
            return "高速流動時の静電気と免状の失効は無関係である。"
        if "指定数量" in blob:
            return "指定数量は政令の数量基準であり、流動で消滅しない。"
        if "不燃" in blob:
            return "液体の不燃性が変わるわけではない。"
        if "pH" in blob:
            return "pHの自動上昇と配管流動時の注意は無関係である。"

    if "単体" in stem and "説明" in stem:
        if "火源" in blob and "燃え" in blob:
            return "火源で燃え始める温度は引火点の説明である。"
        if "気体" in blob and "なる" in blob:
            return "液体が気体になる現象は蒸発の説明である。"
        if "結び" in blob and "元素" in blob:
            return "2種類以上の元素が結びついた物質は化合物の説明である。"
        if "混" in blob and ("合" in blob or "混じ" in blob):
            return "複数の物質が混じり合ったものは混合物の説明である。"

    if "さび" in stem or ("鉄" in stem and "反応" in stem):
        if "中和" in blob:
            return "中和は酸とアルカリの反応であり、さび（酸化）とは別である。"
        if "融解" in blob:
            return "固体が液体になる現象は融解の説明である。"
        if "凝固" in blob:
            return "液体が固体になる現象は凝固の説明である。"
        if "蒸発" in blob:
            return "液体が気体になる現象は蒸発の説明である。"

    if "第4類" in stem and ("危険性" in stem or "中心的" in stem):
        if "激しい" in blob or ("水" in blob and "反応" in blob):
            return "水との激しい反応は第3類禁水性等に関係する。"
        if "放射性" in blob or "崩壊" in blob:
            return "放射性崩壊は危険物の消防法分類とは別である。"
        if "摩擦" in blob:
            return "固体の摩擦発火は第2類自然発火性等に関係する。"
        if "酸素" in blob and "放出" in blob:
            return "酸素放出は酸化性固体（第1類）等の性質である。"

    if "第4類" in stem and ("低所" in stem or "たまり" in stem):
        if "不燃" in blob:
            return "第4類の可燃性蒸気は引火危険がある。"
        if "酸素" in blob and "放出" in blob:
            return "酸素放出性と蒸気比重は別の性質である。"
        if "軽い" in blob or ("空気" in blob and "軽" in blob):
            return "蒸気比重が1より大きいものは空気より重い。"
        if "溶け" in blob or "完全" in blob and "水" in blob:
            return "水溶性と蒸気比重は別の性質である。"
        if "指定数量" in blob:
            return "指定数量は物質ごとの数量基準であり、蒸気滞留でなくなるわけではない。"
        if "沈" in blob and "水" in blob:
            return "液比重は水への浮沈に関係し、低所滞留の蒸気危険とは別である。"

    if "危険物" in stem and "消防法" in stem:
        return "消防法別表第一に基づく危険物の定義とは異なる。"

    if "運搬" in stem and "適切でない" not in stem:
        return "危険物運搬の要件として誤った理解である。"

    if "積載" in stem:
        if "破損" in blob and ("させ" in blob or "やすい" in blob):
            return "運搬では容器の破損を防ぐよう積載しなければならない。"
        if "漏" in blob and ("しやすい" in blob or "えい" in blob):
            return "漏えいを防ぐ積載が基本であり、漏れやすい積み方は不適切である。"
        if "流し" in blob or ("道路" in blob and "積載" in blob):
            return "危険物を道路へ流してはならない。"
        if "火気" in blob:
            return "火気の近くへの積載は引火の危険がある。"

    if "不適切" in stem and ("貯蔵" in stem or "取扱" in stem):
        if "火気" in blob:
            return "火気管理は適切な保安措置であり、不適切な取扱いではない。"
        if "温度" in blob:
            return "温度管理は適切な保安措置であり、不適切な取扱いではない。"
        if "漏" in blob:
            return "漏えい防止は適切な保安措置であり、不適切な取扱いではない。"
        if "換気" in blob:
            return "換気は適切な保安措置であり、不適切な取扱いではない。"

    if "分類学習" in stem or (
        "第4類" in stem and "考え方" in stem and "適切" in stem
    ):
        if "特殊引火物" in blob and "動植物油" in blob:
            return "特殊引火物と動植物油類では危険性や指定数量が異なる。"
        if "水溶性" in blob and "不燃" in blob:
            return "水溶性でも引火危険がある第4類があり、不燃性とは限らない。"
        if "石油類" in blob and ("同じ分類" in blob or "すべて同じ" in blob):
            return "石油類は第一〜第四石油類などに細分される。"
        if "物質名" in blob and "指定数量" in blob:
            return "代表物質ごとに指定数量や水溶性の有無が定められている。"

    if "廃止" in stem and "製造所" in stem:
        if "指定数量" in blob and ("増" in blob or "自動" in blob):
            return "指定数量は物質ごとに定められた基準であり、廃止により増えるわけではない。"
        if "放置" in blob or "何もせず" in blob:
            return "廃止後も残存危険物の安全措置や届出が必要である。"
        if "下水" in blob or "排水" in blob:
            return "残存危険物を下水へ流すと火災・環境汚染の危険がある。"
        if "火気" in blob:
            return "残量確認に火気を用いると引火・爆燃の危険がある。"

    if "人に関する制度" in stem or ("人に関する" in stem and "制度" in stem):
        if "屋内貯蔵" in blob or "給油" in blob:
            return "屋内貯蔵所や給油取扱所は施設の区分名称である。"
        if "設置許可" in blob or "完成検査" in blob:
            return "設置許可や完成検査は施設に関する制度である。"
        if "保安距離" in blob or "保有空地" in blob:
            return "保安距離や保有空地は施設の位置・安全基準に関する事項である。"
        if "消火設備" in blob or "警報設備" in blob:
            return "消火設備や警報設備は施設に備える設備である。"

    if "第4類" in stem and "蒸気" in stem and "注意" in stem:
        if "指定数量" in blob and "なく" in blob:
            return "指定数量は物質ごとの基準であり、蒸気が出てもなくなるわけではない。"
        if "免状" in blob:
            return "可燃性蒸気の発生と免状交付は別の問題である。"
        if "不燃" in blob:
            return "第4類には可燃性蒸気を発生する引火性液体がある。"
        if "水" in blob and "なる" in blob:
            return "蒸気が必ず水になるわけではなく、可燃性蒸気の滞留が問題となる。"

    if "ガソリン" in stem and "浮" in stem:
        if "酸素" in blob and "放出" in blob:
            return "ガソリンの浮沈は液比重の問題であり、酸素放出性ではない。"
        if "蒸気比重" in blob:
            return "蒸気比重は空気中の蒸気滞留に関係するが、水への浮沈の直接原因ではない。"
        if "発火点" in blob:
            return "発火点は自然発火の温度に関する概念であり、浮沈とは別である。"
        if "10,000" in blob or "10000" in blob:
            return "ガソリンは第一石油類非水溶性で、指定数量は200 Lである。"

    if "換気" in stem and "第4類" in stem and "不十分" in stem:
        if "水溶性" in blob and "消滅" in blob:
            return "換気不足では可燃性蒸気が滞留しやすく、引火の危険が高まる。"

    if "法令分野" in stem and "整理" in stem:
        if "保安距離" in blob and "免状" in blob:
            return "保安距離は施設の位置基準であり、免状の有効期限とは別である。"
        if "免状" in blob and "施設" in blob and "不要" in blob:
            return "取扱者免状と施設の設置基準・保安管理は別に整理する。"
        if "製造所等" in blob and "取扱者" in blob:
            return "製造所等は施設の総称であり、危険物取扱者の名称ではない。"
        if "指定数量" in blob and "保安講習" in blob:
            return "指定数量と保安講習は別の制度である。"

    if "元素" in stem and "説明" in stem:
        if "免状" in blob:
            return "元素は物質を構成する基本成分の概念であり、免状の制度とは無関係である。"
        if "指定数量" in blob:
            return "指定数量は危険物管理の数量基準であり、元素の定義とは別である。"
        if "気体" in blob and ("なる" in blob or "温度" in blob):
            return "液体が気体になる温度は沸点の説明であり、元素の定義とは別である。"
        if "蒸気" in blob and "重" in blob:
            return "蒸気比重は蒸気の重さの比であり、元素の定義とは別である。"

    if "酸化物" in stem and "酸素" in stem and ("奪" in stem or "関係" in stem):
        if "中和" in blob:
            return "中和は酸とアルカリの反応であり、酸化物からの酸素夺取とは別である。"
        if "凝固" in blob or "融解" in blob or "蒸発" in blob:
            return "固液気の状態変化は物理変化であり、酸素夺取の化学反応とは別である。"

    if "法令分野" in stem and "施設" in stem and "安全" in stem:
        if "元素" in blob or "化合物" in blob or "混合物" in blob:
            return "元素・化合物・混合物は化学分野の物質構成に関する語である。"
        if "免状" in blob or "受験" in blob or "座席" in blob:
            return "免状交付や試験運営の事務用語であり、施設の安全確保制度とは別である。"
        if "水溶性" in blob or "pH" in blob or "濃度" in blob:
            return "水溶性・pH・濃度は性質・消火分野の化学的概念である。"
        if "販売" in blob or "広告" in blob or "会社" in blob:
            return "販売価格や広告文は取引・営業面の語であり、施設の安全確保とは無関係である。"

    return ""


def _extend_wrong_note_from_o4(
    body: str,
    core: str,
    row: dict,
    correct_body: str,
    choice_num: int | None = None,
) -> str:
    """短い場合のみ、O4原文から追加1文（定型句は使わない）。"""
    short = len(body) < _CHOICE_NOTE_MIN_LEN
    ref = body if short else body + correct_body
    exp = norm(row.get("explanation"))
    if choice_num:
        inline = parse_all_inline_choice_notes(exp)
        full = _strip_choice_verdict_prefix(inline.get(choice_num, ""))
        if full and len(full) > len(core or "") + 8:
            extra = full
            if core and core in full:
                extra = full.split(core, 1)[-1].strip("。．、 ")
            if extra and extra != core:
                sent = extra if extra.endswith("。") else extra + "。"
                if not _sentence_is_redundant(sent, ref):
                    body = body + sent
                    ref = body if short else body + correct_body
    exam = _o4_tagged_block(exp, "試験ポイント")
    if exam and not _sentence_is_redundant(exam, ref):
        if _keyword_overlap_ratio(exam, core) >= 0.15:
            sent = exam if exam.endswith("。") else exam + "。"
            if not _sentence_is_redundant(sent, ref):
                return body + sent
    trap = _o4_tagged_block(exp, "ひっかけ")
    if trap and len(body) < _CHOICE_NOTE_MIN_LEN:
        sent = trap if trap.endswith("。") else trap + "。"
        if _keyword_overlap_ratio(sent, correct_body) < 0.82:
            if not _sentence_is_redundant(sent, ref):
                return body + sent
    elif trap and not _sentence_is_redundant(trap, ref):
        return body + (trap if trap.endswith("。") else trap + "。")
    return body


def _compose_wrong_choice_note(
    page: dict,
    row: dict,
    choice_num: int,
    opt: str,
    base_note: str,
    correct_body: str = "",
) -> str:
    """他肢解説をO4原文ベースで約200字・非重複の段落に整える。"""
    stem = norm(page.get("stem_plain") or page.get("stem"))
    mode = question_ask_mode(stem)
    note = _strip_choice_verdict_prefix(base_note)
    note = _strip_notes_overlapping_reference(note, correct_body)
    note = re.sub(r"^正しい[。．]\s*", "", note).strip()

    opt_core = norm(opt).rstrip("。")
    opt_sn = _snippet(opt_core, 40)
    core = note.rstrip("。") if note else ""
    is_marked_appropriate = bool(re.match(r"^(適切|正しい)", norm(base_note)))

    if mode == "least_appropriate" and is_marked_appropriate:
        reason = core or "内容として妥当"
        ask_label = (
            "誤っているもの"
            if re.search(r"誤っている|誤りである|正しくない", stem)
            else "適切でないもの"
        )
        body = (
            f"「{opt_sn}」について、{reason}。"
            f"正しい記述であり、本問が求める「{ask_label}」には該当しない。"
        )
    elif mode == "least_appropriate" and re.search(
        r"必要である|必要な|妥当|適切な対策|適切な保安|正しい対策",
        core,
    ):
        ask_label = (
            "不適切なもの"
            if "不適切" in stem
            else "誤っているもの"
            if re.search(r"誤っている|誤りである|正しくない", stem)
            else "適切でないもの"
        )
        body = (
            f"「{opt_sn}」について、{core}。"
            f"正しい対策であり、本問が求める「{ask_label}」には該当しない。"
        )
    elif core:
        body = _wrong_note_opening(choice_num, opt_sn, core)
        exp_text = norm(row.get("explanation"))
        exam = _o4_tagged_block(exp_text, "試験ポイント")
        elaborate = _elaborate_wrong_classification(stem, core)
        context = "" if elaborate else _wrong_note_context_sentence(page, core, opt_core)
        extras: list[str] = []
        for extra in (
            _wrong_stem_exam_bridge(stem, exam, core),
            elaborate,
            context,
        ):
            if not extra:
                continue
            sent = extra if extra.endswith("。") else extra + "。"
            ref = body + "".join(extras)
            if _sentence_is_redundant(sent, ref) and len(ref) >= _CHOICE_NOTE_MIN_LEN:
                continue
            extras.append(sent)
        body += "".join(extras)
    else:
        body = f"「{opt_sn}」の記述は、正答の内容と一致しない。"

    if len(body) < _CHOICE_NOTE_MIN_LEN:
        body = _extend_wrong_note_from_o4(
            body, core, row, correct_body, choice_num=choice_num
        )
    body = _dedupe_wrong_note_sentences(body)
    if len(body) < _CHOICE_NOTE_MIN_LEN:
        ctx = _wrong_note_context_sentence(page, core, opt_core)
        if ctx:
            sent = ctx if ctx.endswith("。") else ctx + "。"
            if not _sentence_is_redundant(sent, body):
                body += sent
    if len(body) < _CHOICE_NOTE_MIN_LEN:
        body = _append_if_fresh(
            body,
            "正答肢の記述と照合して確認する。",
            max_overlap=0.35,
        )
    if len(body) > _CHOICE_NOTE_MAX_LEN:
        body = _truncate_prose_at_sentence(body, _CHOICE_NOTE_MAX_LEN)
    return body


def _compose_correct_reason(page: dict, row: dict, existing: str = "") -> str:
    """正解の理由を約200文字の読みやすい段落に整える。"""
    parts: list[str] = []
    exp = norm(row.get("explanation"))
    lead = _o4_explanation_lead(exp) or _o4_explanation_lead(dedupe_prose(existing))
    cor_idx = _correct_choice_index(page.get("correct"))
    notes = parse_all_inline_choice_notes(exp)
    opts = page.get("opts") or []
    cor_note = _strip_choice_verdict_prefix(notes.get(cor_idx or 0, ""))
    if cor_idx and 1 <= cor_idx <= len(opts):
        opt_n = _normalize_for_compare(norm(opts[cor_idx - 1]).rstrip("。"))
        cn = _normalize_for_compare(cor_note.rstrip("。"))
        if cn and (cn == opt_n or cn in opt_n or opt_n in cn):
            cor_note = ""
        elif cor_note:
            generic = bool(re.search(r"基本的な性質|説明として妥当", cor_note))
            opt_text = norm(opts[cor_idx - 1]) if cor_idx else ""
            if generic and _keyword_overlap_ratio(opt_text, lead) >= 0.2:
                cor_note = ""
            elif _keyword_overlap_ratio(cor_note, lead) >= 0.45:
                cor_note = ""
            else:
                expanded = _expand_cor_note_to_sentence(
                    cor_idx, norm(opts[cor_idx - 1]), cor_note
                )
                if _keyword_overlap_ratio(expanded, lead) >= 0.45:
                    cor_note = ""
                elif not _sentence_is_redundant(expanded, lead):
                    cor_note = expanded
                else:
                    cor_note = ""

    for block in (
        lead,
        cor_note,
        _o4_tagged_block(exp, "試験ポイント"),
    ):
        _append_unique_sentences(parts, block)
    point_raw = norm(row.get("explanation_point"))
    if point_raw:
        for sent in _split_explanation_sentences(point_raw):
            _append_unique_sentences(parts, sent)

    trap = _o4_tagged_block(exp, "ひっかけ")
    if trap:
        _append_unique_sentences(parts, trap)

    exam_only = _o4_tagged_block(exp, "試験ポイント")
    if exam_only and len("".join(parts)) < 90:
        for sent in _split_explanation_sentences(exam_only):
            expanded = _normalize_exam_formula_sentence(sent)
            joined = "".join(parts)
            if not _sentence_is_redundant(expanded, joined):
                parts.append(expanded)

    body = "".join(parts)
    if len(body) < _CORRECT_REASON_MIN_LEN:
        body = _expand_correct_reason_if_short(page, row, body, notes, cor_idx)

    if not body:
        body = lead or _strip_choice_verdict_prefix(notes.get(cor_idx or 0, ""))

    stem = norm(page.get("stem_plain") or page.get("stem"))
    if (
        question_ask_mode(stem) == "least_appropriate"
        and cor_idx
        and 1 <= cor_idx <= len(opts)
    ):
        cor_sn = _snippet(norm(opts[cor_idx - 1]).rstrip("。"), 44)
        least = f"（{cor_idx}）「{cor_sn}」は、他肢と比べて最も適切でない記述である。"
        if not _sentence_is_redundant(least, body):
            body += least

    body = _trim_redundant_correct_closer(body, page, cor_idx)
    body = _dedupe_body_sentences(body)
    if len(body) > _CORRECT_REASON_MAX_LEN:
        body = _truncate_prose_at_sentence(body, _CORRECT_REASON_MAX_LEN)
    elif len(body) < _CORRECT_REASON_MIN_LEN:
        body = _pad_correct_reason_body(page, row, body, notes, cor_idx)
        body = _dedupe_body_sentences(body)
    if len(body) < _CORRECT_REASON_MIN_LEN and cor_idx:
        note = _strip_choice_verdict_prefix(notes.get(cor_idx, ""))
        if note and len(note) <= 28:
            body = _append_if_fresh(body, note, max_overlap=0.92)
    if len(body) < _CORRECT_REASON_MIN_LEN:
        stem = norm(page.get("stem_plain") or page.get("stem"))
        if "分類" in stem and re.search(r"石油類|重油|軽油|ガソリン", body):
            body = _append_if_fresh(
                body,
                "灯油は第二石油類、ガソリンは第一石油類に当たる。",
                max_overlap=0.35,
            )
        if "液比重" in stem and "蒸気比重" in stem:
            body = _append_if_fresh(
                body,
                "基準物質を取り違えると低所滞留や浮沈の判断を誤りやすい。",
                max_overlap=0.35,
            )
        if "水" in stem and "重さ" in stem and "比" in stem:
            body = _append_if_fresh(
                body,
                "試験では基準液体が水である点を確認する。",
                max_overlap=0.35,
            )
        if "特殊引火物" in stem and ("組合せ" in stem or "該当" in stem):
            body = _append_if_fresh(
                body,
                "引火危険が特に高いため取扱いに注意が必要である。",
                max_overlap=0.35,
            )
        if "第二石油類" in stem and "正しい" in stem:
            body = _append_if_fresh(
                body,
                "ガソリンは第一石油類、灯油・軽油は第二石油類である。",
                max_overlap=0.35,
            )
        if "物理変化" in stem:
            body = _append_if_fresh(
                body,
                "状態が変わっても成分が同じなら物理変化として整理する。",
                max_overlap=0.35,
            )
        if "酸性" in stem and "水溶液" in stem:
            body = _append_if_fresh(
                body,
                "弱酸・強酸の区別は別の論点として整理する。",
                max_overlap=0.35,
            )
        if "炭化水素" in stem and "構成" in stem:
            body = _append_if_fresh(
                body,
                "炭素原子と水素原子の組合せでできた化合物である。",
                max_overlap=0.35,
            )
        if "二硫化炭素" in stem and "性質" in stem:
            body = _append_if_fresh(
                body,
                "引火危険が高いため取扱いに注意が必要である。",
                max_overlap=0.35,
            )
        if "酢酸エチル" in stem:
            body = _append_if_fresh(
                body,
                "水溶性かどうかと石油類の区分は別に確認する。",
                max_overlap=0.35,
            )
        if "潤滑油" in stem:
            body = _append_if_fresh(
                body,
                "非水溶性の引火性液体として管理が必要である。",
                max_overlap=0.35,
            )
        if "密度" in stem and "説明" in stem:
            body = _append_if_fresh(
                body,
                "単位はg/cm³などで表す。",
                max_overlap=0.35,
            )
        if "液体の比重" in stem or ("比重" in stem and "液体" in stem):
            body = _append_if_fresh(
                body,
                "第4類では液比重と蒸気比重を区別して覚える。",
                max_overlap=0.35,
            )
        if "ジエチルエーテル" in stem and "性質" in stem:
            body = _append_if_fresh(
                body,
                "引火点が低く、取扱い中の火気・静電気には特に注意が必要である。",
                max_overlap=0.35,
            )
        if "分類学習" in stem and "第4類" in stem:
            body = _append_if_fresh(
                body,
                "代表物質・指定数量・水溶性の有無をセットで整理する。",
                max_overlap=0.35,
            )
        if "屋内貯蔵所" in stem and ("説明" in stem or "正しい" in stem):
            body = _append_if_fresh(
                body,
                "試験では給油取扱所や移送取扱所との区別が問われやすい。",
                max_overlap=0.35,
            )
        if "冷却消火" in stem and "水" in stem:
            body = _append_if_fresh(
                body,
                "水は比熱が大きく、燃焼物の温度低下に有効である。",
                max_overlap=0.35,
            )
        if "密度" in stem and ("式" in stem or "求" in stem):
            body = _append_if_fresh(
                body,
                "単位体積あたりの質量としてg/cm³などで表す。",
                max_overlap=0.35,
            )
        if "密度" in stem and ("600" in body or "750" in body or "0.8" in body):
            body = _append_if_fresh(
                body,
                "数値計算の結果を単位とともに確認する。",
                max_overlap=0.35,
            )
        if "ガソリン" in stem and "浮" in stem:
            body = _append_if_fresh(
                body,
                "液比重が1より小さいと水面上に浮きやすい。",
                max_overlap=0.35,
            )
            body = _append_if_fresh(
                body,
                "蒸気比重や指定数量とは別の物理量である。",
                max_overlap=0.35,
            )
        if "メタノール" in stem and "火災" in stem:
            body = _append_if_fresh(
                body,
                "アルコール類は水溶性でも引火性液体として管理される。",
                max_overlap=0.35,
            )
        if "温度" in stem and "説明" in stem:
            body = _append_if_fresh(
                body,
                "熱量やpHなど他の物理量と混同しない。",
                max_overlap=0.35,
            )
        if "分子" in stem:
            body = _append_if_fresh(
                body,
                "水分子や酸素分子などが代表例である。",
                max_overlap=0.35,
            )
        if "簡易タンク貯蔵所" in stem:
            body = _append_if_fresh(
                body,
                "給油取扱所や移送取扱所とは施設種別が異なる。",
                max_overlap=0.35,
            )
        if "酸化" in stem and "説明" in stem:
            body = _append_if_fresh(
                body,
                "電子の授受で酸化・還元を整理する。",
                max_overlap=0.35,
            )
        if "取扱所" in stem and "該当" in stem:
            body = _append_if_fresh(
                body,
                "屋内タンク貯蔵所・簡易タンク貯蔵所は貯蔵所である。",
                max_overlap=0.35,
            )
        if "アルカリ性" in stem:
            body = _append_if_fresh(
                body,
                "アンモニア水はアルカリ性の代表例である。",
                max_overlap=0.35,
            )
        if "第二石油類" in stem and "組合せ" in stem:
            body = _append_if_fresh(
                body,
                "ガソリン・ベンゼンは第一石油類に該当する。",
                max_overlap=0.35,
            )
        if "第三石油類" in stem and "代表例" in stem:
            body = _append_if_fresh(
                body,
                "ガソリン・ベンゼンは第一石油類、灯油・軽油は第二石油類である。",
                max_overlap=0.35,
            )
        if "第四石油類" in stem:
            body = _append_if_fresh(
                body,
                "重油は第三石油類、ガソリンは第一石油類に該当する。",
                max_overlap=0.35,
            )
        if "動植物油類" in stem and "適切" in stem:
            body = _append_if_fresh(
                body,
                "大豆油・菜種油などが動植物油類の代表例である。",
                max_overlap=0.35,
            )
    if len(body) > _CORRECT_REASON_MAX_LEN:
        body = _truncate_prose_at_sentence(body, _CORRECT_REASON_MAX_LEN)
    return body


def _trim_redundant_correct_closer(body: str, page: dict, cor_idx: int | None) -> str:
    """正答引用が本文に既にあるとき、重複する文を除く。"""
    if not cor_idx or not body:
        return body
    opts = page.get("opts") or []
    if not (1 <= cor_idx <= len(opts)):
        return body
    opt_text = norm(opts[cor_idx - 1]).rstrip("。．")
    opt_core = _normalize_for_compare(opt_text)
    body_before = body

    def _drop_choice_sentence(text: str) -> str:
        pattern = rf"選択肢（{cor_idx}）「[^」]+」は、(.+。)"
        while True:
            m = re.search(pattern, text)
            if not m:
                break
            if _keyword_overlap_ratio(m.group(1), text.replace(m.group(0), "")) >= 0.55:
                text = text.replace(m.group(0), "", 1)
            else:
                break
        return text

    body = _drop_choice_sentence(body)

    body_core = _normalize_for_compare(body)
    stem = norm(page.get("stem_plain") or page.get("stem"))
    if question_ask_mode(stem) != "least_appropriate":
        if opt_core in body_core or len(body) >= 80:
            body = re.sub(
                rf"正答（{cor_idx}）「[^」]+」が、設問が求める内容と一致する。",
                "",
                body,
            )

    return body.rstrip() if body.rstrip() else body_before.rstrip()


def text_to_html(text: str) -> str:
    if not text:
        return ""
    return html.escape(text).replace("\n", "<br>\n")


def parse_explanation_choices(raw: str) -> dict[int, str]:
    """選択肢別解説。形式: 「2:理由;3:理由」または改行区切り「（2）理由」。"""
    out: dict[int, str] = {}
    if not raw:
        return out
    for chunk in re.split(r"[\n;]+", raw):
        chunk = norm(chunk)
        if not chunk:
            continue
        m = re.match(r"^[（(]?(\d+)[）)]?\s*[:：]?\s*(.+)$", chunk)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def question_ask_mode(stem: str) -> str:
    """設問の求め方: most_correct / least_appropriate / truefalse_mark / unknown。"""
    s = norm(stem)
    if re.search(r"「適」を.*「不適」|適切なものには.*不適|不適」を記入", s):
        return "truefalse_mark"
    if re.search(r"適切でない|誤っている|誤りである|正しくない|不適切なもの", s):
        return "least_appropriate"
    if re.search(r"正しい|妥当|適切である|適切なもの", s):
        return "most_correct"
    return "unknown"


def _choice_sounds_positive(text: str) -> bool:
    t = norm(text)
    if not t:
        return False
    positive = (
        r"確認する|整理する|復習|見直|用語|過去問|頻出|公式|記録|学習に役立|効率|押さえ|"
        r"組み合わせ|たどる|ブックマーク|振り返|比較表|一覧"
    )
    negative = r"しない方が|不要|優先する|削除|送信される|連携できない|役立たない|変わらない|固定"
    if re.search(negative, t):
        return False
    return bool(re.search(positive, t))


def _snippet(text: str, max_len: int = 36) -> str:
    t = norm(text)
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"[\s、，。．・]", "", norm(text))


def _parrots_stem(stem: str, body: str) -> bool:
    """正解理由が設問文の言い換え・丸写しに近いか。"""
    s = _normalize_for_compare(stem)
    b = _normalize_for_compare(body)
    if not s or not b:
        return False
    if len(s) >= 24 and s in b:
        return True
    if len(s) >= 16 and b in s and len(b) >= int(len(s) * 0.85):
        return True
    return False


def _ichimon_judgment_clause(statement: str) -> str:
    m = re.search(r"「([^」]+)」", norm(statement))
    if m:
        return m.group(1)
    return norm(statement)


_MIN_CHOICE_NOTE_LEN = 72


def _strip_summary_overlap(summary: str, body: str) -> str:
    sm = dedupe_prose(summary)
    bd = dedupe_prose(body)
    if not sm or not bd:
        return bd
    if sm == bd:
        return ""
    sm_core = sm.rstrip("。")
    if bd.startswith(sm_core):
        rest = bd[len(sm_core) :].lstrip("。、 \n")
        if len(re.sub(r"\s+", "", rest)) < 48:
            return ""
        return rest
    if sm.startswith(bd.rstrip("。")):
        return ""
    sm_first = re.split(r"(?<=[。！？!?])\s*", sm)[0].strip()
    if sm_first and len(sm_first) >= 16 and sm_first in bd:
        rest = bd.replace(sm_first, "", 1).lstrip("。、 \n")
        if len(re.sub(r"\s+", "", rest)) < 48:
            return ""
        return rest
    return bd


_WRONG_NOTE_BOILER_RE = re.compile(
    r"解説の要点[：「][^。]*[。]?|解説の要点は「[^」]*」[^。]*[。]?|"
    r"との違いを、?解説の要点[^。]*[。]?|との違いを確認し直してください[。]?|"
    r"[^。]*が示す論点と一致しません[。]?|"
    r"解説では「[^」]{8,}」とある一方、（\d+）の記述はそれと矛盾します[。]?|"
    r"基準と照らすと正答になりません[。]?|"
    r"制度・手続・学習法のいずれかの観点で適切な内容です[。]?|"
    r"正答の解説と、主体・手続・効果のいずれかが一致していません[。]?|"
    r"両立しない限定語・主体・手順がないか確認してください[。]?|"
    r"[^。]*が示す論点とずれています[。]?"
)


def _strip_wrong_note_boilerplate(note: str, *, context: str = "") -> str:
    """enrich テンプレや正解解説の丸写しを他肢解説から除去する。"""
    n = norm(note)
    if not n:
        return n
    n = _WRONG_NOTE_BOILER_RE.sub("", n)
    n = re.sub(r"\s*正解の要点:\s*", "", n)
    if context:
        ctx_keys = {
            re.sub(r"\s+", "", s)
            for s in re.split(r"(?<=[。！？!?])\s*", dedupe_prose(context))
            if len(re.sub(r"\s+", "", s)) >= 16
        }
        kept: list[str] = []
        for sent in re.split(r"(?<=[。！？!?])\s*", n):
            s = sent.strip()
            if not s:
                continue
            if re.sub(r"\s+", "", s) in ctx_keys:
                continue
            kept.append(s if s.endswith("。") else s + "。")
        n = "".join(kept)
    return dedupe_prose(n.strip(" 。、"))


def _is_enrich_boilerplate_note(note: str) -> bool:
    n = norm(note)
    if not n:
        return False
    if re.search(
        r"基準と照らすと正答になりません|制度・手続・学習法のいずれかの観点|"
        r"正答の解説と、主体・手続・効果|両立しない限定語・主体・手順|"
        r"が示す論点とずれています",
        n,
    ):
        return True
    if not re.search(
        r"解説の要点[：「]|解説の要点は「|が示す論点と一致しません|"
        r"との違いを、?解説の要点|との違いを確認し直してください",
        n,
    ):
        return False
    cleaned = _strip_wrong_note_boilerplate(n)
    return len(cleaned) < _MIN_CHOICE_NOTE_LEN


def _ensure_correct_body(page: dict, row: dict, summary: str, correct_body: str) -> tuple[str, str]:
    """要約との重複除去・設問丸写し時は正答肢ベースで理由を組み立てる。"""
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    summary = dedupe_prose(summary)
    correct_body = _strip_summary_overlap(summary, dedupe_prose(correct_body))
    if summary and correct_body and dedupe_prose(summary) == dedupe_prose(correct_body):
        correct_body = ""
    correct = page.get("correct")
    cor_idx = _correct_choice_index(correct)
    opts = page.get("opts") or []
    opt_text = opts[cor_idx - 1] if cor_idx and 1 <= cor_idx <= len(opts) else ""
    correct_indices = correct_choice_indices(correct)
    numbered = parse_all_inline_choice_notes(
        norm(row.get("explanation")) or correct_body
    )
    if len(correct_indices) > 1 and numbered:
        correct_notes = [
            numbered[i] for i in sorted(correct_indices) if i in numbered
        ]
        if correct_notes:
            correct_body = dedupe_prose(" ".join(correct_notes))
        return summary, correct_body

    if correct_body and not _parrots_stem(stem, correct_body):
        return summary, correct_body
    mode = question_ask_mode(stem)
    parts: list[str] = []
    if correct is not None:
        if mode == "least_appropriate":
            parts.append(
                f"正答（{correct}）は、"
                "設問が問う「最も適切でないもの」に該当します。"
            )
        elif not summary or _is_thin_enrich_summary(summary):
            parts.append(f"正答は（{correct}）です。")
    for src in (
        norm(row.get("explanation_correct")),
        norm(row.get("explanation")),
    ):
        if src and not _parrots_stem(stem, src):
            for sent in re.split(r"(?<=[。！？!?])\s*", src):
                s = sent.strip()
                if not s or _is_thin_enrich_summary(s):
                    continue
                if re.fullmatch(r"正答は\d+[。]?", s):
                    continue
                if s.startswith("正答は") and len(s) < 20:
                    continue
                if len(s) >= 16 and not re.match(r"^（\d+）", s):
                    parts.append(s if s.endswith("。") else s + "。")
                    break
            if len(parts) > (0 if mode == "least_appropriate" else 1):
                break
    rebuilt = dedupe_prose("\n\n".join(parts))
    return summary, rebuilt or correct_body


def _is_substantive_choice_note(note: str) -> bool:
    """短くても試験解説として有用（⇒対比・条文・誤り理由など）。"""
    n = norm(note)
    if not n:
        return False
    if len(n) >= _MIN_CHOICE_NOTE_LEN:
        return True
    if _is_enrich_boilerplate_note(n):
        return False
    if re.search(
        r"⇒|→|第\d+条|誤り|誤っ|正しい|正しく|適切|妥当|届出|認可|不適|適\.|「.+」|解説では|効力なし|効力あり|組合せ",
        n,
    ):
        return True
    return False


def _is_redundant_answer_lead(summary: str, correct: object) -> bool:
    """ページ上部の正答欄と同文のリードを省く。"""
    s = norm(summary)
    if not s or correct is None:
        return False
    cor = norm(str(correct))
    return bool(
        re.fullmatch(rf"正答は[（(]{re.escape(cor)}[）)]です[。]?", s)
        or re.fullmatch(rf"正答は\s*[（(]{re.escape(cor)}[）)]\s*です[。]?", s)
    )


def parse_inline_paren_choice_reasons(text: str) -> dict[int, str]:
    """本文中の (2)理由、(3)理由 形式を肢番号ごとに抽出。"""
    out: dict[int, str] = {}
    if not text:
        return out
    for chunk in re.split(r"(?<=[、,。])\s*(?=[（(]\d+[）)])|(?=^[（(]\d+[）)])", text):
        chunk = norm(chunk).lstrip("、,")
        m = re.match(r"^[（(](\d+)[）)](.+)$", chunk)
        if not m:
            continue
        num = int(m.group(1))
        note = norm(m.group(2)).strip("、。；; ")
        if note:
            out[num] = note
    return out


def _inline_wrong_notes(row: dict) -> dict[int, str]:
    return parse_all_inline_choice_notes(norm(row.get("explanation")))


def _is_thin_enrich_summary(text: str) -> bool:
    n = norm(text)
    if not n:
        return True
    if re.search(r"単独の記述としては妥当|設問全体の正答かどうかは他肢と比較", n):
        return len(n) < 160
    return False


def _substantive_explanation_lead(row: dict) -> str:
    for key in ("explanation", "explanation_correct"):
        src = norm(row.get(key))
        if not src:
            continue
        m = re.search(r"正答は[^。]+。", src)
        if m and len(m.group(0)) >= 20:
            return m.group(0)
        for sent in re.split(r"(?<=[。！？!?])\s*", src):
            s = sent.strip()
            if len(s) >= 24 and not _is_thin_enrich_summary(s):
                return s if s.endswith("。") else s + "。"
    return ""


def _keyword_tokens(text: str) -> set[str]:
    return set(
        re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}", _normalize_for_compare(text))
    )


def _keyword_overlap_ratio(a: str, b: str) -> float:
    ta, tb = _keyword_tokens(a), _keyword_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _overlaps_correct_choice_text(text: str, page: dict) -> bool:
    cor_idx = _correct_choice_index(page.get("correct"))
    opts = page.get("opts") or []
    if not cor_idx or not text or not (1 <= cor_idx <= len(opts)):
        return False
    opt = opts[cor_idx - 1]
    if _keyword_overlap_ratio(text, opt) >= 0.5:
        return True
    nt, no = _normalize_for_compare(text), _normalize_for_compare(opt)
    return len(nt) >= 24 and len(no) >= 24 and (nt in no or no in nt)


def _compact_wrong_note_vs_choice(choice_text: str, note: str) -> str:
    """他肢解説が選択肢全文と酷似する場合、対比だけに短縮する。"""
    opt, n = norm(choice_text), norm(note)
    if not opt or not n or _keyword_overlap_ratio(n, opt) < 0.5:
        return note
    flips = (
        (r"小さい", r"大きい"),
        (r"低い", r"高い"),
        (r"少ない", r"多い"),
    )
    for wpat, rpat in flips:
        wm = re.search(wpat, opt)
        rm = re.search(rpat, n)
        if wm and rm:
            return f"「{wm.group(0)}」とあるが、正しくは「{rm.group(0)}」の関係です。"
    if re.search(r"反映する|適している|最も適", opt) and re.search(r"反映しない", n):
        return (
            "RMRは動的筋作業向けの指標であり、"
            "精神的・静的作業の負担は正確に反映されません。"
        )
    if re.search(r"全く無関係|常に一定", opt):
        return "基礎代謝量は体格・性別・年齢等の影響を受けます（「全く一定」は誤り）。"
    return note


def _pick_explanation_lead(page: dict, row: dict, summary: str) -> str:
    """正答肢と重複するリードは出さない。"""
    candidates: list[str] = []
    if summary and not _is_thin_enrich_summary(summary):
        candidates.append(summary)
    lead = _substantive_explanation_lead(row)
    if lead:
        candidates.append(lead)
    for cand in candidates:
        if cand and not _overlaps_correct_choice_text(cand, page):
            return cand
    return ""


def _strip_choice_echo(note: str, choice_text: str, choice_num: int) -> str:
    """選択肢見出しと重複する引用・肢番号付きリードを除去。"""
    n = norm(note)
    if not n:
        return n
    if re.match(rf"^（{choice_num}）(?:の内容は|は)", n):
        return n
    snip = _snippet(choice_text, 48)
    patterns = [
        rf"^（{choice_num}）「{re.escape(snip)}[^」]*」は、?",
        rf"^（{choice_num}）「[^」]+」は、?",
    ]
    for pat in patterns:
        n2 = re.sub(pat, "", n).strip()
        if n2 != n:
            n = n2
            break
    if snip and snip in n and len(n) < len(note) * 0.85:
        # 見出しと同じ長文引用が本文に残る場合は、対比以降だけ残す
        m = re.search(r"(⇒|→).+", n)
        if m:
            n = m.group(0).strip()
    return n.strip(" 。、")


def _is_thin_choice_note(note: str, mode: str) -> bool:
    """CSV の選択肢別解説が形式的・短すぎるか（読み手向けの価値が低い）。"""
    n = norm(note)
    if not n:
        return True
    if _is_substantive_choice_note(n):
        return False
    if len(n) < _MIN_CHOICE_NOTE_LEN:
        return True
    if mode == "least_appropriate":
        if re.search(r"本肢.*妥当|正しい学習|推奨される学習", n) and len(n) < 140:
            if not re.search(
                r"最も適切でない|正答は[（(]?\d|学習効果.*損|有害|放棄|誤った記述",
                n,
            ):
                return True
        if re.search(r"設問形式の読み違えに注意", n) and len(n) < 100:
            return True
    if mode == "most_correct" and re.search(r"本肢を選ぶ場合は、設問が", n):
        return True
    if re.search(r"本問で選ぶべき正答は[（(]?\d", n):
        return len(n) < _MIN_CHOICE_NOTE_LEN
    if re.search(r"単独の記述としては法令上妥当", n):
        return True
    if re.search(r"が示す論点とずれています", n) and len(n) < 200:
        return True
    if re.search(r"基準と照らすと正答になりません", n):
        return True
    return False


def _choice_specific_lead(
    choice_num: int,
    opt: str,
    *,
    mode: str,
    correct: object,
    correct_text: str,
    category: str,
) -> str:
    """肢ごとに異なる冒頭文（同一テンプレ連発を防ぐ）。"""
    snip = _snippet(opt, 36)
    if mode == "least_appropriate" and _choice_sounds_positive(opt):
        return (
            f"（{choice_num}）「{snip}」は単体では妥当な学習法・対応に当たります。"
            "「最も適切でないもの」として選ぶ正答にはなりません。"
        )
    if mode == "least_appropriate":
        return (
            f"（{choice_num}）「{snip}」は一見もっともらしいですが、"
            f"正答（{correct}）「{_snippet(correct_text, 40)}」ほど"
            "学習・制度・実務の観点で問題がある記述ではありません。"
        )
    if mode == "most_correct":
        if correct_text:
            return (
                f"（{choice_num}）「{snip}」は、"
                f"正答（{correct}）「{_snippet(correct_text, 44)}」とは異なる内容です。"
            )
        return (
            f"（{choice_num}）「{snip}」は、本問の正答（{correct}）とは論点が異なります。"
        )
    return (
        f"（{choice_num}）「{snip}」は、設問の求め方と照らすと正答になりません。"
    )


def _wrong_choice_absolute_hint(opt: str) -> str:
    """絶対表現・言い過ぎがあるときの短文ヒント。"""
    if re.search(r"必ず|常に|すべて|全く|だけ|のみ", opt):
        return (
            "「必ず」「常に」「全く」などの断定は、例外や条件付きの整理と食い違うことが多いです。"
            "設問が問う論点と照らして、言い過ぎ・取り違えがないか確認してください。"
        )
    if re.search(r"ない$|しない$|不要|できない|設けない", opt):
        return (
            "否定や「不要」「できない」の言い切りが、正答が示す要件・リスク・手続と矛盾していないか確認してください。"
        )
    return ""


def _wrong_choice_correct_hint(correct_body: str) -> str:
    for sent in re.split(r"(?<=[。！？!?])\s*", dedupe_prose(correct_body)):
        s = sent.strip()
        if len(s) >= 16:
            return s if s.endswith("。") else s + "。"
    return ""


def infer_wrong_choice_note(
    page: dict,
    choice_num: int,
    choice_text: str,
    row: dict,
) -> str:
    """CSV に explanation_choices が無いとき、選択肢文から読み手向けの解説を組み立てる。"""
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    mode = question_ask_mode(stem)
    opt = norm(choice_text)
    correct = page.get("correct")
    numbered = parse_all_inline_choice_notes(norm(row.get("explanation")))
    if choice_num in numbered and _is_substantive_choice_note(numbered[choice_num]):
        return dedupe_prose(numbered[choice_num])

    multi_pick = len(correct_choice_indices(correct)) > 1
    if multi_pick and mode == "most_correct":
        if numbered.get(choice_num):
            return dedupe_prose(numbered[choice_num])
        return dedupe_prose(
            f"（{choice_num}）は正答（{correct}）に含まれないため、この設問の正解の組合せにはなりません。"
            "届出・認可・期限・主体など、正答肢と異なる要件がないか確認してください。"
        )

    correct_text = ""
    cor_idx = _correct_choice_index(correct)
    opts = page.get("opts") or []
    if cor_idx is not None and 1 <= cor_idx <= len(opts):
        correct_text = opts[cor_idx - 1]
    correct_body = norm(row.get("explanation_correct")) or norm(row.get("explanation")) or ""
    category = norm(page.get("category") or "")

    parts: list[str] = [_choice_specific_lead(
        choice_num,
        opt,
        mode=mode,
        correct=correct,
        correct_text=correct_text,
        category=category,
    )]

    if mode == "least_appropriate" and _choice_sounds_positive(opt):
        parts.append(
            f"「{opt}」は、単体では適切な学習法・正しい対応に当たります。"
            "したがって「最も適切でないもの」として選ぶ正答にはなりません。"
        )
        if correct and correct_text:
            parts.append(
                f"本問の正答は（{correct}）「{_snippet(correct_text, 56)}」です。"
                "この記述は、学習効果を著しく損ねる・明らかに誤った方針であり、"
                "他の肢より「最も不適切」と言えます。"
            )
        parts.append(
            "よくある誤解は、「正しい学習法か」で各肢を判断してしまい、"
            "（4）のような明らかに有害な記述を見落とすことです。"
            "設問文の「最も適切でない」を先に線引きし、四肢を比較して選んでください。"
        )
    elif mode == "least_appropriate":
        parts.append(
            "「最も適切でない」形式では、正しそうな肢が複数あることがあります。"
            "各肢の主語・客体・数字・期限・手続の順序が設問条件と合うかを確認し、"
            "最も不適切な一つだけを選びます。"
        )
    elif mode == "most_correct":
        if not multi_pick and correct and correct_text:
            parts.append(
                f"本問で選ぶべき正答は（{correct}）「{_snippet(correct_text, 56)}」です。"
                "この肢の記述は、その論点とは一致しません。"
            )
        abs_hint = _wrong_choice_absolute_hint(opt)
        if abs_hint:
            parts.append(abs_hint)
        hint = _wrong_choice_correct_hint(correct_body)
        if hint and hint not in "".join(parts):
            hint_core = hint.rstrip("。．.!！?？")
            parts.append(
                f"正答の根拠は「{_snippet(hint_core, 60)}」です。"
                "誤答肢との差分を一行メモに残してください。"
            )
    else:
        parts.append(
            "設問文の「正しいもの／誤っているもの／最も適切でないもの」を"
            "先に確認してから、各肢を読み直してください。"
        )

    rules: list[tuple[str, str]] = [
        (
            r"口コミ|SNS|ブログ|噂",
            "受験制度・出題範囲・合格基準の正誤は、実施団体の公式発表が基準です。"
            "口コミは参考程度にとどめ、日程・範囲・申込方法は必ず公式サイトや受験案内で確認してください。",
        ),
        (
            r"毎年|常に|固定|変わらない|前年と同じ",
            "試験日程・出題範囲・申込方法は改定されることがあります。"
            "「一度確認すれば十分」と決めつけると、変更の見落としや学習範囲のズレにつながります。",
        ),
        (
            r"生成済み|直接編集|手編集|JSだけ",
            "公開用データは CSV とビルドスクリプトを正本にすると、再生成・検証・本番同期が一貫します。"
            "生成物だけを手修正すると、次回ビルドで上書きされたり、テンプレと本番の差分が残りやすくなります。",
        ),
        (
            r"列名は自由|列名.*変え",
            "CSV 列名はツールの検証・変換と対応しています。"
            "任意の列名に変えると、ビルドやリンク検証が失敗し、静的ページとアプリ用データの整合が崩れます。",
        ),
        (
            r"ドメイン.*不要|設定は不要",
            "canonical・サイトマップ・OGP には正しいドメイン（siteOrigin）が必要です。"
            "プレースホルダーのままでは検索エンジンと SNS プレビューで URL が誤って扱われます。",
        ),
        (
            r"削除される|送信される|連携できない",
            "本テンプレートでは、学習履歴はブラウザ内保存を基本とし、復習・ブックマーク・用語解説へつなげる設計です。"
            "この肢の断定は、実際の仕様（ローカル保存・関連ページ）と一致しません。",
        ),
        (
            r"図表|比較.*役立たない",
            "関連制度の違いや数値・期限は、表や比較で整理すると混同が減ります。"
            "特に設備・税務・手続き分野では、一覧表を自作して見直すと得点しやすくなります。",
        ),
        (
            r"記録しない|参照しない",
            "苦手分野や混同しやすい用語を記録しておくと、復習の優先順位がつけられます。"
            "用語の定義を飛ばすと、設問の前提（誰が・何を・どこまで）を取り違えやすくなります。",
        ),
        (
            r"二度と見直さない|見直さない",
            "誤答した問題を放置すると、同じパターンのミスが本番まで残ります。"
            "復習リストや間隔を空けた解き直しで、弱点を可視化することが重要です。",
        ),
    ]
    for pattern, msg in rules:
        if re.search(pattern, opt):
            if not any(re.search(pattern, p) for p in parts):
                parts.append(msg)
            break

    if len(parts) < 2:
        parts.append(
            f"正答（{correct}）との差分を一行メモに残し、同分野の過去問・実践演習で解き直すと定着しやすくなります。"
        )

    return dedupe_prose("\n\n".join(parts))


def _wrong_note_context(page: dict, row: dict) -> str:
    parts = [
        norm(row.get("explanation_summary")),
        norm(row.get("explanation_correct")),
        norm(row.get("explanation")),
    ]
    return dedupe_prose(" ".join(p for p in parts if p))


def _brief_wrong_note_from_choice(choice_text: str) -> str:
    opt = norm(choice_text)
    if not opt:
        return ""
    if re.search(r"全く無関係|常に一定|必ず.*同じ|影響は少ない|影響はない", opt):
        return (
            "「全く無関係」「常に一定」などの限定が実態と異なります。"
            "数値・主体・条件の取り違えがないか確認してください。"
        )
    if re.search(r"小さい|低い|少ない|不要|しない", opt):
        m = re.search(r"(小さい|低い|少ない)", opt)
        if m:
            return (
                f"「{m.group(1)}」という方向が実際と逆、または限定が強すぎる記述です。"
                "正答の論点と数値・程度の関係を照合してください。"
            )
    return ""


def resolve_wrong_choice_note(
    page: dict,
    choice_num: int,
    choice_text: str,
    row: dict,
    *,
    csv_note: str = "",
    correct_body: str = "",
) -> str:
    """CSV / O4 原文優先。約200字の非重複解説に整える。"""
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    mode = question_ask_mode(stem)
    context = _wrong_note_context(page, row)
    inline = _inline_wrong_notes(row)
    brief = _brief_wrong_note_from_choice(choice_text)

    base = norm(csv_note)
    if base and _is_generic_wrong_note(base):
        base = ""
    if base and re.search(r"が示す論点とずれています", base):
        base = ""

    if not base and choice_num in inline:
        inl = _strip_choice_verdict_prefix(inline[choice_num])
        if inl and not re.match(r"^正しい", inl):
            base = inl

    if not base:
        inferred = infer_wrong_choice_note(page, choice_num, choice_text, row)
        base = _strip_wrong_note_boilerplate(
            _strip_choice_echo(inferred, choice_text, choice_num),
            context=context,
        )
    elif _is_thin_choice_note(base, mode) or _is_enrich_boilerplate_note(base):
        inferred = infer_wrong_choice_note(page, choice_num, choice_text, row)
        if inferred:
            base = _strip_wrong_note_boilerplate(
                _strip_choice_echo(inferred, choice_text, choice_num),
                context=context,
            )

    if brief and (not base or _is_thin_choice_note(base, mode)):
        base = brief

    base = _strip_choice_echo(base, choice_text, choice_num)
    return _compose_wrong_choice_note(
        page, row, choice_num, choice_text, base, correct_body
    )


CATEGORY_STUDY_HINTS: dict[str, str] = {
    "法令・制度": (
        "試験制度・受験要件は年度ごとに見直されることがあります。"
        "受験要項・実施要領・合格発表の公式ページをブックマークし、改定年度は出題範囲表と学習計画を更新してください。"
        "用語解説で「受験資格」「試験要項」「公式情報」などの定義を押さえたうえで、"
        "同年・前後年度の過去問で出題パターンを確認すると、制度問題と実務問題のつながりが整理できます。"
        "模試・実践演習の前には、最新の公式情報を再確認する習慣を入れておくと安心です。"
    ),
    "契約・実務": (
        "実務・学習法の問題は、「誰が・何を・どこまで」が適切か、または「最も適切でないもの」かを"
        "設問文で切り替えて読むことが重要です。間違えた問題は復習リストに残し、"
        "正答・誤答それぞれについて「どの条件を満たさないか」を一文で書き出してください。"
        "関連ガイド（学習計画・過去問の進め方）と用語解説を往復すると、"
        "単発の暗記ではなく判断基準として定着しやすくなります。"
    ),
    "設備・その他": (
        "数値・期限・例外規定は、暗記だけでは混同しやすいです。"
        "自分用の比較表（単位・条件・責任者・手続の順序）を作り、週次で見直してください。"
        "分野別の用語一覧から関連語をたどり、過去問一覧で出題傾向を確認する流れが効率的です。"
        "実践演習で時間配分を測ったあと、間違えた設問だけ過去問の同分野に戻ると弱点がはっきりします。"
    ),
    "基礎・役割": (
        "管理監督者の役割・法令の趣旨・ストレスの基礎は、用語の定義と"
        "「誰が・何を・どこまで」がセットで出題されます。"
        "間違えた肢ごとに、正答との差分（根拠法令・対象範囲・責任の所在）をメモし、"
        "関連用語から同分野の過去問・実践演習を解き直してください。"
    ),
    "職場環境・配慮": (
        "職場の配慮・リスク要因は、具体策と「誰が担うか」を対にして覚えると得点しやすくなります。"
        "数値基準や手順は表に整理し、同年の過去問で実務イメージを補強してください。"
        "一問一答で用語の定義を確認してから、記述式に近い過去問に戻ると理解が深まります。"
    ),
    "相談・連携・復職": (
        "面談・医療連携・復職支援は、手順と禁止事項（やってはいけないこと）の区別が重要です。"
        "正答肢のキーワードを用語解説で確認し、同分野の過去問でケースのパターンを増やしてください。"
        "「最も不適切」形式では、一見正しそうな肢に惑わされないよう、設問文を先にマークする習慣をつけましょう。"
    ),
    "関係法令": (
        "法令・制度は条文の趣旨と数字・期限をセットで覚えると得点しやすくなります。"
        "関連用語を用語解説で押さえ、同年の過去問で「例外」「罰則」「手続」の組み合わせを確認してください。"
        "公式情報の更新時期は学習カレンダーに入れておくと、直前期の取りこぼしを防げます。"
    ),
    "労働衛生": (
        "衛生・安全は用語の定義と数値基準の組み合わせが多いです。"
        "間違えた問題は復習リストに残し、用語解説で意味を確認しながら解き直してください。"
        "図や表で「基準値・測定・記録義務」を一覧化すると、本番直前の確認が短くなります。"
    ),
    "労働生理": (
        "生理・人体は図解と用語の対応づけが有効です。"
        "分野別の用語一覧から関連語をたどり、過去問で「原因・対策・禁忌」のセットで復習してください。"
    ),
    "賃貸住宅管理業法": (
        "業法は「誰が・何を・どこまで」がセットで問われます。"
        "正答肢の義務主体と手続の流れをメモし、似た制度との違いを表に整理してから、"
        "同年・前後年度の過去問で定着を確認してください。"
    ),
    "民法・借地借家法": (
        "借地借家・民法改正は、権利関係の主体と効果の発生時期を一文で説明できるかが要点です。"
        "間違えた肢は正答と「誰に・いつ・どの効果が及ぶか」で対比してください。"
    ),
    "賃貸借契約": (
        "契約条項・個人情報・原状回復は、条文の趣旨と実務上の判断基準の両方が問われます。"
        "数字・期限・例外は一覧表にし、他の選択肢との差分を意識して復習してください。"
    ),
    "賃貸借契約実務": (
        "実務問題は「適切な対応か」「義務の範囲か」を区別する設問が多いです。"
        "誤答肢がどの要件を満たさないかを具体的に書き出すと定着します。"
    ),
    "賃貸不動産経営": (
        "経営・管理では、貸主・借主・管理者の視点の違いがポイントです。"
        "「最も不適切」形式では、一見正しそうな肢こそ見落としやすいので、設問文を再確認してください。"
    ),
    "管理実務": (
        "管理実務は手続の順序と義務の主体が問われやすいです。"
        "間違えた問題は復習リストに残し、同分野の用語とセットで解き直してください。"
    ),
    "建物・設備": (
        "設備・維持保全は数値基準・点検周期・責任の所在がセットで出題されます。"
        "他選択肢がどの要件（数値・主体・手続）とずれているかを確認してください。"
    ),
    "会計・税金・保険": (
        "税務・会計は計算の前提と課税関係者・時期の取り違えに注意です。"
        "誤答肢がどの前提を誤っているかを明示して復習してください。"
    ),
    "会計税務": (
        "税務・会計は計算の前提と課税関係者・時期の取り違えに注意です。"
        "誤答肢がどの前提を誤っているかを明示して復習してください。"
    ),
    "サブリース": (
        "サブリースは貸主・転貸人・借主の関係と契約上の効果の区別が要点です。"
        "誤答肢がどの関係を取り違えているかを確認してください。"
    ),
    "原状回復": (
        "原状回復は費用負担・範囲・特約の有無が問われやすいです。"
        "正答肢の要件を押さえ、他肢との差分を整理してください。"
    ),
    "賃料管理・督促": (
        "賃料・督促は手続の順序と法的効果の対応が重要です。"
        "誤答肢がどの段階・要件を誤っているかを確認してください。"
    ),
    "関連法令": (
        "関連法令は本試験の主たる論点と位置づけの違いが問われます。"
        "根拠法令名と趣旨をセットで覚えてください。"
    ),
    "政策課題・社会情勢": (
        "政策・社会情勢は制度の目的と論点の組み合わせが出題されます。"
        "公式の考え方・用語の定義を確認したうえで復習してください。"
    ),
}

DEFAULT_STUDY_HINT = (
    "この問題で間違えた場合は、設問文の求め方（「正しいもの」「誤っているもの」「最も適切でないもの」）を"
    "最初に線引きしてください。正答・誤答それぞれについて、用語の定義と制度の前提を用語解説で確認し、"
    "復習リストや実践演習・一問一答と組み合わせて、同分野の過去問を解き直すと定着しやすくなります。"
)


def _is_template_study_hint(text: str) -> bool:
    t = dedupe_prose(text)
    if not t:
        return True
    if t == DEFAULT_STUDY_HINT:
        return True
    return t in CATEGORY_STUDY_HINTS.values()


def _hint_should_skip_explanation_tail(page: dict, row: dict) -> bool:
    """各肢解説・組合せ解説に explanation が既出なら、ヒントへ同文を足さない。"""
    mode = _extended_question_mode(page, row)
    if mode in {"truefalse_group", "combination", "multi"}:
        return True
    exp = norm(row.get("explanation"))
    if exp and parse_all_inline_choice_notes(exp):
        return True
    return False


def build_study_hint(page: dict, row: dict) -> str:
    point = norm(row.get("explanation_point"))
    if point and not _is_template_study_hint(point):
        return dedupe_prose(point)

    stem = norm(
        page.get("stem_plain")
        or page.get("stem")
        or page.get("statement")
        or row.get("question")
        or ""
    )
    category = norm(page.get("category") or "")
    parts: list[str] = []
    if category:
        parts.append(f"分野「{category}」の問題です。")

    mode = question_ask_mode(stem)
    if mode == "least_appropriate":
        parts.append(
            "「最も適切でないもの」を問う設問では、四肢を比較して最も問題のある一つを選びます。"
        )
    elif mode == "truefalse_mark":
        parts.append(
            "各記述を「適」「否」で判定します。⇒ の対比表現や限定語の取り違えに注意してください。"
        )
    elif mode == "most_correct":
        parts.append("正しいものを問う設問では、限定語・主体・手続の条件を順に確認します。")

    if page.get("statement") is not None or row.get("question"):
        clause = _ichimon_judgment_clause(stem)
        ans = "○" if page.get("correct_answer") else "×"
        parts.append(f"判断対象は「{_snippet(clause, 40)}」。正答は {ans} です。")
    elif page.get("correct") is not None:
        parts.append(
            "誤った肢は、どの条件・主体・数字がずれているかを一行メモしてください。"
        )

    for src in (norm(row.get("explanation_correct")), norm(row.get("explanation"))):
        if _hint_should_skip_explanation_tail(page, row):
            break
        if not src:
            continue
        for sent in re.split(r"(?<=[。！？!?])\s*", src):
            s = sent.strip()
            if len(s) >= 18 and not _parrots_stem(stem, s):
                parts.append(s if s.endswith("。") else s + "。")
                break
        if len(parts) >= 3:
            break

    if len(parts) >= 2:
        return dedupe_prose("".join(parts))

    cat_hint = CATEGORY_STUDY_HINTS.get(category)
    if cat_hint:
        return dedupe_prose(_snippet(cat_hint, 180))

    return dedupe_prose("".join(parts)) if parts else DEFAULT_STUDY_HINT


def split_legacy_explanation(exp: str) -> tuple[str, str]:
    m = re.match(r"^正解は\s*(\d+)\s*です[。.]?\s*(.*)$", exp, re.DOTALL)
    if m:
        body = norm(m.group(2)) or exp
        summary = f"正答は（{m.group(1)}）です。"
        return summary, body
    return "", exp


def parse_combination_slots(raw: str) -> dict[str, int]:
    """A-8;B-3;C-4;D-7 → {'A': 8, 'B': 3, ...}"""
    out: dict[str, int] = {}
    for part in norm(raw).split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([A-Za-zア-オ甲乙①-⑫])-(\d+)$", part)
        if m:
            out[m.group(1).upper()] = int(m.group(2))
    return out


def parse_truefalse_group_labels(raw: str) -> dict[str, set[int]]:
    """適-2,3;不適-1 → {'適': {2,3}, '不適': {1}}"""
    out: dict[str, set[int]] = {}
    for part in norm(raw).split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^([^-]+)-(.+)$", part)
        if not m:
            continue
        label = norm(m.group(1))
        nums: set[int] = set()
        for chunk in m.group(2).split(","):
            n = _parse_choice_num(chunk)
            if n is not None:
                nums.add(n)
        if label and nums:
            out[label] = nums
    return out


def _truefalse_display_label(raw_label: str) -> str:
    if raw_label in {"適", "正"}:
        return "適"
    if raw_label in {"不適", "否", "誤"}:
        return "否"
    return raw_label


def _extended_question_mode(page: dict, row: dict) -> str:
    typ = norm(page.get("type"))
    if typ in {"combination", "truefalse_group", "multi"}:
        return typ
    cor = norm(row.get("correct")) or norm(str(page.get("correct") or ""))
    from tools.correct_answer_format import detect_correct_format

    fmt = detect_correct_format(cor)
    if fmt in {"combination", "truefalse_group", "multi"}:
        return fmt
    return "single"


def build_combination_explanation_html(page: dict, row: dict) -> str:
    """穴埋め組合せ — 語句バンク（１～８）を他肢として並べない。"""
    base = norm(row.get("explanation")) or "（解説は未入力です。）"
    correct_raw = norm(str(page.get("correct") or row.get("correct") or ""))
    slots = parse_combination_slots(correct_raw)
    opts = page.get("opts") or []
    parts: list[str] = ['<div class="q-exp">']

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-correct-h">'
        '<h3 id="q-exp-correct-h" class="q-exp-h3">正解の組合せ</h3>'
    )
    if slots:
        lis = []
        for slot in sorted(slots.keys()):
            num = slots[slot]
            word = opts[num - 1] if 1 <= num <= len(opts) else ""
            lis.append(
                f'<li class="q-exp-choice-item">'
                f'<p><strong>{html.escape(slot)}</strong> '
                f"→ <strong>（{num}）</strong> {html.escape(word)}</p></li>"
            )
        parts.append(f'<ul class="q-exp-choice-list">{"".join(lis)}</ul>')
    summary = norm(row.get("explanation_summary")) or norm(row.get("explanation_correct"))
    body = summary or base
    parts.append(f"<p>{text_to_html(body)}</p></section>")

    parts.append("</div>")
    return "\n    ".join(parts)


def build_truefalse_group_explanation_html(page: dict, row: dict) -> str:
    """適/否を記入する記述群 — 各肢ごとに判定と解説を示す。"""
    base = norm(row.get("explanation")) or "（解説は未入力です。）"
    correct_raw = norm(str(page.get("correct") or row.get("correct") or ""))
    labels = parse_truefalse_group_labels(correct_raw)
    numbered = parse_numbered_choice_notes(base)
    opts = page.get("opts") or []

    idx_to_label: dict[int, str] = {}
    for raw_label, nums in labels.items():
        disp = _truefalse_display_label(raw_label)
        for n in nums:
            idx_to_label[n] = disp

    parts: list[str] = ['<div class="q-exp">']

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-stmts-h">'
        '<h3 id="q-exp-stmts-h" class="q-exp-h3">各記述の解説</h3>'
        '<ul class="q-exp-choice-list">'
    )
    for i, _opt in enumerate(opts, start=1):
        verdict = idx_to_label.get(i, "")
        note = numbered.get(i) or ""
        if not note and verdict == "適":
            continue
        badge = (
            f'<span class="q-marubatsu q-tf-verdict">{html.escape(verdict)}</span> '
            if verdict
            else ""
        )
        parts.append(
            f'<li class="q-exp-choice-item">'
            f'<p class="q-exp-choice-head">'
            f'<span class="q-exp-choice-num">（{i}）</span> {badge}</p>'
        )
        if note:
            parts.append(f'<p class="q-exp-choice-note">{text_to_html(note)}</p>')
        parts.append("</li>")
    parts.append("</ul></section>")

    parts.append("</div>")
    return "\n    ".join(parts)


def _wrong_note_dedupe_key(note: str) -> str:
    """肢番号・長い選択肢引用を除いた比較用キー。"""
    n = norm(note)
    if re.search(r"正しくは「|の関係です", n) and len(n) < 80:
        return _normalize_for_compare(n)
    n = re.sub(r"（\d+）", "", n)
    n = re.sub(r"「[^」]{20,}」", "", n)
    return _normalize_for_compare(n)


def _is_generic_wrong_note(note: str) -> bool:
    n = norm(note)
    if not n or len(n) < 48:
        return True
    if _is_enrich_boilerplate_note(n):
        return True
    generic_markers = (
        r"一見もっともらしい",
        r"学習・制度・実務の観点",
        r"記述自体としては正しい",
        r"最も適切でない.*形式では、正しそうな肢",
        r"正答の論点（.+）と両立しない",
        r"が示す論点とずれています",
        r"単体では適切な学習法・正しい対応",
        r"設問形式の読み違え",
        r"単独の記述としては法令上妥当",
        r"問題文の条件（",
        r"基準と照らすと正答になりません",
        r"制度・手続・学習法のいずれかの観点",
        r"正答の解説と、主体・手続・効果",
        r"両立しない限定語・主体・手順",
    )
    return any(re.search(p, n) for p in generic_markers)


def _consolidated_wrong_choices_note(
    page: dict, row: dict, wrong_nums: list[int]
) -> str:
    stem = norm(page.get("stem_plain") or page.get("stem") or "")
    mode = question_ask_mode(stem)
    correct = page.get("correct")
    if mode == "least_appropriate":
        return (
            "いずれも、単体では適切な記述に当たります。"
            f"本問は「最も適切でないもの」を選ぶ形式のため、正答は（{correct}）です。"
            "四肢を比較し、最も不適切な一つだけを選びます。"
        )
    return (
        f"いずれも、正答（{correct}）とは異なる論点です。"
        "設問の条件と照らし、正答に最も合う肢を選び直してください。"
    )


def collapse_wrong_choice_items(
    page: dict, row: dict, items: list[tuple[int, str, str]]
) -> list[tuple[str, str]]:
    """同一解説文の肢をまとめ、汎用テンプレの連打を防ぐ。"""
    if not items:
        return []
    groups: list[dict] = []
    index: dict[str, int] = {}
    for num, _opt, note in items:
        key = _wrong_note_dedupe_key(note)
        if key not in index:
            index[key] = len(groups)
            groups.append({"nums": [num], "note": note})
        else:
            groups[index[key]]["nums"].append(num)
    collapsed: list[tuple[str, str]] = []
    for group in groups:
        nums = sorted(group["nums"])
        label = "、".join(str(n) for n in nums)
        note = group["note"]
        if len(nums) > 1 and _is_generic_wrong_note(note):
            note = _consolidated_wrong_choices_note(page, row, nums)
        collapsed.append((label, note))
    return collapsed


def build_choice_commentary(
    page: dict, row: dict, *, correct_body: str = ""
) -> list[tuple[int, str, str]]:
    mode = _extended_question_mode(page, row)
    if mode in {"combination", "truefalse_group"}:
        return []
    parsed = parse_explanation_choices(norm(row.get("explanation_choices")))
    numbered = parse_all_inline_choice_notes(norm(row.get("explanation")))
    correct = page.get("correct")
    correct_indices = correct_choice_indices(correct)
    items: list[tuple[int, str, str]] = []
    for i, opt in enumerate(page["opts"], start=1):
        if page.get("is_invalidated") or correct is None:
            continue
        if i in correct_indices:
            continue
        csv_note = parsed.get(i) or numbered.get(i) or ""
        note = resolve_wrong_choice_note(
            page, i, opt, row, csv_note=csv_note, correct_body=correct_body
        )
        items.append((i, opt, note))
    return items


def build_explanation_html(page: dict, row: dict) -> str:
    base = norm(row.get("explanation")) or "（解説は未入力です。）"
    if page.get("is_invalidated") or page.get("correct") is None:
        return f'<div class="q-exp"><p>{text_to_html(base)}</p></div>'

    mode = _extended_question_mode(page, row)
    if mode == "combination":
        return build_combination_explanation_html(page, row)
    if mode == "truefalse_group":
        return build_truefalse_group_explanation_html(page, row)

    summary = norm(row.get("explanation_summary"))
    correct_body = norm(row.get("explanation_correct"))
    point = norm(row.get("explanation_point"))

    if not summary and not correct_body and not point:
        leg_summary, leg_body = split_legacy_explanation(base)
        summary = summary or leg_summary
        correct_body = correct_body or leg_body

    summary, correct_body = _ensure_correct_body(page, row, summary, correct_body)
    summary = _pick_explanation_lead(page, row, summary)
    if summary and correct_body and _normalize_for_compare(summary) == _normalize_for_compare(
        correct_body
    ):
        correct_body = ""
    elif correct_body and _is_thin_enrich_summary(correct_body):
        cb = _substantive_explanation_lead(row) or correct_body
        correct_body = "" if _overlaps_correct_choice_text(cb, page) else cb
    elif correct_body and _overlaps_correct_choice_text(correct_body, page):
        correct_body = ""
    if summary and correct_body:
        sm = _normalize_for_compare(summary)
        kept: list[str] = []
        for part in re.split(r"\n\n+", correct_body):
            p = norm(part)
            if not p:
                continue
            pn = _normalize_for_compare(p)
            if pn == sm or pn in sm or sm in pn:
                continue
            if re.fullmatch(r"正答は[（(]?\d+[）)]?です[。]?", p):
                continue
            kept.append(p if p.endswith("。") else p + "。")
        correct_body = dedupe_prose("\n\n".join(kept))

    parts: list[str] = ['<div class="q-exp">']
    correct = page.get("correct")
    if correct and not page.get("is_invalidated"):
        correct_indices = correct_choice_indices(correct)
        correct_body = _compose_correct_reason(page, row, correct_body)
        numbered = parse_all_inline_choice_notes(norm(row.get("explanation")))
        correct_inner: list[str] = []
        if len(correct_indices) > 1:
            if correct_body and not numbered:
                correct_inner.append(f"<p>{text_to_html(correct_body)}</p>")
            for idx in sorted(correct_indices):
                note = numbered.get(idx) or ""
                if note:
                    correct_inner.append(
                        f'<p class="q-exp-correct-opt"><strong>（{idx}）</strong> '
                        f"{text_to_html(note)}</p>"
                    )
        elif correct_body:
            correct_inner.append(f"<p>{text_to_html(correct_body)}</p>")
        if correct_inner:
            parts.append(
                '<section class="q-exp-section" aria-labelledby="q-exp-correct-h">'
                '<h3 id="q-exp-correct-h" class="q-exp-h3">正解の理由</h3>'
            )
            parts.extend(correct_inner)
            parts.append("</section>")

        wrong_items = collapse_wrong_choice_items(
            page, row, build_choice_commentary(page, row, correct_body=correct_body)
        )
        if wrong_items:
            lis = "".join(
                f'<li class="q-exp-choice-item">'
                f'<p class="q-exp-choice-head">'
                f'<span class="q-exp-choice-num">（{nums}）</span></p>'
                f'<p class="q-exp-choice-note">{text_to_html(_strip_wrong_note_head_num(note))}</p></li>'
                for nums, note in wrong_items
            )
            parts.append(
                '<section class="q-exp-section" aria-labelledby="q-exp-wrong-h">'
                '<h3 id="q-exp-wrong-h" class="q-exp-h3">他の選択肢</h3>'
                f'<ul class="q-exp-choice-list">{lis}</ul></section>'
            )

    parts.append("</div>")
    return "\n    ".join(parts)


def _ichimon_answer_is_true(page: dict) -> bool:
    return bool(page.get("correct_answer"))


def split_legacy_ichimon_explanation(
    exp: str, *, is_true: bool, statement: str
) -> tuple[str, str]:
    """1 段落の explanation から要約と正解理由のたたき台を作る。"""
    body = norm(exp) or "（解説は未入力です。）"
    if is_true:
        summary = (
            "この記述は正しい内容です。"
            "○ が正答になります。"
        )
    else:
        summary = (
            "この記述は誤りです。"
            "× が正答になります。"
        )
    if len(body) <= 120:
        return summary, dedupe_prose(body)
    first = re.split(r"[。.]\s*", body, maxsplit=1)[0]
    if first and len(first) >= 20:
        summary = first + ("。" if not first.endswith("。") else "")
    return summary, dedupe_prose(body)


def infer_ichimon_opposite_note(page: dict, row: dict) -> str:
    """○/× のもう一方を選びそうになる理由（CSV 未記入時）。"""
    statement = norm(page.get("statement") or row.get("question"))
    clause = _ichimon_judgment_clause(statement)
    is_true = _ichimon_answer_is_true(page)
    category = norm(page.get("category") or "")
    wrong = "×" if is_true else "○"
    parts: list[str] = []

    if is_true:
        parts.append(
            f"「{_snippet(clause, 44)}」は正しい記述です。"
            f"それでも {wrong} を選ぶ場合は、"
            "一般論と設問の限定語（必要・毎年・常に・しなくてもよい等）を取り違えている可能性があります。"
        )
    else:
        parts.append(
            f"「{_snippet(clause, 44)}」は誤った記述です。"
            f"それでも {wrong} を選ぶ場合は、"
            "一見もっともらしい表現に引っ張られ、判断対象の一文だけを精査していない可能性があります。"
        )

    exp = strip_four_choice_leak(norm(row.get("explanation_correct") or row.get("explanation")))
    if exp:
        for sent in re.split(r"(?<=[。！？!?])\s*", exp):
            s = sent.strip()
            if len(s) >= 16 and (clause[: min(8, len(clause))] in s or (not is_true and "誤" in s)):
                parts.append(s if s.endswith("。") else s + "。")
                break
            if len(s) >= 20 and not _parrots_stem(statement, s):
                parts.append(s if s.endswith("。") else s + "。")
                break

    if re.search(r"第\d+類|危険物|石油類|引火|消火|漏えい", statement + category):
        parts.append(
            "危険物の類別・性質は、政令別表と用語定義の組み合わせで判断します。"
            "類似名称（動植物油類・石油類・特殊引火物など）の違いを用語解説で確認してください。"
        )
    elif re.search(r"復習|見直|定着", statement):
        parts.append(
            "誤答記録と間隔を空けた解き直しは学習の基本です。"
            "「見直さない」「記録しない」系の記述は × になりやすい点に注意してください。"
        )
    elif re.search(r"公式|受験案内|出題範囲|毎年|制度", statement):
        parts.append(
            "制度・数値・期限の正誤は公式情報が基準です。"
            "記憶や一般論だけで ○/× を決めないようにしてください。"
        )
    elif category:
        parts.append(
            f"分野「{category}」では、用語定義と制度の前提を確認し、"
            "同分野の過去問・実践演習で判断基準を固めてください。"
        )

    text = dedupe_prose("\n\n".join(parts))
    if len(text) > _CHOICE_NOTE_MAX_LEN:
        text = _truncate_prose_at_sentence(text, _CHOICE_NOTE_MAX_LEN)
    return text


def _pad_ichimon_correct_body(
    page: dict,
    row: dict,
    body: str,
    *,
    is_true: bool,
) -> str:
    """一問一答の正解理由が短いとき、O4原文のみで補う。"""
    if len(body) >= _CORRECT_REASON_MIN_LEN:
        return body

    exp = strip_four_choice_leak(norm(row.get("explanation")))
    for sent in _split_explanation_sentences(exp):
        core = re.sub(r"^(正しい|誤り)[。.]\s*", "", sent).strip()
        if len(core) < 8:
            continue
        body = _append_if_fresh(body, core, max_overlap=0.88)
        if len(body) >= _CORRECT_REASON_MIN_LEN:
            return body

    point = norm(row.get("explanation_point"))
    for sent in _split_explanation_sentences(point):
        body = _append_if_fresh(body, sent, max_overlap=0.85)
        if len(body) >= _CORRECT_REASON_MIN_LEN:
            return body

    category = norm(page.get("category") or "")
    if category:
        body = _append_if_fresh(
            body,
            f"分野「{category}」の用語定義と制度の前提を確認する。",
            max_overlap=0.5,
        )
        if len(body) >= _CORRECT_REASON_MIN_LEN:
            return body

    clause = _ichimon_judgment_clause(
        norm(page.get("statement") or row.get("question"))
    )
    if clause:
        label = "正しい" if is_true else "誤った"
        body = _append_if_fresh(
            body,
            f"「{_snippet(clause, 36)}」が{label}記述か、定義と照合して判断する。",
            max_overlap=0.55,
        )
    return body


def build_ichimon_explanation_html(page: dict, row: dict) -> str:
    """一問一答 — 正解の理由・もう一方の記号のみ。"""
    statement = norm(page.get("statement") or row.get("question"))
    is_true = _ichimon_answer_is_true(page)
    ans = "○" if is_true else "×"
    wrong = "×" if is_true else "○"

    summary = norm(row.get("explanation_summary"))
    correct_body = strip_four_choice_leak(norm(row.get("explanation_correct")))
    opposite = norm(row.get("explanation_opposite"))
    point = norm(row.get("explanation_point"))
    base = strip_four_choice_leak(norm(row.get("explanation")) or "（解説は未入力です。）")

    if not summary and not correct_body and not point:
        leg_summary, leg_body = split_legacy_ichimon_explanation(
            base, is_true=is_true, statement=statement
        )
        summary = summary or leg_summary
        correct_body = correct_body or leg_body

    summary = dedupe_prose(summary)
    correct_body = clean_ichimon_correct_body(
        correct_body,
        summary=summary,
        is_true=is_true,
    )
    correct_body = _pad_ichimon_correct_body(
        page, row, correct_body, is_true=is_true
    )
    if len(correct_body) > _CORRECT_REASON_MAX_LEN:
        correct_body = _truncate_prose_at_sentence(
            correct_body, _CORRECT_REASON_MAX_LEN
        )
    opposite = dedupe_prose(opposite)
    if not opposite:
        opposite = infer_ichimon_opposite_note(page, row)
    elif len(opposite) > _CHOICE_NOTE_MAX_LEN:
        opposite = _truncate_prose_at_sentence(opposite, _CHOICE_NOTE_MAX_LEN)

    parts: list[str] = ['<div class="q-exp">']

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-correct-h">'
        '<h3 id="q-exp-correct-h" class="q-exp-h3">正解の理由</h3>'
    )
    if correct_body:
        parts.append(f"<p>{text_to_html(correct_body)}</p>")
    if not ichimon_body_already_states_truth(
        f"{summary}\n{correct_body}", is_true=is_true
    ):
        truth = "正しい" if is_true else "誤っている"
        parts.append(
            f'<p class="q-exp-correct-opt">'
            f"設問文は<strong>{truth}</strong>記述のため、答えは "
            f'<strong class="q-marubatsu">{html.escape(ans)}</strong> です。'
            f"</p>"
        )
    parts.append("</section>")

    parts.append(
        '<section class="q-exp-section" aria-labelledby="q-exp-opposite-h">'
        '<h3 id="q-exp-opposite-h" class="q-exp-h3">'
        f"{html.escape(wrong)} を選びやすい考え方</h3>"
        f"<p>{text_to_html(opposite)}</p></section>"
    )

    parts.append("</div>")
    return "\n    ".join(parts)
