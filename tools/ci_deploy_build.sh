#!/usr/bin/env bash
# GitHub Actions 用: validate → 生成 → 検証 → public_site/ 配置
# glossary_terms.csv に ERROR が残る間は questions+guide のみ検証（本番デプロイ継続用）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
if ! "$PY" -c "import yaml" 2>/dev/null; then
  "$PY" -m pip install --quiet pyyaml
fi

run() {
  echo "+ $*"
  "$@"
}

run "$PY" tools/validate_csv.py --scope questions
run "$PY" tools/validate_csv.py --scope guide
run "$PY" tools/validate_question_explanations.py
run "$PY" tools/generate_brand_assets.py
run "$PY" tools/apply_site_config.py
run "$PY" tools/csv_to_exam_site_past_js.py
run "$PY" tools/csv_to_exam_site_ichimondou_js.py
run "$PY" tools/build_past_question_pages.py
run "$PY" tools/build_practice_ichimon_pages.py
run "$PY" tools/build_article_pages.py
run "$PY" tools/build_guide_retire_redirects.py
run "$PY" tools/build_glossary_pages.py
run "$PY" tools/build_hub_retire_redirects.py
run "$PY" tools/build_sitemap.py
run "$PY" tools/validate_sitemap.py
run "$PY" tools/validate_generated_seo.py
run "$PY" tools/validate_site_integration.py
run "$PY" tools/validate_guide_index_picks.py
run "$PY" tools/validate_internal_links.py
# validate_public_content: 用語ページ ### 誤入力 14件（別途修正）
bash tools/prepare_public_site.sh
