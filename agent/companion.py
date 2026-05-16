"""Companion agent: proactive conversational engagement to keep a fatiguing driver alert.

When the safety reasoning agent detects building fatigue (severity low/medium, before a
hard intervention is warranted) the companion agent autonomously initiates conversation —
asks an engaging question, tells a short story, proposes a verbal game, or gently
encourages the driver to pull over soon. Uses Nemotron to generate context-aware,
non-repetitive messages keyed to the driver's current fatigue level and shift elapsed time.
Returns a CompanionMessage that the orchestrator displays on-screen or reads aloud.
"""
