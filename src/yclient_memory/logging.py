from __future__ import annotations

from typing import Any


def emit_decision_log(runtime: Any, payload: dict[str, Any]) -> None:
    try:
        runtime.decision_log(payload)
    except Exception:
        return
