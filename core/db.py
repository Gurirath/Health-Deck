"""Database layer for Health Deck supporting PostgreSQL and SQLite.

Architecture:
- In production (HEALTHDECK_ENV=production): DATABASE_URL (PostgreSQL) is strictly mandatory.
  Silent fallback to SQLite is prohibited and raises an explicit startup error.
- In development/testing: If DATABASE_URL is set, connects to PostgreSQL via connection pool.
  If DATABASE_URL is absent, falls back to local SQLite (healthdeck.db) for developer convenience.
"""

import json
import logging
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("healthdeck.db")

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

# ---------------------------------------------------------------------------
# SQLite Schemas (Development Fallback Only)
# ---------------------------------------------------------------------------
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
    report_pdf_path TEXT,
    reviewed_by_doctor_id INTEGER REFERENCES doctors(id),
    reviewed_by_doctor_name TEXT,
    prescribed_by_doctor_id INTEGER REFERENCES doctors(id)
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

_DOCTORS_SCHEMA = """
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    medical_license TEXT NOT NULL DEFAULT '',
    department TEXT NOT NULL DEFAULT 'General Physician',
    role TEXT NOT NULL DEFAULT 'doctor',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login_at TEXT
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
    "reviewed_by_doctor_id": "ALTER TABLE cases ADD COLUMN reviewed_by_doctor_id INTEGER REFERENCES doctors(id)",
    "reviewed_by_doctor_name": "ALTER TABLE cases ADD COLUMN reviewed_by_doctor_name TEXT",
    "prescribed_by_doctor_id": "ALTER TABLE cases ADD COLUMN prescribed_by_doctor_id INTEGER REFERENCES doctors(id)",
}


# ---------------------------------------------------------------------------
# Environment & Engine Selection
# ---------------------------------------------------------------------------

def is_production() -> bool:
    """Return True if running in production mode."""
    env = os.environ.get("HEALTHDECK_ENV", os.environ.get("ENVIRONMENT", "development")).strip().lower()
    return env in ("production", "prod")


def get_database_url() -> Optional[str]:
    """Return cleaned DATABASE_URL if configured."""
    url = os.environ.get("DATABASE_URL")
    return url.strip() if url and url.strip() else None


def is_postgres() -> bool:
    """Return True if DATABASE_URL is configured for PostgreSQL."""
    url = get_database_url()
    return bool(url and (url.startswith("postgresql://") or url.startswith("postgres://")))


_pg_pool = None


def get_pg_pool():
    """Retrieve or initialize the global psycopg connection pool."""
    global _pg_pool
    if _pg_pool is None:
        url = get_database_url()
        if not url:
            raise RuntimeError("DATABASE_URL is not configured.")
        import psycopg_pool
        from psycopg.rows import dict_row

        try:
            _pg_pool = psycopg_pool.ConnectionPool(
                conninfo=url,
                min_size=int(os.environ.get("HEALTHDECK_DB_POOL_MIN", "1")),
                max_size=int(os.environ.get("HEALTHDECK_DB_POOL_MAX", "10")),
                open=True,
                kwargs={"row_factory": dict_row},
            )
        except Exception as exc:
            if is_production():
                raise RuntimeError(
                    f"FATAL: Failed to connect to PostgreSQL in production mode: {exc}. "
                    "Cannot start or operate Health Deck without an active PostgreSQL database."
                ) from exc
            raise
    return _pg_pool


def close_pg_pool():
    """Close the global connection pool."""
    global _pg_pool
    if _pg_pool is not None:
        try:
            _pg_pool.close()
        except Exception:
            pass
        _pg_pool = None


@contextmanager
def get_pg_connection():
    """Context manager yielding a pooled PostgreSQL connection."""
    pool = get_pg_pool()
    with pool.connection() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Normalization & Row Mapping Helpers
# ---------------------------------------------------------------------------

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


def _row_to_case(row):
    if row is None:
        return None
    case = dict(row)
    for field in _JSON_FIELDS:
        val = case.get(field)
        if isinstance(val, str):
            try:
                case[field] = json.loads(val)
            except Exception:
                pass
        elif val is None and field in (
            "vitals", "transcript", "extracted", "red_flags", "diagnosis",
            "raw_llm_response", "solution_sources", "prescription_medicines"
        ):
            case[field] = [] if field in ("transcript", "red_flags", "solution_sources", "prescription_medicines") else {}

    case["prescription_medicines"] = normalize_medicines(case.get("prescription_medicines"))
    case["escalate"] = bool(case.get("escalate"))
    case["reviewed"] = bool(case.get("reviewed"))
    case["effective_department"] = case.get("department_override") or case.get("department") or "General Physician"

    # Format timestamp objects to ISO strings if needed
    for ts_field in ("created_at", "reviewed_at", "prescribed_at"):
        ts_val = case.get(ts_field)
        if isinstance(ts_val, datetime):
            case[ts_field] = ts_val.isoformat(timespec="seconds")
    return case


def _row_to_doctor(row, include_password_hash=False):
    if row is None:
        return None
    d = dict(row)
    d["is_active"] = bool(d.get("is_active", 1))
    if not include_password_hash:
        d.pop("password_hash", None)
    for ts_field in ("created_at", "last_login_at"):
        ts_val = d.get(ts_field)
        if isinstance(ts_val, datetime):
            d[ts_field] = ts_val.isoformat(timespec="seconds")
    return d


def _db_path():
    return os.environ.get("HEALTHDECK_DB_PATH", DEFAULT_DB_PATH)


def _connect():
    if is_production():
        raise RuntimeError(
            "FATAL: Application is configured in production mode (HEALTHDECK_ENV=production). "
            "SQLite fallback is strictly prohibited in production; PostgreSQL (DATABASE_URL) must be configured."
        )
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Public Database API
# ---------------------------------------------------------------------------

def init_db():
    """Initialize database schema with versioned migrations or SQLite fallback."""
    if is_production() and not is_postgres():
        raise RuntimeError(
            "FATAL: Application is configured in production mode (HEALTHDECK_ENV=production), "
            "but DATABASE_URL is missing or not a valid PostgreSQL connection string. "
            "Silent fallback to SQLite is strictly prohibited in production."
        )

    if is_postgres():
        from core.migrations import apply_migrations
        try:
            with get_pg_connection() as conn:
                apply_migrations(conn)
        except Exception as exc:
            if is_production():
                raise RuntimeError(
                    f"FATAL: Failed to connect to PostgreSQL or apply migrations in production: {exc}. "
                    "Silent fallback to SQLite is strictly prohibited in production."
                ) from exc
            raise
    else:
        with closing(_connect()) as conn:
            conn.execute(_SCHEMA)
            conn.execute(_RAW_VITALS_SCHEMA)
            conn.execute(_SESSION_UPLOADS_SCHEMA)
            conn.execute(_DOCTORS_SCHEMA)
            existing = {r["name"] for r in conn.execute("PRAGMA table_info(cases)")}
            for column, statement in _ADDED_CASE_COLUMNS.items():
                if column not in existing:
                    conn.execute(statement)
            conn.commit()

    seed_admin_doctor_from_env()


def check_health() -> bool:
    """Perform a lightweight health check (SELECT 1) on the active database engine.
    
    Returns True if healthy, False if connection or query fails.
    Never leaks credentials, connection strings, or internal errors.
    """
    try:
        if is_postgres():
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    row = cur.fetchone()
                    return bool(row)
        else:
            with closing(_connect()) as conn:
                row = conn.execute("SELECT 1").fetchone()
                return bool(row)
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


def save_case(state: dict) -> int:
    """Save a newly completed patient triage case."""
    diagnosis = state.get("diagnosis", {}) or {}
    raw_llm_response = state.get("raw_llm_response") or diagnosis
    session_id = state.get("session_id", "") or None
    upload = get_session_upload(session_id) if session_id else None
    photo_path = upload["image_path"] if upload else None
    confidence = int(diagnosis.get("confidence") or 0)
    dept = state.get("department", "")
    escalate = bool(state.get("escalate"))
    esc_reason = state.get("escalation_reason", "")
    valid_session_id = session_id if upload else None

    if is_postgres():
        from psycopg.types.json import Jsonb
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cases (
                        created_at, vitals, chief_complaint, symptom_location,
                        transcript, extracted, red_flags, diagnosis, raw_llm_response,
                        solution_sources, image_analysis, session_id, photo_path,
                        confidence, department, escalate, escalation_reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        datetime.now(timezone.utc),
                        Jsonb(state.get("vitals", {})),
                        state.get("chief_complaint", ""),
                        state.get("symptom_location", ""),
                        Jsonb(state.get("transcript", [])),
                        Jsonb(state.get("extracted", {})),
                        Jsonb(state.get("red_flags", [])),
                        Jsonb(diagnosis),
                        Jsonb(raw_llm_response),
                        Jsonb(state.get("solution_sources", [])),
                        Jsonb(state.get("image_analysis")) if state.get("image_analysis") is not None else None,
                        valid_session_id,
                        photo_path,
                        confidence,
                        dept,
                        escalate,
                        esc_reason,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return row["id"]
    else:
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
            confidence,
            dept,
            1 if escalate else 0,
            esc_reason,
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


def save_raw_vitals(reading: dict) -> int:
    """Ingest hardware sensor readings."""
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO raw_vitals (
                        received_at, device_id, spo2, temp_c, hr,
                        systolic_bp, diastolic_bp, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        datetime.now(timezone.utc),
                        reading.get("device_id"),
                        reading.get("spo2"),
                        reading.get("temp_c"),
                        reading.get("hr"),
                        reading.get("systolic_bp"),
                        reading.get("diastolic_bp"),
                        reading.get("timestamp"),
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return row["id"]
    else:
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


def list_open_cases() -> list:
    """List open cases needing review/prescription."""
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM cases WHERE status != 'prescribed' ORDER BY created_at DESC, id DESC"
                )
                rows = cur.fetchall()
                return [_row_to_case(r) for r in rows]
    else:
        with closing(_connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM cases WHERE status != 'prescribed' "
                "ORDER BY datetime(created_at) DESC, id DESC"
            ).fetchall()
        return [_row_to_case(r) for r in rows]


def list_all_cases() -> list:
    """List all historical and active intake cases."""
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM cases ORDER BY created_at DESC, id DESC")
                rows = cur.fetchall()
                return [_row_to_case(r) for r in rows]
    else:
        with closing(_connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM cases ORDER BY datetime(created_at) DESC, id DESC"
            ).fetchall()
        return [_row_to_case(r) for r in rows]


def get_case(case_id: int):
    """Retrieve full clinical case record by ID."""
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
                row = cur.fetchone()
                return _row_to_case(row)
    else:
        with closing(_connect()) as conn:
            row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        return _row_to_case(row) if row is not None else None


def get_patient_case_status(case_id: int):
    """Retrieve sanitized, patient-safe case status projection."""
    case = get_case(case_id)
    if case is None:
        return None
    return {
        "case_id": case["id"],
        "status": case.get("status", "pending"),
        "reviewed": bool(case.get("reviewed")),
        "reviewed_at": case.get("reviewed_at"),
        "doctor_name": case.get("doctor_name"),
        "prescribed_at": case.get("prescribed_at"),
        "prescription_medicines": case.get("prescription_medicines") or [],
        "has_report": bool(case.get("report_pdf_path")),
        "effective_department": case.get("effective_department") or case.get("department") or "General Physician",
    }


def mark_reviewed(case_id: int, doctor_id=None, doctor_name=None, department_override=None):
    """Mark case reviewed with authenticated doctor attribution."""
    now_dt = datetime.now(timezone.utc)
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE cases SET
                        reviewed = TRUE,
                        reviewed_at = %s,
                        reviewed_by_doctor_id = COALESCE(%s, reviewed_by_doctor_id),
                        reviewed_by_doctor_name = COALESCE(%s, reviewed_by_doctor_name),
                        department_override = COALESCE(%s, department_override)
                    WHERE id = %s
                    """,
                    (now_dt, doctor_id, doctor_name, department_override, case_id),
                )
                conn.commit()
    else:
        reviewed_at_str = now_dt.isoformat(timespec="seconds")
        with closing(_connect()) as conn:
            conn.execute(
                """
                UPDATE cases SET
                    reviewed = 1,
                    reviewed_at = ?,
                    reviewed_by_doctor_id = COALESCE(?, reviewed_by_doctor_id),
                    reviewed_by_doctor_name = COALESCE(?, reviewed_by_doctor_name),
                    department_override = COALESCE(?, department_override)
                WHERE id = ?
                """,
                (reviewed_at_str, doctor_id, doctor_name, department_override, case_id),
            )
            conn.commit()


