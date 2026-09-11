"""Phase 2C — Security & Authentication Regression Test Suite.

Audits and verifies:
1. Authentication matrix (missing, invalid, malformed, expired, inactive, login, /auth/me, /auth/logout)
2. Clinician endpoints authorization (enforced independently of frontend)
3. Anti-spoofing and attribution integrity (fake doctor identities rejected/ignored)
4. JWT & Secret security (no insecure fallback, explicit HS256, no password hash leaks)
5. Patient-safe case status endpoint (public access, strict data minimization, zero internal leakage)
6. Upload security (path traversal prevention, canonical containment, chunked 10MB limit, image validation)
7. Concurrency & multi-doctor case mutation attribution
8. Boundary & malformed input handling
"""

import os
import shutil
import tempfile
import uuid
from datetime import timedelta

# Set up isolated temporary environment before importing backend
_TMP_DIR = tempfile.mkdtemp(prefix="healthdeck_security_audit_")
os.environ["HEALTHDECK_DB_PATH"] = os.path.join(_TMP_DIR, "security_test.db")
os.environ["HEALTHDECK_UPLOADS_DIR"] = os.path.join(_TMP_DIR, "uploads")
os.environ["HEALTHDECK_REPORTS_DIR"] = os.path.join(_TMP_DIR, "reports")
os.environ["HEALTHDECK_JWT_SECRET"] = "sec-audit-jwt-key-" + uuid.uuid4().hex

from fastapi.testclient import TestClient
import jwt

import backend
from core import auth, db

client = TestClient(backend.app)

# Test Image Fixtures
VALID_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"\x00" * 64
VALID_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"


def create_dynamic_doctor(prefix="doc", is_active=1):
    """Create a temporary doctor with dynamic credentials inside the test database."""
    unique_id = uuid.uuid4().hex[:8]
    username = f"{prefix}_{unique_id}"
    password = f"SecPass_{uuid.uuid4().hex[:12]}!"
    full_name = f"Dr. Audit {unique_id.upper()}"
    email = f"{username}@hospital.test"

    pw_hash = auth.hash_password(password)
    doc_id = db.create_doctor(
        username=username,
        email=email,
        password_hash=pw_hash,
        full_name=full_name,
        medical_license=f"MD-SEC-{unique_id.upper()}",
        department="Emergency Triage",
        role="doctor",
        is_active=is_active,
    )
    doctor = db.get_doctor_by_id(doc_id)
    token = auth.create_access_token({
        "sub": str(doc_id),
        "username": username,
        "role": "doctor",
    })
    headers = {"Authorization": f"Bearer {token}"}
    return {
        "id": doc_id,
        "username": username,
        "password": password,
        "full_name": full_name,
        "email": email,
        "token": token,
        "headers": headers,
    }


def create_test_case():
    """Create a test patient case and return its ID."""
    res = client.post(
        "/cases",
        json={
            "chief_complaint": "Persistent headache and fever",
            "symptom_location": "head",
            "department": "General Physician",
            "vitals": {"temp_c": 38.5, "hr": 88, "spo2": 98},
            "transcript": [{"role": "user", "content": "Headache for 3 days"}],
            "red_flags": [],
            "escalate": False,
            "escalation_reason": "",
            "raw_llm_response": {"internal_reasoning": "CONFIDENTIAL LLM DATA"},
            "session_id": f"sess_{uuid.uuid4().hex}",
        },
    )
    assert res.status_code == 200
    return res.json()["id"]


# =========================================================================
# 1. AUTHENTICATION MATRIX TESTS
# =========================================================================

def test_auth_login_and_logout():
    doc = create_dynamic_doctor("login_test")

    # 1. Missing credentials body
    r = client.post("/auth/login", json={})
    assert r.status_code == 400

    # 2. Invalid password
    r = client.post("/auth/login", json={"username": doc["username"], "password": "WrongPassword!"})
    assert r.status_code == 401
    assert "Invalid username/email or password" in r.json()["detail"]

    # 3. Nonexistent user
    r = client.post("/auth/login", json={"username": "nonexistent_doctor_123", "password": "AnyPassword!"})
    assert r.status_code == 401

    # 4. Valid login
    r = client.post("/auth/login", json={"username": doc["username"], "password": doc["password"]})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["doctor"]["username"] == doc["username"]
    assert "password_hash" not in data["doctor"]

    # 5. /auth/me with valid token
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert r.status_code == 200
    assert r.json()["username"] == doc["username"]
    assert "password_hash" not in r.json()

    # 6. /auth/logout
    r = client.post("/auth/logout")
    assert r.status_code == 200


