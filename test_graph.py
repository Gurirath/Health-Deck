import llm_client
from agent_graph import build_graph

llm_client.PROVIDER = "mock"


def run_normal_case():
    llm_client.set_mock_responses(
        [
            {
                "extracted_fields": {"duration": "2 days", "severity_1_to_10": 3},
                "ready_to_diagnose": False,
                "next_question": "Do you have a fever along with the cough?",
            },
            {
                "extracted_fields": {"associated_symptoms": ["mild fever"]},
                "ready_to_diagnose": True,
                "next_question": "",
            },
            {
                "probable_diagnosis": "Common cold",
                "confidence": 82,
                "category": "respiratory",
                "reasoning": "Mild symptoms, short duration, vitals normal.",
                "self_care_advice": "Rest, fluids, over the counter symptom relief.",
                "safety_note": "",
            },
        ]
    )
    graph = build_graph()
    state = {
        "vitals": {"spo2": 98, "temp_c": 37.2, "hr": 76, "systolic_bp": 118, "diastolic_bp": 78},
        "chief_complaint": "I have a cough",
        "symptom_location": "chest",
        "transcript": [{"role": "user", "content": "I have a cough"}],
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
        "status": "",
    }
    result = graph.invoke(state)
    assert result["status"] == "awaiting_answer"
    assert result["next_question"]

    result["transcript"].append({"role": "assistant", "content": result["next_question"]})
    result["transcript"].append({"role": "user", "content": "yes, mild fever"})
    result = graph.invoke(result)

    assert result["status"] == "complete"
    assert result["escalate"] is False
    assert result["escalation_reason"] == ""
    assert result["raw_llm_response"]["probable_diagnosis"] == "Common cold"
    assert result["diagnosis"]["probable_diagnosis"] == "Common cold"
    print("normal case OK ->", result["department"], result["diagnosis"]["confidence"])


def run_redflag_case():
    llm_client.set_mock_responses(
        [
            {
                "extracted_fields": {"duration": "1 hour"},
                "ready_to_diagnose": False,
                "next_question": "Is the chest pain constant or does it come and go?",
            },
            {
                "probable_diagnosis": "Uncertain, possible cardiac involvement",
                "confidence": 40,
                "category": "cardiac",
                "reasoning": "Chest pain with low SpO2 is outside safe self-triage territory.",
                "self_care_advice": "",
                "safety_note": "Escalate immediately, do not delay.",
            },
        ]
    )
    graph = build_graph()
    state = {
        "vitals": {"spo2": 89, "temp_c": 37.0, "hr": 130, "systolic_bp": 120, "diastolic_bp": 80},
        "chief_complaint": "I have chest pain and it's hard to breathe",
        "symptom_location": "chest",
        "transcript": [{"role": "user", "content": "I have chest pain and it's hard to breathe"}],
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
        "status": "",
    }
    result = graph.invoke(state)
    assert result["status"] == "complete"
    assert result["escalate"] is True
    assert result["escalation_reason"] == "red_flag"
    assert len(result["red_flags"]) >= 2
    print("red flag case OK -> escalate:", result["escalate"], "reason:", result["escalation_reason"], "flags:", result["red_flags"])


if __name__ == "__main__":
    run_normal_case()
    run_redflag_case()
    print("all tests passed")
