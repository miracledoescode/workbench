import json

import httpx
import pytest

from workbench import agent, tools


def _resp(content, stop_reason, i=10, o=5):
    return {"model": "m", "content": content, "stop_reason": stop_reason,
            "usage": {"input_tokens": i, "output_tokens": o}}


def test_agent_runs_tool_and_returns_final_text():
    bodies = []
    replies = iter([
        _resp([{"type": "text", "text": "Let me compute."},
               {"type": "tool_use", "id": "t1", "name": "calculator", "input": {"expression": "6*7"}}],
              "tool_use"),
        _resp([{"type": "text", "text": "It is 42."}], "end_turn"),
    ])

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=next(replies))

    calls = []
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        out = agent.run("6*7?", api_key="k", model="m", on_call=calls.append, http=c)

    assert out["text"] == "It is 42."
    assert out["turns"] == 2 and out["stop_reason"] == "end_turn"
    assert [r["turn"] for r in calls] == [1, 2]
    assert {t["name"] for t in bodies[0]["tools"]} == set(tools.TOOLS)
    result = bodies[1]["messages"][-1]["content"][0]
    assert result == {"type": "tool_result", "tool_use_id": "t1", "content": "42", "is_error": False}


def test_agent_stops_at_max_turns():
    loop = _resp([{"type": "tool_use", "id": "t", "name": "current_time", "input": {}}], "tool_use")
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=loop))) as c:
        out = agent.run("x", api_key="k", model="m", max_turns=3, http=c)
    assert out["stop_reason"] == "max_turns" and out["turns"] == 3


def test_disabled_tool_is_reported_as_error():
    bodies = []
    replies = iter([
        _resp([{"type": "tool_use", "id": "t", "name": "read_file", "input": {"path": "x"}}], "tool_use"),
        _resp([{"type": "text", "text": "ok"}], "end_turn"),
    ])

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=next(replies))

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        agent.run("x", api_key="k", model="m", tool_names=["calculator"], http=c)
    assert [t["name"] for t in bodies[0]["tools"]] == ["calculator"]
    assert bodies[1]["messages"][-1]["content"][0]["is_error"] is True


def test_calculator_rejects_code():
    assert tools.calculator("2 ** 10 + 1") == "1025"
    with pytest.raises(ValueError):
        tools.calculator("__import__('os')")


def test_read_file_is_sandboxed(tmp_path):
    (tmp_path / "a.txt").write_text("hi")
    assert tools.read_file("a.txt", root=tmp_path) == "hi"
    with pytest.raises(ValueError):
        tools.read_file("../etc/passwd", root=tmp_path)


def test_run_turns_exceptions_into_errors():
    out, is_error = tools.run("calculator", {"expression": "1/0"})
    assert is_error and "ZeroDivisionError" in out
    assert tools.run("nope", {}) == ("unknown tool: nope", True)
