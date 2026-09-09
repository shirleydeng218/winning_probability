"""Fixed on-page guide character with scroll-aware tips."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from winprob.guide_content import build_guide_payload

GUIDE_MODE_KEY = "winprob_guide_mode"
_GUIDE_DOM_VERSION = "9"
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
body.winprob-guide-active .main .block-container {
  padding-right: var(--winprob-guide-offset, 20rem);
}
@media (max-width: 960px) {
  #winprob-guide-root { display: none !important; }
  body.winprob-guide-active .main .block-container { padding-right: inherit; }
}
"""

def _bayes_character_html() -> str:
    encoded = base64.b64encode(_BAYES_CAT_PATH.read_bytes()).decode("ascii")
    return (
        f'<img class="winprob-guide-character" '
        f'src="data:image/png;base64,{encoded}" '
        f'alt="Bayes guide cat" />'
    )


def _normalize_guide_mode_state() -> None:
    """Map legacy on/minimal/off values to the boolean toggle."""
    if GUIDE_MODE_KEY not in st.session_state:
        st.session_state[GUIDE_MODE_KEY] = True
        return

    mode = st.session_state[GUIDE_MODE_KEY]
    if mode in ("on", "minimal"):
        st.session_state[GUIDE_MODE_KEY] = True
    elif mode == "off":
        st.session_state[GUIDE_MODE_KEY] = False


def render_guide_sidebar() -> None:
    """Sidebar controls for the Bayes guide."""
    _normalize_guide_mode_state()
    with st.sidebar:
        st.markdown("---")
        st.caption("Guide")
        st.toggle(
            "Bayes guide",
            key=GUIDE_MODE_KEY,
            help="Show Bayes on the right with tips for each section as you scroll.",
        )


