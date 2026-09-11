"""Builds the case report the doctor reads and the patient prints.

build_report(case_state) returns a dict with three plainly separated
sections: patient_intake, ai_preliminary_assessment (clearly labelled as
model output, not a diagnosis or prescription), and prescription (empty
until a doctor fills it in).

generate_pdf(case_id, report_dict) renders those sections as an
OVERSIMPLIFIED HOSPITAL patient care report to reports/{case_id}.pdf and
returns the path. Call it only once a prescription exists.

The header logo is read from LOGO_PATH (assets/logo.png next to this
module). If it is missing the report still generates, without the image.
"""

import io
import logging
import os
from datetime import datetime, timezone

import qrcode
from fpdf import FPDF
from fpdf.fonts import FontFace

from core import config

REPORTS_DIR = config.get_reports_dir()
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(_PROJECT_ROOT, "assets", "logo.png")
PUBLIC_BASE_URL = config.get_public_base_url()

HOSPITAL_NAME = "OVERSIMPLIFIED HOSPITAL"
CONTACT_LINE = "Gurirath · Aman · Keerthana · Aryaansh"
EMERGENCY_DISCLAIMER = (
    "This report records an AI-assisted triage session and a doctor's prescription. "
    "It is not a substitute for in-person medical care. In an emergency, call your "
    "local emergency number or go to the nearest emergency department."
)

AI_DISCLAIMER = (
    "AI-generated, for clinician reference only. This is not a diagnosis or a "
    "prescription."
)

logger = logging.getLogger("healthdeck.report")


def _first_present(source, *keys):
    for key in keys:
        value = source.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def build_report(case_state):
    diagnosis = case_state.get("diagnosis", {}) or {}
    extracted = case_state.get("extracted", {}) or {}

    patient_intake = {
        "chief_complaint": case_state.get("chief_complaint", ""),
        "symptom_location": case_state.get("symptom_location", ""),
        "age_band": _first_present(case_state, "age_band")
        or _first_present(extracted, "age_band", "age"),
        "session_ref": case_state.get("session_id", "") or "",
        "vitals": case_state.get("vitals", {}) or {},
        "transcript": case_state.get("transcript", []) or [],
    }

    ai_preliminary_assessment = {
        "disclaimer": AI_DISCLAIMER,
        "probable_diagnosis": diagnosis.get("probable_diagnosis", ""),
        "differential": _first_present(diagnosis, "differential", "differentials") or [],
        "confidence": diagnosis.get("confidence", case_state.get("confidence", 0)),
        "red_flags": case_state.get("red_flags", []) or [],
        "escalation_reason": case_state.get("escalation_reason", ""),
        "department": case_state.get("effective_department")
        or case_state.get("department", ""),
        "image_analysis": case_state.get("image_analysis"),
        "self_care_advice": diagnosis.get("self_care_advice", ""),
        "solution_sources": case_state.get("solution_sources", []) or [],
    }

    prescription = {
        "doctor_name": case_state.get("doctor_name") or "",
        "medicines": case_state.get("prescription_medicines", []) or [],
        "notes": case_state.get("doctor_notes") or "",
        "prescribed_at": case_state.get("prescribed_at") or "",
        "status": case_state.get("status", "pending"),
    }

    return {
        "patient_intake": patient_intake,
        "ai_preliminary_assessment": ai_preliminary_assessment,
        "prescription": prescription,
    }


def _safe(value):
    return str(value).encode("latin-1", "replace").decode("latin-1")


def _text(value):
    if value in (None, "", [], {}):
        return "-"
    return _safe(value)


def _content_width(pdf):
    return pdf.w - pdf.l_margin - pdf.r_margin


def _rule(pdf):
    y = pdf.get_y()
    pdf.set_draw_color(160, 160, 160)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(3)


def _section_title(pdf, text):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(238, 238, 238)
    pdf.multi_cell(0, 8, _safe(text), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)


