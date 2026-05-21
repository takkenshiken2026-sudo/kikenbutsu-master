# data/ — サイト固有コンテンツ（サンプル同梱）

このフォルダの CSV は**テンプレ用サンプル**です。本番サイトでは資格に合わせて差し替えます。

| ファイル | 内容 | 本番目安 |
|----------|------|----------|
| `past_questions.csv` | 過去問（静的 `q/past/` の元） | 試験年度分を順次 |
| `glossary_terms.csv` | 用語解説 | **300件以上** |
| `guide_articles.csv` | 試験ガイド | **100本以上** |
| `ichimon_questions.csv` | 一問一答（SPA） | 任意 |
| `practice_questions.csv` | 実践演習（SPA） | 任意 |

## templates/

`data/templates/` は執筆用の**コピー元**だけ（ビルド対象外）。  
試験ガイド1行雛形: `templates/guide_article_row.template.csv`（[guide-article-template.md](../docs/guide-article-template.md)）

## テンプレ同期について

`data/` 全体は本番サイト専用です。`tools/sync_from_template.py` では**コピーしません**（`tools/template_site_only.paths`）。

共通のビルド・UI を直したあと、各サイトの CSV はそのまま残し、本番側で `python3 tools/build_all.py` を実行してください。
