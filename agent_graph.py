from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from llm_client import chat_json
from prompts import SYSTEM_PROMPT, diagnosis_prompt, followup_prompt
from rules import DEPARTMENT_ROUTES, check_red_flags

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
    status: str


def extract_node(state: TriageState) -> TriageState:
    prompt = followup_prompt(state["vitals"], state["chief_complaint"], state["transcript"])
    result = chat_json(SYSTEM_PROMPT, prompt)
    merged = dict(state.get("extracted", {}))
    merged.update(result.get("extracted_fields", {}))
    state["extracted"] = merged
    state["ready_to_diagnose"] = bool(result.get("ready_to_diagnose", False))
    state["next_question"] = result.get("next_question", "")
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


def build_graph():
    graph = StateGraph(TriageState)
    graph.add_node("extract", extract_node)
    graph.add_node("redflag_check", redflag_node)
    graph.add_node("ask_question", ask_question_node)
    graph.add_node("diagnose", diagnose_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "redflag_check")
    graph.add_conditional_edges(
        "redflag_check",
        route_after_redflag,
        {"diagnose": "diagnose", "ask_question": "ask_question"},
    )
    graph.add_edge("ask_question", END)
    graph.add_edge("diagnose", END)

    return graph.compile()
