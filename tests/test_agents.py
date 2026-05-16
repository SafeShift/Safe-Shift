"""Tests for agents/ — Safety Reasoning Agent and Companion Agent.

Covers: Safety Agent ReAct loop (mocked OpenClaw), correct InterventionDecision
produced per scenario; Companion Agent message generation, deduplication logic.

Owner: Josh (fixtures) / Kevin + Emilio (test cases)
Imports from: core.models, agents.safety, agents.companion
"""
