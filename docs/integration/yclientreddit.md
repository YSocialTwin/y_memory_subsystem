# YClientReddit Replacement

## Goal

Replace direct `_memory_*` usage in `YClientReddit` with package-backed calls while preserving current behavior.

Reference implementation location:

- `../../../YClientReddit/y_client/classes/base_agent.py`

## Recommended migration

1. Instantiate a runtime adapter inside `Agent`
2. Translate current config into `MemoryConfig`
3. Build the package engine during agent initialization
4. Replace read-path helper calls with engine calls
5. Replace write-path helper calls with engine calls
6. Keep old helper methods temporarily as thin wrappers if needed during migration

## Runtime adapter responsibilities

The Reddit adapter should provide:

- author lookup by post id
- thread-root lookup by post id
- recent root post fetch
- post text fetch
- memory-related LLM calls
- decision logging

## Replacement mapping

Current helper to package call:

- `_memory_build_reply_context` -> `build_reply_context`
- `_memory_build_thread_browse_context` -> `build_browse_context`
- `_memory_build_post_style_context` -> `build_post_style_context`
- `_memory_after_comment` -> `record_comment`
- `_memory_after_vote` -> `record_vote`

## Config mapping

Existing Reddit config keys can be passed through `MemoryConfig.from_mapping()` with no call-site renaming required for the implemented fields.

## Validation checklist

- run package tests
- run characterization tests in this repo
- run the upstream Reddit memory tests after replacing the wiring
- confirm prompt-visible memory still suppresses vote artifacts
