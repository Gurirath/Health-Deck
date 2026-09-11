import io
import os
import uuid

import qrcode
import requests
import streamlit as st

from core import ai_clients
from core.agent_graph import build_graph
from core.providers import ManualVitalsProvider, SelectboxLocationProvider

API_URL = os.environ.get("HEALTHDECK_API_URL", "http://localhost:8000")
PUBLIC_BASE_URL = os.environ.get("HEALTHDECK_PUBLIC_BASE_URL", "http://localhost:8000")

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
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.processed_audio = None


def qr_png(target):
    buffer = io.BytesIO()
    qrcode.make(target).save(buffer, format="PNG")
    return buffer.getvalue()


def upload_target():
    return f"{PUBLIC_BASE_URL}/upload/{st.session_state.session_id}"


def public_url_looks_local():
    return "localhost" in PUBLIC_BASE_URL or "127.0.0.1" in PUBLIC_BASE_URL


def fetch_session_image():
    try:
        response = requests.get(
            f"{API_URL}/upload/{st.session_state.session_id}/image", timeout=10
        )
        if response.status_code == 200:
            return response.content
    except requests.RequestException:
        return None
    return None


def photo_arrived():
    try:
        response = requests.get(
            f"{API_URL}/upload/{st.session_state.session_id}/status", timeout=10
        )
        if response.status_code == 200:
            return bool(response.json().get("uploaded"))
    except requests.RequestException:
        return False
    return False


def show_photo_confirmation():
    if not photo_arrived():
        return
    image = fetch_session_image()
    if image is None:
        return
    st.image(
        image,
        width=260,
        caption="Photo received — we'll include this in your report.",
    )


def spoken_text(audio, widget_key):
    if audio is None:
        return None
    marker = (widget_key, hash(audio.getvalue()))
    if st.session_state.get("processed_audio") == marker:
        return None
    st.session_state.processed_audio = marker
    return ai_clients.transcribe(audio.getvalue())


def show_photo_qr(caption):
    st.image(qr_png(upload_target()), width=220, caption=caption)
    if public_url_looks_local():
        st.warning(
            "This QR points at localhost, so a phone on the network cannot open it. "
            "Set HEALTHDECK_PUBLIC_BASE_URL to this kiosk's LAN IP "
            "(for example http://192.168.1.50:8000) and restart before the demo."
        )


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
        "solution_sources": state.get("solution_sources", []),
        "image_analysis": state.get("image_analysis"),
        "session_id": st.session_state.session_id,
    }


def blank_state(vitals, symptom_location, complaint):
    return {
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
        "solution_sources": [],
        "image_bytes": fetch_session_image(),
        "image_analysis": None,
        "status": "",
    }


if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "state" not in st.session_state:
    st.session_state.state = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "saved_case_id" not in st.session_state:
    st.session_state.saved_case_id = None
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "processed_audio" not in st.session_state:
    st.session_state.processed_audio = None

st.title("Health Deck")
st.subheader("Tell us what's going on and a doctor will review it.")

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
    show_photo_qr(
        "Optional: scan to send a photo of the problem from your phone. "
        "You can continue without it."
    )
    show_photo_confirmation()
    audio = st.audio_input("Or record what's bothering you", key="audio_intake")
    complaint = st.chat_input("What's bothering you today?")
    spoken = spoken_text(audio, "audio_intake")
    submitted = complaint or spoken
    if submitted:
        st.session_state.messages.append({"role": "user", "content": submitted})
        result = st.session_state.graph.invoke(
            blank_state(vitals, symptom_location, submitted)
        )
        st.session_state.state = result
        st.rerun()

elif state["status"] == "awaiting_answer":
    with st.chat_message("assistant"):
        st.write(state["next_question"])
    with st.expander("Send a photo from your phone"):
        show_photo_qr("Scan to attach a photo to this session.")
    show_photo_confirmation()
    audio_key = f"audio_followup_{state.get('turn_count', 0)}"
    audio = st.audio_input("Or record your answer", key=audio_key)
    typed = st.chat_input("Your answer")
    spoken = spoken_text(audio, audio_key)
    answer = typed or spoken
    if answer:
        st.session_state.messages.append({"role": "assistant", "content": state["next_question"]})
        st.session_state.messages.append({"role": "user", "content": answer})
        state["transcript"].append({"role": "assistant", "content": state["next_question"]})
        state["transcript"].append({"role": "user", "content": answer})
        state["vitals"] = vitals
        state["image_bytes"] = fetch_session_image()
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

    case_id = st.session_state.saved_case_id
    if case_id is None:
        if st.button("Start new case"):
            reset_case()
            st.rerun()
    else:
        case = None
        try:
            r = requests.get(f"{API_URL}/cases/{case_id}", timeout=10)
            r.raise_for_status()
            case = r.json()
        except requests.RequestException:
            pass

        department = (case or {}).get("department") or state.get("department", "the clinical")
        current_status = (case or {}).get("status", "pending")

        with st.chat_message("assistant"):
            if current_status != "prescribed":
                st.info(
                    f"Your report has been sent to the {department} team for a doctor "
                    "to review. Please wait."
                )
                st.caption(f"Case #{case_id}")
                show_photo_confirmation()
                if st.button("Check status"):
                    st.rerun()
            else:
                st.success("A doctor has reviewed your case and written a prescription.")
                st.write(f"Prescribed by: {case.get('doctor_name', '')}")
                medicines = case.get("prescription_medicines", []) or []
                if medicines:
                    st.table(
                        [
                            {
                                "Medicine": medicine.get("name", ""),
                                "Dosage/day": medicine.get("dosage_per_day", ""),
                                "Remark": medicine.get("remark", ""),
                            }
                            for medicine in medicines
                        ]
                    )
                if case.get("doctor_notes"):
                    st.write(f"Notes from the doctor: {case['doctor_notes']}")
                try:
                    report = requests.get(
                        f"{API_URL}/cases/{case_id}/report", timeout=10
                    )
                    if report.status_code == 200:
                        st.download_button(
                            "Download report",
                            data=report.content,
                            file_name=f"health_deck_case_{case_id}.pdf",
                            mime="application/pdf",
                        )
                except requests.RequestException:
                    pass

        if st.button("Start new case"):
            reset_case()
            st.rerun()
