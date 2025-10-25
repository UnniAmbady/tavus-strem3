#ver-2.4
import streamlit as st
import requests
import json
from datetime import datetime

# ---------------------------------
# 📱 PAGE CONFIG (mobile portrait)
# ---------------------------------
st.set_page_config(
    page_title="TAVUS-2 Echo",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Minimal CSS for clean mobile layout
st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 640px;}
header, footer {visibility: hidden; height: 0;}
iframe {width: 100% !important; border-radius: 12px;}
.stButton>button {width: 100%; padding: 0.9rem 1rem; border-radius: 12px; font-weight: 600;}
textarea {font-family: monospace;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------
# 🔐 Tavus Config (from secrets)
# ---------------------------------
TAVUS_API_KEY = st.secrets["tavus"]["api_key"]
TAVUS_PERSONA_ID = st.secrets["tavus"]["persona_id"]
TAVUS_REPLICA_ID = st.secrets["tavus"]["replica_id"]

# ---------------------------------
# 🪄 Helper Functions
# ---------------------------------
def log(msg):
    st.session_state.setdefault("_log", [])
    stamp = datetime.utcnow().isoformat(timespec='seconds')
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
# 🎥 Embed Tavus (Daily) + JS Echo
# ---------------------------------
if st.session_state.get("conv_url"):
    conv_url = st.session_state["conv_url"]
    conv_id = st.session_state["conv_id"]

    # Fixed Echo message
    echo_text = "Hello, how are you? This is a test to demonstrate the real-time speech of TAVUS AVATAR that can participate in any conversation."

    # JS code: join the conversation silently (no mic/cam) and define echo send
    st.components.v1.html(f"""
        <script src="https://unpkg.com/@daily-co/daily-js"></script>
        <div id="tavus-container" style="width:100%; aspect-ratio:16/9; border-radius:12px; overflow:hidden;"></div>
        <script>
          const container = document.getElementById("tavus-container");
          const daily = window.DailyIframe.createFrame(container, {{
              showLeaveButton: false,
              iframeStyle: {{
                  width: '100%',
                  height: '100%',
                  border: '0',
                  borderRadius: '12px'
              }}
          }});
          daily.join({{
              url: "{conv_url}",
              videoSource: false,    // no local camera
              audioSource: false,    // no mic
              receiveSettings: {{
                  video: true,
                  audio: true
              }}
          }});
          // define the echoText() function to broadcast an Echo event
          window.echoText = function() {{
              daily.sendAppMessage({{
                  message_type: "conversation",
                  event_type: "conversation.echo",
                  conversation_id: "{conv_id}",
                  properties: {{
                      modality: "text",
                      text: "{echo_text}"
                  }}
              }});
          }};
        </script>
    """, height=520)

# ---------------------------------
# 🎛️ Test button
# ---------------------------------
if st.button("Test", type="primary"):
    # Trigger JS function to send Echo event
    st.components.v1.html("""
        <script>
            if (window.echoText) {
                window.echoText();
            } else {
                alert("Echo function not ready.");
            }
        </script>
    """, height=0)
    log("Sent Echo event via Daily JS → Avatar speaking…")

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

st.caption("Tap [Test] to make the Tavus avatar speak the preset line.")

