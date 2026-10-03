"""Raw-HTTP client for the Anthropic Messages API. No SDK on purpose: v0 is about learning HTTP."""
import time

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def create(messages: list[dict], *, api_key: str, model: str, max_tokens: int = 1024,
           tools: list[dict] | None = None, system: str | None = None,
           client: httpx.Client | None = None) -> tuple[dict, int]:
    """POST one Messages request. Returns (raw response JSON, latency in ms)."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if tools:
        body["tools"] = tools
    if system:
        body["system"] = system

    own_client = client is None
    client = client or httpx.Client(timeout=60)
    try:
        start = time.perf_counter()
        resp = client.post(API_URL, headers=headers, json=body)
        latency_ms = round((time.perf_counter() - start) * 1000)
    finally:
        if own_client:
            client.close()

    resp.raise_for_status()
    return resp.json(), latency_ms


def text_of(data: dict) -> str:
    return "".join(b["text"] for b in data["content"] if b["type"] == "text")


def usage_record(data: dict, latency_ms: int) -> dict:
    return {
        "model": data["model"],
        "input_tokens": data["usage"]["input_tokens"],
        "output_tokens": data["usage"]["output_tokens"],
        "latency_ms": latency_ms,
    }


def send(prompt: str, *, api_key: str, model: str, max_tokens: int = 1024,
         client: httpx.Client | None = None) -> dict:
    data, latency_ms = create([{"role": "user", "content": prompt}], api_key=api_key,
                              model=model, max_tokens=max_tokens, client=client)
    return {"text": text_of(data), **usage_record(data, latency_ms)}
