# workbench

**An open-source AI solutions workbench.** Point it at an organization's documents and a problem statement; it builds an LLM solution, evaluates it, and explains the tradeoffs: scope → build → evaluate → explain.

Built in public, one milestone at a time. See [ROADMAP.md](ROADMAP.md).

## Status: v0 — Foundations

v0 is a raw-HTTP LLM client that logs **tokens, latency, and cost for every call**. Measuring from day one is the seed of the eval engine.

## Quickstart

```bash
pip install -e ".[dev]"
cp .env.example .env        # fill in your key and model
set -a; source .env; set +a

workbench ask "Explain RAG in two sentences."
workbench stats
```

### Docker

```bash
docker build -t workbench .
docker run --rm --env-file .env -v "$PWD/.workbench:/app/.workbench" workbench ask "hello"
```

## Develop

```bash
pytest -q
```

## License

MIT
