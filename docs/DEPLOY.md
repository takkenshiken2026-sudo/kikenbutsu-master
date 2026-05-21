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

## 公開を有効にする（初回のみ・要操作）

GitHub で **Settings → Pages** を開き、次を設定してください。

1. **Build and deployment → Source:** `Deploy from a branch`
2. **Branch:** `gh-pages` / **Folder:** `/ (root)`
3. **Custom domain:** `kikenbutsu-master.jp`（未設定なら入力し、DNS の CNAME を GitHub 向けに設定）
4. 保存後、数分待って https://kikenbutsu-master.jp/ を確認

直接 URL: https://takkenshiken2026-sudo.github.io/kikenbutsu-master/

## GitHub Actions で自動デプロイする場合（任意）

`.github/workflows/deploy-pages.yml` を push するには、Git の認証情報に **`workflow` スコープ**付き PAT が必要です。

```bash
# PAT を workflow スコープ付きで再発行後
git add .github/workflows/deploy-pages.yml
git commit -m "Add GitHub Pages deploy workflow"
git push origin main
```

Pages の Source を **GitHub Actions** に切り替えると、`main` への push で `build_all.py` が走ります。

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
