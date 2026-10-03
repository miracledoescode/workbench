"""Adapter for OpenAI-compatible /chat/completions endpoints (Gemini, Groq, OpenRouter, Ollama, ...).

The rest of workbench speaks the Anthropic Messages shape; this module translates the request
on the way out and the response on the way back, so the agent loop doesn't change.
"""
import json


def to_request(messages: list[dict], *, model: str, max_tokens: int,
               tools: list[dict] | None, system: str | None) -> dict:
    out = [{"role": "system", "content": system}] if system else []
    for m in messages:
        if isinstance(m["content"], str):
            out.append({"role": m["role"], "content": m["content"]})
        elif m["role"] == "assistant":
            text = "".join(b["text"] for b in m["content"] if b["type"] == "text")
            calls = [{"id": b["id"], "type": "function",
                      "function": {"name": b["name"], "arguments": json.dumps(b["input"])}}
                     for b in m["content"] if b["type"] == "tool_use"]
            msg = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
        else:  # user turn carrying tool results
            for b in m["content"]:
                if b["type"] == "tool_result":
                    content = ("ERROR: " if b.get("is_error") else "") + b["content"]
                    out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": content})
                elif b["type"] == "text":
                    out.append({"role": "user", "content": b["text"]})

    body = {"model": model, "max_tokens": max_tokens, "messages": out}
    if tools:
        body["tools"] = [{"type": "function",
                          "function": {"name": t["name"], "description": t["description"],
                                       "parameters": t["input_schema"]}} for t in tools]
    return body


def _parse_args(raw: str | None) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"_unparsed_arguments": raw}  # tool call fails; the model sees the error and retries


def from_response(data: dict, model: str) -> dict:
    choice = data["choices"][0]
    msg = choice["message"]
    content = [{"type": "text", "text": msg["content"]}] if msg.get("content") else []
    for c in msg.get("tool_calls") or []:
        content.append({"type": "tool_use", "id": c["id"], "name": c["function"]["name"],
                        "input": _parse_args(c["function"].get("arguments"))})

    if any(b["type"] == "tool_use" for b in content):
        stop = "tool_use"
    elif choice.get("finish_reason") == "length":
        stop = "max_tokens"
    else:
        stop = "end_turn"

    usage = data.get("usage") or {}
    return {
        "model": data.get("model", model),
        "content": content,
        "stop_reason": stop,
        "usage": {"input_tokens": usage.get("prompt_tokens", 0),
                  "output_tokens": usage.get("completion_tokens", 0)},
    }
