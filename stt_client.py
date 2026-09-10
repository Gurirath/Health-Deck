"""Speech-to-text, same provider shape as llm_client.py.

transcribe(audio_bytes) returns a plain string. The caller treats that
string exactly as if the patient had typed it.

- "faster-whisper": local, free, no network. The model is loaded once on
  first use and reused for the life of the process. Size comes from
  HEALTHDECK_WHISPER_MODEL (default "small").
- "mock": returns a fixed string, for tests.
"""

import io
import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.environ.get("HEALTHDECK_STT_PROVIDER", "faster-whisper")
MODEL_SIZE = os.environ.get("HEALTHDECK_WHISPER_MODEL", "small")

_model = None
_mock_transcript = "this is a mock transcription"


def set_mock_transcript(text):
    global _mock_transcript
    _mock_transcript = text


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes):
    if PROVIDER == "mock":
        return _mock_transcript

    model = _get_model()
    segments, _info = model.transcribe(io.BytesIO(audio_bytes))
    return " ".join(segment.text for segment in segments).strip()
