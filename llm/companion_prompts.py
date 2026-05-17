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
  low      → casual, curious, light ("Hey, what's your favourite road trip snack?")
  medium   → warmer, proactive ("You've been driving a while — want to find a stop soon?")
  high     → gentle but direct ("I really think we should pull over. I found a stop nearby.")
  critical → urgent, clear, no small talk ("Please pull over now — there's a safe stop just ahead. Your safety comes first.")

Rules:
- Stay strictly on topic: driver fatigue, rest breaks, staying alert. Never comment on weather, scenery, or anything unrelated to driving safety.
- Never repeat a message said in the last 10 minutes.
- Never mention "fatigue score" or internal metrics to the driver.
- Keep messages under 2 sentences.
- Make statements only. Never ask the driver a question — this is one-way audio, they cannot respond.
- Examples: "Your eyes look a little heavy — there's a rest stop coming up in a few miles." / "You've been at it a while. A short break now will keep you sharp for the rest of the drive."

IMPORTANT: Reply with ONLY the message itself. No preamble, no explanation, no quotes.
Just the words the companion would say out loud. Nothing else.
"""


def build_user_message(context, prior_messages: list, severity: str) -> str:
    """Render ShiftContext and prior messages into the companion user-turn prompt.

    Args:
        context: ShiftContext
        prior_messages: list[CompanionMessage] — this shift, for deduplication context
        severity: current severity level from InterventionDecision

    Returns:
        Formatted string describing driver state and conversation history
    """
    import time
    a = context.current_analysis
    b = context.baseline
    t = context.shift_trend

    eye_pct = ((a.eye_openness - b.avg_eye_openness) / b.avg_eye_openness * 100) if b.avg_eye_openness else 0
    blink_pct = ((a.blink_rate - b.avg_blink_rate) / b.avg_blink_rate * 100) if b.avg_blink_rate else 0

    lines = [
        f"Driver: {context.driver_id} | Shift duration: {context.shift_elapsed_minutes:.0f} min",
        f"Severity: {severity}",
        "",
        "Current fatigue indicators:",
        f"  Eye openness : {a.eye_openness:.2f}  (baseline {b.avg_eye_openness:.2f}, {eye_pct:+.0f}%)",
        f"  Blink rate   : {a.blink_rate:.1f}/min  (baseline {b.avg_blink_rate:.1f}/min, {blink_pct:+.0f}%)",
        f"  Yawn detected: {a.yawn_detected}  |  Yawn freq: {a.yawn_frequency:.1f}/hr",
        f"  Gaze         : {a.gaze_direction}  ({a.gaze_deviation_deg:.1f}° off-center)",
    ]

    if t.avg_eye_openness_trend:
        trend = " → ".join(f"{v:.2f}" for v in t.avg_eye_openness_trend[-5:])
        lines.append(f"  Eye trend (buckets): {trend}")

    if context.vlm_assessment:
        lines.append(f"  VLM: \"{context.vlm_assessment.description}\"")

    if prior_messages:
        lines += ["", "Recent messages (do not repeat these):"]
        now = time.time()
        for msg in prior_messages[-5:]:
            mins = (now - msg.timestamp) / 60
            lines.append(f"  - \"{msg.message}\"  ({mins:.0f} min ago)")

    lines += ["", f"Generate one companion message for severity={severity}."]
    return "\n".join(lines)
