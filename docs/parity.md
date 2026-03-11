# Parity Strategy

## Current approach

The package enforces parity with the current Reddit memory behavior through characterization tests derived from the upstream reference fixtures.

Covered areas:

- subtle reply context
- vote-signal-only suppression
- post-style context maturity behavior
- thread browse context
- high-affect fallback logic

## Why characterization instead of direct import

The upstream `YClientReddit` repo currently pulls in runtime dependencies and Python-version constraints that do not import cleanly in this repository's default environment. The characterization suite freezes the reference behavior in package-local tests so regressions are still caught.

## Validation commands

Default environment:

```bash
pytest -q
```

Python 3.12 characterization subset:

```bash
uv run --python 3.12 --with pytest python -m pytest -q tests/test_reddit_characterization.py
```

## Next parity step

When the upstream Reddit environment is stabilized, add a second validation stage that imports and executes the live reference methods directly.
