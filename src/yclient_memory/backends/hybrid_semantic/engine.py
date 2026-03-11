from __future__ import annotations

from ...capabilities import MemoryCapabilities
from ...contracts import (
    BrowseMemoryContext,
    BrowseMemoryRequest,
    CommentMemoryEvent,
    MaintenanceTickRequest,
    MaintenanceTickResult,
    PostMemoryEvent,
    PostStyleContext,
    PostStyleRequest,
    RelationshipSignal,
    RelationshipSignalRequest,
    ReplyMemoryContext,
    ReplyMemoryRequest,
    VoteMemoryEvent,
)


class HybridSemanticMemoryEngine:
    def __init__(self, *, config, runtime):
        self.config = config
        self.runtime = runtime

    def capabilities(self) -> MemoryCapabilities:
        return MemoryCapabilities(
            semantic_search=True,
            relationship_memory=True,
            thread_memory=True,
            community_digest=True,
            reflections=True,
            high_affect_recall=self.config.high_affect_enabled,
            post_style_context=True,
        )

    def build_reply_context(self, request: ReplyMemoryRequest) -> ReplyMemoryContext:
        return ReplyMemoryContext()

    def build_browse_context(self, request: BrowseMemoryRequest) -> BrowseMemoryContext:
        return BrowseMemoryContext()

    def build_post_style_context(self, request: PostStyleRequest) -> PostStyleContext:
        return PostStyleContext()

    def record_comment(self, event: CommentMemoryEvent) -> None:
        return

    def record_vote(self, event: VoteMemoryEvent) -> None:
        return

    def record_post(self, event: PostMemoryEvent) -> None:
        return

    def relationship_signal(self, request: RelationshipSignalRequest) -> RelationshipSignal:
        return RelationshipSignal()

    def maintenance_tick(self, request: MaintenanceTickRequest) -> MaintenanceTickResult:
        return MaintenanceTickResult()
