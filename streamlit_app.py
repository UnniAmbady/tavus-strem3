import json
import time
from datetime import datetime

import requests
import streamlit as st

##############################
# ⚙️ App Config (iPhone-first)
##############################
st.set_page_config(
    page_title="TAVUS-2 Echo",
    page_icon="🎙️",
    layout="centered",               # Single-column, good for phones
    initial_sidebar_state="collapsed" # No side panels
)

# Minimal CSS to tighten spacing and hide default Streamlit chrome on mobile
st.markdown(
    """
    <style>
      /* Keep things compact for portrait phones */
      .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 640px;}
      header {visibility: hidden; height: 0;}       /* hide top menu */
      footer {visibility: hidden; height: 0;}       /* hide footer */
      /* Make iframe responsive-ish without horizontal scroll */
      iframe { width: 100% !important; border-radius: 12px;}
      /* Neat primary button */
      .stButton>button { width: 100%; padding: 0.9rem 1rem; border-radius: 12px; font-weight: 600; }
      /* Debug box monospace */
      textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    </style>
    """,
    unsafe_allow_html=True,
)

########################################
# 🔐 Secrets (set these in .streamlit/secrets.toml)
########################################
#
# [tavus]
# api_key = "YOUR_TAVUS_API_KEY"
# persona_id = "YOUR_TAVUS_PERSONA_ID"
# replica_id = "YOUR_TAVUS_REPLICA_ID"
#
# # Optional: override if your tenant uses a different interactions path
# TAVUS_INTERACTIONS_URL = "https://tavusapi.com/v2/interactions/broadcast"
#
########################################################
# 🧰 Tavus REST helpers (Conversation + Echo interaction)
########################################################
TAVUS_API_KEY    = st.secrets["tavus"]["api_key"]
TAVUS_PERSONA_ID = st.secrets["tavus"]["persona_id"]
TAVUS_REPLICA_ID = st.secrets["tavus"]["replica_id"]
TAVUS_INTERACTIONS_URL = st.secrets.get(
    "TAVUS_INTERACTIONS_URL",
    "https://tavusapi.com/v2/interactions/broadcast",
)

HEADERS_JSON = {"x-api-key": TAVUS_API_KEY, "Content-Type": "application/json"}


def log(msg: str):
    st.session_state.setdefault("_log", [])
    st.session_state["_log"].append(f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] {msg}")


def create_conversation() -> tuple[str, str]:
    """Create a real-time conversation and return (conversation_id, embed_url)."""
    url = "https://tavusapi.com/v2/conversations"
    payload = {
        "persona_id": TAVUS_PERSONA_ID,
        "replica_id": TAVUS_REPLICA_ID,
        "conversation_name": f"TAVUS-2 Echo {datetime.utcnow().isoformat(timespec='seconds')}Z",
    }
    log("POST /v2/conversations — creating conversation …")
    r = requests.post(url, json=payload, headers=HEADERS_JSON, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Conversation create failed: {r.status_code} — {r.text}")
    data = r.json()
    conv_id = data["conversation_id"]
    conv_url = data["conversation_url"]
    log(f"Conversation created ✓ id={conv_id}")
    return conv_id, conv_url


def end_conversation(conversation_id: str):
    url = f"https://tavusapi.com/v2/conversations/{conversation_id}/end"
    log(f"POST /v2/conversations/{{id}}/end — ending {conversation_id} …")
    try:
        requests.post(url, headers={"x-api-key": TAVUS_API_KEY}, timeout=15)
        log("Conversation ended ✓")
    except Exception as e:
        log(f"Conversation end error: {e}")


def broadcast_echo(conversation_id: str, text: str):
    """Broadcast an Echo interaction so the avatar says exactly `text`."""
    payload = {
        "message_type": "conversation",
        "event_type": "conversation.echo",
        "conversation_id": conversation_id,
        "properties": {"text": text},
    }
    log(f"POST interactions.broadcast — conversation.echo (len={len(text)}) …")
    r = requests.post(TAVUS_INTERACTIONS_URL, headers=HEADERS_JSON, data=json.dumps(payload), timeout=30)
    if r.status_code >= 400:
        log(f"Echo broadcast failed: {r.status_code} — {r.text}")
        st.error(f"Echo broadcast failed: {r.status_code}\n{r.text}")
    else:
        log("Echo broadcast ✓")


############################
# 🧭 ‘≡’ Settings (hamburger)
############################
colA, colB = st.columns([1, 4])
with colA:
    # Use an expander as a simple pull-down menu
    with st.expander("≡", expanded=False):
        st.caption("Quick settings")
        if st.button("🔄 New Session", use_container_width=True):
            # End any existing session then create a fresh one
            if st.session_state.get("conv_id"):
                end_conversation(st.session_state["conv_id"])
                for k in ("conv_id", "conv_url"):
                    st.session_state.pop(k, None)
            try:
                conv_id, conv_url = create_conversation()
                st.session_state["conv_id"] = conv_id
                st.session_state["conv_url"] = conv_url
                st.success("New session ready.")
            except Exception as e:
                st.error(str(e))
        if st.button("🛑 End Session", use_container_width=True):
            if st.session_state.get("conv_id"):
                end_conversation(st.session_state["conv_id"])
                for k in ("conv_id", "conv_url"):
                    st.session_state.pop(k, None)
                st.warning("Session ended.")
        st.divider()
        st.caption("Echo text (optional override)")
        st.text_input(
            "",
            key="_custom_echo",
            value="",
            placeholder="Type custom echo line…",
            label_visibility="collapsed",
        )

with colB:
    st.markdown("# 🎙️ TAVUS-2 Echo")
    st.caption("Single-page, portrait-optimized demo. Tap *Speak* to make the avatar talk.")

###############################
# 🔌 Ensure a live conversation
###############################
if "conv_id" not in st.session_state or "conv_url" not in st.session_state:
    try:
        conv_id, conv_url = create_conversation()
        st.session_state["conv_id"] = conv_id
        st.session_state["conv_url"] = conv_url
        st.toast("Conversation started.")
    except Exception as e:
        st.error(str(e))

#########################################
# 🎥 Avatar embed (WebRTC room via Tavus)
#########################################
if st.session_state.get("conv_url"):
    st.components.v1.iframe(st.session_state["conv_url"], height=520)
else:
    st.info("Start a session to load the live avatar…")

#########################################
# 🗣️ Speak button (Echo Interaction)
#########################################
DEFAULT_LINE = (
    " Helo, how are you? this is a Test to demonstrate the real-time speach of "
    " TAVUS AVTAR that can participate in any any conversation."
)

speak_pressed = st.button("▶️ Speak", type="primary")

if speak_pressed:
    if not st.session_state.get("conv_id"):
        st.error("No active conversation. Try ‘New Session’ in ≡.")
    else:
        line = st.session_state.get("_custom_echo") or DEFAULT_LINE
        try:
            broadcast_echo(st.session_state["conv_id"], line)
            st.success("Speaking… check the avatar above.")
        except Exception as e:
            st.error(str(e))

#########################################
# 🧪 Debug info (per stage logs)
#########################################
log_text = "\n".join(st.session_state.get("_log", []))
st.text_area(
    "Debug log",
    value=log_text,
    height=180,
    key="_log_view",
)

#############################
# 🧹 Cleanup hint for users
#############################
st.caption("Tip: Use the ‘≡’ menu to end or restart the session.")
