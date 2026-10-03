# Roadmap

Milestones, not dates. Each one ships something usable.

## v0 — Foundations ✅ scaffolded
- [x] Raw-HTTP client for the Messages API (no SDK)
- [x] Per-call telemetry: tokens, latency, cost → JSONL
- [x] `ask` and `stats` commands, Docker, CI
- [ ] Exercise: streaming responses (Server-Sent Events)
- [ ] Exercise: retries with exponential backoff on 429/5xx
- [ ] Exercise: multi-turn chat with history

## v1 — LLM apps
- [ ] Tool calling (agent loop)
- [ ] Ingest a folder of docs + RAG retrieval
- [ ] Expose tools over MCP

## v2 — Integration
- [ ] FastAPI service, Postgres, auth
- [ ] One real connector (e.g. Google Drive or Notion)
- [ ] Deploy

## v3 — Eval
- [ ] Golden-set runner (telemetry → eval engine)
- [ ] Guardrails
- [ ] Quality / latency / cost report per run

## v4 — Client
- [ ] Generate a scoped design doc + cost estimate from eval results

## v5 — Ship
- [ ] Docs site, demo video, case study
