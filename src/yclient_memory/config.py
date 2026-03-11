from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryConfig:
    enabled: bool = True
    backend: str = "hybrid_semantic"
    backend_fallback: str = "simple_recent"
    prompt_mode: str = "subtle_forum"
    vote_signal_only: bool = True
    reply_context_max_chars: int = 280
    nuance_enabled: bool = True
    nuance_min_score: float = 0.35
    nuance_callback_probability: float = 0.55
    nuance_cues_max_chars: int = 900
    cross_thread_callback_min_score: float = 0.80
    search_k: int = 8
    search_max_chars: int = 900
    total_max_chars: int = 1400
    tier_a_max_chars: int = 280
    tier_b_max_chars: int = 720
    tier_c_max_chars: int = 520
    tier_c_uncertainty_threshold: float = 0.45
    digest_update_cadence_rounds: int = 3
    digest_events_limit: int = 24
    reflection_cadence_rounds: int = 3
    reflection_min_events: int = 12
    reflection_trigger_importance_sum: float = 3.5
    reflection_max_items_per_run: int = 60
    high_affect_enabled: bool = False
    high_affect_rule_threshold: float = 0.55
    high_affect_uncertain_low: float = 0.35
    high_affect_uncertain_high: float = 0.70
    high_affect_search_k: int = 12
    high_affect_max_items: int = 6
    high_affect_max_chars: int = 900
    high_affect_llm_fallback: bool = True
    pair_history_limit: int = 8
    thread_history_limit: int = 12
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> "MemoryConfig":
        raw = dict(raw or {})
        extra = dict(raw)
        config = cls(
            enabled=bool(raw.get("memory_enabled", raw.get("enabled", True))),
            backend=str(raw.get("memory_backend", raw.get("backend", "hybrid_semantic"))),
            backend_fallback=str(
                raw.get("memory_backend_fallback", raw.get("backend_fallback", "simple_recent"))
            ),
            prompt_mode=str(raw.get("memory_prompt_mode", raw.get("prompt_mode", "subtle_forum"))),
            vote_signal_only=bool(raw.get("memory_vote_signal_only", raw.get("vote_signal_only", True))),
            reply_context_max_chars=int(
                raw.get("memory_reply_context_max_chars", raw.get("reply_context_max_chars", 280))
            ),
            high_affect_enabled=bool(
                raw.get("memory_high_affect_enabled", raw.get("high_affect_enabled", False))
            ),
            cross_thread_callback_min_score=float(
                raw.get(
                    "memory_cross_thread_callback_min_score",
                    raw.get("cross_thread_callback_min_score", 0.80),
                )
            ),
            high_affect_rule_threshold=float(
                raw.get("memory_high_affect_rule_threshold", raw.get("high_affect_rule_threshold", 0.55))
            ),
            high_affect_uncertain_low=float(
                raw.get("memory_high_affect_uncertain_low", raw.get("high_affect_uncertain_low", 0.35))
            ),
            high_affect_uncertain_high=float(
                raw.get("memory_high_affect_uncertain_high", raw.get("high_affect_uncertain_high", 0.70))
            ),
            high_affect_search_k=int(
                raw.get("memory_high_affect_search_k", raw.get("high_affect_search_k", 12))
            ),
            high_affect_max_items=int(
                raw.get("memory_high_affect_max_items", raw.get("high_affect_max_items", 6))
            ),
            high_affect_max_chars=int(
                raw.get("memory_high_affect_max_chars", raw.get("high_affect_max_chars", 900))
            ),
            high_affect_llm_fallback=bool(
                raw.get("memory_high_affect_llm_fallback", raw.get("high_affect_llm_fallback", True))
            ),
            nuance_enabled=bool(raw.get("memory_nuance_enabled", raw.get("nuance_enabled", True))),
            pair_history_limit=int(raw.get("pair_history_limit", 8)),
            thread_history_limit=int(raw.get("thread_history_limit", 12)),
            extra=extra,
        )
        return config
