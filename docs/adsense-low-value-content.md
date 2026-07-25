# AdSense「有用性の低いコンテンツ」で落ちないための対策

Google AdSense の不承認・広告制限の主因である「Low value content（有用性の低いコンテンツ）／
Scaled content abuse（スケール生成の乱用）」のリスクを、当サイトで限りなく下げるための
現状評価・是正手順・運用ルールをまとめる。

数値は `python3 tools/audit_adsense_content.py` の出力（`reports/adsense_content/`）に基づく。
コンテンツを更新したら再実行して追跡する。

## 現状評価（監査結果）

広告掲載ページ **2,008** に対して:

| エリア | ページ数 | 平均本文字数 | 薄い(<600字) | 定型文率≥50% |
|--------|---------:|------------:|------------:|------------:|
| articles   |   39 | 2,222 | 0 | 0 |
| q_ichimon  |  501 | 1,013 | 0 | 107 |
| q_practice | 1,001 | 1,134 | 0 | 20 |
| q_past     |   35 | 1,441 | 0 | 0 |
| terms      |  432 | 3,231 | 2 | 0 |

- **良好**: 必須ページ（運営者情報 `about.html`・プライバシー `privacy.html`・
  連絡先＝問い合わせフォーム）が揃い、記事・用語・過去問は十分な文字量がある。
  極端に薄いページはほぼ無い。
- **対応済み**: 一問一答の定型文は下記のとおり解消し、監査の「定型文率≥50%」は
  **0 ページ**になった（`reports/adsense_content/summary.json`）。

## 対応済み（このリポジトリで実施）

1. **プライバシーポリシーに広告配信の開示を追加**（`privacy.html`）。
   AdSense は「第三者配信広告・Cookie・パーソナライズ広告の無効化方法」の
   明記を必須とする。Google の広告設定 / aboutads.info / Google 広告ポリシーへの
   リンクを含めた。広告タグを出しながらポリシー未記載、という不整合を解消。

2. **監査ツール `tools/audit_adsense_content.py` を追加**。広告掲載ページの
   本文量と定型文率を測り、是正対象を CSV で出力する。ナビ・ヘッダ・フッタなどの
   サイト共通チラシは全ページに出る構造要素で低価値判定の対象外のため、
   本文抽出時に `<nav>/<header>/<footer>/<aside>` を除外し、さらに全体の 60% 超に
   出る文（＝サイト共通の導入・注意書き）は「コンテンツ定型」から除いて測る。
   これにより指標は本文の使い回しだけを捉える。

3. **一問一答 107 問に設問固有の解説を付与**（`tools/enrich_ichimon_adsense.py`
   → `data/ichimon_questions.csv` の `explanation_correct` /
   `explanation_opposite`）。従来これらが空の設問は生成器の汎用フォールバック文で
   埋められていた。各設問の指定数量・性質・制度に即した内容へ置き換え、
   `validate_question_explanations.py` は 0 error / 0 warning。
   本文の使い回し（チラシ除外後の指標）は **11 ページ → 0 ページ**に低下。
   （当初「127」としていたのはサイト共通チラシを含む旧指標での値。純粋な本文定型は
   11 ページで、107 問の是正がこれを完全に覆う。実践演習 `q_practice` の
   フラグはチラシ由来で、本文定型は元々 0 だった。）

## 追加で定型文が出た場合の是正手順

（今回の 107 問は対応済み。将来 `boilerplate_pages.csv` に載った設問はこの手順で直す。）

### 原因

一問一答の解説生成（`tools/q_explanation.py`）は、CSV に個別の解説が
入っていない設問に対して、**汎用のフォールバック文**で補う設計になっている。
該当箇所（例）:

- `infer_ichimon_opposite_note()`
  「それでも × を選ぶ場合は、一般論と設問の限定語（…）を取り違えている可能性があります。」
  「分野「○○」では、用語定義と制度の前提を確認し、同分野の過去問・実践演習で
  判断基準を固めてください。」
- `_pad_ichimon_correct_body()`
  「分野「○○」の用語定義と制度の前提を確認する。」（正解理由が 50 字未満のときの穴埋め）

つまり定型文が多いページ＝**元データ（CSV）の解説が薄い設問**。生成ロジック自体は
妥当なので、直すべきは設問ごとの解説データ。

### 手順

1. 対象を確認: `reports/adsense_content/boilerplate_pages.csv`
   （`path` の末尾が設問 ID。例 `q/ichimon/s/TF-L-008/` → ID `TF-L-008`）。
2. 元データを充実させる（一問一答）: `tools/enrich_ichimon_adsense.py` の
   `ENRICH` 辞書に `ID: (explanation_correct, explanation_opposite)` を追記し、
   `python3 tools/enrich_ichimon_adsense.py` で `data/ichimon_questions.csv` に反映する。
   - `explanation_correct`（正解の理由）は概ね 50〜220 字、設問固有の内容にする。
   - `explanation_opposite`（もう一方を選びやすい理由）は概ね 40〜220 字にする。
   - 執筆は CLAUDE.md 絶対ルール#1（定型文・使い回し禁止）に従い、設問ごとに変える。
3. 再生成と検証:
   ```bash
   python3 tools/csv_to_exam_site_ichimondou_js.py       # SPA データ＋expHtml 再生成
   python3 tools/build_practice_ichimon_pages.py         # 静的ページ再生成
   python3 tools/validate_question_explanations.py       # 0 error 必須（長さ・極性）
   python3 tools/audit_adsense_content.py                # 定型文率≥50% が 0 か確認
   ```
   静的 HTML（`q/`）はビルド副産物なので、`main` への反映時に CI（`build_all.py`）が
   CSV から再生成する。コミットは CSV と `exam-site-data-ichimondou.js` を対象にする。

### 目安（合格ライン）

- 定型文率≥50% のページを **0 に近づける**。
- 各ページの固有本文（Q&A＋解説）が、共通の枠文より明確に多いこと。

## 運用ルール（今後の予防）

- **薄いページに広告を出さない**: 本文が実質数文しかないページ（サンプル・
  インデックスのみ 等）は `noindex` にするか広告タグを外す。
  現状 `terms/diagram-samples/` の 2 ページは既に `noindex`＋サイトマップ除外済み
  （開発用サンプル）。新規に同種を作る場合も同様にする。
- **大量の自動生成ページを増やすときは固有情報を必ず伴わせる**。テンプレの枠だけ
  増やさない（Scaled content abuse 対策）。
- コンテンツ更新のたびに `tools/audit_adsense_content.py` を実行し、
  `reports/adsense_content/summary.json` の `boilerplate_pages` を監視する。

## AdSense 側の操作

- 審査/再審査は、上記の是正（特に 127 ページの解説充実）を反映してから依頼する。
- ポリシー更新（広告開示）を反映したら、`privacy.html` が本番に出ていることを確認する。
- 制限・不承認の通知が来たら、指摘カテゴリ（Low value content 等）と該当 URL を
  上表・CSV と突き合わせて優先対応する。
