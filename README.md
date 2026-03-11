# yclient-memory

`yclient-memory` is an in-tree implementation of the external memory package described in
[`external_memory_package_pipeline.md`](/Users/rossetti/PycharmProjects/y_memory_subsystem/external_memory_package_pipeline.md).

It provides:

- a stable `yclient_memory` import surface
- shared contracts and runtime protocols
- a `build_memory_engine()` factory
- two interchangeable backends:
  - `hybrid_semantic`
  - `simple_recent`

## Quick Start

```python
from yclient_memory import build_memory_engine
from yclient_memory.config import MemoryConfig

memory = build_memory_engine(
    backend="hybrid_semantic",
    config=MemoryConfig.from_mapping({"memory_vote_signal_only": True}),
    runtime=my_runtime_adapter,
)
```

## Development

```bash
python -m pytest
```
