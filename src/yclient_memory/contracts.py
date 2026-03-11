from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryDiagnostics:
    search_used: bool = False
    degraded_mode: bool = False
    embedding_degraded: bool = False
    no_ready_candidates: bool = False
    tier_c_used: bool = False
    retrieved_item_count: int = 0
    top_score: float | None = None
    fallback_used: bool = False
    usage: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryCueSet:
    scope: str = "none"
    callback_hint: str = ""
    continuity_hint: str = ""
    argument_hint: str = ""
    tone_hint: str = ""
    anecdote_hint: str = ""
    should_callback: bool = False
    rendered_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplyMemoryRequest:
    query_text: str
    other_user_id: int | None = None
    other_username: str | None = None
    thread_root_id: int | None = None
    round_id: int | None = None
    thread_context: str = ""
    incoming_text: str = ""
    uncertainty_score: float = 0.0
    mode: str = "comment"


@dataclass
class ReplyMemoryContext:
    rendered_text: str = ""
    cues: MemoryCueSet = field(default_factory=MemoryCueSet)
    diagnostics: MemoryDiagnostics = field(default_factory=MemoryDiagnostics)
    continuity_text: str = ""
    recalled_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BrowseMemoryRequest:
    thread_root_id: int | None
    round_id: int | None = None
    scan_snippets: list[str] = field(default_factory=list)


@dataclass
class BrowseMemoryContext:
    rendered_text: str = ""
    diagnostics: MemoryDiagnostics = field(default_factory=MemoryDiagnostics)


@dataclass
class PostStyleRequest:
    round_id: int


@dataclass
class PostStyleContext:
    rendered_text: str = ""
    diagnostics: MemoryDiagnostics = field(default_factory=MemoryDiagnostics)


@dataclass
class CommentMemoryEvent:
    round_id: int
    target_post_id: int
    thread_root_id: int
    other_user_id: int | None
    other_username: str | None = None
    other_text: str = ""
    my_text: str = ""
    conv_text: str = ""


@dataclass
class VoteMemoryEvent:
    round_id: int
    post_id: int
    vote_type: str
    other_user_id: int | None = None
    other_username: str | None = None
    thread_root_id: int | None = None
    post_text: str = ""


@dataclass
class PostMemoryEvent:
    round_id: int
    text: str
    post_id: int | None = None
    user_id: int | None = None
    origin_kind: str = "text_post"


@dataclass
class RelationshipSignalRequest:
    other_user_id: int | None
    thread_root_id: int | None = None


@dataclass
class RelationshipSignal:
    affinity: float = 0.0
    conflict: float = 0.0
    humor: float = 0.0
    trust: float = 0.0
    summary_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MaintenanceTickRequest:
    round_id: int
    reason: str = "periodic"


@dataclass
class MaintenanceTickResult:
    performed_actions: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
