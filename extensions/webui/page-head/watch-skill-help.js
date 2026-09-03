/*
 * watch-skill WebUI helpers — injected into every page.
 *
 * Responsibilities:
 *   1. Poll /api/plugins/watch-skill/status every 30s and update the topbar
 *      chip.
 *   2. Add a small help button next to the chip that opens a popover with
 *      the available slash commands and the install one-liner (when the
 *      CLI is missing).
 *
 * Designed to be idempotent and re-runnable: every binding checks for the
 * marker class before attaching.
 */

(function () {
  "use strict";
  if (window.__watchSkillHelpLoaded) return;
  window.__watchSkillHelpLoaded = true;

  const POLL_MS = 30000;
  // Real API route (helpers/api.py dispatches /api/plugins/<plugin>/<file>).
  // The v1.0.0 URL (/plugins/watch-skill/status) was a static WebUI route
  // that always 404'd.
  const API_STATUS = "/api/plugins/watch-skill/status";
  const DOCS_URL =
    "https://github.com/oxbshw/watch-skill/tree/main/docs/agents/agent-zero.md";
  const INSTALL_LINE =
    "uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'";

  function $(s, r) { return (r || document).querySelector(s); }
  function el(tag, attrs, ...children) {
    const e = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === "class") e.className = attrs[k];
      else if (k === "html") e.innerHTML = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    for (const c of children) {
      if (c == null) continue;
      e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return e;
  }

  // Prefer the framework's fetchApi (CSRF + error handling), falling back to
  // a plain fetch. Both tolerate failure: a missing endpoint (404) or a
  // network error simply yields null and the chip stays unmounted.
  let _fetchApi = null;
  async function getFetchApi() {
    if (_fetchApi) return _fetchApi;
    try {
      const mod = await import("/js/api.js");
      if (mod && typeof mod.fetchApi === "function") _fetchApi = mod.fetchApi;
    } catch (e) { /* fall back to raw fetch */ }
    return _fetchApi;
  }

  async function fetchStatus() {
    try {
      const fetchApi = await getFetchApi();
      if (fetchApi) {
        const r = await fetchApi(API_STATUS);
        if (!r.ok) return null;
        const data = await r.json();
        return data && typeof data === "object" ? data : null;
      }
      const r = await fetch(API_STATUS, { credentials: "same-origin" });
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }

  function renderChip(status) {
    const ready = !!(status && status.cli_installed);
    const n = status && status.indexed_videos;
    const chip = el("a", {
      class: "ws-chip " + (ready ? "ws-chip-ok" : "ws-chip-warn"),
      href: ready ? DOCS_URL : "https://github.com/oxbshw/watch-skill#start-in-60-seconds",
      target: "_blank",
      rel: "noopener",
      title: ready ? "Open watch-skill docs" : "Click to install the watch-skill CLI",
    },
      el("span", { class: "ws-chip-icon" }, ready ? "🎬" : "⚠️"),
      el("span", { class: "ws-chip-label" },
        ready ? `Watch Skill${n != null ? ` · ${n} videos` : " ready"}`
             : "Watch Skill — install needed")
    );
    return chip;
  }

  function helpPopover() {
    const box = el("div", { class: "ws-help-popover" },
      el("h4", null, "Watch Skill — quick reference"),
      el("p", { class: "ws-help-note" },
        "Slash commands you can type in the chat:"),
      el("ul", null,
        el("li", null, el("code", null, "/watch "), "<video url or path>"),
        el("li", null, el("code", null, "/ws-doctor"), " — self-heal ffmpeg / yt-dlp"),
        el("li", null, el("code", null, "/ws-library"), " — show indexed videos"),
        el("li", null, el("code", null, "/ws-stats"), " — lifetime token savings")
      ),
      el("p", { class: "ws-help-note" },
        "Or just say: “watch this video: <url> and tell me what happens at 0:10”."),
      el("details", null,
        el("summary", null, "Install one-liner"),
        el("pre", { class: "ws-help-pre" }, INSTALL_LINE)
      ),
      el("p", { class: "ws-help-foot" },
        el("a", { href: DOCS_URL, target: "_blank", rel: "noopener" },
          "Full agent-zero guide ↗")
      )
    );
    return box;
  }

  function ensureStyle() {
    if (document.getElementById("ws-help-style")) return;
    const s = document.createElement("style");
    s.id = "ws-help-style";
    s.textContent = `
      .ws-chip{display:inline-flex;align-items:center;gap:6px;
        padding:4px 10px;border-radius:999px;font-size:12px;
        text-decoration:none;margin-left:8px;line-height:1.2;
        border:1px solid rgba(127,127,127,.25);cursor:pointer;}
      .ws-chip-ok{background:rgba(40,200,120,.12);color:#1f7a4d;}
      .ws-chip-warn{background:rgba(255,170,0,.15);color:#9a5a00;}
      .ws-help-btn{margin-left:4px;width:22px;height:22px;border-radius:50%;
        border:1px solid rgba(127,127,127,.35);background:transparent;
        color:inherit;font-size:12px;cursor:pointer;line-height:1;}
      .ws-help-popover{position:absolute;z-index:1000;max-width:340px;
        padding:14px 16px;background:var(--ws-help-bg,#1e1e22);
        color:var(--ws-help-fg,#eee);border:1px solid rgba(127,127,127,.35);
        border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.35);font-size:13px;}
      .ws-help-popover h4{margin:0 0 6px 0;font-size:14px;}
      .ws-help-popover code{background:rgba(127,127,127,.18);padding:1px 4px;
        border-radius:3px;font-size:12px;}
      .ws-help-popover ul{margin:6px 0;padding-left:18px;}
      .ws-help-popover li{margin:2px 0;}
      .ws-help-note{opacity:.75;margin:6px 0 0 0;}
      .ws-help-pre{margin:4px 0;padding:6px 8px;background:rgba(127,127,127,.18);
        border-radius:4px;font-size:12px;overflow-x:auto;}
      .ws-help-foot{margin-top:8px;font-size:12px;}
    `;
    document.head.appendChild(s);
  }

  function mount() {
    ensureStyle();
    // The `ui.*` plugin toggles arrive on the status payload (see api/status.py
    // `_ui_flags`); when the chip is disabled in Settings → Plugins → watch-skill,
    // mount nothing.
    const anchor =
      $(".ws-chip") ||        // already mounted
      $("#topbar-actions") ||
      $(".topbar") ||
      $("header") ||
      document.body;
    if (anchor.querySelector(".ws-chip")) return; // already mounted

    fetchStatus().then((status) => {
      if (!status) return;
      const ui = status.ui || {};
      if (ui.show_status_chip === false) return;
      const chip = renderChip(status);
      const showHelp = !(status.ui && status.ui.show_help_button === false);
      const wrapper = el("span", { class: "ws-topbar-group" }, chip);
      if (showHelp) {
        const helpBtn = el("button", {
          class: "ws-help-btn", title: "Watch Skill — quick reference",
          "aria-label": "Watch Skill help",
        }, "?");
        const pop = helpPopover();
        pop.style.display = "none";
        helpBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          pop.style.display = (pop.style.display === "none") ? "block" : "none";
          const r = helpBtn.getBoundingClientRect();
          pop.style.top  = (window.scrollY + r.bottom + 6) + "px";
          pop.style.left = (window.scrollX + r.left - 160) + "px";
        });
        document.addEventListener("click", (ev) => {
          if (!pop.contains(ev.target) && ev.target !== helpBtn) pop.style.display = "none";
        });
        wrapper.appendChild(helpBtn);
        document.body.appendChild(pop);
      }
      anchor.appendChild(wrapper);
    });
  }

  function start() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mount);
    } else {
      mount();
    }
    setInterval(async () => {
      if (document.visibilityState !== "visible") return;
      const status = await fetchStatus();
      if (!status) return;
      const old = document.querySelector(".ws-chip");
      if (old && status.ui && status.ui.show_status_chip === false) return;
      if (old) old.replaceWith(renderChip(status));
    }, POLL_MS);
  }

  start();
})();
