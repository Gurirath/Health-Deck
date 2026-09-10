"""Image observation, same provider shape as llm_client.py.

analyze_image(image_bytes, context_text) returns a dict:

    {"description": "...", "visual_characteristics": ["..."], "note": "..."}

or None when it cannot run (no key, provider error, empty image). This
model only observes and describes what is visible - colour, pattern,
location, size, texture. It does not name a condition or a diagnosis; that
stays the job of the main diagnosis reasoning in agent_graph.py.

Providers via HEALTHDECK_VISION_PROVIDER:
- "groq": Groq multimodal chat, model qwen/qwen3.6-27b, JSON mode.
- "ollama": a local vision model (default llava, HEALTHDECK_VISION_MODEL).
- "mock": returns a fixed dict, for tests.
"""

import base64
import json
import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.environ.get("HEALTHDECK_VISION_PROVIDER", "groq")
GROQ_VISION_MODEL = os.environ.get("HEALTHDECK_VISION_MODEL", "qwen/qwen3.6-27b")
OLLAMA_VISION_MODEL = os.environ.get("HEALTHDECK_VISION_MODEL", "llava")

VISION_SYSTEM_PROMPT = (
    "You are a visual observation aid on a medical triage kiosk. Look at the "
    "photo and describe only what is objectively visible: colour, pattern, "
    "shape, size relative to nearby anatomy, texture, borders, distribution, "
    "swelling, discharge, and body location. Do not name a disease, do not "
    "give a diagnosis, do not suggest treatment. Observation only - the "
    "diagnosis is made elsewhere from the full picture."
)

_INSTRUCTION = (
    "Describe this photo for a clinician who will read it alongside the "
    "patient's account. Context from the conversation so far:\n{context}\n\n"
    "Respond with JSON only, in exactly this shape:\n"
    '{{"description": "2-4 plain sentences of what is visible", '
    '"visual_characteristics": ["short observed features"], '
    '"note": "anything that limits the observation, e.g. blur, lighting, framing"}}'
)

_mock_analysis = {
    "description": "A small area of skin with mild redness and a few raised bumps.",
    "visual_characteristics": ["erythema", "clustered papules", "well defined border"],
    "note": "mock analysis",
}


def set_mock_analysis(result):
    global _mock_analysis
    _mock_analysis = result


def _instruction(context_text):
    return _INSTRUCTION.format(context=context_text or "none provided")


def _analyze_groq(image_bytes, context_text):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    from groq import Groq

    client = Groq(api_key=api_key)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    completion = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _instruction(context_text)},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(completion.choices[0].message.content)


def _analyze_ollama(image_bytes, context_text):
    import ollama

    encoded = base64.b64encode(image_bytes).decode("ascii")
    response = ollama.chat(
        model=OLLAMA_VISION_MODEL,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": _instruction(context_text), "images": [encoded]},
        ],
        format="json",
        options={"temperature": 0.2},
    )
    return json.loads(response["message"]["content"])


def analyze_image(image_bytes, context_text):
    if not image_bytes:
        return None

    if PROVIDER == "mock":
        return _mock_analysis

    if PROVIDER == "groq":
        return _analyze_groq(image_bytes, context_text)

    if PROVIDER == "ollama":
        return _analyze_ollama(image_bytes, context_text)

    return None
