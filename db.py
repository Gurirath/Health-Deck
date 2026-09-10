"""Local SQLite store for completed triage cases and raw sensor reads.

backend.py exposes these functions over HTTP. The kiosk and the clinician
dashboard call that API rather than importing this module, so a completed
case queued from one kiosk session is visible to a dashboard running in a
different process.

Set HEALTHDECK_DB_PATH to move the file; it defaults to healthdeck.db in the
working directory and is git-ignored.
"""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

DEFAULT_DB_PATH = "healthdeck.db"

_JSON_FIELDS = (
    "vitals",
    "transcript",
    "extracted",
    "red_flags",
    "diagnosis",
    "raw_llm_response",
    "solution_sources",
    "prescription_medicines",
    "image_analysis",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    vitals TEXT NOT NULL,
    chief_complaint TEXT NOT NULL,
    symptom_location TEXT NOT NULL,
    transcript TEXT NOT NULL,
    extracted TEXT NOT NULL,
    red_flags TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    raw_llm_response TEXT NOT NULL DEFAULT '{}',
    solution_sources TEXT NOT NULL DEFAULT '[]',
    image_analysis TEXT NOT NULL DEFAULT 'null',
    session_id TEXT,
    photo_path TEXT,
    confidence INTEGER NOT NULL,
    department TEXT NOT NULL,
    department_override TEXT,
    escalate INTEGER NOT NULL,
    escalation_reason TEXT NOT NULL DEFAULT '',
    reviewed INTEGER NOT NULL DEFAULT 0,
    reviewed_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    doctor_name TEXT,
    prescription_medicines TEXT NOT NULL DEFAULT '[]',
    doctor_notes TEXT,
    prescribed_at TEXT,
    report_pdf_path TEXT
)
"""

_RAW_VITALS_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    device_id TEXT,
    spo2 REAL,
    temp_c REAL,
    hr REAL,
    systolic_bp REAL,
    diastolic_bp REAL,
    timestamp TEXT
)
"""

