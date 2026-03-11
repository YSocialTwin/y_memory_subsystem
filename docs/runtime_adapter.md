# Runtime Adapter

`yclient_memory` stays reusable by pushing client-specific thread, post, and LLM access behind a runtime adapter.

## Required shape

```python
class MemoryRuntime:
    def llm_json(self, prompt_key: str, variables: dict, config: dict | None = None): ...
    def llm_text(self, prompt_key: str, variables: dict, config: dict | None = None) -> str: ...
    def get_author_id_and_username(self, post_id: int) -> tuple[int | None, str | None]: ...
    def get_thread_root_id(self, post_id: int) -> int | None: ...
    def get_recent_root_posts(self, round_id: int, limit: int = 24, rounds_back: int = 18) -> list[dict]: ...
    def get_post_text(self, post_id: int) -> str: ...
    def persona_snapshot(self) -> dict: ...
    def decision_log(self, payload: dict) -> None: ...
```

## Design rules

- Keep raw storage lookups in the adapter, not in the package.
- Return plain Python data structures.
- Treat `llm_json()` as optional for `simple_recent` but available for `hybrid_semantic`.
- Make `decision_log()` best-effort; the package already tolerates adapter logging failures.

## Minimal stub

```python
class RuntimeStub:
    def llm_json(self, prompt_key, variables, config=None):
        return {}

    def llm_text(self, prompt_key, variables, config=None):
        return ""

    def get_author_id_and_username(self, post_id):
        return None, None

    def get_thread_root_id(self, post_id):
        return None

    def get_recent_root_posts(self, round_id, limit=24, rounds_back=18):
        return []

    def get_post_text(self, post_id):
        return ""

    def persona_snapshot(self):
        return {}

    def decision_log(self, payload):
        return None
```
