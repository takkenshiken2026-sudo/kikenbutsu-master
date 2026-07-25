# AdSense の ads.txt が「不明」のままになる場合の対処

AdSense 管理画面で ads.txt が「不明（未確認）」と表示され続けるときの、原因切り分けと対処の手順書です。

## 結論（このリポジトリの状態）

リポジトリ側とデプロイ経路は**正しく構成されています**。

- `ads.txt`（リポジトリ直下）の内容・形式は正常。BOM や CRLF はなく、末尾に改行あり。

  ```text
  google.com, pub-7927260139193410, DIRECT, f08c47fec0942fa0
  ```

- Publisher ID `pub-7927260139193410` は各ページの AdSense タグ
  （`client=ca-pub-7927260139193410`）と一致。
- `tools/prepare_public_site.sh` の**必須ファイル**に `ads.txt` が含まれ、
  ビルド成果物 `public_site/ads.txt` に配置される（無ければビルドが失敗する）。
- GitHub Pages の Source は **GitHub Actions**（`.github/workflows/deploy-pages.yml`）。
  `main` への push ごとに `public_site/`（＝ ads.txt を含む）を配信する。

したがって `https://kikenbutsu-master.jp/ads.txt` は ads.txt 追加以降、配信され続けています。
「不明」表示が残る場合、原因は**リポジトリ外**にあります。以下を順に確認してください。

## 原因の切り分け（上から順に）

### 1. AdSense の再クロール待ち（最も多い）

ads.txt を追加・修正しても、Google が再クロールして状態に反映するまで
**数日〜数週間**かかることがあります。ファイルが正しく配信できていれば、
基本的には待てば解消します。まず下記 2 でファイルが実際に配信されているかを確かめ、
配信できていれば時間をおいて再確認します。

### 2. 本番 URL で実際に配信されているかを確認する

ブラウザや端末から次の URL を開き、`google.com, pub-7927260139193410, DIRECT, f08c47fec0942fa0`
がそのまま表示されるか確認します。

- 本番: `https://kikenbutsu-master.jp/ads.txt`
- Pages オリジン: `https://takkenshiken2026-sudo.github.io/kikenbutsu-master/ads.txt`

コマンドで確認する場合:

```bash
curl -sSIL https://kikenbutsu-master.jp/ads.txt   # ステータスと Content-Type
curl -sSL  https://kikenbutsu-master.jp/ads.txt   # 中身
```

判定:

- **HTTP 200 かつ上記 1 行が返る** → 配信は正常。原因は「1. 再クロール待ち」。待つ。
- **本番は失敗するがオリジン(github.io)は正常** → 前段の CDN/WAF が犯人（下記 3）。
- **両方失敗する** → デプロイが反映されていない。Pages のデプロイ結果を確認（下記 4）。

この確認は GitHub Actions の **`Verify ads.txt (AdSense)` ワークフロー**が
毎日自動で実行します。手動実行は Actions タブ →「Verify ads.txt」→ Run workflow。
失敗時のログにどちらが原因か（前段ブロック / 未デプロイ）を表示します。

### 3. Cloudflare を経由している場合（前段ブロック）

`kikenbutsu-master.jp` を Cloudflare プロキシ経由で配信している場合、
Bot Fight Mode・WAF・チャレンジが Google のクローラや `/ads.txt` を
ブロック（403 / JS チャレンジ）していることがあります。次を確認します。

- Security → Bots → **Bot Fight Mode** が `/ads.txt` を巻き込んでいないか。
  必要なら `URI Path equals /ads.txt` を**スキップ（許可）**する WAF 例外を追加。
- Rules → Redirect / Page Rules で `/ads.txt` が別 URL にリダイレクトされていないか。
  AdSense はクロス URL のリダイレクトを追わないため、`/ads.txt` は **200 で直接**返す。
- SSL/TLS が「フル」で、証明書エラーなく HTTPS で配信できているか。
- キャッシュに古い 404/403 が残っている場合は、該当 URL を**パージ**。

修正後、上記 2 の curl で 200＋正しい中身が返ることを確認します。

### 4. デプロイが反映されていない場合

- Actions タブで **`Deploy GitHub Pages`** の最新実行が成功しているか。
- Settings → Pages の **Source が「GitHub Actions」**になっているか
  （「Deploy from a branch」だと古い `gh-pages`〈ads.txt 未収録〉を配信してしまう）。
- 手動で再デプロイする場合は Actions →「Deploy GitHub Pages」→ Run workflow。

### 5. AdSense 側の登録内容を確認する

- AdSense →「サイト」で対象サイトが `kikenbutsu-master.jp` として登録され、
  審査/承認状態になっているか。
- ads.txt の Publisher ID が AdSense アカウントの ID（`pub-7927260139193410`）と
  一致しているか。複数アカウント/MCM を使う場合は該当行を追記する。
- 配信が確認できたうえで状態が変わらなければ、時間をおいて再確認する
  （Google 側の反映には時間がかかる）。

## メンテナンス上の注意

- ads.txt の Publisher ID を変える際は、リポジトリ直下 `ads.txt` を編集すれば
  ビルドで `public_site/` に反映される。各ページの AdSense タグ（`ca-pub-...`）とも
  一致させること。
- 配信監視は `.github/workflows/verify-ads-txt.yml` が担う。期待値は `ads.txt` から
  自動抽出するため、ファイルを更新すれば監視の期待値も追従する。
