/* Anonymous usage counters: no cookies, local storage, unique IDs or fingerprinting.
   This file does nothing until analytics-config.js contains a deployed HTTPS /collect URL.
   Regional data is resolved at the server. Full IPs (if enabled) stay in separate security logs. */
(function () {
  "use strict";
  if (location.protocol !== "https:" || location.hostname !== "jonasbader7.github.io") return;
  var cfg = window.JB_ANALYTICS_CONFIG || {};
  if (!cfg.endpoint || typeof cfg.endpoint !== "string") return;
  var endpoint;
  try {
    endpoint = new URL(cfg.endpoint);
    if (endpoint.protocol !== "https:" || endpoint.pathname !== "/collect") return;
  } catch (_) { return; }
  if (navigator.globalPrivacyControl === true || navigator.doNotTrack === "1") return;
  var requested = document.currentScript ? document.currentScript.dataset.analyticsSite : "";
  // Keep the existing storage key so the deployed collector and historical counts work.
  var site = ["bors", "greenroute"].includes(requested) ? "bors" : requested === "transparenz" ? "transparenz" : "portfolio";
  var secondsStart = null;
  var reached = new Set();

  function platform() {
    var ua = navigator.userAgent || "";
    if (/iPad|Tablet|Android(?!.*Mobile)/i.test(ua)) return "tablet";
    if (/Mobi|iPhone|Android/i.test(ua)) return "mobile";
    return "desktop";
  }
  function browser() {
    var ua = navigator.userAgent || "";
    if (/Edg\//.test(ua)) return "Edge";
    if (/Firefox\//.test(ua)) return "Firefox";
    if (/Chrome\//.test(ua)) return "Chrome";
    if (/Safari\//.test(ua)) return "Safari";
    return "Other";
  }
  function source() {
    try {
      var s = new URLSearchParams(location.search).get("utm_source") || "";
      if (["instagram","github","linkedin","strava"].includes(s.toLowerCase())) return s.toLowerCase();
      var host = document.referrer ? new URL(document.referrer).hostname.toLowerCase() : "";
      if (host === location.hostname) return "";
      for (var pair of [["github.com","github"],["linkedin.com","linkedin"],["instagram.com","instagram"],["strava.com","strava"]]) {
        if (host === pair[0] || host.endsWith("." + pair[0])) return pair[1];
      }
      return "";
    } catch (_) { return ""; }
  }
  function send(event, detail, duration) {
    var data = {
      site: site, event: event,
      // No query strings, fragments, exact search text or route parameters.
      detail: detail || "", source: source(), device: platform(),
      browser: browser(), duration: duration || 0
    };
    var body = JSON.stringify(data);
    if (event === "engagement" && navigator.sendBeacon) {
      try {
        if (navigator.sendBeacon(endpoint.href, new Blob([body], {type: "text/plain"}))) return;
      } catch (_) {}
    }
    fetch(endpoint.href, {method:"POST",mode:"cors",credentials:"omit",keepalive:true,
      headers:{"Content-Type":"text/plain;charset=UTF-8"},body:body}).catch(function(){});
  }
  function category(anchor) {
    var url;
    try { url = new URL(anchor.href, location.href); } catch (_) { return ""; }
    if (url.protocol === "mailto:") return "contact";
    if (url.hostname === "github.com") {
      var parts = url.pathname.split("/").filter(Boolean);
      var allowed = ["BORS","GreenRoute","SplitMate","Portfoliopage","Projekt-Transparenz","freddy-entrepreneurship-2024",
        "life-expectancy-analysis-r","bfh-digital-business-projects"];
      if (parts[0] === "Jonasbader7" && allowed.includes(parts[1])) return "github:" + (parts[1] === "BORS" ? "GreenRoute" : parts[1]);
      return "github";
    }
    if (url.hostname === "jonasbader7.github.io") {
      if (/^\/(BORS|GreenRoute)(\/|$)/.test(url.pathname)) return "github:GreenRoute-demo";
      if (/^\/Projekt-Transparenz(\/|$)/.test(url.pathname)) return "github:Transparenz-demo";
    }
    if (/^(www\.)?strava\.com$/.test(url.hostname)) return "strava";
    if (url.hostname === location.hostname) return "internal";
    if (url.protocol === "https:" || url.protocol === "http:") return "external";
    return "";
  }
  function onClick(e) {
    var anchor = e.target.closest && e.target.closest("a[href]");
    if (anchor) {
      var group = category(anchor);
      if (group) send("link_click", group, 0);
      return;
    }
    var element = e.target.closest && e.target.closest("[data-analytics-event]");
    if (!element) return;
    if (element.hasAttribute("aria-controls") && element.getAttribute("aria-expanded") === "true") return;
    var value = element.getAttribute("data-analytics-event") || "";
    if (/^(tab|view|demo):[a-z0-9_-]{1,35}$/.test(value)) send("feature_click",value,0);
  }
  function foreground() {
    if (document.visibilityState === "visible") secondsStart = performance.now();
  }
  function flush() {
    if (secondsStart === null) return;
    var duration = Math.min(1800, Math.max(0, Math.round((performance.now()-secondsStart)/1000)));
    secondsStart = null;
    if (duration >= 3) send("engagement","",duration);
  }
  function visibility() {
    if (document.visibilityState === "hidden") flush();
    else foreground();
  }
  function init() {
    send("pageview","",0);
    if (site === "transparenz") {
      var name = location.pathname.split("/").pop() || "index.html";
      // Coarse page type only: never send a fund/company identifier or raw pathname.
      var page = name === "methodik.html" ? "methodik" : name === "datenquellen.html" ? "quellen" : /^fonds-/.test(name) ? "analyse" : "uebersicht";
      send("feature_click", "view:page_" + page, 0);
    }
    document.addEventListener("scroll", function () {
      var height = document.documentElement.scrollHeight - innerHeight;
      if (height < 100) return;
      var pct = Math.min(100, Math.round(scrollY / height * 100));
      [25,50,75,100].forEach(function (n) {
        if (pct >= n && !reached.has(n)) { reached.add(n); send("feature_click", "view:scroll_" + n, 0); }
      });
    }, {passive:true});
    foreground();
    document.addEventListener("click",onClick,{capture:true,passive:true});
    document.addEventListener("visibilitychange",visibility);
    window.addEventListener("pagehide",flush);
    window.addEventListener("pageshow",function(e){if(e.persisted) foreground();});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})();
