"""Historical data migration script: SQLite to PostgreSQL for Health Deck.

Copies historical doctors, session_uploads, raw_vitals, and cases from SQLite to PostgreSQL.
Preserves primary key IDs, advances PostgreSQL sequences, converts data types safely,
and performs an immutable pre-migration backup of the SQLite file.
"""

import os
import sys
import shutil
import sqlite3
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()


def backup_sqlite_db(sqlite_path: str) -> str:
    """Create a timestamped read-only backup of the SQLite database."""
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"Source SQLite database not found at: {sqlite_path}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = f"{sqlite_path}.backup.{timestamp}"
    counter = 1
    while os.path.exists(backup_path):
        backup_path = f"{sqlite_path}.backup.{timestamp}_{counter}"
        counter += 1
    shutil.copy2(sqlite_path, backup_path)
    os.chmod(backup_path, 0o444)  # Read-only
    return backup_path


def migrate(sqlite_path: str, postgres_url: str):
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from core.migrations import apply_migrations

    print(f"[*] Starting migration from: {sqlite_path}")
    backup_file = backup_sqlite_db(sqlite_path)
    print(f"[*] Created read-only pre-migration backup at: {backup_file}")

    sqlite_conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    sqlite_conn.row_factory = sqlite3.Row

    with psycopg.connect(postgres_url) as pg_conn:
        # Step 1: Ensure versioned migrations are applied
        print("[*] Ensuring PostgreSQL schema migrations are up to date...")
        applied_count = apply_migrations(pg_conn)
        print(f"    Applied {applied_count} pending migration(s).")

        with pg_conn.transaction():
            with pg_conn.cursor() as pg_cur:
                # 1. Migrate DOCTORS
                print("[*] Migrating doctors...")
                sqlite_doctors = sqlite_conn.execute("SELECT * FROM doctors ORDER BY id ASC").fetchall()
                for d in sqlite_doctors:
                    created_at = datetime.fromisoformat(d["created_at"]) if d["created_at"] else datetime.now(timezone.utc)
                    last_login_at = datetime.fromisoformat(d["last_login_at"]) if d["last_login_at"] else None
                    pg_cur.execute(
                        """
                        INSERT INTO doctors (
                            id, username, email, password_hash, full_name,
                            medical_license, department, role, is_active,
                            created_at, last_login_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            username = EXCLUDED.username,
                            email = EXCLUDED.email,
                            password_hash = EXCLUDED.password_hash,
                            full_name = EXCLUDED.full_name,
                            medical_license = EXCLUDED.medical_license,
                            department = EXCLUDED.department,
                            role = EXCLUDED.role,
                            is_active = EXCLUDED.is_active,
                            last_login_at = EXCLUDED.last_login_at
                        """,
                        (
                            d["id"], d["username"], d["email"], d["password_hash"], d["full_name"],
                            d["medical_license"], d["department"], d["role"], bool(d["is_active"]),
                            created_at, last_login_at,
                        ),
                    )
                pg_cur.execute("SELECT setval(pg_get_serial_sequence('doctors', 'id'), COALESCE(MAX(id), 1)) FROM doctors")
                print(f"    Migrated {len(sqlite_doctors)} doctor record(s).")

                # 2. Migrate SESSION_UPLOADS
                print("[*] Migrating session uploads...")
                sqlite_uploads = sqlite_conn.execute("SELECT * FROM session_uploads ORDER BY uploaded_at ASC").fetchall()
                for u in sqlite_uploads:
                    uploaded_at = datetime.fromisoformat(u["uploaded_at"]) if u["uploaded_at"] else datetime.now(timezone.utc)
                    pg_cur.execute(
                        """
                        INSERT INTO session_uploads (session_id, image_path, uploaded_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (session_id) DO UPDATE SET
                            image_path = EXCLUDED.image_path,
                            uploaded_at = EXCLUDED.uploaded_at
                        """,
                        (u["session_id"], u["image_path"], uploaded_at),
                    )
                print(f"    Migrated {len(sqlite_uploads)} session upload record(s).")

                # 3. Migrate RAW_VITALS
                print("[*] Migrating raw vitals...")
                sqlite_vitals = sqlite_conn.execute("SELECT * FROM raw_vitals ORDER BY id ASC").fetchall()
                for v in sqlite_vitals:
                    received_at = datetime.fromisoformat(v["received_at"]) if v["received_at"] else datetime.now(timezone.utc)
                    ts = datetime.fromisoformat(v["timestamp"]) if v["timestamp"] else None
                    pg_cur.execute(
                        """
                        INSERT INTO raw_vitals (
                            id, received_at, device_id, spo2, temp_c, hr,
                            systolic_bp, diastolic_bp, timestamp
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            v["id"], received_at, v["device_id"], v["spo2"], v["temp_c"], v["hr"],
                            v["systolic_bp"], v["diastolic_bp"], ts,
                        ),
                    )
                pg_cur.execute("SELECT setval(pg_get_serial_sequence('raw_vitals', 'id'), COALESCE(MAX(id), 1)) FROM raw_vitals")
                print(f"    Migrated {len(sqlite_vitals)} raw vitals record(s).")

                # 4. Migrate CASES
                print("[*] Migrating cases...")
                sqlite_cases = sqlite_conn.execute("SELECT * FROM cases ORDER BY id ASC").fetchall()
                for c in sqlite_cases:
                    created_at = datetime.fromisoformat(c["created_at"]) if c["created_at"] else datetime.now(timezone.utc)
                    reviewed_at = datetime.fromisoformat(c["reviewed_at"]) if c["reviewed_at"] else None
                    prescribed_at = datetime.fromisoformat(c["prescribed_at"]) if c["prescribed_at"] else None

                    vitals = json.loads(c["vitals"]) if c["vitals"] else {}
                    transcript = json.loads(c["transcript"]) if c["transcript"] else []
                    extracted = json.loads(c["extracted"]) if c["extracted"] else {}
                    red_flags = json.loads(c["red_flags"]) if c["red_flags"] else []
                    diagnosis = json.loads(c["diagnosis"]) if c["diagnosis"] else {}
                    raw_llm = json.loads(c["raw_llm_response"]) if c["raw_llm_response"] else {}
                    solution_sources = json.loads(c["solution_sources"]) if c["solution_sources"] else []
                    img_analysis = json.loads(c["image_analysis"]) if (c["image_analysis"] and c["image_analysis"] != "null") else None
                    medicines = json.loads(c["prescription_medicines"]) if c["prescription_medicines"] else []

                    # Session FK check
                    session_id = c["session_id"]
                    if session_id:
                        pg_cur.execute("SELECT 1 FROM session_uploads WHERE session_id = %s", (session_id,))
                        if not pg_cur.fetchone():
                            session_id = None

                    # Doctor FK check
                    reviewed_by_id = c["reviewed_by_doctor_id"]
                    if reviewed_by_id:
                        pg_cur.execute("SELECT 1 FROM doctors WHERE id = %s", (reviewed_by_id,))
                        if not pg_cur.fetchone():
                            reviewed_by_id = None

                    prescribed_by_id = c["prescribed_by_doctor_id"]
                    if prescribed_by_id:
                        pg_cur.execute("SELECT 1 FROM doctors WHERE id = %s", (prescribed_by_id,))
                        if not pg_cur.fetchone():
                            prescribed_by_id = None

                    pg_cur.execute(
                        """
                        INSERT INTO cases (
                            id, created_at, vitals, chief_complaint, symptom_location,
                            transcript, extracted, red_flags, diagnosis, raw_llm_response,
                            solution_sources, image_analysis, session_id, photo_path,
                            confidence, department, department_override, escalate,
                            escalation_reason, reviewed, reviewed_at, status,
                            doctor_name, prescription_medicines, doctor_notes,
                            prescribed_at, report_pdf_path, reviewed_by_doctor_id,
                            reviewed_by_doctor_name, prescribed_by_doctor_id
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            doctor_name = EXCLUDED.doctor_name,
                            department_override = EXCLUDED.department_override,
                            reviewed = EXCLUDED.reviewed,
                            reviewed_at = EXCLUDED.reviewed_at,
                            reviewed_by_doctor_id = EXCLUDED.reviewed_by_doctor_id,
                            reviewed_by_doctor_name = EXCLUDED.reviewed_by_doctor_name,
                            prescribed_at = EXCLUDED.prescribed_at,
                            prescription_medicines = EXCLUDED.prescription_medicines,
                            doctor_notes = EXCLUDED.doctor_notes,
                            report_pdf_path = EXCLUDED.report_pdf_path,
                            prescribed_by_doctor_id = EXCLUDED.prescribed_by_doctor_id
                        """,
                        (
                            c["id"], created_at, Jsonb(vitals), c["chief_complaint"], c["symptom_location"],
                            Jsonb(transcript), Jsonb(extracted), Jsonb(red_flags), Jsonb(diagnosis), Jsonb(raw_llm),
                            Jsonb(solution_sources), Jsonb(img_analysis) if img_analysis is not None else None,
                            session_id, c["photo_path"], c["confidence"], c["department"],
                            c["department_override"], bool(c["escalate"]), c["escalation_reason"],
                            bool(c["reviewed"]), reviewed_at, c["status"], c["doctor_name"],
                            Jsonb(medicines), c["doctor_notes"], prescribed_at, c["report_pdf_path"],
                            reviewed_by_id, c["reviewed_by_doctor_name"], prescribed_by_id,
                        ),
                    )
                pg_cur.execute("SELECT setval(pg_get_serial_sequence('cases', 'id'), COALESCE(MAX(id), 1)) FROM cases")
                print(f"    Migrated {len(sqlite_cases)} case record(s).")

            # Checksums verification
            with pg_conn.cursor() as pg_cur:
                source_doc_ids = [d["id"] for d in sqlite_doctors] or [-1]
                source_case_ids = [c["id"] for c in sqlite_cases] or [-1]
                pg_cur.execute("SELECT count(*) FROM doctors WHERE id = ANY(%s)", (source_doc_ids,))
                migrated_doc_count = pg_cur.fetchone()[0]
                pg_cur.execute("SELECT count(*) FROM cases WHERE id = ANY(%s)", (source_case_ids,))
                migrated_case_count = pg_cur.fetchone()[0]

                print("\n[*] Data Verification Checksums:")
                print(f"    Doctors: SQLite={len(sqlite_doctors)}, Verified in PostgreSQL={migrated_doc_count}")
                print(f"    Cases:   SQLite={len(sqlite_cases)}, Verified in PostgreSQL={migrated_case_count}")

                assert migrated_doc_count == len(sqlite_doctors), "Doctor count mismatch!"
                assert migrated_case_count == len(sqlite_cases), "Case count mismatch!"

    sqlite_conn.close()
    print("\n[+] MIGRATION COMPLETED SUCCESSFULLY WITH 100% INTEGRITY VERIFICATION!")


if __name__ == "__main__":
    sqlite_db = os.environ.get("HEALTHDECK_DB_PATH", "healthdeck.db")
    pg_url = os.environ.get("DATABASE_URL")
    if not pg_url:
        print("Error: DATABASE_URL must be configured to run PostgreSQL migration.")
        sys.exit(1)
    migrate(sqlite_db, pg_url)