class CaseAlreadyPrescribedError(Exception):
    """Raised when an attempt is made to prescribe a case that has already been prescribed."""
    pass


def prescribe_case(case_id: int, doctor_name: str, medicines: list, notes: str, doctor_id=None, only_if_unprescribed: bool = False):
    """Prescribe medicines, generate PDF report, and update case status."""
    now_dt = datetime.now(timezone.utc)
    normalized = normalize_medicines(medicines)

    if is_postgres():
        from psycopg.types.json import Jsonb
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                if only_if_unprescribed:
                    cur.execute(
                        """
                        UPDATE cases SET
                            status = 'prescribed',
                            doctor_name = %s,
                            prescribed_by_doctor_id = COALESCE(%s, prescribed_by_doctor_id),
                            prescription_medicines = %s,
                            doctor_notes = %s,
                            prescribed_at = %s
                        WHERE id = %s AND status != 'prescribed'
                        """,
                        (doctor_name, doctor_id, Jsonb(normalized), notes or "", now_dt, case_id),
                    )
                    if cur.rowcount == 0:
                        cur.execute("SELECT status FROM cases WHERE id = %s", (case_id,))
                        existing = cur.fetchone()
                        if existing and existing["status"] == "prescribed":
                            conn.commit()
                            raise CaseAlreadyPrescribedError(f"Case {case_id} has already been prescribed.")
                        conn.commit()
                        return None
                else:
                    cur.execute(
                        """
                        UPDATE cases SET
                            status = 'prescribed',
                            doctor_name = %s,
                            prescribed_by_doctor_id = COALESCE(%s, prescribed_by_doctor_id),
                            prescription_medicines = %s,
                            doctor_notes = %s,
                            prescribed_at = %s
                        WHERE id = %s
                        """,
                        (doctor_name, doctor_id, Jsonb(normalized), notes or "", now_dt, case_id),
                    )
                conn.commit()
    else:
        prescribed_at_str = now_dt.isoformat(timespec="seconds")
        with closing(_connect()) as conn:
            if only_if_unprescribed:
                cursor = conn.execute(
                    """
                    UPDATE cases SET
                        status = 'prescribed',
                        doctor_name = ?,
                        prescribed_by_doctor_id = COALESCE(?, prescribed_by_doctor_id),
                        prescription_medicines = ?,
                        doctor_notes = ?,
                        prescribed_at = ?
                    WHERE id = ? AND status != 'prescribed'
                    """,
                    (doctor_name, doctor_id, json.dumps(normalized), notes or "", prescribed_at_str, case_id),
                )
                if cursor.rowcount == 0:
                    existing = conn.execute("SELECT status FROM cases WHERE id = ?", (case_id,)).fetchone()
                    if existing and existing["status"] == "prescribed":
                        conn.commit()
                        raise CaseAlreadyPrescribedError(f"Case {case_id} has already been prescribed.")
                    conn.commit()
                    return None
            else:
                conn.execute(
                    """
                    UPDATE cases SET
                        status = 'prescribed',
                        doctor_name = ?,
                        prescribed_by_doctor_id = COALESCE(?, prescribed_by_doctor_id),
                        prescription_medicines = ?,
                        doctor_notes = ?,
                        prescribed_at = ?
                    WHERE id = ?
                    """,
                    (doctor_name, doctor_id, json.dumps(normalized), notes or "", prescribed_at_str, case_id),
                )
            conn.commit()

    from core import report_builder
    case = get_case(case_id)
    if not case:
        return None
    pdf_path = report_builder.generate_pdf(case_id, report_builder.build_report(case))

    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE cases SET report_pdf_path = %s WHERE id = %s", (pdf_path, case_id))
                conn.commit()
    else:
        with closing(_connect()) as conn:
            conn.execute("UPDATE cases SET report_pdf_path = ? WHERE id = ?", (pdf_path, case_id))
            conn.commit()

    return get_case(case_id)


