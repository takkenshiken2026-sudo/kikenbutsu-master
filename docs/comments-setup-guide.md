# ユーザー投稿機能 セットアップ手順書（Supabase + Cloudflare Turnstile）

このサイト（静的サイト＝GitHub Pages）に、**ログイン不要・即時公開**のユーザー投稿
（記事コメント / Q&A / 合格体験記）を追加するための手順です。
無料の範囲で作れます。画面に沿って進めれば、プログラミングの知識は不要です。

---

## 全体像

```
訪問者のブラウザ
  ├ 読む  ：Supabase から表示中コメントを直接取得
  └ 書く  ：Turnstile（bot対策）を通過 → Edge Function → DBに保存
管理（あなた）：Supabase の表で、いつでも投稿を非表示・削除できる
```

- **Supabase**：投稿を保存するデータベース＋保存を行う小さなプログラム（Edge Function）
- **Cloudflare Turnstile**：ログインの代わりの「bot よけ」。ほぼ見えないチェックです

作るファイルは用意済みです（このリポジトリ内）:
- `supabase/schema.sql` … データベースの表の定義
- `supabase/functions/post-comment/index.ts` … 保存を行う門番プログラム
- `site-comments.js` / `site-comments.css` … ページに出すコメント欄
- `comments-test.html` … 公開前の動作確認ページ

---

## 準備するもの（無料アカウント2つ）

1. **Supabase** アカウント … https://supabase.com （GitHub ログインで作れます）
2. **Cloudflare** アカウント … https://dash.cloudflare.com/sign-up

---

## STEP 1：Supabase プロジェクトを作る

1. Supabase にログイン →「New project」
2. 名前（例：`kikenbutsu-comments`）とデータベースのパスワードを設定
   - リージョンは「Northeast Asia (Tokyo)」が速いです
3. 作成完了まで1〜2分待つ

## STEP 2：データベースの表を作る

1. 左メニュー **SQL Editor** →「New query」
2. このリポジトリの `supabase/schema.sql` の中身を**全文コピペ**
3. 右下 **Run** を押す（「Success」と出ればOK）

## STEP 3：公開用キーを2つ控える

左メニュー **Project Settings** で、次の2つをメモ（どちらも公開してよい値）:
- **Project URL**（`https://xxxx.supabase.co`）… Data API の画面
- **anon public key** … API Keys の画面の `anon` `public`

## STEP 4：Cloudflare Turnstile のキーを作る

1. Cloudflare ダッシュボード → 左メニュー **Turnstile** →「Add site」
2. 設定:
   - Domain：`kikenbutsu-master.jp`（テスト用に `localhost` も追加しておくと便利）
   - Widget mode：**Managed**（おまかせ）
3. 作成すると2つのキーが出ます:
   - **Site Key**（公開OK。フロントで使う）
   - **Secret Key**（**絶対に公開しない**。サーバー側で使う）

## STEP 5：Secret Key を Supabase に登録する

1. Supabase → **Edge Functions** → **Secrets**（または Settings → Edge Functions）
2. 次を追加:
   - Name：`TURNSTILE_SECRET_KEY`
   - Value：STEP 4 の **Secret Key**
   - （`SUPABASE_URL` と `SUPABASE_SERVICE_ROLE_KEY` は自動で入っています）

## STEP 6：門番プログラム（Edge Function）を配置する

**かんたんな方法（ダッシュボード）:**
1. Supabase → **Edge Functions** →「Deploy a new function」
2. 関数名：`post-comment`
3. `supabase/functions/post-comment/index.ts` の中身を貼り付け
4. **「Verify JWT」を OFF** にして **Deploy**
   （ログイン不要で呼べるようにするため。bot対策は Turnstile が担当します）

**CLI が使える方なら:**
```bash
supabase functions deploy post-comment --no-verify-jwt
```

## STEP 7：フロントにキーを入れる

`site-comments.js` の冒頭 `COMMENTS_CONFIG` を書き換えます（3つとも公開OKの値）:

```js
var COMMENTS_CONFIG = {
  supabaseUrl: "https://xxxx.supabase.co",   // STEP 3 の Project URL
  supabaseAnonKey: "（anon public key）",     // STEP 3 の anon key
  turnstileSiteKey: "（Turnstile Site Key）", // STEP 4 の Site Key
};
```

> この3つを私（Claude）に教えていただければ、こちらで埋めて記事に組み込みます。
> **Secret Key は渡さないでください**（サーバー側＝STEP 5 だけで使います）。

