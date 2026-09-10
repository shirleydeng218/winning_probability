"""Fixed on-page guide character with scroll-aware tips."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit.components.v1 as components

from winprob.guide_content import build_guide_payload

_GUIDE_DOM_VERSION = "19"
_GUIDE_MINIMIZED_OFFSET = 68
_BAYES_CAT_PATH = Path(__file__).resolve().parent.parent / "assets" / "bayes-cat.png"
_GUIDE_DEFAULT_WIDTH = 280
_GUIDE_MIN_WIDTH = 220
_GUIDE_MAX_WIDTH = 420

_GUIDE_STYLES = """
#winprob-guide-root {
  position: fixed;
  right: 1.35rem;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100002;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.85rem;
  width: 280px;
  min-width: 220px;
  max-width: 420px;
  box-sizing: border-box;
  pointer-events: auto;
  padding: 1.1rem 1.15rem 1rem;
  background: linear-gradient(160deg, #0B1C2D 0%, #12263A 58%, #0f2840 100%);
  border: 1px solid #2F5175;
  border-top: 3px solid #7ED957;
  border-radius: 18px;
  box-shadow: 0 14px 40px rgba(11, 28, 45, 0.45);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  transition: width 0.22s ease, padding 0.22s ease;
}
.winprob-guide-minimize-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 3;
  width: 1.55rem;
  height: 1.55rem;
  border: 1px solid #2F5175;
  border-radius: 999px;
  background: rgba(18, 38, 58, 0.92);
  color: #B8F2E6;
  font-size: 0.95rem;
  line-height: 1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}