def create_doctor(
    username: str,
    email: str,
    password_hash: str,
    full_name: str,
    medical_license: str = "",
    department: str = "General Physician",
    role: str = "doctor",
    is_active: int = 1,
) -> int:
    """Provision a new doctor account."""
    now_dt = datetime.now(timezone.utc)
    clean_user = username.strip().lower()
    clean_email = email.strip().lower()

    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO doctors (
                        username, email, password_hash, full_name,
                        medical_license, department, role, is_active, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        clean_user,
                        clean_email,
                        password_hash,
                        full_name.strip(),
                        medical_license.strip(),
                        department.strip(),
                        role.strip(),
                        bool(is_active),
                        now_dt,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return row["id"]
    else:
        created_at_str = now_dt.isoformat(timespec="seconds")
        with closing(_connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO doctors (
                    username, email, password_hash, full_name,
                    medical_license, department, role, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_user,
                    clean_email,
                    password_hash,
                    full_name.strip(),
                    medical_license.strip(),
                    department.strip(),
                    role.strip(),
                    1 if is_active else 0,
                    created_at_str,
                ),
            )
            conn.commit()
            return cursor.lastrowid


def get_doctor_by_id(doctor_id: int, include_password_hash: bool = False):
    """Retrieve doctor profile by ID."""
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
                row = cur.fetchone()
                return _row_to_doctor(row, include_password_hash=include_password_hash)
    else:
        with closing(_connect()) as conn:
            row = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
        return _row_to_doctor(row, include_password_hash=include_password_hash)


def get_doctor_by_username_or_email(identifier: str, include_password_hash: bool = False):
    """Retrieve doctor profile by username or email with dot/space normalization."""
    clean = identifier.strip().lower()
    alt_clean = clean.replace(" ", ".") if " " in clean else clean.replace(".", " ")

    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM doctors
                    WHERE LOWER(username) = %s
                       OR LOWER(email) = %s
                       OR LOWER(username) = %s
                       OR LOWER(email) = %s
                    """,
                    (clean, clean, alt_clean, alt_clean),
                )
                row = cur.fetchone()
                return _row_to_doctor(row, include_password_hash=include_password_hash)
    else:
        with closing(_connect()) as conn:
            row = conn.execute(
                """
                SELECT * FROM doctors 
                WHERE LOWER(username) = ? 
                   OR LOWER(email) = ? 
                   OR LOWER(username) = ? 
                   OR LOWER(email) = ?
                """,
                (clean, clean, alt_clean, alt_clean),
            ).fetchone()
        return _row_to_doctor(row, include_password_hash=include_password_hash)


def update_doctor_last_login(doctor_id: int):
    """Update last login timestamp for doctor."""
    now_dt = datetime.now(timezone.utc)
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE doctors SET last_login_at = %s WHERE id = %s", (now_dt, doctor_id))
                conn.commit()
    else:
        now_str = now_dt.isoformat(timespec="seconds")
        with closing(_connect()) as conn:
            conn.execute("UPDATE doctors SET last_login_at = ? WHERE id = ?", (now_str, doctor_id))
            conn.commit()


def update_doctor_password(identifier: str, password_hash: str) -> bool:
    """Update doctor password hash."""
    clean = identifier.strip().lower()
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE doctors SET password_hash = %s WHERE LOWER(username) = %s OR LOWER(email) = %s",
                    (password_hash, clean, clean),
                )
                conn.commit()
                return cur.rowcount > 0
    else:
        with closing(_connect()) as conn:
            cursor = conn.execute(
                "UPDATE doctors SET password_hash = ? WHERE LOWER(username) = ? OR LOWER(email) = ?",
                (password_hash, clean, clean),
            )
            conn.commit()
            return cursor.rowcount > 0


def list_doctors(include_password_hash: bool = False) -> list:
    """List all registered doctors."""
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM doctors ORDER BY id ASC")
                rows = cur.fetchall()
                return [_row_to_doctor(r, include_password_hash=include_password_hash) for r in rows]
    else:
        with closing(_connect()) as conn:
            rows = conn.execute("SELECT * FROM doctors ORDER BY id ASC").fetchall()
        return [_row_to_doctor(r, include_password_hash=include_password_hash) for r in rows]


def create_or_update_doctor(
    username: str,
    email: str,
    password_hash: str,
    full_name: str,
    medical_license: str = "",
    department: str = "General Physician",
    role: str = "doctor",
    is_active: int = 1,
) -> tuple[int, bool]:
    """Create or update a doctor account."""
    clean_username = username.strip().lower()
    clean_email = email.strip().lower()
    existing = get_doctor_by_username_or_email(clean_username, include_password_hash=True)
    if not existing:
        existing = get_doctor_by_username_or_email(clean_email, include_password_hash=True)

    if existing:
        if is_postgres():
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE doctors SET
                            username = %s,
                            email = %s,
                            password_hash = %s,
                            full_name = %s,
                            medical_license = %s,
                            department = %s,
                            role = %s,
                            is_active = %s
                        WHERE id = %s
                        """,
                        (
                            clean_username,
                            clean_email,
                            password_hash,
                            full_name.strip(),
                            medical_license.strip(),
                            department.strip(),
                            role.strip(),
                            bool(is_active),
                            existing["id"],
                        ),
                    )
                    conn.commit()
                    return existing["id"], False
        else:
            with closing(_connect()) as conn:
                conn.execute(
                    """
                    UPDATE doctors SET
                        username = ?,
                        email = ?,
                        password_hash = ?,
                        full_name = ?,
                        medical_license = ?,
                        department = ?,
                        role = ?,
                        is_active = ?
                    WHERE id = ?
                    """,
                    (
                        clean_username,
                        clean_email,
                        password_hash,
                        full_name.strip(),
                        medical_license.strip(),
                        department.strip(),
                        role.strip(),
                        1 if is_active else 0,
                        existing["id"],
                    ),
                )
                conn.commit()
                return existing["id"], False
    else:
        new_id = create_doctor(
            username=clean_username,
            email=clean_email,
            password_hash=password_hash,
            full_name=full_name,
            medical_license=medical_license,
            department=department,
            role=role,
            is_active=is_active,
        )
        return new_id, True


