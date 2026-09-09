"""FastAPI wrapper around db.py.

Run it with: uvicorn backend:app --reload

It owns the SQLite database. The kiosk (app.py) and the clinician dashboard
talk to these endpoints over HTTP instead of importing db.py directly, so
cases queued from separate kiosk sessions all land in one place.

POST /vitals is a landing pad for the hardware team: it stores raw sensor
reads in their own table and nothing consumes them yet.
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import db

db.init_db()

app = FastAPI(title="Health Deck API", version="1.0.0")


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


class ReviewPatch(BaseModel):
    department_override: Optional[str] = None


class VitalsReading(BaseModel):
    device_id: str
    spo2: float
    temp_c: float
    hr: float
    systolic_bp: float
    diastolic_bp: float
    timestamp: str


@app.get("/")
def root():
    return {"service": "health-deck", "ok": True}


@app.post("/cases")
def create_case(payload: CasePayload):
    case_id = db.save_case(payload.model_dump())
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


@app.post("/vitals")
def ingest_vitals(reading: VitalsReading):
    reading_id = db.save_raw_vitals(reading.model_dump())
    return {"id": reading_id}