## STEP 8：動作確認

1. ターミナルでサイト直下に移動し `python3 -m http.server 8000`
2. ブラウザで `http://localhost:8000/comments-test.html` を開く
3. 名前・本文を入れ、Turnstile のチェックを通して「投稿する」
4. すぐ下の一覧に表示されればOK。Supabase の Table Editor にも1行増えます

## STEP 9：本番の記事に展開（※ここは Claude が担当）

- `site-comments.js` / `site-comments.css` を公開対象に追加
- 各記事・Q&Aページ・体験記ページにコメント欄を設置
- `privacy.html` に「外部サービス（Supabase / Cloudflare）利用」を追記
- `claude/stoic-ramanujan-dpsyyi` ブランチで数件ずつ → 承認後 `main` 反映

---

## 運用メモ

- **不適切な投稿を消す**：Supabase → Table Editor → `comments` → 対象行の
  `is_visible` を `false` にする（公開画面から即消えます。完全削除は行ごと Delete）。
- **スパムが増えたら**：即時公開をやめて「承認後に公開」へ切り替え可能
  （`is_visible` の初期値を `false` にし、確認後に `true` へ）。
- **無料枠の目安**：Supabase 無料プラン（DB 500MB・Edge Function 月50万回）/
  Turnstile は無料。個人サイトのコメント用途なら十分です。
```

---

## 追加機能の設定（ニックネーム記憶・投稿者ID・管理者削除）

後から追加した3機能を有効にするには、バックエンド側で次の作業が必要です。

### A) DBにID列を追加（SQLを1回実行）

Supabase → SQL Editor で、更新版の `supabase/schema.sql` を**もう一度全文貼り付けて Run**。
（`author_id` 列が追加されます。既存データは消えません。）

### B) 管理キーを登録（Secrets）

Supabase → Edge Functions → Secrets に追加：
- Name：`ADMIN_SECRET`
- Value：**あなただけが知る長いパスワード**（これが管理者削除の合言葉になります）

### C) Edge Function を更新（再デプロイ）

`supabase/functions/post-comment/index.ts` の**更新版コードを貼り替えて再 Deploy**。
（投稿時のID付与と、管理者削除の処理が追加されています。関数名 `swift-responder` のまま。）

### D) フロントは反映済み

`site-comments.js` は更新済みです。サイトをデプロイすれば反映されます。

### 管理者（あなた）の削除のやり方

1. 任意のページのURLの末尾に **`#uc-admin`** を付けてアクセス（例：`https://kikenbutsu-master.jp/qa.html#uc-admin`）
2. 管理キー（＝`ADMIN_SECRET` と同じ値）を入力 → この端末に保存されます
3. 以後、各投稿に「削除」ボタンが表示され、押すと非表示化できます
4. 解除したいときは、末尾に **`#uc-admin-logout`** を付けてアクセス

> 補足：投稿者IDは「ブラウザごとの秘密の値をサーバーでハッシュ化」したものです。他人のIDは逆算できないため、ニックネームを真似されても別IDになり見分けられます。ただしログインほど厳密ではなく、同じ人でも別の端末・ブラウザでは別IDになります。

---

## 自動モデレーション（不適切・ボット・スパム・個人情報の自動ブロック）

更新版の Edge Function には、保存前に投稿を自動チェックして弾く仕組みが入っています。

- **ボット**：Turnstile で遮断（従来どおり）
- **URL・リンク**：`http(s)://` / `www.` / `○○.com` 等を含む投稿を拒否
- **個人情報**：メールアドレス・電話番号・長い数字の並びを拒否
- **スパム**：連投制限（同一IDが60秒に5件以上は拒否）・同一文字の過剰な繰り返しを拒否
- **不適切な表現**：NGワード（`index.ts` の `NG_WORDS`）に該当する投稿を拒否

弾かれた投稿は**保存されません**（画面に理由が表示されます）。NGワードは `index.ts` の `NG_WORDS` 配列を編集して調整できます。

### 有効化の手順
更新版 `supabase/functions/post-comment/index.ts` を Edge Function（swift-responder）に**貼り替えて再 Deploy**するだけです（スキーマ変更・新しいシークレットは不要）。

> さらに高精度にしたい場合：OpenAI の無料モデレーションAPI等をこの関数から呼ぶ拡張も可能です（APIキーの登録が必要）。必要ならご相談ください。

<!-- Generated by Claude Code -->