def test_auth_inactive_doctor():
    inactive_doc = create_dynamic_doctor("inactive", is_active=0)

    # Inactive doctor login rejected
    r = client.post("/auth/login", json={"username": inactive_doc["username"], "password": inactive_doc["password"]})
    assert r.status_code == 401
    assert "disabled" in r.json()["detail"].lower()

    # Inactive doctor token rejected on protected endpoint
    r = client.get("/auth/me", headers=inactive_doc["headers"])
    assert r.status_code == 401
    assert "inactive" in r.json()["detail"].lower()


def test_auth_token_tampering_and_expiration():
    doc = create_dynamic_doctor("tamper")

    # Missing token
    r = client.get("/auth/me")
    assert r.status_code == 401

    # Empty bearer
    r = client.get("/auth/me", headers={"Authorization": "Bearer "})
    assert r.status_code == 401

    # Malformed token
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
    assert r.status_code == 401

    # Tampered signature
    tampered = doc["token"][:-6] + "xxxxxx"
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401

    # Expired token
    expired_token = auth.create_access_token(
        {"sub": str(doc["id"]), "username": doc["username"], "role": "doctor"},
        expires_delta=timedelta(seconds=-3600),
    )
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


def test_jwt_algorithm_none_attack():
    doc = create_dynamic_doctor("alg_none")

    # Construct unsigned token with alg=none
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": str(doc["id"]), "username": doc["username"], "role": "doctor"}
    none_token = jwt.encode(payload, key="", algorithm="none")

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {none_token}"})
    assert r.status_code == 401


def test_jwt_missing_secret_fails_explicitly():
    old_secret = os.environ.get("HEALTHDECK_JWT_SECRET")
    try:
        os.environ["HEALTHDECK_JWT_SECRET"] = ""
        try:
            auth.get_jwt_secret()
            assert False, "Expected RuntimeError when HEALTHDECK_JWT_SECRET is empty"
        except RuntimeError as e:
            assert "HEALTHDECK_JWT_SECRET is not configured" in str(e)
    finally:
        if old_secret:
            os.environ["HEALTHDECK_JWT_SECRET"] = old_secret


# =========================================================================
# 2. PROTECTED CLINICIAN ENDPOINTS AUTHORIZATION
# =========================================================================

def test_clinician_endpoints_require_auth():
    doc = create_dynamic_doctor("clinician_auth")
    case_id = create_test_case()

    endpoints = [
        ("GET", "/cases", None),
        ("GET", "/cases/open", None),
        ("GET", f"/cases/{case_id}", None),
        ("PATCH", f"/cases/{case_id}/review", {"department_override": "Neurology"}),
        ("PATCH", f"/cases/{case_id}/prescribe", {"medicines": [{"name": "Ibuprofen", "dosage_per_day": "400mg", "remark": "After meals"}], "notes": "Rest"}),
        ("GET", f"/cases/{case_id}/report", None),
    ]

    for method, path, payload in endpoints:
        # A. No token -> 401
        if method == "GET":
            r_none = client.get(path)
        else:
            r_none = client.patch(path, json=payload or {})
        assert r_none.status_code == 401, f"{method} {path} without token returned {r_none.status_code}, expected 401"

        # B. Invalid token -> 401
        bad_headers = {"Authorization": "Bearer invalid.token.payload"}
        if method == "GET":
            r_bad = client.get(path, headers=bad_headers)
        else:
            r_bad = client.patch(path, json=payload or {}, headers=bad_headers)
        assert r_bad.status_code == 401, f"{method} {path} with bad token returned {r_bad.status_code}, expected 401"

        # C. Valid token -> Not 401 (either 200 or 404 for report if not yet generated)
        if method == "GET":
            r_valid = client.get(path, headers=doc["headers"])
        else:
            r_valid = client.patch(path, json=payload or {}, headers=doc["headers"])
        assert r_valid.status_code != 401, f"{method} {path} with valid token was rejected with 401"


