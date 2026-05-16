"""NVIDIA Nemotron API client (OpenAI-compatible endpoint).

Shared by both the Safety Reasoning Agent (agents/safety.py) and the Companion Agent
(agents/companion.py). Each agent passes its own system prompt and messages — the
client is stateless and model-agnostic within the Nemotron family.

Owner: Kevin
Imports from: config.settings
"""
from openai import OpenAI
from config.settings import config

_client = OpenAI(
    api_key=config.api.nemotron_api_key,
    base_url=config.api.nemotron_base_url,
)


def complete(model: str, messages: list, temperature: float = 0.2, max_tokens: int = 1024) -> str:
    response = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def complete_with_tools(
    model: str,
    messages: list,
    tools: list,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> dict:
    response = _client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[{"type": "function", "function": t} for t in tools],
        tool_choice="auto",
        temperature=temperature,
        max_tokens=max_tokens,
    )
    message = response.choices[0].message
    return {
        "content": message.content,
        "tool_calls": [
            {
                "id": tc.id,
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            }
            for tc in (message.tool_calls or [])
        ],
    }