def _field(pdf, label, value):
    pdf.set_font("Helvetica", "B", 10)
    pdf.write(6, _safe(f"{label}: "))
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, _text(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _indented_lines(pdf, lines, height=5.5, size=10):
    pdf.set_font("Helvetica", "", size)
    for line in lines:
        pdf.set_x(pdf.l_margin + 6)
        pdf.multi_cell(_content_width(pdf) - 6, height, _safe(line), new_x="LMARGIN", new_y="NEXT")


def _header(pdf, case_id, report_dict):
    intake = report_dict["patient_intake"]
    rx = report_dict["prescription"]
    header_top = pdf.get_y()
    text_x = pdf.l_margin

    if os.path.exists(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=pdf.l_margin, y=header_top, w=22, h=22)
            text_x = pdf.l_margin + 27
        except Exception as exc:
            logger.warning("Could not place logo %s: %s", LOGO_PATH, exc)
    else:
        logger.warning("Logo not found at %s; rendering header without it.", LOGO_PATH)

    pdf.set_xy(text_x, header_top + 1)
    pdf.set_font("Helvetica", "B", 19)
    pdf.cell(0, 9, _safe(HOSPITAL_NAME), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(text_x)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _safe("Point of contact: " + CONTACT_LINE), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(text_x)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, _safe("Patient care report"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(max(pdf.get_y(), header_top + 24))
    _rule(pdf)

    prescribed_at = rx["prescribed_at"] or ""
    date_str = prescribed_at.split("T")[0] or datetime.now(timezone.utc).date().isoformat()
    session_ref = intake.get("session_ref") or "-"
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0,
        6,
        _safe(f"Case ID: {case_id}     Date: {date_str}     Patient session ref: {session_ref}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(1)


def _section_intake(pdf, intake):
    _section_title(pdf, "1. Patient Intake")

    vitals = intake["vitals"]
    known = ("spo2", "temp_c", "hr", "systolic_bp", "diastolic_bp")
    labels = {
        "spo2": "SpO2 (%)",
        "temp_c": "Temperature (C)",
        "hr": "Heart rate (bpm)",
        "systolic_bp": "Systolic BP",
        "diastolic_bp": "Diastolic BP",
    }
    rows = [(labels[key], vitals.get(key)) for key in known if key in vitals]
    rows += [(key, value) for key, value in vitals.items() if key not in known]
    if not rows:
        rows = [("Vitals", "not recorded")]

    label_w = 55
    value_w = _content_width(pdf) - label_w
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w, 7, _safe(label), border=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(value_w, 7, _text(value), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    _field(pdf, "Chief complaint", intake["chief_complaint"])
    _field(pdf, "Symptom location", intake["symptom_location"])
    _field(pdf, "Age band", intake["age_band"])

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 6, _safe("Conversation"), new_x="LMARGIN", new_y="NEXT")
    role_names = {"user": "Patient", "assistant": "Assistant", "system": "System"}
    lines = [
        f"{role_names.get(turn.get('role', ''), turn.get('role', '?'))}: {turn.get('content', '')}"
        for turn in intake["transcript"]
    ]
    _indented_lines(pdf, lines or ["(no conversation recorded)"])
    pdf.ln(2)


def _section_assessment(pdf, ai):
    _section_title(pdf, "2. AI Preliminary Assessment")

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(255, 243, 205)
    pdf.set_draw_color(210, 170, 60)
    pdf.set_line_width(0.4)
    pdf.multi_cell(
        _content_width(pdf), 6, _safe(ai["disclaimer"]), border=1, fill=True, new_x="LMARGIN", new_y="NEXT"
    )
    pdf.set_draw_color(160, 160, 160)
    pdf.set_line_width(0.3)
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)

    _field(pdf, "Probable diagnosis", ai["probable_diagnosis"])
    if ai["differential"]:
        _field(pdf, "Differential", "; ".join(str(item) for item in ai["differential"]))
    _field(pdf, "Confidence", f"{ai['confidence']}%")
    _field(pdf, "Red flags", "; ".join(ai["red_flags"]) if ai["red_flags"] else "none")
    _field(pdf, "Department", ai["department"])

    if ai["image_analysis"]:
        analysis = ai["image_analysis"]
        _field(pdf, "Photo - description", analysis.get("description", ""))
        _field(
            pdf,
            "Photo - visual characteristics",
            "; ".join(analysis.get("visual_characteristics", [])) or "-",
        )
        _field(pdf, "Photo - note", analysis.get("note", ""))
    else:
        _field(pdf, "Photo", "no photo submitted")

    _field(pdf, "Self-care advice (AI draft)", ai["self_care_advice"])
    if ai["solution_sources"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 6, _safe("Advice sources"), new_x="LMARGIN", new_y="NEXT")
        _indented_lines(pdf, ai["solution_sources"], height=5, size=9)
        pdf.ln(1)


def _section_prescription(pdf, rx):
    _section_title(pdf, "3. Prescription")
    _field(pdf, "Prescribing doctor", rx["doctor_name"])
    _field(pdf, "Prescribed at", rx["prescribed_at"])

    pdf.set_font("Helvetica", "", 10)
    medicines = rx["medicines"]
    if medicines:
        with pdf.table(
            width=_content_width(pdf),
            col_widths=(80, 40, 70),
            text_align=("LEFT", "CENTER", "LEFT"),
            first_row_as_headings=True,
            headings_style=FontFace(emphasis="BOLD", fill_color=(230, 230, 230)),
        ) as table:
            table.row(("Medicine", "Dosage/day", "Remark"))
            for medicine in medicines:
                table.row(
                    (
                        _safe(medicine.get("name", "") or "-"),
                        _safe(medicine.get("dosage_per_day", "") or "-"),
                        _safe(medicine.get("remark", "") or "-"),
                    )
                )
    else:
        _field(pdf, "Medicines", "none recorded")
    pdf.ln(3)

    _field(pdf, "Doctor notes", rx["notes"])

    if pdf.get_y() > pdf.h - pdf.b_margin - 22:
        pdf.add_page()
    pdf.ln(14)
    sig_y = pdf.get_y()
    pdf.set_draw_color(120, 120, 120)
    pdf.line(pdf.l_margin, sig_y, pdf.l_margin + 65, sig_y)
    pdf.set_xy(pdf.l_margin, sig_y + 1)
    pdf.set_font("Helvetica", "", 10)
    doctor = rx["doctor_name"] or "____________"
    pdf.cell(0, 5, _safe(f"Dr. {doctor}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _footer_block(pdf, case_id):
    if pdf.get_y() > pdf.h - pdf.b_margin - 34:
        pdf.add_page()
    _rule(pdf)

    footer_top = pdf.get_y()
    report_base = config.get_public_base_url()
    report_url = f"{report_base}/cases/{case_id}/report"
    qr_buffer = io.BytesIO()
    qrcode.make(report_url).save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    try:
        pdf.image(qr_buffer, x=pdf.l_margin, y=footer_top, w=22, h=22)
    except Exception as exc:
        logger.warning("Could not place report QR: %s", exc)

    pdf.set_xy(pdf.l_margin + 26, footer_top + 2)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        _content_width(pdf) - 26, 5, _safe("Scan to re-download this report"), new_x="LMARGIN", new_y="NEXT"
    )
    pdf.set_x(pdf.l_margin + 26)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(_content_width(pdf) - 26, 4.5, _safe(report_url), new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(max(pdf.get_y(), footer_top + 24))
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5, _safe(EMERGENCY_DISCLAIMER), new_x="LMARGIN", new_y="NEXT")


def generate_pdf(case_id, report_dict):
    reports_dir = config.get_reports_dir()
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, f"{case_id}.pdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(f"{HOSPITAL_NAME} - Case Report {case_id}")
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    _header(pdf, case_id, report_dict)
    _section_intake(pdf, report_dict["patient_intake"])
    _section_assessment(pdf, report_dict["ai_preliminary_assessment"])
    _section_prescription(pdf, report_dict["prescription"])
    _footer_block(pdf, case_id)

    pdf.output(path)
    return path
