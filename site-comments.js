/* 乙4マスター ユーザー投稿ウィジェット（Supabase + Cloudflare Turnstile）
 *
 * 置き方: ページ内に次の入れ物を置く（data-* で場所と種類を指定）。
 *   <div data-comments data-page-id="articles/pass-score" data-category="comment"></div>
 * そしてこのファイルと site-comments.css を読み込む。
 *
 * 下の COMMENTS_CONFIG に3つのキーを入れれば動きます（いずれも公開してよい値）。
 */
(function () {
  "use strict";

  // ▼▼▼ ここだけ書き換える（すべて公開OKの値）▼▼▼
  var COMMENTS_CONFIG = {
    supabaseUrl: "https://PROJECT_REF.supabase.co", // Supabase: Project Settings → Data API → URL
    supabaseAnonKey: "PUT_SUPABASE_ANON_KEY_HERE", // Supabase: Project Settings → API Keys → anon public
    turnstileSiteKey: "PUT_TURNSTILE_SITE_KEY_HERE", // Cloudflare: Turnstile → Site Key
    functionName: "swift-responder", // Supabase Edge Function 名（デプロイ時の関数名に合わせる）
  };
  // ▲▲▲ ここまで ▲▲▲

  var CATEGORY_LABEL = { comment: "コメント", qa: "質問", taikenki: "体験記" };
  var PLACEHOLDER = {
    comment: "記事の感想や補足を書いてください。",
    qa: "分からない点や相談したいことを書いてください。",
    taikenki: "受験の体験・勉強法・結果などを書いてください。",
  };

  function isConfigured() {
    return (
      COMMENTS_CONFIG.supabaseUrl.indexOf("PROJECT_REF") === -1 &&
      COMMENTS_CONFIG.supabaseAnonKey.indexOf("PUT_") === -1 &&
      COMMENTS_CONFIG.turnstileSiteKey.indexOf("PUT_") === -1
    );
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

  // Turnstile スクリプトを一度だけ読み込む
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
    var url = COMMENTS_CONFIG.supabaseUrl +
      "/rest/v1/comments?select=id,created_at,author_name,body,category" +
      "&page_id=eq." + encodeURIComponent(pageId) +
      "&is_visible=eq.true&order=created_at.desc&limit=200";
    return fetch(url, { headers: restHeaders() }).then(function (r) {
      if (!r.ok) throw new Error("read failed");
      return r.json();
    });
  }

  function postComment(data) {
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

  function renderItem(c) {
    var item = el("li", "uc-item");
    var head = el("div", "uc-item-head");
    head.appendChild(el("span", "uc-item-name", c.author_name || "匿名"));
    head.appendChild(el("span", "uc-item-date", formatDate(c.created_at)));
    item.appendChild(head);
    var bodyEl = el("div", "uc-item-body");
    // 改行だけ反映、本文は textContent で安全に
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

    function reload() {
      fetchComments(pageId).then(function (rows) {
        list.innerHTML = "";
        if (!rows.length) {
          count.textContent = "まだ投稿はありません。最初の1件をどうぞ。";
          return;
        }
        count.textContent = rows.length + "件の" + label;
        rows.forEach(function (c) { list.appendChild(renderItem(c)); });
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
      postComment({
        page_id: pageId,
        category: category,
        author_name: nameInput.value.trim(),
        body: body,
        token: token,
      }).then(function (res) {
        submit.disabled = false;
        if (window.turnstile && widgetId != null) window.turnstile.reset(widgetId);
        if (res.ok && res.data && res.data.ok) {
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

  function init() {
    var roots = document.querySelectorAll("[data-comments]");
    Array.prototype.forEach.call(roots, buildWidget);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
