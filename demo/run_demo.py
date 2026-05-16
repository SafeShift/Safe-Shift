"""Standalone demo: start FastAPI server + replay fake fatigue events.

No camera or NEMOTRON_API_KEY required. Feeds all 6 SSE event types into the
dashboard so every panel lights up.

Usage:
    cd Safe-Shift
    python3 demo/run_demo.py [mild|moderate|severe]

Open http://localhost:8080 while it runs.
"""

import dataclasses
import os
import sys
import time
import threading
import uuid

# Ensure NEMOTRON_API_KEY is set so config.settings doesn't crash,
# but don't require a real key for demo purposes.
os.environ.setdefault("NEMOTRON_API_KEY", "demo-key")

import uvicorn
from api.server import app
import api.events as events
from demo.simulate_fatigue import get_scenario_frames
from core.models import (
    VLMFrameAssessment,
    InterventionDecision,
    CompanionMessage,
    InterventionRecord,
    AuditEntry,
)


SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "moderate"
SHIFT_ID = str(uuid.uuid4())[:8]
DRIVER_ID = "Trucker Tom"

# ── VLM flag banks per fatigue level ─────────────────────────────────────────

def _vlm_flags(eye_openness: float) -> list:
    if eye_openness > 0.65:
        return []
    if eye_openness > 0.50:
        return ["eyes_drooping"]
    if eye_openness > 0.38:
        return ["eyes_drooping", "head_tilt"]
    return ["eyes_drooping", "head_tilt", "yawning", "microsleep_risk"]


def _vlm_description(eye_openness: float) -> str:
    if eye_openness > 0.65:
        return "Driver appears alert; eye contact steady, posture upright."
    if eye_openness > 0.50:
        return "Mild fatigue signs — eyelids slightly heavy, gaze softening."
    if eye_openness > 0.38:
        return "Moderate fatigue — head drooping forward, eyes half-closed."
    return "Severe fatigue — driver's head lolling, eyes barely open, micro-sleep risk."


def _severity(eye_openness: float) -> str:
    if eye_openness > 0.65: return "none"
    if eye_openness > 0.55: return "low"
    if eye_openness > 0.44: return "medium"
    if eye_openness > 0.34: return "high"
    return "critical"


# ── Publisher thread ──────────────────────────────────────────────────────────

