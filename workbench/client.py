"""Raw-HTTP client for the Anthropic Messages API. No SDK on purpose: v0 is about learning HTTP."""
import time

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def send(prompt: str, *, api_key: str, model: str, max_tokens: int = 1024,
         client: httpx.Client | None = None) -> dict:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

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
    data = resp.json()
    return {
        "text": "".join(b["text"] for b in data["content"] if b["type"] == "text"),
        "model": data["model"],
        "input_tokens": data["usage"]["input_tokens"],
        "output_tokens": data["usage"]["output_tokens"],
        "latency_ms": latency_ms,
    }
