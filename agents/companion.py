"""Companion Agent — Nemotron-Super, proactive driver engagement.

Spawned by agents/orchestrator.py when InterventionDecision.trigger_companion=True.
Acts independently of the Safety Reasoning Agent — it does not share a session or
context window with agents/safety.py.

Responsibilities:
- Receive ShiftContext + list of prior CompanionMessages (to avoid repetition).
- Call Nemotron-Super with companion-specific prompt (llm/companion_prompts.py).
- Generate a contextually appropriate message: engaging question, short story,
  gentle break suggestion, or verbal game depending on fatigue level and shift duration.
- Return a CompanionMessage for the orchestrator to send to display/TTS.

Tone guidelines (encoded in llm/companion_prompts.py):
  severity=low    → casual, curious ("Hey, good music lately?")
  severity=medium → warmer, proactive ("You've been at it a while — want to pull over soon?")
  severity=high   → gentle but direct ("I really think we should find a stop. I found one nearby.")

Owner: Emilio
Imports from: core.models, llm.client, llm.companion_prompts
"""


import subprocess
import time

from core.models import CompanionMessage, ShiftContext
from llm.client import complete
from llm.companion_prompts import COMPANION_SYSTEM_PROMPT, build_user_message


def generate(context: ShiftContext, prior_messages: list, severity: str, model: str) -> CompanionMessage:
    """Generate a proactive CompanionMessage for the current cycle.

    Args:
        context: ShiftContext from agents/context_builder.py
        prior_messages: list[CompanionMessage] — this shift, for deduplication
        severity: current severity level from InterventionDecision ("none"|"low"|"medium"|"high"|"critical")
        model: Nemotron model ID — passed in from main.py via config.api.nemotron_companion_model

    Returns:
        CompanionMessage
    """
    messages = [
        {"role": "system", "content": COMPANION_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(context, prior_messages, severity)},
    ]
    response = complete(
        model=model,
        messages=messages,
        temperature=0.8,   # higher than safety agent — we want natural, varied conversation
        max_tokens=80,     # keep it short; companion speaks in 1-2 sentences
    )
    message_text = response.strip()
    _speak(message_text)
    return CompanionMessage(
        timestamp=time.time(),
        driver_id=context.driver_id,
        message=message_text,
        trigger_reason=_infer_trigger_reason(severity, context),
        severity_context=severity,
    )


def _infer_trigger_reason(severity: str, context: ShiftContext) -> str:
    if severity in ("high", "critical"):
        return "pre_intervention"
    if not context.prior_interventions:
        return "fatigue_building"
    return "fatigue_building"


def _speak(text: str) -> None:
    # macOS TTS — reads the companion message aloud; no-ops silently on non-Mac
    try:
        subprocess.Popen(["say", "-v", "Samantha", text])
    except FileNotFoundError:
        pass
