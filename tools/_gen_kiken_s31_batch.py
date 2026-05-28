#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot generator for kikenbutsu S31 hub batch files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
S30_DATA = TOOLS / "write_kikenbutsu_hub_s30_data.py"

_OFFICIAL = (
    "数値・日程・合格基準は消防試験研究センター"
    "（https://www.shoubo-shiken.or.jp/kikenbutsu/）の試験要項で必ずご確認ください。"
)


def extract_s30_content() -> None:
    src = S30_DATA.read_text(encoding="utf-8")
    start = src.index("def cmp(")
    end = src.index("\n\n\ndef write_csv")
    body = src[start:end]
    header = f'''# -*- coding: utf-8 -*-
"""危険物取扱者乙4 知識ハブ S30 行データ."""

from __future__ import annotations

from tools.write_kikenbutsu_hub_s30 import COMPARISONS as _C_BASE, _faq, _rows

_OFFICIAL = "{_OFFICIAL}"

'''
    footer = "\n\nCOMPARISONS = _C_BASE + MORE_COMPARISONS\n"
    (TOOLS / "write_kikenbutsu_hub_s30_content.py").write_text(
        header + body + footer, encoding="utf-8"
    )


def write_s31_content() -> None:
    header = f'''# -*- coding: utf-8 -*-
"""危険物取扱者乙4 知識ハブ S31 追加分（各10件）."""

from tools.write_kikenbutsu_hub_s30_content import _OFFICIAL, cmp, mis, num

L, M, F = "法令・制度", "物性・化学", "火災・消火・漏えい"

'''
    body = (TOOLS / "_kiken_s31_body.py").read_text(encoding="utf-8")
    (TOOLS / "write_kikenbutsu_hub_s31_content.py").write_text(header + body, encoding="utf-8")


def _expand_answer(a: str, points: str, official: bool) -> str:
    base = a.strip()
    if len(base) < 100:
        extra = points.split(";")[0] if points else "試験要点"
        base = (
            f"{base} 乙4試験では{extra}を条文・政令とセットで確認し、"
            "過去問の正誤肢を用語集ページと照合しながら分類してください。"
        )
    if official and "shoubo-shiken" not in base:
        base += " " + _OFFICIAL
    if len(base) < 100:
        base += " 本ページは学習整理用です。最新の試験要項・政令改正は必ず公式情報で確認してください。"
    return base


def write_premium_faqs() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.write_kikenbutsu_hub_s30_content import COMPARISONS, MISTAKES, NUMBERS

    lines = [
        "# -*- coding: utf-8 -*-",
        '"""危険物取扱者乙4 知識ハブ：試験特化FAQ."""',
        "",
        "from tools.write_kikenbutsu_hub_s30_content import _OFFICIAL",
        "",
        "PREMIUM_FAQS: dict[str, list[tuple[str, str]]] = {",
    ]
    official_slugs = {
        "koshu-otsu-hei-hikaku", "otsu4-goukaku-ten", "juryo-menjo-ryo",
        "shiken-mondai-jikan", "shiken-nittei-2026", "menjo-gokai", "menjo-hourei-bukka",
        "dai4-shitei-suryo", "inka-ten-bunrui",
    }
    for rows in (COMPARISONS, NUMBERS, MISTAKES):
        for row in rows:
            slug = row["slug"]
            lines.append(f'    "{slug}": [')
            pts = row.get("exam_points", "")
            for n in range(1, 5):
                q = row.get(f"faq_{n}_question", "")
                a = row.get(f"faq_{n}_answer", "")
                if not q or len(q.strip()) < 6:
                    continue
                ans = _expand_answer(a, pts, slug in official_slugs or "試験" in slug or "手数料" in slug)
                q_esc = q.replace('"', '\\"')
                a_esc = ans.replace('"', '\\"')
                lines.append(f'        ("{q_esc}", "{a_esc}"),')
            lines.append("    ],")
    lines.append("}")
    footer = '''


def apply_premium_faqs(row: dict[str, str]) -> dict[str, str]:
    slug = row.get("slug", "")
    if slug not in PREMIUM_FAQS:
        return row
    row = dict(row)
    for i, (q, a) in enumerate(PREMIUM_FAQS[slug], start=1):
        row[f"faq_{i}_question"] = q
        row[f"faq_{i}_answer"] = a
    return row


def apply_all(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [apply_premium_faqs(r) for r in rows]
'''
    (TOOLS / "write_kikenbutsu_hub_premium_faqs.py").write_text(
        "\n".join(lines) + footer, encoding="utf-8"
    )


def write_hub_data() -> None:
    content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""危険物取扱者乙4 知識ハブ CSV 統合出力（S30 + S31 …）."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.hub_merge_data import merge  # noqa: E402
from tools.write_kikenbutsu_hub_s30 import DATA, HEADER_COMPARE, HEADER_MISTAKES, HEADER_NUMBERS  # noqa: E402
from tools.write_kikenbutsu_hub_s30_content import COMPARISONS as C30, MISTAKES as M30, NUMBERS as N30  # noqa: E402
from tools.write_kikenbutsu_hub_s31_content import COMPARISONS_ADD, MISTAKES_ADD, NUMBERS_ADD  # noqa: E402
from tools.write_kikenbutsu_hub_premium_faqs import apply_all as apply_premium_faqs  # noqa: E402


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    comparisons = apply_premium_faqs(merge(C30, COMPARISONS_ADD))
    numbers = apply_premium_faqs(merge(N30, NUMBERS_ADD))
    mistakes = apply_premium_faqs(merge(M30, MISTAKES_ADD))
    write_csv(DATA / "comparisons.csv", HEADER_COMPARE, comparisons)
    write_csv(DATA / "numbers.csv", HEADER_NUMBERS, numbers)
    write_csv(DATA / "mistakes.csv", HEADER_MISTAKES, mistakes)
    print(f"wrote compare={len(comparisons)} numbers={len(numbers)} mistakes={len(mistakes)}")


if __name__ == "__main__":
    main()
'''
    (TOOLS / "write_kikenbutsu_hub_data.py").write_text(content, encoding="utf-8")


def write_s30_data_wrapper() -> None:
    content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate kikenbutsu hub rows and write all CSVs (legacy entry)."""

from tools.write_kikenbutsu_hub_data import main

if __name__ == "__main__":
    main()
'''
    (TOOLS / "write_kikenbutsu_hub_s30_data.py").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    extract_s30_content()
    write_s31_content()
    write_premium_faqs()
    write_hub_data()
    write_s30_data_wrapper()
    print("kikenbutsu S31 batch files generated")
