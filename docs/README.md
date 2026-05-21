# ドキュメント一覧

資格対策サイトテンプレート（exam-site-shell）の運用ルールは、この `docs/` と `.cursor/rules/` に集約しています。

## 読む順番

1. リポジトリ直下の [README.md](../README.md) … セットアップとビルド
2. **[seo-article-guidelines.md](./seo-article-guidelines.md)** … 記事・用語・色・内部リンク・公開前チェック（**正本**）
   - 試験ガイドのジャンル MECE（12区分）: **[guide-article-genres.md](./guide-article-genres.md)**
   - 100本以上の slug 例: **[guide-article-catalog.md](./guide-article-catalog.md)**
   - 新規記事テンプレ（CSV・スクリプト）: **[guide-article-template.md](./guide-article-template.md)**
   - アフィリエイト記事（テーマ→自動作成）: **[affiliate/README.md](./affiliate/README.md)**
3. [.cursor/rules/seo-article-template.mdc](../.cursor/rules/seo-article-template.mdc) … Cursor 向け要約（SEO / CSV / CSS 編集時）
5. [.cursor/rules/affiliate-article.mdc](../.cursor/rules/affiliate-article.mdc) … アフィリエイト記事・ブリーフ編集時
6. [.cursor/rules/exam-site-shell-template.mdc](../.cursor/rules/exam-site-shell-template.mdc) … テンプレ全体の必須事項（常時適用）

## ルールの優先順位（矛盾したとき）

1. **`tools/build_all.py` が通る検証**（`validate_csv` / `validate_generated_seo` / `validate_internal_links` / `validate_public_content`）… 公開物の実態に最も近い
2. **[seo-article-guidelines.md](./seo-article-guidelines.md)** … 人間向けの正本。検証に落とし込めていない細部はこちらに従う
3. **`.cursor/rules/*.mdc`** … 編集支援用の要約。ガイドラインや検証と食い違う記述は 1・2 を優先する

## テンプレート標準（要約）

| 項目 | ルール |
|------|--------|
| 本番ボリューム | 試験ガイド 100本以上、用語 300件以上、アフィリエイト記事 **10本目安**（`tags` に `アフィリエイト`） |
| 公開ページ | 運用者向け（独自メモ・更新方針・テンプレ説明等）を表・一覧・本文に出さない |
| 内部リンク | リンク切れゼロ（`validate_csv` + `validate_internal_links`） |
| 色 | `site-config.json` の `theme.accent`、カードは中立・ラベルのみジャンル色 |
| ビルド | `python3 tools/build_all.py` 成功後のみ公開 |

## 主要ツール

| スクリプト | 役割 |
|------------|------|
| `tools/build_all.py` | 一括ビルド（検証込み） |
| `tools/validate_csv.py` | CSV と内部リンク先の事前検証 |
| `tools/scaffold_guide_article.py` | 試験ガイド CSV 行の雛形生成 |
| `tools/scaffold_affiliate_article.py` | アフィリエイト記事（ブリーフ YAML + CSV 行） |
| `tools/validate_generated_seo.py` | 生成 HTML の構成・禁止行 |
| `tools/validate_internal_links.py` | 全内部 `href` の整合性 |
| `tools/validate_public_content.py` | 公開 HTML の運用者向け文言・禁止表の検出 |
| `tools/audit_article_freshness.py` | 更新管理列の監査（任意） |
| `tools/stress_config_build.py` | 長いサイト名・多分野での表示確認（任意） |
| `tools/sync_from_template.py` | 共通エンジンを本番へコピー（`--target` 必須） |
| `tools/check_template_drift.py` | テンプレと本番の差分一覧 |

## 生成物について

- `public_site/` … `build_all` の出力（Git 管理外）。配布用バンドル。
- `exam-site-data-past.js` / `exam-site-data-practice.js` / `exam-site-data-ichimondou.js` … SPA 用（CSV から自動生成）。用語は静的 `terms/` のみ（埋め込み JS は使わない）。
