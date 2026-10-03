import argparse
import json
import os
import sys
from pathlib import Path

import httpx

from . import client, telemetry


def _env_float(name: str) -> float | None:
    value = os.environ.get(name)
    return float(value) if value else None


def cmd_ask(args) -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("WORKBENCH_MODEL")
    if not api_key or not model:
        print("Set ANTHROPIC_API_KEY and WORKBENCH_MODEL (see .env.example).", file=sys.stderr)
        return 1

    try:
        result = client.send(args.prompt, api_key=api_key, model=model, max_tokens=args.max_tokens)
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

    stats = sub.add_parser("stats", help="Summarize logged calls.")
    stats.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