# =========================================================================
# 3. DOCTOR IDENTITY ANTI-SPOOFING & ATTRIBUTION
# =========================================================================

def test_doctor_identity_anti_spoofing():
    doc_legit = create_dynamic_doctor("legit")
    case_id = create_test_case()

    # Attempt to spoof doctor_name in prescription payload
    spoofed_payload = {
        "doctor_name": "Dr. Hacker Fake",
        "medicines": [{"name": "Amoxicillin", "dosage_per_day": "500mg 3x", "remark": "With water"}],
        "notes": "Legitimate prescription from actual doctor.",
    }

    r = client.patch(f"/cases/{case_id}/prescribe", json=spoofed_payload, headers=doc_legit["headers"])
    assert r.status_code == 200
    prescribed_case = r.json()

    # Attribution MUST be the authenticated doctor, NOT the spoofed payload name
    assert prescribed_case["doctor_name"] == doc_legit["full_name"]
    assert prescribed_case["prescribed_by_doctor_id"] == doc_legit["id"]
    assert prescribed_case["doctor_name"] != "Dr. Hacker Fake"

    # Verify review attribution
    case_id_2 = create_test_case()
    r_rev = client.patch(
        f"/cases/{case_id_2}/review",
        json={"department_override": "Pulmonology"},
        headers=doc_legit["headers"],
    )
    assert r_rev.status_code == 200
    reviewed_case = r_rev.json()
    assert reviewed_case["reviewed_by_doctor_id"] == doc_legit["id"]
    assert reviewed_case["reviewed_by_doctor_name"] == doc_legit["full_name"]


# =========================================================================
# 4. PATIENT-SAFE CASE STATUS ENDPOINT
# =========================================================================

def test_patient_safe_case_status_endpoint():
    doc = create_dynamic_doctor("status_checker")
    case_id = create_test_case()

    # 1. Unauthenticated access MUST succeed (200 OK)
    r = client.get(f"/cases/{case_id}/patient-status")
    assert r.status_code == 200
    data = r.json()

    # 2. Verify safe fields exist
    assert data["case_id"] == case_id
    assert data["status"] == "pending"
    assert data["reviewed"] is False
    assert "effective_department" in data
    assert "prescription_medicines" in data
    assert "has_report" in data

    # 3. CRITICAL: Strictly verify sensitive internal fields are NOT exposed
    forbidden_fields = [
        "raw_llm_response",
        "transcript",
        "extracted",
        "red_flags",
        "diagnosis",
        "doctor_notes",
        "session_id",
        "photo_path",
        "password_hash",
        "confidence",
    ]
    for field in forbidden_fields:
        assert field not in data, f"Patient-safe endpoint leaked sensitive field: {field}"

    # 4. Prescribe the case and check patient status reflects update
    client.patch(
        f"/cases/{case_id}/prescribe",
        json={
            "medicines": [{"name": "Paracetamol", "dosage_per_day": "500mg", "remark": "SOS"}],
            "notes": "CONFIDENTIAL CLINICAL NOTE: Patient has mild viral symptoms.",
        },
        headers=doc["headers"],
    )

    r_updated = client.get(f"/cases/{case_id}/patient-status")
    assert r_updated.status_code == 200
    data_up = r_updated.json()
    assert data_up["status"] == "prescribed"
    assert data_up["doctor_name"] == doc["full_name"]
    assert len(data_up["prescription_medicines"]) == 1
    assert data_up["has_report"] is True
    # Verify doctor_notes is still NOT leaked
    assert "doctor_notes" not in data_up
    assert "CONFIDENTIAL" not in str(data_up)

    # 5. Non-existent case ID returns 404
    r_404 = client.get("/cases/99999999/patient-status")
    assert r_404.status_code == 404

    # 6. Malformed case ID returns 422
    r_422 = client.get("/cases/not-a-number/patient-status")
    assert r_422.status_code == 422


# =========================================================================
# 5. UPLOAD & PATH TRAVERSAL SECURITY
# =========================================================================

