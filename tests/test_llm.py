"""Tests for llm/ — LLM client layer (Kevin).

Covers: safety prompt rendering, companion prompt rendering, InterventionDecision
parsing, CompanionMessage parsing, edge case model outputs (malformed JSON, empty
response, missing fields).

Owner: Josh (fixtures) / Kevin (test cases)
Imports from: core.models, llm.*
"""
