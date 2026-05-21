# exam-site-shell

資格対策サイトを短時間で立ち上げるためのテンプレートです。サイト名・試験名・分野・CSV を差し替え、`python3 tools/build_all.py` で SPA・静的 SEO ページ・配布用バンドルを生成します。

## フォルダ構成

```
exam-site-shell/
├── README.md                 … このファイル
├── site-config.json          … サイト名・試験名・テーマ色・ナビ・公式リンク
├── index.html                … 学習 SPA（過去問・一問一答・用語など）
├── about.html / privacy.html / related-sites.html
├── site-pages.css / site-theme.css
├── data/                     … 問題・用語・試験ガイド CSV（差し替え・[data/README.md](data/README.md)）
├── sites/                    … 本番サイトごとの運用メモ（テンプレ内・コードは置かない）
├── articles/ terms/ q/       … ビルドで生成される SEO / 過去問ページ
├── tools/                    … 生成・検証スクリプト
├── docs/                     … 運用ルール（正本）
├── .cursor/rules/            … Cursor 向けルール
├── .github/workflows/        … GitHub Pages デプロイ例
└── public_site/              … build 出力（Git 管理外・配布用）
```

自動生成（手編集しない）: `exam-site-data-past.js`, `exam-site-data-practice.js`, `exam-site-data-ichimondou.js`, `site-config.js`, `site-theme.css`, `sitemap.xml`, `articles/**`, `terms/g-*.html` など。

## クイックスタート

```bash
python3 tools/build_all.py
python3 -m http.server 8765
```

- トップ（SPA）: http://127.0.0.1:8765/
- 試験ガイド: http://127.0.0.1:8765/articles/
- 用語集: http://127.0.0.1:8765/terms/

## 差し替えポイント

| ファイル | 内容 |
|----------|------|
| `site-config.json` | ブランド名、試験名、ドメイン、分野、ナビ、`theme.accent`、公式リンク |
| `data/past_questions.csv` | 過去問 |
| `data/practice_questions.csv` | 実践演習（任意） |
| `data/ichimon_questions.csv` | 一問一答 |
| `data/glossary_terms.csv` | 用語（本番 300件以上想定） |
| `data/guide_articles.csv` | 試験ガイド（本番 100本以上想定） |

## 複数サイト（本番）への反映

テンプレを正本にし、本番は `tools/sync_from_template.py --target /path/to/site` で共通部分だけコピーします。  
手順の詳細: **[docs/multi-site-workflow.md](docs/multi-site-workflow.md)**（本番リポジトリは `--target` で明示したローカルパスのみ）。

## 運用ルール

**[docs/README.md](docs/README.md)** から辿ってください。試験ガイドの新規記事は `python3 tools/scaffold_guide_article.py`（[guide-article-template.md](docs/guide-article-template.md)）が最短です。要約:

- 正本: [docs/seo-article-guidelines.md](docs/seo-article-guidelines.md)
- Cursor: [.cursor/rules/](.cursor/rules/)
- リンク切れ禁止（`validate_internal_links.py`）
- 運用者向け情報を公開ページに出さない
- 試験ガイド一覧はラベルのみ色分け（カード本体は中立）

## ビルドと検証

```bash
python3 tools/build_all.py
```

実行内容: CSV 検証 → 設定反映 → JS/HTML 生成 → SEO 検証 → 内部リンク検証 → `public_site/` 配置。

個別実行:

```bash
python3 tools/validate_csv.py
python3 tools/validate_internal_links.py   # 生成後
python3 tools/audit_article_freshness.py   # 任意
```

## 任意: 表示ストレステスト

長い試験名・多分野でも崩れないか確認する場合:

```bash
python3 tools/stress_config_build.py
```

実行後は `site-config.json` を元に戻し、再ビルドしてください。

## 注意

同梱 CSV・`example.com` リンクはサンプルです。本番公開前に公式 URL・権利・プライバシー・GA4 を必ず確認してください。
