# API Surface

## Public imports

```python
from yclient_memory import build_memory_engine
from yclient_memory import MemoryCapabilities
from yclient_memory.contracts import (
    BrowseMemoryRequest,
    CommentMemoryEvent,
    PostMemoryEvent,
    PostStyleRequest,
    RelationshipSignalRequest,
    ReplyMemoryRequest,
    VoteMemoryEvent,
)
```

## Factory

```python
memory = build_memory_engine(
    backend="hybrid_semantic",
    config=MemoryConfig.from_mapping(raw_config),
    runtime=runtime_adapter,
)
```

Supported backend names:

- `hybrid_semantic`
- `simple_recent`

## Engine protocol

Every backend implements the same methods:

- `capabilities()`
- `build_reply_context(request)`
- `build_browse_context(request)`
- `build_post_style_context(request)`
- `record_comment(event)`
- `record_vote(event)`
- `record_post(event)`
- `relationship_signal(request)`
- `maintenance_tick(request)`

## Contracts

Read-side contracts:

- `ReplyMemoryRequest`
- `ReplyMemoryContext`
- `BrowseMemoryRequest`
- `BrowseMemoryContext`
- `PostStyleRequest`
- `PostStyleContext`

Write-side contracts:

- `CommentMemoryEvent`
- `VoteMemoryEvent`
- `PostMemoryEvent`
- `MaintenanceTickRequest`
- `MaintenanceTickResult`

Analytical contracts:

- `RelationshipSignalRequest`
- `RelationshipSignal`
- `MemoryCueSet`
- `MemoryDiagnostics`
