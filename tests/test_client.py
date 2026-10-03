import httpx

from workbench import client

FAKE = {
    "model": "test-model",
    "content": [{"type": "text", "text": "Hello"}],
    "usage": {"input_tokens": 10, "output_tokens": 3},
}


def test_send_builds_request_and_parses_response():
    seen = {}

    def handler(request: httpx.Request):
        seen["headers"] = request.headers
        seen["url"] = str(request.url)
        return httpx.Response(200, json=FAKE)

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        out = client.send("hi", api_key="k", model="test-model", client=c)

    assert seen["url"] == client.API_URL
    assert seen["headers"]["x-api-key"] == "k"
    assert seen["headers"]["anthropic-version"] == client.API_VERSION
    assert out["text"] == "Hello"
    assert (out["input_tokens"], out["output_tokens"]) == (10, 3)
    assert out["latency_ms"] >= 0
