// Google Analytics 4 — window.__GA4_MEASUREMENT_ID__ で上書き可（未設定・空なら下記の既定ID）
// 測定IDの正: tools/html_footer.GA4_MEASUREMENT_ID と揃えること
(function () {
  var DEFAULT_MID = "G-CH3RF5CKLH";
  var raw = "";
  try {
    if (typeof window !== "undefined" && window.__GA4_MEASUREMENT_ID__ != null) {
      raw = String(window.__GA4_MEASUREMENT_ID__).trim();
    }
    if (!raw && typeof window !== "undefined" && window.SITE_CONFIG && window.SITE_CONFIG.ga4MeasurementId != null) {
      raw = String(window.SITE_CONFIG.ga4MeasurementId).trim();
    }
  } catch (_e) {}
  if (!raw) raw = DEFAULT_MID;
  var MID = /^G-[A-Za-z0-9]+$/.test(raw) ? raw : "";
  if (!MID) return;

  /**
   * SPA 等で URL・title が変わったあとに呼ぶ。index.html の gotoPage / popstate から利用。
   * 引数省略時は現在の location + document.title。
   */
  function ga4PageView(pagePath, pageTitle) {
    if (typeof window.gtag !== "function") return;
    var path = pagePath != null && String(pagePath) ? String(pagePath) : "";
    if (!path && typeof location !== "undefined") {
      path = location.pathname + location.search + location.hash;
    }
    var title = pageTitle != null ? String(pageTitle) : typeof document !== "undefined" ? document.title : "";
    try {
      var o = { page_path: path, page_title: title };
      if (typeof location !== "undefined" && location.href) {
        o.page_location = location.href;
      }
      window.gtag("config", MID, o);
    } catch (_e) {}
  }
  window.ga4PageView = ga4PageView;

  /**
   * アフィリエイト（sponsored）リンクのクリックを GA4 イベント affiliate_click として計測。
   * 委譲リスナー1つで、rel に sponsored を含む / class に affiliate を含む / 既知 ASP ホストの
   * <a> を捕捉するため、記事を再ビルドしても将来のリンクが自動で対象になる。
   * GA4 側でレポートに link_url / link_domain / link_text を出すには「カスタム定義」で
   * 同名のカスタムディメンションを登録する（イベント計測自体は登録不要）。
   */
  function initAffiliateClickTracking() {
    if (typeof document === "undefined" || !document.addEventListener) return;
    if (window.__GA4_AFFILIATE_CLICK_INIT__) return;
    window.__GA4_AFFILIATE_CLICK_INIT__ = true;

    // 既知の ASP / 物販ホスト（rel・class が無いリンクの保険）。
    var ASP_HOST_RE = /(^|\.)(a8\.net|amzn\.to|amazon\.co\.jp|amazon\.com|onsuku\.jp|afi-b\.com|affiliate-b\.com|afb\.io)$/i;

    function hostOf(href) {
      try {
        return new URL(href, location.href).hostname;
      } catch (_e) {
        return "";
      }
    }

    function isAffiliateAnchor(a) {
      if (!a || a.tagName !== "A") return false;
      var rel = (a.getAttribute("rel") || "").toLowerCase();
      if (/\bsponsored\b/.test(rel)) return true;
      var cls = a.className && a.className.toString ? a.className.toString() : "";
      if (/affiliate/.test(cls)) return true;
      var href = a.getAttribute("href") || "";
      if (!/^https?:/i.test(href)) return false;
      return ASP_HOST_RE.test(hostOf(href));
    }

    function closestAnchor(node) {
      while (node && node !== document) {
        if (node.tagName === "A") return node;
        node = node.parentNode;
      }
      return null;
    }

    function linkText(a) {
      var t = a.getAttribute("aria-label") || a.textContent || "";
      return t.replace(/\s+/g, " ").trim().slice(0, 100);
    }

    function onClick(ev) {
      var a = closestAnchor(ev.target);
      if (!a || !isAffiliateAnchor(a)) return;
      if (typeof window.gtag !== "function") return;
      var href = a.href || a.getAttribute("href") || "";
      try {
        window.gtag("event", "affiliate_click", {
          link_url: href,
          link_domain: hostOf(href),
          link_text: linkText(a),
          page_path: location.pathname + location.search,
          page_location: location.href,
          // 同一タブ遷移でも送信を取りこぼさない。
          transport_type: "beacon",
        });
      } catch (_e) {}
    }

    // capture 段階で拾い、遷移前に確実に送る。中クリック（新規タブ）も対象。
    document.addEventListener("click", onClick, true);
    document.addEventListener("auxclick", onClick, true);
  }
  initAffiliateClickTracking();

  if (window.__GA4_SNIPPET_INIT__ === MID) return;
  window.__GA4_SNIPPET_INIT__ = MID;

  try {
    if (document.querySelector('script[src*="googletagmanager.com/gtag/js"][data-ga4-mid="' + MID + '"]')) {
      ga4PageView();
      return;
    }
  } catch (_e) {}

  window.dataLayer = window.dataLayer || [];
  function gtag() {
    window.dataLayer.push(arguments);
  }
  window.gtag = gtag;
  gtag("js", new Date());

  var s = document.createElement("script");
  s.async = true;
  s.setAttribute("data-ga4-mid", MID);
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(MID);
  document.head.appendChild(s);

  try {
    var cfg0 = {};
    if (typeof location !== "undefined" && location.href) {
      cfg0.page_location = location.href;
      cfg0.page_path = location.pathname + location.search + location.hash;
    }
    if (typeof document !== "undefined" && document.title) {
      cfg0.page_title = document.title;
    }
    gtag("config", MID, cfg0);
  } catch (_e2) {}
})();
