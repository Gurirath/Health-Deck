import os

import requests
import streamlit as st

from rules import DEPARTMENT_ROUTES

st.set_page_config(page_title="Health Deck — Clinician Dashboard", layout="wide")

API_URL = os.environ.get("HEALTHDECK_API_URL", "http://localhost:8000")

DEPARTMENT_OPTIONS = list(dict.fromkeys(DEPARTMENT_ROUTES.values()))

ESCALATION_LABELS = {
    "red_flag": "red flag",
    "low_confidence": "low confidence",
    "": "none",
}


def format_department(department, escalation_reason):
    if escalation_reason == "red_flag":
        return f"{department} (urgent)"
    return department


st.title("Clinician Dashboard")
st.caption("Open triage cases from every kiosk session, newest first.")

if st.button("Refresh"):
    st.rerun()

try:
    resp = requests.get(f"{API_URL}/cases/open", timeout=10)
    resp.raise_for_status()
    open_cases = resp.json()
except requests.RequestException:
    st.error(
        f"Could not reach the backend at {API_URL}. "
        "Start it with: uvicorn backend:app --reload"
    )
    st.stop()

if not open_cases:
    st.success("No open cases. Everything triaged so far has been reviewed.")
    st.stop()

st.write(f"{len(open_cases)} open case(s).")

for case in open_cases:
    reason = case.get("escalation_reason", "")
    flag = "ESCALATED" if case["escalate"] else "routine"
    dept_display = format_department(case["effective_department"], reason)
    reason_label = ESCALATION_LABELS.get(reason, reason or "none")
    header = (
        f"#{case['id']} · {flag} · {dept_display} · "
        f"conf {case['confidence']}% · {case['created_at']}"
    )
    with st.expander(header, expanded=case["escalate"]):
        st.write(f"Confidence: {case['confidence']}% — escalation reason: {reason_label}")

        left, right = st.columns(2)
        with left:
            st.markdown(f"**Chief complaint:** {case['chief_complaint']}")
            st.markdown(f"**Symptom location:** {case['symptom_location'] or 'not given'}")
            st.markdown("**Vitals**")
            st.json(case["vitals"])
            st.markdown("**Extracted fields**")
            st.json(case["extracted"])
        with right:
            if case["red_flags"]:
                st.error("Red flags")
                for rf in case["red_flags"]:
                    st.write(f"- {rf}")
            else:
                st.write("No deterministic red flags.")
            st.markdown("**Diagnosis**")
            st.json(case["diagnosis"])
            st.markdown("**Raw LLM response**")
            st.json(case.get("raw_llm_response", {}))

        st.markdown("**Transcript**")
        for turn in case["transcript"]:
            st.write(f"**{turn.get('role', '?')}:** {turn.get('content', '')}")

        options = list(DEPARTMENT_OPTIONS)
        if case["effective_department"] not in options:
            options.insert(0, case["effective_department"])
        default_index = options.index(case["effective_department"])

        with st.form(f"review_{case['id']}"):
            chosen = st.selectbox(
                "Department (override if needed)",
                options,
                index=default_index,
            )
            submitted = st.form_submit_button("Mark reviewed")
            if submitted:
                override = chosen if chosen != case["department"] else None
                try:
                    r = requests.patch(
                        f"{API_URL}/cases/{case['id']}/review",
                        json={"department_override": override},
                        timeout=10,
                    )
                    r.raise_for_status()
                    st.rerun()
                except requests.RequestException:
                    st.error("Could not reach the backend to save the review.")
