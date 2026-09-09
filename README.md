# Health Deck — Agentic Triage Kiosk

Health Deck is a self-service kiosk demo. A patient's vitals are captured, then an
agentic LLM conversation asks a few targeted follow-up questions and produces a
triage decision. A deterministic safety layer runs alongside the model: if a vital
is out of range or a red-flag symptom is mentioned, the case is escalated to a
human clinician **regardless of what the model's confidence score says**. Every
completed case is written — through a small FastAPI backend — to a local database
that a second page, the clinician dashboard, reads to work through the escalation
queue.

This repo is the software-only slice. Vitals are sidebar sliders standing in for a
real sensor module; the sensor seam is already abstracted (see
[What still needs hardware](#what-still-needs-hardware)).

## Quickstart (Groq, ~2 minutes)

You need Python 3.10+ and a free Groq API key (no credit card).

```bash
git clone <this-repo-url>
cd "Health Deck"
pip install -r requirements.txt

cp .env.example .env          # Windows: copy .env.example .env
```

Get a key at <https://console.groq.com/keys>, then open `.env` and set it:

```
GROQ_API_KEY=gsk_your_real_key_here
```

Health Deck runs as **two processes** — start each in its own terminal:

```bash
# terminal 1 — the API and persistence layer
uvicorn backend:app --reload

# terminal 2 — the kiosk UI (and the clinician dashboard page)
streamlit run app.py
```

The backend listens on `http://localhost:8000` and owns the SQLite database. The
kiosk and the clinician dashboard both talk to it over HTTP — they no longer open
the database file directly. Point them somewhere else with `HEALTHDECK_API_URL`.

Streamlit opens a browser tab. Enter vitals in the sidebar, pick where the problem
is, describe a symptom, answer the follow-up questions, and you'll get a triage
result. Escalated cases show up on the **Clinician Dashboard** page (page switcher
in the sidebar).

Groq is the default provider. If `GROQ_API_KEY` is missing you get a clear message
pointing back here, not a stack trace. If Groq rate-limits a request, the client
waits and retries once, then shows "the assistant is busy, try again in a moment"
rather than a traceback.

## The `.env` file

`python-dotenv` loads `.env` automatically on startup, so the key never has to be
exported into your shell or pasted into a command. `.env` is git-ignored — only the
placeholder `.env.example` is committed. Real environment variables still win over
`.env` if both are set.

## Offline alternative: Ollama

No API calls, works with no internet — but you need a machine that can run a 7B
model locally.

1. Install Ollama from <https://ollama.com>.
2. Pull a model:

   ```bash
   ollama pull qwen2.5:7b-instruct
   ```

3. Point Health Deck at Ollama:

   ```bash
   HEALTHDECK_LLM_PROVIDER=ollama streamlit run app.py
   ```

`llama3.1:8b-instruct` and `gemma2:9b` also work — pull one and set
`HEALTHDECK_OLLAMA_MODEL` to its tag. Ollama must be running (`ollama serve`,
usually automatic after install).

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `HEALTHDECK_LLM_PROVIDER` | `groq` | `groq`, `ollama`, or `mock` (tests) |
| `GROQ_API_KEY` | — | required when provider is `groq` |
| `HEALTHDECK_GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model id |
| `HEALTHDECK_OLLAMA_MODEL` | `qwen2.5:7b-instruct` | local model tag |
| `HEALTHDECK_API_URL` | `http://localhost:8000` | where the Streamlit apps reach the backend |
| `HEALTHDECK_DB_PATH` | `healthdeck.db` | SQLite file location (read by the backend) |

## Testing the agent logic without a model

`test_graph.py` runs the full LangGraph state machine with mocked LLM responses —
one normal case, one red-flag case — so you can confirm the wiring (question loop,
red-flag override, escalation reason, escalation routing, department mapping)
before pointing it at a real model. It needs neither the backend nor a model:

```bash
python test_graph.py
```

Smoke-test the backend once it's running with `curl http://localhost:8000/` or by
opening <http://localhost:8000/docs>.

## Project layout

| File | Responsibility |
|---|---|
| `app.py` | Kiosk UI (touchscreen-oriented, full width); POSTs completed cases to the backend |
| `pages/1_Clinician_Dashboard.py` | Escalation queue: reads/updates cases via the backend, mark reviewed, override department |
| `backend.py` | FastAPI wrapper over `db.py`: case create/read/review, plus a `/vitals` landing pad |
| `agent_graph.py` | LangGraph flow: extract → red-flag check → ask another question or diagnose |
| `rules.py` | Deterministic red-flag checks that override the model's confidence |
| `prompts.py` | System prompt + the two task prompts; JSON-only output contract |
| `llm_client.py` | Provider-agnostic LLM wrapper (groq / ollama / mock), with Groq 429 retry |
| `vitals_provider.py` | `VitalsProvider` interface + manual (sliders) and sensor (stub) implementations |
| `symptom_location.py` | Body-region input, abstracted so a 3D body map can replace the selectbox |
| `db.py` | SQLite persistence for completed cases and raw sensor reads |
| `test_graph.py` | Wiring test with mocked responses |

## What still needs hardware

- **Vitals.** `vitals_provider.SensorVitalsProvider.get_vitals()` is a stub that
  raises `NotImplementedError`. The hardware team implements it to read the sensor
  board and return `{spo2, temp_c, hr, systolic_bp, diastolic_bp}`; nothing in the
  agent or UI changes. `ManualVitalsProvider` (sidebar sliders) is the stand-in.
- **Symptom location.** `symptom_location.SelectboxLocationProvider` is a coarse
  body-region selectbox. `BodyMapLocationProvider` is reserved for a tappable 3D
  body map (Blender → glTF → Three.js) and implements the same `get_location()`.
- **Raw sensor feed.** `POST /vitals` on the backend accepts
  `{device_id, spo2, temp_c, hr, systolic_bp, diastolic_bp, timestamp}` and lands
  it in a `raw_vitals` table. Nothing reads that table yet — it exists so the
  hardware team has somewhere to send readings while the rest of the integration
  is built. It is not wired to the triage flow.

## License

MIT — see `LICENSE`. Import it, fork it, ship it.
