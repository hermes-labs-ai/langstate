# Contributing

## Getting started

1. Fork the repository.
2. Create a feature branch from `main`.
3. Install dependencies: `pip install -e ".[dev]"`
4. Make your changes.

## Running tests

```bash
python -m pytest tests/ -v
```

The default run is network-free. To also run the live Ollama integration
tests, set `LANGSTATE_LIVE_OLLAMA=1` with Ollama running locally and
`qwen3:4b` pulled.

## Code style

- Line length: 100
- Target: Python 3.10+

## Pull requests

1. Keep changes focused — one feature or fix per PR.
2. Add tests for new functionality.
3. Update `CHANGELOG.md` under an `Unreleased` section.
4. Open a PR against `main` with a clear description of what and why.
