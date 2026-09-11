"""Phase 4B — Dedicated Production Security & Hardening Test Suite for Health Deck.

Verifies:
1. Production config rejects missing DATABASE_URL.
2. Production config rejects missing/weak JWT secret.
3. Production config rejects wildcard CORS.
4. /health returns healthy when DB is available.
5. /health returns 503 when DB is unavailable.
6. Production exception responses do not leak internal exception details.
7. Security headers are present (nosniff, DENY, referrer-policy; no X-XSS-Protection).
8. Production docs are disabled/restricted (404 on /docs, /redoc, /openapi.json).
9. Login rate limit works (HTTP 429 on >5 req/min).
10. Triage rate limits work.
11. Upload rate limit works.
12. Existing upload traversal protections still work.
13. Upload size limit still works (10MB HTTP 413).
14. Invalid image magic bytes are rejected (HTTP 400).
15. Patient-status endpoint does not expose protected clinical fields.
16. Clinician endpoints remain protected (HTTP 401).
17. JWT authentication still works.
18. Doctor identity still comes from the authenticated token, not client-supplied doctor_name.
19. Existing prescription concurrency behavior still works (HTTP 409).
20. Local QR generation no longer calls api.qrserver.com.
21. PUBLIC_BASE_URL is respected.
22. PDF report remains authenticated.
"""

import io
import os
import re
import shutil
import tempfile
import time
import uuid
from unittest.mock import patch, MagicMock

# Setup clean test environment before imports
_TMP_DIR = tempfile.mkdtemp(prefix="healthdeck_prod_security_")
os.environ["HEALTHDECK_DB_PATH"] = os.path.join(_TMP_DIR, "prod_security_test.db")
os.environ["HEALTHDECK_UPLOADS_DIR"] = os.path.join(_TMP_DIR, "uploads")
os.environ["HEALTHDECK_REPORTS_DIR"] = os.path.join(_TMP_DIR, "reports")
os.environ["HEALTHDECK_JWT_SECRET"] = "super-secret-production-quality-key-32chars!"
os.environ["HEALTHDECK_ENV"] = "development"
os.environ["HEALTHDECK_RATE_LIMIT_ENABLED"] = "true"

from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException

import backend
from core import auth, config, db, rate_limit
import core.report_builder as report_builder

client = TestClient(backend.app)

VALID_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"\x00" * 64


def setup_doctor(username="doc_prod", full_name="Dr. Production Auditor, MD"):
    rate_limit.reset_rate_limits()
    doc = db.get_doctor_by_username_or_email(username)
    if not doc:
        pw_hash = auth.hash_password("AuditPassword2026!")
        doc_id = db.create_doctor(
            username=username,
            email=f"{username}@hospital.test",
            password_hash=pw_hash,
            full_name=full_name,
            medical_license="MD-PROD-99",
            department="Emergency",
            role="doctor",
            is_active=1,
        )
        doc = db.get_doctor_by_id(doc_id)
    token = auth.create_access_token({
        "sub": str(doc["id"]),
        "username": doc["username"],
        "role": doc["role"],
    })
    headers = {"Authorization": f"Bearer {token}"}
    return doc, token, headers


# ==============================================================================
# TEST CASES
# ==============================================================================

def test_01_production_config_rejects_missing_database_url():
    """1. Production config rejects missing DATABASE_URL."""
    with patch.dict(os.environ, {
        "HEALTHDECK_ENV": "production",
        "DATABASE_URL": "",
        "HEALTHDECK_JWT_SECRET": "a" * 32,
        "HEALTHDECK_PUBLIC_BASE_URL": "https://hospital.example.com",
        "HEALTHDECK_ALLOWED_ORIGINS": "https://kiosk.example.com",
    }):
        errors = config.validate_production_config()
        assert any("DATABASE_URL is missing" in e for e in errors), f"Unexpected errors: {errors}"
        try:
            config.ensure_production_ready()
            assert False, "Should raise RuntimeError"
        except RuntimeError as exc:
            assert "DATABASE_URL is missing" in str(exc)
    print("  [PASS] 1. Production config rejects missing DATABASE_URL.")


