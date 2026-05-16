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


def generate(context, prior_messages: list) -> "CompanionMessage":
    """Generate a proactive CompanionMessage for the current cycle.

    Args:
        context: ShiftContext from agents/context_builder.py
        prior_messages: list[CompanionMessage] — this shift, for deduplication

    Returns:
        CompanionMessage
    """
    raise NotImplementedError
