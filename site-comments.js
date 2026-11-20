/* 乙4マスター ユーザー投稿ウィジェット（Supabase + Cloudflare Turnstile）
 *
 * 置き方: ページ内に次の入れ物を置く（data-* で場所と種類を指定）。
 *   <div data-comments data-page-id="articles/pass-score" data-category="comment"></div>
 * そしてこのファイルと site-comments.css を読み込む。
 *
 * 機能:
 *  - ニックネームを記憶（次回自動入力）
 *  - ブラウザごとの投稿者ID（なりすまし対策・後半マスク表示）
 *  - 管理者削除（URL末尾に #uc-admin を付けて管理キーを入力すると削除ボタンが出る）
 */
(function () {
  "use strict";

  // ▼▼▼ ここだけ書き換える（すべて公開OKの値）▼▼▼
  var COMMENTS_CONFIG = {
    supabaseUrl: "https://dzyxoaehdylibvpwfyui.supabase.co", // Supabase: Project Settings → Data API → URL
    supabaseAnonKey: "sb_publishable_OvB3nXIDF6UG3mbyyh46fg_mkZ9NIqY", // Supabase: API Keys → publishable (anon)
    turnstileSiteKey: "0x4AAAAAAGJfzqZL5Xk0QQWV", // Cloudflare: Turnstile → Site Key
    functionName: "swift-responder", // Supabase Edge Function 名（デプロイ時の関数名に合わせる）
  };
  // ▲▲▲ ここまで ▲▲▲

  var CATEGORY_LABEL = { comment: "コメント", qa: "質問", taikenki: "体験記" };
  var PLACEHOLDER = {
    comment: "記事の感想や補足を書いてください。",
    qa: "分からない点や相談したいことを書いてください。",
    taikenki: "受験の体験・勉強法・結果などを書いてください。",
  };

  var LS_NAME = "uc_name";
  var LS_UID = "uc_uid";
  var LS_ADMIN = "uc_admin";

  function isConfigured() {
    return (
      COMMENTS_CONFIG.supabaseUrl.indexOf("PROJECT_REF") === -1 &&
      COMMENTS_CONFIG.supabaseAnonKey.indexOf("PUT_") === -1 &&
      COMMENTS_CONFIG.turnstileSiteKey.indexOf("PUT_") === -1
    );
  }

  // --- localStorage ヘルパ（プライベートモード等でも落ちないよう try/catch）---
  function lsGet(k) { try { return localStorage.getItem(k) || ""; } catch (_) { return ""; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (_) { } }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (_) { } }

  function randomHex(bytes) {
    var a = new Uint8Array(bytes);
    var c = window.crypto || window.msCrypto;
    if (c && c.getRandomValues) {
      c.getRandomValues(a);
    } else {
      for (var i = 0; i < bytes; i++) a[i] = Math.floor(Math.random() * 256);
    }
    return Array.prototype.map.call(a, function (b) {
      return ("0" + b.toString(16)).slice(-2);
    }).join("");
  }

  // ブラウザ固有の秘密 uid（これは外に表示しない。サーバーがハッシュ化してIDにする）
  function getUid() {
    var v = lsGet(LS_UID);
    if (!v) { v = randomHex(16); lsSet(LS_UID, v); }
    return v;
  }

  function isAdmin() { return !!lsGet(LS_ADMIN); }
  function adminKey() { return lsGet(LS_ADMIN); }

  // 投稿者IDの表示（後半マスク）: 16桁 → 先頭8桁 + …
  function maskedId(id) {
    if (!id) return "";
    var head = String(id).slice(0, 8);
    return "#" + head + "…";
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text; // textContent なので XSS 安全
    return e;
  }

  function formatDate(iso) {
    try {
      var d = new Date(iso);
      var p = function (n) { return String(n).padStart(2, "0"); };
      return d.getFullYear() + "/" + p(d.getMonth() + 1) + "/" + p(d.getDate()) +
        " " + p(d.getHours()) + ":" + p(d.getMinutes());
    } catch (_) {
      return "";
    }
  }

  var turnstileReady = null;
  function loadTurnstile() {
    if (turnstileReady) return turnstileReady;
    turnstileReady = new Promise(function (resolve) {
      if (window.turnstile) { resolve(); return; }
      var s = document.createElement("script");
      s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      s.async = true;
      s.defer = true;
      s.onload = function () { resolve(); };
      document.head.appendChild(s);
    });
    return turnstileReady;
  }

  function restHeaders() {
    return {
      apikey: COMMENTS_CONFIG.supabaseAnonKey,
      Authorization: "Bearer " + COMMENTS_CONFIG.supabaseAnonKey,
    };
  }

  function fetchComments(pageId) {
    // select=* とすることで author_id 列が未追加でも読み込みが壊れないようにする
    var url = COMMENTS_CONFIG.supabaseUrl +
      "/rest/v1/comments?select=*" +
      "&page_id=eq." + encodeURIComponent(pageId) +
      "&is_visible=eq.true&order=created_at.desc&limit=200";
    return fetch(url, { headers: restHeaders() }).then(function (r) {
      if (!r.ok) throw new Error("read failed");
      return r.json();
    });
  }

  function callFunction(data) {
    var fn = COMMENTS_CONFIG.functionName || "post-comment";
    var url = COMMENTS_CONFIG.supabaseUrl + "/functions/v1/" + fn;
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: COMMENTS_CONFIG.supabaseAnonKey,
        Authorization: "Bearer " + COMMENTS_CONFIG.supabaseAnonKey,
      },
      body: JSON.stringify(data),
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, data: j }; });
    });
  }

  function renderItem(c, onDelete) {
    var item = el("li", "uc-item");
    var head = el("div", "uc-item-head");
    head.appendChild(el("span", "uc-item-name", c.author_name || "匿名"));
    if (c.author_id) head.appendChild(el("span", "uc-item-id", maskedId(c.author_id)));
    head.appendChild(el("span", "uc-item-date", formatDate(c.created_at)));
    if (isAdmin()) {
      var del = el("button", "uc-del", "削除");
      del.type = "button";
      del.addEventListener("click", function () { onDelete(c, del); });
      head.appendChild(del);
    }
    item.appendChild(head);
    var bodyEl = el("div", "uc-item-body");
    (c.body || "").split("\n").forEach(function (line, i) {
      if (i > 0) bodyEl.appendChild(document.createElement("br"));
      bodyEl.appendChild(document.createTextNode(line));
    });
    item.appendChild(bodyEl);
    return item;
  }

  function buildWidget(root) {
    var pageId = root.getAttribute("data-page-id") || location.pathname;
    var category = root.getAttribute("data-category") || "comment";
    var label = CATEGORY_LABEL[category] || "コメント";

    root.classList.add("uc-root");
    root.innerHTML = "";

    var title = el("h2", "uc-title", label + "を投稿");
    root.appendChild(title);

    if (isAdmin()) {
      var badge = el("p", "uc-admin-badge", "管理者モード（各投稿に削除ボタンが表示されます）");
      root.appendChild(badge);
    }

    if (!isConfigured()) {
      root.appendChild(el("p", "uc-note",
        "（設定前です。site-comments.js の COMMENTS_CONFIG に3つのキーを入れると表示されます。）"));
      return;
    }

    // --- 投稿フォーム ---
    var form = el("form", "uc-form");
    var nameInput = el("input", "uc-input");
    nameInput.type = "text";
    nameInput.maxLength = 40;
    nameInput.placeholder = "ニックネーム（未入力なら匿名）";
    nameInput.setAttribute("aria-label", "ニックネーム");
    nameInput.value = lsGet(LS_NAME); // 前回のニックネームを自動入力

    var bodyInput = el("textarea", "uc-textarea");
    bodyInput.maxLength = 2000;
    bodyInput.rows = 4;
    bodyInput.required = true;
    bodyInput.placeholder = PLACEHOLDER[category] || "";
    bodyInput.setAttribute("aria-label", label + "本文");

    var widgetBox = el("div", "uc-turnstile");
    var row = el("div", "uc-form-row");
    var submit = el("button", "uc-submit", "投稿する");
    submit.type = "submit";
    var msg = el("p", "uc-msg");
    msg.setAttribute("role", "status");
    row.appendChild(submit);
    row.appendChild(msg);

    form.appendChild(nameInput);
    form.appendChild(bodyInput);
    form.appendChild(widgetBox);
    form.appendChild(row);
    root.appendChild(form);

    // --- 一覧 ---
    var listWrap = el("div", "uc-list-wrap");
    var count = el("p", "uc-count", "読み込み中…");
    var list = el("ul", "uc-list");
    listWrap.appendChild(count);
    listWrap.appendChild(list);
    root.appendChild(listWrap);

    function handleDelete(c, btn) {
      if (!window.confirm("この投稿を削除（非表示）しますか？")) return;
      btn.disabled = true;
      btn.textContent = "削除中…";
      callFunction({ action: "delete", id: c.id, admin: adminKey() }).then(function (res) {
        if (res.ok && res.data && res.data.ok) {
          reload();
        } else {
          btn.disabled = false;
          btn.textContent = "削除";
          window.alert((res.data && res.data.error) || "削除に失敗しました。");
        }
      }).catch(function () {
        btn.disabled = false;
        btn.textContent = "削除";
        window.alert("通信エラーが発生しました。");
      });
    }

    function reload() {
      fetchComments(pageId).then(function (rows) {
        list.innerHTML = "";
        if (!rows.length) {
          count.textContent = "まだ投稿はありません。最初の1件をどうぞ。";
          return;
        }
        count.textContent = rows.length + "件の" + label;
        rows.forEach(function (c) { list.appendChild(renderItem(c, handleDelete)); });
      }).catch(function () {
        count.textContent = "読み込みに失敗しました。";
      });
    }

    // Turnstile 描画
    var widgetId = null;
    loadTurnstile().then(function () {
      if (window.turnstile) {
        widgetId = window.turnstile.render(widgetBox, {
          sitekey: COMMENTS_CONFIG.turnstileSiteKey,
        });
      }
    });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      msg.className = "uc-msg";
      var body = bodyInput.value.trim();
      if (!body) { msg.textContent = "本文を入力してください。"; return; }
      var token = (window.turnstile && widgetId != null)
        ? window.turnstile.getResponse(widgetId) : "";
      if (!token) { msg.textContent = "認証（下のチェック）を完了してください。"; return; }

      submit.disabled = true;
      msg.textContent = "送信中…";
      var name = nameInput.value.trim();
      callFunction({
        action: "post",
        page_id: pageId,
        category: category,
        author_name: name,
        body: body,
        token: token,
        uid: getUid(),
      }).then(function (res) {
        submit.disabled = false;
        if (window.turnstile && widgetId != null) window.turnstile.reset(widgetId);
        if (res.ok && res.data && res.data.ok) {
          lsSet(LS_NAME, name); // ニックネームを記憶
          bodyInput.value = "";
          msg.className = "uc-msg uc-msg-ok";
          msg.textContent = "投稿しました。ありがとうございます。";
          reload();
        } else {
          msg.className = "uc-msg uc-msg-err";
          msg.textContent = (res.data && res.data.error) || "投稿に失敗しました。";
        }
      }).catch(function () {
        submit.disabled = false;
        msg.className = "uc-msg uc-msg-err";
        msg.textContent = "通信エラーが発生しました。";
      });
    });

    reload();
  }

  function ensureCss() {
    if (document.querySelector("link[data-uc-css]")) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = "/site-comments.css"; // サイトはドメイン直下配信なので絶対パスでOK
    l.setAttribute("data-uc-css", "1");
    document.head.appendChild(l);
  }

  // 管理者ログイン/ログアウト（URLの #uc-admin / #uc-admin-logout で切替）
  function handleAdminHash() {
    var h = location.hash;
    if (h === "#uc-admin") {
      var key = window.prompt("管理キーを入力してください（この端末に保存されます）");
      if (key) { lsSet(LS_ADMIN, key); window.alert("管理者モードを有効にしました。"); }
      history.replaceState(null, "", location.pathname + location.search);
    } else if (h === "#uc-admin-logout") {
      lsDel(LS_ADMIN);
      window.alert("管理者モードを解除しました。");
      history.replaceState(null, "", location.pathname + location.search);
    }
  }

  function init() {
    handleAdminHash();
    var roots = document.querySelectorAll("[data-comments]");
    if (!roots.length) return;
    ensureCss();
    Array.prototype.forEach.call(roots, buildWidget);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
