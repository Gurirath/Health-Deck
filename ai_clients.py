"""Provider-agnostic AI clients for Health Deck, all in one place.

Four independent capabilities, each with its own env-selected provider and
its own mock mode for tests:

- LLM chat (HEALTHDECK_LLM_PROVIDER): chat_json / set_mock_llm_responses
- Web search (HEALTHDECK_SEARCH_PROVIDER): search / set_mock_search_results
- Image observation (HEALTHDECK_VISION_PROVIDER): analyze_image / set_mock_vision_analysis
- Speech to text (HEALTHDECK_STT_PROVIDER): transcribe / set_mock_transcription

Each block keeps the behavior it had as its own module; only the file
location and the mock-setter names changed.
"""

import base64
import io
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


LLM_PROVIDER = os.environ.get("HEALTHDECK_LLM_PROVIDER", "groq")
OLLAMA_MODEL = os.environ.get("HEALTHDECK_OLLAMA_MODEL", "qwen2.5:7b-instruct")
GROQ_MODEL = os.environ.get("HEALTHDECK_GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_RETRY_WAIT_SECONDS = 3

_mock_queue = []


def _is_rate_limit(exc):
    if exc.__class__.__name__ == "RateLimitError":
        return True
    return getattr(exc, "status_code", None) == 429


def set_mock_llm_responses(responses):
    global _mock_queue
    _mock_queue = list(responses)


def chat_json(system_prompt, user_prompt):
    if LLM_PROVIDER == "mock":
        if not _mock_queue:
            raise RuntimeError("No mock responses queued")
        return _mock_queue.pop(0)

    if LLM_PROVIDER == "ollama":
        import ollama

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format="json",
            options={"temperature": 0.2},
        )
        content = response["message"]["content"]
        return json.loads(content)

    if LLM_PROVIDER == "groq":
        from groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add a free "
                "Groq API key, or set HEALTHDECK_LLM_PROVIDER=ollama to run fully "
                "offline. See the README Quickstart for details."
            )
        client = Groq(api_key=api_key)

        def _call_groq():
            return client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

        try:
            completion = _call_groq()
        except Exception as first_error:
            if not _is_rate_limit(first_error):
                raise
            print(
                f"Groq rate limit hit; waiting {GROQ_RETRY_WAIT_SECONDS}s and retrying once."
            )
            time.sleep(GROQ_RETRY_WAIT_SECONDS)
            try:
                completion = _call_groq()
            except Exception as second_error:
                if _is_rate_limit(second_error):
                    raise RuntimeError(
                        "The assistant is busy right now. Please try again in a moment."
                    ) from second_error
                raise
        return json.loads(completion.choices[0].message.content)

    raise ValueError(f"Unknown HEALTHDECK_LLM_PROVIDER: {LLM_PROVIDER}")


SEARCH_PROVIDER = os.environ.get("HEALTHDECK_SEARCH_PROVIDER", "tavily")

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

TRUSTED_MEDICAL_DOMAINS = [
    "mayoclinic.org",
    "nhs.uk",
    "medlineplus.gov",
    "cdc.gov",
    "who.int",
    "clevelandclinic.org",
]

_mock_results = []


def set_mock_search_results(results):
    global _mock_results
    _mock_results = list(results)


def _tavily_search(query):
    api_key = os.environ.get("TAVILY_API_KEY")
    response = requests.post(
        TAVILY_SEARCH_URL,
        json={
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 5,
            "include_domains": TRUSTED_MEDICAL_DOMAINS,
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    results = []
    for item in payload.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
        )
    return results


def search(query):
    provider = SEARCH_PROVIDER
    if provider == "tavily" and not os.environ.get("TAVILY_API_KEY"):
        provider = "mock"

    if provider == "mock":
        return list(_mock_results)

    if provider == "tavily":
        try:
            return _tavily_search(query)
        except requests.RequestException:
            return []

    return []


VISION_PROVIDER = os.environ.get("HEALTHDECK_VISION_PROVIDER", "groq")
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

_VISION_INSTRUCTION = (
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


def set_mock_vision_analysis(result):
    global _mock_analysis
    _mock_analysis = result


def _vision_instruction(context_text):
    return _VISION_INSTRUCTION.format(context=context_text or "none provided")


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
                    {"type": "text", "text": _vision_instruction(context_text)},
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
            {"role": "user", "content": _vision_instruction(context_text), "images": [encoded]},
        ],
        format="json",
        options={"temperature": 0.2},
    )
    return json.loads(response["message"]["content"])


def analyze_image(image_bytes, context_text):
    if not image_bytes:
        return None

    if VISION_PROVIDER == "mock":
        return _mock_analysis

    if VISION_PROVIDER == "groq":
        return _analyze_groq(image_bytes, context_text)

    if VISION_PROVIDER == "ollama":
        return _analyze_ollama(image_bytes, context_text)

    return None


STT_PROVIDER = os.environ.get("HEALTHDECK_STT_PROVIDER", "faster-whisper")
MODEL_SIZE = os.environ.get("HEALTHDECK_WHISPER_MODEL", "small")

_model = None
_mock_transcript = "this is a mock transcription"


def set_mock_transcription(text):
    global _mock_transcript
    _mock_transcript = text


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes):
    if STT_PROVIDER == "mock":
        return _mock_transcript

    model = _get_model()
    segments, _info = model.transcribe(io.BytesIO(audio_bytes))
    return " ".join(segment.text for segment in segments).strip()
