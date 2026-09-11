"""FastAPI wrapper around db.py.

Run it with: uvicorn backend:app --reload

It owns the SQLite database and the uploads/ and reports/ directories. The
kiosk (app.py) and the clinician dashboard talk to these endpoints over
HTTP instead of importing db.py directly.

Every completed case is created with status "pending" and stays in the
dashboard queue until a doctor prescribes for it. POST /vitals is a landing
pad for the hardware team; nothing consumes it yet.
"""

import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from core import alerts, auth, config, db
from core.auth import get_current_doctor
from core.rate_limit import rate_limit

logger = logging.getLogger("healthdeck.backend")

UPLOADS_DIR = os.path.abspath(config.get_uploads_dir())
REPORTS_DIR = os.path.abspath(config.get_reports_dir())
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Initialize database
db.init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager validating production configuration and running migrations."""
    if config.is_production():
        config.ensure_production_ready()
    db.init_db()
    yield


# Restrict Swagger/OpenAPI docs in production to prevent schema harvesting
app = FastAPI(
    title="Health Deck API",
    version="1.0.0",
    docs_url="/docs" if not config.is_production() else None,
    redoc_url="/redoc" if not config.is_production() else None,
    openapi_url="/openapi.json" if not config.is_production() else None,
    lifespan=lifespan,
)

# CORS Configuration:
# In development, allows broad origins to permit local network testing from mobile devices (QR uploads).
# In production, uses strictly configured explicit origins and disallows wildcard '*'.
allowed_origins = config.get_allowed_origins()
if not allowed_origins and not config.is_production():
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject modern production security headers into all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Enforce HSTS only in production mode or when running over HTTPS
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if config.is_production() or proto == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Sanitized global exception handler to prevent internal info leakage in production."""
    logger.error(
        "Unhandled exception processing %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )

    if config.is_production():
        detail = "An internal server error occurred. Please contact hospital technical support."
    else:
        detail = str(exc)

    origin = request.headers.get("origin", "")
    origins_list = config.get_allowed_origins()
    if "*" in origins_list or not config.is_production():
        cors_origin = origin if origin else "*"
    elif origin in origins_list:
        cors_origin = origin
    else:
        cors_origin = origins_list[0] if origins_list else ""

    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    if cors_origin:
        headers["Access-Control-Allow-Origin"] = cors_origin

    return JSONResponse(
        status_code=500,
        content={"detail": detail},
        headers=headers,
    )


@app.get("/health")
def health_check():
    """Sanitized database liveness and readiness probe.
    
    Returns 200 {'status': 'healthy'} when database is responsive.
    Returns 503 {'status': 'unhealthy'} if database is unreachable.
    Never exposes internal hosts, paths, credentials, or stack traces.
    """
    is_healthy = db.check_health()
    if not is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "detail": "Database connectivity check failed"},
        )
    return {"status": "healthy"}


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


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
    doctor_name: Optional[str] = None
    medicines: List[Medicine] = Field(default_factory=list)
    notes: str = ""
    only_if_unprescribed: bool = False


class VitalsReading(BaseModel):
    device_id: str
    spo2: float
    temp_c: float
    hr: float
    systolic_bp: float
    diastolic_bp: float
    timestamp: str


SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def _upload_path(session_id: str) -> str:
    if not session_id or not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")

    target = os.path.join(UPLOADS_DIR, f"{session_id}.jpg")
    canonical_target = os.path.realpath(target)
    canonical_base = os.path.realpath(UPLOADS_DIR)

    try:
        common = os.path.commonpath([canonical_target, canonical_base])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session path")

    if common != canonical_base:
        raise HTTPException(status_code=400, detail="Invalid session path")

    return canonical_target


def _is_valid_image(header: bytes) -> bool:
    if len(header) < 12:
        return False
    if header.startswith(b"\xff\xd8\xff"):
        return True
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return True
    return False


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


