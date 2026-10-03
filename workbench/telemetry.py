"""Log every LLM call (tokens, latency, cost) to JSONL. This file grows into the eval engine."""
import json
from datetime import datetime, timezone
from pathlib import Path


def cost_usd(input_tokens: int, output_tokens: int,
             price_in: float | None, price_out: float | None) -> float | None:
    """Prices are USD per million tokens. Returns None if prices aren't configured."""
    if price_in is None or price_out is None:
        return None
    return round((input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6)


def log_call(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **record}
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def summarize(path: Path) -> dict:
    if not path.exists():
        return {"calls": 0}
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        return {"calls": 0}
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    return {
        "calls": len(rows),
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in rows) / len(rows)),
        "total_cost_usd": round(sum(costs), 6) if costs else None,
    }
