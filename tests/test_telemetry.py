from workbench import telemetry


def test_cost_needs_both_prices():
    assert telemetry.cost_usd(100, 100, None, 1.0) is None
    assert telemetry.cost_usd(1_000_000, 1_000_000, 3.0, 15.0) == 18.0


def test_log_and_summarize(tmp_path):
    log = tmp_path / "calls.jsonl"
    assert telemetry.summarize(log) == {"calls": 0}
    telemetry.log_call(log, {"input_tokens": 10, "output_tokens": 5, "latency_ms": 100, "cost_usd": 0.01})
    telemetry.log_call(log, {"input_tokens": 20, "output_tokens": 5, "latency_ms": 300, "cost_usd": None})
    s = telemetry.summarize(log)
    assert s == {"calls": 2, "input_tokens": 30, "output_tokens": 10,
                 "avg_latency_ms": 200, "total_cost_usd": 0.01}
