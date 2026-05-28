#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""危険物取扱者乙4 知識ハブ CSV 統合出力（S30 + S31 + S32 …）."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.hub_merge_data import finalize_hub_rows, merge  # noqa: E402
from tools.write_kikenbutsu_hub_s30 import DATA, HEADER_COMPARE, HEADER_MISTAKES, HEADER_NUMBERS  # noqa: E402
from tools.write_kikenbutsu_hub_s30_content import COMPARISONS as C30, MISTAKES as M30, NUMBERS as N30  # noqa: E402
from tools.write_kikenbutsu_hub_s31_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S31,
    MISTAKES_ADD as MISTAKES_S31,
    NUMBERS_ADD as NUMBERS_S31,
)
from tools.write_kikenbutsu_hub_s32_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S32,
    MISTAKES_ADD as MISTAKES_S32,
    NUMBERS_ADD as NUMBERS_S32,
)
from tools.write_kikenbutsu_hub_s33_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S33,
    MISTAKES_ADD as MISTAKES_S33,
    NUMBERS_ADD as NUMBERS_S33,
)
from tools.write_kikenbutsu_hub_s34_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S34,
    MISTAKES_ADD as MISTAKES_S34,
    NUMBERS_ADD as NUMBERS_S34,
)
from tools.write_kikenbutsu_hub_s35_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S35,
    MISTAKES_ADD as MISTAKES_S35,
    NUMBERS_ADD as NUMBERS_S35,
)
from tools.write_kikenbutsu_hub_s36_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S36,
    MISTAKES_ADD as MISTAKES_S36,
    NUMBERS_ADD as NUMBERS_S36,
)
from tools.write_kikenbutsu_hub_s37_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S37,
    MISTAKES_ADD as MISTAKES_S37,
    NUMBERS_ADD as NUMBERS_S37,
)
from tools.write_kikenbutsu_hub_s38_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S38,
    MISTAKES_ADD as MISTAKES_S38,
    NUMBERS_ADD as NUMBERS_S38,
)
from tools.write_kikenbutsu_hub_s39_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S39,
    MISTAKES_ADD as MISTAKES_S39,
    NUMBERS_ADD as NUMBERS_S39,
)
from tools.write_kikenbutsu_hub_s40_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S40,
    MISTAKES_ADD as MISTAKES_S40,
    NUMBERS_ADD as NUMBERS_S40,
)
from tools.write_kikenbutsu_hub_s41_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S41,
    MISTAKES_ADD as MISTAKES_S41,
    NUMBERS_ADD as NUMBERS_S41,
)
from tools.write_kikenbutsu_hub_s42_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S42,
    MISTAKES_ADD as MISTAKES_S42,
    NUMBERS_ADD as NUMBERS_S42,
)
from tools.write_kikenbutsu_hub_s43_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S43,
    MISTAKES_ADD as MISTAKES_S43,
    NUMBERS_ADD as NUMBERS_S43,
)
from tools.write_kikenbutsu_hub_s44_content import (  # noqa: E402
    COMPARISONS_ADD as COMPARISONS_S44,
    MISTAKES_ADD as MISTAKES_S44,
    NUMBERS_ADD as NUMBERS_S44,
)
from tools.write_kikenbutsu_hub_premium_faqs import apply_all as apply_premium_faqs  # noqa: E402


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    comparisons = finalize_hub_rows(
        merge(
            C30,
            COMPARISONS_S31,
            COMPARISONS_S32,
            COMPARISONS_S33,
            COMPARISONS_S34,
            COMPARISONS_S35,
            COMPARISONS_S36,
            COMPARISONS_S37,
            COMPARISONS_S38,
            COMPARISONS_S39,
            COMPARISONS_S40,
            COMPARISONS_S41,
            COMPARISONS_S42,
            COMPARISONS_S43,
            COMPARISONS_S44,
        ),
        apply_premium=apply_premium_faqs,
    )
    numbers = finalize_hub_rows(
        merge(
            N30,
            NUMBERS_S31,
            NUMBERS_S32,
            NUMBERS_S33,
            NUMBERS_S34,
            NUMBERS_S35,
            NUMBERS_S36,
            NUMBERS_S37,
            NUMBERS_S38,
            NUMBERS_S39,
            NUMBERS_S40,
            NUMBERS_S41,
            NUMBERS_S42,
            NUMBERS_S43,
            NUMBERS_S44,
        ),
        apply_premium=apply_premium_faqs,
    )
    mistakes = finalize_hub_rows(
        merge(
            M30,
            MISTAKES_S31,
            MISTAKES_S32,
            MISTAKES_S33,
            MISTAKES_S34,
            MISTAKES_S35,
            MISTAKES_S36,
            MISTAKES_S37,
            MISTAKES_S38,
            MISTAKES_S39,
            MISTAKES_S40,
            MISTAKES_S41,
            MISTAKES_S42,
            MISTAKES_S43,
            MISTAKES_S44,
        ),
        apply_premium=apply_premium_faqs,
    )
    write_csv(DATA / "comparisons.csv", HEADER_COMPARE, comparisons)
    write_csv(DATA / "numbers.csv", HEADER_NUMBERS, numbers)
    write_csv(DATA / "mistakes.csv", HEADER_MISTAKES, mistakes)
    print(f"wrote compare={len(comparisons)} numbers={len(numbers)} mistakes={len(mistakes)}")


if __name__ == "__main__":
    main()