_SESSION_UPLOADS_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_uploads (
    session_id TEXT PRIMARY KEY,
    image_path TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
)
"""

_ADDED_CASE_COLUMNS = {
    "raw_llm_response": "ALTER TABLE cases ADD COLUMN raw_llm_response TEXT NOT NULL DEFAULT '{}'",
    "escalation_reason": "ALTER TABLE cases ADD COLUMN escalation_reason TEXT NOT NULL DEFAULT ''",
    "solution_sources": "ALTER TABLE cases ADD COLUMN solution_sources TEXT NOT NULL DEFAULT '[]'",
    "image_analysis": "ALTER TABLE cases ADD COLUMN image_analysis TEXT NOT NULL DEFAULT 'null'",
    "session_id": "ALTER TABLE cases ADD COLUMN session_id TEXT",
    "photo_path": "ALTER TABLE cases ADD COLUMN photo_path TEXT",
    "status": "ALTER TABLE cases ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'",
    "doctor_name": "ALTER TABLE cases ADD COLUMN doctor_name TEXT",
    "prescription_medicines": "ALTER TABLE cases ADD COLUMN prescription_medicines TEXT NOT NULL DEFAULT '[]'",
    "doctor_notes": "ALTER TABLE cases ADD COLUMN doctor_notes TEXT",
    "prescribed_at": "ALTER TABLE cases ADD COLUMN prescribed_at TEXT",
    "report_pdf_path": "ALTER TABLE cases ADD COLUMN report_pdf_path TEXT",
}


def _normalize_medicine(item):
    item = item or {}
    remark = item.get("remark")
    if remark in (None, ""):
        remark = item.get("instructions", "")
    return {
        "name": item.get("name", "") or "",
        "dosage_per_day": item.get("dosage_per_day", "") or "",
        "remark": remark or "",
    }


def normalize_medicines(medicines):
    return [_normalize_medicine(item) for item in (medicines or [])]


def _db_path():
    return os.environ.get("HEALTHDECK_DB_PATH", DEFAULT_DB_PATH)


def _connect():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_connect()) as conn:
        conn.execute(_SCHEMA)
        conn.execute(_RAW_VITALS_SCHEMA)
        conn.execute(_SESSION_UPLOADS_SCHEMA)
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(cases)")}
        for column, statement in _ADDED_CASE_COLUMNS.items():
            if column not in existing:
                conn.execute(statement)
        conn.commit()


def save_case(state):
    diagnosis = state.get("diagnosis", {}) or {}
    raw_llm_response = state.get("raw_llm_response") or diagnosis
    session_id = state.get("session_id", "")
    upload = get_session_upload(session_id) if session_id else None
    photo_path = upload["image_path"] if upload else None
    row = (
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        json.dumps(state.get("vitals", {})),
        state.get("chief_complaint", ""),
        state.get("symptom_location", ""),
        json.dumps(state.get("transcript", [])),
        json.dumps(state.get("extracted", {})),
        json.dumps(state.get("red_flags", [])),
        json.dumps(diagnosis),
        json.dumps(raw_llm_response),
        json.dumps(state.get("solution_sources", [])),
        json.dumps(state.get("image_analysis")),
        session_id,
        photo_path,
        int(diagnosis.get("confidence") or 0),
        state.get("department", ""),
        1 if state.get("escalate") else 0,
        state.get("escalation_reason", ""),
    )
    with closing(_connect()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO cases (
                created_at, vitals, chief_complaint, symptom_location,
                transcript, extracted, red_flags, diagnosis, raw_llm_response,
                solution_sources, image_analysis, session_id, photo_path,
                confidence, department, escalate, escalation_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        conn.commit()
        return cursor.lastrowid


def save_raw_vitals(reading):
    row = (
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        reading.get("device_id"),
        reading.get("spo2"),
        reading.get("temp_c"),
        reading.get("hr"),
        reading.get("systolic_bp"),
        reading.get("diastolic_bp"),
        reading.get("timestamp"),
    )
    with closing(_connect()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO raw_vitals (
                received_at, device_id, spo2, temp_c, hr,
                systolic_bp, diastolic_bp, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        conn.commit()
        return cursor.lastrowid


def _row_to_case(row):
    case = dict(row)
    for field in _JSON_FIELDS:
        case[field] = json.loads(case[field])
    case["prescription_medicines"] = normalize_medicines(case.get("prescription_medicines"))
    case["escalate"] = bool(case["escalate"])
    case["reviewed"] = bool(case["reviewed"])
    case["effective_department"] = case["department_override"] or case["department"]
    return case


def list_open_cases():
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM cases WHERE status != 'prescribed' "
            "ORDER BY datetime(created_at) DESC, id DESC"
        ).fetchall()
    return [_row_to_case(r) for r in rows]


def get_case(case_id):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return _row_to_case(row) if row is not None else None


def mark_reviewed(case_id, department_override=None):
    reviewed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE cases SET reviewed = 1, reviewed_at = ?, "
            "department_override = COALESCE(?, department_override) WHERE id = ?",
            (reviewed_at, department_override, case_id),
        )
        conn.commit()


def prescribe_case(case_id, doctor_name, medicines, notes):
    prescribed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    normalized = normalize_medicines(medicines)
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE cases SET status = 'prescribed', doctor_name = ?, "
            "prescription_medicines = ?, doctor_notes = ?, prescribed_at = ? "
            "WHERE id = ?",
            (doctor_name, json.dumps(normalized), notes or "", prescribed_at, case_id),
        )
        conn.commit()

    import report_builder

    case = get_case(case_id)
    pdf_path = report_builder.generate_pdf(case_id, report_builder.build_report(case))
    with closing(_connect()) as conn:
        conn.execute(
            "UPDATE cases SET report_pdf_path = ? WHERE id = ?", (pdf_path, case_id)
        )
        conn.commit()
    return get_case(case_id)


def save_session_upload(session_id, image_path):
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO session_uploads (session_id, image_path, uploaded_at) "
            "VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
            "image_path = excluded.image_path, uploaded_at = excluded.uploaded_at",
            (session_id, image_path, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        conn.commit()


def get_session_upload(session_id):
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM session_uploads WHERE session_id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row is not None else None