@app.post(
    "/upload/{session_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(rate_limit("upload", max_requests=10, window_seconds=60))],
)
async def upload_photo(session_id: str, file: UploadFile = File(...)):
    path = _upload_path(session_id)

    content_type = (file.content_type or "").lower()
    if content_type and not (content_type.startswith("image/") or content_type == "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image (JPEG, PNG, or WebP)",
        )

    total_bytes = 0
    header_bytes = bytearray()
    chunk_size = 64 * 1024

    with open(path, "wb") as handle:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE:
                handle.close()
                if os.path.exists(path):
                    os.remove(path)
                raise HTTPException(
                    status_code=413,
                    detail="File exceeds maximum size of 10MB",
                )
            if len(header_bytes) < 16:
                header_bytes.extend(chunk[: 16 - len(header_bytes)])
            handle.write(chunk)

    if total_bytes == 0:
        if os.path.exists(path):
            os.remove(path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if not _is_valid_image(bytes(header_bytes)):
        if os.path.exists(path):
            os.remove(path)
        raise HTTPException(
            status_code=400,
            detail="File content does not match a supported image format (JPEG, PNG, WebP)",
        )

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


@app.post("/auth/login", dependencies=[Depends(rate_limit("login", max_requests=5, window_seconds=60))])
def auth_login(req: LoginRequest):
    username_or_email = req.username.strip()
    if not username_or_email or not req.password:
        raise HTTPException(
            status_code=400,
            detail="Username/email and password are required",
        )

    doctor = db.get_doctor_by_username_or_email(username_or_email, include_password_hash=True)
    if not doctor or not auth.verify_password(req.password, doctor.get("password_hash", "")):
        raise HTTPException(
            status_code=401,
            detail="Invalid username/email or password",
        )

    if not doctor.get("is_active"):
        raise HTTPException(
            status_code=401,
            detail="Doctor account is disabled",
        )

    db.update_doctor_last_login(doctor["id"])
    token = auth.create_access_token({
        "sub": str(doctor["id"]),
        "username": doctor["username"],
        "role": doctor.get("role", "doctor"),
    })

    safe_doctor = db.get_doctor_by_id(doctor["id"], include_password_hash=False)
    return {
        "access_token": token,
        "token_type": "bearer",
        "doctor": safe_doctor,
    }


@app.get("/auth/me")
def auth_me(doctor: dict = Depends(get_current_doctor)):
    return doctor


@app.post("/auth/logout")
def auth_logout():
    return {"ok": True, "message": "Logged out successfully"}


@app.post("/cases", dependencies=[Depends(rate_limit("cases", max_requests=10, window_seconds=60))])
def create_case(payload: CasePayload):
    data = payload.model_dump()
    case_id = db.save_case(data)
    if data.get("escalation_reason") == "red_flag":
        alerts.send_critical_alert(db.get_case(case_id) or {**data, "id": case_id})
    return {"id": case_id}


@app.get("/cases")
def all_cases(doctor: dict = Depends(get_current_doctor)):
    return db.list_all_cases()


@app.get("/cases/open")
def open_cases(doctor: dict = Depends(get_current_doctor)):
    return db.list_open_cases()


@app.get("/cases/{case_id}/patient-status")
def patient_case_status(case_id: int):
    status_data = db.get_patient_case_status(case_id)
    if status_data is None:
        raise HTTPException(status_code=404, detail="case not found")
    return status_data


@app.get("/cases/{case_id}")
def read_case(case_id: int, doctor: dict = Depends(get_current_doctor)):
    case = db.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    return case


@app.patch("/cases/{case_id}/review")
def review_case(
    case_id: int,
    patch: ReviewPatch,
    doctor: dict = Depends(get_current_doctor),
):
    if db.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="case not found")
    db.mark_reviewed(
        case_id,
        doctor_id=doctor["id"],
        doctor_name=doctor["full_name"],
        department_override=patch.department_override,
    )
    return db.get_case(case_id)


@app.patch("/cases/{case_id}/prescribe")
def prescribe(
    case_id: int,
    patch: PrescribePatch,
    doctor: dict = Depends(get_current_doctor),
):
    case = db.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case not found")
    if patch.only_if_unprescribed and case.get("status") == "prescribed":
        raise HTTPException(status_code=409, detail="Case has already been prescribed")
    medicines = [medicine.model_dump() for medicine in patch.medicines]
    try:
        updated = db.prescribe_case(
            case_id,
            doctor_name=doctor["full_name"],
            medicines=medicines,
            notes=patch.notes,
            doctor_id=doctor["id"],
            only_if_unprescribed=patch.only_if_unprescribed,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="case not found")
        return updated
    except db.CaseAlreadyPrescribedError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/cases/{case_id}/report")
def case_report(
    case_id: int,
    doctor: dict = Depends(get_current_doctor),
):
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


@app.post(
    "/triage/start",
    dependencies=[Depends(rate_limit("triage_start", max_requests=10, window_seconds=60))],
)
def triage_start(req: TriageStartRequest):
    from core import agent_graph

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
            "question_type": "free_text",
            "question_options": [],
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


@app.post(
    "/triage/step",
    dependencies=[Depends(rate_limit("triage_step", max_requests=30, window_seconds=60))],
)
def triage_step(req: TriageStepRequest):
    from core import agent_graph

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


MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB


@app.post(
    "/triage/transcribe",
    dependencies=[Depends(rate_limit("triage_transcribe", max_requests=10, window_seconds=60))],
)
async def triage_transcribe(file: UploadFile = File(...)):
    from core import ai_clients

    try:
        total_size = 0
        chunks = []
        chunk_size = 64 * 1024
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_AUDIO_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Audio file exceeds maximum size of 10MB",
                )
            chunks.append(chunk)

        audio_bytes = b"".join(chunks)
        if not audio_bytes:
            return {"text": ""}
        text = ai_clients.transcribe(audio_bytes)
        return {"text": (text or "").strip()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Audio transcription failed: %s", e)
        if config.is_production():
            raise HTTPException(
                status_code=500,
                detail="Audio transcription service temporarily unavailable.",
            )
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

