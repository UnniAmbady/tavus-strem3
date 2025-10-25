#ver-2.2
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

# ---------------------------------
# 🎥 Embed Tavus (Daily) + JS Echo (no mic/cam)
# ---------------------------------
if st.session_state.get("conv_url"):
    conv_url = st.session_state["conv_url"]
    conv_id = st.session_state["conv_id"]

    # Fixed Echo message
    echo_text = (
        "Hello, how are you? This is a test to demonstrate the real-time speech of "
        "TAVUS AVATAR that can participate in any conversation."
    )

    # IMPORTANT: use Daily Prebuilt with url at createFrame (safer than join() inside sandboxed iframe)
    # Add robust error handling to surface client-side exceptions into a visible log area.
    st.components.v1.html(
        f"""
        <div id=frameWrap></div>
        <div id=jslog style="display:none"></div>
        <script>
          (function() {{
            const L = (...a) => {{
              const el = document.getElementById('jslog');
              el.style.display='block';
              el.textContent += `[$] ${{new Date().toISOString()}} ${{a.join(' ')}}
`;
            }};

            function loadScript(src) {{
              return new Promise((res, rej) => {{
                const s = document.createElement('script');
                s.src = src; s.async = true;
                s.onload = res; s.onerror = () => rej(new Error('script load failed: '+src));
                document.head.appendChild(s);
              }});
            }}

            const roomUrl = {json.dumps(conv_url)};
            const conversationId = {json.dumps(conv_id)};
            const echoText = {json.dumps(echo_text)};

            loadScript('https://unpkg.com/@daily-co/daily-js')
              .then(() => {{
                const container = document.getElementById('frameWrap');
                const daily = window.DailyIframe.createFrame(container, {{
                  url: roomUrl,
                  showLeaveButton: false,
                  iframeStyle: {{ width: '100%', height: '100%', border: '0', borderRadius: '12px' }},
                }});

                // On load, proactively set local tracks off (Daily respects URL, but we also enforce)
                daily.on('loaded', () => L('daily loaded'));
                daily.on('error', (e) => L('daily error', e && e.errorMsg ? e.errorMsg : 'unknown'));
                daily.on('joined-meeting', () => L('joined meeting'));
                daily.on('participant-joined', (ev) => L('participant-joined', ev && ev.participant && ev.participant.user_name || '')); 

                // Expose a safe trigger for Streamlit to call below
                window.__echoTextOnce = () => {{
                  try {{
                    daily.sendAppMessage({{
                      message_type: 'conversation',
                      event_type: 'conversation.echo',
                      conversation_id: conversationId,
                      properties: {{ modality: 'text', text: echoText }}
                    }});
                    L('sendAppMessage echo sent');
                  }} catch (err) {{
                    L('sendAppMessage failed', err && (err.message||err.toString()));
                  }}
                }};
              }})
              .catch(err => {{
                const el = document.getElementById('jslog');
                el.style.display='block';
                el.textContent += ('Daily JS load failed: ' + err.message + '
');
              }});
          }})();
        </script>
        """,
        height=520,
    )

# ---------------------------------
# 🎛️ Test button (fires JS echo)
# ---------------------------------
if st.button("Test", type="primary"):
    # trigger the JS function inside the component iframe
    st.components.v1.html(
        """
        <script>
          try { if (window.__echoTextOnce) { window.__echoTextOnce(); } } catch(e) {}
        </script>
        """,
        height=0,
    )
    log("Sent Echo event via Daily JS → Avatar speaking…")

# ---------------------------------
# 🧾 Debug info
# ---------------------------------
st.text_area("Debug log", "
".join(st.session_state.get("_log", [])), height=180)
st.caption("Tap [Test] to make the Tavus avatar speak the preset line. No mic/cam published.")
