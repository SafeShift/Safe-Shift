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
from llm.companion_prompts import COMPANION_SYSTEM_PROMPT, build_user_message


class CompanionAgent:
    """Proactive conversational agent that keeps the driver engaged before hard interventions.

    Args:
        config: SimpleNamespace from load_config().
        client: NemotronClient instance — shared with SafetyAgent.
    """

    def __init__(self, config, client):
        self._model  = client.companion_model
        self._client = client

    def generate(self, context: ShiftContext, prior_messages: list, severity: str) -> CompanionMessage:
        """Generate a proactive CompanionMessage for the current cycle.

        Args:
            context: ShiftContext from agents/context_builder.py
            prior_messages: list[CompanionMessage] — this shift, for deduplication
            severity: current severity level from InterventionDecision

        Returns:
            CompanionMessage
        """
        messages = [
            {"role": "system", "content": COMPANION_SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_message(context, prior_messages, severity)},
        ]
        response = self._client.complete(
            model=self._model,
            messages=messages,
            temperature=0.8,  # higher than safety agent — natural, varied conversation
            max_tokens=300,   # room to think then produce a short response
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
    return "fatigue_building"


def _speak(text: str, voice: str = "en-US-AriaNeural") -> None:
    # edge-tts — natural TTS; falls back silently on failure
    try:
        import asyncio, edge_tts, tempfile, os
        async def _play():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            await edge_tts.Communicate(text, voice).save(tmp)
            subprocess.run(["afplay", tmp], check=True)
            os.unlink(tmp)
        asyncio.run(_play())
    except Exception:
        pass