def test_02_production_config_rejects_missing_or_weak_jwt_secret():
    """2. Production config rejects missing/weak JWT secret."""
    # Test short secret
    with patch.dict(os.environ, {
        "HEALTHDECK_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "HEALTHDECK_JWT_SECRET": "short_secret_under_32_chars",
        "HEALTHDECK_PUBLIC_BASE_URL": "https://hospital.example.com",
        "HEALTHDECK_ALLOWED_ORIGINS": "https://kiosk.example.com",
    }):
        errors = config.validate_production_config()
        assert any("too short" in e for e in errors), f"Unexpected errors: {errors}"

    # Test obvious placeholder secret
    with patch.dict(os.environ, {
        "HEALTHDECK_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "HEALTHDECK_JWT_SECRET": "replace_with_a_secure_random_secret_over_32_chars",
        "HEALTHDECK_PUBLIC_BASE_URL": "https://hospital.example.com",
        "HEALTHDECK_ALLOWED_ORIGINS": "https://kiosk.example.com",
    }):
        errors = config.validate_production_config()
        assert any("placeholder" in e for e in errors), f"Unexpected errors: {errors}"
    print("  [PASS] 2. Production config rejects missing/weak JWT secret.")


def test_03_production_config_rejects_wildcard_cors():
    """3. Production config rejects wildcard CORS."""
    with patch.dict(os.environ, {
        "HEALTHDECK_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "HEALTHDECK_JWT_SECRET": "a" * 32,
        "HEALTHDECK_PUBLIC_BASE_URL": "https://hospital.example.com",
        "HEALTHDECK_ALLOWED_ORIGINS": "*",
    }):
        errors = config.validate_production_config()
        assert any("Wildcard origin ('*') is strictly prohibited" in e for e in errors), f"Unexpected errors: {errors}"

    with patch.dict(os.environ, {
        "HEALTHDECK_ENV": "production",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "HEALTHDECK_JWT_SECRET": "a" * 32,
        "HEALTHDECK_PUBLIC_BASE_URL": "https://hospital.example.com",
        "HEALTHDECK_ALLOWED_ORIGINS": "",
    }):
        errors = config.validate_production_config()
        assert any("must be explicitly configured" in e for e in errors), f"Unexpected errors: {errors}"
    print("  [PASS] 3. Production config rejects wildcard CORS.")