def seed_admin_doctor_from_env():
    """Seed initial doctor from environment variables if present."""
    username = os.environ.get("HEALTHDECK_ADMIN_USERNAME")
    password = os.environ.get("HEALTHDECK_ADMIN_PASSWORD")
    if not username or not password:
        return None

    username = username.strip().lower()
    existing = get_doctor_by_username_or_email(username)
    if existing:
        return existing

    email = os.environ.get("HEALTHDECK_ADMIN_EMAIL", f"{username}@hospital.internal").strip().lower()
    existing_email = get_doctor_by_username_or_email(email)
    if existing_email:
        return existing_email

    full_name = os.environ.get("HEALTHDECK_ADMIN_NAME", "Attending Physician").strip()
    license_num = os.environ.get("HEALTHDECK_ADMIN_LICENSE", "MD-DEFAULT").strip()
    dept = os.environ.get("HEALTHDECK_ADMIN_DEPARTMENT", "General Physician").strip()

    from core.auth import hash_password
    pw_hash = hash_password(password)

    doctor_id = create_doctor(
        username=username,
        email=email,
        password_hash=pw_hash,
        full_name=full_name,
        medical_license=license_num,
        department=dept,
        role="doctor",
        is_active=1,
    )
    return get_doctor_by_id(doctor_id)


