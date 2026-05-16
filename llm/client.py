"""NVIDIA Nemotron API client (OpenAI-compatible endpoint).

Shared by both the Safety Reasoning Agent (agents/safety.py) and the Companion Agent
(agents/companion.py). Each agent passes its own system prompt and messages — the
client is stateless and model-agnostic within the Nemotron family.

Model IDs and endpoint URL come from config/settings.py:
  NEMOTRON_SUPER_MODEL   = "nvidia/llama-3_3-nemotron-super-49b-v1_5"
  NEMOTRON_VLM_MODEL     = "nvidia/nemotron-3-nano-omi"
  NEMOTRON_BASE_URL      = "https://integrate.api.nvidia.com/v1"

Usage:
  from llm.client import complete, complete_with_tools

  response = complete(model=settings.NEMOTRON_SUPER_MODEL, messages=[...])
  response = complete_with_tools(model=..., messages=[...], tools=[...])

Owner: Kevin
Imports from: config.settings
"""
from typing import Optional


def complete(model: str, messages: list, temperature: float = 0.2, max_tokens: int = 1024) -> str:
    """Send a chat completion request to the Nemotron endpoint.

    Args:
        model: Nemotron model ID from config/settings.py
        messages: list of {"role": ..., "content": ...} dicts
        temperature: sampling temperature
        max_tokens: max tokens in completion

    Returns:
        Raw completion string from the model
    """
    raise NotImplementedError


def complete_with_tools(
    model: str,
    messages: list,
    tools: list,
    temperature: float = 0.2,
    max_tokens: int = 2048
) -> dict:
    """Send a function-calling request to the Nemotron endpoint.

    Used by agents/safety.py to run the OpenClaw ReAct loop — Nemotron decides
    which tools to call; this function returns the raw response including tool_calls.

    Args:
        model: Nemotron model ID
        messages: conversation history
        tools: list of OpenClaw tool schemas from agents/tools.py
        temperature: sampling temperature
        max_tokens: max tokens

    Returns:
        Raw API response dict (includes tool_calls if model called a tool)
    """
    raise NotImplementedError
