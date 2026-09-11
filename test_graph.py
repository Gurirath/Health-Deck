import ai_clients
from agent_graph import build_graph

ai_clients.LLM_PROVIDER = "mock"
ai_clients.SEARCH_PROVIDER = "mock"
ai_clients.VISION_PROVIDER = "mock"

FAKE_IMAGE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
MOCK_IMAGE_ANALYSIS = {
    "description": "A small reddened patch of skin with a few raised bumps.",
    "visual_characteristics": ["erythema", "clustered papules"],
    "note": "mock analysis",
}

BASE_NORMAL_LLM_RESPONSES = [
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


def _normal_state():
    return {
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
        "solution_sources": [],
        "image_bytes": None,
        "image_analysis": None,
        "status": "",
    }


def _fresh_normal_responses():
    return [dict(response) for response in BASE_NORMAL_LLM_RESPONSES]


def run_normal_case():
    ai_clients.set_mock_search_results(
        [
            {
                "title": "Common cold - self-care",
                "url": "https://www.nhs.uk/conditions/common-cold/",
                "content": "Rest, keep warm, drink plenty of water. Gargle salt water for a sore throat.",
            },
            {
                "title": "Common cold",
                "url": "https://medlineplus.gov/commoncold.html",
                "content": "Symptoms usually ease within 7 to 10 days. See a clinician if a fever tops 39C or breathing gets hard.",
            },
        ]
    )
    ai_clients.set_mock_llm_responses(
        _fresh_normal_responses()
        + [
            {
                "self_care_advice": (
                    "GROUNDED: rest and keep warm, sip water often, gargle salt water for the sore throat. "
                    "It usually settles within 7 to 10 days. An OTC fever reducer such as "
                    "paracetamol/acetaminophen can help; follow the package directions and check with a "
                    "pharmacist if you take other medication, are pregnant, or are treating a child. See a "
                    "clinician if your fever tops 39C or breathing gets hard."
                )
            }
        ]
    )
    ai_clients.set_mock_vision_analysis(MOCK_IMAGE_ANALYSIS)
    graph = build_graph()
    state = _normal_state()
    state["image_bytes"] = FAKE_IMAGE_BYTES

    result = graph.invoke(state)
    assert result["status"] == "awaiting_answer"
    assert result["next_question"]

    result["transcript"].append({"role": "assistant", "content": result["next_question"]})
    result["transcript"].append({"role": "user", "content": "yes, mild fever"})
    result = graph.invoke(result)

    assert result["status"] == "complete"
    assert result["escalate"] is False
    assert result["escalation_reason"] == ""
    assert result["diagnosis"]["probable_diagnosis"] == "Common cold"
    assert result["solution_sources"] == [
        "https://www.nhs.uk/conditions/common-cold/",
        "https://medlineplus.gov/commoncold.html",
    ]
    assert result["diagnosis"]["self_care_advice"].startswith("GROUNDED:")
    assert result["raw_llm_response"]["self_care_advice"] == "Rest, fluids, over the counter symptom relief."
    assert result["image_analysis"] == MOCK_IMAGE_ANALYSIS
    print("normal case (grounded + photo) OK ->", result["department"], "sources:", len(result["solution_sources"]))


def run_normal_case_no_search():
    ai_clients.set_mock_search_results([])
    ai_clients.set_mock_llm_responses(_fresh_normal_responses())
    graph = build_graph()
    state = _normal_state()

    result = graph.invoke(state)
    result["transcript"].append({"role": "assistant", "content": result["next_question"]})
    result["transcript"].append({"role": "user", "content": "yes, mild fever"})
    result = graph.invoke(result)

    assert result["status"] == "complete"
    assert result["escalate"] is False
    assert result["solution_sources"] == []
    assert result["diagnosis"]["self_care_advice"] == "Rest, fluids, over the counter symptom relief."
    assert result["image_analysis"] is None
    print("normal case (no search, no photo) OK -> original advice, image_analysis None")


def _redflag_responses():
    return [
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


def _redflag_state():
    return {
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
        "solution_sources": [],
        "image_bytes": None,
        "image_analysis": None,
        "status": "",
    }


def run_redflag_case():
    ai_clients.set_mock_search_results([])
    ai_clients.set_mock_vision_analysis(MOCK_IMAGE_ANALYSIS)
    ai_clients.set_mock_llm_responses(_redflag_responses())
    graph = build_graph()
    state = _redflag_state()
    state["image_bytes"] = FAKE_IMAGE_BYTES

    result = graph.invoke(state)
    assert result["status"] == "complete"
    assert result["escalate"] is True
    assert result["escalation_reason"] == "red_flag"
    assert result["solution_sources"] == []
    assert len(result["red_flags"]) >= 2
    assert result["image_analysis"] == MOCK_IMAGE_ANALYSIS
    print("red flag case (with photo) OK -> escalate:", result["escalate"], "image analysed anyway")


def run_redflag_case_no_photo():
    ai_clients.set_mock_search_results([])
    ai_clients.set_mock_llm_responses(_redflag_responses())
    graph = build_graph()
    state = _redflag_state()

    result = graph.invoke(state)
    assert result["status"] == "complete"
    assert result["escalate"] is True
    assert result["escalation_reason"] == "red_flag"
    assert result["image_analysis"] is None
    print("red flag case (no photo) OK -> image_analysis None")


def run_photo_arrives_after_first_turn():
    ai_clients.set_mock_search_results([])
    ai_clients.set_mock_vision_analysis(MOCK_IMAGE_ANALYSIS)
    ai_clients.set_mock_llm_responses(_fresh_normal_responses())
    graph = build_graph()

    state = _normal_state()
    assert state["image_bytes"] is None
    state = graph.invoke(state)
    assert state["status"] == "awaiting_answer"
    assert state["image_analysis"] is None

    state["transcript"].append({"role": "assistant", "content": state["next_question"]})
    state["transcript"].append({"role": "user", "content": "yes, mild fever"})
    state["image_bytes"] = FAKE_IMAGE_BYTES
    state = graph.invoke(state)

    assert state["status"] == "complete"
    assert state["image_analysis"] == MOCK_IMAGE_ANALYSIS
    print("photo arriving after the first turn OK -> analysed before the case finalised")


if __name__ == "__main__":
    run_normal_case()
    run_normal_case_no_search()
    run_redflag_case()
    run_redflag_case_no_photo()
    run_photo_arrives_after_first_turn()
    print("all tests passed")
