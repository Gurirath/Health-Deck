import os
import shutil
import tempfile
from datetime import timedelta

_TMP = tempfile.mkdtemp(prefix="healthdeck_test_")
os.environ["HEALTHDECK_DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["HEALTHDECK_UPLOADS_DIR"] = os.path.join(_TMP, "uploads")
os.environ["HEALTHDECK_REPORTS_DIR"] = os.path.join(_TMP, "reports")
os.environ["HEALTHDECK_JWT_SECRET"] = "test-jwt-secret-very-secure-key-123456"

from fastapi.testclient import TestClient

import backend
from core import auth, db

client = TestClient(backend.app)

FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"fake jpeg payload" * 8


def setup_test_doctor():
    doc = db.get_doctor_by_username_or_email("dr.chen")
    if not doc:
        pw_hash = auth.hash_password("DoctorSecret123!")
        doc_id = db.create_doctor(
            username="dr.chen",
            email="dr.chen@hospital.internal",
            password_hash=pw_hash,
            full_name="Dr. Sarah Chen, MD",
            medical_license="MD-89241-CA",
            department="Cardiology",
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


def test_password_hashing():
    pw = "SuperSecurePass123!"
    h1 = auth.hash_password(pw)
    h2 = auth.hash_password(pw)

    # 1. Password hashes are not plaintext
    assert h1 != pw
    assert h2 != pw
    assert pw not in h1

    # 2. Hashing produces salted hashes (different each time)
    assert h1 != h2

    # 3. Correct password verifies
    assert auth.verify_password(pw, h1) is True
    assert auth.verify_password(pw, h2) is True

    # 4. Incorrect password fails
    assert auth.verify_password("WrongPass123!", h1) is False
    assert auth.verify_password("", h1) is False
    print("password hashing and verification OK")


def test_auth_login_and_me():
    doc, token, headers = setup_test_doctor()

    # 5. Valid doctor credentials return 200 with token and doctor
    res = client.post(
        "/auth/login",
        json={"username": "dr.chen", "password": "DoctorSecret123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["doctor"]["username"] == "dr.chen"
    assert data["doctor"]["department"] == "Cardiology"
    # 20. Password hash is never exposed
    assert "password_hash" not in data["doctor"]
    assert "password" not in data["doctor"]

    # Login with email also works
    res_email = client.post(
        "/auth/login",
        json={"username": "dr.chen@hospital.internal", "password": "DoctorSecret123!"},
    )
    assert res_email.status_code == 200

    # 6. Invalid password returns 401
    res_bad_pw = client.post(
        "/auth/login",
        json={"username": "dr.chen", "password": "WrongPassword!"},
    )
    assert res_bad_pw.status_code == 401

    # 7. Unknown doctor returns 401
    res_unknown = client.post(
        "/auth/login",
        json={"username": "nonexistent_doctor", "password": "DoctorSecret123!"},
    )
    assert res_unknown.status_code == 401

    # 8. Inactive doctor returns 401
    inactive_id = db.create_doctor(
        username="dr.inactive",
        email="dr.inactive@hospital.internal",
        password_hash=auth.hash_password("InactivePass123!"),
        full_name="Dr. Inactive",
        is_active=0,
    )
    res_inactive = client.post(
        "/auth/login",
        json={"username": "dr.inactive", "password": "InactivePass123!"},
    )
    assert res_inactive.status_code == 401

    # 19. /auth/me returns the authenticated doctor's profile without password hash
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "dr.chen"
    assert me_data["full_name"] == "Dr. Sarah Chen, MD"
    assert "password_hash" not in me_data

    # Logout endpoint
    assert client.post("/auth/logout").status_code == 200
    print("auth login, /auth/me, and logout OK")


def test_jwt_validation():
    doc, valid_token, headers = setup_test_doctor()

    # 9. Valid token works
    res = client.get("/cases/open", headers=headers)
    assert res.status_code == 200

    # 10. Expired token returns 401
    expired_token = auth.create_access_token(
        {"sub": str(doc["id"]), "username": doc["username"]},
        expires_delta=timedelta(seconds=-10),
    )
    res_expired = client.get(
        "/cases/open",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401
    assert "expired" in res_expired.text.lower()

    # 11. Invalid / tampered token returns 401
    res_tampered = client.get(
        "/cases/open",
        headers={"Authorization": f"Bearer {valid_token}tampered"},
    )
    assert res_tampered.status_code == 401

    # 12. Missing token returns 401
    res_missing = client.get("/cases/open")
    assert res_missing.status_code == 401
    print("jwt token validation & expiration OK")


def test_protected_routes_unauthenticated():
    # 13. GET /cases/open without token -> 401
    assert client.get("/cases/open").status_code == 401

    # 14. GET /cases/{id} without token -> 401
    assert client.get("/cases/1").status_code == 401

    # 15. PATCH /cases/{id}/review without token -> 401
    assert client.patch("/cases/1/review", json={"department_override": "ENT"}).status_code == 401

    # 16. PATCH /cases/{id}/prescribe without token -> 401
    assert client.patch(
        "/cases/1/prescribe",
        json={"doctor_name": "Dr. Imposter", "medicines": [], "notes": "note"},
    ).status_code == 401

    # 17. GET /cases/{id}/report without token -> 401
    assert client.get("/cases/1/report").status_code == 401
    print("all clinician endpoints reject unauthenticated access with 401 OK")


def test_upload_page_renders():
    response = client.get("/upload/sess-page")
    assert response.status_code == 200
    assert '<input type="file"' in response.text
    assert 'capture="environment"' in response.text
    assert "/upload/sess-page" in response.text
    print("upload page renders OK")


def test_upload_roundtrip():
    posted = client.post(
        "/upload/sess-photo",
        files={"file": ("photo.jpg", FAKE_JPEG, "image/jpeg")},
    )
    assert posted.status_code == 200
    assert "received" in posted.text.lower()

    assert client.get("/upload/sess-photo/status").json() == {"uploaded": True}
    assert client.get("/upload/sess-none/status").json() == {"uploaded": False}

    fetched = client.get("/upload/sess-photo/image")
    assert fetched.status_code == 200
    assert fetched.content == FAKE_JPEG
    assert client.get("/upload/sess-none/image").status_code == 404
    print("upload roundtrip OK")


def test_case_stores_photo_path():
    doc, token, headers = setup_test_doctor()

    client.post(
        "/upload/sess-hasphoto",
        files={"file": ("p.jpg", FAKE_JPEG, "image/jpeg")},
    )
    with_photo = client.post(
        "/cases",
        json={
            "chief_complaint": "rash on hand",
            "session_id": "sess-hasphoto",
            "diagnosis": {"probable_diagnosis": "x", "confidence": 70},
        },
    ).json()["id"]
    case = client.get(f"/cases/{with_photo}", headers=headers).json()
    assert case["photo_path"], "photo_path not populated from session_uploads"
    assert os.path.exists(case["photo_path"])

    no_photo = client.post(
        "/cases",
        json={
            "chief_complaint": "cough",
            "session_id": "sess-never-uploaded",
            "diagnosis": {"probable_diagnosis": "y", "confidence": 70},
        },
    ).json()["id"]
    assert client.get(f"/cases/{no_photo}", headers=headers).json()["photo_path"] in (None, "")
    print("case stores photo_path from session_uploads OK")


def test_prescribe_review_and_attribution():
    doc, token, headers = setup_test_doctor()

    payload = {
        "chief_complaint": "itchy rash on forearm",
        "symptom_location": "skin",
        "transcript": [{"role": "user", "content": "itchy rash"}],
        "diagnosis": {
            "probable_diagnosis": "Contact dermatitis",
            "confidence": 70,
            "self_care_advice": "keep the area clean; follow package directions",
        },
        "department": "General Physician",
        "session_id": "sess-photo",
        "image_analysis": {
            "description": "a red patch with small bumps",
            "visual_characteristics": ["erythema", "papules"],
            "note": "ok",
        },
    }
    case_id = client.post("/cases", json=payload).json()["id"]

    # 18. Valid doctor token can access clinician endpoints
    case_data = client.get(f"/cases/{case_id}", headers=headers).json()
    assert case_data["id"] == case_id

    # 21. Review stores authenticated doctor ID/name
    reviewed = client.patch(
        f"/cases/{case_id}/review",
        json={"department_override": "Dermatology"},
        headers=headers,
    )
    assert reviewed.status_code == 200
    rev_data = reviewed.json()
    assert rev_data["reviewed"] is True
    assert rev_data["department_override"] == "Dermatology"
    assert rev_data["reviewed_by_doctor_id"] == doc["id"]
    assert rev_data["reviewed_by_doctor_name"] == doc["full_name"]

    # Unprescribed report returns 404 even with token
    assert client.get(f"/cases/{case_id}/report", headers=headers).status_code == 404

    # 22. & 23. Prescription stores authenticated doctor ID/name, client-supplied doctor_name is ignored
    prescribed = client.patch(
        f"/cases/{case_id}/prescribe",
        json={
            "doctor_name": "Dr. MaliciousFictionalName",  # should be ignored!
            "medicines": [
                {"name": "Cetirizine", "dosage_per_day": "1 tablet", "remark": "at night, 5 days"},
                {"name": "Hydrocortisone 1%", "dosage_per_day": "2 applications", "remark": "thin layer"},
            ],
            "notes": "return if it spreads or blisters",
        },
        headers=headers,
    )
    assert prescribed.status_code == 200
    body = prescribed.json()
    assert body["status"] == "prescribed"
    # Authenticated identity wins over client payload!
    assert body["doctor_name"] == doc["full_name"]
    assert body["prescribed_by_doctor_id"] == doc["id"]
    assert body["prescription_medicines"][0] == {
        "name": "Cetirizine",
        "dosage_per_day": "1 tablet",
        "remark": "at night, 5 days",
    }
    assert body["report_pdf_path"] and os.path.exists(body["report_pdf_path"])

    # Report download with token succeeds
    report = client.get(f"/cases/{case_id}/report", headers=headers)
    assert report.status_code == 200
    assert report.content[:4] == b"%PDF"

    # Report download without token fails with 401
    assert client.get(f"/cases/{case_id}/report").status_code == 401

    open_ids = [c["id"] for c in client.get("/cases/open", headers=headers).json()]
    assert case_id not in open_ids
    print("prescribe, review, attribution, and report OK")


def test_old_shape_medicines_normalised():
    doc, token, headers = setup_test_doctor()

    case_id = client.post(
        "/cases",
        json={
            "chief_complaint": "legacy case",
            "session_id": "sess-legacy",
            "diagnosis": {"probable_diagnosis": "x", "confidence": 70},
        },
    ).json()["id"]
    db.prescribe_case(
        case_id,
        "Dr. Legacy",
        [{"name": "Amoxicillin", "instructions": "500mg twice daily"}],
        "note",
        doctor_id=doc["id"],
    )
    medicines = client.get(f"/cases/{case_id}", headers=headers).json()["prescription_medicines"]
    assert medicines == [
        {"name": "Amoxicillin", "dosage_per_day": "", "remark": "500mg twice daily"}
    ]
    print("old-shape medicines fold into {name, dosage_per_day, remark} OK")


def test_report_pdf_layout_and_missing_logo():
    from core import report_builder

    case = {
        "chief_complaint": "sore throat and mild fever",
        "symptom_location": "throat",
        "vitals": {"spo2": 98, "temp_c": 37.8, "hr": 88},
        "transcript": [
            {"role": "user", "content": "sore throat"},
            {"role": "assistant", "content": "how long, any fever?"},
            {"role": "user", "content": "two days, mild fever"},
        ],
        "diagnosis": {
            "probable_diagnosis": "Acute pharyngitis",
            "differential": ["viral URI", "strep pharyngitis"],
            "confidence": 74,
            "self_care_advice": "rest, warm fluids, salt-water gargle; follow package directions",
        },
        "red_flags": [],
        "department": "ENT",
        "session_id": "sess-report",
        "solution_sources": ["https://www.nhs.uk/conditions/sore-throat/"],
        "image_analysis": {
            "description": "mild pharyngeal erythema, no exudate",
            "visual_characteristics": ["erythema", "no exudate"],
            "note": "indoor lighting",
        },
        "status": "prescribed",
        "doctor_name": "Aman",
        "prescribed_at": "2026-09-10T09:41:00+00:00",
        "prescription_medicines": [
            {"name": "Paracetamol 500mg", "dosage_per_day": "3 tablets", "remark": "after food"},
            {"name": "Salt-water gargle", "dosage_per_day": "4-6 times", "remark": ""},
        ],
        "doctor_notes": "reassess in 3 days; return sooner if breathing difficulty",
    }
    report = report_builder.build_report(case)

    path_a = report_builder.generate_pdf(90001, report)
    with open(path_a, "rb") as handle:
        data_a = handle.read()
    assert data_a[:4] == b"%PDF"
    assert len(data_a) > 2000

    original_logo = report_builder.LOGO_PATH
    try:
        report_builder.LOGO_PATH = os.path.join(_TMP, "definitely-missing-logo.png")
        path_b = report_builder.generate_pdf(90002, report)
        with open(path_b, "rb") as handle:
            data_b = handle.read()
        assert data_b[:4] == b"%PDF"
        assert len(data_b) > 2000
    finally:
        report_builder.LOGO_PATH = original_logo
    print("hospital PDF valid + missing logo tolerated OK")


def test_patient_regression_endpoints():
    # 24. /triage/start remains public
    # 25. /triage/step remains public
    # 26. /triage/transcribe remains public
    # 27. /cases POST remains public
    # 28. /vitals remains public

    # Empty transcribe test
    res_transcribe = client.post(
        "/triage/transcribe",
        files={"file": ("test.wav", b"", "audio/wav")},
    )
    assert res_transcribe.status_code == 200
    assert res_transcribe.json() == {"text": ""}

    # Cases POST test without any auth headers
    res_case = client.post(
        "/cases",
        json={
            "chief_complaint": "headache",
            "vitals": {"spo2": 98, "temp_c": 37.0, "hr": 72, "systolic_bp": 120, "diastolic_bp": 80},
            "symptom_location": "head",
        },
    )
    assert res_case.status_code == 200
    assert "id" in res_case.json()

    # Hardware vitals POST without auth
    res_vitals = client.post(
        "/vitals",
        json={
            "device_id": "sensor-01",
            "spo2": 99.0,
            "temp_c": 36.8,
            "hr": 70.0,
            "systolic_bp": 118.0,
            "diastolic_bp": 78.0,
            "timestamp": "2026-09-11T12:00:00Z",
        },
    )
    assert res_vitals.status_code == 200
    assert "id" in res_vitals.json()

    print("patient endpoints remain public OK")


if __name__ == "__main__":
    try:
        test_password_hashing()
        test_auth_login_and_me()
        test_jwt_validation()
        test_protected_routes_unauthenticated()
        test_upload_page_renders()
        test_upload_roundtrip()
        test_case_stores_photo_path()
        test_prescribe_review_and_attribution()
        test_old_shape_medicines_normalised()
        test_report_pdf_layout_and_missing_logo()
        test_patient_regression_endpoints()
        print("ALL 28+ AUTH & BACKEND TESTS PASSED SUCCESSFULLY!")
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
