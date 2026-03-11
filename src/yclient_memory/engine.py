from __future__ import annotations

from typing import Protocol

from .capabilities import MemoryCapabilities
from .contracts import (
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


class MemoryEngine(Protocol):
    def capabilities(self) -> MemoryCapabilities: ...

    def build_reply_context(self, request: ReplyMemoryRequest) -> ReplyMemoryContext: ...

    def build_browse_context(self, request: BrowseMemoryRequest) -> BrowseMemoryContext: ...

    def build_post_style_context(self, request: PostStyleRequest) -> PostStyleContext: ...

    def record_comment(self, event: CommentMemoryEvent) -> None: ...

    def record_vote(self, event: VoteMemoryEvent) -> None: ...

    def record_post(self, event: PostMemoryEvent) -> None: ...

    def relationship_signal(self, request: RelationshipSignalRequest) -> RelationshipSignal: ...

    def maintenance_tick(self, request: MaintenanceTickRequest) -> MaintenanceTickResult: ...
