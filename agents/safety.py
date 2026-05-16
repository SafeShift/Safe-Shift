"""Safety Reasoning Agent — Nemotron-Super ReAct loop."""
import json
import logging
import time

from config.settings import config
from core.models import InterventionDecision
from llm.client import complete_with_tools
from llm.safety_prompts import SAFETY_SYSTEM_PROMPT, build_user_message
from llm.parser import parse_intervention_decision
from agents.tools import TOOLS, TOOL_HANDLERS

logger = logging.getLogger(__name__)

MAX_REACT_STEPS = 8  # max tool calls before forcing a decision


def run(context) -> InterventionDecision:
    messages = [
        {"role": "system", "content": SAFETY_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(context)},
    ]

    for step in range(MAX_REACT_STEPS):
        response = complete_with_tools(
            model=config.api.nemotron_super_model,
            messages=messages,
            tools=TOOLS,
            enable_thinking=True,
        )

        if response.get("thinking"):
            logger.info("[Safety Agent thinking]\n%s", response["thinking"])

        # no tool calls — model is done, parse the decision
        if not response["tool_calls"]:
            return _parse_or_fallback(response["content"])

        # append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": response["content"],
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in response["tool_calls"]
            ],
        })

        # execute each tool and feed results back
        for tc in response["tool_calls"]:
            handler = TOOL_HANDLERS.get(tc["name"])
            if handler is None:
                result = {"error": f"unknown tool: {tc['name']}"}
            else:
                try:
                    args = json.loads(tc["arguments"])
                    # inject shift_id and driver_id so handlers have context
                    args.setdefault("shift_id", context.shift_id)
                    args.setdefault("driver_id", context.driver_id)
                    result = handler(**args)
                except Exception as e:
                    result = {"error": str(e)}

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result),
            })

    # hit max steps — force a final completion with no tools
    final = complete_with_tools(
        model=config.api.nemotron_super_model,
        messages=messages + [{"role": "user", "content": "Emit your final JSON decision now."}],
        tools=[],
    )
    return _parse_or_fallback(final["content"])


def _parse_or_fallback(raw: str) -> InterventionDecision:
    try:
        return parse_intervention_decision(raw, timestamp=time.time())
    except ValueError:
        logger.warning("Failed to parse InterventionDecision — returning safe fallback")
        return InterventionDecision(
            should_intervene=False,
            severity="none",
            intervention_type="none",
            trigger_companion=False,
            reason="Parse error — defaulting to no intervention",
            confidence=0.0,
            timestamp=time.time(),
        )
