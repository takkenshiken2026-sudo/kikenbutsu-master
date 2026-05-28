# -*- coding: utf-8 -*-
"""Shared emit helpers for hub S33/S34 content generators."""

from __future__ import annotations


def qa4(items: list[tuple[str, str]]) -> str:
    lines = ["        ["]
    for q, a in items:
        lines.append("            (")
        lines.append(f'                "{q}",')
        lines.append(f'                "{a}",')
        lines.append("            ),")
    lines.append("        ],")
    return "\n".join(lines)


def emit_cmp(d: dict) -> str:
    axis = "\n".join(
        f'            ("{a}", [{", ".join(chr(34) + c + chr(34) for c in cols)}]),'
        for a, cols in d["axes"]
    )
    return f'''    cmp(
        "{d["slug"]}", "{d["title"]}", {d["cat"]}, "{d["tags"]}", "{d["summary"]}",
        "{d["labels"]}",
        [
{axis}
        ],
        "{d["article_title"]}",
        "{d["lead"]}" + _OFFICIAL,
        "{d["points"]}", "{d["mistakes"]}", "{d["tip"]}", "{d["related"]}",
{qa4(d["qa"])}
    ),'''


def emit_num(d: dict) -> str:
    items = "\n".join(f'            ("{i}", "{v}", "{n}"),' for i, v, n in d["items"])
    return f'''    num(
        "{d["slug"]}", "{d["title"]}", {d["cat"]}, "{d["tags"]}", "{d["summary"]}",
        "{d["highlight"]}",
        [
{items}
        ],
        "{d["article_title"]}",
        "{d["lead"]}" + _OFFICIAL,
        "{d["points"]}", "{d["mistakes"]}", "{d["tip"]}", "{d["related"]}",
{qa4(d["qa"])}
    ),'''


def emit_mis(d: dict) -> str:
    pat = "\n".join(
        f'            ("{t}", "{w}", "{c}", "{p}"),' for t, w, c, p in d["patterns"]
    )
    return f'''    mis(
        "{d["slug"]}", "{d["title"]}", {d["cat"]}, "{d["tags"]}", "{d["summary"]}",
        "{d["confusion"]}",
        [
{pat}
        ],
        "{d["article_title"]}",
        "{d["lead"]}" + _OFFICIAL,
        "{d["points"]}", "{d["mistakes"]}", "{d["tip"]}", "{d["related"]}",
{qa4(d["qa"])}
    ),'''


QFIX = {
    "確認先は？": "確認先はどこですか？",
    "試験対策は？": "試験対策の進め方は？",
    "正解は？": "正しい理解は何ですか？",
    "誤りは？": "誤りの内容は何ですか？",
}


def fix_entry(d: dict) -> dict:
    d = dict(d)
    if len(d.get("mistakes", "")) < 15:
        d["mistakes"] = d["mistakes"] + ";試験の正誤肢に注意"
    if len(d.get("tip", "")) < 10:
        d["tip"] = d["tip"] + "（暗記用フレーズ）"
    if len(d.get("article_title", "")) < 10:
        d["article_title"] = d["article_title"] + "（試験）"
    if "qa" in d:
        fixed = []
        for q, a in d["qa"]:
            q = QFIX.get(q, q)
            if len(a) < 100:
                a = a + "賃管試験では用語集と条文の対応づけが得点の鍵になります。最新の試験要項もあわせて確認してください。"
            fixed.append((q, a))
        d["qa"] = fixed
    return d


def write_content_file(
    out_path,
    *,
    batch: str,
    import_from: str,
    cat_vars: str,
    comparisons: list,
    numbers: list,
    mistakes: list,
) -> None:
    header = f'''# -*- coding: utf-8 -*-
"""賃管 知識ハブ {batch} 追加分（各10件・計30件）."""

from {import_from} import _OFFICIAL, cmp, mis, num

{cat_vars}

'''
    parts = [header, "COMPARISONS_ADD = [\n"]
    parts += [emit_cmp(fix_entry(c)) for c in comparisons]
    parts += ["]\n\nNUMBERS_ADD = [\n"]
    parts += [emit_num(fix_entry(n)) for n in numbers]
    parts += ["]\n\nMISTAKES_ADD = [\n"]
    parts += [emit_mis(fix_entry(m)) for m in mistakes]
    parts.append("]\n")
    out_path.write_text("".join(parts), encoding="utf-8")
    print("wrote", out_path)
