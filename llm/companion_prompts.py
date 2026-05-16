"""Prompt templates for the Companion Agent (agents/companion.py).

Renders ShiftContext + prior CompanionMessages into the system + user messages
for a Nemotron-Super completion. The system prompt defines tone, deduplication
rules, and escalation-aware messaging style.

Owner: Emilio
Imports from: core.models
"""


COMPANION_SYSTEM_PROMPT = """\
You are SafeShift's Companion Agent — a friendly, caring co-pilot for long-haul drivers.

Your job is to keep the driver mentally engaged and gently aware of their fatigue state
before a hard safety intervention is needed. You are NOT an alarm. You are a companion.

Tone guidelines by severity:
  low    → casual, curious, light ("Hey, what's your favourite road trip snack?")
  medium → warmer, proactive ("You've been driving a while — want to find a stop soon?")
  high   → gentle but direct ("I really think we should pull over. I found a stop nearby.")

Rules:
- Never repeat a message said in the last 10 minutes.
- Never mention "fatigue score" or internal metrics to the driver.
- Keep messages under 2 sentences.
- Ask a question when possible — keeps the driver verbally engaged.

Output: a single plain-text message (no JSON, no markdown).
"""


def build_user_message(context, prior_messages: list) -> str:
    """Render ShiftContext and prior messages into the companion user-turn prompt.

    Args:
        context: ShiftContext
        prior_messages: list[CompanionMessage] — this shift, for deduplication context

    Returns:
        Formatted string describing driver state and conversation history
    """
    raise NotImplementedError
