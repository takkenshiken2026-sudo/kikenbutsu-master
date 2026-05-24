# デプロイ手順（kikenbutsu-master.jp）

## ビルド

```bash
cd /Users/otedaiki/Desktop/kikenbutsu-master
python3 tools/build_all.py
```

`public_site/` に GitHub Pages 用の静的ファイルが出力されます（`.gitignore` 対象）。

## GitHub への反映（実施済み 2026-05-21）

| ブランチ | 内容 |
|----------|------|
| `main` | ソース・CSV・生成ツール（CI 用） |
| `gh-pages` | `public_site/` のビルド成果物（公開用） |

リモート: https://github.com/takkenshiken2026-sudo/kikenbutsu-master

## 公開設定

| 項目 | 値 |
|------|-----|
| Source（推奨） | **GitHub Actions**（`.github/workflows/deploy-pages.yml`） |
| Source（従来） | Deploy from a branch → `gh-pages` / `/ (root)` |
| Custom domain | `kikenbutsu-master.jp`（HTTPS 証明書済み） |

**Actions 運用:** `main` へ push すると CI が `python3 tools/build_all.py` を実行し、`public_site/` を Pages にデプロイします。ワークフローファイルの push には Git 認証の **`workflow` スコープ**が必要です（下記）。

**ブランチ運用（手動）:** 初回や Actions 未設定時は、上記ブランチ公開に切り替えたうえで Pages ビルドをキューしてください（認証済み環境）:

```bash
# gh-pages を push したあと（任意・API）
curl -sS -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/takkenshiken2026-sudo/kikenbutsu-master/pages/builds
```

本番: https://kikenbutsu-master.jp/  
GitHub 既定 URL（カスタムドメインへリダイレクト）: https://takkenshiken2026-sudo.github.io/kikenbutsu-master/

## GitHub Actions で自動デプロイする場合（任意）

`.github/workflows/deploy-pages.yml` を push するには、Git の認証情報に **`workflow` スコープ**付き PAT が必要です。

```bash
# PAT を workflow スコープ付きで再発行後
git add .github/workflows/deploy-pages.yml
git commit -m "Add GitHub Pages deploy workflow"
git push origin main
```

Pages の Source を **GitHub Actions** に切り替えると、`main` への push で `build_all.py` が走ります。

## PageSpeed / キャッシュ（GitHub Pages + カスタムドメイン）

GitHub Pages 単体では静的ファイルの `Cache-Control` は **max-age=600（10分）固定**で、リポジトリから変更できません。PageSpeed Insights の「効率的なキャッシュ保存期間」は、次のいずれかで解消します。

### Cloudflare プロキシ（kikenbutsu-master.jp で推奨）

1. Cloudflare ダッシュボード → **Caching** → **Cache Rules**
2. ルール例:
   - **If** URI Path contains `exam-site-data-` **Then** Edge TTL = 1 year
   - **If** URI Path ends with `.js` or `.css`（`index.html` を除く） **Then** Edge TTL = 1 month
3. `index.html` は短め（10分〜1時間）のままにし、JS/CSS は `?v=` 付き URL（`build_all` が index に付与）で更新時にキャッシュ bust

ビルド時に `exam-site-data-*.js` 等へ内容ハッシュ付き `?v=` が付きます。Cloudflare で長期キャッシュを有効にしても、CSV 再生成後は URL が変わるため stale 配信を避けられます。

### Cloudflare Pages / Netlify へ移行する場合

リポジトリ直下の `_headers` が `public_site/` にコピーされます（`prepare_public_site.sh`）。

## 再デプロイ（日常）

```bash
python3 tools/build_all.py
# gh-pages 更新
WORK=$(mktemp -d) && cp -R public_site/. "$WORK/" && cd "$WORK" \
  && git init -b gh-pages && git add -A \
  && git commit -m "Deploy: $(date +%Y-%m-%d)" \
  && git remote add origin https://github.com/takkenshiken2026-sudo/kikenbutsu-master.git \
  && git push -f origin gh-pages
```
