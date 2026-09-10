"""Red-flag alert fan-out over the Twilio WhatsApp Sandbox.

send_critical_alert(case) POSTs the same message straight to Twilio's REST
API (no twilio SDK) for every number in TWILIO_WHATSAPP_TO.

It is a best-effort side effect. If TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
or TWILIO_WHATSAPP_TO is missing it logs a warning and returns without
sending, so a public clone with no Twilio account runs normally and simply
never delivers alerts.

Sandbox caveat: every recipient must first send the sandbox join code
("join <two-words>") from their own WhatsApp to the sandbox number once.
Until they do, Twilio accepts the request but does not deliver the message.
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("healthdeck.alerts")

TWILIO_API_ROOT = "https://api.twilio.com/2010-04-01"
DEFAULT_WHATSAPP_FROM = "whatsapp:+14155238886"


def _recipients():
    raw = os.environ.get("TWILIO_WHATSAPP_TO", "")
    return [number.strip() for number in raw.split(",") if number.strip()]


def _format_message(case):
    vitals = case.get("vitals", {}) or {}
    vitals_line = ", ".join(f"{key}={value}" for key, value in vitals.items()) or "not recorded"
    red_flags = case.get("red_flags", []) or []
    flags_line = "; ".join(red_flags) or "none listed"
    return (
        "HEALTH DECK - RED FLAG\n"
        f"Case #{case.get('id', 'unknown')}\n"
        f"Time: {case.get('created_at', 'unknown')}\n"
        f"Chief complaint: {case.get('chief_complaint', 'n/a')}\n"
        f"Vitals: {vitals_line}\n"
        f"Red flags: {flags_line}"
    )


def send_critical_alert(case):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    recipients = _recipients()
    whatsapp_from = os.environ.get("TWILIO_WHATSAPP_FROM", DEFAULT_WHATSAPP_FROM)

    if not account_sid or not auth_token or not recipients:
        logger.warning(
            "Twilio not configured (need TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "TWILIO_WHATSAPP_TO); skipping red-flag alert for case %s.",
            case.get("id", "unknown"),
        )
        return 0

    body = _format_message(case)
    url = f"{TWILIO_API_ROOT}/Accounts/{account_sid}/Messages.json"
    sent = 0
    for number in recipients:
        try:
            response = requests.post(
                url,
                data={"From": whatsapp_from, "To": number, "Body": body},
                auth=(account_sid, auth_token),
                timeout=10,
            )
            response.raise_for_status()
            sent += 1
        except requests.RequestException as exc:
            logger.warning("Failed to send red-flag alert to %s: %s", number, exc)
    return sent
