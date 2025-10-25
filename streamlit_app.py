#ver-2.5
import streamlit as st
import requests
import json
from datetime import datetime
from html import escape

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
      #frameWrap{width:100%;aspect-ratio:16/9;border-radius:12px;overflow:hidden}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------
# 🔐 Tavus Config (from secrets)
# ---------------------------------
TAVUS_API_KEY = st.secrets["tavus"]["api_key"]
TAVUS_PERSONA_ID = st.secrets["tavus"]["persona_id"]
TAVUS_REPLICA_ID = st.secrets["tavus"]["replica_id"]

# ---------------------------------
# 🪄 Helper Functions
# ---------------------------------
def log(msg: str):
    st.session_state.setdefault("_log", [])
    stamp = datetime.utcnow().isoformat(timespec="seconds")
    st.session_state["_log"].append(f"[{stamp}Z] {msg}")


def create_conversation():
    """Create a new Tavus conversation and return (id, url)."""
    url = "https://tavusapi.com/v2/conversations"
    payload = {
        "persona_id": TAVUS_PERSONA_ID,
        "replica_id": TAVUS_REPLICA_ID,
        "conversation_name": f"TAVUS-Echo-{datetime.utcnow().isoformat(timespec='seconds')}"
    }
    headers = {"x-api-key": TAVUS_API_KEY, "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Conversation creation failed: {r.status_code} - {r.text}")
    data = r.json()
    log(f"Conversation created ✓ id={data['conversation_id']}")
    return data["conversation_id"], data["conversation_url"]

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

# A flip-flop trigger to avoid cross-iframe calls. We pass this value into the
# single HTML component; when True, JS will send the Echo once and we reset it.
if "_echo_trigger" not in st.session_state:
    st.session_state["_echo_trigger"] = False
if "_echo_nonce" not in st.session_state:
    st.session_state["_echo_nonce"] = 0

# ---------------------------------
# 🎥 Embed Tavus (Daily) + JS Echo (single component, no cross-iframe)
# ---------------------------------
if st.session_state.get("conv_url"):
    conv_url = st.session_state["conv_url"]
    conv_id = st.session_state["conv_id"]

    echo_text = (
        "Hello, how are you? This is a test to demonstrate the real-time speech of "
        "TAVUS AVATAR that can participate in any conversation."
    )

    TRIGGER = st.session_state["_echo_trigger"]  # bool -> injected into JS
    NONCE = st.session_state["_echo_nonce"]      # forces refresh when changed

    html = f"""
        <div id="frameWrap" style="width:100%;aspect-ratio:16/9;border-radius:12px;overflow:hidden;"></div>
        <pre id="jslog" style="display:none;white-space:pre-wrap;font-size:12px;background:#0b1020;color:#d6e1ff;padding:8px;border-radius:8px;margin-top:8px;"></pre>
        <script>
          (function() {{
            const TRIGGER = {json.dumps(bool(TRIGGER)).lower()};
            const NONCE = {int(NONCE)}; // force rerender usage if needed
            const roomUrl = {json.dumps(conv_url)};
            const conversationId = {json.dumps(conv_id)};
            const echoText = {json.dumps(echo_text)};

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
              daily.on('joined-meeting', () => {{
                log('joined meeting');
                if (TRIGGER) sendEcho();
              }});

              // If already joined by the time TRIGGER flips on rerender
              try {{
                // Prebuilt joins automatically; if TRIGGER and not yet joined, the handler above will fire.
                if (TRIGGER && daily.participants && Object.keys(daily.participants()).length) {{
                  sendEcho();
                }}
              }} catch(_e) {{}}

              // Also expose a manual function for future use (stays inside same component)
              window.__echoTextOnce = sendEcho;
            }}).catch(err => {{
              log('Daily JS load failed:', err && err.message ? err.message : err);
            }});
          }})();
        </script>
    """

    # Single component render. Changing NONCE or TRIGGER re-renders this one component only.
    st.components.v1.html(html, height=520, key=f"tavus_iframe_{NONCE}")

# ---------------------------------
# 🎛️ Test button (toggles trigger and re-renders component)
# ---------------------------------
if st.button("Test", type="primary"):
    st.session_state["_echo_trigger"] = True
    st.session_state["_echo_nonce"] += 1  # bump to force re-render
    log("Echo trigger set → component will send on next render.")
    st.rerun()

# After rerun, clear trigger so it only fires once per press
if st.session_state.get("_echo_trigger"):
    st.session_state["_echo_trigger"] = False

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


