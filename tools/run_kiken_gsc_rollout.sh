#!/usr/bin/env bash
# GSC着地品質リライト Wave1〜N を順に適用・ビルド・検証する。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"

WAVES=(
  tools/kiken_rewrite_batch_gsc1.py
  tools/kiken_rewrite_batch_gsc2.py
  tools/kiken_rewrite_batch_gsc3.py
  tools/kiken_rewrite_batch_gsc4.py
  tools/kiken_rewrite_batch_gsc5.py
  tools/kiken_rewrite_batch_gsc6.py
  tools/kiken_rewrite_batch_gsc7.py
  tools/kiken_rewrite_batch_gsc8.py
  tools/kiken_rewrite_batch_gsc9.py
  tools/kiken_rewrite_batch_gsc10.py
  tools/kiken_rewrite_batch_gsc11.py
  tools/kiken_rewrite_batch_gsc12.py
  tools/kiken_rewrite_batch_gsc13.py
  tools/kiken_rewrite_batch_gsc14.py
  tools/kiken_rewrite_batch_gsc15.py
)

for batch in "${WAVES[@]}"; do
  if [[ ! -f "$batch" ]]; then
    echo "skip (missing): $batch"
    continue
  fi
  echo "=== $batch ==="
  "$PY" tools/validate_guide_hand_batch.py --batch "$batch"
  "$PY" tools/apply_guide_rewrite_batch.py --batch "$batch" \
    --revision "$(date +%Y-%m-%d): GSC着地品質リライト $(basename "$batch" .py)"
  "$PY" tools/build_article_pages.py
done

"$PY" tools/audit_guide_prose_quality.py --root . --strict
echo "run_kiken_gsc_rollout.sh: guide waves complete"
