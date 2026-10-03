import argparse
import json
import os
import sys
from pathlib import Path

import httpx

from . import agent, client, telemetry, tools


def _env_float(name: str) -> float | None:
    value = os.environ.get(name)
    return float(value) if value else None


def _config() -> dict | None:
    """Provider settings from env. Returns None (after printing why) if incomplete."""
    provider = os.environ.get("WORKBENCH_PROVIDER", "anthropic")
    model = os.environ.get("WORKBENCH_MODEL")
    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or not model:
            print("Set ANTHROPIC_API_KEY and WORKBENCH_MODEL (see .env.example).", file=sys.stderr)
            return None
        return {"provider": provider, "api_key": api_key, "model": model}
    if provider == "openai":
        base_url = os.environ.get("WORKBENCH_BASE_URL")
        if not base_url or not model:
            print("Set WORKBENCH_BASE_URL and WORKBENCH_MODEL (see .env.example).", file=sys.stderr)
            return None
        return {"provider": provider, "base_url": base_url, "model": model,
                "api_key": os.environ.get("WORKBENCH_API_KEY", "")}
    print(f"Unknown WORKBENCH_PROVIDER {provider!r}; use 'anthropic' or 'openai'.", file=sys.stderr)
    return None


def cmd_ask(args) -> int:
    cfg = _config()
    if cfg is None:
        return 1

    try:
        result = client.send(args.prompt, max_tokens=args.max_tokens, **cfg)
    except httpx.HTTPStatusError as e:
        print(f"API error {e.response.status_code}: {e.response.text}", file=sys.stderr)
        return 1

    cost = telemetry.cost_usd(result["input_tokens"], result["output_tokens"],
                              _env_float("WORKBENCH_PRICE_IN"), _env_float("WORKBENCH_PRICE_OUT"))
    record = {k: v for k, v in result.items() if k != "text"} | {"cost_usd": cost}
    telemetry.log_call(Path(args.log), record)

    print(result["text"])
    print(f"\n[{result['input_tokens']} in / {result['output_tokens']} out · "
          f"{result['latency_ms']} ms · cost {cost if cost is not None else 'n/a'}]", file=sys.stderr)
    return 0


def cmd_agent(args) -> int:
    cfg = _config()
    if cfg is None:
        return 1

    price_in, price_out = _env_float("WORKBENCH_PRICE_IN"), _env_float("WORKBENCH_PRICE_OUT")
    totals = {"input_tokens": 0, "output_tokens": 0, "latency_ms": 0}

    def on_call(record):
        cost = telemetry.cost_usd(record["input_tokens"], record["output_tokens"], price_in, price_out)
        telemetry.log_call(Path(args.log), record | {"cost_usd": cost, "kind": "agent"})
        for k in totals:
            totals[k] += record[k]

    def on_tool(name, tool_input, output, is_error):
        status = "error" if is_error else "ok"
        print(f"[tool] {name}({json.dumps(tool_input)}) -> {status}: {output[:200]}", file=sys.stderr)

    try:
        result = agent.run(args.prompt, max_tokens=args.max_tokens, **cfg,
                           max_turns=args.max_turns, tool_names=args.tools,
                           on_call=on_call, on_tool=on_tool)
    except httpx.HTTPStatusError as e:
        print(f"API error {e.response.status_code}: {e.response.text}", file=sys.stderr)
        return 1

    print(result["text"])
    cost = telemetry.cost_usd(totals["input_tokens"], totals["output_tokens"], price_in, price_out)
    print(f"\n[{result['turns']} turns · stop: {result['stop_reason']} · "
          f"{totals['input_tokens']} in / {totals['output_tokens']} out · "
          f"{totals['latency_ms']} ms · cost {cost if cost is not None else 'n/a'}]", file=sys.stderr)
    return 0 if result["stop_reason"] != "max_turns" else 2


def cmd_stats(args) -> int:
    print(json.dumps(telemetry.summarize(Path(args.log)), indent=2))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="workbench", description="AI solutions workbench (v0).")
    parser.add_argument("--log", default=os.environ.get("WORKBENCH_LOG", ".workbench/calls.jsonl"))
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Send a prompt and log tokens/latency/cost.")
    ask.add_argument("prompt")
    ask.add_argument("--max-tokens", type=int, default=1024)
    ask.set_defaults(func=cmd_ask)

    ag = sub.add_parser("agent", help="Run a tool-calling agent loop; logs every API call.")
    ag.add_argument("prompt")
    ag.add_argument("--max-tokens", type=int, default=1024)
    ag.add_argument("--max-turns", type=int, default=10)
    ag.add_argument("--tools", nargs="+", choices=list(tools.TOOLS), default=None,
                    help="Tools to enable (default: all).")
    ag.set_defaults(func=cmd_agent)

    stats = sub.add_parser("stats", help="Summarize logged calls.")
    stats.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
