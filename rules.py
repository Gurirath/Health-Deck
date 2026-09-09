RED_FLAG_VITALS = {
    "spo2_below": 92,
    "temp_c_above": 39.5,
    "hr_above": 120,
    "hr_below": 50,
    "systolic_bp_above": 180,
    "systolic_bp_below": 90,
}

RED_FLAG_KEYWORDS = [
    "chest pain",
    "difficulty breathing",
    "shortness of breath",
    "can't breathe",
    "severe headache",
    "worst headache",
    "confusion",
    "fainting",
    "passed out",
    "blue lips",
    "coughing blood",
    "stiff neck",
    "one sided weakness",
    "slurred speech",
    "severe abdominal pain",
]

DEPARTMENT_ROUTES = {
    "respiratory": "General Physician / Pulmonology",
    "cardiac": "Cardiology",
    "ent": "ENT",
    "gi": "General Physician / Gastroenterology",
    "neuro": "Neurology",
    "general": "General Physician",
}


def check_red_flags(vitals, extracted, chief_complaint, transcript):
    triggered = []

    spo2 = vitals.get("spo2")
    if spo2 is not None and spo2 < RED_FLAG_VITALS["spo2_below"]:
        triggered.append(f"SpO2 {spo2}% below safe threshold")

    temp_c = vitals.get("temp_c")
    if temp_c is not None and temp_c > RED_FLAG_VITALS["temp_c_above"]:
        triggered.append(f"Temperature {temp_c}C above safe threshold")

    hr = vitals.get("hr")
    if hr is not None:
        if hr > RED_FLAG_VITALS["hr_above"]:
            triggered.append(f"Heart rate {hr} bpm above safe threshold")
        elif hr < RED_FLAG_VITALS["hr_below"]:
            triggered.append(f"Heart rate {hr} bpm below safe threshold")

    systolic = vitals.get("systolic_bp")
    if systolic is not None:
        if systolic > RED_FLAG_VITALS["systolic_bp_above"]:
            triggered.append(f"Systolic BP {systolic} above safe threshold")
        elif systolic < RED_FLAG_VITALS["systolic_bp_below"]:
            triggered.append(f"Systolic BP {systolic} below safe threshold")

    text_blob = chief_complaint.lower()
    for turn in transcript:
        text_blob += " " + turn.get("content", "").lower()

    for keyword in RED_FLAG_KEYWORDS:
        if keyword in text_blob:
            triggered.append(f"Reported symptom matches red-flag keyword: {keyword}")

    return triggered
