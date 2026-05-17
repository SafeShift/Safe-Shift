# SafeShift

SafeShift is a privacy-first, multi-agent driver fatigue detection system built for long-haul truckers. It monitors the driver in real time via webcam, analyzes fatigue signals (eye droopiness, blink rate, yawn frequency, gaze direction) using MediaPipe face landmarks, and reasons against a per-driver baseline stored in persistent SQLite memory. When fatigue is detected, it triggers graduated interventions — in-cab audio/visual alerts, nearby rest-stop recommendations, and push notifications to the driver's phone — all without sending data to a fleet employer.

**See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design, interface
contracts, module ownership, and build conventions before touching any code.**

## Quick Start

```bash
cp .env.example .env          # fill in API keys
pip install -r requirements.txt
python -m demo.seed_db        # seed driver baseline
python main.py                # start the agent loop
```

Open `http://localhost:8080` for the live monitoring dashboard.

## Team
- **Caleb** — Overall architecture design, vision pipeline, MediaPipe face landmark model, feature extraction (yawning, blinking, gaze), Brev deployment, system optimization, UI layout
- **Kevin** — Safety Reasoning Agent (Nemotron-Super, ReAct loop, tool calling, chain-of-thought), persistent SQLite driver baseline and shift memory, SSE intervention events wired to the live frontend dashboard with Leaflet.js rest stop map
- **Emilio** — Companion Agent (Nemotron + edge-TTS/AriaNeural), orchestration pipeline, per-severity cooldown system, push notifications (ntfy), safety agent prompt tuning
- **Josh** — Frontend monitoring dashboard, helped shape the original concept
