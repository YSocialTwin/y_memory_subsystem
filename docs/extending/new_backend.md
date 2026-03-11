# Build a New Backend

## Goal

A new backend must preserve the same external engine signature even if it supports fewer capabilities.

## Required steps

1. Add a backend package under `src/yclient_memory/backends/<name>/`
2. Implement the engine methods required by `MemoryEngine`
3. Return a coherent `MemoryCapabilities` object
4. Register the backend in `build_memory_engine()`
5. Add backend-specific tests
6. Add at least one contract-level test ensuring the backend returns the shared contract types

## Implementation checklist

- Accept `config` and `runtime` in the constructor
- Keep client-specific data access in the runtime adapter
- Use shared policy helpers where behavior overlaps existing backends
- Return empty/default contexts instead of raising when a capability is unsupported

## Recommended test coverage

- reply context output
- browse context output
- write-path behavior
- relationship signal behavior
- maintenance behavior
- capability advertisement

## Example skeleton

```python
class MyMemoryEngine:
    def __init__(self, *, config, runtime):
        self.config = config
        self.runtime = runtime

    def capabilities(self):
        return MemoryCapabilities(...)
```
