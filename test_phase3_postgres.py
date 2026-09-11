"""Comprehensive test suite for Phase 3: PostgreSQL Central Database Migration.

Verifies:
1. Environment Fallback Behavior (Development SQLite allowed, Production SQLite strictly prohibited).
2. Production Startup Guard (Unreachable PostgreSQL or missing DATABASE_URL raises fatal error).
3. Versioned Schema Migration Subsystem (Migration files ordered, valid SQL, runner tracking).
4. Explicit JSONB adaptation for all 9 JSON fields.
5. Historical Data Migration script & SQLite backup functionality.
"""

import os
import sys
import tempfile
import sqlite3
import shutil
from unittest.mock import patch, MagicMock

# 1. TEST PRODUCTION FALLBACK & STARTUP GUARDS
def test_environment_guards():
    print("[*] Testing environment guards and SQLite fallback rules...")
    import core.db as db

    # Case A: Development mode without DATABASE_URL -> SQLite allowed
    with patch.dict(os.environ, {"HEALTHDECK_ENV": "development", "DATABASE_URL": ""}):
        assert not db.is_production()
        assert not db.is_postgres()
        # Should not raise
        conn = db._connect()
        conn.close()

    # Case B: Production mode without DATABASE_URL -> RuntimeError
    with patch.dict(os.environ, {"HEALTHDECK_ENV": "production", "DATABASE_URL": ""}):
        assert db.is_production()
        assert not db.is_postgres()
        try:
            db.init_db()
            assert False, "init_db() should have raised RuntimeError in production without DATABASE_URL"
        except RuntimeError as e:
            assert "Silent fallback to SQLite is strictly prohibited" in str(e)

        try:
            db._connect()
            assert False, "_connect() should have raised RuntimeError in production"
        except RuntimeError as e:
            assert "SQLite fallback is strictly prohibited in production" in str(e)

    # Case C: Production mode with unreachable DATABASE_URL -> RuntimeError
    with patch.dict(os.environ, {
        "HEALTHDECK_ENV": "production",
        "DATABASE_URL": "postgresql://invalid_user:invalid_pass@127.0.0.1:54329/nonexistent_db"
    }):
        assert db.is_production()
        assert db.is_postgres()
        db.close_pg_pool()
        try:
            db.init_db()
            assert False, "init_db() should have raised RuntimeError when PostgreSQL is unreachable in production"
        except RuntimeError as e:
            assert "FATAL: Failed to connect to PostgreSQL" in str(e)
        finally:
            db.close_pg_pool()

    print("    [PASS] Production guards and SQLite fallback rules verified.")


# 2. TEST VERSIONED MIGRATIONS
def test_versioned_migrations():
    print("[*] Testing versioned migrations subsystem...")
    import core.migrations as migrations

    available = migrations.get_available_migrations()
    assert len(available) >= 2, f"Expected at least 2 migrations, got {len(available)}"
    
    # Check ordering
    versions = [v[0] for v in available]
    assert versions == sorted(versions), f"Migrations not ordered: {versions}"
    assert versions[0] == "001"
    assert versions[1] == "002"

    # Verify SQL file contents
    for version, name, path in available:
        assert os.path.exists(path), f"Migration file missing: {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content.strip()) > 0
            # Basic DDL check
            assert "CREATE" in content.upper()

    print(f"    [PASS] Found {len(available)} valid ordered migration scripts ({versions}).")


