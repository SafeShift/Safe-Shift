# SafeShift

SafeShift is an autonomous driver-safety agent that monitors drivers via camera feed,
analyzes fatigue and distraction signals (eye droopiness, blink rate, yawn frequency,
gaze direction), reasons across a full shift against a per-driver baseline held in
persistent memory, and triggers graduated interventions — in-cab alerts, rest-stop
recommendations, and fleet-manager notifications.

**See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design, interface
contracts, module ownership, and build conventions before touching any code.**

## Quick Start

```bash
cp .env.example .env          # fill in API keys
pip install -r requirements.txt
python -m agent.orchestrator  # starts the agent loop
```

## Team
- Emilio — Vision pipeline + Config
- Kevin — Agent orchestration + Reasoning (Nemotron)
- Josh — Memory + Interventions + Integrations + Deployment
