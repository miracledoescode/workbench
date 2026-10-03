"""Agent loop: call the model, run any tools it asks for, feed results back, repeat until it stops."""
from collections.abc import Callable

import httpx

from . import client, tools


def run(prompt: str, *, api_key: str, model: str, max_tokens: int = 1024, max_turns: int = 10,
        tool_names: list[str] | None = None, on_call: Callable[[dict], None] | None = None,
        on_tool: Callable[[str, dict, str, bool], None] | None = None,
        http: httpx.Client | None = None) -> dict:
    """Returns {"text", "turns", "stop_reason", "messages"}. `on_call` gets one usage record per API call."""
    names = tool_names or list(tools.TOOLS)
    schemas = [tools.TOOLS[n]["schema"] for n in names]
    messages = [{"role": "user", "content": prompt}]

    for turn in range(1, max_turns + 1):
        data, latency_ms = client.create(messages, api_key=api_key, model=model,
                                         max_tokens=max_tokens, tools=schemas, client=http)
        if on_call:
            on_call(client.usage_record(data, latency_ms) | {"turn": turn})
        messages.append({"role": "assistant", "content": data["content"]})

        if data["stop_reason"] != "tool_use":
            return {"text": client.text_of(data), "turns": turn,
                    "stop_reason": data["stop_reason"], "messages": messages}

        results = []
        for block in data["content"]:
            if block["type"] != "tool_use":
                continue
            output, is_error = (tools.run(block["name"], block["input"]) if block["name"] in names
                                else (f"tool not enabled: {block['name']}", True))
            if on_tool:
                on_tool(block["name"], block["input"], output, is_error)
            results.append({"type": "tool_result", "tool_use_id": block["id"],
                            "content": output, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    return {"text": "", "turns": max_turns, "stop_reason": "max_turns", "messages": messages}
