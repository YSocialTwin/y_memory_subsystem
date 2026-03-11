from __future__ import annotations

from typing import Any, Protocol


class MemoryRuntime(Protocol):
    def llm_json(
        self, prompt_key: str, variables: dict[str, Any], config: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any] | str: ...

    def llm_text(
        self, prompt_key: str, variables: dict[str, Any], config: dict[str, Any] | None = None
    ) -> str: ...

    def get_author_id_and_username(self, post_id: int) -> tuple[int | None, str | None]: ...

    def get_thread_root_id(self, post_id: int) -> int | None: ...

    def get_recent_root_posts(
        self, round_id: int, limit: int = 24, rounds_back: int = 18
    ) -> list[dict[str, Any]]: ...

    def get_post_text(self, post_id: int) -> str: ...

    def persona_snapshot(self) -> dict[str, Any]: ...

    def decision_log(self, payload: dict[str, Any]) -> None: ...