def save_session_upload(session_id: str, image_path: str):
    """Store or update session photo upload reference."""
    now_dt = datetime.now(timezone.utc)
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO session_uploads (session_id, image_path, uploaded_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(session_id) DO UPDATE SET
                        image_path = EXCLUDED.image_path,
                        uploaded_at = EXCLUDED.uploaded_at
                    """,
                    (session_id, image_path, now_dt),
                )
                conn.commit()
    else:
        with closing(_connect()) as conn:
            conn.execute(
                "INSERT INTO session_uploads (session_id, image_path, uploaded_at) "
                "VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
                "image_path = excluded.image_path, uploaded_at = excluded.uploaded_at",
                (session_id, image_path, now_dt.isoformat(timespec="seconds")),
            )
            conn.commit()


def get_session_upload(session_id: str):
    """Retrieve session upload metadata."""
    if is_postgres():
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM session_uploads WHERE session_id = %s", (session_id,))
                row = cur.fetchone()
                if row:
                    d = dict(row)
                    if isinstance(d.get("uploaded_at"), datetime):
                        d["uploaded_at"] = d["uploaded_at"].isoformat(timespec="seconds")
                    return d
                return None
    else:
        with closing(_connect()) as conn:
            row = conn.execute(
                "SELECT * FROM session_uploads WHERE session_id = ?", (session_id,)
            ).fetchone()
        return dict(row) if row is not None else None