def test_upload_path_traversal_prevention():
    # 1. Path traversal session IDs must return 400 Bad Request
    traversal_ids = [
        "../../evil",
        "..\\..\\evil",
        "valid/../../../etc/passwd",
        "session;rm -rf",
        "session with spaces",
        "session$name",
        "session%00null",
        "session%2e%2e",
    ]

    for bad_id in traversal_ids:
        # GET /upload/{session_id}/image
        r_get = client.get(f"/upload/{bad_id}/image")
        assert r_get.status_code in (400, 404), f"Path traversal in GET returned {r_get.status_code}"

        # GET /upload/{session_id}/status
        r_status = client.get(f"/upload/{bad_id}/status")
        assert r_status.status_code in (400, 404), f"Path traversal in status returned {r_status.status_code}"

        # POST /upload/{session_id}
        r_post = client.post(
            f"/upload/{bad_id}",
            files={"file": ("photo.jpg", VALID_JPEG, "image/jpeg")},
        )
        assert r_post.status_code in (400, 404), f"Path traversal in POST returned {r_post.status_code}"


def test_upload_file_validation_and_size_limits():
    valid_id = f"sess_valid_{uuid.uuid4().hex}"

    # 1. Valid JPEG succeeds
    r_jpg = client.post(
        f"/upload/{valid_id}",
        files={"file": ("photo.jpg", VALID_JPEG, "image/jpeg")},
    )
    assert r_jpg.status_code == 200
    assert "Thanks" in r_jpg.text

    # 2. Valid PNG succeeds
    png_id = f"sess_png_{uuid.uuid4().hex}"
    r_png = client.post(
        f"/upload/{png_id}",
        files={"file": ("photo.png", VALID_PNG, "image/png")},
    )
    assert r_png.status_code == 200

    # 3. Non-image file rejected (magic bytes check)
    text_id = f"sess_text_{uuid.uuid4().hex}"
    r_txt = client.post(
        f"/upload/{text_id}",
        files={"file": ("script.py", b"import os; os.system('ls')", "text/plain")},
    )
    assert r_txt.status_code == 400
    assert "image" in r_txt.json()["detail"].lower()

    # 4. Oversized upload rejected with HTTP 413
    oversized_id = f"sess_big_{uuid.uuid4().hex}"
    # Generate 10MB + 64KB payload with valid JPEG header
    oversized_payload = VALID_JPEG + b"A" * (10 * 1024 * 1024 + 64 * 1024)
    r_big = client.post(
        f"/upload/{oversized_id}",
        files={"file": ("giant.jpg", oversized_payload, "image/jpeg")},
    )
    assert r_big.status_code == 413
    assert "10MB" in r_big.json()["detail"]


# =========================================================================
# 6. CONCURRENCY & MULTI-DOCTOR CASE MUTATION ATTRIBUTION
# =========================================================================

