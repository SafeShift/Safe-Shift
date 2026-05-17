"""Safety Reasoning Agent — pure reasoning, no tool calls."""
import logging
import time

from core.models import InterventionDecision
from llm.safety_prompts import SAFETY_SYSTEM_PROMPT, build_user_message
from llm.parser import parse_intervention_decision

logger = logging.getLogger(__name__)


class SafetyAgent:
    """Safety Reasoning Agent.

    Calls Nemotron once and parses the JSON decision. Action dispatch
    is handled by the orchestrator, which applies cooldown before firing.

    Args:
        config: SimpleNamespace from load_config().
        client: NemotronClient instance.
    """

    def __init__(self, config, client):
        self._model  = client.super_model
        self._client = client

    def run(self, context) -> InterventionDecision:
        messages = [
            {"role": "system", "content": SAFETY_SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_message(context)},
            {"role": "user",   "content": "Output ONLY the JSON block now. No tools. No explanation. Just the JSON."},
        ]
        response = self._client.complete_with_tools(
            model=self._model,
            messages=messages,
            tools=[],
            temperature=0.2,
            max_tokens=256,
        )
        return self._parse_or_fallback(response.get("content"))

    def _parse_or_fallback(self, raw) -> InterventionDecision:
        if not raw:
            logger.warning("Safety agent returned no content — returning safe fallback")
            return InterventionDecision(
                should_intervene=False,
                severity="none",
                intervention_type="none",
                trigger_companion=False,
                reason="No content returned — defaulting to no intervention",
                confidence=0.0,
                timestamp=time.time(),
            )
        try:
            return parse_intervention_decision(raw, timestamp=time.time())
        except ValueError:
            logger.warning("Failed to parse InterventionDecision — returning safe fallback")
            return InterventionDecision(
                should_intervene=False,
                severity="none",
                intervention_type="none",
                trigger_companion=False,
                reason="Parse error — defaulting to no intervention",
                confidence=0.0,
                timestamp=time.time(),
            )
