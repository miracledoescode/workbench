import json

import httpx

from workbench import agent, client, openai_compat


def test_request_translation():
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "calling"},
            {"type": "tool_use", "id": "c1", "name": "calculator", "input": {"expression": "1+1"}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "c1", "content": "boom", "is_error": True}]},
    ]
    tool = {"name": "calculator", "description": "d", "input_schema": {"type": "object"}}
    body = openai_compat.to_request(msgs, model="m", max_tokens=9, tools=[tool], system="sys")

    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["messages"][2]["tool_calls"][0]["function"] == {
        "name": "calculator", "arguments": '{"expression": "1+1"}'}
    assert body["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": "ERROR: boom"}
    assert body["tools"][0]["function"]["parameters"] == {"type": "object"}


def test_response_translation():
    data = {"choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "calculator", "arguments": "not json"}}]}}],
        "usage": {"prompt_tokens": 7, "completion_tokens": 2}}
    out = openai_compat.from_response(data, "m")
    assert out["stop_reason"] == "tool_use"
    assert out["content"][0]["input"] == {"_unparsed_arguments": "not json"}
    assert out["usage"] == {"input_tokens": 7, "output_tokens": 2} and out["model"] == "m"

    plain = {"choices": [{"finish_reason": "length", "message": {"content": "hi"}}]}
    out = openai_compat.from_response(plain, "m")
    assert out["stop_reason"] == "max_tokens" and out["usage"] == {"input_tokens": 0, "output_tokens": 0}


def test_agent_loop_over_openai_provider():
    seen = []
    replies = iter([
        {"model": "m", "usage": {"prompt_tokens": 5, "completion_tokens": 1},
         "choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
             {"id": "c1", "type": "function",
              "function": {"name": "calculator", "arguments": '{"expression": "6*7"}'}}]}}]},
        {"model": "m", "usage": {"prompt_tokens": 9, "completion_tokens": 3},
         "choices": [{"finish_reason": "stop", "message": {"content": "42"}}]},
    ])

    def handler(request):
        seen.append((str(request.url), request.headers.get("authorization"), json.loads(request.content)))
        return httpx.Response(200, json=next(replies))

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        out = agent.run("6*7?", api_key="", model="m", provider="openai",
                        base_url="http://localhost:11434/v1/", http=c)

    assert out["text"] == "42" and out["turns"] == 2
    assert seen[0][0] == "http://localhost:11434/v1/chat/completions"
    assert seen[0][1] is None  # no key -> no auth header
    assert seen[1][2]["messages"][-1] == {"role": "tool", "tool_call_id": "c1", "content": "42"}


def test_send_with_key_sets_bearer():
    def handler(request):
        assert request.headers["authorization"] == "Bearer k"
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        out = client.send("hi", api_key="k", model="m", provider="openai", base_url="http://x/v1", client=c)
    assert out["text"] == "ok"