def inject_winprob_guide(*, show_home_tip: bool = False) -> None:
    """Inject the fixed guide rail into the parent Streamlit document."""
    _normalize_guide_mode_state()
    mode_on = bool(st.session_state.get(GUIDE_MODE_KEY, True))
    payload = build_guide_payload()
    if show_home_tip:
        payload["force_home"] = True

    payload_json = json.dumps(payload).replace("</", "<\\/")
    character_html = json.dumps(_bayes_character_html())
    styles = _GUIDE_STYLES.replace("`", "")
    dom_version = _GUIDE_DOM_VERSION
    default_width = _GUIDE_DEFAULT_WIDTH
    min_width = _GUIDE_MIN_WIDTH
    max_width = _GUIDE_MAX_WIDTH

    components.html(
        f"""
        <script>
        (function () {{
          const MODE_ON = {json.dumps(mode_on)};
          const PAYLOAD = {payload_json};
          const STYLES = `{styles}`;
          const CHARACTER_HTML = {character_html};
          const DOM_VERSION = {json.dumps(dom_version)};
          const DEFAULT_WIDTH = {default_width};
          const MIN_WIDTH = {min_width};
          const MAX_WIDTH = {max_width};
          const WIDTH_STORAGE_KEY = "winprob_guide_width";
          const doc = window.parent.document;
          const win = window.parent;

          function guideMarkup() {{
            return `
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

          function applyGuideWidth(width) {{
            const clamped = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
            root.style.width = `${{clamped}}px`;
            doc.documentElement.style.setProperty("--winprob-guide-offset", `${{clamped + 52}}px`);
            return clamped;
          }}

          function loadGuideWidth() {{
            const stored = parseInt(win.localStorage.getItem(WIDTH_STORAGE_KEY) || "", 10);
            if (stored >= MIN_WIDTH && stored <= MAX_WIDTH) {{
              return stored;
            }}
            return DEFAULT_WIDTH;
          }}

          function setupGuideResize() {{
            const handle = root.querySelector("#winprob-guide-resize");
            if (!handle || handle.dataset.bound === "1") return;
            handle.dataset.bound = "1";

            let dragging = false;

            const onMove = (clientX) => {{
              const rightEdge = root.getBoundingClientRect().right;
              applyGuideWidth(rightEdge - clientX);
            }};

            handle.addEventListener("mousedown", (event) => {{
              dragging = true;
              handle.classList.add("dragging");
              event.preventDefault();
            }});

            handle.addEventListener(
              "touchstart",
              (event) => {{
                dragging = true;
                handle.classList.add("dragging");
                if (event.touches[0]) {{
                  onMove(event.touches[0].clientX);
                }}
                event.preventDefault();
              }},
              {{ passive: false }}
            );

            win.addEventListener("mousemove", (event) => {{
              if (!dragging) return;
              onMove(event.clientX);
            }});

            win.addEventListener(
              "touchmove",
              (event) => {{
                if (!dragging || !event.touches[0]) return;
                onMove(event.touches[0].clientX);
                event.preventDefault();
              }},
              {{ passive: false }}
            );

            const stopDrag = () => {{
              if (!dragging) return;
              dragging = false;
              handle.classList.remove("dragging");
              win.localStorage.setItem(WIDTH_STORAGE_KEY, String(root.offsetWidth));
            }};

            win.addEventListener("mouseup", stopDrag);
            win.addEventListener("touchend", stopDrag);
          }}

          function removeGuide() {{
            doc.getElementById("winprob-guide-root")?.remove();
            doc.getElementById("winprob-guide-style")?.remove();
            doc.body?.classList.remove("winprob-guide-active");
          }}

          if (!MODE_ON) {{
            removeGuide();
            return;
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

          let root = doc.getElementById("winprob-guide-root");
          if (!root) {{
            root = doc.createElement("div");
            root.id = "winprob-guide-root";
            doc.body.appendChild(root);
          }}

          if (root.dataset.version !== DOM_VERSION || !root.querySelector(".winprob-guide-character")) {{
            root.innerHTML = guideMarkup();
            root.dataset.version = DOM_VERSION;
          }}

          applyGuideWidth(loadGuideWidth());
          setupGuideResize();

          doc.body.classList.add("winprob-guide-active");

          const bubble = root.querySelector("#winprob-guide-text");
          const bubbleWrap = root.querySelector("#winprob-guide-bubble");
          const character = root.querySelector(".winprob-guide-character");
          let lastTip = "";
          let scrollTicking = false;

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

          function setTip(text) {{
            if (!text || !bubble || !bubbleWrap) return;
            if (text === lastTip) return;
            lastTip = text;
            bubble.textContent = text;
            bubbleWrap.classList.add("visible");
            character?.classList.remove("react");
            void character?.offsetWidth;
            character?.classList.add("react");
          }}

          function collectAnchors() {{
            const anchors = Array.from(doc.querySelectorAll("[id]")).filter((el) => shouldTrackSection(el.id));
            return anchors.sort((a, b) => {{
              if (a === b) return 0;
              const position = a.compareDocumentPosition(b);
              if (position & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
              if (position & Node.DOCUMENT_POSITION_PRECEDING) return 1;
              return 0;
            }});
          }}

          function getActiveAnchor(anchors) {{
            if (!anchors.length) return null;
            const viewportHeight = win.innerHeight || doc.documentElement.clientHeight;
            // Trigger when section title reaches the upper half of the viewport.
            const triggerY = viewportHeight * 0.38;

            let active = anchors[0];
            for (const el of anchors) {{
              const top = el.getBoundingClientRect().top;
              if (top <= triggerY) {{
                active = el;
              }}
            }}
            return active;
          }}

          function updateGuideFromScroll() {{
            const anchors = collectAnchors();
            const active = getActiveAnchor(anchors);
            if (!active) return;
            const key = resolveSectionKey(active.id);
            const tip = PAYLOAD.sections[key] || PAYLOAD.default;
            setTip(tip);
          }}

          function onScroll() {{
            if (scrollTicking) return;
            scrollTicking = true;
            win.requestAnimationFrame(() => {{
              updateGuideFromScroll();
              scrollTicking = false;
            }});
          }}

          if (PAYLOAD.force_home) {{
            setTip(PAYLOAD.home || PAYLOAD.default);
          }} else {{
            updateGuideFromScroll();
            if (!lastTip) {{
              setTip(PAYLOAD.default);
            }}
          }}

          const scrollTargets = [
            win,
            doc,
            doc.documentElement,
            doc.body,
            doc.querySelector(".main"),
            doc.querySelector('[data-testid="stAppViewContainer"]'),
            doc.querySelector('[data-testid="stMain"]'),
          ].filter(Boolean);

          scrollTargets.forEach((target) => {{
            target.addEventListener("scroll", onScroll, {{ passive: true }});
          }});
          win.addEventListener("resize", onScroll);

          if (!doc.body.dataset.winprobGuideClickBound) {{
            doc.body.dataset.winprobGuideClickBound = "1";
            doc.body.addEventListener("click", (event) => {{
              const summary = event.target.closest("details summary");
              if (!summary) return;
              window.setTimeout(() => {{
                const details = summary.parentElement;
                if (!details?.open) return;
                const label = summary.innerText.trim();
                const tip = PAYLOAD.expanders[label];
                if (tip) setTip(tip);
              }}, 120);
            }}, true);
          }}

          if (!doc.body.dataset.winprobGuideMutationBound) {{
            doc.body.dataset.winprobGuideMutationBound = "1";
            const mo = new MutationObserver(() => onScroll());
            mo.observe(doc.body, {{ childList: true, subtree: true }});
          }}
        }})();
        </script>
        """,
        height=0,
    )
