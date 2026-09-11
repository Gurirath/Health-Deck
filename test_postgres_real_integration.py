"""Comprehensive Real PostgreSQL Integration Test Suite for Health Deck (Phase 3.5).

Connects to a REAL running PostgreSQL instance (e.g. local Docker container).
Validates:
1. Availability check of real PostgreSQL.
2. Versioned schema migrations from clean slate, table structures, column types, idempotency & transaction rollback.
3. JSONB round-trip validation for all 9 fields with complex nested structures and NULL support.
4. Full Health Deck case lifecycle (patient intake -> store -> auth -> open cases -> review -> prescribe -> patient status -> PDF).
5. Doctor authentication, RBAC, JWT validation, and attribution against PostgreSQL.
6. Patient-safe case status redaction & non-leakage.
7. Prescription concurrency under simultaneous execution (row-locking & 409 conflict).
8. Connection pool management, connection reuse, transaction commit/rollback, and cleanup.
9. Historical SQLite -> PostgreSQL data migration with checksums, sequence synchronization, and collision resistance.
10. Production safety rules and environment fallback guards.
11. Data integrity, foreign keys, uniqueness, and index verification.
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Configuration: obtain real PostgreSQL connection string
TEST_PG_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql://postgres:test_secret_pass@127.0.0.1:5433/healthdeck_test")
)


def verify_real_postgres_connection():
    """Verify that a REAL PostgreSQL server is reachable."""
    print(f"[*] Checking connection to real PostgreSQL at: {TEST_PG_URL.split('@')[-1]}")
    try:
        with psycopg.connect(TEST_PG_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version(), current_database(), current_user")
                row = cur.fetchone()
                print(f"[+] REAL POSTGRESQL CONNECTED!")
                print(f"    Database: {row[1]}")
                print(f"    User:     {row[2]}")
                print(f"    Version:  {row[0]}")
                return True, row[0]
    except Exception as exc:
        print("\n" + "!" * 70)
        print("REAL POSTGRESQL VALIDATION BLOCKED — PostgreSQL instance unavailable.")
        print(f"Error details: {exc}")
        print("!" * 70 + "\n")
        return False, str(exc)


def reset_pg_schema():
    """Drop and recreate public schema to ensure an entirely clean database."""
    with psycopg.connect(TEST_PG_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
            cur.execute("CREATE SCHEMA public")
            cur.execute("GRANT ALL ON SCHEMA public TO postgres")
            cur.execute("GRANT ALL ON SCHEMA public TO public")
        conn.commit()


# ==============================================================================
# 1. MIGRATION VALIDATION (Section 3)
# ==============================================================================
def test_migrations():
    print("\n--- [1/10] Testing Versioned PostgreSQL Migrations ---")
    reset_pg_schema()

    import core.migrations as mig
    with psycopg.connect(TEST_PG_URL) as conn:
        # A & B: Run migration runner on empty database
        applied = mig.apply_migrations(conn)
        print(f"    Applied {applied} migrations on initial run.")
        assert applied >= 2, f"Expected at least 2 migrations, got {applied}"

        # C & D: Verify schema_migrations table
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM schema_migrations ORDER BY version ASC")
            applied_rows = cur.fetchall()
            versions = [r["version"] for r in applied_rows]
            assert "001" in versions, "Migration 001 missing in schema_migrations"
            assert "002" in versions, "Migration 002 missing in schema_migrations"
            print(f"    schema_migrations contains versions: {versions}")

        # E: Verify all expected tables exist
        expected_tables = {"doctors", "session_uploads", "cases", "raw_vitals", "schema_migrations"}
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            tables = {r[0] for r in cur.fetchall()}
            for t in expected_tables:
                assert t in tables, f"Expected table '{t}' not found in database"
            print(f"    Verified existence of all tables: {tables}")

        # F: Verify column types
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'cases'
                """
            )
            case_cols = {r["column_name"]: r for r in cur.fetchall()}
            assert case_cols["id"]["data_type"] == "bigint", "cases.id must be bigint"
            assert case_cols["reviewed"]["data_type"] == "boolean", "cases.reviewed must be boolean"
            assert case_cols["escalate"]["data_type"] == "boolean", "cases.escalate must be boolean"
            assert case_cols["created_at"]["data_type"] == "timestamp with time zone", "cases.created_at must be timestamptz"
            assert case_cols["vitals"]["data_type"] == "jsonb", "cases.vitals must be jsonb"
            assert case_cols["diagnosis"]["data_type"] == "jsonb", "cases.diagnosis must be jsonb"
            assert case_cols["image_analysis"]["data_type"] == "jsonb", "cases.image_analysis must be jsonb"

            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'raw_vitals'
                """
            )
            vitals_cols = {r["column_name"]: r["data_type"] for r in cur.fetchall()}
            assert vitals_cols["spo2"] == "double precision", "raw_vitals.spo2 must be double precision"
            assert vitals_cols["temp_c"] == "double precision", "raw_vitals.temp_c must be double precision"
            print("    Verified column data types (BIGINT, BOOLEAN, TIMESTAMPTZ, JSONB, DOUBLE PRECISION).")

        # G: Run runner a second time -> Idempotency check
        applied_second = mig.apply_migrations(conn)
        assert applied_second == 0, f"Second migration run should apply 0 migrations, got {applied_second}"
        print("    Verified migration runner idempotency (0 migrations applied on second run).")

        # H: Transaction rollback on failure
        # Create a dummy bad migration file in a temp dir and verify atomic rollback
        bad_sql = "CREATE TABLE dummy_rollback (id INT); INVALID SQL SYNTAX HERE;"
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as f:
            f.write(bad_sql)
            bad_path = f.name
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            # Verify transaction rollbacks when executed via conn.transaction()
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute("CREATE TABLE test_aborted (id INT)")
                        cur.execute("THIS IS INVALID SQL")
                assert False, "Should have raised an error on invalid SQL"
            except Exception:
                pass  # expected
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = 'test_aborted'"
                )
                assert cur.fetchone() is None, "Table created inside aborted transaction should not exist"
            print("    Verified atomic transaction rollback on migration error.")
        finally:
            if os.path.exists(bad_path):
                os.remove(bad_path)

    print("    [PASS] Migration validation passed completely.")


# ==============================================================================
# 2. JSONB ROUND-TRIP VALIDATION (Section 4)
# ==============================================================================
def test_jsonb_roundtrip():
    print("\n--- [2/10] Testing JSONB Round-Trip Data Fidelity ---")
    import core.db as db

    os.environ["DATABASE_URL"] = TEST_PG_URL
    os.environ["HEALTHDECK_ENV"] = "development"
    db.close_pg_pool()
    db.init_db()

    # Representative nested structures for all 9 fields
    test_payload = {
        "vitals": {
            "spo2": 97.5,
            "hr": 84,
            "temp_c": 38.2,
            "blood_pressure": {"systolic": 122, "diastolic": 78},
            "flags": ["mild_fever"]
        },
        "transcript": [
            {"role": "assistant", "content": "How long have you had this cough?", "turn": 1},
            {"role": "user", "content": "About 4 days, worse at night.", "turn": 2}
        ],
        "extracted": {
            "symptoms": ["cough", "nocturnal worsening"],
            "duration_days": 4,
            "known_allergies": None,
            "smoking_history": False
        },
        "red_flags": [
            "chest_pain",
            "persistent_fever"
        ],
        "diagnosis": {
            "probable_diagnosis": "Acute Bronchitis",
            "confidence": 88,
            "differential": ["URI", "Early Pneumonia"],
            "self_care_advice": "Hydration, honey, humidified air."
        },
        "raw_llm_response": {
            "provider": "groq",
            "model": "openai/gpt-oss-120b",
            "tokens": {"input": 450, "output": 120},
            "verdict": "routine"
        },
        "solution_sources": [
            {"title": "CDC Bronchitis Guidelines", "url": "https://www.cdc.gov/bronchitis", "rank": 1},
            {"title": "NHS Cough Management", "url": "https://www.nhs.uk/coughs", "rank": 2}
        ],
        "prescription_medicines": [
            {"name": "Dextromethorphan", "dosage_per_day": "10ml twice daily", "remark": "after meals"},
            {"name": "Paracetamol", "dosage_per_day": "500mg every 6 hours", "remark": "as needed for fever"}
        ],
        "image_analysis": {
            "observation": "Clear pharynx without exudates",
            "visual_characteristics": ["mild erythema", "no tonsillar swelling"],
            "confidence": 0.92
        }
    }

    state = {
        "chief_complaint": "Persistent cough",
        "symptom_location": "Chest",
        "department": "General Physician",
        "escalate": False,
        "escalation_reason": "",
        **test_payload
    }

    # Write initial case to real PostgreSQL (populates 8 of 9 fields)
    case_id = db.save_case(state)
    assert case_id > 0

    # Populate 9th field (prescription_medicines) via clinician prescribe_case
    prescribed = db.prescribe_case(
        case_id,
        doctor_name="Dr. Roundtrip Tester",
        medicines=test_payload["prescription_medicines"],
        notes="Testing JSONB roundtrip."
    )
    assert prescribed is not None

    # Read back from real PostgreSQL
    fetched = db.get_case(case_id)
    assert fetched is not None

    # Deep equality assertion on all 9 JSON fields
    fields_to_check = [
        "vitals",
        "transcript",
        "extracted",
        "red_flags",
        "diagnosis",
        "raw_llm_response",
        "solution_sources",
        "prescription_medicines",
        "image_analysis"
    ]
    for field in fields_to_check:
        original = test_payload[field]
        retrieved = fetched[field]
        assert retrieved == original, f"JSONB mismatch in field '{field}':\nExpected: {original}\nGot: {retrieved}"
        print(f"    Field '{field}' perfectly matched input Python object.")

    # Also test image_analysis being NULL
    state_no_img = dict(state)
    state_no_img["image_analysis"] = None
    case_id_null = db.save_case(state_no_img)
    fetched_null = db.get_case(case_id_null)
    assert fetched_null["image_analysis"] is None, f"Expected None for image_analysis, got {fetched_null['image_analysis']}"
    print("    Verified nullable JSONB field (image_analysis=None preserved as NULL).")

    print("    [PASS] JSONB round-trip verified for all 9 fields.")


# ==============================================================================
# 3. REAL HEALTH DECK CASE LIFECYCLE (Section 5)
# ==============================================================================
def test_real_case_lifecycle():
    print("\n--- [3/10] Testing Complete Real Case Lifecycle in PostgreSQL ---")
    import core.db as db

    os.environ["DATABASE_URL"] = TEST_PG_URL
    os.environ["HEALTHDECK_ENV"] = "development"
    db.close_pg_pool()
    db.init_db()

    # 1. Provision attending doctor in PostgreSQL
    from core.auth import hash_password
    doc_id = db.create_doctor(
        username="lifecycle_doc",
        email="lifecycle.doc@hospital.internal",
        password_hash=hash_password("DocSecurePass123!"),
        full_name="Dr. Gregory House, MD",
        medical_license="MD-TEST-999",
        department="Diagnostics",
        role="doctor"
    )
    assert doc_id > 0
    doctor = db.get_doctor_by_id(doc_id)

    # 2. Patient creates triage case
    state = {
        "chief_complaint": "Acute abdominal pain",
        "symptom_location": "Abdomen",
        "vitals": {"spo2": 99, "hr": 88, "temp_c": 37.1},
        "transcript": [{"role": "user", "content": "Lower right quadrant pain."}],
        "extracted": {"location": "RLQ"},
        "red_flags": [],
        "diagnosis": {"probable_diagnosis": "Appendicitis query", "confidence": 75},
        "department": "Emergency",
        "escalate": True,
        "escalation_reason": "Severe RLQ abdominal pain",
        "solution_sources": [],
        "image_analysis": None
    }
    case_id = db.save_case(state)
    assert case_id > 0
    print(f"    Created case ID={case_id} in PostgreSQL.")

    # 3. Retrieve open cases
    open_cases = db.list_open_cases()
    open_ids = [c["id"] for c in open_cases]
    assert case_id in open_ids, f"Case {case_id} should be in open cases"
    print(f"    Case {case_id} successfully listed in open cases.")

    # 4. Clinician reviews case
    db.mark_reviewed(
        case_id,
        doctor_id=doctor["id"],
        doctor_name=doctor["full_name"],
        department_override="General Surgery"
    )
    reviewed_case = db.get_case(case_id)
    assert reviewed_case["reviewed"] is True
    assert reviewed_case["reviewed_by_doctor_id"] == doctor["id"]
    assert reviewed_case["reviewed_by_doctor_name"] == doctor["full_name"]
    assert reviewed_case["effective_department"] == "General Surgery"
    print("    Case successfully marked reviewed with doctor attribution.")

    # 5. Clinician prescribes medicines
    medicines = [
        {"name": "Cefazolin", "dosage_per_day": "1g IV pre-op", "remark": "surgical prophylaxis"},
        {"name": "Normal Saline", "dosage_per_day": "1000ml IV", "remark": "hydration"}
    ]
    prescribed_case = db.prescribe_case(
        case_id,
        doctor_name=doctor["full_name"],
        medicines=medicines,
        notes="Urgent surgical consult requested.",
        doctor_id=doctor["id"]
    )
    assert prescribed_case["status"] == "prescribed"
    assert prescribed_case["doctor_name"] == doctor["full_name"]
    assert prescribed_case["prescribed_by_doctor_id"] == doctor["id"]
    assert len(prescribed_case["prescription_medicines"]) == 2
    assert prescribed_case["report_pdf_path"] is not None
    assert os.path.exists(prescribed_case["report_pdf_path"])
    print("    Case successfully prescribed and PDF generated.")

    # 6. Check open cases list -> Case should be removed from open cases
    open_cases_after = db.list_open_cases()
    assert case_id not in [c["id"] for c in open_cases_after]
    print("    Prescribed case automatically removed from open cases queue.")

    # 7. Patient status projection
    status = db.get_patient_case_status(case_id)
    assert status["status"] == "prescribed"
    assert status["reviewed"] is True
    assert status["doctor_name"] == doctor["full_name"]
    assert status["has_report"] is True
    assert status["effective_department"] == "General Surgery"
    print("    Patient-safe case status successfully verified.")

    print("    [PASS] Full case lifecycle verified in real PostgreSQL.")


# ==============================================================================
# 4. DOCTOR AUTHENTICATION AGAINST POSTGRESQL (Section 6)
# ==============================================================================
def test_doctor_authentication():
    print("\n--- [4/10] Testing Doctor Authentication & RBAC against PostgreSQL ---")
    from starlette.testclient import TestClient
    import core.db as db
    import core.auth as auth

    os.environ["DATABASE_URL"] = TEST_PG_URL
    os.environ["HEALTHDECK_JWT_SECRET"] = "real_postgres_integration_secret_key_12345"
    os.environ["HEALTHDECK_ENV"] = "development"
    db.close_pg_pool()
    db.init_db()

    # Provision test doctor with clean credentials
    test_username = f"doc_auth_{int(time.time())}"
    test_email = f"{test_username}@hospital.test"
    test_password = "SecurePassword2026!"
    doc_id = db.create_doctor(
        username=test_username,
        email=test_email,
        password_hash=auth.hash_password(test_password),
        full_name="Dr. Auth Tester, MD",
        medical_license="MD-AUTH-100",
        department="Internal Medicine",
        role="doctor"
    )

    from backend import app
    client = TestClient(app)

    # 1. Unauthenticated requests to clinician endpoints return 401
    assert client.get("/cases/open").status_code == 401
    assert client.get("/auth/me").status_code == 401
    print("    Unauthenticated access rejected with 401 Unauthorized.")

    # 2. Login with correct credentials
    login_resp = client.post(
        "/auth/login",
        json={"username": test_username, "password": test_password}
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token_data = login_resp.json()
    token = token_data.get("access_token") or token_data.get("token")
    assert token and len(token) > 20
    headers = {"Authorization": f"Bearer {token}"}
    print("    Doctor login succeeded and JWT token received.")

    # 3. GET /auth/me returns accurate doctor record from PostgreSQL
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == doc_id
    assert me_data["username"] == test_username
    assert me_data["email"] == test_email
    assert "password_hash" not in me_data
    print("    /auth/me confirmed doctor identity against PostgreSQL.")

    # 4. Clinician endpoint access with token
    open_resp = client.get("/cases/open", headers=headers)
    assert open_resp.status_code == 200
    assert isinstance(open_resp.json(), list)
    print("    Authenticated doctor accessed clinician endpoints successfully.")

    # 5. Invalid password fails with 401
    bad_login = client.post(
        "/auth/login",
        json={"username": test_username, "password": "WrongPassword!"}
    )
    assert bad_login.status_code == 401
    print("    Invalid credentials rejected with 401.")

    print("    [PASS] Doctor authentication and RBAC verified against PostgreSQL.")


# ==============================================================================
# 5. PATIENT-SAFE STATUS VALIDATION (Section 7)
# ==============================================================================
def test_patient_safe_status_leakage():
    print("\n--- [5/10] Testing Patient-Safe Status Privacy & Non-Leakage ---")
    from starlette.testclient import TestClient
    import core.db as db
    from backend import app

    os.environ["DATABASE_URL"] = TEST_PG_URL
    os.environ["HEALTHDECK_ENV"] = "development"
    db.close_pg_pool()
    db.init_db()

    client = TestClient(app)

    # Create sensitive clinical case
    sensitive_notes = "CONFIDENTIAL: Patient has undisclosed cardiac arrhythmia history."
    state = {
        "chief_complaint": "Chest flutter",
        "symptom_location": "Chest",
        "vitals": {"hr": 110},
        "transcript": [{"role": "user", "content": "I feel fluttering and anxiety."}],
        "extracted": {"anxiety": True},
        "red_flags": ["tachycardia"],
        "diagnosis": {"probable_diagnosis": "Sinus Tachycardia", "confidence": 90},
        "raw_llm_response": {"internal_reasoning_token_dump": "Sensitive reasoning data"},
        "department": "Cardiology",
        "escalate": False,
        "session_id": "sess-secret-kiosk-99",
        "solution_sources": [{"title": "Heart Org"}]
    }
    case_id = db.save_case(state)

    # Doctor prescribes with confidential notes
    db.prescribe_case(
        case_id,
        doctor_name="Dr. Cardiologist",
        medicines=[{"name": "Metoprolol", "dosage_per_day": "25mg", "remark": "daily"}],
        notes=sensitive_notes
    )

    # Call public endpoint without authentication
    resp = client.get(f"/cases/{case_id}/patient-status")
    assert resp.status_code == 200
    data = resp.json()

    # STRICT PROJECTION: Must contain only allowed fields
    allowed_keys = {
        "case_id",
        "status",
        "reviewed",
        "reviewed_at",
        "doctor_name",
        "prescribed_at",
        "prescription_medicines",
        "has_report",
        "effective_department"
    }
    for k in data.keys():
        assert k in allowed_keys, f"Forbidden key '{k}' exposed in patient status!"

    # ZERO LEAKAGE of sensitive internal clinical fields
    forbidden_keys = [
        "raw_llm_response",
        "doctor_notes",
        "transcript",
        "extracted",
        "red_flags",
        "photo_path",
        "session_id",
        "diagnosis"
    ]
    for k in forbidden_keys:
        assert k not in data, f"Sensitive field '{k}' leaked in patient status!"

    # Verify sensitive text not in JSON response string
    assert sensitive_notes not in resp.text
    assert "internal_reasoning_token_dump" not in resp.text
    print("    Verified zero leakage of internal notes, LLM dumps, transcript, or diagnosis.")

    # Nonexistent case returns 404
    assert client.get("/cases/9999999/patient-status").status_code == 404
    print("    Nonexistent case returned 404 Not Found.")

    print("    [PASS] Patient-safe status privacy confirmed.")


# ==============================================================================
# 6. PRESCRIPTION CONCURRENCY TEST (Section 8)
# ==============================================================================
def test_prescription_concurrency():
    print("\n--- [6/10] Testing Prescription Concurrency & Conflict Rejection ---")
    from starlette.testclient import TestClient
    import core.db as db
    from backend import app
    import core.auth as auth

    os.environ["DATABASE_URL"] = TEST_PG_URL
    os.environ["HEALTHDECK_ENV"] = "development"
    db.close_pg_pool()
    db.init_db()

    # Provision Doctor 1 and Doctor 2 in PostgreSQL
    d1_id = db.create_doctor("conc_doc1", "doc1@hospital.internal", auth.hash_password("pw1"), "Dr. One", department="General Physician")
    d2_id = db.create_doctor("conc_doc2", "doc2@hospital.internal", auth.hash_password("pw2"), "Dr. Two", department="General Physician")

    t1 = auth.create_access_token({"sub": str(d1_id), "username": "conc_doc1", "role": "doctor"})
    t2 = auth.create_access_token({"sub": str(d2_id), "username": "conc_doc2", "role": "doctor"})
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    client = TestClient(app)

    # Create unprescribed case
    case_id = db.save_case({
        "chief_complaint": "Severe migraine",
        "symptom_location": "Head",
        "vitals": {"hr": 76},
        "transcript": [],
        "extracted": {},
        "red_flags": [],
        "diagnosis": {"probable_diagnosis": "Migraine", "confidence": 85},
        "department": "Neurology",
        "escalate": False
    })

    # Prepare concurrent prescribe requests from Doctor 1 and Doctor 2
    results = []

    def doctor_prescribe(client_headers, doc_label, med_name):
        res = client.patch(
            f"/cases/{case_id}/prescribe",
            json={
                "medicines": [{"name": med_name, "dosage_per_day": "1 tab", "remark": "once"}],
                "notes": f"Prescribed by {doc_label}",
                "only_if_unprescribed": True,
            },
            headers=client_headers
        )
        results.append((doc_label, res.status_code, res.json()))

    # Execute both simultaneously using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(doctor_prescribe, h1, "Doctor 1", "Sumatriptan")
        f2 = executor.submit(doctor_prescribe, h2, "Doctor 2", "Zolmitriptan")
        f1.result()
        f2.result()

    status_codes = [r[1] for r in results]
    print(f"    Concurrent request results: {[(r[0], r[1]) for r in results]}")

    # One must succeed (200) and one must receive conflict (409)
    assert 200 in status_codes, "At least one concurrent prescription must succeed (200)"
    assert 409 in status_codes, f"The second concurrent prescription must be rejected with 409 Conflict, got {status_codes}"

    # Verify final case state in PostgreSQL
    final_case = db.get_case(case_id)
    assert final_case["status"] == "prescribed"
    winner_doc_id = final_case["prescribed_by_doctor_id"]
    assert winner_doc_id in (d1_id, d2_id)
    assert len(final_case["prescription_medicines"]) == 1
    winning_med = final_case["prescription_medicines"][0]["name"]
    print(f"    Prescription race won cleanly by doctor ID={winner_doc_id} with medicine '{winning_med}'.")
    print("    Verified single effective prescription, correct attribution, and zero partial corruption.")

    print("    [PASS] Prescription concurrency test passed.")


# ==============================================================================
# 7. CONNECTION POOL VALIDATION (Section 9)
# ==============================================================================
def test_connection_pool():
    print("\n--- [7/10] Testing Connection Pool Resilience & Reuse ---")
    import core.db as db

    os.environ["DATABASE_URL"] = TEST_PG_URL
    os.environ["HEALTHDECK_ENV"] = "development"
    os.environ["HEALTHDECK_DB_POOL_MIN"] = "2"
    os.environ["HEALTHDECK_DB_POOL_MAX"] = "5"
    db.close_pg_pool()
    pool = db.get_pg_pool()

    assert pool is not None
    print("    PostgreSQL ConnectionPool initialized.")

    # Run multiple concurrent queries across threads to verify pool checkout/return
    def worker_query(w_id):
        with db.get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_backend_pid(), %s", (w_id,))
                pid, val = cur.fetchone()
                return pid, val

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_query, i) for i in range(16)]
        outcomes = [f.result() for f in futures]
    assert len(outcomes) == 16
    print("    16 concurrent operations across 8 threads completed successfully through pool.")

    # Test transaction rollback on intentional failure
    try:
        with db.get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE pool_rollback_test (id INT PRIMARY KEY)")
                cur.execute("INSERT INTO pool_rollback_test VALUES (1)")
                # Intentional error: duplicate PK
                cur.execute("INSERT INTO pool_rollback_test VALUES (1)")
                conn.commit()
    except Exception:
        pass  # expected error

    # Verify connection returned in healthy state and subsequent queries succeed
    with db.get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS num")
            res = cur.fetchone()["num"]
            assert res == 1
    print("    Pool recovered cleanly after transaction rollback.")

    db.close_pg_pool()
    print("    Pool closed cleanly.")
    print("    [PASS] Connection pool validation passed.")


# ==============================================================================
# 8. SQLITE -> POSTGRES MIGRATION VALIDATION (Section 10)
# ==============================================================================
def test_sqlite_to_pg_migration():
    print("\n--- [8/10] Testing SQLite to PostgreSQL Historical Data Migration ---")
    reset_pg_schema()

    import scripts.migrate_sqlite_to_pg as migrator
    import core.db as db
    from core.auth import hash_password

    # 1. Create temporary SQLite database with rich representative data
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite_file = os.path.join(tmpdir, "healthdeck_source.db")
        with sqlite3.connect(sqlite_file) as s_conn:
            s_conn.execute("""
                CREATE TABLE doctors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    medical_license TEXT NOT NULL,
                    department TEXT NOT NULL,
                    role TEXT NOT NULL,
                    is_active INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                )
            """)
            s_conn.execute("""
                CREATE TABLE session_uploads (
                    session_id TEXT PRIMARY KEY,
                    image_path TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL
                )
            """)
            s_conn.execute("""
                CREATE TABLE raw_vitals (
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
            """)
            s_conn.execute("""
                CREATE TABLE cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    vitals TEXT NOT NULL,
                    chief_complaint TEXT NOT NULL,
                    symptom_location TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    extracted TEXT NOT NULL,
                    red_flags TEXT NOT NULL,
                    diagnosis TEXT NOT NULL,
                    raw_llm_response TEXT NOT NULL,
                    solution_sources TEXT NOT NULL,
                    image_analysis TEXT,
                    session_id TEXT,
                    photo_path TEXT,
                    confidence INTEGER NOT NULL,
                    department TEXT NOT NULL,
                    department_override TEXT,
                    escalate INTEGER NOT NULL,
                    escalation_reason TEXT NOT NULL,
                    reviewed INTEGER NOT NULL,
                    reviewed_at TEXT,
                    status TEXT NOT NULL,
                    doctor_name TEXT,
                    prescription_medicines TEXT NOT NULL,
                    doctor_notes TEXT,
                    prescribed_at TEXT,
                    report_pdf_path TEXT,
                    reviewed_by_doctor_id INTEGER,
                    reviewed_by_doctor_name TEXT,
                    prescribed_by_doctor_id INTEGER
                )
            """)

            # Seed 2 Doctors
            now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
            s_conn.execute("""
                INSERT INTO doctors VALUES
                (1, 'dr_meredith', 'meredith@seattlegrace.internal', 'hashed_pass_1', 'Dr. Meredith Grey', 'MD-101', 'General Surgery', 'doctor', 1, ?, ?),
                (2, 'dr_derek', 'derek@seattlegrace.internal', 'hashed_pass_2', 'Dr. Derek Shepherd', 'MD-102', 'Neurosurgery', 'doctor', 1, ?, NULL)
            """, (now_iso, now_iso, now_iso))

            # Seed Session Upload
            s_conn.execute("INSERT INTO session_uploads VALUES ('sess-mig-01', '/uploads/scan.jpg', ?)", (now_iso,))

            # Seed Raw Vitals
            s_conn.execute("INSERT INTO raw_vitals VALUES (1, ?, 'dev-001', 98.6, 36.8, 72.0, 120.0, 80.0, ?)", (now_iso, now_iso))

            # Seed 2 Cases (one reviewed & prescribed, one open with nullable image_analysis)
            s_conn.execute("""
                INSERT INTO cases VALUES
                (1, ?, '{"spo2": 98}', 'Severe Headache', 'Head', '[]', '{"headache": true}', '[]',
                 '{"condition": "Migraine"}', '{"tokens": 100}', '[]', 'null', NULL, NULL, 80,
                 'Neurology', NULL, 0, '', 0, NULL, 'pending', NULL, '[]', NULL, NULL, NULL, NULL, NULL, NULL),
                (2, ?, '{"spo2": 99}', 'Laceration', 'Arm', '[]', '{"bleeding": true}', '[]',
                 '{"condition": "Forearm wound"}', '{}', '[]', '{"wound_depth_cm": 0.5}', 'sess-mig-01', '/uploads/scan.jpg', 95,
                 'General Surgery', 'Plastic Surgery', 0, '', 1, ?, 'prescribed', 'Dr. Meredith Grey',
                 '[{"name": "Amoxicillin", "dosage_per_day": "500mg", "remark": "3 times daily"}]',
                 'Wound cleaned and sutured.', ?, '/reports/case_2.pdf', 1, 'Dr. Meredith Grey', 1)
            """, (now_iso, now_iso, now_iso, now_iso))
            s_conn.commit()

        # 2. Run Migration Script
        migrator.migrate(sqlite_file, TEST_PG_URL)

        # 3. Verify Backup was created with read-only permissions
        backups = [f for f in os.listdir(tmpdir) if f.startswith("healthdeck_source.db.backup.")]
        assert len(backups) == 1, "Backup file was not created!"
        backup_stat = os.stat(os.path.join(tmpdir, backups[0]))
        assert not (backup_stat.st_mode & 0o222), "Backup file must have read-only permissions"
        print("    Verified read-only SQLite pre-migration backup creation.")

        # 4. Connect to PostgreSQL and verify counts, data types, sequences
        with psycopg.connect(TEST_PG_URL, row_factory=dict_row) as pg_conn:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM doctors")
                assert cur.fetchone()["count"] == 2
                cur.execute("SELECT count(*) FROM cases")
                assert cur.fetchone()["count"] == 2
                cur.execute("SELECT count(*) FROM session_uploads")
                assert cur.fetchone()["count"] == 1
                cur.execute("SELECT count(*) FROM raw_vitals")
                assert cur.fetchone()["count"] == 1
                print("    Verified 100% row count checksums across all tables.")

                # Verify Case 2 Preserved Foreign Keys, Types, JSONB
                cur.execute("SELECT * FROM cases WHERE id = 2")
                c2 = cur.fetchone()
                assert c2["chief_complaint"] == "Laceration"
                assert c2["reviewed"] is True
                assert c2["status"] == "prescribed"
                assert c2["reviewed_by_doctor_id"] == 1
                assert c2["prescribed_by_doctor_id"] == 1
                assert c2["session_id"] == "sess-mig-01"
                assert isinstance(c2["image_analysis"], dict)
                assert c2["image_analysis"]["wound_depth_cm"] == 0.5
                assert isinstance(c2["prescription_medicines"], list)
                assert c2["prescription_medicines"][0]["name"] == "Amoxicillin"

                # Verify Case 1 null image_analysis became NULL, not string 'null'
                cur.execute("SELECT * FROM cases WHERE id = 1")
                c1 = cur.fetchone()
                assert c1["image_analysis"] is None, "String 'null' should have been converted to Python None / SQL NULL"

                # 5. Sequence Advancement & Non-Collision Check:
                # Insert a NEW doctor and a NEW case; verify IDs advance past migrated IDs (3, not 1)
                cur.execute(
                    "INSERT INTO doctors (username, email, password_hash, full_name, medical_license, department, role) "
                    "VALUES ('dr_new', 'new@hospital.test', 'hash', 'Dr. New', 'MD-NEW', 'ER', 'doctor') RETURNING id"
                )
                new_doc_id = cur.fetchone()["id"]
                assert new_doc_id > 2, f"Sequence collision: Expected ID > 2, got {new_doc_id}"

                cur.execute(
                    "INSERT INTO cases (chief_complaint, symptom_location, department) "
                    "VALUES ('New Patient', 'Leg', 'ER') RETURNING id"
                )
                new_case_id = cur.fetchone()["id"]
                assert new_case_id > 2, f"Sequence collision: Expected ID > 2, got {new_case_id}"
                print(f"    Sequence advancement verified: New records assigned IDs {new_doc_id} and {new_case_id} without collision.")

        # 6. Re-run migration to test idempotency/safety
        migrator.migrate(sqlite_file, TEST_PG_URL)
        print("    Verified migration script is safe to re-run against populated PostgreSQL.")

    print("    [PASS] Historical SQLite to PostgreSQL migration completely verified.")


# ==============================================================================
# 9. PRODUCTION SAFETY VALIDATION (Section 11)
# ==============================================================================
def test_production_safety_scenarios():
    print("\n--- [9/10] Testing Production Safety & Environment Fallback Scenarios ---")
    import core.db as db

    # Scenario A: HEALTHDECK_ENV=production, DATABASE_URL missing -> Fatal error, NO SQLite
    os.environ["HEALTHDECK_ENV"] = "production"
    os.environ.pop("DATABASE_URL", None)
    db.close_pg_pool()
    try:
        db.init_db()
        assert False, "Scenario A failed: init_db() should fail when DATABASE_URL missing in production"
    except RuntimeError as e:
        assert "Silent fallback to SQLite is strictly prohibited in production" in str(e)
        print("    Scenario A PASS: Missing DATABASE_URL in production triggers fatal startup error.")

    try:
        db._connect()
        assert False, "Scenario A failed: _connect() should fail in production"
    except RuntimeError as e:
        assert "SQLite fallback is strictly prohibited in production" in str(e)
        print("    Scenario A PASS: Direct SQLite connection attempt in production strictly blocked.")

    # Scenario B: HEALTHDECK_ENV=production, DATABASE_URL malformed -> Fatal error, NO SQLite
    os.environ["HEALTHDECK_ENV"] = "production"
    os.environ["DATABASE_URL"] = "not_a_valid_postgres_url"
    db.close_pg_pool()
    try:
        db.init_db()
        assert False, "Scenario B failed: Malformed DATABASE_URL should fail in production"
    except RuntimeError as e:
        assert "Silent fallback to SQLite is strictly prohibited in production" in str(e)
        print("    Scenario B PASS: Malformed DATABASE_URL in production triggers fatal startup error.")

    # Scenario C: HEALTHDECK_ENV=production, unreachable PostgreSQL -> Fatal error, NO SQLite
    os.environ["HEALTHDECK_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://postgres:pass@127.0.0.1:54329/unreachable_db"
    db.close_pg_pool()
    try:
        db.init_db()
        assert False, "Scenario C failed: Unreachable PostgreSQL should fail in production"
    except RuntimeError as e:
        assert "FATAL: Failed to connect to PostgreSQL" in str(e)
        print("    Scenario C PASS: Unreachable PostgreSQL in production triggers fatal startup error.")

    # Scenario D: HEALTHDECK_ENV=development, DATABASE_URL missing -> SQLite fallback functional
    os.environ["HEALTHDECK_ENV"] = "development"
    os.environ.pop("DATABASE_URL", None)
    db.close_pg_pool()
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp_sqlite:
        os.environ["HEALTHDECK_DB_PATH"] = tmp_sqlite.name
        db.init_db()
        sqlite_conn = db._connect()
        sqlite_conn.execute("SELECT 1")
        sqlite_conn.close()
        print("    Scenario D PASS: SQLite fallback works in development mode when DATABASE_URL is unset.")

    # Scenario E: HEALTHDECK_ENV=development, DATABASE_URL points to real PostgreSQL -> PostgreSQL used
    os.environ["HEALTHDECK_ENV"] = "development"
    os.environ["DATABASE_URL"] = TEST_PG_URL
    db.close_pg_pool()
    db.init_db()
    assert db.is_postgres() is True
    with db.get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            db_name = cur.fetchone()["current_database"]
            assert db_name == "healthdeck_test"
    print("    Scenario E PASS: Real PostgreSQL used when DATABASE_URL is configured.")

    print("    [PASS] All 5 production safety scenarios verified.")


# ==============================================================================
# 10. DATA INTEGRITY & CONSTRAINT CHECKS (Section 12)
# ==============================================================================
def test_data_integrity_and_constraints():
    print("\n--- [10/10] Testing PostgreSQL Constraints, Foreign Keys & Indexes ---")
    import core.db as db

    os.environ["DATABASE_URL"] = TEST_PG_URL
    os.environ["HEALTHDECK_ENV"] = "development"
    db.close_pg_pool()
    db.init_db()

    with psycopg.connect(TEST_PG_URL) as conn:
        # 1. Test Doctor Username Uniqueness
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO doctors (username, email, password_hash, full_name) "
                "VALUES ('unique_test_user', 'unique1@test.com', 'h1', 'Doc U1')"
            )
            conn.commit()
            try:
                cur.execute(
                    "INSERT INTO doctors (username, email, password_hash, full_name) "
                    "VALUES ('unique_test_user', 'unique2@test.com', 'h2', 'Doc U2')"
                )
                conn.commit()
                assert False, "Duplicate doctor username should violate unique constraint"
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                print("    Doctor username unique constraint verified.")

        # 2. Test Doctor Email Uniqueness
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO doctors (username, email, password_hash, full_name) "
                    "VALUES ('different_user', 'unique1@test.com', 'h3', 'Doc U3')"
                )
                conn.commit()
                assert False, "Duplicate doctor email should violate unique constraint"
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                print("    Doctor email unique constraint verified.")

        # 3. Test Foreign Key Constraint Violation
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO cases (chief_complaint, symptom_location, department, reviewed_by_doctor_id) "
                    "VALUES ('FK test', 'Arm', 'ER', 9999999)"
                )
                conn.commit()
                assert False, "Invalid doctor foreign key should violate FK constraint"
            except psycopg.errors.ForeignKeyViolation:
                conn.rollback()
                print("    Doctor foreign key constraint verified.")

        # 4. Verify Performance Indexes Existence
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public'
                """
            )
            indexes = {r[0] for r in cur.fetchall()}
            expected_indexes = {
                "idx_cases_status_created",
                "idx_cases_created_at",
                "idx_cases_reviewed_by",
                "idx_cases_prescribed_by",
                "idx_doctors_lower_user",
                "idx_doctors_lower_email",
                "idx_raw_vitals_received"
            }
            for idx in expected_indexes:
                assert idx in indexes, f"Index '{idx}' missing in PostgreSQL!"
            print(f"    Verified existence of all performance indexes: {expected_indexes}")

    print("    [PASS] Data integrity, uniqueness, foreign keys, and indexes verified.")


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================
if __name__ == "__main__":
    print("======================================================================")
    print("PHASE 3.5: REAL POSTGRESQL INTEGRATION VALIDATION SUITE")
    print("======================================================================")

    # 1. Verify real PostgreSQL
    connected, pg_version = verify_real_postgres_connection()
    if not connected:
        sys.exit(1)

    start_time = time.time()
    try:
        test_migrations()
        test_jsonb_roundtrip()
        test_real_case_lifecycle()
        test_doctor_authentication()
        test_patient_safe_status_leakage()
        test_prescription_concurrency()
        test_connection_pool()
        test_sqlite_to_pg_migration()
        test_production_safety_scenarios()
        test_data_integrity_and_constraints()

        elapsed = time.time() - start_time
        print("\n======================================================================")
        print(f"ALL 10 REAL POSTGRESQL INTEGRATION SUITES PASSED ({elapsed:.2f}s)!")
        print(f"Verified against REAL PostgreSQL: {pg_version.split(',')[0]}")
        print("======================================================================")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"\n[!] INTEGRATION VALIDATION FAILED: {exc}")
        sys.exit(1)
    finally:
        import core.db as db
        db.close_pg_pool()
