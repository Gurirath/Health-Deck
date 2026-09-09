import json
import os
import time

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.environ.get("HEALTHDECK_LLM_PROVIDER", "groq")
OLLAMA_MODEL = os.environ.get("HEALTHDECK_OLLAMA_MODEL", "qwen2.5:7b-instruct")
GROQ_MODEL = os.environ.get("HEALTHDECK_GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_RETRY_WAIT_SECONDS = 3

_mock_queue = []


def _is_rate_limit(exc):
    if exc.__class__.__name__ == "RateLimitError":
        return True
    return getattr(exc, "status_code", None) == 429


def set_mock_responses(responses):
    global _mock_queue
    _mock_queue = list(responses)


def chat_json(system_prompt, user_prompt):
    if PROVIDER == "mock":
        if not _mock_queue:
            raise RuntimeError("No mock responses queued")
        return _mock_queue.pop(0)

    if PROVIDER == "ollama":
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

    if PROVIDER == "groq":
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

    raise ValueError(f"Unknown HEALTHDECK_LLM_PROVIDER: {PROVIDER}")
