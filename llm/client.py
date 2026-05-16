"""NVIDIA Nemotron API client (OpenAI-compatible endpoint).

Shared by the Safety Reasoning Agent and the Companion Agent.
Constructed once in main.py and injected into agents via constructor.

Owner: Kevin
"""
from openai import OpenAI


class NemotronClient:
    """Stateless wrapper around the Nemotron NIM endpoint.

    Args:
        config: SimpleNamespace from load_config(). Reads config.api.* values.
    """

    def __init__(self, config):
        self._client = OpenAI(
            api_key=config.api.nemotron_api_key,
            base_url=config.api.nemotron_base_url,
        )
        self.super_model     = config.api.nemotron_super_model
        self.companion_model = config.api.nemotron_companion_model
        self.vlm_model       = config.api.nemotron_vlm_model

    def complete(
        self,
        model: str,
        messages: list,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def complete_with_tools(
        self,
        model: str,
        messages: list,
        tools: list,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        enable_thinking: bool = False,
    ) -> dict:
        kwargs = dict(
            model=model,
            messages=messages,
            tools=[{"type": "function", "function": t} for t in tools],
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if enable_thinking:
            kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": True},
                "reasoning_budget": 4096,
            }

        response = self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        return {
            "content": message.content,
            "thinking": getattr(message, "reasoning_content", None),
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in (message.tool_calls or [])
            ],
        }
