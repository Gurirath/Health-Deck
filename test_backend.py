import os
import shutil
import tempfile

_TMP = tempfile.mkdtemp(prefix="healthdeck_test_")
os.environ["HEALTHDECK_DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["HEALTHDECK_UPLOADS_DIR"] = os.path.join(_TMP, "uploads")
os.environ["HEALTHDECK_REPORTS_DIR"] = os.path.join(_TMP, "reports")

from fastapi.testclient import TestClient

import backend

client = TestClient(backend.app)

FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"fake jpeg payload" * 8


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
    case = client.get(f"/cases/{with_photo}").json()
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
    assert client.get(f"/cases/{no_photo}").json()["photo_path"] in (None, "")
    print("case stores photo_path from session_uploads OK")


def test_prescribe_and_report():
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

    assert client.get(f"/cases/{case_id}/report").status_code == 404

    prescribed = client.patch(
        f"/cases/{case_id}/prescribe",
        json={
            "doctor_name": "Dr. Rao",
            "medicines": [
                {"name": "Cetirizine", "dosage_per_day": "1 tablet", "remark": "at night, 5 days"},
                {"name": "Hydrocortisone 1%", "dosage_per_day": "2 applications", "remark": "thin layer"},
            ],
            "notes": "return if it spreads or blisters",
        },
    )
    assert prescribed.status_code == 200
    body = prescribed.json()
    assert body["status"] == "prescribed"
    assert body["doctor_name"] == "Dr. Rao"
    assert body["prescription_medicines"][0] == {
        "name": "Cetirizine",
        "dosage_per_day": "1 tablet",
        "remark": "at night, 5 days",
    }
    assert set(body["prescription_medicines"][1]) == {"name", "dosage_per_day", "remark"}
    assert body["report_pdf_path"] and os.path.exists(body["report_pdf_path"])

    report = client.get(f"/cases/{case_id}/report")
    assert report.status_code == 200
    assert report.content[:4] == b"%PDF"

    open_ids = [c["id"] for c in client.get("/cases/open").json()]
    assert case_id not in open_ids

    missing = client.patch(
        "/cases/99999/prescribe", json={"doctor_name": "Dr. X"}
    )
    assert missing.status_code == 404
    print("prescribe + report OK")


def test_old_shape_medicines_normalised():
    from core import db

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
    )
    medicines = client.get(f"/cases/{case_id}").json()["prescription_medicines"]
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


if __name__ == "__main__":
    try:
        test_upload_page_renders()
        test_upload_roundtrip()
        test_case_stores_photo_path()
        test_prescribe_and_report()
        test_old_shape_medicines_normalised()
        test_report_pdf_layout_and_missing_logo()
        print("all backend tests passed")
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
