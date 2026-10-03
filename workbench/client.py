"""Raw-HTTP client for the Anthropic Messages API. No SDK on purpose: v0 is about learning HTTP."""
import time

import httpx

from . import openai_compat

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def create(messages: list[dict], *, api_key: str, model: str, max_tokens: int = 1024,
           tools: list[dict] | None = None, system: str | None = None,
           provider: str = "anthropic", base_url: str | None = None,
           client: httpx.Client | None = None) -> tuple[dict, int]:
    """POST one request. Returns (response in Anthropic Messages shape, latency in ms).

    provider="openai" sends to `{base_url}/chat/completions` and translates both directions.
    """
    if provider == "openai":
        if not base_url:
            raise ValueError("provider 'openai' needs a base_url")
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {"content-type": "application/json"}
        if api_key:  # local servers like Ollama need no key
            headers["authorization"] = f"Bearer {api_key}"
        body = openai_compat.to_request(messages, model=model, max_tokens=max_tokens,
                                        tools=tools, system=system)
    else:
        url = API_URL
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
        resp = client.post(url, headers=headers, json=body)
        latency_ms = round((time.perf_counter() - start) * 1000)
    finally:
        if own_client:
            client.close()

    resp.raise_for_status()
    data = resp.json()
    if provider == "openai":
        data = openai_compat.from_response(data, model)
    return data, latency_ms


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
         provider: str = "anthropic", base_url: str | None = None,
         client: httpx.Client | None = None) -> dict:
    data, latency_ms = create([{"role": "user", "content": prompt}], api_key=api_key,
                              model=model, max_tokens=max_tokens, provider=provider,
                              base_url=base_url, client=client)
    return {"text": text_of(data), **usage_record(data, latency_ms)}