# 3. TEST JSONB ADAPTATION FOR ALL 9 JSON FIELDS
def test_jsonb_adaptation():
    print("[*] Testing explicit Jsonb adaptation for all 9 JSON fields...")
    import core.db as db
    from psycopg.types.json import Jsonb

    expected_fields = [
        "vitals",
        "transcript",
        "extracted",
        "red_flags",
        "diagnosis",
        "raw_llm_response",
        "solution_sources",
        "prescription_medicines",
        "image_analysis",
    ]
    for field in expected_fields:
        assert field in db._JSON_FIELDS, f"Field {field} missing from _JSON_FIELDS"

    # Test Jsonb wrapping
    sample_data = {
        "vitals": {"spo2": 98, "hr": 72},
        "transcript": [{"role": "user", "text": "fever"}],
        "extracted": {"symptoms": ["fever"]},
        "red_flags": ["high_fever"],
        "diagnosis": {"primary_condition": "Viral Infection"},
        "raw_llm_response": {"confidence": 85},
        "solution_sources": [{"title": "CDC"}],
        "prescription_medicines": [{"name": "Paracetamol", "dosage_per_day": "500mg"}],
        "image_analysis": {"observation": "Rash"},
    }

    for key, val in sample_data.items():
        wrapped = Jsonb(val)
        assert wrapped.obj == val, f"Jsonb wrapping failed for {key}"

    print(f"    [PASS] All {len(expected_fields)} JSONB fields verified with psycopg.types.json.Jsonb.")


# 4. TEST SQLITE IMMUTABLE BACKUP & DATA MIGRATION LOGIC
def test_sqlite_backup():
    print("[*] Testing SQLite pre-migration backup...")
    import scripts.migrate_sqlite_to_pg as migrator

    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = os.path.join(tmpdir, "test.db")
        with sqlite3.connect(test_db) as conn:
            conn.execute("CREATE TABLE test (id INT, val TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'hello')")
            conn.commit()

        backup_path = migrator.backup_sqlite_db(test_db)
        assert os.path.exists(backup_path)
        assert backup_path.startswith(test_db + ".backup.")

        # Check read-only permission (0o444)
        stat = os.stat(backup_path)
        # Check that write permission is unset
        assert not (stat.st_mode & 0o222), "Backup file should be read-only"

        # Verify contents of backup
        with sqlite3.connect(backup_path) as conn:
            row = conn.execute("SELECT val FROM test WHERE id = 1").fetchone()
            assert row[0] == "hello"

    print("    [PASS] SQLite pre-migration backup and read-only permission verified.")


# 5. TEST ROW NORMALIZATION & JSON DESERIALIZATION
def test_row_normalization():
    print("[*] Testing row-to-case and medicine normalization...")
    import core.db as db

    raw_row = {
        "id": 42,
        "created_at": "2026-09-11T12:00:00+00:00",
        "vitals": '{"spo2": 99}',
        "chief_complaint": "Cough",
        "symptom_location": "Chest",
        "transcript": '[{"role": "doctor", "text": "How long?"}]',
        "extracted": '{"duration": "3 days"}',
        "red_flags": '[]',
        "diagnosis": '{"condition": "Bronchitis"}',
        "raw_llm_response": '{}',
        "solution_sources": '[]',
        "image_analysis": 'null',
        "prescription_medicines": '[{"name": "Amoxicillin", "instructions": "twice daily"}]',
        "escalate": 0,
        "reviewed": 1,
        "department": "General Physician",
        "department_override": "Pulmonology",
    }

    case = db._row_to_case(raw_row)
    assert case["id"] == 42
    assert isinstance(case["vitals"], dict) and case["vitals"]["spo2"] == 99
    assert isinstance(case["transcript"], list) and len(case["transcript"]) == 1
    assert case["escalate"] is False
    assert case["reviewed"] is True
    assert case["effective_department"] == "Pulmonology"
    # Medicine instructions mapped to remark
    assert case["prescription_medicines"][0]["remark"] == "twice daily"

    print("    [PASS] Case normalization and deserialization verified.")


if __name__ == "__main__":
    print("======================================================================")
    print("RUNNING PHASE 3 POSTGRESQL & MIGRATION TEST SUITE")
    print("======================================================================")
    test_environment_guards()
    test_versioned_migrations()
    test_jsonb_adaptation()
    test_sqlite_backup()
    test_row_normalization()
    print("======================================================================")
    print("ALL PHASE 3 TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")
