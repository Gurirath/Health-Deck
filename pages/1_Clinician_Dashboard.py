import os

import requests
import streamlit as st

import report_builder
from rules import DEPARTMENT_ROUTES

st.set_page_config(page_title="Health Deck — Clinician Dashboard", layout="wide")

API_URL = os.environ.get("HEALTHDECK_API_URL", "http://localhost:8000")

DEPARTMENT_OPTIONS = list(dict.fromkeys(DEPARTMENT_ROUTES.values()))

ESCALATION_LABELS = {
    "red_flag": "red flag",
    "low_confidence": "low confidence",
    "": "none",
}

MED_COL_NAME = "Medicine Name"
MED_COL_DOSAGE = "Dosage (per day)"
MED_COL_REMARK = "Remark"
EMPTY_MED_ROW = {MED_COL_NAME: "", MED_COL_DOSAGE: "", MED_COL_REMARK: ""}


def format_department(department, escalation_reason):
    if escalation_reason == "red_flag":
        return f"{department} (urgent)"
    return department


def to_medicines(rows):
    if hasattr(rows, "to_dict"):
        rows = rows.to_dict("records")
    medicines = []
    for row in rows or []:
        name = str(row.get(MED_COL_NAME, "") or "").strip()
        dosage = str(row.get(MED_COL_DOSAGE, "") or "").strip()
        remark = str(row.get(MED_COL_REMARK, "") or "").strip()
        if not (name or dosage or remark):
            continue
        medicines.append({"name": name, "dosage_per_day": dosage, "remark": remark})
    return medicines


def medicines_table_rows(medicines):
    return [
        {
            "Medicine": medicine.get("name", ""),
            "Dosage/day": medicine.get("dosage_per_day", ""),
            "Remark": medicine.get("remark", ""),
        }
        for medicine in medicines
    ]


def fetch_photo(session_id):
    if not session_id:
        return None
    try:
        response = requests.get(f"{API_URL}/upload/{session_id}/image", timeout=10)
        if response.status_code == 200:
            return response.content
    except requests.RequestException:
        return None
    return None


def load_photo(case):
    stored_path = case.get("photo_path")
    if stored_path and os.path.exists(stored_path):
        return stored_path
    return fetch_photo(case.get("session_id"))


def render_report(report):
    intake = report["patient_intake"]
    ai = report["ai_preliminary_assessment"]

    st.markdown("#### 1. Patient intake")
    st.markdown(f"**Chief complaint:** {intake['chief_complaint']}")
    st.markdown(f"**Symptom location:** {intake['symptom_location'] or 'not given'}")
    st.markdown(f"**Age band:** {intake['age_band'] or 'not given'}")
    st.markdown("**Vitals**")
    st.json(intake["vitals"])
    st.markdown("**Transcript**")
    for turn in intake["transcript"]:
        st.write(f"**{turn.get('role', '?')}:** {turn.get('content', '')}")

    st.markdown("#### 2. AI preliminary assessment")
    st.warning(ai["disclaimer"])
    st.markdown(f"**Probable diagnosis:** {ai['probable_diagnosis'] or 'unclear'}")
    if ai["differential"]:
        st.markdown("**Differential:** " + "; ".join(str(d) for d in ai["differential"]))
    st.markdown(f"**Confidence:** {ai['confidence']}%")
    st.markdown(
        "**Red flags:** "
        + ("; ".join(ai["red_flags"]) if ai["red_flags"] else "none")
    )
    st.markdown(
        f"**Escalation reason:** {ESCALATION_LABELS.get(ai['escalation_reason'], ai['escalation_reason'] or 'none')}"
    )
    st.markdown(f"**Department:** {ai['department']}")
    if ai["self_care_advice"]:
        st.markdown(f"**Self-care advice (AI draft):** {ai['self_care_advice']}")
    if ai["solution_sources"]:
        st.markdown("**Advice sources**")
        for url in ai["solution_sources"]:
            st.markdown(f"- [{url}]({url})")

    rx = report["prescription"]
    st.markdown("#### 3. Prescription")
    if rx["status"] == "prescribed":
        st.markdown(f"**Prescribed by:** {rx['doctor_name']} at {rx['prescribed_at']}")
        if rx["medicines"]:
            st.table(medicines_table_rows(rx["medicines"]))
        if rx["notes"]:
            st.markdown(f"**Notes:** {rx['notes']}")
    else:
        st.markdown("_Not prescribed yet — use the form below._")


st.title("Clinician Dashboard")
st.caption(
    "Every completed case waits here for a doctor to prescribe. Red = a red-flag "
    "priority case. Newest first."
)

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
    st.success("No cases waiting. Every completed case has been prescribed for.")
    st.stop()

st.write(f"{len(open_cases)} case(s) waiting for a doctor.")

for case in open_cases:
    reason = case.get("escalation_reason", "")
    urgent = reason == "red_flag"
    dept_display = format_department(case["effective_department"], reason)
    header = (
        f"{'🔴 ' if urgent else ''}#{case['id']} · {dept_display} · "
        f"conf {case['confidence']}% · {case['created_at']}"
    )
    with st.expander(header, expanded=urgent):
        report = report_builder.build_report(case)

        photo = load_photo(case)
        if photo is not None:
            try:
                st.image(
                    photo, width=280, caption="Patient photo — AI-preliminary only"
                )
            except Exception:
                st.caption("Patient photo is on file but could not be displayed.")

        if case.get("image_analysis"):
            st.markdown("**AI photo observation (not a diagnosis)**")
            st.json(case["image_analysis"])
        elif photo is not None:
            st.caption("Photo on file; no AI observation was recorded for it.")

        render_report(report)

        st.divider()
        st.markdown("#### Complete prescription")
        with st.form(f"prescribe_{case['id']}"):
            doctor_name = st.text_input("Doctor name")
            st.caption("Medicines — add a row per medicine")
            edited_rows = st.data_editor(
                [dict(EMPTY_MED_ROW)],
                key=f"meds_{case['id']}",
                num_rows="dynamic",
                hide_index=True,
                column_config={
                    MED_COL_NAME: st.column_config.TextColumn(MED_COL_NAME),
                    MED_COL_DOSAGE: st.column_config.TextColumn(MED_COL_DOSAGE),
                    MED_COL_REMARK: st.column_config.TextColumn(MED_COL_REMARK),
                },
            )
            notes = st.text_area("Notes for the patient")
            prescribed = st.form_submit_button("Complete Prescription")
            if prescribed:
                medicines = to_medicines(edited_rows)
                if not doctor_name.strip():
                    st.error("Doctor name is required.")
                elif not medicines:
                    st.error("Add at least one medicine row.")
                else:
                    try:
                        r = requests.patch(
                            f"{API_URL}/cases/{case['id']}/prescribe",
                            json={
                                "doctor_name": doctor_name.strip(),
                                "medicines": medicines,
                                "notes": notes.strip(),
                            },
                            timeout=15,
                        )
                        r.raise_for_status()
                        st.rerun()
                    except requests.RequestException:
                        st.error("Could not reach the backend to save the prescription.")

        st.markdown("#### Acknowledge / reassign (does not prescribe)")
        review_options = list(DEPARTMENT_OPTIONS)
        if case["effective_department"] not in review_options:
            review_options.insert(0, case["effective_department"])
        default_index = review_options.index(case["effective_department"])
        with st.form(f"review_{case['id']}"):
            chosen = st.selectbox(
                "Department (override if needed)", review_options, index=default_index
            )
            reviewed = st.form_submit_button("Mark reviewed")
            if reviewed:
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
