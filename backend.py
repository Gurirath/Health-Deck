"""FastAPI wrapper around db.py.

Run it with: uvicorn backend:app --reload

It owns the SQLite database and the uploads/ and reports/ directories. The
kiosk (app.py) and the clinician dashboard talk to these endpoints over
HTTP instead of importing db.py directly.

Every completed case is created with status "pending" and stays in the
dashboard queue until a doctor prescribes for it. POST /vitals is a landing
pad for the hardware team; nothing consumes it yet.
"""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

import alerts
import db

UPLOADS_DIR = os.path.abspath(os.environ.get("HEALTHDECK_UPLOADS_DIR", "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)

db.init_db()

app = FastAPI(title="Health Deck API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": origin if origin else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


class CasePayload(BaseModel):
    vitals: Dict[str, Any] = Field(default_factory=dict)
    chief_complaint: str = ""
    symptom_location: str = ""
    transcript: List[Dict[str, Any]] = Field(default_factory=list)
    extracted: Dict[str, Any] = Field(default_factory=dict)
    red_flags: List[str] = Field(default_factory=list)
    diagnosis: Dict[str, Any] = Field(default_factory=dict)
    raw_llm_response: Dict[str, Any] = Field(default_factory=dict)
    escalate: bool = False
    escalation_reason: str = ""
    department: str = ""
    solution_sources: List[str] = Field(default_factory=list)
    image_analysis: Optional[Dict[str, Any]] = None
    session_id: str = ""


class ReviewPatch(BaseModel):
    department_override: Optional[str] = None


class Medicine(BaseModel):
    name: str = ""
    dosage_per_day: str = ""
    remark: str = ""


class PrescribePatch(BaseModel):
    doctor_name: str
    medicines: List[Medicine] = Field(default_factory=list)
    notes: str = ""


class VitalsReading(BaseModel):
    device_id: str
    spo2: float
    temp_c: float
    hr: float
    systolic_bp: float
    diastolic_bp: float
    timestamp: str


def _upload_path(session_id):
    return os.path.join(UPLOADS_DIR, f"{session_id}.jpg")


UPLOAD_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Health Deck - send a photo</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; padding: 24px; background: #f4f6f8; }}
.card {{ max-width: 420px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 24px; }}
h1 {{ font-size: 1.3rem; }}
input[type=file] {{ display: block; width: 100%; margin: 16px 0; font-size: 1rem; }}
button {{ width: 100%; padding: 14px; font-size: 1.1rem; border: 0; border-radius: 12px; background: #1a73e8; color: #fff; }}
</style>
</head>
<body>
<div class="card">
<h1>Send a photo of the problem</h1>
<p>Take or choose one photo. It is attached to your kiosk session.</p>
<form method="post" action="/upload/{session_id}" enctype="multipart/form-data">
<input type="file" name="file" accept="image/*" capture="environment" required>
<button type="submit">Send photo</button>
</form>
</div>
</body>
</html>
"""

CONFIRM_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Health Deck - photo received</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; padding: 24px; background: #f4f6f8; }}
.card {{ max-width: 420px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 24px; text-align: center; }}
</style>
</head>
<body>
<div class="card">
<h1>Thanks</h1>
<p>Your photo has been received. You can go back to the kiosk and continue.</p>
</div>
</body>
</html>
"""


@app.get("/")
def root():
    return {"service": "health-deck", "ok": True}


@app.get("/upload/{session_id}", response_class=HTMLResponse)
def upload_page(session_id: str):
    return UPLOAD_PAGE.format(session_id=session_id)


@app.post("/upload/{session_id}", response_class=HTMLResponse)
def upload_photo(session_id: str, file: UploadFile = File(...)):
    path = _upload_path(session_id)
    with open(path, "wb") as handle:
        handle.write(file.file.read())
    db.save_session_upload(session_id, path)
    return CONFIRM_PAGE.format(session_id=session_id)


@app.get("/upload/{session_id}/status")
def upload_status(session_id: str):
    return {"uploaded": os.path.exists(_upload_path(session_id))}


@app.get("/upload/{session_id}/image")
def upload_image(session_id: str):
    path = _upload_path(session_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="no photo for this session")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/cases")
def create_case(payload: CasePayload):
    data = payload.model_dump()
    case_id = db.save_case(data)
    if data.get("escalation_reason") == "red_flag":
        alerts.send_critical_alert(db.get_case(case_id) or {**data, "id": case_id})
    return {"id": case_id}


@app.get("/cases/open")
def open_cases():
    return db.list_open_cases()


@app.get("/cases/{case_id}")
def read_case(case_id: int):
    case = db.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    return case


@app.patch("/cases/{case_id}/review")
def review_case(case_id: int, patch: ReviewPatch):
    if db.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="case not found")
    db.mark_reviewed(case_id, patch.department_override)
    return db.get_case(case_id)


@app.patch("/cases/{case_id}/prescribe")
def prescribe(case_id: int, patch: PrescribePatch):
    if db.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="case not found")
    medicines = [medicine.model_dump() for medicine in patch.medicines]
    return db.prescribe_case(case_id, patch.doctor_name, medicines, patch.notes)


@app.get("/cases/{case_id}/report")
def case_report(case_id: int):
    case = db.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    path = case.get("report_pdf_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="not yet prescribed")
    return FileResponse(
        path, media_type="application/pdf", filename=f"health_deck_case_{case_id}.pdf"
    )


@app.post("/vitals")
def ingest_vitals(reading: VitalsReading):
    reading_id = db.save_raw_vitals(reading.model_dump())
    return {"id": reading_id}


class TriageStartRequest(BaseModel):
    vitals: Dict[str, Any] = Field(default_factory=dict)
    symptom_location: str = ""
    chief_complaint: str = ""
    session_id: str = ""


class TriageStepRequest(BaseModel):
    state: Dict[str, Any]
    answer: str


@app.post("/triage/start")
def triage_start(req: TriageStartRequest):
    import agent_graph

    try:
        graph = agent_graph.build_graph()
        initial_state = {
            "vitals": req.vitals,
            "chief_complaint": req.chief_complaint,
            "symptom_location": req.symptom_location,
            "transcript": [{"role": "user", "content": req.chief_complaint}],
            "extracted": {},
            "turn_count": 0,
            "ready_to_diagnose": False,
            "red_flags": [],
            "next_question": "",
            "diagnosis": {},
            "raw_llm_response": {},
            "escalate": False,
            "escalation_reason": "",
            "department": "",
            "solution_sources": [],
            "image_bytes": None,
            "image_analysis": None,
            "status": "",
            "session_id": req.session_id,
        }
        if req.session_id:
            path = _upload_path(req.session_id)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    initial_state["image_bytes"] = f.read()

        result = graph.invoke(initial_state)
        result_copy = dict(result)
        result_copy.pop("image_bytes", None)
        result_copy["session_id"] = req.session_id
        return result_copy
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/triage/step")
def triage_step(req: TriageStepRequest):
    import agent_graph

    try:
        graph = agent_graph.build_graph()
        state = dict(req.state)
        if state.get("next_question"):
            state.setdefault("transcript", []).append(
                {"role": "assistant", "content": state["next_question"]}
            )
        state.setdefault("transcript", []).append({"role": "user", "content": req.answer})
        session_id = state.get("session_id", "")
        if session_id:
            path = _upload_path(session_id)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    state["image_bytes"] = f.read()

        result = graph.invoke(state)
        result_copy = dict(result)
        result_copy.pop("image_bytes", None)
        result_copy["session_id"] = session_id
        return result_copy
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/triage/transcribe")
def triage_transcribe(file: UploadFile = File(...)):
    import stt_client

    try:
        audio_bytes = file.file.read()
        if not audio_bytes:
            return {"text": ""}
        text = stt_client.transcribe(audio_bytes)
        return {"text": (text or "").strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