.winprob-guide-minimize-btn:hover,
.winprob-guide-minimize-btn:focus {
  color: #7ED957;
  border-color: #7ED957;
  outline: none;
}
#winprob-guide-root.minimized {
  width: 52px !important;
  min-width: 52px;
  padding: 0.65rem 0.3rem 0.45rem;
  cursor: pointer;
}
#winprob-guide-root.minimized .winprob-guide-bubble,
#winprob-guide-root.minimized .winprob-guide-resize-handle {
  display: none;
}
#winprob-guide-root.minimized .winprob-guide-character-wrap {
  padding-top: 1.35rem;
}
#winprob-guide-root.minimized .winprob-guide-character {
  width: 38px;
  max-height: 42px;
}
#winprob-guide-root.minimized .winprob-guide-halo {
  width: 52px;
  height: 52px;
}
.winprob-guide-resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 12px;
  cursor: ew-resize;
  border-radius: 18px 0 0 18px;
  touch-action: none;
}
.winprob-guide-resize-handle:hover,
.winprob-guide-resize-handle.dragging {
  background: rgba(126, 217, 87, 0.14);
}
.winprob-guide-resize-grip {
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 42px;
  border-radius: 999px;
  background: rgba(184, 242, 230, 0.35);
  box-shadow: 5px 0 0 rgba(184, 242, 230, 0.2);
}
.winprob-guide-bubble {
  width: 100%;
  background: rgba(18, 38, 58, 0.72);
  border: 1px solid #2F5175;
  border-radius: 14px 14px 14px 6px;
  padding: 1rem 1.05rem;
  color: #E6F2F0;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.winprob-guide-bubble.visible {
  opacity: 1;
  transform: translateY(0);
}
.winprob-guide-label {
  color: #7ED957;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin-bottom: 0.45rem;
}
.winprob-guide-text {
  font-size: 1.05rem;
  line-height: 1.55;
  margin: 0;
  color: #E6F2F0;
}
.winprob-guide-character-wrap {
  position: relative;
  align-self: center;
  line-height: 0;
  background: transparent;
  padding: 0.35rem 0 0.15rem;
}
.winprob-guide-halo {
  position: absolute;
  left: 50%;
  top: 56%;
  width: 148px;
  height: 148px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(
    circle,
    rgba(126, 217, 87, 0.62) 0%,
    rgba(126, 217, 87, 0.28) 42%,
    rgba(126, 217, 87, 0.08) 62%,
    rgba(126, 217, 87, 0) 78%
  );
  box-shadow:
    0 0 28px rgba(126, 217, 87, 0.5),
    0 0 56px rgba(126, 217, 87, 0.28),
    0 0 84px rgba(126, 217, 87, 0.14);
  z-index: 0;
  pointer-events: none;
  animation: winprob-guide-glow 3.8s ease-in-out infinite;
}
.winprob-guide-character {
  position: relative;
  z-index: 1;
  width: 152px;
  height: auto;
  max-height: 168px;
  object-fit: contain;
  display: block;
  filter:
    drop-shadow(0 0 10px rgba(126, 217, 87, 0.75))
    drop-shadow(0 0 22px rgba(126, 217, 87, 0.45))
    drop-shadow(0 0 38px rgba(126, 217, 87, 0.22));
  animation: winprob-guide-float 4.5s ease-in-out infinite;
}
.winprob-guide-character.react {
  animation: winprob-guide-bounce 0.55s ease;
}
@keyframes winprob-guide-glow {
  0%, 100% { opacity: 0.82; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.07); }
}
@keyframes winprob-guide-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
@keyframes winprob-guide-bounce {
  0%, 100% { transform: translateY(0) scale(1); }
  35% { transform: translateY(-10px) scale(1.04); }
  70% { transform: translateY(-3px) scale(0.98); }
}
body.winprob-guide-active [data-testid="stMain"],
body.winprob-guide-active section.main {
  padding-right: var(--winprob-guide-offset, 20rem) !important;
  padding-left: calc(var(--winprob-guide-offset, 20rem) * 0.12) !important;
  box-sizing: border-box;
}
body.winprob-guide-active [data-testid="stMain"] .block-container,
body.winprob-guide-active .main .block-container {
  max-width: min(1140px, 100%);
  margin-left: auto;
  margin-right: auto;
}
@media (max-width: 960px) {
  #winprob-guide-root { display: none !important; }
  body.winprob-guide-active [data-testid="stMain"],
  body.winprob-guide-active section.main {
    padding-right: inherit !important;
    padding-left: inherit !important;
  }
}
"""


def _bayes_character_html() -> str:
    encoded = base64.b64encode(_BAYES_CAT_PATH.read_bytes()).decode("ascii")
    return (
        f'<img class="winprob-guide-character" '
        f'src="data:image/png;base64,{encoded}" '
        f'alt="Bayes guide cat" />'
    )


def inject_winprob_guide(*, show_home_tip: bool = False) -> None:
    """Inject the fixed guide rail into the parent Streamlit document."""
    payload = build_guide_payload()
    if show_home_tip:
        payload["force_home"] = True

    payload_json = json.dumps(payload).replace("</", "<\\/")
    character_html = json.dumps(_bayes_character_html())
    styles = _GUIDE_STYLES.replace("`", "")

    components.html(
        f"""
        <script>
        (function () {{
          const PAYLOAD = {payload_json};
          const STYLES = `{styles}`;
          const CHARACTER_HTML = {character_html};
          const DOM_VERSION = {json.dumps(_GUIDE_DOM_VERSION)};
          const DEFAULT_WIDTH = {_GUIDE_DEFAULT_WIDTH};
          const MIN_WIDTH = {_GUIDE_MIN_WIDTH};
          const MAX_WIDTH = {_GUIDE_MAX_WIDTH};
          const WIDTH_STORAGE_KEY = "winprob_guide_width";
          const MINIMIZED_STORAGE_KEY = "winprob_guide_minimized";
          const MINIMIZED_OFFSET = {_GUIDE_MINIMIZED_OFFSET};
          const win = window.parent;
          const doc = win.document;

          function guideMarkup() {{
            return `
              <button type="button" class="winprob-guide-minimize-btn" id="winprob-guide-minimize"
                title="Minimize guide" aria-label="Minimize guide">›</button>
              <div class="winprob-guide-resize-handle" id="winprob-guide-resize" title="Drag to resize">
                <span class="winprob-guide-resize-grip" aria-hidden="true"></span>
              </div>
              <div class="winprob-guide-bubble visible" id="winprob-guide-bubble">
                <div class="winprob-guide-label">Bayes · Guide</div>
                <p class="winprob-guide-text" id="winprob-guide-text"></p>
              </div>
              <div class="winprob-guide-character-wrap">
                <div class="winprob-guide-halo" aria-hidden="true"></div>
                ${{CHARACTER_HTML}}
              </div>
            `;
          }}

          function getRoot() {{
            return doc.getElementById("winprob-guide-root");
          }}

          function loadGuideWidth() {{
            const stored = parseInt(win.localStorage.getItem(WIDTH_STORAGE_KEY) || "", 10);
            if (stored >= MIN_WIDTH && stored <= MAX_WIDTH) return stored;
            return DEFAULT_WIDTH;
          }}

          function loadGuideMinimized() {{
            return win.localStorage.getItem(MINIMIZED_STORAGE_KEY) === "1";
          }}

          function applyGuideWidth(width) {{
            const root = getRoot();
            if (!root) return width;
            const clamped = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
            root.style.width = `${{clamped}}px`;
            const guideRightInset = 22;
            const guideGap = 16;
            doc.documentElement.style.setProperty(
              "--winprob-guide-offset",
              `${{clamped + guideRightInset + guideGap}}px`
            );
            return clamped;
          }}

          function setGuideMinimized(minimized) {{
            const root = getRoot();
            if (!root) return;
            root.classList.toggle("minimized", minimized);
            const btn = root.querySelector("#winprob-guide-minimize");
            if (btn) {{
              btn.textContent = minimized ? "‹" : "›";
              btn.title = minimized ? "Expand guide" : "Minimize guide";
              btn.setAttribute("aria-label", btn.title);
            }}
            if (minimized) {{
              doc.documentElement.style.setProperty(
                "--winprob-guide-offset",
                `${{MINIMIZED_OFFSET}}px`
              );
            }} else {{
              applyGuideWidth(loadGuideWidth());
            }}
            win.localStorage.setItem(MINIMIZED_STORAGE_KEY, minimized ? "1" : "0");
          }}

          function toggleGuideMinimized() {{
            const root = getRoot();
            if (!root) return;
            setGuideMinimized(!root.classList.contains("minimized"));
          }}

          function bindGuideControls(root) {{
            const btn = root.querySelector("#winprob-guide-minimize");
            if (btn) {{
              btn.onclick = (event) => {{
                event.preventDefault();
                event.stopPropagation();
                toggleGuideMinimized();
              }};
            }}

            const handle = root.querySelector("#winprob-guide-resize");
            if (handle) {{
              let dragging = false;
              const onMove = (clientX) => {{
                const activeRoot = getRoot();
                if (!dragging || !activeRoot || activeRoot.classList.contains("minimized")) return;
                const rightEdge = activeRoot.getBoundingClientRect().right;
                const nextWidth = applyGuideWidth(rightEdge - clientX);
                win.localStorage.setItem(WIDTH_STORAGE_KEY, String(nextWidth));
              }};
              const stopDrag = () => {{
                if (!dragging) return;
                dragging = false;
                handle.classList.remove("dragging");
                const activeRoot = getRoot();
                if (activeRoot) {{
                  win.localStorage.setItem(WIDTH_STORAGE_KEY, String(activeRoot.offsetWidth));
                }}
              }};

              handle.onmousedown = (event) => {{
                dragging = true;
                handle.classList.add("dragging");
                event.preventDefault();
              }};
              handle.ontouchstart = (event) => {{
                dragging = true;
                handle.classList.add("dragging");
                if (event.touches[0]) onMove(event.touches[0].clientX);
                event.preventDefault();
              }};
              win.onmousemove = (event) => onMove(event.clientX);
              win.ontouchmove = (event) => {{
                if (!dragging || !event.touches[0]) return;
                onMove(event.touches[0].clientX);
                event.preventDefault();
              }};
              win.onmouseup = stopDrag;
              win.ontouchend = stopDrag;
            }}

            root.onclick = (event) => {{
              const activeRoot = getRoot();
              if (!activeRoot || !activeRoot.classList.contains("minimized")) return;
              if (event.target.closest("#winprob-guide-minimize")) return;
              setGuideMinimized(false);
            }};
          }}

          let lastTip = "";

          function setTip(text) {{
            const root = getRoot();
            if (!root || !text) return;
            const bubble = root.querySelector("#winprob-guide-text");
            const bubbleWrap = root.querySelector("#winprob-guide-bubble");
            const character = root.querySelector(".winprob-guide-character");
            if (!bubble || !bubbleWrap) return;
            if (text === lastTip) return;
            lastTip = text;
            bubble.textContent = text;
            bubbleWrap.classList.add("visible");
            if (character) {{
              character.classList.remove("react");
              void character.offsetWidth;
              character.classList.add("react");
            }}
          }}

          function resolveSectionKey(id) {{
            if (!id) return "default";
            for (const rule of PAYLOAD.rules || []) {{
              if (rule.id && rule.id === id) return rule.key;
              if (rule.suffix && id.endsWith(rule.suffix)) return rule.key;
            }}
            return "default";
          }}

          function shouldTrackSection(id) {{
            return resolveSectionKey(id) !== "default";
          }}

          function refreshGuideTip() {{
            if (PAYLOAD.force_home) {{
              setTip(PAYLOAD.home || PAYLOAD.default);
              return;
            }}
            const anchors = Array.from(doc.querySelectorAll("[id]"))
              .filter((el) => shouldTrackSection(el.id))
              .sort((a, b) => {{
                if (a === b) return 0;
                const position = a.compareDocumentPosition(b);
                if (position & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
                if (position & Node.DOCUMENT_POSITION_PRECEDING) return 1;
                return 0;
              }});
            if (anchors.length) {{
              const viewportHeight = win.innerHeight || doc.documentElement.clientHeight;
              const triggerY = viewportHeight * 0.38;
              let active = anchors[0];
              for (const el of anchors) {{
                if (el.getBoundingClientRect().top <= triggerY) active = el;
              }}
              const key = resolveSectionKey(active.id);
              setTip(PAYLOAD.sections[key] || PAYLOAD.default);
              return;
            }}
            if (!lastTip) setTip(PAYLOAD.default);
          }}

          function ensureParentObservers() {{
            win.__winprobGuideRefreshTip = refreshGuideTip;
            win.__winprobGuideSetTip = setTip;
            win.__winprobGuidePayload = PAYLOAD;

            if (win.__winprobGuideScrollBound) return;
            win.__winprobGuideScrollBound = true;

            let scrollTicking = false;
            const onScroll = () => {{
              if (scrollTicking) return;
              scrollTicking = true;
              win.requestAnimationFrame(() => {{
                win.__winprobGuideRefreshTip?.();
                scrollTicking = false;
              }});
            }};

            [win, doc, doc.documentElement, doc.body,
              doc.querySelector(".main"),
              doc.querySelector('[data-testid="stAppViewContainer"]'),
              doc.querySelector('[data-testid="stMain"]'),
            ].filter(Boolean).forEach((target) => {{
              target.addEventListener("scroll", onScroll, {{ passive: true }});
            }});
            win.addEventListener("resize", onScroll);

            doc.body.addEventListener("click", (event) => {{
              const summary = event.target.closest("details summary");
              if (!summary) return;
              window.setTimeout(() => {{
                const details = summary.parentElement;
                if (!details?.open) return;
                const payload = win.__winprobGuidePayload;
                const tip = payload?.expanders?.[summary.innerText.trim()];
                if (tip) win.__winprobGuideSetTip?.(tip);
              }}, 120);
            }}, true);

            new MutationObserver(onScroll).observe(doc.body, {{ childList: true, subtree: true }});
          }}

          const styleEl = doc.getElementById("winprob-guide-style");
          if (styleEl) {{
            styleEl.textContent = STYLES;
          }} else {{
            const style = doc.createElement("style");
            style.id = "winprob-guide-style";
            style.textContent = STYLES;
            doc.head.appendChild(style);
          }}

          let root = getRoot();
          if (!root) {{
            root = doc.createElement("div");
            root.id = "winprob-guide-root";
            doc.body.appendChild(root);
          }}

          doc.body.appendChild(root);

          if (
            root.dataset.version !== DOM_VERSION
            || !root.querySelector(".winprob-guide-character")
            || !root.querySelector("#winprob-guide-minimize")
          ) {{
            root.innerHTML = guideMarkup();
            root.dataset.version = DOM_VERSION;
          }}

          doc.body.classList.add("winprob-guide-active");
          bindGuideControls(root);

          const shouldMinimize = loadGuideMinimized();
          if (root.classList.contains("minimized") !== shouldMinimize) {{
            setGuideMinimized(shouldMinimize);
          }} else if (!shouldMinimize) {{
            applyGuideWidth(loadGuideWidth());
          }}

          ensureParentObservers();
          if (PAYLOAD.force_home) lastTip = "";
          refreshGuideTip();
        }})();
        </script>
        """,
        height=0,
    )