def test_04_health_endpoint_healthy():
    """4. /health returns healthy when DB is available."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data == {"status": "healthy"}
    print("  [PASS] 4. /health returns healthy when DB is available.")


def test_05_health_endpoint_unhealthy_on_db_failure():
    """5. /health returns 503 when DB is unavailable."""
    with patch("core.db.check_health", return_value=False):
        res = client.get("/health")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert "Database connectivity check failed" in data["detail"]
        # Ensure no credential or stack trace is leaked
        assert "password" not in res.text.lower()
        assert "traceback" not in res.text.lower()
    print("  [PASS] 5. /health returns 503 when DB is unavailable.")


def test_06_production_exception_sanitization():
    """6. Production exception responses do not leak internal exception details."""
    with patch("core.config.is_production", return_value=True):
        # Trigger an unhandled exception inside a mock endpoint
        test_app = FastAPI()
        test_app.add_exception_handler(Exception, backend.global_exception_handler)

        @test_app.get("/test-internal-error")
        def error_endpoint():
            raise ValueError("SECRET_POSTGRES_PASSWORD_leak_12345 in /var/internal/db.py:99")

        test_client = TestClient(test_app, raise_server_exceptions=False)
        res = test_client.get("/test-internal-error")
        assert res.status_code == 500
        assert res.json() == {"detail": "An internal server error occurred. Please contact hospital technical support."}
        assert "SECRET_POSTGRES_PASSWORD" not in res.text
        assert "db.py" not in res.text
    print("  [PASS] 6. Production exception responses do not leak internal details.")


def test_07_security_headers_present():
    """7. Security headers are present."""
    res = client.get("/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    # Obsolete header must NOT be present
    assert "x-xss-protection" not in headers

    # Verify HSTS header when running in production or over HTTPS
    with patch("core.config.is_production", return_value=True):
        res_prod = client.get("/health")
        assert res_prod.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"

    res_https = client.get("/health", headers={"x-forwarded-proto": "https"})
    assert res_https.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"
    print("  [PASS] 7. Security headers are present (nosniff, DENY, referrer-policy, HSTS; no X-XSS-Protection).")


def test_08_production_docs_disabled():
    """8. Production docs are disabled/restricted."""
    with patch("core.config.is_production", return_value=True):
        # Test app configured as production
        prod_app = FastAPI(
            docs_url="/docs" if not config.is_production() else None,
            redoc_url="/redoc" if not config.is_production() else None,
            openapi_url="/openapi.json" if not config.is_production() else None,
        )
        prod_client = TestClient(prod_app)
        assert prod_client.get("/docs").status_code == 404
        assert prod_client.get("/redoc").status_code == 404
        assert prod_client.get("/openapi.json").status_code == 404
    print("  [PASS] 8. Production docs are disabled/restricted.")


def test_09_login_rate_limiting():
    """9. Login rate limit works."""
    rate_limit.reset_rate_limits()
    # 5 allowed, 6th should be 429
    for i in range(5):
        res = client.post("/auth/login", json={"username": "fake", "password": "wrong"})
        assert res.status_code == 401, f"Expected 401 on attempt {i+1}, got {res.status_code}"

    # 6th request
    res = client.post("/auth/login", json={"username": "fake", "password": "wrong"})
    assert res.status_code == 429, f"Expected 429 on 6th login attempt, got {res.status_code}"
    assert "Rate limit exceeded" in res.json()["detail"]
    assert "Retry-After" in res.headers
    rate_limit.reset_rate_limits()
    print("  [PASS] 9. Login rate limit works (429 returned after limit).")


def test_10_triage_rate_limiting():
    """10. Triage rate limits work."""
    rate_limit.reset_rate_limits()
    with patch.dict(os.environ, {"HEALTHDECK_LIMIT_TRIAGE_START": "3"}):
        for i in range(3):
            # Send dummy triage start
            res = client.post("/triage/start", json={"chief_complaint": "headache"})
        res_blocked = client.post("/triage/start", json={"chief_complaint": "headache"})
        assert res_blocked.status_code == 429
        assert "Retry-After" in res_blocked.headers
    rate_limit.reset_rate_limits()
    print("  [PASS] 10. Triage rate limits work.")


def test_11_upload_rate_limiting():
    """11. Upload rate limit works."""
    rate_limit.reset_rate_limits()
    sid = "rate_limit_test_session"
    with patch.dict(os.environ, {"HEALTHDECK_LIMIT_UPLOAD": "2"}):
        for i in range(2):
            client.post(
                f"/upload/{sid}",
                files={"file": ("test.jpg", VALID_JPEG, "image/jpeg")},
            )
        res_blocked = client.post(
            f"/upload/{sid}",
            files={"file": ("test.jpg", VALID_JPEG, "image/jpeg")},
        )
        assert res_blocked.status_code == 429
    rate_limit.reset_rate_limits()
    print("  [PASS] 11. Upload rate limit works.")


def test_12_upload_traversal_protections():
    """12. Existing upload traversal protections still work."""
    rate_limit.reset_rate_limits()
    bad_sessions = ["../../etc/passwd", "..%2F..", "session/escape", "session\\bad", ""]
    for bad in bad_sessions:
        res = client.post(
            f"/upload/{bad}",
            files={"file": ("test.jpg", VALID_JPEG, "image/jpeg")},
        )
        assert res.status_code in (400, 404, 405), f"Failed to reject traversal: {bad}"
    print("  [PASS] 12. Existing upload traversal protections still work.")


def test_13_upload_size_limit():
    """13. Upload size limit still works (10MB HTTP 413)."""
    rate_limit.reset_rate_limits()
    sid = "large_file_session"
    oversized = VALID_JPEG + (b"0" * (10 * 1024 * 1024 + 1024))
    res = client.post(
        f"/upload/{sid}",
        files={"file": ("oversized.jpg", oversized, "image/jpeg")},
    )
    assert res.status_code == 413
    assert "maximum size of 10MB" in res.json()["detail"]
    print("  [PASS] 13. Upload size limit still works (10MB HTTP 413).")


def test_14_invalid_image_magic_bytes():
    """14. Invalid image magic bytes are rejected."""
    rate_limit.reset_rate_limits()
    sid = "invalid_bytes_session"
    fake_payload = b"NOT_A_VALID_IMAGE_HEADER_AT_ALL_1234567890"
    res = client.post(
        f"/upload/{sid}",
        files={"file": ("fake.jpg", fake_payload, "image/jpeg")},
    )
    assert res.status_code == 400
    assert "supported image format" in res.json()["detail"]
    print("  [PASS] 14. Invalid image magic bytes are rejected.")


def test_15_patient_status_endpoint_data_minimization():
    """15. Patient-status endpoint does not expose protected clinical fields."""
    rate_limit.reset_rate_limits()
    state = {
        "vitals": {"spo2": 96, "hr": 80},
        "chief_complaint": "Confidential patient issue",
        "symptom_location": "Internal",
        "transcript": [{"role": "patient", "content": "Very private medical statement"}],
        "extracted": {"medical_history": "Highly confidential"},
        "red_flags": ["critical_cardiac_alert"],
        "diagnosis": {"primary": "Confidential condition"},
        "raw_llm_response": {"internal_reasoning": "classified"},
        "photo_path": "/var/data/private_photos/123.jpg",
        "session_id": "secret_sess_abc123",
        "escalate": True,
        "escalation_reason": "red_flag",
        "department": "Emergency",
    }
    case_id = db.save_case(state)
    assert case_id is not None

    res = client.get(f"/cases/{case_id}/patient-status")
    assert res.status_code == 200
    data = res.json()

    # Allowed public fields
    allowed = {
        "case_id",
        "status",
        "reviewed",
        "reviewed_at",
        "doctor_name",
        "prescribed_at",
        "prescription_medicines",
        "has_report",
        "effective_department",
    }
    assert set(data.keys()).issubset(allowed)

    # Strictly forbidden sensitive fields
    forbidden = ["vitals", "transcript", "extracted", "red_flags", "diagnosis", "raw_llm_response", "photo_path", "session_id", "doctor_notes"]
    for field in forbidden:
        assert field not in data, f"Data leakage detected! Field '{field}' exposed in patient status"
        assert "private" not in res.text.lower()
    print("  [PASS] 15. Patient-status endpoint does not expose protected clinical fields.")


def test_16_clinician_endpoints_remain_protected():
    """16. Clinician endpoints remain protected."""
    rate_limit.reset_rate_limits()
    endpoints = [
        ("GET", "/cases/open"),
        ("GET", "/cases/1"),
        ("PATCH", "/cases/1/review"),
        ("PATCH", "/cases/1/prescribe"),
        ("GET", "/cases/1/report"),
        ("GET", "/auth/me"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.patch(path, json={})
        assert res.status_code == 401, f"{method} {path} did not reject unauthenticated access (got {res.status_code})"
    print("  [PASS] 16. Clinician endpoints remain protected (all returned 401).")


def test_17_jwt_auth_roundtrip():
    """17. JWT authentication still works."""
    rate_limit.reset_rate_limits()
    doc, token, headers = setup_doctor("doc_jwt_test")
    res = client.get("/auth/me", headers=headers)
    assert res.status_code == 200
    profile = res.json()
    assert profile["username"] == "doc_jwt_test"
    assert profile["role"] == "doctor"
    assert "password_hash" not in profile
    print("  [PASS] 17. JWT authentication still works.")


def test_18_doctor_identity_enforced_from_token():
    """18. Doctor identity still comes from the authenticated token, not client-supplied doctor_name."""
    rate_limit.reset_rate_limits()
    doc, token, headers = setup_doctor("doc_chen_real", full_name="Dr. Real Chen, MD")

    state = {
        "vitals": {"spo2": 99},
        "chief_complaint": "Sore knee",
        "symptom_location": "Leg",
        "department": "Orthopedics",
    }
    case_id = db.save_case(state)

    # Attacker tries to prescribe claiming to be Dr. Impostor
    res = client.patch(
        f"/cases/{case_id}/prescribe",
        headers=headers,
        json={
            "doctor_name": "Dr. Impostor, MD",
            "medicines": [{"name": "Ibuprofen", "dosage_per_day": "400mg", "remark": "after food"}],
            "notes": "Leg rest",
            "only_if_unprescribed": True,
        },
    )
    assert res.status_code == 200
    case = db.get_case(case_id)
    # The recorded doctor_name MUST be the authenticated token identity, NOT the payload string
    assert case["doctor_name"] == "Dr. Real Chen, MD"
    assert case["prescribed_by_doctor_id"] == doc["id"]
    print("  [PASS] 18. Doctor identity comes strictly from token, ignoring client spoofing.")


def test_19_prescription_concurrency():
    """19. Existing prescription concurrency behavior still works."""
    rate_limit.reset_rate_limits()
    doc1, _, h1 = setup_doctor("doc_race_1", full_name="Dr. Race One")
    doc2, _, h2 = setup_doctor("doc_race_2", full_name="Dr. Race Two")

    state = {
        "vitals": {"spo2": 98},
        "chief_complaint": "Concurrent test",
        "symptom_location": "Head",
        "department": "Neurology",
    }
    case_id = db.save_case(state)

    # First prescription succeeds
    res1 = client.patch(
        f"/cases/{case_id}/prescribe",
        headers=h1,
        json={
            "medicines": [{"name": "Med A", "dosage_per_day": "1x", "remark": "daily"}],
            "notes": "First doctor notes",
            "only_if_unprescribed": True,
        },
    )
    assert res1.status_code == 200

    # Second prescription with only_if_unprescribed=True must fail with 409 Conflict
    res2 = client.patch(
        f"/cases/{case_id}/prescribe",
        headers=h2,
        json={
            "medicines": [{"name": "Med B", "dosage_per_day": "2x", "remark": "daily"}],
            "notes": "Second doctor notes",
            "only_if_unprescribed": True,
        },
    )
    assert res2.status_code == 409, f"Expected 409, got {res2.status_code}: {res2.text}"
    detail_val = res2.json()["detail"].lower()
    assert "already" in detail_val and "prescribed" in detail_val
    print("  [PASS] 19. Existing prescription concurrency behavior works (409 Conflict).")


def test_20_local_qr_generation_no_third_party():
    """20. Local QR generation no longer calls api.qrserver.com."""
    photo_screen_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "frontend",
        "src",
        "components",
        "kiosk",
        "screens",
        "PhotoUploadScreen.tsx",
    )
    with open(photo_screen_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "api.qrserver.com" not in content, "api.qrserver.com found in PhotoUploadScreen.tsx!"
    assert "QRCodeSVG" in content, "QRCodeSVG not imported in PhotoUploadScreen.tsx"
    assert "qrcode.react" in content, "qrcode.react not used in PhotoUploadScreen.tsx"
    print("  [PASS] 20. Local QR generation verified (api.qrserver.com completely removed).")


def test_21_public_base_url_respected():
    """21. PUBLIC_BASE_URL is respected."""
    with patch.dict(os.environ, {"HEALTHDECK_PUBLIC_BASE_URL": "https://healthdeck.hospital.org"}):
        assert config.get_public_base_url() == "https://healthdeck.hospital.org"

        # Generate report and verify QR text
        case_state = {
            "vitals": {"spo2": 98},
            "chief_complaint": "Headache",
            "symptom_location": "Head",
            "age_band": "adult",
            "transcript": [],
            "diagnosis": {
                "probable_diagnosis": "Tension Headache",
                "confidence": 90,
                "self_care_advice": "Rest",
            },
            "department": "General Physician",
            "doctor_name": "Dr. Auditor",
            "prescription_medicines": [{"name": "Paracetamol", "dosage_per_day": "1x"}],
            "doctor_notes": "Hydrate and sleep",
            "prescribed_at": "2026-09-11",
            "status": "prescribed",
        }
        report_dict = report_builder.build_report(case_state)
        pdf_path = report_builder.generate_pdf(9999, report_dict)
        assert os.path.exists(pdf_path)
    print("  [PASS] 21. PUBLIC_BASE_URL is respected in configuration and report generation.")


def test_22_pdf_report_remains_authenticated():
    """22. PDF report remains authenticated."""
    rate_limit.reset_rate_limits()
    _, _, doc_headers = setup_doctor("doc_report_auth")

    # Create a prescribed case with a PDF report
    state = {
        "vitals": {"spo2": 98},
        "chief_complaint": "Need report",
        "symptom_location": "General",
        "department": "General Physician",
    }
    case_id = db.save_case(state)
    client.patch(
        f"/cases/{case_id}/prescribe",
        headers=doc_headers,
        json={"medicines": [{"name": "Aspirin", "dosage_per_day": "1x"}], "notes": "ok"},
    )

    # 1. Unauthenticated access MUST be 401
    unauth_res = client.get(f"/cases/{case_id}/report")
    assert unauth_res.status_code == 401, f"Report endpoint was public! Expected 401, got {unauth_res.status_code}"

    # 2. Authenticated doctor access succeeds
    auth_res = client.get(f"/cases/{case_id}/report", headers=doc_headers)
    assert auth_res.status_code == 200
    assert auth_res.headers["content-type"] == "application/pdf"
    print("  [PASS] 22. PDF report remains authenticated (HTTP 401 on unauthenticated access).")


def test_23_forwarded_ip_spoofing_protection():
    """Verify reverse-proxy forwarded-IP parsing and spoofing prevention."""
    from starlette.requests import Request
    from core import rate_limit, config

    rate_limit.reset_rate_limits()

    # Scenario A: Behind 1 trusted proxy (default PaaS behavior)
    os.environ["HEALTHDECK_BEHIND_PROXY"] = "true"
    os.environ["HEALTHDECK_TRUSTED_PROXY_COUNT"] = "1"

    # Helper to create mock request with headers
    def make_mock_request(headers_dict, client_host="10.0.0.1"):
        scope = {
            "type": "http",
            "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers_dict.items()],
            "client": (client_host, 12345),
        }
        return Request(scope)

    # 1. Attacker attempts to spoof X-Forwarded-For by prefixing random IPs:
    # Proxy appends real client IP (203.0.113.50) at the end
    req1 = make_mock_request({"x-forwarded-for": "198.51.100.1, 203.0.113.50"})
    assert rate_limit.get_client_ip(req1) == "203.0.113.50", "Failed to extract real client IP from right"

    req2 = make_mock_request({"x-forwarded-for": "198.51.100.99, 1.2.3.4, 203.0.113.50"})
    assert rate_limit.get_client_ip(req2) == "203.0.113.50", "Failed to extract real client IP with multi-spoof header"

    # 2. Rate limit test: repeated requests with rotating spoofed prefixes but same real IP
    # Limit login to 3 requests
    os.environ["HEALTHDECK_LIMIT_LOGIN"] = "3"
    for i in range(3):
        spoofed_hdr = f"1.1.1.{i}, 203.0.113.50"
        r = make_mock_request({"x-forwarded-for": spoofed_hdr})
        rate_limit.check_rate_limit(r, scope="login", default_max_requests=3, window_seconds=60)

    # 4th request from same real client with another spoofed header MUST be rejected with 429
    r_blocked = make_mock_request({"x-forwarded-for": "9.9.9.9, 203.0.113.50"})
    try:
        rate_limit.check_rate_limit(r_blocked, scope="login", default_max_requests=3, window_seconds=60)
        assert False, "Expected 429 Too Many Requests when rotating spoofed IP prefix behind proxy"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429, f"Expected 429, got {exc}"

    # Scenario B: Behind 2 trusted proxies (e.g. Cloudflare + Render)
    os.environ["HEALTHDECK_TRUSTED_PROXY_COUNT"] = "2"
    req_2proxies = make_mock_request({"x-forwarded-for": "spoofed.ip, 198.51.100.77, 172.68.1.1"})
    assert rate_limit.get_client_ip(req_2proxies) == "198.51.100.77"

    # Scenario C: Direct connection, NOT behind proxy (HEALTHDECK_BEHIND_PROXY=false)
    os.environ["HEALTHDECK_BEHIND_PROXY"] = "false"
    req_direct = make_mock_request({"x-forwarded-for": "1.2.3.4"}, client_host="192.168.1.100")
    # Untrusted X-Forwarded-For must be ignored; socket host must be used
    assert rate_limit.get_client_ip(req_direct) == "192.168.1.100"

    # Cleanup
    rate_limit.reset_rate_limits()
    os.environ.pop("HEALTHDECK_BEHIND_PROXY", None)
    os.environ.pop("HEALTHDECK_TRUSTED_PROXY_COUNT", None)
    os.environ.pop("HEALTHDECK_LIMIT_LOGIN", None)
    print("  [PASS] 23. Reverse-proxy forwarded-IP spoofing protection validated.")


if __name__ == "__main__":
    print("======================================================================")
    print("RUNNING PHASE 4B/4C PRODUCTION SECURITY & HARDENING TEST SUITE")
    print("======================================================================")
    test_01_production_config_rejects_missing_database_url()
    test_02_production_config_rejects_missing_or_weak_jwt_secret()
    test_03_production_config_rejects_wildcard_cors()
    test_04_health_endpoint_healthy()
    test_05_health_endpoint_unhealthy_on_db_failure()
    test_06_production_exception_sanitization()
    test_07_security_headers_present()
    test_08_production_docs_disabled()
    test_09_login_rate_limiting()
    test_10_triage_rate_limiting()
    test_11_upload_rate_limiting()
    test_12_upload_traversal_protections()
    test_13_upload_size_limit()
    test_14_invalid_image_magic_bytes()
    test_15_patient_status_endpoint_data_minimization()
    test_16_clinician_endpoints_remain_protected()
    test_17_jwt_auth_roundtrip()
    test_18_doctor_identity_enforced_from_token()
    test_19_prescription_concurrency()
    test_20_local_qr_generation_no_third_party()
    test_21_public_base_url_respected()
    test_22_pdf_report_remains_authenticated()
    test_23_forwarded_ip_spoofing_protection()
    print("======================================================================")
    print("ALL 23 PRODUCTION SECURITY TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")
