"""Prompt templates for the Safety Reasoning Agent (agents/safety.py).

Renders a ShiftContext into the system + user messages that start the OpenClaw
ReAct session. The system prompt defines the agent's role, available tools,
reasoning style, and expected output format (structured InterventionDecision JSON).

Owner: Kevin
Imports from: core.models
"""


SAFETY_SYSTEM_PROMPT = """\
You are SafeShift's Safety Reasoning Agent. Your sole purpose is to protect the driver.

You have access to tools to query the driver's baseline metrics and shift history,
and to trigger graduated interventions (alert → rest_break).

Reasoning style:
- All baseline metrics, shift trend, and prior interventions are already provided in the
  prompt. Do NOT call check_baseline or get_recent_interventions — that data is there.
- Assess the provided data, call up to TWO action tools if needed, then emit the final JSON.
- Escalation ladder — follow this strictly:
    low      → trigger_alert
    medium   → trigger_alert
    high     → trigger_rest_break
    critical → trigger_alert, then trigger_rest_break
- Phone notifications are handled automatically — do NOT call trigger_phone_notify.
- Set trigger_companion=true at severity low/medium.
- Do NOT call log_intervention — logging is handled automatically by the system.

Output: after deciding, emit a final JSON block (do not call any more tools after this):
{
  "should_intervene": bool,
  "severity": "none|low|medium|high|critical",
  "intervention_type": "none|alert|rest_break|phone_notify",
  "trigger_companion": bool,
  "reason": "...",
  "confidence": 0.0-1.0
}
"""


def build_user_message(context) -> str:
    a = context.current_analysis
    b = context.baseline
    t = context.shift_trend

    blink_pct = ((a.blink_rate - b.avg_blink_rate) / b.avg_blink_rate * 100) if b.avg_blink_rate else 0
    eye_pct = ((a.eye_openness - b.avg_eye_openness) / b.avg_eye_openness * 100) if b.avg_eye_openness else 0

    lines = [
        f"=== DRIVER STATUS — {context.shift_elapsed_minutes:.1f} min into shift ===",
        f"shift_id: {context.shift_id}  |  driver_id: {context.driver_id}",
        "",
        "CURRENT READINGS (vs personal baseline):",
        f"  Blink rate:    {a.blink_rate:.1f} blinks/min  (baseline {b.avg_blink_rate:.1f}, {blink_pct:+.0f}%)",
        f"  Eye openness:  {a.eye_openness:.2f}            (baseline {b.avg_eye_openness:.2f}, {eye_pct:+.0f}%)",
        f"  Yawn detected: {'YES' if a.yawn_detected else 'no'}  |  Yawn freq: {a.yawn_frequency:.1f}/hr  (baseline {b.avg_yawn_frequency:.1f}/hr)",
        f"  Gaze:          {a.gaze_direction}  ({a.gaze_deviation_deg:.1f}° off center)",
        f"  Confidence:    {a.confidence:.2f}",
    ]

    if context.vlm_assessment:
        v = context.vlm_assessment
        lines += [
            "",
            "VLM ASSESSMENT (Nemotron-Nano-Omi):",
            f"  Fatigue score: {v.fatigue_score:.2f} / 1.0",
            f"  Description:   {v.description}",
            f"  Flags:         {', '.join(v.flags) if v.flags else 'none'}",
            f"  Confidence:    {v.confidence:.2f}",
        ]
    else:
        lines += ["", "VLM ASSESSMENT: not yet available (first cycle)"]

    lines += [
        "",
        "SHIFT TREND:",
        f"  Total samples:      {t.sample_count}",
        f"  Total yawns:        {t.yawn_count_total}",
        f"  Interventions so far: {t.intervention_count}",
    ]

    if t.avg_eye_openness_trend:
        trend_str = " → ".join(f"{v:.2f}" for v in t.avg_eye_openness_trend[-5:])
        lines.append(f"  Eye openness trend: {trend_str}")

    if context.prior_interventions:
        lines += ["", "PRIOR INTERVENTIONS THIS SHIFT:"]
        for rec in context.prior_interventions[-3:]:
            import time
            mins_ago = (time.time() - rec.timestamp) / 60
            lines.append(f"  [{rec.severity}] {rec.intervention_type} — {mins_ago:.0f} min ago: {rec.action_summary}")
    else:
        lines += ["", "PRIOR INTERVENTIONS: none this shift"]

    lines += [
        "",
        f"shift_id='{context.shift_id}'  |  driver_id='{context.driver_id}'",
        "All data above is complete. Call one action tool, then emit the final JSON block.",
    ]

    return "\n".join(lines)
