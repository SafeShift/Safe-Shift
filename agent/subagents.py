"""Multi-agent configuration for SafeShift.

Declares the three specialized agent roles and their model assignments:
  - Perception Agent: Nemotron-3-Nano-Omi (VLM) — scene-level fatigue assessment
  - Safety Reasoning Agent: Nemotron-Super (llama-3_3-nemotron-super-49b-v1_5) — multi-step
    shift analysis, intervention planning, ReAct reasoning loop
  - Companion Agent: Nemotron-Super — proactive driver conversation generation

Orchestrator imports agent handles from here; model IDs and endpoint configs come from
config/settings.py so they can be swapped without touching agent logic.
"""
