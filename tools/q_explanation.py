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


def _dedupe_body_sentences(body: str) -> str:
    """段落内の重複文を除去する。"""
    kept: list[str] = []
    joined = ""
    for sent in _split_explanation_sentences(body):
        if kept and _keyword_overlap_ratio(sent, kept[-1]) >= 0.8:
            continue
        sn = _normalize_for_compare(sent)
        pn = _normalize_for_compare(kept[-1]) if kept else ""
        if kept and len(sn) >= 14 and len(pn) >= 14 and sn[:14] == pn[:14]:
            continue
        if _sentence_is_redundant(sent, joined):
            continue
        kept.append(sent)
        joined += sent
    return joined


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
    if "代表例" in stem and "代表例" in exam:
        topic = stem.split("の代表例")[0].split("として")[0]
        exam_subj = exam.split("は")[0] if "は" in exam else exam
        if exam_subj and _normalize_for_compare(exam_subj) not in _normalize_for_compare(core):
            return f"本問が問う{topic}の代表例は{exam_subj}などであり、{core.split('は')[0] if 'は' in core else core}は該当しない。"
    if "該当" in stem and "は" in exam:
        exam_subj = exam.split("は")[0]
        core_subj = core.split("は")[0]
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
    if "製造所" in stem or "取扱所" in stem:
        if "分類ではない" in core:
            return "法令上の製造所等は、製造所・貯蔵所・取扱所を指す。"
        return "製造所・貯蔵所・取扱所の分類として誤りである。"
    if ("取扱者" in stem and ("甲種" in core or "乙種" in core or "丙種" in core)):
        return "危険物取扱者の区分と取扱範囲の説明として誤りである。"
    return ""


def _wrong_note_opening(choice_num: int, opt_sn: str, core: str) -> str:
    """O4の誤答メモから1文目を作る。"""
    core = core.rstrip("。").strip()
    opt_core = norm(opt_sn).rstrip("。")
    return f"（{choice_num}）「{opt_sn}」について、{core}。"


def _wrong_note_context_sentence(page: dict, core: str) -> str:
    """肢ごとの2文目。stem と core の内容からのみ生成（正答引用なし）。"""
    stem = norm(page.get("stem_plain") or page.get("stem"))
    core = core.rstrip("。")
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

    if "三要素" in stem or ("燃焼" in stem and "要素" in stem):
        return "可燃物・酸素供給源・点火源がそろった組合せではない。"

    if "蒸気圧" in stem:
        if "同じ" in core or "色" in core or "引火しない" in core or "にくい" in core:
            return "蒸気圧と蒸発の関係として誤った理解である。"

    if "静電気" in stem:
        if any(k in core for k in ("絶縁", "かき混", "高速", "ためる", "流動")):
            return "静電気の発生や着火リスクを下げる方法ではない。"

    if "不完全燃焼" in stem:
        if "存在しない" in core and "可燃物" in core:
            return "不完全燃焼も燃焼の一種であり、可燃物が存在する状態で起こる。"
        if "十分" in core and "酸素" in core:
            return "酸素が十分にある条件では完全燃焼に近くなりやすい。"
        if "二酸化炭素だけ" in core:
            return "一酸化炭素やすすを生じる点で不完全燃焼の説明と異なる。"

    if "指定数量" in stem:
        return ""

    if "危険物" in stem and "消防法" in stem:
        return "消防法別表第一に基づく危険物の定義とは異なる。"

    if "取扱者" in stem or "乙種危険物取扱者" in stem:
        return "免状の効力・取扱範囲の説明として誤りである。"

    if "運搬" in stem and "適切でない" not in stem:
        return "危険物運搬の要件として誤った理解である。"

    return ""


def _extend_wrong_note_from_o4(
    body: str,
    core: str,
    row: dict,
    correct_body: str,
) -> str:
    """短い場合のみ、O4原文から追加1文（定型句は使わない）。"""
    ref = body + correct_body
    exp = norm(row.get("explanation"))
    exam = _o4_tagged_block(exp, "試験ポイント")
    if exam and not _sentence_is_redundant(exam, ref):
        if _keyword_overlap_ratio(exam, core) >= 0.2:
            sent = exam if exam.endswith("。") else exam + "。"
            if not _sentence_is_redundant(sent, ref):
                return body + sent
    trap = _o4_tagged_block(exp, "ひっかけ")
    if trap and not _sentence_is_redundant(trap, ref):
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
    is_marked_appropriate = bool(re.match(r"^適切", norm(base_note)))

    if mode == "least_appropriate" and is_marked_appropriate:
        reason = core or "内容として妥当"
        body = (
            f"（{choice_num}）「{opt_sn}」は、{reason}。"
            f"運搬上必要とされる適切な内容であり、"
            f"本問が求める「適切でないもの」には該当しない。"
        )
    elif core:
        body = _wrong_note_opening(choice_num, opt_sn, core)
        exp_text = norm(row.get("explanation"))
        exam = _o4_tagged_block(exp_text, "試験ポイント")
        elaborate = _elaborate_wrong_classification(stem, core)
        context = "" if elaborate else _wrong_note_context_sentence(page, core)
        extras: list[str] = []
        for extra in (
            _wrong_stem_exam_bridge(stem, exam, core),
            elaborate,
            context,
        ):
            if not extra:
                continue
            sent = extra if extra.endswith("。") else extra + "。"
            if _sentence_is_redundant(sent, body + "".join(extras)):
                continue
            extras.append(sent)
        body += "".join(extras)
    else:
        body = f"（{choice_num}）「{opt_sn}」の記述は、正答の内容と一致しない。"

    if len(body) < _CHOICE_NOTE_MIN_LEN:
        body = _extend_wrong_note_from_o4(body, core, row, correct_body)
    body = _dedupe_body_sentences(body)
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
            expanded = _expand_cor_note_to_sentence(
                cor_idx, norm(opts[cor_idx - 1]), cor_note
            )
            if _keyword_overlap_ratio(expanded, lead) >= 0.55:
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
                f'<p class="q-exp-choice-note">{text_to_html(note)}</p></li>'
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

    return dedupe_prose("\n\n".join(parts))


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
    opposite = dedupe_prose(opposite)
    if not opposite:
        opposite = infer_ichimon_opposite_note(page, row)

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
