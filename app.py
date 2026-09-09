import os

import requests
import streamlit as st

from agent_graph import build_graph
from symptom_location import SelectboxLocationProvider
from vitals_provider import ManualVitalsProvider

API_URL = os.environ.get("HEALTHDECK_API_URL", "http://localhost:8000")

ESCALATION_LABELS = {
    "red_flag": "red flag",
    "low_confidence": "low confidence",
    "": "none",
}

st.set_page_config(
    page_title="Health Deck — Triage",
    layout="wide",
    initial_sidebar_state="expanded",
)

KIOSK_CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 2.5rem; padding-bottom: 6rem; max-width: 100%;}
html, body, [class*="css"] {font-size: 19px;}
h1 {font-size: 2.4rem;}
.stButton > button {
    font-size: 1.3rem;
    font-weight: 600;
    padding: 0.9rem 1.6rem;
    width: 100%;
    border-radius: 14px;
}
.stChatMessage {font-size: 1.15rem;}
[data-testid="stChatInput"] textarea {font-size: 1.2rem;}
div[data-baseweb="select"] > div {font-size: 1.15rem; min-height: 3rem;}
</style>
"""
st.markdown(KIOSK_CSS, unsafe_allow_html=True)

vitals_provider = ManualVitalsProvider()
location_provider = SelectboxLocationProvider()


def reset_case():
    st.session_state.messages = []
    st.session_state.state = None
    st.session_state.saved_case_id = None


def format_department(department, escalation_reason):
    if escalation_reason == "red_flag":
        return f"{department} (urgent)"
    return department


def case_payload(state):
    return {
        "vitals": state.get("vitals", {}),
        "chief_complaint": state.get("chief_complaint", ""),
        "symptom_location": state.get("symptom_location", ""),
        "transcript": state.get("transcript", []),
        "extracted": state.get("extracted", {}),
        "red_flags": state.get("red_flags", []),
        "diagnosis": state.get("diagnosis", {}),
        "raw_llm_response": state.get("raw_llm_response") or state.get("diagnosis", {}),
        "escalate": state.get("escalate", False),
        "escalation_reason": state.get("escalation_reason", ""),
        "department": state.get("department", ""),
    }


if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "state" not in st.session_state:
    st.session_state.state = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "saved_case_id" not in st.session_state:
    st.session_state.saved_case_id = None

st.title("Health Deck")
st.subheader("Tell us what's going on and we'll point you to the right care.")

with st.sidebar:
    vitals = vitals_provider.get_vitals()
    st.divider()
    if st.button("Reset conversation"):
        reset_case()
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

state = st.session_state.state

if state is None:
    symptom_location = location_provider.get_location()
    complaint = st.chat_input("What's bothering you today?")
    if complaint:
        st.session_state.messages.append({"role": "user", "content": complaint})
        new_state = {
            "vitals": vitals,
            "chief_complaint": complaint,
            "symptom_location": symptom_location,
            "transcript": [{"role": "user", "content": complaint}],
            "extracted": {},
            "turn_count": 0,
            "ready_to_diagnose": False,
            "red_flags": [],
            "next_question": "",
            "diagnosis": {},
            "raw_llm_response": {},
            "escalate": False,
            "escalation_reason": "",
            "department": "",
            "status": "",
        }
        result = st.session_state.graph.invoke(new_state)
        st.session_state.state = result
        st.rerun()

elif state["status"] == "awaiting_answer":
    with st.chat_message("assistant"):
        st.write(state["next_question"])
    answer = st.chat_input("Your answer")
    if answer:
        st.session_state.messages.append({"role": "assistant", "content": state["next_question"]})
        st.session_state.messages.append({"role": "user", "content": answer})
        state["transcript"].append({"role": "assistant", "content": state["next_question"]})
        state["transcript"].append({"role": "user", "content": answer})
        state["vitals"] = vitals
        result = st.session_state.graph.invoke(state)
        st.session_state.state = result
        st.rerun()

elif state["status"] == "complete":
    if st.session_state.saved_case_id is None:
        try:
            resp = requests.post(f"{API_URL}/cases", json=case_payload(state), timeout=10)
            resp.raise_for_status()
            st.session_state.saved_case_id = resp.json()["id"]
        except requests.RequestException:
            st.error(
                f"Could not file this case to the backend at {API_URL}. "
                "Start it with: uvicorn backend:app --reload"
            )

    diagnosis = state["diagnosis"]
    department = format_department(state["department"], state["escalation_reason"])
    reason_label = ESCALATION_LABELS.get(state["escalation_reason"], state["escalation_reason"])

    with st.chat_message("assistant"):
        if state["escalate"]:
            st.error("This case needs a human clinician to take a look.")
            st.write(f"Recommended department: {department}")
            if state["red_flags"]:
                st.write("Red flags detected:")
                for flag in state["red_flags"]:
                    st.write(f"- {flag}")
            st.write(diagnosis.get("reasoning", ""))
            st.info(diagnosis.get("safety_note", ""))
        else:
            st.success(f"Likely: {diagnosis.get('probable_diagnosis', 'Unclear')}")
            st.write(diagnosis.get("reasoning", ""))
            st.write(diagnosis.get("self_care_advice", ""))
        st.write(f"Confidence: {diagnosis.get('confidence', 0)}% — escalation reason: {reason_label}")

    if st.session_state.saved_case_id is not None:
        st.caption(f"Case #{st.session_state.saved_case_id} filed for clinician review.")

    if st.button("Start new case"):
        reset_case()
        st.rerun()
