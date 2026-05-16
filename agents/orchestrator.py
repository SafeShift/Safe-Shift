"""Main per-cycle agent loop for SafeShift.

Per-cycle responsibilities:
1. Receive FrameAnalysis from vision/pipeline.py.
2. Call agents/context_builder.build_context() to assemble ShiftContext.
3. Invoke the Safety Reasoning Agent (agents/safety.py) — OpenClaw ReAct loop with
   Nemotron-Super — to produce InterventionDecision.
4. If decision.trigger_companion: spawn Companion Agent (agents/companion.py) in
   parallel; dispatch CompanionMessage to display/TTS.
5. If decision.should_intervene: dispatch the appropriate action handler via OpenClaw
   tool call (actions/alert, rest_break, or phone_notify).
6. Write the returned InterventionRecord to memory/shift_history.
7. Always call actions/logging_client every cycle regardless of should_intervene.
8. Publish all events to api/events.py for the frontend SSE stream.

Owner: Kevin
Imports from: core.models, agents.context_builder, agents.safety, agents.companion,
              agents.tools, actions.*, memory.shift_history, api.events
"""
