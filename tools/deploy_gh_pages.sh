#!/usr/bin/env bash
# public_site/ を gh-pages ブランチへ push（GitHub Pages 公開用）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 tools/build_all.py
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp -R public_site/. "$WORK/"
cd "$WORK"
git init -q -b gh-pages
git add -A
git commit -q -m "Deploy: $(date +%Y-%m-%d) $(date +%H:%M)"
git remote add origin "https://github.com/takkenshiken2026-sudo/kikenbutsu-master.git"
git push -f origin gh-pages
NFILES=$(find "$WORK" -type f | wc -l | tr -d ' ')
echo "deploy_gh_pages.sh: pushed gh-pages ($NFILES files)"
# legacy ブランチ公開時: push 後に Pages ビルドをキュー（GITHUB_TOKEN または git credential）
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  curl -fsS -X POST \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/takkenshiken2026-sudo/kikenbutsu-master/pages/builds" \
    >/dev/null && echo "deploy_gh_pages.sh: queued Pages build"
fi
