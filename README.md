# Health Deck — Agentic Triage Kiosk

Health Deck is a self-service kiosk demo. A patient's vitals are captured, then an
agentic LLM conversation asks a few targeted follow-up questions. The patient can
type or **speak** their answers, and can **scan a QR code to send a photo** of the
problem from their phone; a vision model describes what is visible and a search
layer grounds the AI's self-care notes in trusted medical sites.

**Every completed case then goes to a doctor.** There is no instant AI answer to
the patient. The model's diagnosis, confidence, and notes become a *preliminary AI
assessment* section that a clinician reads on the dashboard before writing the
actual prescription. The patient waits, then downloads a printable report with the
doctor's prescription on it. A deterministic safety layer still runs: a red-flag
vital or symptom fires an immediate WhatsApp alert and marks the case urgent in
the queue — but urgent or not, every case waits for a doctor.

Optional integrations (photo vision, grounded advice, WhatsApp alerts) all no-op
cleanly when their keys are absent — see [Optional integrations](#optional-integrations).

This repo is the software-only slice. Vitals are sidebar sliders standing in for a
real sensor module; the sensor seam is already abstracted (see
[What still needs hardware](#what-still-needs-hardware)).

## Quickstart (Groq, ~2 minutes)

You need Python 3.10+ and a free Groq API key (no credit card).

```bash
git clone <this-repo-url>
cd "Health Deck"
pip install -r requirements.txt   # includes faster-whisper; first install is ~200MB

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

The backend listens on `http://localhost:8000` and owns the SQLite database plus
the `uploads/` and `reports/` folders. The kiosk and the clinician dashboard both
talk to it over HTTP. Point them elsewhere with `HEALTHDECK_API_URL`.

Streamlit opens a browser tab. Enter vitals in the sidebar, pick where the problem
is, describe a symptom (type or record it), optionally scan the QR to add a photo,
answer the follow-ups. The case is then filed for a doctor — open the **Clinician
Dashboard** page (sidebar page switcher), write a prescription, and back on the
kiosk the patient can download the report.

## The one thing that silently breaks: the photo QR

The kiosk shows a QR code the patient scans **with their phone**. Their phone is a
different device on the network, so the QR cannot point at `localhost`. Set
`HEALTHDECK_PUBLIC_BASE_URL` to this machine's LAN IP before a demo:

```bash
# find your LAN IP
ipconfig                      # Windows — look for IPv4 Address
ipconfig getifaddr en0        # macOS

# then, in .env
HEALTHDECK_PUBLIC_BASE_URL=http://192.168.1.50:8000
```

Left as `localhost`, the QR still renders and the kiosk shows a warning, but no
phone on the network can open it — the rest of the flow (typing, voice, doctor
review) works fine without a photo. The backend must also be reachable at that
IP:port from the phone (same Wi-Fi, firewall allowing the port).

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

## The case flow

1. **Intake** — vitals (sidebar), body region, chief complaint typed or spoken.
   Optional: scan the QR to upload one photo from a phone.
2. **Conversation** — the LangGraph agent asks up to five follow-ups, each
   answerable by typing or recording. A red-flag vital or keyword short-circuits
   straight to a decision.
3. **Assessment** — the agent produces a probable diagnosis, confidence,
   department, and draft self-care notes. If a photo was sent, a vision model adds
   a plain visual description (it never names a condition). None of this is shown
   to the patient.
4. **Doctor review** — the case lands on the dashboard as `pending`. It stays
   there until a doctor submits a prescription, red-flag or not. Red-flag cases
   are marked urgent and also trigger a WhatsApp alert.
5. **Prescription + report** — the doctor's prescription is saved, a three-section
   PDF (patient intake / AI preliminary assessment / prescription) is generated,
   and the patient can download it from the kiosk once status flips to
   `prescribed`.

## Speech input

Answers can be recorded instead of typed, at every step. Transcription runs
locally with `faster-whisper` — no key, no network. The model size is
`HEALTHDECK_WHISPER_MODEL` (`tiny` / `base` / `small` / `medium` / `large-v3`,
default `small`); it downloads once on first use and is then reused for the life
of the process.

## Optional integrations

All of these are off-by-default and degrade cleanly — the app runs fine without
any of them, you just lose that piece.

### Photo vision analysis

If a photo is uploaded, `analyze_photo_node` sends it to a vision model that
describes only what is visible (colour, pattern, size, texture, location) and
never names a condition. `HEALTHDECK_VISION_PROVIDER` is `groq` (reuses
`GROQ_API_KEY`, model `qwen/qwen3.6-27b`), `ollama` (local, default `llava`,
override with `HEALTHDECK_VISION_MODEL`), or `mock`. With no working provider the
photo is still stored and shown to the doctor; `image_analysis` just stays null.

### Grounded self-care advice (Tavily)

For non-escalated cases, `search_solution_node` searches a fixed allowlist of
trusted medical domains (Mayo Clinic, NHS, MedlinePlus, CDC, WHO, Cleveland
Clinic) and asks the model to rewrite `self_care_advice` from those results,
then shows the source links to the patient and the clinician.

1. Sign up free at <https://app.tavily.com> (no card), open **API Keys**, copy one.
2. Put it in `.env`: `TAVILY_API_KEY=tvly-...` (and keep `HEALTHDECK_SEARCH_PROVIDER=tavily`).

Without `TAVILY_API_KEY`, search returns nothing, the rewrite is skipped, and
the model-only `self_care_advice` is kept as-is. No error.

### Red-flag WhatsApp alerts (Twilio Sandbox)

When a case escalates specifically because of a **red flag** (not low
confidence), the backend POSTs a WhatsApp message — chief complaint, vitals,
which red flags fired, timestamp, case id — to every number in
`TWILIO_WHATSAPP_TO`.

1. Create a free Twilio trial: <https://www.twilio.com/try-twilio>.
2. In the console: **Messaging -> Try it out -> Send a WhatsApp message**. That
   page shows your **sandbox number** and a **join code** like `join two-words`.
3. **Each** recipient sends that join code once, from their own WhatsApp, to the
   sandbox number. Until they do, Twilio silently drops messages to them.
4. In `.env` set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and
   `TWILIO_WHATSAPP_TO` (comma-separated, e.g. two doctors).
   `TWILIO_WHATSAPP_FROM` defaults to the sandbox number `whatsapp:+14155238886`.

If any of `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_TO` is
missing, the alert is logged and skipped — the case still saves normally.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `HEALTHDECK_LLM_PROVIDER` | `groq` | `groq`, `ollama`, or `mock` (tests) |
| `GROQ_API_KEY` | — | required when provider is `groq`; also used by vision `groq` mode |
| `HEALTHDECK_GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model id |
| `HEALTHDECK_OLLAMA_MODEL` | `qwen2.5:7b-instruct` | local model tag |
| `HEALTHDECK_API_URL` | `http://localhost:8000` | where the Streamlit apps reach the backend |
| `HEALTHDECK_PUBLIC_BASE_URL` | `http://localhost:8000` | **set to the kiosk LAN IP** or the photo QR is unreachable from a phone |
| `HEALTHDECK_DB_PATH` | `healthdeck.db` | SQLite file location (read by the backend) |
| `HEALTHDECK_UPLOADS_DIR` | `uploads` | where the backend saves uploaded photos |
| `HEALTHDECK_REPORTS_DIR` | `reports` | where generated PDF reports are written |
| `HEALTHDECK_VISION_PROVIDER` | `groq` | `groq`, `ollama`, or `mock`; absent key = photo stored, no analysis |
| `HEALTHDECK_VISION_MODEL` | `qwen/qwen3.6-27b` (groq) / `llava` (ollama) | vision model override |
| `HEALTHDECK_STT_PROVIDER` | `faster-whisper` | `faster-whisper` or `mock` |
| `HEALTHDECK_WHISPER_MODEL` | `small` | whisper size: `tiny`/`base`/`small`/`medium`/`large-v3` |
| `HEALTHDECK_SEARCH_PROVIDER` | `tavily` | `tavily` or `mock` |
| `TAVILY_API_KEY` | — | enables grounded `self_care_advice`; absent = model-only, no sources |
| `TWILIO_ACCOUNT_SID` | — | Twilio auth; all three TWILIO_* below are needed to send alerts |
| `TWILIO_AUTH_TOKEN` | — | Twilio auth |
| `TWILIO_WHATSAPP_TO` | — | comma-separated recipient list, e.g. `whatsapp:+1...,whatsapp:+1...` |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` | Twilio sandbox number |

## Tests

`test_graph.py` runs the full LangGraph state machine with mocked LLM, search, and
vision clients — normal and red-flag cases, each with and without a photo — and
confirms the wiring: question loop, red-flag override, escalation reason,
department mapping, grounded-advice fallback, and that `image_analysis` populates
only when an image is present. No backend or model needed.

`test_backend.py` uses FastAPI's `TestClient` against a temp DB: the upload page
renders, a posted photo round-trips, prescribing flips status and writes a PDF,
and `GET /cases/{id}/report` 404s before prescribing and returns the PDF after.

```bash
python test_graph.py
python test_backend.py
```

Smoke-test the running backend with `curl http://localhost:8000/` or open
<http://localhost:8000/docs>.

## Project layout

| File | Responsibility |
|---|---|
| `app.py` | Kiosk UI: session id, QR photo prompt, typed/spoken input, patient waiting + report download |
| `pages/1_Clinician_Dashboard.py` | Doctor queue (every non-prescribed case): full report, patient photo, prescribing form, lighter review action |
| `backend.py` | FastAPI over `db.py`: cases, QR upload endpoints, prescribe, report PDF, `/vitals`, red-flag alerts |
| `agent_graph.py` | LangGraph flow: extract → red-flag check → ask / diagnose → ground advice → analyse photo |
| `ai_clients.py` | All four provider-agnostic AI clients: LLM chat (groq/ollama, 429 retry), search (tavily), image observation (groq/ollama), speech-to-text (faster-whisper); each with a `mock` mode |
| `providers.py` | `VitalsProvider` (manual sliders + sensor stub) and `SymptomLocationProvider` (region selectbox + body-map stub) |
| `report_builder.py` | `build_report` (3-section dict) and `generate_pdf` (fpdf2) — patient intake / AI assessment / prescription |
| `alerts.py` | Twilio WhatsApp Sandbox fan-out for red-flag cases; no-ops if unconfigured |
| `rules.py` | Deterministic red-flag checks that override the model's confidence |
| `prompts.py` | System prompt + the task prompts; JSON-only output contract |
| `db.py` | SQLite: cases (with prescription + photo fields), `session_uploads`, raw sensor reads |
| `test_graph.py` / `test_backend.py` | Graph wiring test / backend endpoint test |

## What still needs hardware

- **Vitals.** `providers.SensorVitalsProvider.get_vitals()` is a stub that
  raises `NotImplementedError`. The hardware team implements it to read the sensor
  board and return `{spo2, temp_c, hr, systolic_bp, diastolic_bp}`; nothing in the
  agent or UI changes. `ManualVitalsProvider` (sidebar sliders) is the stand-in.
- **Symptom location.** `providers.SelectboxLocationProvider` is a coarse
  body-region selectbox. `BodyMapLocationProvider` is reserved for a tappable 3D
  body map (Blender → glTF → Three.js) and implements the same `get_location()`.
- **Raw sensor feed.** `POST /vitals` on the backend accepts
  `{device_id, spo2, temp_c, hr, systolic_bp, diastolic_bp, timestamp}` and lands
  it in a `raw_vitals` table. Nothing reads that table yet — it exists so the
  hardware team has somewhere to send readings while the rest of the integration
  is built. It is not wired to the triage flow.

## License

MIT — see `LICENSE`. Import it, fork it, ship it.
