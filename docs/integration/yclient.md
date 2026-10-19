# YClient Replacement

## Goal

Adopt the same package in `YClient` while mapping its timeline/post model into the shared memory contracts.

Reference files:

- `../../../YClient/y_client/classes/base_agent.py`

## Recommended rollout

1. Start with `simple_recent`
2. Implement a `YClient` runtime adapter
3. Replace action-specific memory strings with package calls
4. Keep memory disabled by default until server/runtime support is ready
5. Add `hybrid_semantic` only after the richer backend services are available

## Concept mapping

- Reddit thread card -> timeline/conversation card
- Reddit community digest -> timeline style digest
- Reddit reply context -> comment/reply memory context

## Minimal integration surface

Read path:

- comment/reply actions use `build_reply_context`
- read/search ranking can use `build_browse_context`
- post composition can use `build_post_style_context`

Write path:

- replies/comments call `record_comment`
- likes/dislikes call `record_vote`
- root posts/shares call `record_post`

## Why start with `simple_recent`

- lower adoption risk
- no need to mirror the full Reddit retrieval stack immediately
- easier to validate in the timeline-first client

## Upgrade path to `hybrid_semantic`

Move to `hybrid_semantic` only after:

- runtime adapter supports richer context retrieval
- server-side storage/search parity exists
- characterization-style tests are added for YClient-specific scenarios
