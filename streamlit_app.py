# Ver-3.3 — TAVUS-3 Echo (Daily Interactions) — iPhone-friendly

import json
from datetime import datetime

import requests
import streamlit as st

# ---------------------------------
# 📱 PAGE CONFIG (mobile portrait)
# ---------------------------------
st.set_page_config(
    page_title="TAVUS-2 Echo",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Minimal CSS for clean mobile layout
st.markdown(
    """
    <style>
      .block-container{padding-top:1rem;padding-bottom:2rem;max-width:640px}
      header,footer{visibility:hidden;height:0}
      .stButton>button{width:100%;padding:0.9rem 1rem;border-radius:12px;font-weight:600}
      textarea{font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace}
      #frameWrap{width:100%;height:360px;border-radius:12px;overflow:hidden;background:#0b1020}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------
# 🔐 Tavus Config (from secrets) (from secrets)
# ---------------------------------
TAVUS_API_KEY = st.secrets["tavus"]["api_key"]
TAVUS_PERSONA_ID = st.secrets["tavus"]["persona_id"]
TAVUS_REPLICA_ID = st.secrets["tavus"]["replica_id"]

API_HEADERS = {"x-api-key": TAVUS_API_KEY, "Content-Type": "application/json"}

# ---------------------------------
# 🪄 Helper Utilities
# ---------------------------------
def log(msg: str):
    st.session_state.setdefault("_log", [])
    stamp = datetime.utcnow().isoformat(timespec="seconds")
    st.session_state["_log"].append(f"[{stamp}Z] {msg}")


def create_conversation():
    """Create a new Tavus conversation and return (id, url). If max concurrent
    conversations reached, raise a friendly message so user can end current one.
    """
    url = "https://tavusapi.com/v2/conversations"
    payload = {
        "persona_id": TAVUS_PERSONA_ID,
        "replica_id": TAVUS_REPLICA_ID,
        "conversation_name": f"TAVUS-Echo-{datetime.utcnow().isoformat(timespec='seconds')}"
    }
    r = requests.post(url, json=payload, headers=API_HEADERS, timeout=30)
    if r.status_code >= 400:
        try:
            data = r.json()
            msg = data.get("message", r.text)
        except Exception:
            msg = r.text
        raise RuntimeError(f"Conversation creation failed: {r.status_code} - {msg}")
    data = r.json()
    log(f"Conversation created ✓ id={data['conversation_id']}")
    return data["conversation_id"], data["conversation_url"]


def end_conversation(conversation_id: str):
    url = f"https://tavusapi.com/v2/conversations/{conversation_id}/end"
    try:
        requests.post(url, headers={"x-api-key": TAVUS_API_KEY}, timeout=20)
        log("Conversation ended ✓")
    except Exception as e:
        log(f"End conversation error: {e}")

# ---------------------------------
# 🎬 Create / Load conversation
# ---------------------------------
if "conv_id" not in st.session_state:
    try:
        cid, curl = create_conversation()
        st.session_state["conv_id"] = cid
        st.session_state["conv_url"] = curl
        log("Conversation ready.")
    except Exception as e:
        st.error(str(e))

# Toolbar (≡) with session control
cols = st.columns([1,4])
with cols[0]:
    with st.expander("≡", expanded=False):
        if st.button("🔄 New Session", use_container_width=True):
            if st.session_state.get("conv_id"):
                end_conversation(st.session_state["conv_id"])
                st.session_state.pop("conv_id", None)
                st.session_state.pop("conv_url", None)
            try:
                cid, curl = create_conversation()
                st.session_state["conv_id"] = cid
                st.session_state["conv_url"] = curl
                st.success("New session ready.")
            except Exception as e:
                st.error(str(e))
        if st.button("🛑 End Session", use_container_width=True):
            if st.session_state.get("conv_id"):
                end_conversation(st.session_state["conv_id"])
                st.session_state.pop("conv_id", None)
                st.session_state.pop("conv_url", None)
                st.warning("Session ended.")

with cols[1]:
    st.markdown("# 🎙️ TAVUS-2 Echo — Ver 3.0")
    st.caption("Single-page, portrait-optimized. Press Test to trigger Echo over the live CVI data channel.")

# One-shot trigger value placed in the component markup itself (no `key` arg)
if "_echo_nonce" not in st.session_state:
    st.session_state["_echo_nonce"] = 0

# ---------------------------------
# 🎥 Embed Tavus (Daily) + JS Echo (single component, no mic/cam publish)
# ---------------------------------
if st.session_state.get("conv_url"):
    conv_url = st.session_state["conv_url"]
    conv_id = st.session_state["conv_id"]

    echo_text = (
        "Hello, how are you? This is a test to demonstrate the real-time speech of "
        "TAVUS AVATAR that can participate in any conversation."
    )

    NONCE = int(st.session_state["_echo_nonce"])  # included in DOM to force refresh

    html = f"""
        <div id="frameWrap"></div>
        <pre id="jslog" style="display:none;white-space:pre-wrap;font-size:12px;background:#0b1020;color:#d6e1ff;padding:8px;border-radius:8px;margin-top:8px;"></pre>
        <div id="nonce" data-v="{NONCE}" style="display:none"></div>
        <script>
          (function() {{
            const roomUrl = {json.dumps(conv_url)};
            const conversationId = {json.dumps(conv_id)};
            const echoText = {json.dumps(echo_text)};
            const pendingEcho = true; // when NONCE changes, we plan to send one echo

            function log() {{
              const el = document.getElementById('jslog');
              el.style.display='block';
              el.textContent += Array.from(arguments).join(' ') + "
";
            }}

            function loadScript(src) {{
              return new Promise((res, rej) => {{
                const s = document.createElement('script');
                s.src = src; s.async = true;
                s.onload = res; s.onerror = () => rej(new Error('script load failed: '+src));
                document.head.appendChild(s);
              }});
            }}

            loadScript('https://unpkg.com/@daily-co/daily-js').then(() => {{
              const container = document.getElementById('frameWrap');
              const daily = window.DailyIframe.createFrame(container, {{
                url: roomUrl,
                showLeaveButton: false,
                iframeStyle: {{ width: '100%', height: '100%', border: '0', borderRadius: '12px' }},
              }});

              function sendEcho() {{
                try {{
                  daily.sendAppMessage({{
                    message_type: 'conversation',
                    event_type: 'conversation.echo',
                    conversation_id: conversationId,
                    properties: {{ modality: 'text', text: echoText }}
                  }});
                  log('sendAppMessage: echo sent');
                }} catch (e) {{
                  log('sendAppMessage error:', e && (e.message || e.toString()));
                }}
              }}

              daily.on('error', (e) => log('daily error:', e && e.errorMsg ? e.errorMsg : 'unknown'));
              daily.on('loaded', () => log('daily loaded'));
              daily.on('joined-meeting', async () => {{
                log('joined meeting');
                try {{
                  // ensure local publishing stays off
                  await daily.setLocalAudio(false);
                  await daily.setLocalVideo(false);
                  log('local tracks disabled');
                }} catch(_e) {{}}
                // send queued echo once joined
                if (pendingEcho) sendEcho();
              }});

              // Defensive: if already joined (fast joins), try immediately
              try {{
                const parts = daily.participants && daily.participants();
                if (parts && Object.keys(parts).length) {{
                  sendEcho();
                }}
              }} catch(_e) {{}}

              // keep a manual hook for future
              window.__echoTextOnce = sendEcho;
            }}).catch(err => {{
              log('Daily JS load failed:', err && err.message ? err.message : err);
            }});
          }})();
        </script>
    """

    # IMPORTANT: Streamlit 1.50's html() does NOT accept `key`; omit it.
    st.components.v1.html(html, height=520)

# ---------------------------------
# 🎛️ Test button (increments NONCE → component auto-sends once on render)
# ---------------------------------
if st.button("Test", type="primary"):
    st.session_state["_echo_nonce"] += 1
    log("Echo trigger set → component will send on next render.")
    st.rerun()

# ---------------------------------
# 🧾 Debug info
# ---------------------------------
st.text_area(
    label="Debug log",
    value="\n".join(st.session_state.get("_log", [])),
    height=180,
    key="debug_log",
    disabled=True,
)
st.caption("Tap [Test] to make the Tavus avatar speak the preset line. No mic/cam published.")