def _publish_events():
    time.sleep(1.5)   # wait for uvicorn to be ready

    frames = get_scenario_frames(SCENARIO)
    vlm_cycle = 0
    prev_severity_rank = 0
    severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

    for i, frame in enumerate(frames):
        # ── Panel 1: frame event every 2 s ───────────────────────────────────
        events.publish("frame", {
            **dataclasses.asdict(frame),
            "shift_id": SHIFT_ID,
        })

        # ── Panel 2: VLM event every ~10 s (5 frame cycles) ──────────────────
        if i % 5 == 0:
            vlm_cycle += 1
            score = max(0.0, min(1.0, 1.0 - frame.eye_openness / 0.74))
            vlm = VLMFrameAssessment(
                timestamp=frame.timestamp,
                driver_id=DRIVER_ID,
                fatigue_score=round(score, 2),
                description=_vlm_description(frame.eye_openness),
                flags=_vlm_flags(frame.eye_openness),
                confidence=0.91,
            )
            events.publish("vlm", dataclasses.asdict(vlm))
            events.publish("audit", dataclasses.asdict(AuditEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=frame.timestamp,
                source="perception",
                action_type="api_call",
                description=f"vlm_assess(fatigue_score={score:.2f}, flags={vlm.flags})",
                verdict="allowed",
                metadata={"model": "nemotron-3-nano-omni", "cycle": vlm_cycle},
            )))

        # ── Panel 3: safety decision every cycle ─────────────────────────────
        sev = _severity(frame.eye_openness)
        sev_rank = severity_rank[sev]
        should_intervene = sev in ("medium", "high", "critical")
        trigger_companion = sev_rank >= 1

        decision = InterventionDecision(
            should_intervene=should_intervene,
            severity=sev,
            intervention_type="alert" if should_intervene else "none",
            trigger_companion=trigger_companion,
            reason=f"Eye openness {frame.eye_openness:.2f} — {_vlm_description(frame.eye_openness)}",
            confidence=0.88,
            timestamp=frame.timestamp,
        )
        events.publish("decision", {
            **dataclasses.asdict(decision),
            "driver_id": DRIVER_ID,
            "shift_id": SHIFT_ID,
        })
        events.publish("audit", dataclasses.asdict(AuditEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=frame.timestamp,
            source="safety",
            action_type="decision",
            description=f"severity={sev}, intervene={should_intervene}, companion={trigger_companion}",
            verdict="allowed",
            metadata={"confidence": 0.88},
        )))

        # ── NemoClaw audit on escalation ─────────────────────────────────────
        if sev_rank > prev_severity_rank:
            events.publish("audit", dataclasses.asdict(AuditEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=frame.timestamp,
                source="nemoclaw",
                action_type="policy_event",
                description=f"severity_escalation: {list(severity_rank.keys())[prev_severity_rank]} → {sev}",
                verdict="allowed",
                metadata={},
            )))
        prev_severity_rank = sev_rank

        # ── Panel 4: companion message on first entry to each severity ────────
        if trigger_companion and sev_rank > 0 and i % 15 == 0:
            messages = {
                "low": "Hey, how are you holding up out there?",
                "medium": "You've been on the road a while — want to hear some music?",
                "high": "I'm noticing you seem tired. There's a rest stop 4 miles ahead.",
                "critical": "Please pull over safely — you need a rest break now.",
            }
            companion = CompanionMessage(
                timestamp=frame.timestamp,
                driver_id=DRIVER_ID,
                message=messages.get(sev, "Stay alert out there."),
                trigger_reason="fatigue_building",
                severity_context=sev,
            )
            events.publish("companion", dataclasses.asdict(companion))
            events.publish("audit", dataclasses.asdict(AuditEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=frame.timestamp,
                source="companion",
                action_type="decision",
                description=f"companion_message(severity={sev}, trigger=fatigue_building)",
                verdict="allowed",
                metadata={"model": "nemotron-super"},
            )))

        # ── Panel 5: intervention record when should_intervene ────────────────
        if should_intervene and i % 20 == 0:
            stops = ["Rest Stop 7 (4.2 mi)", "Pilot Travel Center (8.1 mi)"] if sev in ("high", "critical") else []
            record = InterventionRecord(
                intervention_id=str(uuid.uuid4()),
                driver_id=DRIVER_ID,
                shift_id=SHIFT_ID,
                timestamp=frame.timestamp,
                severity=sev,
                intervention_type="rest_break" if sev in ("high", "critical") else "alert",
                action_summary=f"Fatigue {sev}: {_vlm_description(frame.eye_openness)}",
                suggested_stops=stops,
            )
            events.publish("intervention", dataclasses.asdict(record))
            verdict = "blocked" if sev == "critical" and i % 40 == 0 else "allowed"
            events.publish("audit", dataclasses.asdict(AuditEntry(
                entry_id=str(uuid.uuid4()),
                timestamp=frame.timestamp,
                source="nemoclaw",
                action_type="policy_event",
                description=f"trigger_intervention(type={record.intervention_type}, severity={sev})",
                verdict=verdict,
                metadata={"intervention_id": record.intervention_id},
            )))

        time.sleep(0.4)   # 0.4 s per frame → 5× faster than real-time for demo

    print("\nScenario complete. Ctrl-C to stop.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Starting SafeShift demo  scenario={SCENARIO}  shift={SHIFT_ID}")
    print("Open http://localhost:8080 in your browser.\n")

    t = threading.Thread(target=_publish_events, daemon=True)
    t.start()

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
