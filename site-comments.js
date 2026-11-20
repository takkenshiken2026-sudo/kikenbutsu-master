/* 乙4マスター ユーザー投稿ウィジェット（Supabase + Cloudflare Turnstile）
 *
 * 置き方: ページ内に次の入れ物を置く（data-* で場所と種類を指定）。
 *   <div data-comments data-page-id="articles/pass-score" data-category="comment"></div>
 * そしてこのファイルと site-comments.css を読み込む。
 *
 * 機能:
 *  - ニックネームを記憶（次回自動入力）
 *  - ブラウザごとの投稿者ID（なりすまし対策・後半マスク表示・投稿前にも表示）
 *  - 返信（スレッド）: 各投稿に返信をぶら下げられる
 *  - 管理者削除（URL末尾に #uc-admin を付けて管理キーを入力すると削除ボタンが出る）
 */
(function () {
  "use strict";

  // ▼▼▼ ここだけ書き換える（すべて公開OKの値）▼▼▼
  var COMMENTS_CONFIG = {
    supabaseUrl: "https://dzyxoaehdylibvpwfyui.supabase.co", // Supabase: Project Settings → Data API → URL
    supabaseAnonKey: "sb_publishable_OvB3nXIDF6UG3mbyyh46fg_mkZ9NIqY", // Supabase: API Keys → publishable (anon)
    turnstileSiteKey: "0x4AAAAAAGJfzqZL5Xk0QQWV", // Cloudflare: Turnstile → Site Key
    functionName: "swift-responder", // Supabase Edge Function 名
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

  function lsGet(k) { try { return localStorage.getItem(k) || ""; } catch (_) { return ""; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (_) { } }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (_) { } }

  function randomHex(bytes) {
    var a = new Uint8Array(bytes);
    var c = window.crypto || window.msCrypto;
    if (c && c.getRandomValues) { c.getRandomValues(a); }
    else { for (var i = 0; i < bytes; i++) a[i] = Math.floor(Math.random() * 256); }
    return Array.prototype.map.call(a, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
  }

  function getUid() {
    var v = lsGet(LS_UID);
    if (!v) { v = randomHex(16); lsSet(LS_UID, v); }
    return v;
  }

  function isAdmin() { return !!lsGet(LS_ADMIN); }
  function adminKey() { return lsGet(LS_ADMIN); }

  function maskedId(id) {
    if (!id) return "";
    return "#" + String(id).slice(0, 8) + "…";
  }

  function sha256hex(str) {
    var c = window.crypto || window.msCrypto;
    if (!c || !c.subtle || typeof TextEncoder === "undefined") return Promise.resolve("");
    var data = new TextEncoder().encode(str);
    return c.subtle.digest("SHA-256", data).then(function (buf) {
      return Array.prototype.map.call(new Uint8Array(buf), function (b) {
        return ("0" + b.toString(16)).slice(-2);
      }).join("");
    }).catch(function () { return ""; });
  }
  function myAuthorId() {
    return sha256hex(getUid()).then(function (h) { return h ? h.slice(0, 16) : ""; });
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function personIcon() {
    var s = document.createElement("span");
    s.className = "uc-avatar";
    s.setAttribute("aria-hidden", "true");
    // 固定のSVG（ユーザー入力は含まないので innerHTML でも安全）
    s.innerHTML = '<svg viewBox="0 0 16 16"><circle cx="8" cy="5" r="2.6"/><path d="M3 13.5a5 5 0 0 1 10 0"/></svg>';
    return s;
  }

  function bodyEl(text) {
    var b = el("div", "uc-item-body");
    (text || "").split("\n").forEach(function (line, i) {
      if (i > 0) b.appendChild(document.createElement("br"));
      b.appendChild(document.createTextNode(line));
    });
    return b;
  }

  function formatDate(iso) {
    try {
      var d = new Date(iso);
      var p = function (n) { return String(n).padStart(2, "0"); };
      return d.getFullYear() + "/" + p(d.getMonth() + 1) + "/" + p(d.getDate()) +
        " " + p(d.getHours()) + ":" + p(d.getMinutes());
    } catch (_) { return ""; }
  }

  var turnstileReady = null;
  function loadTurnstile() {
    if (turnstileReady) return turnstileReady;
    turnstileReady = new Promise(function (resolve) {
      if (window.turnstile) { resolve(); return; }
      var s = document.createElement("script");
      s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      s.async = true; s.defer = true;
      s.onload = function () { resolve(); };
      document.head.appendChild(s);
    });
    return turnstileReady;
  }
  function renderTurnstile(box) {
    // 戻り値: getResponse()/reset() を持つオブジェクト（未ロード時は空）
    var state = { id: null };
    loadTurnstile().then(function () {
      if (window.turnstile) state.id = window.turnstile.render(box, { sitekey: COMMENTS_CONFIG.turnstileSiteKey });
    });
    return {
      token: function () { return (window.turnstile && state.id != null) ? window.turnstile.getResponse(state.id) : ""; },
      reset: function () { if (window.turnstile && state.id != null) window.turnstile.reset(state.id); },
    };
  }

  function restHeaders() {
    return {
      apikey: COMMENTS_CONFIG.supabaseAnonKey,
      Authorization: "Bearer " + COMMENTS_CONFIG.supabaseAnonKey,
    };
  }

  function fetchComments(pageId) {
    var url = COMMENTS_CONFIG.supabaseUrl +
      "/rest/v1/comments?select=*" +
      "&page_id=eq." + encodeURIComponent(pageId) +
      "&is_visible=eq.true&order=created_at.desc&limit=400";
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

  function buildWidget(root) {
    var pageId = root.getAttribute("data-page-id") || location.pathname;
    var category = root.getAttribute("data-category") || "comment";
    var label = CATEGORY_LABEL[category] || "コメント";
    var replyVerb = category === "qa" ? "回答" : "返信";

    root.classList.add("uc-root");
    root.innerHTML = "";
    root.appendChild(el("h2", "uc-title", label + "を投稿"));

    if (isAdmin()) {
      root.appendChild(el("p", "uc-admin-badge", "管理者モード（各投稿に削除ボタンが表示されます）"));
    }
    if (!isConfigured()) {
      root.appendChild(el("p", "uc-note",
        "（設定前です。site-comments.js の COMMENTS_CONFIG に3つのキーを入れると表示されます。）"));
      return;
    }

    // --- メイン投稿フォーム（トップレベル投稿） ---
    var form = el("form", "uc-form");
    var nameInput = el("input", "uc-input");
    nameInput.type = "text"; nameInput.maxLength = 40;
    nameInput.placeholder = "ニックネーム（未入力なら匿名）";
    nameInput.setAttribute("aria-label", "ニックネーム");
    nameInput.value = lsGet(LS_NAME);

    var idHint = el("p", "uc-id-hint", "あなたの投稿者ID：（計算中…）");
    myAuthorId().then(function (id) {
      idHint.textContent = "あなたの投稿者ID：" + (id ? maskedId(id) : "（この端末では利用できません）");
    });

    var bodyInput = el("textarea", "uc-textarea");
    bodyInput.maxLength = 2000; bodyInput.rows = 4; bodyInput.required = true;
    bodyInput.placeholder = PLACEHOLDER[category] || "";
    bodyInput.setAttribute("aria-label", label + "本文");

    var tsBox = el("div", "uc-turnstile");
    var row = el("div", "uc-form-row");
    var submit = el("button", "uc-submit", "投稿する"); submit.type = "submit";
    var msg = el("p", "uc-msg"); msg.setAttribute("role", "status");
    row.appendChild(submit); row.appendChild(msg);

    form.appendChild(nameInput);
    form.appendChild(idHint);
    form.appendChild(bodyInput);
    form.appendChild(tsBox);
    form.appendChild(row);
    root.appendChild(form);

    var listWrap = el("div", "uc-list-wrap");
    var count = el("p", "uc-count", "読み込み中…");
    var list = el("ul", "uc-list");
    listWrap.appendChild(count); listWrap.appendChild(list);
    root.appendChild(listWrap);

    var mainTs = renderTurnstile(tsBox);

    function handleDelete(c, btn) {
      if (!window.confirm("この投稿を削除（非表示）しますか？")) return;
      btn.disabled = true; btn.textContent = "削除中…";
      callFunction({ action: "delete", id: c.id, admin: adminKey() }).then(function (res) {
        if (res.ok && res.data && res.data.ok) { reload(); }
        else { btn.disabled = false; btn.textContent = "削除"; window.alert((res.data && res.data.error) || "削除に失敗しました。"); }
      }).catch(function () { btn.disabled = false; btn.textContent = "削除"; window.alert("通信エラーが発生しました。"); });
    }

    function handleReport(c, btn) {
      if (!window.confirm("この投稿を通報しますか？（不適切・スパム・個人情報など）")) return;
      btn.disabled = true; btn.textContent = "通報中…";
      callFunction({ action: "report", comment_id: c.id, uid: getUid() }).then(function (res) {
        if (res.ok && res.data && res.data.ok) {
          btn.textContent = res.data.already ? "通報済み" : "通報しました";
        } else {
          btn.disabled = false; btn.textContent = "通報";
          window.alert((res.data && res.data.error) || "通報に失敗しました。");
        }
      }).catch(function () { btn.disabled = false; btn.textContent = "通報"; window.alert("通信エラーが発生しました。"); });
    }

    function headRow(c) {
      var head = el("div", "uc-item-head");
      head.appendChild(personIcon());
      head.appendChild(el("span", "uc-item-name", c.author_name || "匿名"));
      if (c.author_id) head.appendChild(el("span", "uc-item-id", maskedId(c.author_id)));
      head.appendChild(el("span", "uc-item-date", formatDate(c.created_at)));
      var report = el("button", "uc-report", "通報"); report.type = "button";
      report.addEventListener("click", function () { handleReport(c, report); });
      head.appendChild(report);
      if (isAdmin()) {
        var del = el("button", "uc-del", "削除"); del.type = "button";
        del.addEventListener("click", function () { handleDelete(c, del); });
        head.appendChild(del);
      }
      return head;
    }

    // 返信フォーム（押したときだけ生成）
    function makeReplyForm(parentId, onDone) {
      var f = el("form", "uc-reply-form");
      var nm = el("input", "uc-input"); nm.type = "text"; nm.maxLength = 40;
      nm.placeholder = "ニックネーム（未入力なら匿名）"; nm.value = lsGet(LS_NAME);
      var bd = el("textarea", "uc-textarea"); bd.rows = 3; bd.maxLength = 2000; bd.required = true;
      bd.placeholder = replyVerb + "を書く";
      var tb = el("div", "uc-turnstile");
      var rr = el("div", "uc-form-row");
      var sb = el("button", "uc-submit", replyVerb + "する"); sb.type = "submit";
      var cc = el("button", "uc-cancel", "キャンセル"); cc.type = "button";
      var mm = el("p", "uc-msg");
      rr.appendChild(sb); rr.appendChild(cc); rr.appendChild(mm);
      f.appendChild(nm); f.appendChild(bd); f.appendChild(tb); f.appendChild(rr);
      var ts = renderTurnstile(tb);
      cc.addEventListener("click", function () { onDone(false); });
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); mm.className = "uc-msg";
        var b = bd.value.trim();
        if (!b) { mm.textContent = "本文を入力してください。"; return; }
        var tk = ts.token();
        if (!tk) { mm.textContent = "認証（チェック）を完了してください。"; return; }
        sb.disabled = true; mm.textContent = "送信中…";
        var n = nm.value.trim();
        callFunction({
          action: "post", page_id: pageId, category: category,
          author_name: n, body: b, token: tk, uid: getUid(), parent_id: parentId,
        }).then(function (res) {
          sb.disabled = false; ts.reset();
          if (res.ok && res.data && res.data.ok) { lsSet(LS_NAME, n); onDone(true); }
          else { mm.className = "uc-msg uc-msg-err"; mm.textContent = (res.data && res.data.error) || (replyVerb + "に失敗しました。"); }
        }).catch(function () { sb.disabled = false; mm.className = "uc-msg uc-msg-err"; mm.textContent = "通信エラーが発生しました。"; });
      });
      return f;
    }

    function renderReply(r) {
      var li = el("li", "uc-reply");
      li.appendChild(headRow(r));
      li.appendChild(bodyEl(r.body));
      return li;
    }

    function renderItem(c, replies) {
      var item = el("li", "uc-item");
      item.appendChild(headRow(c));
      item.appendChild(bodyEl(c.body));

      if (replies && replies.length) {
        var rwrap = el("ul", "uc-replies");
        replies.forEach(function (r) { rwrap.appendChild(renderReply(r)); });
        item.appendChild(rwrap);
      }

      var actions = el("div", "uc-item-actions");
      var replyBtn = el("button", "uc-reply-btn", replyVerb + "する"); replyBtn.type = "button";
      var slot = el("div", "uc-reply-slot");
      replyBtn.addEventListener("click", function () {
        if (slot.firstChild) { slot.innerHTML = ""; return; } // トグル
        slot.appendChild(makeReplyForm(c.id, function (posted) {
          slot.innerHTML = "";
          if (posted) reload();
        }));
      });
      actions.appendChild(replyBtn);
      item.appendChild(actions);
      item.appendChild(slot);
      return item;
    }

    function reload() {
      fetchComments(pageId).then(function (rows) {
        list.innerHTML = "";
        var tops = [], byParent = {};
        rows.forEach(function (r) {
          if (r.parent_id) { (byParent[r.parent_id] = byParent[r.parent_id] || []).push(r); }
          else { tops.push(r); }
        });
        Object.keys(byParent).forEach(function (k) {
          byParent[k].sort(function (a, b) { return new Date(a.created_at) - new Date(b.created_at); });
        });
        if (!tops.length) { count.textContent = "まだ投稿はありません。最初の1件をどうぞ。"; return; }
        count.textContent = tops.length + "件の" + label;
        tops.forEach(function (c) { list.appendChild(renderItem(c, byParent[c.id] || [])); });
      }).catch(function () { count.textContent = "読み込みに失敗しました。"; });
    }

    form.addEventListener("submit", function (ev) {
      ev.preventDefault(); msg.className = "uc-msg";
      var body = bodyInput.value.trim();
      if (!body) { msg.textContent = "本文を入力してください。"; return; }
      var token = mainTs.token();
      if (!token) { msg.textContent = "認証（下のチェック）を完了してください。"; return; }
      submit.disabled = true; msg.textContent = "送信中…";
      var name = nameInput.value.trim();
      callFunction({
        action: "post", page_id: pageId, category: category,
        author_name: name, body: body, token: token, uid: getUid(),
      }).then(function (res) {
        submit.disabled = false; mainTs.reset();
        if (res.ok && res.data && res.data.ok) {
          lsSet(LS_NAME, name); bodyInput.value = "";
          msg.className = "uc-msg uc-msg-ok"; msg.textContent = "投稿しました。ありがとうございます。";
          reload();
        } else {
          msg.className = "uc-msg uc-msg-err"; msg.textContent = (res.data && res.data.error) || "投稿に失敗しました。";
        }
      }).catch(function () {
        submit.disabled = false; msg.className = "uc-msg uc-msg-err"; msg.textContent = "通信エラーが発生しました。";
      });
    });

    reload();
  }

  function ensureCss() {
    if (document.querySelector("link[data-uc-css]")) return;
    var l = document.createElement("link");
    l.rel = "stylesheet"; l.href = "/site-comments.css";
    l.setAttribute("data-uc-css", "1");
    document.head.appendChild(l);
  }

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
