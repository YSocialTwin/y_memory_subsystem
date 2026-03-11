# yclient-memory

`yclient-memory` packages the agent memory subsystem so both `YClientReddit` and `YClient` can call the same public API while choosing different backends.

## What is implemented

- Stable package import surface: `yclient_memory`
- Shared contracts, config, and runtime interfaces
- Backend factory: `build_memory_engine()`
- `hybrid_semantic` backend for the richer Reddit-derived behavior
- `simple_recent` backend for low-dependency adoption
- Characterization tests derived from the current `YClientReddit` reference behavior
- Example notebooks for both backends

## Core design

The package isolates memory logic into three layers:

1. Contracts and engine protocol
2. Runtime adapter
3. Backend implementation

That separation keeps client-specific storage, thread models, and LLM orchestration outside the package.

## Repository layout

```text
src/yclient_memory/
  __init__.py
  factory.py
  contracts.py
  config.py
  runtime.py
  policies/
  backends/
tests/
docs/
output/jupyter-notebook/
```

## Starting point

```python
from yclient_memory import build_memory_engine
from yclient_memory.config import MemoryConfig

memory = build_memory_engine(
    backend="hybrid_semantic",
    config=MemoryConfig.from_mapping({"memory_vote_signal_only": True}),
    runtime=my_runtime_adapter,
)
```