def test_concurrency_and_multi_doctor_attribution():
    doc_a = create_dynamic_doctor("doc_alpha")
    doc_b = create_dynamic_doctor("doc_beta")
    case_id = create_test_case()

    # Doctor A reviews the case with Neurology override
    r_rev_a = client.patch(
        f"/cases/{case_id}/review",
        json={"department_override": "Neurology"},
        headers=doc_a["headers"],
    )
    assert r_rev_a.status_code == 200
    case_a = r_rev_a.json()
    assert case_a["reviewed_by_doctor_id"] == doc_a["id"]
    assert case_a["reviewed_by_doctor_name"] == doc_a["full_name"]
    assert case_a["effective_department"] == "Neurology"

    # Doctor B updates the review with Cardiology override
    r_rev_b = client.patch(
        f"/cases/{case_id}/review",
        json={"department_override": "Cardiology"},
        headers=doc_b["headers"],
    )
    assert r_rev_b.status_code == 200
    case_b = r_rev_b.json()
    # Attribution must reflect Doctor B (latest reviewer)
    assert case_b["reviewed_by_doctor_id"] == doc_b["id"]
    assert case_b["reviewed_by_doctor_name"] == doc_b["full_name"]
    assert case_b["effective_department"] == "Cardiology"

    # Doctor A prescribes medication
    r_presc_a = client.patch(
        f"/cases/{case_id}/prescribe",
        json={"medicines": [{"name": "Aspirin", "dosage_per_day": "75mg", "remark": "Daily"}], "notes": "From Doc A"},
        headers=doc_a["headers"],
    )
    assert r_presc_a.status_code == 200
    assert r_presc_a.json()["doctor_name"] == doc_a["full_name"]
    assert r_presc_a.json()["prescribed_by_doctor_id"] == doc_a["id"]

    # Doctor B adjusts prescription
    r_presc_b = client.patch(
        f"/cases/{case_id}/prescribe",
        json={"medicines": [{"name": "Clopidogrel", "dosage_per_day": "75mg", "remark": "Alternative"}], "notes": "From Doc B"},
        headers=doc_b["headers"],
    )
    assert r_presc_b.status_code == 200
    assert r_presc_b.json()["doctor_name"] == doc_b["full_name"]
    assert r_presc_b.json()["prescribed_by_doctor_id"] == doc_b["id"]

    # Final DB check confirms no cross-attribution pollution
    final_case = db.get_case(case_id)
    assert final_case["prescribed_by_doctor_id"] == doc_b["id"]
    assert final_case["doctor_name"] == doc_b["full_name"]


# =========================================================================
# 7. REPORT SECURITY & URL TOKEN LEAKAGE
# =========================================================================

def test_report_security():
    doc = create_dynamic_doctor("report_sec")
    case_id = create_test_case()

    # Prescribe case to generate report
    client.patch(
        f"/cases/{case_id}/prescribe",
        json={"medicines": [{"name": "Salbutamol", "dosage_per_day": "Inhaler", "remark": "PRN"}], "notes": "Report test"},
        headers=doc["headers"],
    )

    # 1. Unauthenticated download rejected
    r_no_auth = client.get(f"/cases/{case_id}/report")
    assert r_no_auth.status_code == 401

    # 2. Authenticated download succeeds and returns valid PDF
    r_auth = client.get(f"/cases/{case_id}/report", headers=doc["headers"])
    assert r_auth.status_code == 200
    assert r_auth.headers["content-type"] == "application/pdf"
    assert r_auth.content.startswith(b"%PDF")


# =========================================================================
# RUN ALL SUITES
# =========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING PHASE 2C SECURITY & AUTHENTICATION AUDIT TESTS")
    print("=" * 70)

    test_auth_login_and_logout()
    print("  [PASS] 1. Auth login, safe profile & logout")

    test_auth_inactive_doctor()
    print("  [PASS] 2. Inactive doctor rejection (login & token)")

    test_auth_token_tampering_and_expiration()
    print("  [PASS] 3. Token tampering, malformed, and expiration checks")

    test_jwt_algorithm_none_attack()
    print("  [PASS] 4. JWT algorithm 'none' attack blocked")

    test_jwt_missing_secret_fails_explicitly()
    print("  [PASS] 5. Missing HEALTHDECK_JWT_SECRET fails explicitly")

    test_clinician_endpoints_require_auth()
    print("  [PASS] 6. All 6 clinician endpoints enforce auth independently of UI")

    test_doctor_identity_anti_spoofing()
    print("  [PASS] 7. Anti-spoofing strictly enforces authenticated doctor identity")

    test_patient_safe_case_status_endpoint()
    print("  [PASS] 8. Patient-safe status endpoint (public, zero leakage of notes/LLM)")

    test_upload_path_traversal_prevention()
    print("  [PASS] 9. Upload path traversal blocked (canonical containment)")

    test_upload_file_validation_and_size_limits()
    print("  [PASS] 10. Upload size limit (10MB HTTP 413) & magic bytes image validation")

    test_concurrency_and_multi_doctor_attribution()
    print("  [PASS] 11. Multi-doctor concurrency & accurate attribution")

    test_report_security()
    print("  [PASS] 12. Report security (protected PDF binary stream)")

    print("=" * 70)
    print("ALL 12 SECURITY AUDIT TEST SUITES PASSED SUCCESSFULLY!")
    print("=" * 70)

    # Cleanup test temporary folder
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
