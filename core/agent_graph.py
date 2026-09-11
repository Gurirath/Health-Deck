from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from core.ai_clients import analyze_image, chat_json
from core.ai_clients import search as web_search
from core.prompts import (
    SYSTEM_PROMPT,
    diagnosis_prompt,
    followup_prompt,
    grounded_advice_prompt,
)
from core.rules import DEPARTMENT_ROUTES, check_red_flags

MAX_TURNS = 5
CONFIDENCE_THRESHOLD = 65


class TriageState(TypedDict):
    vitals: Dict[str, Any]
    chief_complaint: str
    symptom_location: str
    transcript: List[Dict[str, str]]
    extracted: Dict[str, Any]
    turn_count: int
    ready_to_diagnose: bool
    red_flags: List[str]
    next_question: str
    diagnosis: Dict[str, Any]
    raw_llm_response: Dict[str, Any]
    escalate: bool
    escalation_reason: str
    department: str
    solution_sources: List[str]
    image_bytes: Any
    image_analysis: Any
    status: str
    session_id: str
    question_type: str
    question_options: List[str]


def extract_node(state: TriageState) -> TriageState:
    prompt = followup_prompt(state["vitals"], state["chief_complaint"], state["transcript"])
    result = chat_json(SYSTEM_PROMPT, prompt)
    merged = dict(state.get("extracted", {}))
    merged.update(result.get("extracted_fields", {}))
    state["extracted"] = merged
    state["ready_to_diagnose"] = bool(result.get("ready_to_diagnose", False))
    state["next_question"] = result.get("next_question", "")
    raw_options = result.get("question_options")
    if isinstance(raw_options, list):
        state["question_options"] = [str(opt).strip() for opt in raw_options if str(opt).strip()]
    else:
        state["question_options"] = []
    state["question_type"] = result.get(
        "question_type", "single_choice" if state["question_options"] else "free_text"
    )
    state["turn_count"] = state.get("turn_count", 0) + 1
    return state


def redflag_node(state: TriageState) -> TriageState:
    state["red_flags"] = check_red_flags(
        state["vitals"], state["extracted"], state["chief_complaint"], state["transcript"]
    )
    return state


def route_after_redflag(state: TriageState) -> str:
    if state["red_flags"]:
        return "diagnose"
    if state["ready_to_diagnose"] or state["turn_count"] >= MAX_TURNS:
        return "diagnose"
    return "ask_question"


def ask_question_node(state: TriageState) -> TriageState:
    state["status"] = "awaiting_answer"
    return state


def diagnose_node(state: TriageState) -> TriageState:
    prompt = diagnosis_prompt(
        state["vitals"],
        state["chief_complaint"],
        state["transcript"],
        state["extracted"],
        state["red_flags"],
    )
    result = chat_json(SYSTEM_PROMPT, prompt)
    state["raw_llm_response"] = dict(result)
    state["diagnosis"] = result
    confidence = result.get("confidence", 0)
    state["escalate"] = bool(state["red_flags"]) or confidence < CONFIDENCE_THRESHOLD
    if state["red_flags"]:
        state["escalation_reason"] = "red_flag"
    elif state["escalate"]:
        state["escalation_reason"] = "low_confidence"
    else:
        state["escalation_reason"] = ""
    category = result.get("category", "general")
    state["department"] = DEPARTMENT_ROUTES.get(category, DEPARTMENT_ROUTES["general"])
    state["status"] = "complete"
    return state


def _diagnosis_label(diagnosis):
    label = diagnosis.get("probable_diagnosis", "")
    if label:
        return label
    differentials = diagnosis.get("differentials") or []
    if differentials:
        first = differentials[0]
        if isinstance(first, dict):
            return first.get("name", "") or first.get("diagnosis", "")
        return str(first)
    return ""


def search_solution_node(state: TriageState) -> TriageState:
    state.setdefault("solution_sources", [])
    if state.get("escalate"):
        return state

    diagnosis = state.get("diagnosis", {}) or {}
    label = _diagnosis_label(diagnosis)
    query = " ".join(
        part for part in ("self-care home treatment for", label, state.get("chief_complaint", "")) if part
    ).strip()
    if not label:
        return state

    results = web_search(query)
    sources = [item.get("url", "") for item in results if item.get("url")]
    if not sources:
        return state
    state["solution_sources"] = sources

    snippets = [item.get("content", "") for item in results if item.get("content")]
    rewrite = chat_json(
        SYSTEM_PROMPT,
        grounded_advice_prompt(diagnosis, diagnosis.get("self_care_advice", ""), snippets),
    )
    new_advice = rewrite.get("self_care_advice", "")
    if new_advice:
        state["diagnosis"] = {**diagnosis, "self_care_advice": new_advice}
    return state


def analyze_photo_node(state: TriageState) -> TriageState:
    image_bytes = state.get("image_bytes")
    if not image_bytes:
        state["image_analysis"] = None
        return state

    diagnosis = state.get("diagnosis", {}) or {}
    context = (
        f"Chief complaint: {state.get('chief_complaint', '')}. "
        f"Body location: {state.get('symptom_location', '')}. "
        f"Working impression from the conversation: {diagnosis.get('probable_diagnosis', 'none')}."
    )
    try:
        state["image_analysis"] = analyze_image(image_bytes, context)
    except Exception:
        state["image_analysis"] = None
    return state


def build_graph():
    graph = StateGraph(TriageState)
    graph.add_node("extract", extract_node)
    graph.add_node("redflag_check", redflag_node)
    graph.add_node("ask_question", ask_question_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("search_solution", search_solution_node)
    graph.add_node("analyze_photo", analyze_photo_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "redflag_check")
    graph.add_conditional_edges(
        "redflag_check",
        route_after_redflag,
        {"diagnose": "diagnose", "ask_question": "ask_question"},
    )
    graph.add_edge("ask_question", END)
    graph.add_edge("diagnose", "search_solution")
    graph.add_edge("search_solution", "analyze_photo")
    graph.add_edge("analyze_photo", END)

    return graph.compile()
