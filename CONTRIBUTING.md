# Contributing

## Getting started

1. Fork the repository.
2. Create a feature branch from `main`.
3. Install dependencies: `pip install -e ".[dev]"`
4. Make your changes.

## Running tests

```bash
python -m pytest test_compress.py -v
```

Tests require Ollama running locally with `qwen3:4b` pulled.

## Code style

- Line length: 100
- Target: Python 3.10+

## Pull requests

1. Keep changes focused — one feature or fix per PR.
2. Add tests for new functionality.
3. Update `CHANGELOG.md` under an `Unreleased` section.
4. Open a PR against `main` with a clear description of what and why.
