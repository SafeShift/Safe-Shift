"""Safety Reasoning Agent — Nemotron-Super via OpenClaw ReAct loop.

The primary decision-making agent. Receives ShiftContext and runs a multi-step
Reason → Act → Observe loop using Nemotron-Super (llama-3_3-nemotron-super-49b-v1_5)
as the reasoning core inside an OpenClaw session.

ReAct loop steps (autonomous — OpenClaw drives, not orchestrator):
  1. Reason: read ShiftContext + VLM assessment, identify what info is needed.
  2. Act: call query tools (check_baseline, get_shift_trend, get_recent_interventions).
  3. Observe: incorporate tool results, update reasoning.
  4. Repeat until ready to decide.
  5. Act: call one action tool (trigger_alert | trigger_rest_break | trigger_phone_notify)
     OR decide no intervention needed.
  6. Always call log_intervention last.

Returns InterventionDecision (parsed from the completed OpenClaw session).

Owner: Kevin
Imports from: core.models, agents.tools, llm.client, llm.safety_prompts, llm.parser
"""


def run(context) -> "InterventionDecision":
    """Start an OpenClaw session with Nemotron-Super and return the InterventionDecision.

    Args:
        context: ShiftContext assembled by agents/context_builder.py

    Returns:
        InterventionDecision
    """
    raise NotImplementedError
